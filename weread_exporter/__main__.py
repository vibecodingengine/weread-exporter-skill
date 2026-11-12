import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path


async def async_main():
    from . import export, utils, webpage

    parser = argparse.ArgumentParser(
        prog="weread-exporter", description="WeRead book export cmdline tool"
    )
    parser.add_argument("-b", "--book-id", help="book id", required=True)
    parser.add_argument(
        "-o",
        "--output-format",
        help="output file format",
        action="append",
        choices=["md", "epub", "txt"],
    )
    parser.add_argument(
        "--load-timeout",
        help="load chapter page timeout",
        type=int,
        default=60,
    )
    parser.add_argument(
        "--load-interval",
        help="load chapter page interval time",
        type=int,
        default=30,
    )
    parser.add_argument(
        "--css-file",
        help="overide default css style",
    )
    parser.add_argument(
        "--headless", help="chrome headless", action="store_true", default=False
    )
    parser.add_argument(
        "--force-login", help="force login first", action="store_true", default=False
    )
    parser.add_argument(
        "--login-timeout",
        help="login QR code timeout in seconds (default: 180)",
        type=int,
        default=180,
    )
    parser.add_argument(
        "--mock-user-agent",
        help="use mock user-agent",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--proxy-server",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("WEREAD_EXPORTER_DATA_DIR", "~/.weread-exporter"),
        help="private session/cache directory (default: ~/.weread-exporter)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="directory for exported files (default: ./output)",
    )
    args = parser.parse_args()
    args.output_format = args.output_format or ["epub"]
    utils.validate_book_id(args.book_id)
    if args.load_timeout < 10 or args.load_timeout > 600:
        parser.error("--load-timeout must be between 10 and 600")
    if args.load_interval < 0 or args.load_interval > 300:
        parser.error("--load-interval must be between 0 and 300")
    if args.login_timeout < 30 or args.login_timeout > 600:
        parser.error("--login-timeout must be between 30 and 600")

    data_dir = Path(args.data_dir).expanduser().resolve()
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        data_dir.chmod(0o700)
    except OSError:
        pass
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(mode=0o755, parents=True, exist_ok=True)

    extra_css = None
    if args.css_file:
        if not os.path.isfile(args.css_file):
            raise RuntimeError("CSS file %s not exist" % args.css_file)
        with open(args.css_file) as fp:
            extra_css = fp.read()

    if "_" in args.book_id:
        # book list id
        book_list = [it["id"] for it in await utils.get_book_list(args.book_id)]
    else:
        book_list = [args.book_id]

    for book_id in book_list:
        logging.info("Exporting book %s" % book_id)
        page = webpage.WeReadWebPage(
            book_id,
            cookie_path=str(data_dir / "cookie.json"),
            webcache_path=str(data_dir / "cache"),
        )
        if not await page.check_valid():
            logging.warning("Book %s status is invalid, stop exporting" % book_id)
            continue

        # Check login status before launching browser
        if not args.force_login and not page._cookie.get("wr_vid"):
            print("\n" + "=" * 60)
            print("⚠️  Login Required")
            print("=" * 60)
            print(
                "No login session found. This is likely your first time using the tool."
            )
            print()
            print("To use this tool, you need to:")
            print("  1. Add the --force-login parameter to trigger login")
            print(
                "  2. Run: .venv/bin/python -m weread_exporter -b %s -o epub --headless --force-login"
                % book_id
            )
            print()
            print("Your first run will:")
            print("  - Start an isolated browser")
            print("  - Save a private QR screenshot and print its path")
            print("  - Wait for you to scan with WeChat mobile app")
            print("  - Save your login session for future use")
            print()
            print("After first login, you can omit --force-login parameter.")
            print("=" * 60 + "\n")
            logging.error(
                "No login session found. Please use --force-login parameter for first-time use."
            )
            return 2
        elif not args.force_login:
            logging.info("Found an existing login session")

        save_path = data_dir / "books" / book_id
        exporter = export.WeReadExporter(page, str(save_path))
        for attempt in range(1, 4):
            try:
                await page.launch(
                    headless=args.headless,
                    force_login=args.force_login,
                    mock_user_agent=args.mock_user_agent,
                    proxy_server=args.proxy_server,
                    login_timeout=args.login_timeout,
                )
            except RuntimeError:
                logging.exception(
                    "Launch attempt %d/3 failed for book %s", attempt, book_id
                )
                await page.close()
                if attempt == 3:
                    raise
                await asyncio.sleep(2)
                continue

            try:
                await exporter.export_markdown(args.load_timeout, args.load_interval)
            except utils.LoadChapterFailedError:
                logging.warning("Load chapter failed, close browser and retry")
                await page.close()
            else:
                await page.close()
                break
        else:
            raise RuntimeError("Export failed after three attempts")

        await exporter.pre_process_markdown()
        title = await exporter.get_book_title()
        title = utils.format_filename(title)
        if "md" in args.output_format:
            save_path = str(output_dir / ("%s.md" % title))
            if not os.path.isfile(save_path):
                await exporter.merge_markdown(save_path)
                logging.info("Save file %s complete" % save_path)
        if "epub" in args.output_format:
            save_path = str(output_dir / ("%s.epub" % title))
            if os.path.isfile(save_path):
                logging.info("File %s exist, ignore export" % save_path)
            else:
                await exporter.markdown_to_epub(save_path, extra_css=extra_css)
                logging.info("Save file %s complete" % save_path)

        if "txt" in args.output_format:
            save_path = str(output_dir / ("%s.txt" % title))
            if os.path.isfile(save_path):
                logging.info("File %s exist, ignore export" % save_path)
            else:
                await exporter.markdown_to_txt(save_path)
                logging.info("Save file %s complete" % save_path)
    return 0


def main():
    logging.root.level = logging.INFO
    handler = logging.StreamHandler()
    fmt = "[%(asctime)s][%(levelname)s]%(message)s"
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)
    logging.root.addHandler(handler)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_main())
    except Exception:
        import traceback

        traceback.print_exc()
        return 1
    finally:
        loop.close()


if __name__ == "__main__":
    sys.exit(main())
