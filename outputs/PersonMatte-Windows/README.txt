PERSON MATTE - PORTABLE WINDOWS EDITION
======================================

TURN A VIDEO INTO A WHITE-ON-BLACK PERSON MATTE

1. Extract the entire ZIP to a normal folder, such as Desktop\PersonMatte.
   Do not run the launcher from inside the ZIP.
2. Double-click EXTRACT PERSON.cmd and choose a video.
   Or drag one or more video files onto EXTRACT PERSON.cmd.
3. Wait for DONE. A new timestamped MATTE folder appears beside each input.

Your result is person_matte.mov: a full-resolution grayscale matte for
compositing. White keeps the person, black removes the room, and gray
preserves partially covered edges. The source video is never overwritten.

WHAT YOU NEED
-------------
Windows 10 (64-bit, version 2004 or newer) or Windows 11, an NVIDIA GPU
supporting DirectX 12, and a working current graphics driver.
8 GB RAM minimum; 16 GB or more and 6 GB or more GPU memory recommended
for HD/large webcam files. Larger clips need more memory and disk space.
Close GPU-heavy apps if memory is tight. Performance depends on the PC.

Python, the model, GPU inference libraries and FFmpeg are bundled.
No separate Python, CUDA toolkit, paid account, API key, or internet
connection is needed for extraction. Nothing uploads your footage.
No administrator installation is required for the included tool itself.
Keep the whole extracted folder together, including runtime, bin and models.

WHAT GETS EXPORTED
------------------
person_matte.mov  - 10-bit ProRes 422 HQ luma matte; no embedded alpha,
                   no sound. Apply it to the original video in your editor.
render.json      - source, dimensions, frame rate, frame count and timing.
decoder.log / encoder.log - processing messages for troubleshooting.

The matte keeps the displayed orientation. Odd image dimensions are padded
with one black pixel where required by the codec. Constant-frame-rate clips
are preferred. Variable-frame-rate clips are normalized by timestamps to
their reported average rate; match that rate in the editor and align by time.
Very high bit-depth/HDR source RGB is decoded to 8-bit RGB for the AI model.
This is an automatic human matte, not a general object selector. Multiple
people may all be retained. Fine hair, fast motion and similar background
textures may need cleanup for a final composite.

AFTER EFFECTS / FUSION
---------------------
After Effects: align the original video and matte at the same start time.
Set the original layer's Track Matte to person_matte.mov, choose Luma Matte,
and leave inversion off. Older AE versions require the matte directly above.

Fusion: feed the matte into a Bitmap mask set to luminance, and use that mask
on the foreground Merge. Avoid creative grades or gamma changes on the matte.
ProRes video-range levels should decode to normalized black and white.

PRIVACY
-------
No footage, person images, audio, or demonstration video is included.
All processing stays local. Do not upload your inputs or generated media.

IF SOMETHING DOES NOT WORK
--------------------------
- Run CHECK THIS PC.cmd. It checks the bundled model, runtime and FFmpeg.
- For GPU errors, update the NVIDIA driver or use EXTRACT - CPU FALLBACK.cmd.
  CPU processing is slower. The fallback still needs all bundled files.
- If a company policy blocks the command file, ask your IT team to review it.
  The readable Python source and third-party notices are included.
- If the picker is blocked by PowerShell policy, drag the video onto the
  launcher instead. This does not require the picker.
- If a job fails, its folder contains INCOMPLETE.txt. Do not use the partial
  movie. Keep the log files when reporting the problem.
- Keep the output drive writable and allow space for a ProRes movie, which
  can be substantially larger than the compressed source.
- Do not rename or remove the runtime, bin, models, or person_matte.py files.

ADVANCED / OPTIONAL
-------------------
From a terminal opened in this folder:
runtime\python.exe person_matte.py "C:\clips\interview.mp4" --start 60 --duration 10

The test matte starts at frame zero; align it to 60 seconds in the original.
--cpu uses CPU inference. --device-id 0 (or 1, etc.) selects a specific
DirectML adapter if automatic high-performance selection chooses the wrong GPU.

LICENSES AND SOURCE
-------------------
See licenses\THIRD-PARTY.txt and the included license files.
Model: Robust Video Matting / MobileNetV3, PeterL1n/RobustVideoMatting.
The person_matte.py source is included for inspection and modification.
