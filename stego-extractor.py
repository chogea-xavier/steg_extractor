import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Header, Footer, Button, Input, Label, Static

# Stegosphere imports
from stegosphere.embeddings import LSB
from stegosphere import image, audio, binary_to_data

class StegoExtractorApp(App):
    """A Textual app that extracts hidden payloads from media files."""

    CSS_PATH = "extractor.tcss"  # Optional styling file
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        yield Vertical(
            Label("📂 Enter the path to the stego file (image, audio, etc.):"),
            Input(placeholder="e.g., /path/to/stego_image.png", id="file_path"),
            Button("🔍 Extract Hidden Data", id="extract", variant="primary"),
            Label("", id="result_label", classes="result"),
            Footer(),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle the extraction when the button is clicked."""
        if event.button.id != "extract":
            return

        path_str = self.query_one("#file_path", Input).value.strip()
        result_widget = self.query_one("#result_label", Label)

        if not path_str:
            result_widget.update("⚠️ Please enter a file path.")
            return

        file_path = Path(path_str)
        if not file_path.exists():
            result_widget.update(f"⚠️ File not found: {file_path}")
            return

        # Attempt extraction using the Stegosphere backend
        try:
            extracted = self._extract_payload(file_path)
            if extracted:
                # Try to decode as UTF-8 text; otherwise show as bytes
                try:
                    text = extracted.decode("utf-8")
                    result_widget.update(f"✅ Extracted text:\n\n{text}")
                except UnicodeDecodeError:
                    result_widget.update(
                        f"✅ Extracted raw data ({len(extracted)} bytes):\n\n{extracted[:200]}..."
                    )
            else:
                result_widget.update("❌ No hidden data found with the tried methods.")
        except Exception as e:
            result_widget.update(f"❌ Extraction error: {e}")

    def _extract_payload(self, file_path: Path) -> bytes | None:
        """
        Try to extract hidden data using Stegosphere.
        Supports images and audio via their respective containers.
        """
        suffix = file_path.suffix.lower()

        # Image formats supported by Stegosphere's ImageContainer (via Pillow)
        image_exts = {".png", ".bmp", ".tiff", ".webp", ".jpg", ".jpeg"}
        # Audio formats supported by Stegosphere's AudioContainer (via soundfile)
        audio_exts = {".wav", ".flac", ".ogg"}

        # Try LSB extraction with different framing methods
        methods = [None, "delimiter"]  # None uses the library's default

        if suffix in image_exts:
            container = image.ImageContainer(str(file_path))
            pixels = container.read()
            for method in methods:
                try:
                    if method:
                        payload_bits = LSB.extract(pixels, method=method)
                    else:
                        payload_bits = LSB.extract(pixels)
                    data = binary_to_data(payload_bits)
                    if data:
                        return data
                except Exception:
                    continue  # Try the next method

        elif suffix in audio_exts:
            container = audio.AudioContainer(str(file_path))
            frames = container.read()
            for method in methods:
                try:
                    if method:
                        payload_bits = LSB.extract(frames, method=method)
                    else:
                        payload_bits = LSB.extract(frames)
                    data = binary_to_data(payload_bits)
                    if data:
                        return data
                except Exception:
                    continue

        # Fallback: attempt a generic LSB extraction on raw file bytes
        # (useful for unsupported formats, though may not succeed)
        try:
            raw = file_path.read_bytes()
            # Use a simple LSB extraction on the raw bytes
            payload_bits = "".join(str(b & 1) for b in raw)
            # This naive approach may produce noise; limit to a reasonable size
            data = binary_to_data(payload_bits[:8000])
            return data if data else None
        except Exception:
            return None


if __name__ == "__main__":
    StegoExtractorApp().run()
