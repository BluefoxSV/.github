#!/usr/bin/env python3
"""Sync ERP Project children from their parent Story.

- Story Status=Ready -> child Tasks in Backlog become Ready
  (skips In progress and Done)
- Story Sprint set -> child Tasks get the same Sprint
- Child Task In progress -> parent Story Backlog/Ready becomes In progress
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

PROJECT_OWNER = os.environ.get("PROJECT_OWNER", "BluefoxSV")
PROJECT_NUMBER = int(os.environ.get("PROJECT_NUMBER", "19"))
STATUS_FIELD_ID = os.environ["STATUS_FIELD_ID"]
SPRINT_FIELD_ID = os.environ["SPRINT_FIELD_ID"]
STATUS_READY_OPTION_ID = os.environ["STATUS_READY_OPTION_ID"]
STATUS_IN_PROGRESS_OPTION_ID = os.environ["STATUS_IN_PROGRESS_OPTION_ID"]

QUERY = """
query ($login: String!, $number: Int!, $cursor: String) {
  organization(login: $login) {
    projectV2(number: $number) {
      id
      items(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          content {
            __typename
            ... on Issue {
              number
              title
              state
              issueType { name }
              repository { nameWithOwner }
              parent {
                number
                issueType { name }
                repository { nameWithOwner }
              }
            }
          }
          fieldValues(first: 20) {
            nodes {
              __typename
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field { ... on ProjectV2SingleSelectField { name } }
              }
              ... on ProjectV2ItemFieldIterationValue {
                title
                iterationId
                field { ... on ProjectV2IterationField { name } }
              }
            }
          }
        }
      }
    }
  }
}
"""


def gh_graphql(query: str, **variables) -> dict:
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        if value is None:
            continue
        if isinstance(value, int):
            cmd.extend(["-F", f"{key}={value}"])
        else:
            cmd.extend(["-f", f"{key}={value}"])
    raw = subprocess.check_output(cmd, text=True)
    data = json.loads(raw)
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data


def parse_item(node: dict) -> dict | None:
    content = node.get("content") or {}
    if content.get("__typename") != "Issue":
        return None
    repo = (content.get("repository") or {}).get("nameWithOwner")
    number = content.get("number")
    if not repo or number is None:
        return None
    status = None
    sprint_title = None
    sprint_id = None
    for fv in (node.get("fieldValues") or {}).get("nodes") or []:
        field = (fv.get("field") or {}).get("name")
        if fv.get("__typename") == "ProjectV2ItemFieldSingleSelectValue" and field == "Status":
            status = fv.get("name")
        if fv.get("__typename") == "ProjectV2ItemFieldIterationValue" and field == "Sprint":
            sprint_title = fv.get("title")
            sprint_id = fv.get("iterationId")
    parent = content.get("parent")
    parent_key = None
    if parent and parent.get("number") is not None:
        prepo = (parent.get("repository") or {}).get("nameWithOwner")
        if prepo:
            parent_key = f"{prepo}#{parent['number']}"
    itype = ((content.get("issueType") or {}).get("name")) or ""
    return {
        "item_id": node["id"],
        "key": f"{repo}#{number}",
        "title": content.get("title") or "",
        "state": content.get("state") or "",
        "type": itype,
        "status": status or "",
        "sprint_title": sprint_title or "",
        "sprint_id": sprint_id or "",
        "parent_key": parent_key,
    }


def item_edit(**kwargs) -> bool:
    cmd = ["gh", "project", "item-edit"]
    for key, value in kwargs.items():
        cmd.extend([f"--{key.replace('_', '-')}", value])
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        return False
    return True


def main() -> int:
    cursor = None
    project_id = None
    items: list[dict] = []
    while True:
        payload = gh_graphql(
            QUERY,
            login=PROJECT_OWNER,
            number=PROJECT_NUMBER,
            cursor=cursor,
        )
        project = payload["data"]["organization"]["projectV2"]
        if not project:
            print("::warning::No se pudo leer el Project ERP. Revisa permisos de la GitHub App para el Project ERP.")
            return 0
        project_id = project["id"]
        conn = project["items"]
        for node in conn["nodes"]:
            parsed = parse_item(node)
            if parsed:
                items.append(parsed)
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]

    by_key = {item["key"]: item for item in items}
    children_by_parent: dict[str, list[dict]] = {}
    for item in items:
        if item["type"] == "Task" and item["parent_key"]:
            children_by_parent.setdefault(item["parent_key"], []).append(item)

    ready_n = sprint_n = progress_n = 0

    for story in items:
        if story["type"] != "Story":
            continue
        kids = children_by_parent.get(story["key"]) or []

        if story["status"] == "Ready":
            for kid in kids:
                if kid["status"] != "Backlog":
                    continue
                print(f"Ready: {kid['key']} ({kid['title']}) Backlog -> Ready  parent={story['key']}")
                if item_edit(
                    id=kid["item_id"],
                    project_id=project_id,
                    field_id=STATUS_FIELD_ID,
                    single_select_option_id=STATUS_READY_OPTION_ID,
                ):
                    kid["status"] = "Ready"
                    ready_n += 1

        if story["sprint_id"]:
            for kid in kids:
                if kid["sprint_id"] == story["sprint_id"]:
                    continue
                print(
                    f"Sprint: {kid['key']} ({kid['title']}) "
                    f"{kid['sprint_title'] or '(none)'} -> {story['sprint_title']}  parent={story['key']}"
                )
                if item_edit(
                    id=kid["item_id"],
                    project_id=project_id,
                    field_id=SPRINT_FIELD_ID,
                    iteration_id=story["sprint_id"],
                ):
                    kid["sprint_id"] = story["sprint_id"]
                    kid["sprint_title"] = story["sprint_title"]
                    sprint_n += 1

    for task in items:
        if task["type"] != "Task" or task["status"] != "In progress" or not task["parent_key"]:
            continue
        story = by_key.get(task["parent_key"])
        if not story or story["type"] != "Story":
            continue
        if story["state"] != "OPEN":
            continue
        if story["status"] not in ("Backlog", "Ready"):
            continue
        print(
            f"In progress: {story['key']} ({story['title']}) "
            f"{story['status']} -> In progress  from={task['key']}"
        )
        if item_edit(
            id=story["item_id"],
            project_id=project_id,
            field_id=STATUS_FIELD_ID,
            single_select_option_id=STATUS_IN_PROGRESS_OPTION_ID,
        ):
            story["status"] = "In progress"
            progress_n += 1

    print(f"Done. ready={ready_n} sprint={sprint_n} story_in_progress={progress_n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
