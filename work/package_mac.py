"""Assemble a Unix-permission-preserving Mac ZIP from Windows."""
from pathlib import Path, PurePosixPath
import base64
import hashlib
import json
import posixpath
import stat
import tarfile
import zipfile

root=Path(__file__).resolve().parents[1]
stage=root/'outputs/PersonMatte-Mac-AppleSilicon'
downloads=root/'work/mac-downloads'
output=root/'outputs/PersonMatte-Mac-AppleSilicon-v1.1-private.zip'
prefix=stage.name
entries={}
from privacy_packaging import validate_stage, allowed_entry, MEDIA
validate_stage(stage)

def put(path,data,mode=0o644,link=False):
    path=PurePosixPath(path).as_posix()
    if PurePosixPath(path).suffix.lower() in MEDIA:
        return
    if not allowed_entry(path):
        raise ValueError(f'Privacy policy blocks archive entry: {path}')
    if path.startswith('/') or '..' in PurePosixPath(path).parts:
        raise ValueError(f'Unsafe archive path: {path}')
    if path in entries:
        raise ValueError(f'Duplicate archive entry: {path}')
    if link:
        target=data.decode('utf-8')
        resolved=posixpath.normpath(posixpath.join(posixpath.dirname(path),target))
        if target.startswith('/') or resolved.startswith('../'):
            raise ValueError(f'Unsafe symlink: {path} -> {target}')
    entries[path]=(data,mode,link)

def digest(path,algorithm):
    with path.open('rb') as f:
        return hashlib.file_digest(f,algorithm).hexdigest()

python_meta=json.loads((downloads/'python-assets.json').read_text(encoding='utf-8-sig'))
if digest(downloads/'python.tar.gz','sha256')!=python_meta['digest'].split(':')[1]:
    raise RuntimeError('Python publisher checksum mismatch')
video_meta=json.loads((downloads/'ffmpeg-lgpl.json').read_text(encoding='utf-8-sig'))
actual='sha512-'+base64.b64encode(bytes.fromhex(digest(downloads/'ffmpeg-lgpl.tgz','sha512'))).decode()
if actual!=video_meta['Integrity']:
    raise RuntimeError('Video-tools publisher checksum mismatch')

for p in sorted(stage.rglob('*')):
    if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':
        data=p.read_bytes()
        if p.suffix=='.command': data=data.replace(b'\r\n',b'\n')
        put(p.relative_to(stage).as_posix(),data,0o755 if p.suffix=='.command' else 0o644)

with tarfile.open(downloads/'python.tar.gz') as tar:
    for member in tar:
        if '__pycache__' in PurePosixPath(member.name).parts or member.name.endswith('.pyc'):
            continue
        path='runtime/'+member.name.removeprefix('python/')
        if member.issym():
            put(path,member.linkname.encode('utf-8'),0o777,link=True)
        elif member.isfile() or member.islnk():
            put(path,tar.extractfile(member).read(),member.mode & 0o777)

for wheel in sorted((downloads/'wheels').glob('*.whl')):
    if wheel.name.startswith('pyreadline3-'):
        continue  # Windows-only conditional dependency selected by cross-platform pip.
    with zipfile.ZipFile(wheel) as z:
        for name in z.namelist():
            if name.endswith('/') or '__pycache__' in PurePosixPath(name).parts or name.endswith('.pyc'):
                continue
            if '.data/' in name:
                if '.data/purelib/' in name: name_target=name.split('.data/purelib/',1)[1]
                elif '.data/platlib/' in name: name_target=name.split('.data/platlib/',1)[1]
                elif '.data/data/' in name:
                    put('runtime/'+name.split('.data/data/',1)[1],z.read(name))
                    continue
                else: raise ValueError(f'Unexpected wheel data layout: {name}')
            else:
                name_target=name
            mode=0o755 if name_target.endswith(('.so','.dylib')) else 0o644
            put('runtime/lib/python3.13/site-packages/'+name_target,z.read(name),mode)

with tarfile.open(downloads/'ffmpeg-lgpl.tgz') as tar:
    for member in tar:
        path='video-tools/'+member.name.removeprefix('package/')
        if member.issym():
            put(path,member.linkname.encode('utf-8'),0o777,link=True)
        elif member.isfile() or member.islnk():
            put(path,tar.extractfile(member).read(),member.mode & 0o777)

# Check every relative runtime link resolves inside this exact package.
for name,(data,mode,islink) in entries.items():
    if islink:
        resolved=posixpath.normpath(posixpath.join(posixpath.dirname(name),data.decode()))
        if resolved not in entries:
            raise RuntimeError(f'Missing symlink target: {name} -> {resolved}')

for name in ['runtime/bin/python3.13','video-tools/bin/ffmpeg','video-tools/bin/ffprobe','EXTRACT PERSON.command','CHECK THIS MAC.command']:
    if name not in entries or not entries[name][1]&0o111:
        raise RuntimeError(f'Missing executable permission: {name}')

manifest=''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n' for name,(data,_,_) in sorted(entries.items()))
put('SHA256SUMS.txt',manifest.encode())
provenance={'python':python_meta,'video_tools':video_meta,'wheels':{p.name:digest(p,'sha256') for p in (downloads/'wheels').glob('*.whl') if not p.name.startswith('pyreadline3-')},'minimum_macos':'13.4','architecture':'arm64','native_mac_tested':False}
put('BUILD-PROVENANCE.json',json.dumps(provenance,indent=2).encode())

with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name,(data,mode,islink) in sorted(entries.items()):
        info=zipfile.ZipInfo(prefix+'/'+name,date_time=(2026,10,28,12,0,0))
        info.create_system=3
        info.external_attr=((stat.S_IFLNK if islink else stat.S_IFREG)|mode)<<16
        info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,data,compresslevel=6)
print(f'ZIP created: {output.stat().st_size/1e6:.1f} MB / {len(entries)} files',flush=True)

with zipfile.ZipFile(output) as z:
    if z.testzip() is not None: raise RuntimeError('ZIP CRC check failed')
    for name,(expected,mode,islink) in entries.items():
        info=z.getinfo(prefix+'/'+name)
        actual=z.read(info)
        if hashlib.sha256(actual).digest()!=hashlib.sha256(expected).digest():
            raise RuntimeError(f'Archive content mismatch: {name}')
        if (info.external_attr>>16)&0o777!=mode:
            raise RuntimeError(f'Archive permissions changed: {name}')
        if islink and not stat.S_ISLNK(info.external_attr>>16):
            raise RuntimeError(f'Archive symlink type lost: {name}')

output.with_suffix('.zip.sha256').write_text(f'{digest(output,"sha256")}  {output.name}\n',encoding='utf-8')
print('CRC, all file contents, Unix permissions and relative symlinks verified. Native Mac execution remains untested.',flush=True)
