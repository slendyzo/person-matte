"""Distribution allowlist. No examples, source media, logs, or personal exports."""
from pathlib import Path, PurePosixPath

MEDIA={'.mp4','.mov','.mkv','.avi','.webm','.m4v','.png','.jpg','.jpeg','.gif',
       '.webp','.bmp','.tif','.tiff','.heic','.exr','.dpx','.mp3','.wav','.aac',
       '.flac','.m4a','.ogg','.pdf','.psd','.aep','.blend'}
ROOT_FILES={'person_matte.py','README.txt','VALIDATION.txt','CHECK THIS PC.cmd',
            'EXTRACT PERSON.cmd','EXTRACT - CPU FALLBACK.cmd',
            'CHECK THIS MAC.command','EXTRACT PERSON.command',
            'SHA256SUMS.txt','BUILD-PROVENANCE.json','PRIVACY.txt'}
VENDOR_ROOTS={'runtime','bin','video-tools','models','licenses'}

def allowed_entry(name):
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        return False
    if path.suffix.lower() in MEDIA or '__pycache__' in path.parts or path.suffix=='.pyc':
        return False
    if len(path.parts)==1:
        return name in ROOT_FILES
    return path.parts[0] in VENDOR_ROOTS

def validate_stage(folder):
    for p in Path(folder).rglob('*'):
        if not p.is_file(): continue
        rel=p.relative_to(folder).as_posix()
        if '__pycache__' in p.parts or p.suffix=='.pyc': continue
        # Vendor GUI icons/test plots are omitted by the packer, not shipped.
        if p.relative_to(folder).parts[0] in VENDOR_ROOTS and p.suffix.lower() in MEDIA:
            continue
        if not allowed_entry(rel):
            raise RuntimeError(f'Privacy policy blocks distribution entry: {rel}')
