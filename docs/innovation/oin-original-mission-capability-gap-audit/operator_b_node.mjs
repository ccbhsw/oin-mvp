#!/usr/bin/env node
/* Experimental operator B. Uses Node built-ins and the zip CLI only. */
import { createHash, generateKeyPairSync, sign, createPrivateKey, createPublicKey } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync, existsSync, rmSync, copyFileSync, unlinkSync } from 'node:fs';
import { join, resolve } from 'node:path';

const ROOT = resolve(new URL('.', import.meta.url).pathname);
const OPERATOR_ID = 'experimental-operator-b';
const args = process.argv.slice(2);
function option(name, fallback) { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : fallback; }
function digest(bytes) { return createHash('sha256').update(bytes).digest('hex'); }
function now() { return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'); }
function canonical(value) { return Buffer.from(JSON.stringify(value, Object.keys(value).sort(), 0)); }
function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(k => [k, stable(value[k])]));
  return value;
}
function jsonBytes(value) { return Buffer.from(JSON.stringify(stable(value))); }
function writeJson(path, value) { const bytes = jsonBytes(value); writeFileSync(path, bytes); return bytes; }
function pemKeys(keysDir) {
  const priv = join(keysDir, 'ed25519-private.pem');
  const pub = join(keysDir, 'ed25519-public.pem');
  if (!existsSync(priv)) {
    const pair = generateKeyPairSync('ed25519');
    writeFileSync(priv, pair.privateKey.export({ type: 'pkcs8', format: 'pem' }));
    writeFileSync(pub, pair.publicKey.export({ type: 'spki', format: 'pem' }));
  }
  return { privateKey: createPrivateKey(readFileSync(priv)), publicPem: readFileSync(pub) };
}
function warcRecord(kind, url, contentType, content, stamp, extra = {}) {
  const fields = [
    'WARC/1.1', `WARC-Type: ${kind}`, `WARC-Target-URI: ${url}`, `WARC-Date: ${stamp}`,
    `WARC-Record-ID: <urn:uuid:${crypto.randomUUID()}>`, `Content-Type: ${contentType}`,
    `Content-Length: ${Buffer.byteLength(content)}`, ...Object.entries(extra).map(([k, v]) => `${k}: ${v}`)
  ];
  return Buffer.concat([Buffer.from(fields.join('\r\n') + '\r\n\r\n'), Buffer.from(content), Buffer.from('\r\n\r\n')]);
}
async function get(url, headers) {
  try {
    const response = await fetch(url, { headers, redirect: 'manual', signal: AbortSignal.timeout(30000) });
    const output = [];
    for (const [k, v] of response.headers.entries()) output.push([k, v]);
    return { status: response.status, reason: response.statusText, headers: output, body: Buffer.from(await response.arrayBuffer()), transportError: null };
  } catch (err) { return { status: 0, reason: 'TRANSPORT_ERROR', headers: [], body: Buffer.from(String(err)), transportError: String(err) }; }
}
function responseMessage(result) {
  const selected = result.headers.filter(([k]) => !['content-length', 'transfer-encoding'].includes(k.toLowerCase()));
  const prefix = `HTTP/1.1 ${result.status} ${result.reason}\r\n${selected.map(([k, v]) => `${k}: ${v}\r\n`).join('')}Content-Length: ${result.body.length}\r\n\r\n`;
  return Buffer.concat([Buffer.from(prefix), result.body]);
}
function packageWacz(bundle, target, capture, warc) {
  const build = join(bundle, 'package-build'); rmSync(build, { recursive: true, force: true });
  mkdirSync(join(build, 'archive'), { recursive: true }); mkdirSync(join(build, 'indexes'), { recursive: true });
  copyFileSync(warc, join(build, 'archive', 'capture.warc'));
  const index = { url: target.url, timestamp: capture.captured_at, status: capture.status, digest: capture.payload_sha256, filename: 'archive/capture.warc' };
  writeFileSync(join(build, 'indexes', 'index.cdxj'), `${target.url} ${capture.captured_at.replaceAll('-', '').replaceAll(':', '').replace('T', '').replace('Z', '')} ${JSON.stringify(index)}\n`);
  writeJson(join(build, 'metadata.json'), { format: 'experimental-wacz-data-package', target: target.url, capture });
  const resources = ['archive/capture.warc', 'indexes/index.cdxj', 'metadata.json'].map(path => { const raw = readFileSync(join(build, path)); return { path, bytes: raw.length, hash: `sha256:${digest(raw)}` }; });
  writeJson(join(build, 'datapackage.json'), { profile: 'data-package', resources });
  const outfile = join(bundle, 'evidence.wacz');
  execFileSync('zip', ['-q', '-0', '-X', outfile, 'datapackage.json', 'metadata.json', 'archive/capture.warc', 'indexes/index.cdxj'], { cwd: build });
  rmSync(build, { recursive: true, force: true });
  return outfile;
}
async function capture(root, privateKey, publicPem, target, languageAlternate) {
  const headers = { ...(languageAlternate ? target.alternate_request_headers : target.request_headers), 'User-Agent': languageAlternate ? 'MissionNetworkOperatorB/1.0' : 'MissionNetworkOperatorB/1.0' };
  const stamp = now(); const res = await get(target.url, headers); const id = digest(Buffer.from(`${target.case_id}|${stamp}|${digest(res.body)}`)).slice(0, 24);
  const bundle = join(root, 'bundles', id); mkdirSync(bundle, { recursive: true });
  const request = `GET ${target.url} HTTP/1.1\r\n${Object.entries(headers).map(([k, v]) => `${k}: ${v}\r\n`).join('')}\r\n`;
  const warc = join(bundle, 'capture.warc');
  const warcBytes = Buffer.concat([
    warcRecord('request', target.url, 'application/http; msgtype=request', request, stamp),
    warcRecord('response', target.url, 'application/http; msgtype=response', responseMessage(res), stamp, { 'WARC-Payload-Digest': `sha256:${digest(res.body)}` })
  ]);
  writeFileSync(warc, warcBytes);
  const captureData = { captured_at: stamp, status: res.status, reason: res.reason, request_headers: headers, response_headers: res.headers, payload_sha256: digest(res.body), warc_sha256: digest(warcBytes), transport_error: res.transportError };
  const wacz = packageWacz(bundle, target, captureData, warc); const packageDigest = digest(readFileSync(wacz));
  const statement = {
    '@context': ['https://www.w3.org/ns/credentials/v2', 'https://www.w3.org/ns/prov#'], type: ['VerifiableCredential', 'CaptureEvidenceStatement'], id: `urn:sha256:${id}`,
    issuer: { id: OPERATOR_ID, publicKeySha256: digest(publicPem) }, validFrom: stamp,
    credentialSubject: { id: target.url, capture: { activity: 'http-get', requestHeaders: headers, responseStatus: res.status, responsePayloadSha256: captureData.payload_sha256, transportError: res.transportError }, evidence: { format: 'WARC-1.1-in-WACZ-ZIP', file: 'evidence.wacz', sha256: packageDigest, warcSha256: captureData.warc_sha256, location: `/bundles/${id}/` } }
  };
  const statementBytes = writeJson(join(bundle, 'statement.json'), statement);
  writeFileSync(join(bundle, 'statement.sig'), sign(null, statementBytes, privateKey)); writeFileSync(join(bundle, 'signer-public.pem'), publicPem); unlinkSync(warc);
  return { statement_id: id, kind: 'local-capture', target: target.url, case_id: target.case_id, issuer: OPERATOR_ID, captured_at: stamp, bundle: `/bundles/${id}/`, statement_sha256: digest(statementBytes), evidence_sha256: packageDigest, payload_sha256: captureData.payload_sha256, status: res.status, public_key_sha256: digest(publicPem) };
}
async function main() {
  const targetsPath = resolve(option('--targets', join(ROOT, 'targets.json'))); const root = resolve(option('--operator-root', join(ROOT, 'operators', 'operator-b')));
  const cases = option('--cases', 'T01-unchanged,T02-changed,T03-redirect,T05-language-header-variation,T07-query-variation-beta,T08-http-failure').split(',');
  mkdirSync(join(root, 'keys'), { recursive: true }); const { privateKey, publicPem } = pemKeys(join(root, 'keys'));
  const targets = JSON.parse(readFileSync(targetsPath)).targets.filter(x => cases.includes(x.case_id)); const entries = [];
  for (const target of targets) entries.push(await capture(root, privateKey, publicPem, target, target.case_id === 'T05-language-header-variation'));
  const catalog = { catalog_type: 'signed-static-web-capture-catalog', operator: { id: OPERATOR_ID, publicKeySha256: digest(publicPem) }, generated_at: now(), scope: { kind: 'local-and-explicit-imports', completeness: 'complete-for-this-directory-at-generation' }, entries };
  const catBytes = writeJson(join(root, 'catalog.json'), catalog); writeFileSync(join(root, 'catalog.sig'), sign(null, catBytes, privateKey)); writeFileSync(join(root, 'catalog-public.pem'), publicPem);
  console.log(JSON.stringify({ operator: OPERATOR_ID, entries: entries.length, catalog_sha256: digest(catBytes) }));
}
main().catch(err => { console.error(err); process.exit(1); });
