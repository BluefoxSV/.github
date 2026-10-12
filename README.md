# BluefoxSV shared GitHub configuration

This public repository provides organization-default Issue Forms and reusable
ERP project workflows.

- `.github/ISSUE_TEMPLATE/` is inherited by BluefoxSV repositories that have no
  local issue template or `config.yml` in their own `.github/ISSUE_TEMPLATE/`.
- `.github/workflows/` contains reusable workflows called by small event
  workflows in FoxPosReact and BluefoxAPI. These files do not run automatically
  in other repositories.
- The ERP board sync is started manually from FoxPosReact Actions. Its script
  lives here under `.github/scripts/`.

The reusable workflows use the calling repository's `BOT_CLIENT_ID` variable
and `BOT_PRIVATE_KEY` secret to authenticate as the organization GitHub App.
The caller passes its runner choice through `runner_json`.
