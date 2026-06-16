"""CLI entrypoint for sending a WeChat message.

Use arguments for normal calls. Environment variables are supported to avoid
Windows command-line encoding problems with Chinese text:

    HERMES_WECHAT_CONTACT
    HERMES_WECHAT_MESSAGE
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wechat_utils import send_wechat_message


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a WeChat message via Hermes skill scripts.")
    parser.add_argument("--contact", default=os.environ.get("HERMES_WECHAT_CONTACT", ""))
    parser.add_argument("--message", default=os.environ.get("HERMES_WECHAT_MESSAGE", ""))
    parser.add_argument("--dry-run", action="store_true", help="Print parsed contact/message without sending.")
    args = parser.parse_args()

    contact = (args.contact or "").strip()
    message = args.message or ""
    if not contact:
        print("ERROR: missing contact. Use --contact or HERMES_WECHAT_CONTACT.", file=sys.stderr)
        return 2
    if not message:
        print("ERROR: missing message. Use --message or HERMES_WECHAT_MESSAGE.", file=sys.stderr)
        return 2

    if args.dry_run:
        print(f"CONTACT={contact}")
        print(f"MESSAGE={message}")
        return 0

    ok = send_wechat_message(contact, message)
    print(f"SEND_OK={bool(ok)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
