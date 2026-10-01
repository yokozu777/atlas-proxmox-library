# Pre-publish checklist (`atlas-proxmox-library`)

Checklist before a public GitHub snapshot. This does not rewrite git history.

Companion: [`SECURITY.md`](../SECURITY.md).

## Automated gate

```bash
./tests/run_ci.sh
```

That runs the unit tests and checks that `LICENSE`, `SECURITY.md`, `.gitignore`, and
`.github/workflows/ci.yml` are present. It also rejects `mxhash` and private-key
markers in `proxmoxlib/`, `roles/`, and `README.md`.

## Manual checks

- `PROXMOX_PASSWORD` is not stored in the tree. Token secrets from `create-token`
  are not committed.
- `__pycache__/` stays untracked (`.gitignore`).
- Publish with `./push-github.sh`. That command drops `push-gitea.sh`,
  `push-github.sh`, and `git-publish-lib.sh` from the GitHub tree.
