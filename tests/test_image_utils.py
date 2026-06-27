from pathlib import Path

from PIL import Image

from src.ingestion.image_utils import load_rgb_image_for_clip


def test_load_rgb_rejects_tiny_image(tmp_path):
    path = tmp_path / "tiny.png"
    Image.new("RGB", (8, 8), color="red").save(path)
    assert load_rgb_image_for_clip(path) is None


def test_load_rgb_accepts_normal_image(tmp_path):
    path = tmp_path / "ok.png"
    Image.new("RGB", (64, 64), color="blue").save(path)
    img = load_rgb_image_for_clip(path)
    assert img is not None
    assert img.mode == "RGB"
    assert img.size == (64, 64)


def test_load_rgb_palette_image(tmp_path):
    path = tmp_path / "pal.png"
    pal = Image.new("P", (40, 40))
    pal.putpalette([i % 256 for i in range(768)])
    pal.save(path)
    img = load_rgb_image_for_clip(path)
    assert img is not None
    assert img.mode == "RGB"
