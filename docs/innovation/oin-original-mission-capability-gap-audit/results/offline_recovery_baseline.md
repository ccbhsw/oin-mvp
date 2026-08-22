# Offline, Recovery and Cross-Implementation Results

## B offline while A/C continue

B’s independent static service was stopped. The discovery client still queried all three declared peer endpoints. A and C catalogs remained valid and their existing local/imported evidence was still verifiable. The B peer report became invalid due to fetch failure; it did not become a history-absence claim. The third-party `example.com` query returned three valid retained records (A local, A’s retained B import, C’s retained B import). This is a **PASS** for continued operation of surviving stores and imported replicas, with declared peer-set scope.

## B recovery and Node import of C evidence

B was restarted with its own original storage. Node operator B then used C’s static public catalog to find C’s actual canonical-source capture, verified C’s catalog, Ed25519 statement, signer binding, WACZ ZIP/resource digests and package digest, then copied the original C bundle into B’s separate foreign store. B’s signed local catalog recorded itself as importer while the original signed issuer remained `experimental-operator-c`.

| Check | Result |
| --- | --- |
| B recovery endpoint | reachable on its original independent port. |
| Node B verified C source before copy | PASS. |
| C issuer retained after B import | `true`. |
| Imported C WACZ SHA-256 | `06c60d9443805ea893f219eeab84a44746a5d89583bb8bc9e612cad6451240cb`. |
| Canonical target valid results while C online | 3 (C source, B import, plus any retained evidence). |

## C endpoint withdrawal

C’s static endpoint was stopped. The third-party canonical-target discovery output recorded C catalog fetch failure but retained two valid results from A/B reachable sources, including B’s independently verified imported C bundle. No central catalog/database supplied those results. C endpoint was restarted only after recording this failure mode.

This establishes endpoint outage tolerance and recovery. The following stronger step will separately test temporary removal of C’s storage directory and of its catalog/index files. Results do not claim resilience against loss of every copy.

## C operator storage and index removal

For the stronger disappearance test, C’s service was stopped and its whole directory—catalog, signature, public key, local WACZ bundles and index—was moved out of the served path. The discovery client then queried the unchanged three-peer descriptor. C produced a failed peer report, while A and B catalogs were still independently valid. The canonical target returned two valid results: an A-side retained result and B’s imported C bundle, whose foreign issuer remained C. C’s directory was then restored unchanged and a new C static service was started; the same query again returned three valid results.

| State | Valid canonical-target results | Valid source catalogs | Interpretation |
| --- | ---: | ---: | --- |
| C live before removal | 3 | A, B, C | C source and replicas are discoverable. |
| C service + directory absent | 2 | A, B | C’s own endpoint is unavailable; preserved copies remain verifiable from surviving operator stores. |
| C directory restored | 3 | A, B, C | Original endpoint recovery adds its source back without changing replicas. |

This is a PASS for the requested single-operator and single-index disappearance scenario within the experimental peer set. It does not establish durability if all copies of a foreign bundle disappear simultaneously, nor Internet-wide discovery beyond the declared peer descriptor.
