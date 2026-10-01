# atlas-proxmox-library

Proxmox VE helpers for Atlas. The `proxmox-library` CLI talks to the API. Ansible roles call that same binary. Atlas UI uses the CLI for dropdowns, VMID checks, and API tokens.

**License:** Apache-2.0 ([`LICENSE`](LICENSE)).  
**Checks:** `./tests/run_ci.sh`

The password is the `PROXMOX_PASSWORD` environment variable. It is not an argument.

```bash
export PROXMOX_PASSWORD='…'
./proxmox-library --host 192.168.1.20 --user root@pam nodes
./proxmox-library --host 192.168.1.20 --user root@pam storages --node pve
./proxmox-library --host 192.168.1.20 --user root@pam bridges --node pve
./proxmox-library --host 192.168.1.20 --user root@pam vmid-free --vmid 220
./proxmox-library --host 192.168.1.20 --user root@pam create-token --token-id atlas-ui
```

Stdout is one JSON object. A failure is `{"ok": false, "error": "…"}` and exit code 1.

Roles: `check_vmid`, `list_nodes`, `list_storages`, `list_bridges`, `create_token`.

They expect `proxmox_host`, `proxmox_user`, `proxmox_password`, and when needed `proxmox_node`, `proxmox_vmid`, or `proxmox_token_id`. `proxmox_port` defaults to 8006. `proxmox_library_bin` overrides the CLI path.
