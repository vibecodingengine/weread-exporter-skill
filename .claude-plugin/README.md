# WeRead Exporter plugin

This plugin exposes one tool, `export_weread_book`, for EPUB, TXT, or Markdown export. Run `./install.sh` from the repository root first.

Inputs are validated and bounded. Cookie values are never returned in tool output. First login should use `force_login: true`, `headless: true`, and a `login_timeout` between 30 and 600 seconds.
