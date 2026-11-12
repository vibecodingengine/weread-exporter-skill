# Skill installation

Claude Code may load `.claude-plugin/` after `./install.sh`.

For Codex, link `codex-skill/weread-book-exporter` into the user's Codex skill directory:

```bash
ln -s "$(pwd)/codex-skill/weread-book-exporter" ~/.codex/skills/weread-book-exporter
```

The skill invokes the repository's `.venv`; it never installs packages globally.
