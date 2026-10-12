# BluefoxSV shared GitHub configuration

This public repository provides organization-default Issue Forms and reusable
ERP project workflows.
It must stay public for GitHub to provide the default Issue Forms. Reusable
workflows can also be shared from private repositories.

- `.github/ISSUE_TEMPLATE/` provides ERP Issue Forms to BluefoxSV repositories
  without local issue templates or a local issue template configuration.
- `.github/workflows/` contains reusable workflows called by small event
  workflows in FoxPosReact and BluefoxAPI. These files do not run automatically
  in other repositories.
- The ERP board sync is started manually from FoxPosReact Actions. Its script
  is packaged as a composite action under `.github/actions/sync-story/`.

The reusable workflows use the calling repository's `BOT_CLIENT_ID` variable
and `BOT_PRIVATE_KEY` secret to authenticate as the organization GitHub App.
The caller passes its runner choice through `runner_json`.
