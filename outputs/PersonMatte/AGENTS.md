# Person Matte

Local drag-and-drop video matting utility for Kiko's Ceteris webcam footage. Exports a full-frame white-on-black grayscale ProRes matte for compositing and provides a 10-second VFX review.

Python, PyTorch CUDA, FFmpeg, NumPy and Pillow. Reuses the existing Podcast Tools Python environment without modifying it. Bundled RVM MobileNetV3 TorchScript model and upstream GPL-3.0 license in models/. Keep original videos untouched. Each extraction creates a unique output folder beside its source. Never overwrite a previous export. SHOWCASE.html is the human-facing guide.

Test: source 99.5–109.5 seconds, 2702×1520 at 24 fps, 240 frames. Test assets live in test-10s/. Master contains grayscale RGB/luma, not an embedded alpha channel. Soft gray edge values represent partial coverage. Model output is automatic and may need hair-edge cleanup.
