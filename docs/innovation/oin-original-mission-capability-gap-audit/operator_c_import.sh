#!/usr/bin/env bash
# Import a foreign signed bundle into experimental operator C without rewriting foreign issuer fields.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; OP_ROOT="$ROOT/operators/operator-c"; BASE=""; SID=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --foreign-base) BASE="$2"; shift 2 ;;
    --statement-id) SID="$2"; shift 2 ;;
    --operator-root) OP_ROOT="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$BASE" ] && [ -n "$SID" ]
sha_file() { sha256sum "$1" | awk '{print $1}'; }
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
curl -fsS "$BASE/catalog.json" -o "$tmp/catalog.json"; curl -fsS "$BASE/catalog.sig" -o "$tmp/catalog.sig"; curl -fsS "$BASE/catalog-public.pem" -o "$tmp/catalog-public.pem"
openssl pkeyutl -verify -rawin -pubin -inkey "$tmp/catalog-public.pem" -in "$tmp/catalog.json" -sigfile "$tmp/catalog.sig" >/dev/null
# The statement id is supplied by a verified discovery response, not inferred by a central service.
foreign_issuer="experimental-operator-b"; dest="$OP_ROOT/foreign/$foreign_issuer/$SID"; mkdir -p "$dest"
for f in statement.json statement.sig signer-public.pem evidence.wacz; do curl -fsS "$BASE/bundles/$SID/$f" -o "$dest/$f"; done
openssl pkeyutl -verify -rawin -pubin -inkey "$dest/signer-public.pem" -in "$dest/statement.json" -sigfile "$dest/statement.sig" >/dev/null
unzip -tqq "$dest/evidence.wacz"
package_sha="$(sha_file "$dest/evidence.wacz")"; statement_sha="$(sha_file "$dest/statement.json")"; signer_sha="$(sha_file "$dest/signer-public.pem")"
# Verify the evidence hash text that is cryptographically protected by the foreign statement.
grep -q "\"sha256\":\"$package_sha\"" "$dest/statement.json"
grep -q "\"publicKeySha256\":\"$signer_sha\"" "$dest/statement.json"
url="$(perl -MJSON::PP -0777 -e '$x=decode_json(<>); print $x->{credentialSubject}{id}' "$dest/statement.json")"; captured="$(sed -n 's/.*"validFrom":"\([^"]*\)".*/\1/p' "$dest/statement.json")"; payload="$(sed -n 's/.*"responsePayloadSha256":"\([^"]*\)".*/\1/p' "$dest/statement.json")"; status="$(sed -n 's/.*"responseStatus":\([0-9]*\).*/\1/p' "$dest/statement.json")"
[ -n "$url" ] && [ -n "$captured" ] && [ -n "$payload" ] && [ -n "$status" ]
entry="{\"statement_id\":\"$SID\",\"kind\":\"import\",\"target\":\"$url\",\"issuer\":\"$foreign_issuer\",\"captured_at\":\"$captured\",\"bundle\":\"/foreign/$foreign_issuer/$SID/\",\"statement_sha256\":\"$statement_sha\",\"evidence_sha256\":\"$package_sha\",\"payload_sha256\":\"$payload\",\"status\":$status,\"public_key_sha256\":\"$signer_sha\",\"imported_by\":\"experimental-operator-c\",\"imported_from\":\"$BASE\"}"
old="$OP_ROOT/catalog.json"; prefix="$(sed 's/]}$//' "$old")"; printf '%s,%s]}' "$prefix" "$entry" > "$old"
openssl pkeyutl -sign -rawin -inkey "$OP_ROOT/keys/ed25519-private.pem" -in "$old" -out "$OP_ROOT/catalog.sig" >/dev/null 2>&1
printf '{"importer":"experimental-operator-c","foreign_issuer":"%s","statement_id":"%s","issuer_preserved":true,"package_sha256":"%s"}\n' "$foreign_issuer" "$SID" "$package_sha"
