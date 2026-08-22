#!/usr/bin/env python3
"""Create controlled invalid and conflicting signed claims for one experimental operator."""
from __future__ import annotations
import hashlib, json, shutil, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT=Path(__file__).resolve().parent

def sha(x:bytes)->str:return hashlib.sha256(x).hexdigest()
def now()->str:return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def stable(x):
 if isinstance(x,dict):return {k:stable(x[k]) for k in sorted(x)}
 if isinstance(x,list):return [stable(v) for v in x]
 return x
def encode(x):return json.dumps(stable(x),separators=(',',':')).encode()
def write(path:Path,x)->bytes:
 raw=encode(x);path.write_bytes(raw);return raw
def record(kind,url,ctype,data,stamp,extra=None):
 extra=extra or {}; rows=['WARC/1.1',f'WARC-Type: {kind}',f'WARC-Target-URI: {url}',f'WARC-Date: {stamp}',f'WARC-Record-ID: <urn:uuid:{uuid.uuid4()}>',f'Content-Type: {ctype}',f'Content-Length: {len(data)}']+[f'{k}: {v}' for k,v in extra.items()]
 return ('\r\n'.join(rows)+'\r\n\r\n').encode()+data+b'\r\n\r\n'
def build_actual_bundle(root:Path,private:Ed25519PrivateKey,pub:bytes,target:str,claim_key:str)->dict:
 stamp=now(); hdr={'User-Agent':'MissionNetworkAdversarialB/1.0','Accept-Language':'en-US,en;q=0.9'}
 req=Request(target,headers=hdr); 
 with urlopen(req,timeout=30) as r: status=r.status; reason=str(r.reason or ''); rh=list(r.headers.items()); body=r.read()
 sid=sha(f'{target}|{stamp}|{sha(body)}'.encode())[:24]; bundle=root/'bundles'/sid;bundle.mkdir(parents=True)
 request=(f'GET {target} HTTP/1.1\r\n'+''.join(f'{k}: {v}\r\n' for k,v in hdr.items())+'\r\n').encode(); response=(f'HTTP/1.1 {status} {reason}\r\n'+''.join(f'{k}: {v}\r\n' for k,v in rh)+f'Content-Length: {len(body)}\r\n\r\n').encode()+body
 warc=record('request',target,'application/http; msgtype=request',request,stamp)+record('response',target,'application/http; msgtype=response',response,stamp,{'WARC-Payload-Digest':f'sha256:{sha(body)}'})
 build=bundle/'build';(build/'archive').mkdir(parents=True);(build/'indexes').mkdir();(build/'archive'/'capture.warc').write_bytes(warc)
 (build/'indexes'/'index.cdxj').write_text(f'{target} {stamp.replace("-","").replace(":","").replace("T","").replace("Z","")} {json.dumps({"url":target,"digest":sha(body),"status":status})}\n')
 write(build/'metadata.json',{'format':'experimental-wacz-data-package','target':target,'captured_at':stamp,'status':status})
 resources=[]
 for rel in ['archive/capture.warc','indexes/index.cdxj','metadata.json']:
  raw=(build/rel).read_bytes();resources.append({'path':rel,'bytes':len(raw),'hash':'sha256:'+sha(raw)})
 write(build/'datapackage.json',{'profile':'data-package','resources':resources})
 package=bundle/'evidence.wacz'
 with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_STORED) as z:
  for rel in ['datapackage.json','metadata.json','archive/capture.warc','indexes/index.cdxj']:z.write(build/rel,rel)
 shutil.rmtree(build); package_sha=sha(package.read_bytes()); warc_sha=sha(warc)
 statement={'@context':['https://www.w3.org/ns/credentials/v2','https://www.w3.org/ns/prov#'],'type':['VerifiableCredential','CaptureEvidenceStatement'],'id':'urn:sha256:'+sid,'issuer':{'id':'experimental-operator-b','publicKeySha256':sha(pub)},'validFrom':stamp,'credentialSubject':{'id':target,'capture':{'activity':'http-get','claimKey':claim_key,'requestHeaders':hdr,'responseStatus':status,'responsePayloadSha256':sha(body),'transportError':None},'evidence':{'format':'WARC-1.1-in-WACZ-ZIP','file':'evidence.wacz','sha256':package_sha,'warcSha256':warc_sha,'location':f'/bundles/{sid}/'}}}
 raw=write(bundle/'statement.json',statement);(bundle/'statement.sig').write_bytes(private.sign(raw));(bundle/'signer-public.pem').write_bytes(pub)
 return {'statement_id':sid,'kind':'conflicting-valid-claim','target':target,'case_id':'T02-changed','issuer':'experimental-operator-b','captured_at':stamp,'bundle':f'/bundles/{sid}/','statement_sha256':sha(raw),'evidence_sha256':package_sha,'payload_sha256':sha(body),'status':status,'public_key_sha256':sha(pub),'claim_key':claim_key}
def main():
 root=ROOT/'operators'/'operator-b'; private=serialization.load_pem_private_key((root/'keys'/'ed25519-private.pem').read_bytes(),password=None);assert isinstance(private,Ed25519PrivateKey);pub=(root/'keys'/'ed25519-public.pem').read_bytes();cat=json.loads((root/'catalog.json').read_bytes()); uuid_entry=next(e for e in cat['entries'] if e.get('case_id')=='T02-changed' and e.get('kind')=='local-capture'); src=root/uuid_entry['bundle'].lstrip('/'); invalid_id='invalid-'+uuid_entry['statement_id'];dst=root/'bundles'/invalid_id;shutil.rmtree(dst,ignore_errors=True);shutil.copytree(src,dst)
 s=json.loads((dst/'statement.json').read_bytes());s['id']='urn:sha256:'+invalid_id;s['credentialSubject']['evidence']['sha256']='0'*64;raw=write(dst/'statement.json',s);(dst/'statement.sig').write_bytes(private.sign(raw)); invalid={**uuid_entry,'statement_id':invalid_id,'kind':'malicious-invalid-binding','bundle':f'/bundles/{invalid_id}/','statement_sha256':sha(raw),'evidence_sha256':uuid_entry['evidence_sha256'],'public_key_sha256':sha(pub)}
 claim_key='operator-b-declared-capture-slot-001'; first_dir=root/'bundles'/uuid_entry['statement_id']; first_s=json.loads((first_dir/'statement.json').read_bytes());first_id='conflict-a-'+uuid_entry['statement_id'];conf_a=root/'bundles'/first_id;shutil.rmtree(conf_a,ignore_errors=True);shutil.copytree(first_dir,conf_a);first_s['id']='urn:sha256:'+first_id;first_s['credentialSubject']['capture']['claimKey']=claim_key;first_raw=write(conf_a/'statement.json',first_s);(conf_a/'statement.sig').write_bytes(private.sign(first_raw));first={**uuid_entry,'statement_id':first_id,'kind':'conflicting-valid-claim','bundle':f'/bundles/{first_id}/','statement_sha256':sha(first_raw),'claim_key':claim_key}
 second=build_actual_bundle(root,private,pub,'https://httpbingo.org/uuid',claim_key)
 cat['entries'] += [invalid,first,second];raw=write(root/'catalog.json',cat);(root/'catalog.sig').write_bytes(private.sign(raw)); print(json.dumps({'invalid_statement_id':invalid_id,'conflict_statement_ids':[first_id,second['statement_id']],'claim_key':claim_key},sort_keys=True))
if __name__=='__main__':main()
