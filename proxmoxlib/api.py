"""Small Proxmox VE API client. Password stays in the caller, never in URLs."""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DISK_CONTENTS = frozenset({"images", "rootdir"})
_GUEST_TYPES = frozenset({"qemu", "lxc"})


class ProxmoxError(Exception):
    """API or transport failure safe to show in the UI."""


def storage_contents(row: dict[str, Any]) -> set[str]:
    raw = row.get("content")
    if isinstance(raw, str):
        parts = raw.split(",")
    elif isinstance(raw, list):
        parts = [str(item) for item in raw]
    else:
        return set()
    return {part.strip() for part in parts if part.strip()}


def usable_storages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Storages that can hold a VM disk or a cloud-init drive."""
    found: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        enabled = row.get("enabled", 1)
        if enabled in (0, False, "0"):
            continue
        contents = storage_contents(row)
        if not contents & DISK_CONTENTS:
            continue
        storage_id = str(row.get("storage") or "").strip()
        if not storage_id:
            continue
        found.append(
            {
                "id": storage_id,
                "type": str(row.get("type") or ""),
                "content": sorted(contents),
            }
        )
    return found


def bridge_names(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("type") or "") != "bridge":
            continue
        name = str(row.get("iface") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def vmid_is_used(rows: list[dict[str, Any]], vmid: int) -> bool:
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("type") or "") not in _GUEST_TYPES:
            continue
        raw = row.get("vmid")
        if raw is None:
            continue
        try:
            if int(raw) == vmid:
                return True
        except (TypeError, ValueError):
            continue
    return False


def node_names(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("node") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def _host_for_url(host: str) -> str:
    text = host.strip()
    if ":" in text and not text.startswith("["):
        return f"[{text}]"
    return text


def _error_message(body: bytes, status: int) -> str:
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        return f"Proxmox API HTTP {status}"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text[:300]
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, dict) and errors:
            parts = [f"{key}: {value}" for key, value in errors.items()]
            return "; ".join(parts)[:300]
        message = payload.get("message")
        if message:
            return str(message).strip()[:300]
    return f"Proxmox API HTTP {status}"


class ProxmoxClient:
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        *,
        port: int = 8006,
        verify: bool = False,
        timeout: float = 20,
    ) -> None:
        self.host = host.strip()
        self.user = user.strip()
        self.password = password
        self.port = port
        self.timeout = timeout
        self._ticket = ""
        self._csrf = ""
        self._ssl = ssl.create_default_context() if verify else ssl._create_unverified_context()

    def _url(self, path: str) -> str:
        return f"https://{_host_for_url(self.host)}:{self.port}/api2/json{path}"

    def _call(
        self,
        method: str,
        path: str,
        form: dict[str, str] | None = None,
        *,
        auth: bool = True,
    ) -> Any:
        data = urllib.parse.urlencode(form).encode() if form is not None else None
        headers = {"Accept": "application/json"}
        if auth:
            if not self._ticket:
                self._login()
            headers["Cookie"] = f"PVEAuthCookie={self._ticket}"
            if method.upper() != "GET":
                headers["CSRFPreventionToken"] = self._csrf
        request = urllib.request.Request(
            self._url(path),
            data=data,
            headers=headers,
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout, context=self._ssl
            ) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = _error_message(exc.read(), exc.code)
            raise ProxmoxError(detail) from exc
        except urllib.error.URLError as exc:
            raise ProxmoxError(f"cannot reach {self.host}:{self.port}") from exc
        if not raw:
            return None
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ProxmoxError("Proxmox API returned invalid JSON") from exc
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    def _login(self) -> None:
        data = self._call(
            "POST",
            "/access/ticket",
            {"username": self.user, "password": self.password},
            auth=False,
        )
        if not isinstance(data, dict) or not data.get("ticket"):
            raise ProxmoxError("Proxmox login failed")
        self._ticket = str(data["ticket"])
        self._csrf = str(data.get("CSRFPreventionToken") or "")

    def nodes(self) -> list[str]:
        data = self._call("GET", "/nodes")
        if not isinstance(data, list):
            raise ProxmoxError("Proxmox nodes response is invalid")
        return node_names(data)

    def storages(self, node: str) -> list[dict[str, Any]]:
        quoted = urllib.parse.quote(node.strip(), safe="")
        data = self._call("GET", f"/nodes/{quoted}/storage")
        if not isinstance(data, list):
            raise ProxmoxError("Proxmox storage response is invalid")
        return usable_storages(data)

    def bridges(self, node: str) -> list[str]:
        quoted = urllib.parse.quote(node.strip(), safe="")
        data = self._call("GET", f"/nodes/{quoted}/network")
        if not isinstance(data, list):
            raise ProxmoxError("Proxmox network response is invalid")
        return bridge_names(data)

    def vmid_free(self, vmid: int) -> bool:
        data = self._call("GET", "/cluster/resources")
        if not isinstance(data, list):
            raise ProxmoxError("Proxmox resources response is invalid")
        return not vmid_is_used(data, vmid)

    def create_token(self, token_id: str, *, comment: str = "atlas-ui") -> dict[str, str]:
        user = urllib.parse.quote(self.user, safe="")
        token = urllib.parse.quote(token_id, safe="")
        data = self._call(
            "POST",
            f"/access/users/{user}/token/{token}",
            {"privsep": "1", "comment": comment},
        )
        if not isinstance(data, dict) or not data.get("value"):
            raise ProxmoxError("Proxmox did not return a token secret")
        full_id = str(data.get("full-tokenid") or f"{self.user}!{token_id}")
        self._call(
            "PUT",
            "/access/acl",
            {
                "path": "/",
                "roles": "PVEAdmin",
                "tokens": full_id,
                "propagate": "1",
            },
        )
        return {"token_id": full_id, "secret": str(data["value"])}
