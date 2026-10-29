"""Fail closed for unreviewed files and media, including reachable Git history."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT/'privacy-allowlist.json').read_text())
RULES=POLICY['files']
SECRETS=[rb'github_pat_[A-Za-z0-9_]{20,}',rb'gh[pousr]_[A-Za-z0-9]{20,}',
         rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
         rb'(?i)(?:sk-proj-|napi_|plane_api_)[A-Za-z0-9_-]{20,}',
         rb'eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}']

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

def validate(name,data):
    rule=RULES.get(name)
    if not rule: raise ValueError(f'Unreviewed file: {name}')
    if rule['kind']=='binary':
        if hashlib.sha256(data).hexdigest()!=rule['sha256']:
            raise ValueError(f'Changed/unreviewed binary: {name}')
        return
    if b'\x00' in data or len(data)>2_000_000:
        raise ValueError(f'Unexpected binary or oversized text: {name}')
    data.decode('utf-8-sig')
    if re.search(rb'data:(?:image|video|audio)/[^;]+;base64,',data,re.I):
        raise ValueError(f'Embedded media: {name}')
    for pattern in SECRETS:
        if re.search(pattern,data): raise ValueError(f'Credential-like content in {name}; content withheld')
    # Block long encoded payloads, including media hidden without a data URL.
    if re.search(rb'[A-Za-z0-9+/]{1000,}={0,2}',data):
        raise ValueError(f'Unreviewed encoded payload: {name}')

def audit():
    count=0
    for row in git('ls-files','--stage','-z').split(b'\x00'):
        if not row: continue
        meta,name=row.split(b'\t',1)
        mode,oid,stage=meta.decode().split()
        if mode not in ('100644','100755'): raise ValueError('Git links/submodules are not allowed')
        validate(name.decode(),git('cat-file','blob',oid))
        count+=1
    for row in git('rev-list','--objects','--all').splitlines():
        pieces=row.split(b' ',1)
        if len(pieces)!=2: continue
        oid,name=pieces
        if git('cat-file','-t',oid.decode()).strip()==b'blob':
            validate(name.decode(),git('cat-file','blob',oid.decode()))
    print(f'Privacy audit passed: {count} indexed files and all reachable history.')

if __name__=='__main__':
    try: audit()
    except Exception as exc:
        print(f'PUSH/COMMIT BLOCKED: {exc}',file=sys.stderr)
        sys.exit(1)
