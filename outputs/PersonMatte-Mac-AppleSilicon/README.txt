PERSON MATTE - APPLE SILICON MAC EDITION
=======================================

Requires an M-series Mac and macOS 13.4 Ventura or newer.
This package is for Apple silicon only, not Intel Macs.

START HERE
----------
1. Double-click the ZIP in Finder to extract the whole folder.
2. Double-click CHECK THIS MAC.command once. It should say CHECK PASSED.
3. Double-click EXTRACT PERSON.command and choose one or more videos.
   Wait for DONE. A new timestamped MATTE folder appears beside each source.

Python, the model, video tools and inference libraries are included.
No Homebrew, separate Python installation, account, API key or internet
connection is needed for extraction. Processing stays on the Mac.
Keep the complete extracted folder together.

IMPORTANT FIRST-RUN NOTE
------------------------
This is a locally assembled, unsigned/not-notarized tool, not an App Store
application. macOS or your company's policy may ask for trust approval or
block it. Do not disable Gatekeeper or remove quarantine attributes to run it.
If it is blocked, ask your IT team to review the included readable source.
The package was assembled on Windows; it has NOT been executed on a Mac.
Native startup and performance still need the CHECK THIS MAC test above.

THE RESULT
----------
person_matte.mov - 10-bit ProRes 422 HQ grayscale/luma matte.
White keeps the person. Black removes the room. Gray preserves partial edges.
The MOV has no embedded alpha and no audio. Apply it to your original video.
render.json records the source, dimensions, frame rate, frame count and timing.
decoder.log and encoder.log contain processing diagnostics.
Original videos are never overwritten; each run creates a fresh output folder.

The matte keeps the displayed orientation. Odd dimensions are padded with
one black pixel where the codec needs it. Constant-frame-rate clips work best.
Variable-frame-rate video is normalized by timestamps to its reported average
rate; align by time and use the exported rate in your editing timeline.
HDR/high-bit-depth source RGB is decoded to 8-bit RGB for the model.
Fine hair, fast motion and similar background textures may need edge cleanup.
This is human matting; it is not a general object selector. More than one
person in the shot may be included.

COMPOSITING
-----------
After Effects: align the source and matte. Set the source layer's Track Matte
to person_matte.mov and choose Luma Matte, with inversion off. Older AE versions
require the matte layer directly above the source.

Fusion: feed the matte into a Bitmap mask set to luminance and use the mask
on the foreground Merge. Avoid creative grades/gamma changes on the matte.
Its ProRes video-range levels should decode to normalized black and white.

PROCESSING SPEED
----------------
Default processing uses the native Apple-silicon CPU. This avoids relying on
an untested Core ML graph conversion. There is no CUDA or NVIDIA dependency.
Mac speed has not been measured. Start with a short clip before a long job.
8 GB memory minimum; 16 GB or more is recommended for larger webcam videos.
Allow free space for a ProRes movie, which can exceed the size of the input.

PRIVACY
-------
No footage, person images, audio, or demonstration video is included.
All processing stays local. Do not upload your inputs or generated media.

TROUBLESHOOTING
---------------
- Run CHECK THIS MAC.command and keep its CHECK-RESULT.txt if it fails.
- Check that macOS is version 13.4 or newer and that the Mac has an M-series chip.
- If the script opens in an editor, its .command association may differ from
  the macOS default. Ask IT to review/open it with Terminal.
- If macOS asks to access the selected source/output folder, review that
  permission request. No Full Disk Access is required by the tool itself.
- A failed job contains INCOMPLETE.txt. Do not use the partial output movie.
- Do not rename or remove runtime, video-tools, models or person_matte.py.

ADVANCED (OPTIONAL)
-------------------
From Terminal in the extracted folder:
./runtime/bin/python3.13 -I -B person_matte.py "/path/to/video.mp4" --start 60 --duration 10

This makes a 10-second test starting at 60 seconds. Align its frame zero with
60 seconds in the original. The default launcher processes the entire clip.

--coreml opts into an experimental Core ML + CPU path. It may compile slowly,
fail on this recurrent model or run slower than CPU. It has not been tested
on Mac hardware. Omit the option to return to the default CPU path.

SOURCE AND THIRD-PARTY COMPONENTS
--------------------------------
The wrapper source is person_matte.py. Third-party notices are in licenses/.
Model: Robust Video Matting / MobileNetV3, PeterL1n/RobustVideoMatting.
Executable permissions and relative runtime links are preserved in the ZIP.
