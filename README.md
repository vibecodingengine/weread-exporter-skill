# WeRead Exporter — hardened fork

安全导出本人微信读书账号有权阅读的书籍，支持 EPUB、TXT 和 Markdown。

本 fork 针对原项目做了以下加固：

- Cookie 不再写入日志或 MCP 返回值；会话文件权限为 `0600`。
- 浏览器和 HTTP 客户端仅允许访问 `https://*.weread.qq.com`，Cookie 只发送给主域 `weread.qq.com`。
- 校验书籍 ID、章节 ID、输出路径、缓存路径、参数类型和数值范围。
- 使用 Playwright 取代旧的 pyppeteer/urllib3 依赖。
- 默认在 `.venv` 中安装；不修改全局 Python 环境。
- 删除预编译的 kindlegen/DLL，并禁用 PDF/MOBI 输出。
- 远程服务器登录会生成私有二维码截图，便于通过 Codex 展示后扫码。

此工具不会、也不应绕过购买、订阅或其他访问控制。

## 安装

需要 Python 3.11 或更高版本：

```bash
./install.sh
```

安装脚本创建 `.venv`，按带哈希的 `requirements.lock` 安装依赖，再安装 Playwright Chromium。不会全局执行 `pip install`。

## 使用

首次登录：

```bash
.venv/bin/python -m weread_exporter \
  -b 08232ac0720befa90825d88 \
  -o epub \
  --headless \
  --force-login \
  --login-timeout 300
```

程序输出 `LOGIN_QR=/absolute/path/login-qr.png` 后，用微信扫描该图片。登录会话保存在 `~/.weread-exporter/cookie.json`；不要分享这个文件。

后续导出：

```bash
.venv/bin/python -m weread_exporter -b 08232ac0720befa90825d88 -o epub --headless
```

可重复添加 `-o`，允许值为 `epub`、`txt`、`md`。结果默认写入 `output/`。

## Codex skill

Codex skill 位于 `codex-skill/weread-book-exporter/`。安装时可将该目录链接到 `~/.codex/skills/weread-book-exporter`。

## 验证

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip_audit -r requirements.txt --progress-spinner off
.venv/bin/python -m bandit -q -r .claude-plugin weread_exporter
```

## 来源

基于 `semicolonstail/weread-exporter-skill` 与 `drunkdream/weread-exporter`。本 fork 仅用于个人、合法访问内容的备份与格式转换。
