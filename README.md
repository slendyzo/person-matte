# Person Matte

Local video person extraction: full-resolution white-on-black ProRes mattes,
with soft gray edges for compositing in After Effects, Fusion, or another editor.

## Run the tool

Download the appropriate **v1.1-private** ZIP from this private repository's
[Releases](https://github.com/slendyzo/person-matte/releases/tag/v1.1-private).
Extract the entire ZIP before running it. Runtime, model, launchers, and README
are included. No separate Python installation or online processing is needed.

- **Apple silicon Mac:** macOS 13.4+. Run `CHECK THIS MAC.command`, then
  `EXTRACT PERSON.command` and select the input. This bundle was assembled and
  inspected on Windows; native Mac startup/performance remain unverified.
- **Windows:** run `EXTRACT PERSON.cmd`, or drop video files onto that launcher.
  Uses DirectML, with a CPU fallback launcher. The Windows runtime and export
  pipeline have been tested locally.

The source is untouched. Each run creates a timestamped output folder beside
the input. `person_matte.mov` is a grayscale luma matte, not an RGBA movie.
Automatic matting can require cleanup around fine hair and background texture.

## Privacy boundary

**Never push the person's face.** No source footage, person images, audio,
silhouette exports, or demonstration videos are in this repository or release.
The old local v1.0 ZIPs contain face-visible demonstrations and must never be
uploaded. Only the two reviewed, person-free generated room backgrounds are
included as image assets. Pretrained RVM weights were not trained on this clip.

This is a fresh Git repository with no imported parent/workspace history.
`.gitignore` denies unlisted files. `privacy-allowlist.json` lists reviewed files;
binary assets are locked to SHA-256 hashes. The privacy guard checks the index
and every reachable committed blob, including historical versions. A GitHub
workflow repeats the checks after push. CI is a secondary check: local hooks
must pass **before** transmitting data. These controls are not a face detector;
do not bypass them or add media to the allowlist without inspecting it.

Enable hooks on another clone (Python 3 required):

```sh
git config core.hooksPath .githooks
git config personmatte.python /absolute/path/to/python3
```

The hooks refuse to continue without a configured interpreter. Do not use
`--no-verify`, force-add footage, upload the old packages, or paste credentials
into tracked documentation. Never copy the user's global AGENTS.md here.

## Project layout

- `outputs/PersonMatte/`: original Torch/CUDA extractor, local HTML review UI,
  pretrained model, and generated room-only backgrounds.
- `outputs/PersonMatte-Windows/`: portable Windows wrapper and launchers.
- `outputs/PersonMatte-Mac-AppleSilicon/`: Mac wrapper and launchers.
- `work/`: source for video renders, original package assembly, and validation.
  Rendering requires your own local footage/matte files, intentionally absent.
- `tools/privacy_guard.py`: commit and push auditing.

The HTML viewer is retained as source for local use; its private `test-10s`
media is intentionally omitted. The video renderers preserve the original
production setup, including local source paths and Windows fonts. Configure
those paths for your own machine before running. They generate private media
that must stay local. Rendered MP4s are not part of the repository.

## Runtime and packaging

Large third-party runtimes and video executables are provided in the private
release ZIPs, rather than Git blobs. To restore a working source layout, extract
a release folder under this checkout's `outputs/` directory. Runtime files
remain ignored. Models, code, launchers, notices, and room artwork are in Git.

`work/package_mac.py` and `work/package_portable.py` retain the original build
processes with a distribution allowlist. Mac building additionally requires the
publisher archives/wheels in `work/mac-downloads/`; publisher metadata and exact
component versions are retained. Download origins and licenses are documented
under each platform's `licenses/`. Do not copy face-visible examples into a
package staging directory. The builders reject them.

`work/repackage_private.py` migrates the original local bundles to media-free
ones, preserving Mac executable permissions and symlinks, regenerating file
hashes, and checking CRC/content. Its input archives remain local. Output ZIPs
must receive a separate archive audit before release upload.

Third-party components retain their upstream licenses. No open-source license
is granted for first-party private project code by this README.
