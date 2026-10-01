import io
import json
import unittest
import urllib.request
from unittest.mock import patch

from proxmoxlib.api import (
    ProxmoxClient,
    ProxmoxError,
    bridge_names,
    usable_bridges,
    usable_storages,
    vmid_is_used,
)
from proxmoxlib.cli import main


class FilterTests(unittest.TestCase):
    def test_usable_storages_keep_images_and_rootdir(self):
        rows = usable_storages(
            [
                {"storage": "local-zfs", "type": "zfspool", "content": "images,rootdir"},
                {"storage": "local", "type": "dir", "content": "iso,backup"},
                {"storage": "off", "type": "dir", "content": "images", "enabled": 0},
            ]
        )
        self.assertEqual(rows, [{"id": "local-zfs", "type": "zfspool", "content": ["images", "rootdir"]}])

    def test_usable_storages_keep_free_and_used_bytes(self):
        rows = usable_storages(
            [
                {
                    "storage": "local-zfs",
                    "type": "zfspool",
                    "content": "images",
                    "avail": 1024,
                    "used": "2048",
                }
            ]
        )
        self.assertEqual(rows[0]["avail"], 1024)
        self.assertEqual(rows[0]["used"], 2048)

    def test_bridges_include_cidr(self):
        rows = usable_bridges(
            [
                {"iface": "vmbr0", "type": "bridge", "cidr": "192.168.1.244/24"},
                {"iface": "vmbr1", "type": "bridge", "address": "10.0.0.1", "netmask": "255.255.255.0"},
                {"iface": "eth0", "type": "eth", "cidr": "192.168.1.2/24"},
            ]
        )
        self.assertEqual(
            rows,
            [
                {"name": "vmbr0", "cidr": "192.168.1.244/24"},
                {"name": "vmbr1", "cidr": "10.0.0.1/24"},
            ],
        )

    def test_bridges_and_vmid(self):
        self.assertEqual(
            bridge_names(
                [
                    {"iface": "vmbr0", "type": "bridge"},
                    {"iface": "eth0", "type": "eth"},
                ]
            ),
            ["vmbr0"],
        )
        self.assertTrue(vmid_is_used([{"type": "qemu", "vmid": 220}], 220))
        self.assertFalse(vmid_is_used([{"type": "node", "vmid": 220}], 220))
        self.assertFalse(vmid_is_used([{"type": "lxc", "vmid": 221}], 220))


class _Body:
    def __init__(self, payload: dict, status: int = 200):
        self._raw = json.dumps(payload).encode()
        self.status = status

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class ClientTests(unittest.TestCase):
    def test_login_then_nodes_and_token(self):
        calls = []

        def fake_urlopen(request, timeout=None, context=None):
            calls.append(request)
            path = request.full_url
            if path.endswith("/access/ticket"):
                body = request.data.decode()
                self.assertIn("password=secret", body)
                return _Body({"data": {"ticket": "TICKET", "CSRFPreventionToken": "CSRF"}})
            if path.endswith("/nodes"):
                self.assertIn("PVEAuthCookie=TICKET", request.headers["Cookie"])
                return _Body({"data": [{"node": "pve"}, {"node": "proxmox2"}]})
            if path.endswith("/token/atlas-ui"):
                self.assertEqual(request.headers["Csrfpreventiontoken"], "CSRF")
                self.assertIn("root%40pam", path)
                self.assertIn("privsep=0", request.data.decode())
                return _Body({"data": {"full-tokenid": "root@pam!atlas-ui", "value": "SECRET"}})
            raise AssertionError(path)

        with patch("proxmoxlib.api.urllib.request.urlopen", fake_urlopen):
            client = ProxmoxClient("192.168.1.20", "root@pam", "secret")
            self.assertEqual(client.nodes(), ["pve", "proxmox2"])
            created = client.create_token("atlas-ui")
        self.assertEqual(created["token_id"], "root@pam!atlas-ui")
        self.assertEqual(created["secret"], "SECRET")
        self.assertEqual(len(calls), 3)
        self.assertFalse(any(call.full_url.endswith("/access/acl") for call in calls))

    def test_http_error_hides_password(self):
        def fake_urlopen(request, timeout=None, context=None):
            raise urllib.request.HTTPError(
                request.full_url,
                401,
                "no",
                hdrs=None,
                fp=io.BytesIO(b'{"message":"authentication failure"}'),
            )

        # HTTPError signature uses fp; the urllib class expects hdrs email.message
        with patch("proxmoxlib.api.urllib.request.urlopen", fake_urlopen):
            client = ProxmoxClient("192.168.1.20", "root@pam", "secret")
            with self.assertRaises(ProxmoxError) as caught:
                client.nodes()
        self.assertNotIn("secret", str(caught.exception))
        self.assertIn("authentication failure", str(caught.exception))


class CliTests(unittest.TestCase):
    def test_version_does_not_need_a_password(self):
        stdout = io.StringIO()
        with patch("proxmoxlib.cli.sys.stdout", stdout):
            code = main(["--version"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(stdout.getvalue())["ok"])

    def test_missing_password(self):
        stdout = io.StringIO()
        with patch.dict("os.environ", {}, clear=True), patch("proxmoxlib.cli.sys.stdout", stdout):
            code = main(["--host", "192.168.1.20", "--user", "root@pam", "nodes"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertIn("PROXMOX_PASSWORD", payload["error"])


if __name__ == "__main__":
    unittest.main()
