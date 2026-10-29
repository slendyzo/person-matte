"""Exercise Mac wrapper logic using Windows-native test dependencies.
This is NOT a macOS runtime test.
"""
import importlib.util
from pathlib import Path
import types
import sys

root=Path(__file__).resolve().parents[1]
path=root/'outputs/PersonMatte-Mac-AppleSilicon/person_matte.py'
spec=importlib.util.spec_from_file_location('mac_matte',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.FFMPEG=str(root/'outputs/PersonMatte-Windows/bin/ffmpeg.exe')
module.FFPROBE=str(root/'outputs/PersonMatte-Windows/bin/ffprobe.exe')
module.NO_WINDOW=0x08000000
sys.argv=[str(path),'--check']
module.main()
args=types.SimpleNamespace(coreml=False,start=0,duration=None,output=str(root/'work/mac-wrapper-cpu-check'))
module.extract(root/'work/portable-cpu-input.mp4',args,module.create_session())
print('Cross-platform wrapper logic passed using WINDOWS test dependencies. Native Mac execution remains untested.')
