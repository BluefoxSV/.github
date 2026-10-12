# BluefoxSV shared GitHub configuration

This public repository provides organization-default Issue Forms and reusable
ERP project workflows.
This repo should be public because of github shared workflows restriction.

- `.github/ISSUE_TEMPLATE/` is the source for ERP Issue Forms. Because this
  repository is private, GitHub does not inherit them automatically; copy them
  into each participating repository when they change.
- `.github/workflows/` contains reusable workflows called by small event
  workflows in FoxPosReact and BluefoxAPI. These files do not run automatically
  in other repositories.
- The ERP board sync is started manually from FoxPosReact Actions. Its script
  is packaged as a private composite action under `.github/actions/sync-story/`.

The reusable workflows use the calling repository's `BOT_CLIENT_ID` variable
and `BOT_PRIVATE_KEY` secret to authenticate as the organization GitHub App.
The caller passes its runner choice through `runner_json`.
