# Security

## Reporting

If you discover a security issue in this repository, open a private report with the
maintainers. Do not file a public issue with exploit details, passwords, or API tokens.

## Secrets

The Proxmox password is the `PROXMOX_PASSWORD` environment variable. It is not a CLI
argument and must not be committed.

Do not commit:

- Proxmox passwords or API token secrets (`create-token` prints the secret once)
- SSH private keys
- filled `.env` files or `*.token` files

Tracked examples stay inert (`example.com`, a documentation host such as `192.168.1.20`).
Do not add lab passwords or internal hostnames to `proxmoxlib/`, `roles/`, or `README.md`.

## GitHub tree

`./push-github.sh` publishes `git@github.com:yokozu777/atlas-proxmox-library.git` and
removes `push-gitea.sh`, `push-github.sh`, and `git-publish-lib.sh` from that tree.
Those scripts may name internal git hosts. They stay on the operator checkout and are
not part of the public GitHub snapshot.

## Before this repository is public

1. Confirm no live secrets remain in tracked files. Rotate anything that was pushed.
2. Run `./tests/run_ci.sh`.
3. Follow [`docs/pre-publish.md`](docs/pre-publish.md).
