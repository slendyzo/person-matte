from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import zipfile

workspace=Path(__file__).resolve().parents[1]
root=workspace/'outputs/PersonMatte-Windows'
archive=workspace/'outputs/PersonMatte-Windows-v1.1-private.zip'
from privacy_packaging import validate_stage, allowed_entry
validate_stage(root)
files=sorted(p for p in root.rglob('*') if p.is_file() and allowed_entry(p.relative_to(root).as_posix()) and p.name!='SHA256SUMS.txt')
manifest=''.join(f'{hashlib.file_digest(p.open("rb"),"sha256").hexdigest()}  {p.relative_to(root).as_posix()}\n' for p in files)
(root/'SHA256SUMS.txt').write_text(manifest,encoding='utf-8')
files.append(root/'SHA256SUMS.txt')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:
        z.write(p,Path(root.name)/p.relative_to(root))
print(f'ZIP: {archive.stat().st_size/1024/1024:.1f} MiB; {len(files)} files',flush=True)
relocated=workspace/'work/Portable QA - Joao coworker'
relocated.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as z:
    broken=z.testzip()
    if broken: raise RuntimeError(f'ZIP CRC failed: {broken}')
    z.extractall(relocated)
copy=relocated/root.name
for line in (copy/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    digest,name=line.split('  ',1)
    p=copy/name
    if hashlib.file_digest(p.open('rb'),'sha256').hexdigest()!=digest:
        raise RuntimeError(f'Hash mismatch: {name}')
print('ZIP CRC and every extracted-file SHA256 passed.',flush=True)
environment=dict(os.environ)
environment['PATH']=str(Path(os.environ['SystemRoot'])/'System32')
environment.pop('PYTHONPATH',None)
environment.pop('PYTHONHOME',None)
check=subprocess.run([str(copy/'runtime/python.exe'),'-B',str(copy/'person_matte.py'),'--check'],cwd=relocated,env=environment,text=True,capture_output=True)
print(check.stdout,flush=True)
if check.returncode:
    raise RuntimeError(check.stderr)
test=workspace/'work/portable-cpu-input.mp4'
extract=subprocess.run([str(copy/'runtime/python.exe'),'-B',str(copy/'person_matte.py'),str(test),'--output',str(relocated/'relocated-test-result')],cwd=relocated,env=environment,text=True,capture_output=True)
print(extract.stdout,flush=True)
if extract.returncode: raise RuntimeError(extract.stderr)
digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n',encoding='utf-8')
print('RELOCATED EXPORT PASSED. No external Python/FFmpeg path required.',flush=True)
