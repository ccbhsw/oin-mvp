# OIN Local Network Demo — Test Report

**Report status:** PASS for the defined local mechanism tests.  
**Scope:** a single sandbox with three isolated local Operator roots.  
**This report does not claim:** real independent organizations, independent cloud accounts, geographic redundancy, production durability, legal evidence admissibility, continuous uptime, or public-network decentralization.

## 1. Test environment

| Item | Actual environment |
| --- | --- |
| OS | Ubuntu sandbox on Linux amd64. |
| Python | Python 3.11.0rc1. |
| Node.js | Node.js 22.13.0. |
| Project | `/home/ubuntu/oin-mvp`. |
| Primary implementation | Existing Python OIN MVP plus `network-demo/tools/operator.py`. |
| Independent verifier | `network-demo/tools/node_verifier.mjs`, using Node built-in modules only. |
| Network target | `https://example.com` for successful real public HTTP capture; a deliberately missing path on that host for HTTP 404. |
| Archive format | WARC in WACZ, with `datapackage.json` resource digests. |
| Signature | Ed25519. |
| Integrity | SHA-256 of archive, response payload, manifests and transport files. |

## 2. Classification of evidence

> **LOCAL SIMULATION:** A, B and C use different Ed25519 keys, different directory roots, separate import/export artifacts and different local custody receipts. However, they run under one sandbox, one filesystem and one controlling account.

> **REAL INDEPENDENT OPERATOR:** Not performed. No claim is made that any test involved independent organizations, independent funding, independent legal control, independent locations or unrelated administrators.

| Claim | Status | Basis |
| --- | --- | --- |
| Real public HTTP transaction was captured. | **Performed.** | `https://example.com` returned HTTP 200 during actual runs. |
| Result was stored as WARC/WACZ and checked offline. | **Performed.** | WACZ contained WARC, pages index and `datapackage.json`; Python and Node verifiers returned `VERIFIED`. |
| A/B/C identities and data paths are distinct. | **Performed locally.** | Each test initialized its own directory and Ed25519 keypair. |
| B imported only an A export artifact. | **Performed locally.** | B import accepts an outer ZIP; it does not accept an A root path or private key. |
| A loss can be recovered from B. | **Performed locally.** | A evidence/manifest/statement material was moved out of the active custody path before `recover` imported B export. |
| C can join from a B export. | **Performed locally.** | C initialized a new identity, then imported B export and verified it. |
| Operators are truly independent in the real world. | **Not tested.** | No separate organization, account, server or location was involved. |

## 3. Commands actually run

The following quality and test commands were executed from the project root:

```bash
python3 -m ruff check network-demo/tools/operator.py network-demo/tests/test_network_demo.py
node --check network-demo/tools/node_verifier.mjs
python3 -m pytest -q network-demo/tests
python3 -m pytest -q tests
```

Actual results:

```text
All checks passed!
11 passed in 51.66s
30 passed in 1.52s
```

The 11 tests are the new network-demo suite. The 30 tests are the pre-existing OIN MVP suite. Earlier full-repository `ruff check .` was not accepted as a quality result because legacy one-off audit scripts under historical documentation directories have style violations unrelated to `oin/` core or the new network-demo code; the scoped quality command above passed.

## 4. End-to-end mechanism results

| Scenario | What was actually performed | Expected machine result | Actual result |
| --- | --- | --- | --- |
| A real capture | A fetched `https://example.com`. | HTTP 200 plus locally verified WACZ/manifest. | PASS: `CAPTURED`, `http_status: 200`, then `VERIFIED`. |
| Python offline verification | Bundle only: manifest, WACZ, public key and evidence metadata. | Hash, binding and Ed25519 checks pass without service contact. | PASS: `VERIFIED`. |
| Node offline verification | Node read the Python-produced bundle independently. | Same evidence checks pass. | PASS: `VERIFIED`. |
| A → B replication | A signed portable export; B verified before copy. | `ACCEPTED`, A retained as original issuer. | PASS. |
| B → C replication | B signed a new export; C checked B as exporter and A as original issuer. | `ACCEPTED`, role separation retained. | PASS. |
| Node → Python interoperability | Node generated C-signed transport export; Python B imported it. | `ACCEPTED` and offline-valid retained bundle. | PASS. |
| A evidence-loss recovery | A active evidence/manifest paths were moved aside, then B export restored them. | `RECOVERED`, restored bundle verifies. | PASS. |
| Scope-aware history | A/B declared scope queried with all online, then A marked offline. | `VERIFIED` online; `PARTIAL_SCOPE` plus `UNAVAILABLE_OPERATOR` when A offline. | PASS. |
| No-match query | A declared reachable scope queried for absent target. | `NO_MATCH_IN_DECLARED_SCOPE`. | PASS. |
| Conflict retention | C made a new actual capture of the same target. | Both valid observations retained; `CONFLICT` with no truth verdict. | PASS. |

## 5. Fault and negative-test matrix

| Scenario | Test action | Expected status | Actual result |
| --- | --- | --- | --- |
| Evidence bytes changed | Rewrote `bundle/raw.wacz` in an export without updating digest. | `INVALID_BINDING`; no accepted custody copy. | PASS. |
| Manifest signature changed | Replaced local manifest signature with invalid bytes. | `INVALID_SIGNATURE` in Python and Node offline verifiers. | PASS. |
| Export signature changed | Replaced signed export manifest signature. | `INVALID_SIGNATURE`. | PASS. |
| Descriptor changed | Changed `descriptor_revision` inside export without updating signed digest. | `INVALID_BINDING`. | PASS. |
| Malformed export | Supplied non-ZIP bytes to importer. | `MALFORMED_ARTIFACT`. | PASS. |
| Missing export | Imported nonexistent ZIP path. | `NOT_FOUND`. | PASS. |
| Missing replica | Removed B retained evidence after receipt. | statement `MISSING_REPLICA`; history `PARTIAL_SCOPE`. | PASS. |
| Operator unavailable | Wrote local A offline marker before scoped query. | `UNAVAILABLE_OPERATOR` for A; bounded aggregate status. | PASS. |
| HTTP 404 | Captured an intentionally missing `example.com` path. | Valid capture record with `http_status: 404`. | PASS: `CAPTURED`, `http_status: 404`. |
| Timeout | Used a near-zero capture timeout for a public target. | `TIMEOUT`. | PASS. |
| Divergent statement | C captured same target with distinct signer/artifact. | `CONFLICT`; retain all statements. | PASS. |

## 6. Verification checks actually exercised

A `VERIFIED` offline result required all applicable checks to be true:

```text
archive_hash
raw_content_hash
raw_content_bytes
manifest_id
observer_signature
observer_identity
canonical_url
object_identity
```

Node export verification additionally required:

```text
descriptor_operator
descriptor_public_key
descriptor_key_id
exporter_identity
export_signature
original_issuer
artifact_binding
manifest_binding
observation_binding
descriptor_digest
```

The timestamp result in successful current bundles is `DECLARED_ONLY`: the local signer supplied a timestamp hash binding, but no RFC 3161 third-party timestamp authority was used. This is intentionally not presented as independent proof of capture time.

## 7. Findings and limitations

The test evidence supports a narrow conclusion: the selected standard components can be assembled into a working local multi-Operator evidence mechanism. It supports portable WACZ evidence, original signer preservation, verified import before retention, replica receipts, offline checking, a recovery drill, scope-limited history and non-destructive conflict retention.

The test evidence does **not** support stronger claims. It does not show that a third party trusts the Operator identities, that separate organizations will run nodes, that two remote storage providers will retain artifacts, that HTTP capture represents a browser-rendered page, that a signer is truthful, or that the network can survive loss of the sandbox. It does not implement global discovery, authorization, privacy controls, legal evidence workflows, governance or persistent production hosting.

## 8. Reproduction

Run the complete local test suite:

```bash
cd /home/ubuntu/oin-mvp
python3 -m pytest -q network-demo/tests
```

For a manual chain, follow [README.md](README.md). Architecture and trust boundaries are in [ARCHITECTURE.md](ARCHITECTURE.md).
