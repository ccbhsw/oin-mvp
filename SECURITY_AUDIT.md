# Security Audit — OIN MVP

**Audit type:** source, configuration, dependency-declaration, Git-history, and runtime-boundary review.
**Reviewed revision:** `bd63d3c` plus the security-hardening changes documented below.
**Scope limitation:** this is an engineering review of the repository available in the audit environment. It is not a formal penetration test, a malware guarantee, a dependency-SBOM attestation, or a claim that future revisions are safe.

> **Conclusion:** No backdoor, reverse shell, credential-harvesting path, telemetry client, hidden upload, `eval`, `exec`, `shell=True`, automatic remote-code execution, or tracked credential matching the scanned patterns was found in the reviewed supported code paths. The audit did identify and fix several concrete hardening gaps: core key-file permissions, private-peer SSRF defaults, unsafe-sized portable ZIP acceptance, default container dependency breadth, and unnecessarily broad Compose port binding. Residual risks remain and are listed below.

## 1. Method and reviewed files

The audit used only static inspection and project test execution; it did not execute historical research scripts or make arbitrary capture requests. Local audit logs were created under `security-audit-work/`, are ignored by Git, and are not part of the project deliverable.

| Area | Files / commands reviewed | Result |
| --- | --- | --- |
| Core Python service | `oin/api/app.py`, `oin/capture/http_capture.py`, `oin/storage/backends.py`, `oin/timestamp/rfc3161.py`, `oin/verifier/offline.py`, `oin/identity/keys.py`, `oin/cli.py` | Reviewed for network, subprocess, environment, filesystem, archive, and signature behavior. |
| Multi-Operator demo | `network-demo/tools/operator.py`, `network-demo/tools/node_verifier.mjs`, `network-demo/tests/test_network_demo.py`, schemas, ignore rules, docs | Reviewed for local-root boundaries, ZIP parsing, process invocation, and network behavior. |
| Examples and historical research | `examples/*.py`, `docs/innovation/**/operator_*.mjs`, `*.sh`, and Node verifier files matching process/network scans | Retained as non-default experiments; external requests and CLI use are documented as residual review surface. |
| Build and runtime configuration | `pyproject.toml`, `requirements-build.in`, `requirements*.lock`, `Dockerfile`, Compose files and ignore rules | Python 3.11 build/runtime/dev resolutions are committed with SHA-256 hashes; Docker installs them before a no-dependency local project install. No GitHub Actions, Node package manager or hidden bootstrap file exists. |
| Git history and repository state | 8 reachable commits, `git grep` secret-pattern scan at every reachable commit, `git fsck --unreachable` blob scan, tracked-path scan, `git check-ignore` probes | No match for scanned token, cloud-key, private-key, Slack, OpenAI-style, or Google API-key patterns. Runtime key/data paths are ignored. |
| Dependency declarations | `pyproject.toml`, `requirements-build.in`, `requirements*.lock`, `pip check`, installed package metadata | Build, runtime and development resolutions are version-pinned and hash-locked for Python 3.11. Vulnerability/SBOM automation remains absent. |

### Static patterns checked

The review searched supported source, examples, and tracked experimental scripts for the following classes of behavior:

- `subprocess`, `Popen`, `os.system`, `os.popen`, `shell=True`, `eval`, `exec`, `compile`, dynamic imports, native-code loading, and unsafe deserialization;
- reads of home, SSH, AWS, browser cookie, wallet, seed, password, token, secret, credential, and environment paths/variables;
- HTTP clients, sockets, S3 clients, `fetch`, upload calls, telemetry/analytics/tracking identifiers, and literal URLs;
- `curl`, `wget`, package installation, `git clone`, `apt-get`, remote download helpers, container `ADD` URLs, privileged containers, host networking, and broad bind mounts;
- Git-history patterns for GitHub PATs, AWS keys, PEM private-key headers, Slack-style tokens, OpenAI-style keys, and Google API keys.

## 2. Dangerous behavior findings

| Finding | Location | Classification | Status |
| --- | --- | --- | --- |
| Fixed-command OpenSSL subprocess for RFC 3161 request generation and verification. | `oin/timestamp/rfc3161.py`, `oin/verifier/offline.py` | Controlled subprocess; argument arrays, `shell=False` default, temporary files only. | Retained and documented. |
| Optional outbound TSA POST. | `obtain_rfc3161_token()` | Caller-directed external network operation. | TSA URL now passes public HTTP(S) validation before use by API capture. |
| Optional S3 client and cloud credential reads. | `oin/storage/backends.py`, `oin/api/app.py` | Explicit optional storage backend; no default activation. | Retained and documented. |
| Replication pull fetched a caller-supplied peer URL. | `oin/api/app.py` | SSRF risk if API is exposed. | Fixed: public peer validation by default; private peers require `OIN_ALLOW_PRIVATE_PEERS=1` plus `OIN_ALLOWED_PRIVATE_PEER_HOSTS`. |
| Portable ZIP import read unbounded member data. | `network-demo/tools/operator.py`, `node_verifier.mjs` | Resource-exhaustion / ZIP-bomb risk. | Fixed: input, member, count, duplicate-name, path, and uncompressed-size limits. |
| Core key writer did not explicitly set private-key permissions. | `oin/identity/keys.py` | Local key disclosure risk on permissive umask/platforms. | Fixed: private PEM receives Unix mode `0600`. |
| Normal Compose published development ports on all interfaces. | `docker-compose.yml` | Accidental LAN exposure. | Fixed: ports now bind to `127.0.0.1`. |
| Default Docker build installed optional S3/Postgres extras. | `Dockerfile` | Unnecessary default dependency breadth. | Fixed: default image installs only core dependency set. |
| Historical experimental scripts run `curl`, `fetch`, `openssl`, `zip` or `unzip`. | `docs/innovation/**` | Non-default research tooling; not part of safe demo. | Retained as evidence; explicitly excluded from supported safe-demo path. |

No `eval`, `exec`, `shell=True`, reverse shell, netcat listener, remote script piping, runtime `curl | sh`, automatic `git clone`, browser-cookie lookup, SSH-key scan, wallet scan, telemetry SDK, analytics SDK, or hidden upload routine was found in supported source paths.

## 3. Network request inventory

No network connection is made merely by importing the Python package, running `oin verify`, running the Node verifier, or running the default `SAFE_DEMO` identity initialization.

| Trigger | Destination | Data sent or received | Default state |
| --- | --- | --- | --- |
| `capture_url`, `oin capture`, `operator.py capture`, or API capture endpoint | Exact public HTTP(S) URL supplied by caller and validated redirects | Outbound HTTP GET. Captured response headers/body are retained locally in WARC/WACZ. No local files are uploaded. | Explicit only. |
| `POST /v1/replication/pull` | Caller-supplied peer URL | GETs replication IDs and portable observation exports; stores only verified copies locally. | Explicit only; private peer blocked unless both opt-in and host allowlist are configured. |
| `POST /v1/observations` or replication push | Local API server receiving caller data | Receives manifest and base64 archive in request body; no automatic forwarding. | Explicit inbound API use. |
| RFC 3161 API `tsa_url` | Caller-supplied validated public TSA | Timestamp query containing the signed manifest’s hash. | Explicit only. |
| Optional S3 backend | `OIN_S3_ENDPOINT_URL` / AWS SDK selected by deployer | Archive bytes and bucket operations. AWS variables are read only when `OIN_STORAGE_BACKEND=s3`. | Disabled by default. |
| Example scripts | User-supplied local node URL or hardcoded historical research URL | Explicit sample HTTP traffic. | Not run by installation, tests, or safe demo. |
| Dependency installation / Docker build | Configured package index / image registry | Dependency and base-image retrieval. | Setup/build action only; not demo runtime. |

The HTTP capture helper rejects non-HTTP(S) schemes, user-info in URLs, unresolved hosts, and DNS answers that are not globally routable. It checks every redirect target before requesting it. This reduces SSRF exposure but does not eliminate DNS rebinding or application-layer proxy risks; operators should retain egress controls.

## 4. Sensitive data and permissions

The reviewed application does not enumerate or read SSH keys, browser profiles, cookie stores, wallet directories, password managers, or home directories. It reads only explicit user-supplied file paths (such as a CLI `--key` or verification bundle), project/runtime data paths, and the named optional S3 environment variables when S3 is deliberately enabled.

| Data / permission | Actual behavior |
| --- | --- |
| Observer private keys | Generated only at a caller-selected output root; written as `observer-private.pem` with mode `0600` on Unix. |
| Existing user private keys | Never discovered automatically. CLI accepts only an explicit `--key` path. |
| Environment variables | API reads explicit `OIN_*` configuration plus `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION` only for opt-in S3. The project does not dump or upload the process environment. |
| Browser / SSH / wallet / cookie data | No discovered code path reads these locations. |
| Local demo writes | `SAFE_DEMO` writes only to `demo/data/`; network-demo runtime data is ignored by Git. |
| Docker safe demo | No root process, no Docker socket, no host home mount, no host network, no privileged mode, no added capabilities, and only `demo/data` is writable. |

## 5. Dependencies

`pyproject.toml` is the human-maintained dependency declaration. `requirements-build.in` and the generated `requirements-build.lock`, `requirements.lock`, and `requirements-dev.lock` record Python 3.11 build, runtime and development resolutions with SHA-256 hashes. There is no Node package manager, Poetry or Pipenv lock file, GitHub Action, or automatic shell installer.

| Dependency | Purpose in supported code | Declared as |
| --- | --- | --- |
| `cryptography` | Ed25519 keys and signatures | Core runtime |
| `fastapi`, `pydantic`, `uvicorn`, `python-multipart` | Local API server and request validation | Core runtime |
| `httpx` | Explicit HTTP capture, replication pull, optional TSA | Core runtime |
| `sqlalchemy` | Local metadata persistence | Core runtime |
| `typer` | CLI | Core runtime |
| `pytest`, `pytest-asyncio`, `ruff` | Test and lint tooling | Development extra |
| `psycopg[binary]`, `boto3` | Optional Postgres and S3 adapters | Opt-in extras |

`python3 -m pip check` reported no broken requirements in the audit environment. The project now has hash-locked build, runtime and development resolutions, but no committed SBOM or automated vulnerability scanner. Therefore the audit does **not** claim a complete CVE assessment of transitive packages; a reviewed offline/CI vulnerability scan remains required before production use.

## 6. Git history and secret result

The scan covered all 8 reachable commits and the 9 unreachable blobs reported by `git fsck` at audit time. It emitted only filenames/object IDs, never secret contents.

- No scanned credential pattern was found in any reachable commit.
- No scanned credential pattern was found in the unreachable blobs.
- No tracked private-key, `.env`, database, timestamp-response, `run-artifacts`, or demo runtime path was found.
- `.gitignore` excludes `data/`, common private-key extensions, `.env*`, database files, user export paths, and local audit logs.
- `network-demo/.gitignore` additionally excludes runtime keys, captures, evidence, manifests, statements, verification records, replication receipts, imports, exports, recovery data, identity JSON, and descriptor JSON while retaining only directory `.gitkeep` files.

This is pattern-based scanning, not proof that every possible secret format is absent. A credential that does not match the scanned patterns, is encrypted, or exists outside reachable Git objects requires separate review.

## 7. Safe container demo

`docker-compose.safe-demo.yml` supplies an isolated default demo. It deliberately uses an already-local image tag `oin-mvp-safe:local` instead of `build:` so that invoking the demo does not automatically download an image or resolve dependencies. It has `network_mode: none`, a read-only root filesystem, `cap_drop: ALL`, `no-new-privileges`, an `noexec,nosuid` temporary filesystem, and only three project-local mounts: read-only `oin/`, read-only `network-demo/`, and writable `demo/data/`.

The current audit environment has no Docker binary, so the configuration was statically reviewed but not executed here. See [SAFE_DEMO.md](SAFE_DEMO.md) for exact behavior and optional explicit build instructions.

## 8. Risks that remain

1. **No authentication or rate limiting on the API.** Running `oin serve` or the normal Compose network where untrusted clients can reach it is unsafe without an external access-control layer.
2. **Capture is a networked web-fetching feature.** Public-IP checks reduce SSRF but cannot fully remove DNS rebinding, proxy, malicious response, bandwidth, parser, or legal-content risks. Keep egress filtering and response-size limits.
3. **Artifacts intentionally preserve web response data.** WARC/WACZ may contain sensitive material if an operator captures sensitive URLs. Use only public, authorized targets and review retention/access policy.
4. **Optional S3, PostgreSQL, TSA, and peer replication create external trust boundaries.** They are disabled by default but require independent endpoint, credential, TLS, authorization, and data-residency review when enabled.
5. **Development-only adapter credentials exist in optional Compose profiles.** They are visible defaults for isolated development, not production credentials.
6. **No SBOM/CVE automation is committed.** Python 3.11 build, runtime and development packages are now version- and hash-locked, but vulnerability intelligence and package provenance must still be reviewed before release.
7. **Historical experiment scripts are executable if manually invoked.** They may contact their declared targets and use installed CLIs. They are not automatically run, but researchers should inspect them before use.
8. **No claim of absolute malware absence.** Static review cannot prove the absence of a future compromise, malicious dependency release, operating-system compromise, or hidden behavior outside reviewed paths.

## 9. Safe-use checklist for strangers

1. Clone, inspect `pyproject.toml`, `SECURITY.md`, this report, and `SAFE_DEMO.md` before installation.
2. Start with the no-network identity initialization in `demo/data/`; do not start the API or execute historical research scripts first.
3. Use a fresh virtual environment or a reviewed local wheelhouse; do not run `pip` as root.
4. Do not provide an existing private key, API key, cloud credential, browser export, wallet, or token to the demo.
5. Keep generated `demo/data/`, `data/`, WARC/WACZ files, and export ZIPs out of Git.
6. Before capture, decide exactly which public URL may be contacted and inspect any redirect behavior.
7. Before enabling API, S3, TSA, or replication, bind services to private/localhost interfaces and add authentication, rate limits, egress policy, and retention controls.
8. Re-run the checks below after updating dependencies or source:

```bash
python3 -m ruff check oin network-demo/tools/operator.py network-demo/tests/test_network_demo.py tests/security
node --check network-demo/tools/node_verifier.mjs
python3 -m pytest -q tests/security network-demo/tests
python3 -m pytest -q tests
```
