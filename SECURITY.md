# Security Policy

## Security posture

OIN MVP is an experimental public-web observation prototype. It is **not** presented as malware-free by assertion, as production-hardened archival infrastructure, or as a substitute for an independently reviewed security program. The repository includes a documented static audit and repeatable tests in [SECURITY_AUDIT.md](SECURITY_AUDIT.md), but every deployment operator remains responsible for its own threat model, review, patching, access control, retention policy, and backup strategy.

Before running any command, read [SAFE_DEMO.md](SAFE_DEMO.md). The default safe demo is deliberately offline and writes only under `demo/data/`. Public-web capture is an explicit, separate action because it makes an outbound HTTP(S) request to a URL chosen by the user.

## Supported scope

The current security review covers the Python MVP, the `network-demo` tools, top-level container configuration, tracked dependency declarations, and the reachable Git history at the reviewed commit. Historical audit experiments under `docs/` are retained as research evidence and are not the supported safe-demo path.

The following areas are particularly relevant for reports:

- SSRF or private-network access through capture, replication, timestamping, or storage configuration;
- unsafe archive import, path traversal, resource exhaustion, signature or hash-binding bypass;
- unintended collection, export, or upload of local files, credentials, browser data, SSH material, wallets, tokens, or environment values;
- unsafe private-key creation, file permissions, or accidental Git inclusion;
- container privilege, host mount, network exposure, or default credential issues;
- dependency, installation, or build-chain compromise.

## Reporting a vulnerability

Do **not** open a public issue containing an exploit, private key, token, captured private data, or proof that could harm a third party. Use GitHub’s private security-advisory reporting flow for this repository, or contact the repository owner privately through the contact method displayed on the repository profile. Include the affected revision, concise reproduction steps, expected and observed behavior, impact, and a safe proof of concept.

A report receives an acknowledgement target of seven calendar days. Remediation timing depends on severity, reproducibility, maintainer availability, and whether a coordinated disclosure is needed. No bounty, service-level agreement, or guaranteed response time is promised by this experimental project.

## Secret handling

Never commit private keys, `.env` files, cloud credentials, browser exports, wallet material, production WARC/WACZ captures, or portable export packages. The repository ignores common key, environment, database, bundle, and demo-runtime paths, but `.gitignore` is a safeguard against accidental new files, not a substitute for pre-commit review.

If a credential is ever committed, treat it as exposed: revoke or rotate it, remove it from current files and reachable history where appropriate, invalidate derived access, and document the remediation without republishing the secret.

## Deployment cautions

The default API has no authentication, authorization, rate limiting, multi-tenant isolation, or legal retention/takedown workflow. Bind it to localhost or a private network unless the operator independently adds these controls. Do not use the development-only Postgres/MinIO credentials in `docker-compose.yml` outside an isolated development environment.

Optional S3 storage, external replication peers, and RFC 3161 timestamping make outbound network connections only when explicitly configured. Review their endpoint, credentials, transport security, access policy, data residency, and retention implications before enabling them.

## Security documents

- [SAFE_DEMO.md](SAFE_DEMO.md): smallest isolated, no-network demonstration path.
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md): reviewed files, observed behavior, fixes, residual risks, and verification commands.
- [network-demo/ARCHITECTURE.md](network-demo/ARCHITECTURE.md): evidence, custody, import, recovery, and trust-boundary model.
