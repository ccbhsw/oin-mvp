#!/usr/bin/env python3
"""Import a verified foreign WARC/WACZ evidence bundle without rewriting its issuer."""
from __future__ import annotations
import argparse, hashlib, json, shutil, urllib.request
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature


def sha(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=20) as response: return response.read()
def verify(pub: bytes, data: bytes, sig: bytes) -> bool:
    try: serialization.load_pem_public_key(pub).verify(sig, data); return True
    except (ValueError, InvalidSignature): return False
def join(base: str, path: str) -> str: return base.rstrip('/') + '/' + path.lstrip('/')
def package_ok(raw: bytes) -> bool:
    try:
        with ZipFile(BytesIO(raw)) as z:
            if z.testzip(): return False
            for r in json.loads(z.read('datapackage.json')).get('resources', []):
                if sha(z.read(r['path'])) != r['hash'].removeprefix('sha256:'): return False
        return True
    except Exception: return False
def stable(v):
    if isinstance(v, dict): return {k: stable(v[k]) for k in sorted(v)}
    if isinstance(v, list): return [stable(x) for x in v]
    return v
def dump(v) -> bytes: return json.dumps(stable(v), separators=(',', ':'), ensure_ascii=False).encode()

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument('--importer-root', required=True); p.add_argument('--foreign-base', required=True); p.add_argument('--statement-id', required=True); p.add_argument('--output', required=True); a=p.parse_args()
    root=Path(a.importer_root).resolve(); base=a.foreign_base; sid=a.statement_id
    cat_raw=get(join(base, 'catalog.json')); cat_sig=get(join(base,'catalog.sig')); cat_pub=get(join(base,'catalog-public.pem'))
    if not verify(cat_pub,cat_raw,cat_sig): raise SystemExit('foreign catalog signature invalid')
    foreign_cat=json.loads(cat_raw); entry=next(x for x in foreign_cat['entries'] if x['statement_id']==sid)
    rel=entry['bundle']; files=['statement.json','statement.sig','signer-public.pem','evidence.wacz']; raw={name:get(join(base,rel+name)) for name in files}
    statement=json.loads(raw['statement.json'])
    if not verify(raw['signer-public.pem'],raw['statement.json'],raw['statement.sig']): raise SystemExit('foreign statement signature invalid')
    if statement['issuer']['id'] != entry['issuer'] or statement['issuer']['publicKeySha256'] != sha(raw['signer-public.pem']): raise SystemExit('foreign issuer binding invalid')
    if entry['evidence_sha256'] != sha(raw['evidence.wacz']) or statement['credentialSubject']['evidence']['sha256'] != sha(raw['evidence.wacz']): raise SystemExit('foreign evidence binding invalid')
    if not package_ok(raw['evidence.wacz']): raise SystemExit('foreign package invalid')
    destination=root/'foreign'/entry['issuer']/sid; destination.mkdir(parents=True, exist_ok=True)
    for name, content in raw.items(): (destination/name).write_bytes(content)
    cat_path=root/'catalog.json'; local=json.loads(cat_path.read_bytes()); local_pub=(root/'catalog-public.pem').read_bytes()
    import_entry={**entry, 'kind':'import', 'bundle':f'/foreign/{entry["issuer"]}/{sid}/', 'imported_from':base, 'imported_by':local['operator']['id'], 'original_statement_sha256':sha(raw['statement.json']), 'original_evidence_sha256':sha(raw['evidence.wacz'])}
    local['entries']=[x for x in local['entries'] if not (x.get('kind')=='import' and x.get('statement_id')==sid)] + [import_entry]
    local['scope']['completeness']='complete-for-this-directory-at-generation'
    updated=dump(local); cat_path.write_bytes(updated)
    private=serialization.load_pem_private_key((root/'keys'/'ed25519-private.pem').read_bytes(), password=None)
    assert isinstance(private, Ed25519PrivateKey); (root/'catalog.sig').write_bytes(private.sign(updated))
    result={'importer':local['operator']['id'],'foreign_issuer':entry['issuer'],'statement_id':sid,'valid_before_copy':True,'issuer_preserved':entry['issuer']==statement['issuer']['id'],'bundle_path':str(destination),'package_sha256':sha(raw['evidence.wacz'])}
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n'); print(json.dumps(result,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
