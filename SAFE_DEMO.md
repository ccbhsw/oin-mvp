# Safe Demo Guide

This guide is for a developer who has not previously trusted OIN MVP. Its default path performs one local operation only: it creates a new demo-only Ed25519 identity under `demo/data/operator-a/`. It does **not** capture a web page, start an API server, contact an Operator, read a personal key, search the home directory, load an API key, or upload data.

> Do not run commands from the historical research directories under `docs/innovation/` as a first demo. They are retained experiment material, not the supported safe-demo path.

## What the default demo does and does not do

| Property | Default safe demo |
| --- | --- |
| Network access | None. The container uses `network_mode: none`; the native command has no HTTP client invocation. |
| Sensitive-directory access | None. It uses only the current repository and `demo/data/`. It does not enumerate `~/.ssh`, browser profiles, wallets, cookies, cloud configuration, or environment secrets. |
| Privileges | No `sudo`, root, administrator permission, API key, cloud credential, or user-provided private key is required. |
| Files written | Only `demo/data/operator-a/identity/`, `keys/`, and `descriptors/`. The private key is created for this disposable demo and receives mode `0600` on Unix. |
| Files read | Project source plus the explicit demo paths. The container mounts only `oin/`, `network-demo/`, and `demo/data/`. |
| Remote code | None is downloaded or executed by the demo command. |
| Git impact | `demo/data/**` is ignored except for its empty `.gitkeep` skeleton. Do not add its generated files to Git. |

The demo creates a private key because an OIN observer needs a signing identity. It never asks for an existing user key and never reads one from an SSH, browser, wallet, cloud, or home directory path.

## Option A — native offline demo

Use an isolated Python virtual environment located under `demo/data/`, not under the user’s home directory or the repository root. Package installation is the only setup step that may contact a package index; it downloads the reviewed, version-pinned and hash-verified dependencies in `requirements.lock`. `PIP_CONFIG_FILE=/dev/null` avoids loading user pip configuration and `PIP_NO_CACHE_DIR=1` prevents a package cache outside the demo directory. If you require completely offline setup, install from a locally reviewed wheelhouse and use `--no-index` instead.

```bash
cd oin-mvp
mkdir -p demo/data
python3 -m venv ./demo/data/venv
PIP_CONFIG_FILE=/dev/null PIP_NO_CACHE_DIR=1 ./demo/data/venv/bin/python -m pip install \
  --require-hashes -r requirements.lock

./demo/data/venv/bin/python network-demo/tools/operator.py init \
  ./demo/data/operator-a \
  --operator-id did:oin-local:safe-demo

./demo/data/venv/bin/python network-demo/tools/operator.py verify \
  ./demo/data/operator-a/evidence/does-not-exist || true
```

The last command is intentionally offline and returns `NOT_FOUND`; it demonstrates that verification does not contact an OIN server. The virtual environment and generated identity are the only mutable material, and both remain under `demo/data/`.

## Option B — isolated Docker/Compose demo

`docker-compose.safe-demo.yml` is supplied for environments that already have a locally reviewed image tagged `oin-mvp-safe:local`. It does not use `build:` or `pull_policy`, so `docker compose` does not automatically pull an image. Its default command creates the same demo-only identity as Option A.

```bash
cd oin-mvp
mkdir -p demo/data
export OIN_DEMO_UID="$(id -u)"
export OIN_DEMO_GID="$(id -g)"
docker compose -f docker-compose.safe-demo.yml run --rm safe-demo
```

The container configuration applies all of the following boundaries:

```text
network_mode: none
read_only: true
cap_drop: ALL
security_opt: no-new-privileges:true
tmpfs: /tmp with noexec,nosuid
host mounts: ./oin (read-only), ./network-demo (read-only), ./demo/data (read-write)
```

The configuration does not use `privileged`, host networking, host PID namespaces, Docker socket mounts, home-directory mounts, SSH-agent mounts, or cloud credential mounts. It requires Docker daemon access, but the documented command does not use `sudo` or root in the container.

### Building the image is an explicit separate action

If you choose to build `oin-mvp-safe:local`, inspect `Dockerfile` and the committed `requirements-build.lock` / `requirements.lock` first. A build pulls `python:3.11-slim` and downloads the hash-locked Python distributions from package sources; that is a networked build-chain action, not part of the no-network demo run.

```bash
cd oin-mvp
# Optional, explicit, networked build action after reviewing Dockerfile and pyproject.toml:
docker build --tag oin-mvp-safe:local .
```

The current audit environment did not have Docker installed, so this Compose file was statically reviewed but not executed here.

## Explicitly networked actions

The following operations are **not** part of the safe demo. Run them only after choosing and reviewing each target.

| Action | Network destination | Data sent | Default? |
| --- | --- | --- | --- |
| `operator.py capture <URL>` or `oin capture <URL>` | The exact public HTTP(S) URL supplied by the user, including validated redirect targets. | An HTTP GET with `OIN-Observer/0.1` or the configured user agent; no local files are uploaded. | No. |
| API `POST /v1/captures` | The request’s validated public URL and redirect targets. | HTTP GET request only; captured response is stored locally or in explicitly configured storage. | No. |
| API `POST /v1/replication/pull` | The explicitly supplied peer URL. Private peers are rejected by default; Docker internal peers require both `OIN_ALLOW_PRIVATE_PEERS=1` and an `OIN_ALLOWED_PRIVATE_PEER_HOSTS` allowlist. | GET requests for peer identifiers and exported observation packages. | No. |
| API `tsa_url` option | The validated public RFC 3161 TSA URL supplied by the caller. | A timestamp query containing a hash of the signed manifest. | No. |
| Optional S3 storage | The bucket/endpoint configured through explicit `OIN_S3_*` and AWS environment variables. | OIN archive bytes and storage operations. | No. |
| Docker image build / `pip install` | The configured container registry and Python package index, unless an offline local source is configured. | Dependency download requests. | No. |

## Do not use these defaults as production controls

The normal `docker-compose.yml` starts three API nodes and maps their ports to loopback only. It explicitly enables `OIN_ALLOW_PRIVATE_PEERS=1` and allowlists only `observer-a`, `observer-b`, and `observer-c` so that those containers can replicate over their private Compose network. Its optional `adapters` profile contains development-only Postgres and MinIO credentials; do not use those credentials outside an isolated development environment.

The API has no authentication, authorization, rate limiting, tenancy isolation, or production access-control policy. Do not expose it directly to the public internet. Review [SECURITY.md](SECURITY.md) and [SECURITY_AUDIT.md](SECURITY_AUDIT.md) before enabling capture, replication, external timestamps, or S3 storage.

## Verify the safety boundaries yourself

```bash
# Show the only safe-demo write root.
find demo/data -maxdepth 4 -print

# Confirm Git ignores generated demo material.
git check-ignore -v demo/data/operator-a/keys/observer-private.pem

# Run the audited tests.
python3 -m pytest -q tests/security network-demo/tests
```
