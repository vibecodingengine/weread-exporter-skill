# WeRead Exporter (hardened)

Export books that the user can legitimately access in WeChat Reading. Supported formats are EPUB, TXT, and Markdown. PDF and MOBI are disabled to avoid vulnerable rendering dependencies and bundled native executables.

## Run

Use the repository virtual environment only:

```bash
.venv/bin/python -m weread_exporter -b <book_id> -o epub --headless
```

For first login on a remote server:

```bash
.venv/bin/python -m weread_exporter -b <book_id> -o epub --headless --force-login --login-timeout 300
```

Show the PNG named by `LOGIN_QR=<path>` to the user while the process continues to run. Never read or expose `~/.weread-exporter/cookie.json`.

## Security boundaries

- Book IDs may contain only letters, digits, `_`, and `-`.
- Network access is restricted to HTTPS hosts under `weread.qq.com`.
- Cookies are stored with mode `0600` and sent only to `weread.qq.com` itself.
- Do not add proxy, browser-profile, arbitrary URL, or filesystem parameters.
- Stop and report subscription, purchase, or access-control failures; do not bypass them.
