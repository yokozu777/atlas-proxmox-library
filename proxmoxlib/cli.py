"""JSON CLI. The password is read from PROXMOX_PASSWORD, never from argv."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from proxmoxlib import __version__
from proxmoxlib.api import ProxmoxClient, ProxmoxError

_TOKEN_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"


def _emit(payload: dict, code: int = 0) -> int:
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    return code


def _fail(message: str) -> int:
    return _emit({"ok": False, "error": message}, 1)


def _client(args: argparse.Namespace) -> ProxmoxClient:
    password = os.environ.get("PROXMOX_PASSWORD", "")
    if not password:
        raise ProxmoxError("PROXMOX_PASSWORD is not set")
    if not args.host.strip():
        raise ProxmoxError("host is required")
    if not args.user.strip():
        raise ProxmoxError("user is required")
    return ProxmoxClient(
        args.host,
        args.user,
        password,
        port=args.port,
        verify=args.verify,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="proxmox-library")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--host", default="")
    parser.add_argument("--user", default="root@pam")
    parser.add_argument("--port", type=int, default=8006)
    parser.add_argument("--verify", action="store_true")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("nodes")
    storages = sub.add_parser("storages")
    storages.add_argument("--node", required=True)
    bridges = sub.add_parser("bridges")
    bridges.add_argument("--node", required=True)
    vmid = sub.add_parser("vmid-free")
    vmid.add_argument("--vmid", required=True, type=int)
    token = sub.add_parser("create-token")
    token.add_argument("--token-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        return _emit({"ok": True, "version": __version__})
    if not args.command:
        return _fail("command is required")
    if args.port < 1 or args.port > 65535:
        return _fail("port is invalid")
    try:
        client = _client(args)
        if args.command == "nodes":
            return _emit({"ok": True, "nodes": client.nodes()})
        if args.command == "storages":
            return _emit({"ok": True, "storages": client.storages(args.node)})
        if args.command == "bridges":
            return _emit({"ok": True, "bridges": client.bridges(args.node)})
        if args.command == "vmid-free":
            if args.vmid < 100 or args.vmid > 999999999:
                return _fail("vmid is invalid")
            free = client.vmid_free(args.vmid)
            return _emit({"ok": True, "vmid": args.vmid, "free": free})
        if args.command == "create-token":
            if not re.fullmatch(_TOKEN_ID, args.token_id):
                return _fail("token id is invalid")
            created = client.create_token(args.token_id)
            return _emit({"ok": True, **created})
    except ProxmoxError as exc:
        return _fail(str(exc))
    return _fail(f"unknown command: {args.command}")
