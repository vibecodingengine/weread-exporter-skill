#!/usr/bin/env python3
"""
WeRead Exporter Skill - Export accessible WeRead books

Usage as a skill:
  Input JSON: {"book_id": "xxx", "formats": ["epub", "txt"], "headless": false, ...}
"""

import argparse
import asyncio
import json
import os
import sys

# Add project root to path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from weread_exporter import utils


ALLOWED_FORMATS = frozenset({"epub", "txt", "md"})


def main():
    parser = argparse.ArgumentParser(
        prog="weread-exporter-skill", description="WeRead book exporter skill"
    )
    parser.add_argument("--skill-input", help="JSON input for skill execution")

    args = parser.parse_args()

    # If skill input is provided, parse and execute
    if args.skill_input:
        try:
            input_data = json.loads(args.skill_input)
            skill_main(input_data)
        except json.JSONDecodeError as e:
            print(f"Error parsing skill input: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Show usage information
        print("=" * 60)
        print("WeRead Exporter Skill")
        print("=" * 60)
        print()
        print("This skill exports accessible WeRead books to EPUB, TXT, or Markdown.")
        print()
        print("Usage:")
        print("  /export-weread-book <book_id> [options]")
        print()
        print("Parameters:")
        print("  book_id       (required)  The WeRead book ID")
        print(
            "                           Get it from: https://weread.qq.com/web/bookDetail/{id}"
        )
        print()
        print("Options:")
        print("  formats       (optional)  Output format(s): epub, txt, md")
        print("                           Default: epub")
        print(
            "  headless      (optional)  Run chrome in headless mode (default: false)"
        )
        print("  force_login   (optional)  Force login first (default: false)")
        print(
            "  login_timeout (optional)  Login QR code timeout in seconds (default: 180)"
        )
        print(
            "  load_timeout  (optional)  Load chapter timeout in seconds (default: 60)"
        )
        print(
            "  load_interval (optional)  Load chapter interval in seconds (default: 30)"
        )
        print()
        print("Examples:")
        print("  /export-weread-book 08232ac0720befa90825d88")
        print("  /export-weread-book 08232ac0720befa90825d88 --formats epub txt")
        print(
            "  /export-weread-book 08232ac0720befa90825d88 --formats epub --headless true"
        )
        print()
        print("Output:")
        print("  Exported files are saved to: ./output/")
        print()
        print("=" * 60)


def skill_main(input_data):
    """Main skill execution function"""
    # Validate required parameters
    book_id = input_data.get("book_id")
    try:
        utils.validate_book_id(book_id)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Validate formats against the intentionally small supported set.
    formats = input_data.get("formats", ["epub"])
    if (
        not isinstance(formats, list)
        or not formats
        or any(
            not isinstance(fmt, str) or fmt not in ALLOWED_FORMATS for fmt in formats
        )
    ):
        print("Error: formats may contain only epub, txt, or md", file=sys.stderr)
        sys.exit(1)

    # Build command arguments
    cmd_args = ["-m", "weread_exporter", "-b", book_id]
    for fmt in formats:
        cmd_args.extend(["-o", fmt])

    # Default to force_login for better compatibility
    force_login = input_data.get("force_login", False)
    if force_login:
        cmd_args.append("--force-login")

    # Optional parameters
    if input_data.get("headless"):
        cmd_args.append("--headless")

    load_timeout = input_data.get("load_timeout", 60)
    load_interval = input_data.get("load_interval", 30)
    login_timeout = input_data.get("login_timeout", 180)
    if (
        isinstance(load_timeout, bool)
        or not isinstance(load_timeout, int)
        or not 10 <= load_timeout <= 600
    ):
        raise ValueError("load_timeout must be between 10 and 600")
    if (
        isinstance(load_interval, bool)
        or not isinstance(load_interval, int)
        or not 0 <= load_interval <= 300
    ):
        raise ValueError("load_interval must be between 0 and 300")
    if (
        isinstance(login_timeout, bool)
        or not isinstance(login_timeout, int)
        or not 30 <= login_timeout <= 600
    ):
        raise ValueError("login_timeout must be between 30 and 600")
    cmd_args.extend(["--load-timeout", str(load_timeout)])
    cmd_args.extend(["--load-interval", str(load_interval)])
    cmd_args.extend(["--login-timeout", str(login_timeout)])

    # Execute the exporter
    print(f"Exporting WeRead book: {book_id}")
    print(f"Formats: {', '.join(formats)}")
    print()

    # The interpreter is fixed and every argument is allowlisted or range-checked.
    import subprocess  # nosec B404

    result = subprocess.run(  # nosec B603
        [sys.executable] + cmd_args, cwd=PROJECT_DIR, check=True
    )

    # Show output location
    output_dir = os.path.join(PROJECT_DIR, "output")
    print()
    print("=" * 60)
    print(f"Export completed! Check output directory: {output_dir}")
    print("=" * 60)

    # List exported files
    if os.path.exists(output_dir):
        files = os.listdir(output_dir)
        if files:
            print("Exported files:")
            for f in sorted(files):
                fpath = os.path.join(output_dir, f)
                if os.path.isfile(fpath):
                    size = os.path.getsize(fpath)
                    size_mb = size / (1024 * 1024)
                    print(f"  - {f} ({size_mb:.2f} MB)")

    return result.returncode


if __name__ == "__main__":
    main()
