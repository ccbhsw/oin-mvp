#!/usr/bin/env python3
"""Replicate and independently sign a static peer descriptor at each experimental operator."""
from __future__ import annotations
import json
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT=Path(__file__).resolve().parent
raw=(ROOT/'peers.json').read_bytes()
for name in ('operator-a','operator-b','operator-c'):
 root=ROOT/'operators'/name
 private=serialization.load_pem_private_key((root/'keys'/'ed25519-private.pem').read_bytes(),password=None)
 assert isinstance(private,Ed25519PrivateKey)
 (root/'peer-descriptor.json').write_bytes(raw)
 (root/'peer-descriptor.sig').write_bytes(private.sign(raw))
 print(json.dumps({'operator':name,'descriptor_bytes':len(raw)}))
