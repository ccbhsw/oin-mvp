#!/usr/bin/env node
/**
 * Independent Path B: provenance/statement first reading.
 * No imports from Path A or any external project implementation.
 */
import { readFile, writeFile } from 'node:fs/promises';

const getArgument = (name) => {
  const i = process.argv.indexOf(name);
  if (i === -1 || !process.argv[i + 1]) throw new Error(`missing ${name}`);
  return process.argv[i + 1];
};

const makeCase = (case_id, result, reason, standard_used) => ({
  case_id,
  path: 'B_PROVENANCE_STATEMENT_FIRST',
  result,
  reason,
  standard_used,
});

const main = async () => {
  const corpus = JSON.parse(await readFile(getArgument('--corpus'), 'utf8'));
  const output = getArgument('--output');
  const recordIds = new Set(corpus.evidence_records.map((record) => record.evidence_id));
  const required = [
    'IA-EXAMPLE-2010', 'IA-EXAMPLE-2024', 'ARQUIVO-EXAMPLE-20100323',
    'IA-EXAMPLE-20100323', 'CC-SATURN-20260714', 'SUP-ETD-20170706',
  ];
  const missing = required.filter((id) => !recordIds.has(id));
  if (missing.length) throw new Error(`missing required real evidence records: ${missing.join(', ')}`);

  const cases = [
    makeCase(
      'RW-01-ia-same-uri-different-replay',
      {
        target: 'ONE_ORIGINAL_RESOURCE_CANDIDATE_BY_LITERAL_URI',
        representation: 'TWO_DIFFERENT_MEMENTO_RESPONSES',
        time: 'MEMENTO_DATETIME_ORDER_2010_BEFORE_2024',
        relation: 'SEPARATE_ARCHIVE_ASSERTIONS_NO_SIGNED_PROVENANCE',
        scope: 'ONE_ARCHIVE_KNOWN_HISTORY_ONLY',
        agency: 'ARCHIVE_SERVICE_REPORTS_ONLY',
        equivocation: 'NO_TRANSPARENCY_RECEIPTS',
      },
      'Memento terminology can describe two prior states for one literal Original Resource URI, but the actual evidence carries no signed capture-provenance assertion establishing causal change.',
      ['RFC 7089', 'PROV-DM', 'VC 2.0'],
    ),
    makeCase(
      'RW-02-arquivo-same-digest-multiple-records',
      {
        target: 'ONE_ORIGINAL_RESOURCE_CANDIDATE_BY_LITERAL_URI',
        representation: 'SAME_DIGEST_ARTIFACT_CLAIM',
        time: 'MULTIPLE_DECLARED_CAPTURE_TIMES',
        relation: 'POTENTIAL_DUPLICATE_EVIDENCE_NO_PROVENANCE_ACTIVITY',
        scope: 'ONE_ARCHIVE_QUERY_SCOPE',
        agency: 'ARCHIVE_INDEX_ISSUER_UNSPECIFIED',
        equivocation: 'NO_TRANSPARENCY_RECEIPTS',
      },
      'Equal CDX digest is an artifact property. A provenance graph could express distinct capture Activities, but no such graph was delivered with the real rows.',
      ['PROV-DM', 'WARC 1.1', 'Arquivo.pt CDX API'],
    ),
    makeCase(
      'RW-03-two-archives-same-uri-same-datetime',
      {
        target: 'ONE_ORIGINAL_RESOURCE_CANDIDATE_BY_LITERAL_URI',
        representation: 'TWO_UNATTESTED_ARCHIVE_ARTIFACT_REFERENCES',
        time: 'SAME_DECLARED_DATETIME_NO_COMMON_CLOCK_PROOF',
        relation: 'NO_PROV_COMMUNICATION_OR_DERIVATION_ASSERTED',
        scope: 'TWO_SEPARATE_ARCHIVE_SCOPES',
        agency: 'TWO_ARCHIVE_SERVICES_NO_DELEGATION_PROOF',
        equivocation: 'NO_TRANSPARENCY_RECEIPTS',
      },
      'PROV communication, derivation, delegation and attribution are available models, but none is present in the real pair. Equal declared datetime alone does not establish a shared activity.',
      ['PROV-DM', 'VC 2.0', 'RFC 7089'],
    ),
    makeCase(
      'RW-04-commoncrawl-vary-context',
      {
        target: 'ONE_REFERENCED_RESOURCE',
        representation: 'ONE_CONTEXTUALIZED_RESPONSE_ENTITY',
        time: 'ONE_WARC_CAPTURE_BEGIN_TIME',
        relation: 'NO_SECOND_ENTITY_FOR_DERIVATION_OR_COMPARISON',
        scope: 'ONE_WARC_RECORD',
        agency: 'CRAWLER_ACTIVITY_IMPLIED_NOT_ATTESTED',
        equivocation: 'NO_TRANSPARENCY_RECEIPTS',
        recorded_context: ['content-language', 'Vary', 'Cookie', 'Authorization', 'User-Agent', 'GeoIP'],
      },
      'The WARC permits a response entity with rich context. Any comparison, provenance attribution or authority decision requires another asserted entity/activity relation that the corpus lacks.',
      ['WARC 1.1', 'RFC 9110', 'PROV-DM'],
    ),
    makeCase(
      'RW-05-legacy-wacz-redirect-canonical',
      {
        target: 'TWO_REFERENCES_WITH_TYPED_WEB_LINK_EVIDENCE',
        representation: 'PACKAGE_LOCAL_ARCHIVE_ENTITIES',
        time: 'PACKAGE_LOCAL_CAPTURE_TIME',
        relation: 'NO_PROV_SPECIALIZATION_OR_EQUIVALENCE_ASSERTED',
        scope: 'ONE_COLLECTION_DESCRIPTION',
        agency: 'COLLECTION_CONTEXT_NOT_SIGNED_PROVENANCE',
        equivocation: 'NO_TRANSPARENCY_RECEIPTS',
      },
      'HTTP typed links and package context do not by themselves create a PROV same-thing or derivation assertion between archive targets.',
      ['RFC 9110', 'PROV-DM', 'WACZ 1.1.1'],
    ),
    makeCase(
      'RW-06-ukwa-query-blocked',
      {
        target: 'NO_ENTITY_RETRIEVED',
        representation: 'NO_ENTITY_RETRIEVED',
        time: 'NO_ENTITY_RETRIEVED',
        relation: 'ACCESS_CHALLENGE_NOT_PROVENANCE',
        scope: 'UNDECLARED',
        agency: 'NO_ASSERTION_RETRIEVED',
        equivocation: 'NO_ASSERTION_RETRIEVED',
      },
      'An access challenge is neither a statement nor a provenance event sufficient to claim archival absence.',
      ['Observed public access result'],
    ),
    makeCase(
      'RW-07-import-and-checkpoint',
      {
        target: 'NO_CASE_EVIDENCE',
        representation: 'NO_CASE_EVIDENCE',
        time: 'NO_CASE_EVIDENCE',
        relation: 'NO_TRANSFER_ACTIVITY_OR_RECEIPT',
        scope: 'NO_CASE_EVIDENCE',
        agency: 'NO_DELEGATION_OR_ATTRIBUTION_EVIDENCE',
        equivocation: 'NO_SAME_LOG_CHECKPOINT_PAIR',
      },
      'Existing provenance and transparency standards have carriers and algorithms, but no case-level artifact exists for a verifier to process.',
      ['PROV-DM', 'VC 2.0', 'RFC 9943', 'RFC 9162'],
    ),
  ];

  await writeFile(output, JSON.stringify({ corpus_version: corpus.registry_version, cases }, null, 2) + '\n', 'utf8');
};

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
