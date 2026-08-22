# Standards-Only Experimental Public Web History Network — 架构 v0.1

## 1. 实验网络声明

本网络由三个**隔离 experimental operator environments**组成：`operator-a`、`operator-b` 与 `operator-c`。它们是同一沙箱中为测试建立的独立技术环境，具有独立密钥、目录、进程、HTTP endpoint、Git object database 和 catalog；它们不被宣称为现实世界彼此独立的组织或网络出口。

网络不使用 OIN 源码、schema、术语、端点或私有 protocol。每个 operator 独立产生和保存真实公开 URL 的 HTTP capture evidence、WARC、WACZ、request/response metadata、capture time、digest、signer verification material、PROV-like provenance graph、local catalog 与可复制 object bundle。

## 2. Operator 与工具链

| Operator | Runtime / public implementation | 独立根目录 | Key / signer | Local endpoint | 角色 |
| --- | --- | --- | --- | --- | --- |
| A | Python 3 standard library + `cryptography` + `zipfile` | `operators/operator-a/` | A Ed25519 keypair | `127.0.0.1:8801` | Captures, signs, catalogs, verifies/imports. |
| B | Node.js built-in `fetch`, `crypto`, `child_process` + `zip` CLI | `operators/operator-b/` | B Ed25519 keypair | `127.0.0.1:8802` | Captures, signs, catalogs, verifies/imports. |
| C | POSIX shell + `curl`/`wget`, `openssl`, `zip`, `sha256sum`, `git` | `operators/operator-c/` | C Ed25519 keypair | `127.0.0.1:8803` | Joins later, creates one capture with a third public toolchain, verifies/imports. |

No operator imports another operator’s source code. Shared information can travel only as an exported evidence bundle, a public verification key, a signed catalog record, a peer descriptor or a Git/object transfer recorded in the experiment log.

## 3. Evidence bundle

Each captured target is emitted as a standalone `application/zip` WACZ-style package. The package contains a WARC 1.1 file, `datapackage.json` resource inventory, `indexes/index.cdxj`, request/response metadata, and a manifest of SHA-256 digests. The WARC stores the actual HTTP request/response exchange; package-level and payload-level digest are never substituted for one another.

Each package is accompanied by a detached, signed statement and signer verification material. The statement is a generic standards-extension mapping—not a new wire protocol—with existing public concepts only:

| File | Existing basis | Required information |
| --- | --- | --- |
| `evidence.wacz` | WARC 1.1 + WACZ/ZIP data package | Capture bytes, request/response, WARC records, package resource fixity. |
| `statement.json` | VC 2.0 / PROV-style JSON-LD extension carrier | `issuer`, capture `activity`, `entity` artifact URL/digest, request URI/context, response digest/status, time, archive location, import provenance when applicable. |
| `statement.sig` | Detached Ed25519 signature (RFC 8032 primitive) over canonical UTF-8 JSON bytes | Cryptographic signer binding. |
| `signer-public.pem` / `signer-public.jwk` | Ed25519 public verification material | Public verifier key. |
| `catalog.json` + `catalog.sig` | Signed static collection metadata | Local inventory of the operator’s own and imported evidence entries. |
| `peers.json` | Static peer descriptor | Multiple independently hosted catalog URLs and public keys; no designated central authority. |

The JSON is deliberately minimal and is documented as a mapping over VC/PROV concepts. It does not claim a new standard. The detached signature permits all three runtimes to interoperate with no shared code. A verifier checks: signature; signed statement digest; package digest; WARC record/payload digest; signer key; and catalog inclusion. A valid signature proves key control over the statement, **not** Web server non-repudiation, social/operator independence, or truth of page content.

## 4. Discovery without central index

Each operator serves its own static `catalog.json`, signature, public key and evidence bundles. Every operator’s local `peers.json` lists at least two peer catalog endpoints plus their verification material fingerprint. A third-party discovery client starts from a peer descriptor obtained from any surviving operator, queries every listed peer directly, validates the catalog signature, filters entries by exact target URI, and reports the operator, capture time, artifact location, digest, verification state and multiple distinct evidence bundles.

This is **multi-source discovery**, not a global DHT or global registry. A bootstrap peer descriptor is still required; the experiment tests whether its copying among operators prevents one removed catalog from becoming a single point of discovery failure. No result will claim Internet-wide discovery completeness.

## 5. Replication and agency-preserving import

An importing operator downloads a foreign `evidence.wacz`, `statement.json`, `statement.sig` and signer public key, then verifies all bytes locally before copying them to `foreign/<issuer>/<statement-id>/`. The importer adds a new local catalog record of `kind: "import"` that references the foreign statement ID, foreign issuer/key fingerprint and verified artifact digest. It does not re-sign or replace the foreign `issuer`, capture activity, capture time or evidence digest.

Git is used only as a public replication/transfer substrate: each operator owns a separate bare Git repository and can fetch an exported bundle/object from another operator. Git commit identity is not treated as capture identity; the signed evidence statement remains the source of agency.

## 6. Offline, disappearance and recovery tests

Offline is simulated by stopping B’s static HTTP service and making B’s endpoint unavailable, while A/C retain their own stores and any previously imported B evidence. A/C discovery must still return their locally served catalogs; it may return cached/imported B evidence with its original issuer. B recovery means restarting its independently owned service, comparing catalogs and importing items it lacks.

Index disappearance is simulated by stopping or withdrawing one catalog service. Operator disappearance is simulated by disabling one endpoint and withholding its active store. The test passes only if remaining operator catalog copies and imported bundles continue to verify without a central database. It does not prove long-term availability against simultaneous disappearance of every replica.

## 7. Malicious and conflict tests

The test includes two non-destructive attack inputs created solely by an experimental operator: (a) a statement whose signed digest does not match the package; (b) two validly signed statements from the same key for the same target/time window whose payload-digest claims conflict. Verifiers must reject (a) as invalid, retain both records for (b), identify the same signer/key and flag a `conflicting-claims-by-same-signer` condition. This is catalog-level conflict evidence, not a claim of CT/SCITT log equivocation unless the test includes actual signed tree-head/receipt proofs.

## 8. Capability limits fixed in advance

| Requested capability | Experimental status | Boundary |
| --- | --- | --- |
| three independent organizations/networks | Not claimed | Three isolated technical environments share one sandbox host and one external egress. |
| genuine CDN/geographic difference | `UNAVAILABLE_IN_THIS_ENVIRONMENT` unless independently witnessed public evidence is acquired | A common sandbox egress cannot manufacture geography variation. |
| Web server non-repudiation | Not available | WACZ Auth itself notes HTTP/S does not give archive creator proof of Web-server delivery. |
| Internet-wide discovery/history completeness | Not claimed | Static peer descriptor has declared, copied scope only. |
| CT/SCITT cryptographic equivocation detection | Not available without actual receipt/tree-head pair | Catalog conflicts must not be misnamed as log equivocation. |

## 9. Anticipated falsification logic

If the network passes discovery, verification, replication/import, original-agency preservation, offline recovery, conflict retention, operator/index disappearance, new join and three-toolchain interoperability using only the stack above, it falsifies the claim that a distinct OIN-specific network protocol is necessary to produce a working public Web observation network. Any remaining failure must be tested against the capability-limit table before being called a technical gap.
