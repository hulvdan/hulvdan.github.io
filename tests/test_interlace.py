from pathlib import Path

import pytest
from PIL import Image

from main import interlace, is_interlaced


def make_image(mode: str) -> Image.Image:
    img = Image.new("RGBA", (40, 30))
    for x in range(40):
        for y in range(30):
            img.putpixel((x, y), (x * 6, y * 8, (x + y) * 3, 255 - x))
    if mode == "P":
        return img.convert("RGB").quantize(16)
    return img.convert(mode)


@pytest.mark.parametrize("mode", ["L", "LA", "RGB", "RGBA", "P", "I;16"])
def test_png(tmp_path: Path, mode: str):
    path = tmp_path / "a.png"
    original = make_image(mode)
    original.save(path)
    with Image.open(path) as img:
        assert not is_interlaced(img)

    interlace([path])

    with Image.open(path) as img:
        assert is_interlaced(img)
        assert img.size == original.size
        if mode != "I;16":
            assert img.convert("RGBA").tobytes() == original.convert("RGBA").tobytes()


def test_png_palette_with_transparency(tmp_path: Path):
    path = tmp_path / "a.png"
    original = make_image("P")
    original.save(path, transparency=0)
    with Image.open(path) as img:
        expected = img.convert("RGBA").tobytes()

    interlace([path])

    with Image.open(path) as img:
        assert is_interlaced(img)
        assert img.convert("RGBA").tobytes() == expected


def test_jpeg(tmp_path: Path):
    path = tmp_path / "a.jpg"
    make_image("RGB").save(path, quality=90)
    with Image.open(path) as img:
        assert not is_interlaced(img)

    interlace([path])

    with Image.open(path) as img:
        assert is_interlaced(img)
        assert img.size == (40, 30)


def test_already_interlaced_is_untouched(tmp_path: Path):
    path = tmp_path / "a.jpg"
    make_image("RGB").save(path, progressive=True)
    before = path.read_bytes()
    mtime = path.stat().st_mtime_ns

    interlace([path])

    assert path.read_bytes() == before
    assert path.stat().st_mtime_ns == mtime


def test_idempotent(tmp_path: Path):
    path = tmp_path / "a.png"
    make_image("RGB").save(path)
    interlace([path])
    after_first = path.read_bytes()

    interlace([path])

    assert path.read_bytes() == after_first


def test_many_files(tmp_path: Path):
    paths = [tmp_path / f"{i}.png" for i in range(10)]
    for path in paths:
        make_image("RGB").save(path)

    interlace(paths)

    for path in paths:
        with Image.open(path) as img:
            assert is_interlaced(img)
