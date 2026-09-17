"""Operator CLI: mint and revoke MCP HTTP credentials."""

from __future__ import annotations

import argparse
import sys

from app.db.mcp_tokens import create_token, revoke_token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage MCP HTTP credentials")
    sub = parser.add_subparsers(dest="command", required=True)

    create_p = sub.add_parser("create", help="Mint a credential; print secret once")
    create_p.add_argument("--label", required=True)
    create_p.add_argument("--role", required=True, choices=("admin", "reader"))

    revoke_p = sub.add_parser("revoke", help="Revoke active credential by label")
    revoke_p.add_argument("--label", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            cred, raw = create_token(args.label, args.role)
            print(f"id={cred.id}")
            print(f"label={cred.label}")
            print(f"role={cred.role}")
            print(f"token={raw}")
            return 0
        if args.command == "revoke":
            cred = revoke_token(args.label)
            print(f"revoked id={cred.id} label={cred.label} role={cred.role}")
            return 0
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
