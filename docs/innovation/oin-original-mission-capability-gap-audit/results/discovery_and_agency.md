# Cross-Operator Discovery, Verification and Agency Results

Three independently started local HTTP services served three separately generated catalogs and evidence stores. A third-party verifier started only with `peers.json`, queried every listed endpoint directly, verified each catalog’s Ed25519 signature, then verified the matching signed statement, signer key binding, WACZ ZIP/resources and package digest.

| Target | Valid evidence matches | Operators returned | Distinct valid payload digests | Result |
| --- | ---: | --- | ---: | --- |
| `https://example.com/` before import | 2 | A, B | 1 | PASS: two separate signed capture records are discoverable and valid. |
| `https://example.com/` after B→A import | 3 | A local, A import of B, B local | 1 | PASS: foreign original is discoverable at a replica without agency rewrite. |
| `https://httpbingo.org/uuid` | 2 | A, B | 2 | PASS: distinct real responses remain separate valid records. |
| redirect target | 2 | A, B | 2 | PASS: both response records are retained; no verifier target merge occurred. |
| request-header target | 2 | A, B | 2 | PASS: different request contexts and response bytes are preserved. |
| query alpha / beta | 1 / 1 | A / B | 1 / 1 | PASS: distinct query targets remain separately discoverable. |
| HTTP 503 target | 1 | B | 1 | PASS: captured server failure is discoverable as evidence; it is not declared history absence. |

## Agency-preserving import

A downloaded B’s exact `statement.json`, detached signature, signer public key and `evidence.wacz`; verified B catalog signature, B statement signature, B issuer key fingerprint, package digest and WACZ resources before copy; and recorded a local import entry. The copied bundle stayed byte-identical to B’s source and its signed issuer remained `experimental-operator-b`. A signed A catalog now says only that A imported B’s statement. The external verifier found three valid `example.com` records: A local capture, B’s local source, and A’s replica of B’s original. No imported field rewrites B’s issuer/capture identity as A.

| Check | Actual result |
| --- | --- |
| B statement valid before copy | `true` |
| B issuer preserved in copied statement | `true` |
| copied WACZ SHA-256 | `36d9d5f7b2363a91e2c5e08262a3ca9e8409f0f0c69aee134b2a4d0ceaae59b3` |
| A catalog signature after import | valid |
| external lookup of A replica | valid under B signer key |

This result demonstrates technical agency preservation in an isolated three-environment test. It does not prove that A and B are real-world independent operators.
