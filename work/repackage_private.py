"""Create media-free distribution ZIPs from LOCAL original portable packages.
The input ZIPs must never be uploaded. Output goes outside the repository.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import zipfile
from privacy_packaging import allowed_entry, MEDIA

ROOT=Path(__file__).resolve().parents[1]

def check_nested(data):
    import io
    if data.startswith(b'PK\x03\x04'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for i in archive.infolist():
                if PurePosixPath(i.filename).suffix.lower() in MEDIA:
                    raise RuntimeError('Media inside a nested runtime archive')

def build(original,destination):
    hashes={}
    omitted=[]
    with zipfile.ZipFile(original) as src, zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
        for info in src.infolist():
            if info.is_dir(): continue
            prefix,rel=info.filename.split('/',1)
            if rel=='SHA256SUMS.txt' or not allowed_entry(rel):
                omitted.append(rel)
                continue
            replacement=ROOT/'outputs'/prefix/rel
            if replacement.is_file():
                data=replacement.read_bytes()
            else:
                data=src.read(info)
            if rel=='BUILD-PROVENANCE.json':
                provenance=json.loads(data)
                provenance['privacy']='No footage, audio, person images, or demonstration media included.'
                data=json.dumps(provenance,indent=2).encode()
            check_nested(data)
            if data.startswith((b'\x89PNG',b'\xff\xd8\xff',b'GIF87a',b'GIF89a')) or data[4:8]==b'ftyp':
                raise RuntimeError(f'Media signature in distribution: {rel}')
            if rel.endswith('.command'): data=data.replace(b'\r\n',b'\n')
            hashes[rel]=hashlib.sha256(data).hexdigest()
            dst.writestr(info,data)
        notice=b'No person imagery, source footage, audio, or demo media is included. Original local packages were not uploaded.\n'
        dst.writestr(prefix+'/PRIVACY.txt',notice)
        hashes['PRIVACY.txt']=hashlib.sha256(notice).hexdigest()
        manifest=''.join(f'{digest}  {name}\n' for name,digest in sorted(hashes.items()))
        dst.writestr(prefix+'/SHA256SUMS.txt',manifest)
    with zipfile.ZipFile(destination) as z:
        if z.testzip(): raise RuntimeError('ZIP CRC failure')
        for name,digest in hashes.items():
            assert hashlib.sha256(z.read(prefix+'/'+name)).hexdigest()==digest
        assert all(allowed_entry(i.filename.split('/',1)[1]) for i in z.infolist())
        for i in z.infolist():
            if i.filename.endswith('.command'): assert (i.external_attr>>16)&0o111
    digest=hashlib.file_digest(destination.open('rb'),'sha256').hexdigest()
    destination.with_suffix('.zip.sha256').write_text(f'{digest}  {destination.name}\n')
    print(json.dumps({'file':destination.name,'bytes':destination.stat().st_size,'entries':len(hashes)+1,'omitted':omitted,'sha256':digest}))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--original-dir',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True)
    args=p.parse_args()
    args.destination.mkdir(parents=True,exist_ok=True)
    for platform in ('Windows','Mac-AppleSilicon'):
        build(args.original_dir/f'PersonMatte-{platform}-v1.0.zip',args.destination/f'PersonMatte-{platform}-v1.1-private.zip')
