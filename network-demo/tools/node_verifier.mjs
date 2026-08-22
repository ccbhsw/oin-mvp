#!/usr/bin/env node
/**
 * Independent Node.js verifier for OIN local network-demo artifacts.
 *
 * This file intentionally does not import Python code or the `oin` package. It
 * independently implements ZIP/WACZ reads, WARC payload extraction, canonical
 * JSON serialization, SHA-256 identifiers, Ed25519 verification and export
 * signer binding using only Node.js built-in modules.
 */

import { createHash, createPrivateKey, createPublicKey, sign as signPayload, verify as verifySignature } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { inflateRawSync } from 'node:zlib';

const MAX_ZIP_INPUT_BYTES = 32 * 1024 * 1024;
const MAX_ZIP_MEMBERS = 16;
const MAX_ZIP_MEMBER_BYTES = 16 * 1024 * 1024;
const MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES = 32 * 1024 * 1024;

function sha256Prefixed(bytes) {
  return `sha256:${createHash('sha256').update(bytes).digest('hex')}`;
}

function sha256Hex(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  }
  return value;
}

function canonicalJson(value) {
  return Buffer.from(JSON.stringify(stable(value)), 'utf8');
}

function withoutSignature(manifest) {
  const clone = structuredClone(manifest);
  delete clone.signature;
  return clone;
}

function withoutObservationIdentity(manifest) {
  const clone = withoutSignature(manifest);
  delete clone.observation_id;
  return clone;
}

function rawEd25519PublicKey(raw) {
  if (!Buffer.isBuffer(raw) || raw.length !== 32) throw new Error('Ed25519 raw public key must be 32 bytes');
  const spkiPrefix = Buffer.from('302a300506032b6570032100', 'hex');
  return createPublicKey({ key: Buffer.concat([spkiPrefix, raw]), format: 'der', type: 'spki' });
}

function verifyEd25519(publicKeyBase64, payload, signatureBase64) {
  try {
    const raw = Buffer.from(publicKeyBase64, 'base64');
    const signature = Buffer.from(signatureBase64, 'base64');
    return verifySignature(null, canonicalJson(payload), rawEd25519PublicKey(raw), signature);
  } catch {
    return false;
  }
}

function observerId(publicKeyBase64) {
  return `oin:observer:sha256:${sha256Hex(Buffer.from(publicKeyBase64, 'base64'))}`;
}

function canonicalizeUrl(value) {
  const url = new URL(value);
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('only HTTP(S) URLs are supported');
  url.protocol = url.protocol.toLowerCase();
  url.hostname = url.hostname.toLowerCase();
  if ((url.protocol === 'https:' && url.port === '443') || (url.protocol === 'http:' && url.port === '80')) url.port = '';
  if (!url.pathname) url.pathname = '/';
  if (url.pathname !== '/' && url.pathname.endsWith('/')) url.pathname = url.pathname.slice(0, -1);
  const pairs = [...url.searchParams.entries()]
    .filter(([key]) => !/^(utm_|fbclid|gclid)/i.test(key))
    .sort(([firstKey, firstValue], [secondKey, secondValue]) => (firstKey === secondKey ? firstValue.localeCompare(secondValue) : firstKey.localeCompare(secondKey)));
  const encode = (text) => encodeURIComponent(text).replace(/%20/g, '+');
  url.search = pairs.length ? `?${pairs.map(([key, item]) => `${encode(key)}=${encode(item)}`).join('&')}` : '';
  url.hash = '';
  return url.toString();
}

function objectId(canonicalUrl, resourceType) {
  return `oin:object:sha256:${sha256Hex(canonicalJson({ canonical_url: canonicalUrl, protocol: 'oin/0.1', resource_type: resourceType }))}`;
}

function observationId(manifest) {
  return `oin:observation:sha256:${sha256Hex(canonicalJson(withoutObservationIdentity(manifest)))}`;
}

class ZipArchive {
  constructor(bytes) {
    if (bytes.length > MAX_ZIP_INPUT_BYTES) throw new Error('ZIP input exceeds safe size limit');
    this.bytes = bytes;
    this.entries = new Map();
    this.parseCentralDirectory();
  }

  parseCentralDirectory() {
    const signature = 0x06054b50;
    const start = Math.max(0, this.bytes.length - 65557);
    let end = -1;
    for (let offset = this.bytes.length - 22; offset >= start; offset -= 1) {
      if (this.bytes.readUInt32LE(offset) === signature) {
        end = offset;
        break;
      }
    }
    if (end < 0) throw new Error('ZIP end of central directory not found');
    const entries = this.bytes.readUInt16LE(end + 10);
    if (entries > MAX_ZIP_MEMBERS) throw new Error('ZIP has too many members');
    const centralOffset = this.bytes.readUInt32LE(end + 16);
    let cursor = centralOffset;
    let totalUncompressedSize = 0;
    for (let index = 0; index < entries; index += 1) {
      if (cursor + 46 > this.bytes.length || this.bytes.readUInt32LE(cursor) !== 0x02014b50) throw new Error('ZIP central directory is malformed');
      const compression = this.bytes.readUInt16LE(cursor + 10);
      const compressedSize = this.bytes.readUInt32LE(cursor + 20);
      const uncompressedSize = this.bytes.readUInt32LE(cursor + 24);
      const nameLength = this.bytes.readUInt16LE(cursor + 28);
      const extraLength = this.bytes.readUInt16LE(cursor + 30);
      const commentLength = this.bytes.readUInt16LE(cursor + 32);
      const localOffset = this.bytes.readUInt32LE(cursor + 42);
      const recordEnd = cursor + 46 + nameLength + extraLength + commentLength;
      if (recordEnd > this.bytes.length) throw new Error('ZIP central directory is truncated');
      const name = this.bytes.subarray(cursor + 46, cursor + 46 + nameLength).toString('utf8');
      if (!name || name.endsWith('/') || name.includes('..') || name.startsWith('/') || name.includes('\\')) throw new Error('unsafe ZIP member name');
      if (this.entries.has(name) || uncompressedSize > MAX_ZIP_MEMBER_BYTES || localOffset >= this.bytes.length) throw new Error('unsafe ZIP member metadata');
      totalUncompressedSize += uncompressedSize;
      if (totalUncompressedSize > MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES) throw new Error('ZIP exceeds safe uncompressed size limit');
      this.entries.set(name, { compression, compressedSize, uncompressedSize, localOffset });
      cursor = recordEnd;
    }
  }

  read(name) {
    const entry = this.entries.get(name);
    if (!entry) throw new Error(`ZIP member missing: ${name}`);
    const offset = entry.localOffset;
    if (this.bytes.readUInt32LE(offset) !== 0x04034b50) throw new Error('ZIP local entry header is malformed');
    const nameLength = this.bytes.readUInt16LE(offset + 26);
    const extraLength = this.bytes.readUInt16LE(offset + 28);
    const compressedStart = offset + 30 + nameLength + extraLength;
    const compressedEnd = compressedStart + entry.compressedSize;
    if (compressedEnd > this.bytes.length) throw new Error(`ZIP member is truncated: ${name}`);
    const compressed = this.bytes.subarray(compressedStart, compressedEnd);
    let output;
    if (entry.compression === 0) output = compressed;
    else if (entry.compression === 8) output = inflateRawSync(compressed, { maxOutputLength: MAX_ZIP_MEMBER_BYTES });
    else throw new Error(`unsupported ZIP compression method: ${entry.compression}`);
    if (output.length !== entry.uncompressedSize) throw new Error(`ZIP member size mismatch: ${name}`);
    return output;
  }
}

function extractWarcResponsePayload(warc) {
  let cursor = 0;
  while (cursor < warc.length) {
    const recordStart = warc.indexOf(Buffer.from('WARC/1.1\r\n'), cursor);
    if (recordStart < 0) break;
    const headerEnd = warc.indexOf(Buffer.from('\r\n\r\n'), recordStart);
    if (headerEnd < 0) throw new Error('WARC header is malformed');
    const header = warc.subarray(recordStart, headerEnd).toString('utf8');
    const lengthLine = header.split('\r\n').find((line) => line.toLowerCase().startsWith('content-length:'));
    if (!lengthLine) throw new Error('WARC content length is missing');
    const length = Number.parseInt(lengthLine.split(':', 2)[1].trim(), 10);
    if (!Number.isSafeInteger(length) || length < 0) throw new Error('WARC content length is invalid');
    const blockStart = headerEnd + 4;
    const block = warc.subarray(blockStart, blockStart + length);
    if (block.length !== length) throw new Error('WARC content is truncated');
    if (/^WARC-Type: response$/mi.test(header)) {
      const responseEnd = block.indexOf(Buffer.from('\r\n\r\n'));
      if (responseEnd < 0) throw new Error('embedded HTTP response is malformed');
      return block.subarray(responseEnd + 4);
    }
    cursor = blockStart + length + 4;
  }
  throw new Error('WARC response record is missing');
}

function verifyWacz(archive) {
  const packageFile = new ZipArchive(archive);
  const dataPackage = JSON.parse(packageFile.read('datapackage.json').toString('utf8'));
  for (const resource of dataPackage.resources || []) {
    const bytes = packageFile.read(resource.path);
    if (sha256Prefixed(bytes) !== resource.hash) throw new Error(`WACZ resource digest mismatch: ${resource.path}`);
  }
  return packageFile.read('archive/data.warc');
}

function verifyBundleBytes(files) {
  const checks = {};
  const manifestBytes = files.get('observation.json');
  const archiveName = [...files.keys()].find((name) => name === 'raw.wacz' || name === 'raw.warc');
  const publicBytes = files.get('observer-public.json');
  if (!manifestBytes || !archiveName || !publicBytes) return { status: 'NOT_FOUND', checks, errors: ['required offline bundle file is missing'] };
  try {
    const manifest = JSON.parse(manifestBytes.toString('utf8'));
    const archive = files.get(archiveName);
    const publicDocument = JSON.parse(publicBytes.toString('utf8'));
    const warc = manifest.content.archive_format === 'wacz' ? verifyWacz(archive) : archive;
    const payload = extractWarcResponsePayload(warc);
    checks.archive_hash = sha256Prefixed(archive) === manifest.content.archive_hash;
    checks.raw_content_hash = sha256Prefixed(payload) === manifest.content.raw_content_hash;
    checks.raw_content_bytes = payload.length === manifest.content.raw_content_bytes;
    checks.manifest_id = observationId(manifest) === manifest.observation_id;
    checks.observer_signature = verifyEd25519(manifest.observer.public_key, withoutSignature(manifest), manifest.signature?.value || '');
    checks.observer_identity = observerId(manifest.observer.public_key) === manifest.observer.observer_id;
    checks.public_key_binding = canonicalJson(publicDocument).equals(canonicalJson(manifest.observer));
    checks.canonical_url = canonicalizeUrl(manifest.object.canonical_url) === manifest.object.canonical_url;
    checks.object_identity = objectId(manifest.object.canonical_url, manifest.object.resource_type) === manifest.object.object_id;
    const valid = Object.values(checks).every((check) => check === true);
    let status = 'VERIFIED';
    if (!valid && checks.observer_signature === false) status = 'INVALID_SIGNATURE';
    else if (!valid) status = 'INVALID_BINDING';
    return { status, checks, errors: valid ? [] : Object.entries(checks).filter(([, check]) => check === false).map(([name]) => name), manifest };
  } catch (error) {
    return { status: 'MALFORMED_ARTIFACT', checks, errors: [String(error.message || error)] };
  }
}

function verifyBundleDirectory(directory) {
  const root = resolve(directory);
  if (!existsSync(root)) return { status: 'NOT_FOUND', checks: {}, errors: ['bundle directory is missing'] };
  const files = new Map();
  for (const name of ['observation.json', 'raw.wacz', 'raw.warc', 'observer-public.json', 'evidence.json']) {
    const path = `${root}/${name}`;
    if (existsSync(path)) files.set(name, readFileSync(path));
  }
  return verifyBundleBytes(files);
}

function verifyExport(file) {
  if (!existsSync(file)) return { status: 'NOT_FOUND', checks: {}, errors: ['export file is missing'] };
  try {
    const outer = new ZipArchive(readFileSync(file));
    const exportManifest = JSON.parse(outer.read('export-manifest.json').toString('utf8'));
    const exportSignature = JSON.parse(outer.read('export-signature.json').toString('utf8'));
    const descriptorBytes = outer.read('operator-descriptor.json');
    const descriptor = JSON.parse(descriptorBytes.toString('utf8'));
    const exporterPublic = JSON.parse(outer.read('exporter-public.json').toString('utf8'));
    const bundleFiles = new Map();
    for (const [name, digest] of Object.entries(exportManifest.bundle_files || {})) {
      const content = outer.read(`bundle/${name}`);
      if (sha256Prefixed(content) !== digest) return { status: 'INVALID_BINDING', checks: { [`bundle_${name}`]: false }, errors: [`bundle digest mismatch: ${name}`] };
      bundleFiles.set(name, content);
    }
    const bundle = verifyBundleBytes(bundleFiles);
    const exportChecks = {
      descriptor_operator: descriptor.operator_id === exportManifest.source_operator,
      descriptor_public_key: descriptor.public_key?.public_key_base64 === exporterPublic.public_key,
      descriptor_key_id: descriptor.public_key?.key_id === exporterPublic.observer_id,
      exporter_identity: exportManifest.exporter_observer_id === exporterPublic.observer_id,
      export_signature: verifyEd25519(exporterPublic.public_key, exportManifest, exportSignature.value || ''),
      original_issuer: exportManifest.original_issuer === bundle.manifest?.observer?.observer_id,
      artifact_binding: exportManifest.artifact?.digest === bundle.manifest?.content?.archive_hash,
      manifest_binding: exportManifest.manifest?.digest === sha256Prefixed(bundleFiles.get('observation.json')),
      observation_binding: exportManifest.observation_id === bundle.manifest?.observation_id,
      descriptor_digest: exportManifest.descriptor_digest === sha256Prefixed(descriptorBytes),
    };
    const valid = bundle.status === 'VERIFIED' && Object.values(exportChecks).every((check) => check === true);
    let status = 'VERIFIED';
    if (!valid && exportChecks.export_signature === false) status = 'INVALID_SIGNATURE';
    else if (!valid && bundle.status === 'INVALID_SIGNATURE') status = 'INVALID_SIGNATURE';
    else if (!valid && bundle.status === 'MALFORMED_ARTIFACT') status = 'MALFORMED_ARTIFACT';
    else if (!valid) status = 'INVALID_BINDING';
    return { status, checks: { ...bundle.checks, ...exportChecks }, errors: valid ? [] : [...bundle.errors, ...Object.entries(exportChecks).filter(([, check]) => check === false).map(([name]) => name)] };
  } catch (error) {
    return { status: 'MALFORMED_ARTIFACT', checks: {}, errors: [String(error.message || error)] };
  }
}

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let index = 0; index < 8; index += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function writeStoredZip(entries) {
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  for (const [name, content] of entries) {
    const filename = Buffer.from(name, 'utf8');
    const data = Buffer.from(content);
    const checksum = crc32(data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0, 6);
    local.writeUInt16LE(0, 8);
    local.writeUInt16LE(0, 10);
    local.writeUInt16LE(0, 12);
    local.writeUInt32LE(checksum, 14);
    local.writeUInt32LE(data.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(filename.length, 26);
    local.writeUInt16LE(0, 28);
    localParts.push(local, filename, data);

    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0, 8);
    central.writeUInt16LE(0, 10);
    central.writeUInt16LE(0, 12);
    central.writeUInt16LE(0, 14);
    central.writeUInt32LE(checksum, 16);
    central.writeUInt32LE(data.length, 20);
    central.writeUInt32LE(data.length, 24);
    central.writeUInt16LE(filename.length, 28);
    central.writeUInt16LE(0, 30);
    central.writeUInt16LE(0, 32);
    central.writeUInt16LE(0, 34);
    central.writeUInt16LE(0, 36);
    central.writeUInt32LE(0, 38);
    central.writeUInt32LE(offset, 42);
    centralParts.push(central, filename);
    offset += local.length + filename.length + data.length;
  }
  const centralDirectory = Buffer.concat(centralParts);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(centralDirectory.length, 12);
  end.writeUInt32LE(offset, 16);
  end.writeUInt16LE(0, 20);
  return Buffer.concat([...localParts, centralDirectory, end]);
}

function createExport(bundleDirectory, descriptorPath, privateKeyPath, exporterPublicPath, outputPath) {
  try {
    const bundleRoot = resolve(bundleDirectory);
    const bundleFiles = new Map();
    for (const name of ['observation.json', 'raw.wacz', 'raw.warc', 'observer-public.json', 'evidence.json']) {
      const path = `${bundleRoot}/${name}`;
      if (existsSync(path)) bundleFiles.set(name, readFileSync(path));
    }
    const bundle = verifyBundleBytes(bundleFiles);
    if (bundle.status !== 'VERIFIED') return bundle;
    const descriptorBytes = readFileSync(resolve(descriptorPath));
    const descriptor = JSON.parse(descriptorBytes.toString('utf8'));
    const exporterPublicBytes = readFileSync(resolve(exporterPublicPath));
    const exporterPublic = JSON.parse(exporterPublicBytes.toString('utf8'));
    if (descriptor.public_key?.public_key_base64 !== exporterPublic.public_key || descriptor.public_key?.key_id !== exporterPublic.observer_id) {
      return { status: 'INVALID_BINDING', checks: { descriptor_exporter_binding: false }, errors: ['descriptor and exporter public key do not bind'] };
    }
    const archiveName = bundleFiles.has('raw.wacz') ? 'raw.wacz' : 'raw.warc';
    const digests = Object.fromEntries([...bundleFiles.entries()].map(([name, content]) => [name, sha256Prefixed(content)]));
    const manifest = bundle.manifest;
    const exportManifest = {
      export_version: '1.0',
      exported_at: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
      source_operator: descriptor.operator_id,
      exporter_observer_id: exporterPublic.observer_id,
      descriptor_revision: descriptor.descriptor_revision,
      descriptor_digest: sha256Prefixed(descriptorBytes),
      observation_id: manifest.observation_id,
      original_issuer: manifest.observer.observer_id,
      artifact: { filename: archiveName, digest: manifest.content.archive_hash, media_type: manifest.content.archive_media_type },
      manifest: { filename: 'observation.json', digest: digests['observation.json'] },
      bundle_files: digests,
    };
    const signature = signPayload(null, canonicalJson(exportManifest), createPrivateKey(readFileSync(resolve(privateKeyPath)))).toString('base64');
    const entries = [
      ...[...bundleFiles.entries()].map(([name, content]) => [`bundle/${name}`, content]),
      ['operator-descriptor.json', descriptorBytes],
      ['exporter-public.json', exporterPublicBytes],
      ['export-manifest.json', canonicalJson(exportManifest)],
      ['export-signature.json', canonicalJson({ algorithm: 'Ed25519', signed: 'export-manifest.json', value: signature })],
    ];
    writeFileSync(resolve(outputPath), writeStoredZip(entries));
    return verifyExport(resolve(outputPath));
  } catch (error) {
    return { status: 'MALFORMED_ARTIFACT', checks: {}, errors: [String(error.message || error)] };
  }
}

function printResult(result) {
  const { manifest, ...serializable } = result;
  console.log(JSON.stringify(serializable));
  process.exitCode = result.status === 'VERIFIED' ? 0 : 1;
}

const [command, ...argumentsList] = process.argv.slice(2);
if (command === 'verify-bundle' && argumentsList.length === 1) {
  printResult(verifyBundleDirectory(argumentsList[0]));
} else if (command === 'verify-export' && argumentsList.length === 1) {
  printResult(verifyExport(argumentsList[0]));
} else if (command === 'create-export' && argumentsList.length === 5) {
  printResult(createExport(...argumentsList));
} else {
  console.error('Usage: node node_verifier.mjs verify-bundle <bundle-dir> | verify-export <export.zip> | create-export <bundle-dir> <descriptor.json> <private.pem> <exporter-public.json> <output.zip>');
  process.exitCode = 2;
}
