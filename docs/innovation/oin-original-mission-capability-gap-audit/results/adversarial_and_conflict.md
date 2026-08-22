# Malicious Statement, Conflict Retention and Evidence Verification Results

The controlled adversarial publisher was experimental operator B. It used B’s real Ed25519 key; the test never publishes an invalid record outside the isolated local network. The verifier therefore distinguishes **key-valid statement** from **valid capture evidence**.

## Invalid evidence-binding claim

B issued a new detached-signed statement that referenced a real B WACZ but declared a deliberately incorrect package SHA-256. The statement signature verified under B’s public key and the WACZ ZIP/resources themselves remained intact. The verifier marked `signature_valid: true`, `package_valid: true`, `binding_valid: false`, and `valid: false`. It retained the full record and error state rather than silently deleting it or treating the signed statement as a valid historical record.

| Property | Result |
| --- | --- |
| Statement signer key valid | true |
| WACZ package/resources valid | true |
| Statement-to-package evidence digest binding valid | false |
| Overall accepted as valid capture evidence | false |
| Record retained in signed B catalog | true |

This is a **PASS** for evidence validation and preservation of rejected input. It also demonstrates an existing cryptographic distinction: signature authenticity alone does not establish that an evidence reference is correct.

## Same-signer conflicting valid claims

B issued two different, individually valid signed evidence bundles for `https://httpbingo.org/uuid`. Both used one explicit extension claim key, `operator-b-declared-capture-slot-001`, to assert that they describe the same declared capture slot. The first and second records had different real payload and WARC/package digests. The verifier kept both, verified both signatures/bindings and emitted one `same_signer_conflicts` record with B’s issuer ID, the shared target/claim key, both statement IDs and both payload digests.

This is a **PASS** for conflict preservation and same-signer conflicting-claim detection in the standards-only mapping. It is **not** Certificate Transparency or SCITT cryptographic equivocation detection: the test has no transparency-service receipt, signed tree head, consistency proof or gossip witness. The result is limited to conflict detection in signed catalog/evidence material available to the verifier.

## Non-adjudication behavior

The discovery client reports all five UUID-related records: A’s valid capture, B’s ordinary valid capture, B’s invalid-binding record, and B’s two valid conflicting claims. It does not choose a winner, call either payload “true,” make a global content-change claim, or infer malicious organizational intent. It reports only which constraints verify and which two valid claims conflict under B’s own declared claim key.
