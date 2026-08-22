#!/usr/bin/env bash
# Experimental operator C. Uses shell, curl, openssl, zip, and sha256sum only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
OPERATOR_ID="experimental-operator-c"
OP_ROOT="$ROOT/operators/operator-c"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --operator-root) OP_ROOT="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
sha() { sha256sum "$1" | awk '{print $1}'; }
now() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
mkdir -p "$OP_ROOT/keys" "$OP_ROOT/bundles"
if [ ! -f "$OP_ROOT/keys/ed25519-private.pem" ]; then
  openssl genpkey -algorithm Ed25519 -out "$OP_ROOT/keys/ed25519-private.pem" >/dev/null 2>&1
  openssl pkey -in "$OP_ROOT/keys/ed25519-private.pem" -pubout -out "$OP_ROOT/keys/ed25519-public.pem" >/dev/null 2>&1
fi
PUB="$OP_ROOT/keys/ed25519-public.pem"
PRIV="$OP_ROOT/keys/ed25519-private.pem"
PUB_SHA="$(sha "$PUB")"
entries_file="$(mktemp)"
trap 'rm -f "$entries_file"' EXIT
capture() {
  local case_id="$1" url="$2" accept_lang="$3" ua="$4" stamp status tmp body headers reqhttp resphttp warc id bundle build payload_sha warc_sha package_sha stmt
  stamp="$(now)"; tmp="$(mktemp -d)"; body="$tmp/body"; headers="$tmp/headers"
  status="$(curl -sS --connect-timeout 10 --max-time 30 -A "$ua" -H "Accept-Language: $accept_lang" -D "$headers" -o "$body" -w '%{http_code}' "$url" || true)"
  if [ -z "$status" ]; then status=0; fi
  payload_sha="$(sha "$body")"
  id="$(printf '%s|%s|%s' "$case_id" "$stamp" "$payload_sha" | sha256sum | awk '{print substr($1,1,24)}')"
  bundle="$OP_ROOT/bundles/$id"; mkdir -p "$bundle"; warc="$bundle/capture.warc"
  reqhttp="$tmp/request.http"; resphttp="$tmp/response.http"
  printf 'GET %s HTTP/1.1\r\nUser-Agent: %s\r\nAccept-Language: %s\r\n\r\n' "$url" "$ua" "$accept_lang" > "$reqhttp"
  cat "$headers" "$body" > "$resphttp"
  {
    printf 'WARC/1.1\r\nWARC-Type: request\r\nWARC-Target-URI: %s\r\nWARC-Date: %s\r\nWARC-Record-ID: <urn:sha256:%s-request>\r\nContent-Type: application/http; msgtype=request\r\nContent-Length: %s\r\n\r\n' "$url" "$stamp" "$id" "$(wc -c < "$reqhttp")"
    cat "$reqhttp"; printf '\r\n\r\n'
    printf 'WARC/1.1\r\nWARC-Type: response\r\nWARC-Target-URI: %s\r\nWARC-Date: %s\r\nWARC-Record-ID: <urn:sha256:%s-response>\r\nContent-Type: application/http; msgtype=response\r\nWARC-Payload-Digest: sha256:%s\r\nContent-Length: %s\r\n\r\n' "$url" "$stamp" "$id" "$payload_sha" "$(wc -c < "$resphttp")"
    cat "$resphttp"; printf '\r\n\r\n'
  } > "$warc"
  warc_sha="$(sha "$warc")"
  build="$bundle/package-build"; mkdir -p "$build/archive" "$build/indexes"; cp "$warc" "$build/archive/capture.warc"
  printf '{"format":"experimental-wacz-data-package","target":"%s","captured_at":"%s","status":%s,"payload_sha256":"%s","warc_sha256":"%s"}' "$url" "$stamp" "$status" "$payload_sha" "$warc_sha" > "$build/metadata.json"
  printf '%s %s {"url":"%s","timestamp":"%s","status":%s,"digest":"%s","filename":"archive/capture.warc"}\n' "$url" "${stamp//[-:TZ]/}" "$url" "$stamp" "$status" "$payload_sha" > "$build/indexes/index.cdxj"
  printf '{"profile":"data-package","resources":[{"path":"archive/capture.warc","bytes":%s,"hash":"sha256:%s"},{"path":"indexes/index.cdxj","bytes":%s,"hash":"sha256:%s"},{"path":"metadata.json","bytes":%s,"hash":"sha256:%s"}]}' "$(wc -c < "$build/archive/capture.warc")" "$(sha "$build/archive/capture.warc")" "$(wc -c < "$build/indexes/index.cdxj")" "$(sha "$build/indexes/index.cdxj")" "$(wc -c < "$build/metadata.json")" "$(sha "$build/metadata.json")" > "$build/datapackage.json"
  (cd "$build" && zip -q -0 -X "$bundle/evidence.wacz" datapackage.json metadata.json archive/capture.warc indexes/index.cdxj)
  rm -rf "$build" "$warc"; package_sha="$(sha "$bundle/evidence.wacz")"
  stmt="$bundle/statement.json"
  printf '{"@context":["https://www.w3.org/ns/credentials/v2","https://www.w3.org/ns/prov#"],"type":["VerifiableCredential","CaptureEvidenceStatement"],"id":"urn:sha256:%s","issuer":{"id":"%s","publicKeySha256":"%s"},"validFrom":"%s","credentialSubject":{"id":"%s","capture":{"activity":"http-get","requestHeaders":{"Accept-Language":"%s","User-Agent":"%s"},"responseStatus":%s,"responsePayloadSha256":"%s","transportError":null},"evidence":{"format":"WARC-1.1-in-WACZ-ZIP","file":"evidence.wacz","sha256":"%s","warcSha256":"%s","location":"/bundles/%s/"}}}' "$id" "$OPERATOR_ID" "$PUB_SHA" "$stamp" "$url" "$accept_lang" "$ua" "$status" "$payload_sha" "$package_sha" "$warc_sha" "$id" > "$stmt"
  openssl pkeyutl -sign -rawin -inkey "$PRIV" -in "$stmt" -out "$bundle/statement.sig" >/dev/null 2>&1
  cp "$PUB" "$bundle/signer-public.pem"
  printf '{"statement_id":"%s","kind":"local-capture","target":"%s","case_id":"%s","issuer":"%s","captured_at":"%s","bundle":"/bundles/%s/","statement_sha256":"%s","evidence_sha256":"%s","payload_sha256":"%s","status":%s,"public_key_sha256":"%s"}' "$id" "$url" "$case_id" "$OPERATOR_ID" "$stamp" "$id" "$(sha "$stmt")" "$package_sha" "$payload_sha" "$status" "$PUB_SHA" >> "$entries_file"
  printf '\n' >> "$entries_file"; rm -rf "$tmp"
}
# C joins later and independently captures a canonical-source case and an egress-boundary case.
capture "T04-canonical" "https://en.wikipedia.org/wiki/Saturn" "en-US,en;q=0.9" "MissionNetworkOperatorC/1.0"
capture "T09-cdn-geo" "https://httpbingo.org/ip" "en-US,en;q=0.9" "MissionNetworkOperatorC/1.0"
entries="$(paste -sd, "$entries_file")"
cat > "$OP_ROOT/catalog.json" <<EOF
{"catalog_type":"signed-static-web-capture-catalog","operator":{"id":"$OPERATOR_ID","publicKeySha256":"$PUB_SHA"},"generated_at":"$(now)","scope":{"kind":"local-and-explicit-imports","completeness":"complete-for-this-directory-at-generation"},"entries":[$entries]}
EOF
openssl pkeyutl -sign -rawin -inkey "$PRIV" -in "$OP_ROOT/catalog.json" -out "$OP_ROOT/catalog.sig" >/dev/null 2>&1
cp "$PUB" "$OP_ROOT/catalog-public.pem"
printf '{"operator":"%s","entries":%s,"catalog_sha256":"%s"}\n' "$OPERATOR_ID" "$(wc -l < "$entries_file")" "$(sha "$OP_ROOT/catalog.json")"
