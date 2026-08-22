#!/usr/bin/env node
/**
 * Independent implementation B of the IWOH v0.1 verifier.
 *
 * This source does not import implementation A, OIN source, or the fixture
 * generator. It uses Node.js built-ins and the system unzip command as a
 * separate WACZ processing path. The corpus only exercises I-JSON without
 * floats, making the explicit JCS serializer below sufficient for all inputs.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { createHash, createPublicKey, verify as verifyEd25519 } from 'node:crypto';

const ROOT = resolve(dirname(new URL(import.meta.url).pathname), '..');
const ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
const ASSERTIONS = [
  'target_identity', 'target_relation', 'statement_validity', 'comparability',
  'relationship', 'history_membership', 'completeness_scope',
  'statement_import_validity', 'equivocation_status',
];

function args() {
  const options = {};
  for (let index = 2; index < process.argv.length; index += 2) {
    const key = process.argv[index];
    const value = process.argv[index + 1];
    if (!key?.startsWith('--') || value === undefined) throw new Error('usage: --corpus PATH --output PATH');
    options[key.slice(2)] = value;
  }
  if (!options.corpus || !options.output) throw new Error('usage: --corpus PATH --output PATH');
  return options;
}

function json(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

function digest(bytes) {
  return `sha256:${createHash('sha256').update(bytes).digest('hex')}`;
}

function jcs(value) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number') {
    if (!Number.isInteger(value) || !Number.isFinite(value)) throw new Error('unsupported non-integer fixture number');
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map(jcs).join(',')}]`;
  if (typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${jcs(value[key])}`).join(',')}}`;
  }
  throw new Error('unsupported JCS value');
}

function b58decode(multibase) {
  if (typeof multibase !== 'string' || !multibase.startsWith('z')) throw new Error('multibase prefix');
  let number = 0n;
  for (const char of multibase.slice(1)) {
    const index = ALPHABET.indexOf(char);
    if (index < 0) throw new Error('invalid base58 character');
    number = number * 58n + BigInt(index);
  }
  let payload = number === 0n ? Buffer.alloc(0) : Buffer.from(number.toString(16).padStart(Math.ceil(number.toString(16).length / 2) * 2, '0'), 'hex');
  let zeros = 0;
  for (const char of multibase.slice(1)) {
    if (char !== '1') break;
    zeros += 1;
  }
  return Buffer.concat([Buffer.alloc(zeros), payload]);
}

function noProof(document) {
  const cloned = structuredClone(document);
  delete cloned.proof;
  return cloned;
}

function proofWithoutValue(proof) {
  const cloned = structuredClone(proof);
  delete cloned.proofValue;
  return cloned;
}

function unpack(corpus, relative, entry) {
  return execFileSync('unzip', ['-p', join(corpus, relative), entry], { encoding: 'buffer', maxBuffer: 8 * 1024 * 1024 });
}

class ProfileVerifierB {
  constructor(corpus) {
    this.corpus = corpus;
    const methods = json(join(corpus, 'keys', 'public_keys.json')).verification_methods;
    this.methods = new Map(methods.map((method) => [method.id, method]));
    const trust = json(join(corpus, 'trust_registry.json'));
    this.trustedControllers = new Set(trust.trusted_assertion_method_controllers);
    this.trustedReceipts = new Set(trust.trusted_time_receipt_issuers);
    this.trustedHistories = new Set(trust.trusted_history_issuers);
    this.statements = new Map();
  }

  statement(name) {
    if (!this.statements.has(name)) this.statements.set(name, json(join(this.corpus, 'statements', `${name}.json`)));
    return this.statements.get(name);
  }

  verifyProof(document) {
    const proof = document.proof;
    if (!proof || proof.type !== 'DataIntegrityProof' || proof.cryptosuite !== 'eddsa-jcs-2022' || proof.proofPurpose !== 'assertionMethod') return 'INVALID_SIGNATURE';
    const method = this.methods.get(proof.verificationMethod);
    if (!method || typeof proof.proofValue !== 'string') return 'INVALID_SIGNATURE';
    try {
      const unsecured = noProof(document);
      const proofOptions = proofWithoutValue(proof);
      if (proofOptions['@context'] !== undefined) {
        const docContext = unsecured['@context'] || [];
        const proofContext = proofOptions['@context'];
        if (!Array.isArray(docContext) || !Array.isArray(proofContext) || proofContext.some((item, index) => docContext[index] !== item)) return 'INVALID_SIGNATURE';
        unsecured['@context'] = proofContext;
      }
      const hashData = Buffer.concat([
        createHash('sha256').update(Buffer.from(jcs(proofOptions), 'utf8')).digest(),
        createHash('sha256').update(Buffer.from(jcs(unsecured), 'utf8')).digest(),
      ]);
      const rawKey = b58decode(method.publicKeyMultibase);
      const signature = b58decode(proof.proofValue);
      if (rawKey.length !== 34 || rawKey[0] !== 0xed || rawKey[1] !== 0x01 || signature.length !== 64) return 'INVALID_SIGNATURE';
      const spkiPrefix = Buffer.from('302a300506032b6570032100', 'hex');
      const publicKey = createPublicKey({ key: Buffer.concat([spkiPrefix, rawKey.subarray(2)]), format: 'der', type: 'spki' });
      if (!verifyEd25519(null, hashData, publicKey, signature)) return 'INVALID_SIGNATURE';
    } catch (_) {
      return 'INVALID_SIGNATURE';
    }
    if (document.issuer !== method.controller || !this.trustedControllers.has(method.controller)) return 'INVALID_AGENT_BINDING';
    return 'VALID';
  }

  validateArtifact(statement) {
    const evidence = statement.evidence || {};
    let warc;
    try {
      const archive = readFileSync(join(this.corpus, evidence.artifact));
      if (digest(archive) !== evidence.wacz_digest) return 'INVALID_ARCHIVE_DIGEST';
      const manifestBytes = unpack(this.corpus, evidence.artifact, 'datapackage.json');
      const packageDigest = JSON.parse(unpack(this.corpus, evidence.artifact, 'datapackage-digest.json').toString('utf8'));
      if (packageDigest.path !== 'datapackage.json' || packageDigest.hash !== digest(manifestBytes)) return 'INVALID_ARCHIVE_DIGEST';
      const manifest = JSON.parse(manifestBytes.toString('utf8'));
      if (manifest.profile !== 'data-package' || manifest.wacz_version !== '1.1.1') return 'INVALID_ARCHIVE_DIGEST';
      for (const resource of manifest.resources || []) {
        const resourceBytes = unpack(this.corpus, evidence.artifact, resource.path);
        if (resource.bytes !== resourceBytes.length || resource.hash !== digest(resourceBytes)) return 'INVALID_ARCHIVE_DIGEST';
      }
      warc = unpack(this.corpus, evidence.artifact, 'archive/data.warc');
    } catch (_) {
      return 'EVIDENCE_UNAVAILABLE';
    }
    const marker = Buffer.from(`WARC-Record-ID: <${evidence.warc_record_id}>\r\n`, 'utf8');
    if (warc.indexOf(marker) < 0) return 'INVALID_PAYLOAD_DIGEST';
    try {
      const headerEnd = warc.indexOf(Buffer.from('\r\n\r\n'));
      const headerText = warc.subarray(0, headerEnd).toString('utf8');
      const contentLine = headerText.split('\r\n').find((line) => line.toLowerCase().startsWith('content-length:'));
      if (!contentLine) return 'INVALID_PAYLOAD_DIGEST';
      const contentLength = Number.parseInt(contentLine.split(':', 2)[1].trim(), 10);
      const http = warc.subarray(headerEnd + 4, headerEnd + 4 + contentLength);
      const httpEnd = http.indexOf(Buffer.from('\r\n\r\n'));
      if (httpEnd < 0) return 'INVALID_PAYLOAD_DIGEST';
      const payload = http.subarray(httpEnd + 4);
      const payloadDigest = digest(payload);
      if (payloadDigest !== evidence.payload_digest || payloadDigest !== statement.response?.payload_digest || payload.length !== statement.response?.body_byte_length) return 'INVALID_PAYLOAD_DIGEST';
    } catch (_) {
      return 'INVALID_PAYLOAD_DIGEST';
    }
    return 'VALID';
  }

  receipt(statement) {
    const timing = statement.time_evidence || {};
    if (timing.kind !== 'causal-receipt' || typeof timing.receipt !== 'string') return null;
    try {
      const receipt = json(join(this.corpus, timing.receipt));
      if (this.verifyProof(receipt) !== 'VALID') return null;
      if (!this.trustedReceipts.has(receipt.issuer) || receipt.statement_id !== statement.id || !Number.isInteger(receipt.ordinal)) return null;
      if (!receipt.interval?.not_before || !receipt.interval?.not_after) return null;
      return receipt;
    } catch (_) {
      return null;
    }
  }

  validateStatement(name) {
    const statement = this.statement(name);
    const proof = this.verifyProof(statement);
    if (proof !== 'VALID') return proof;
    const archive = this.validateArtifact(statement);
    if (archive !== 'VALID') return archive;
    if (statement.time_evidence?.kind === 'causal-receipt' && this.receipt(statement) === null) return 'INVALID_EXTERNAL_EVIDENCE';
    return 'VALID';
  }

  history(name) {
    const document = json(join(this.corpus, 'history', `${name}.json`));
    let state = this.verifyProof(document);
    if (state === 'VALID' && !this.trustedHistories.has(document.issuer)) state = 'INVALID_AGENT_BINDING';
    return { state, document };
  }

  targetRelation(left, right) {
    const a = left.request_target.uri;
    const b = right.request_target.uri;
    if (a === b) return { identity: 'SAME_REQUEST_TARGET', relation: 'EXACT_REQUEST_TARGET' };
    const related = (source, other) => (source.target_relations || []).some((relation) => relation.from === source.request_target.uri && relation.to === other.request_target.uri && ['response', 'archive', 'external-signer'].includes(relation.asserted_by));
    return related(left, right) || related(right, left)
      ? { identity: 'DIFFERENT_REQUEST_TARGETS', relation: 'RELATED_TARGET' }
      : { identity: 'DIFFERENT_REQUEST_TARGETS', relation: 'DISTINCT_REQUEST_TARGETS' };
  }

  selectionDifference(left, right) {
    const a = left.request_context;
    const b = right.request_context;
    if (a.method !== b.method) return 'METHOD_MISMATCH';
    if (left.capture_context_completeness !== 'COMPLETE_FOR_REPRESENTATION_SELECTION' || right.capture_context_completeness !== 'COMPLETE_FOR_REPRESENTATION_SELECTION') return 'INCOMPLETE_CONTEXT';
    if (a.authentication_class !== b.authentication_class) return 'AUTH_CONTEXT_MISMATCH';
    if (a.network_vantage?.id !== b.network_vantage?.id && !(a.network_vantage?.vantage_effect === 'NONE_EXPECTED' && b.network_vantage?.vantage_effect === 'NONE_EXPECTED')) return 'VANTAGE_MISMATCH';
    const responseHeaders = (statement) => Object.fromEntries(Object.entries(statement.response?.recorded_response_headers || {}).map(([key, value]) => [key.toLowerCase(), String(value)]));
    const firstHeaders = responseHeaders(left);
    const secondHeaders = responseHeaders(right);
    const vary = new Set([...String(firstHeaders.vary || '').split(','), ...String(secondHeaders.vary || '').split(',')].map((value) => value.trim().toLowerCase()).filter(Boolean));
    const requestHeaders = (statement) => Object.fromEntries(Object.entries(statement.request_context?.recorded_request_headers || {}).map(([key, value]) => [key.toLowerCase(), String(value)]));
    const firstRequest = requestHeaders(left);
    const secondRequest = requestHeaders(right);
    for (const header of vary) {
      if (firstRequest[header] === undefined || secondRequest[header] === undefined || firstRequest[header] !== secondRequest[header]) return 'VARY_VALUE_MISMATCH';
    }
    if (jcs(a.capture_policy) !== jcs(b.capture_policy)) return 'CAPTURE_POLICY_MISMATCH';
    return null;
  }

  compare(leftName, rightName, states) {
    const left = this.statement(leftName);
    const right = this.statement(rightName);
    const target = this.targetRelation(left, right);
    if (Object.values(states).some((state) => state !== 'VALID')) return { ...target, comparability: 'INCOMPARABLE', relationship: 'INCOMPARABLE' };
    const selection = this.selectionDifference(left, right);
    if (selection !== null) {
      const differentBytes = left.response.payload_digest !== right.response.payload_digest;
      const representationReason = ['AUTH_CONTEXT_MISMATCH', 'VANTAGE_MISMATCH', 'VARY_VALUE_MISMATCH', 'CAPTURE_POLICY_MISMATCH'].includes(selection);
      return { ...target, comparability: 'INCOMPARABLE', relationship: target.identity === 'SAME_REQUEST_TARGET' && differentBytes && representationReason ? 'REPRESENTATION_VARIATION' : 'INCOMPARABLE' };
    }
    if (target.identity !== 'SAME_REQUEST_TARGET') return { ...target, comparability: 'INCOMPARABLE', relationship: 'INCOMPARABLE' };
    if (left.response.payload_digest === right.response.payload_digest) return { ...target, comparability: 'COMPARABLE', relationship: 'REPEATED_OBSERVATION' };
    const leftReceipt = this.receipt(left);
    const rightReceipt = this.receipt(right);
    if (!leftReceipt || !rightReceipt) return { ...target, comparability: 'COMPARABLE', relationship: 'UNKNOWN' };
    const leftPred = new Set(leftReceipt.predecessor_statement_ids || []);
    const rightPred = new Set(rightReceipt.predecessor_statement_ids || []);
    const ordered = (leftReceipt.interval.not_after < rightReceipt.interval.not_before && rightPred.has(left.id)) || (rightReceipt.interval.not_after < leftReceipt.interval.not_before && leftPred.has(right.id));
    if (ordered) return { ...target, comparability: 'COMPARABLE', relationship: 'TEMPORAL_VARIATION' };
    const overlap = leftReceipt.interval.not_before <= rightReceipt.interval.not_after && rightReceipt.interval.not_before <= leftReceipt.interval.not_after;
    if (overlap && !leftPred.has(right.id) && !rightPred.has(left.id)) return { ...target, comparability: 'COMPARABLE', relationship: 'PARALLEL_OBSERVATION' };
    return { ...target, comparability: 'COMPARABLE', relationship: 'UNKNOWN' };
  }

  blank() {
    return Object.fromEntries(ASSERTIONS.map((name) => [name, name === 'statement_validity' ? {} : 'NOT_APPLICABLE']));
  }

  evaluate(scenario) {
    const output = this.blank();
    const names = scenario.statements || [];
    if (names.length) output.statement_validity = Object.fromEntries(names.map((name) => [name, this.validateStatement(name)]));
    if (scenario.kind === 'comparison') {
      const comparison = this.compare(names[0], names[1], output.statement_validity);
      output.target_identity = comparison.identity;
      output.target_relation = comparison.relation;
      output.comparability = comparison.comparability;
      output.relationship = comparison.relationship;
    } else if (scenario.kind === 'history-membership') {
      const { state, document } = this.history(scenario.history_views[0]);
      if (state !== 'VALID') {
        output.completeness_scope = 'UNKNOWN';
        output.history_membership = 'HISTORY_ABSENCE_UNPROVEN';
      } else {
        output.completeness_scope = document.completeness || 'UNKNOWN';
        output.history_membership = (document.statement_ids || []).includes(this.statement(names[0]).id)
          ? 'PRESENT'
          : document.completeness === 'COMPLETE_FOR_DECLARED_SCOPE' ? 'MISSING_HISTORY' : 'HISTORY_ABSENCE_UNPROVEN';
      }
    } else if (scenario.kind === 'equivocation') {
      const histories = scenario.history_views.map((name) => ({ name, ...this.history(name) }));
      output.statement_validity = Object.fromEntries(histories.map(({ name, state }) => [name, state]));
      output.completeness_scope = histories.every(({ document }) => document.completeness === 'COMPLETE_FOR_DECLARED_SCOPE') ? 'COMPLETE_FOR_DECLARED_SCOPE' : 'UNKNOWN';
      const [left, right] = histories;
      const samePosition = left.document.checkpoint?.log_id === right.document.checkpoint?.log_id && left.document.checkpoint?.tree_size === right.document.checkpoint?.tree_size;
      output.equivocation_status = histories.every(({ state }) => state === 'VALID') && samePosition && left.document.checkpoint?.root_hash !== right.document.checkpoint?.root_hash ? 'EQUIVOCATION_DETECTED' : 'EQUIVOCATION_NOT_DETECTABLE';
    } else if (scenario.kind === 'import') {
      output.statement_import_validity = output.statement_validity[names[0]] === 'VALID' ? 'IMPORTED_VALID' : 'REJECTED_INVALID';
    }
    return output;
  }
}

function main() {
  const options = args();
  const corpus = resolve(options.corpus);
  const scenarios = json(join(corpus, 'scenarios.json')).scenarios;
  const verifier = new ProfileVerifierB(corpus);
  const results = Object.fromEntries(scenarios.map((scenario) => [scenario.id, verifier.evaluate(scenario)]));
  mkdirSync(dirname(resolve(options.output)), { recursive: true });
  writeFileSync(resolve(options.output), `${JSON.stringify({ implementation: 'B-node-native-crypto-unzip', profile_version: 'IWOH-0.1', assertion_fields: ASSERTIONS, results }, null, 2)}\n`, 'utf8');
  console.log(`implementation=B scenarios=${Object.keys(results).length} output=${resolve(options.output)}`);
}

main();
