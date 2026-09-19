"""Drawing and GIF encoding for the motion skill: fonts, text, and the size budget.

Two things here are the whole reason this is shipped code rather than something written
per turn:

  * FONTS. Pillow has no font fallback chain. `ImageDraw.text` with the default bitmap
    font draws Chinese as boxes and says nothing about it, so the face has to be found on
    the host and opened by PATH. matplotlib is already installed and already indexes every
    font on the machine, so it is used as the finder -- not for drawing.
  * THE BUDGET. `run_python` runs under RLIMIT_FSIZE (8 MiB). A GIF written past that does
    not fail with an exception, it kills the process with SIGXFSZ and the turn is lost. So
    frames are encoded IN MEMORY, measured, and degraded -- colours, then scale, then frame
    count -- until they fit, and only then written to disk.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_HERE = Path(__file__).resolve().parent
_FONT_CACHE: dict = {}

# First hit wins, so this is a preference order, not a set. The deployed image installs
# fonts-wqy-zenhei; a bare checkout usually has none of these and falls back to Latin.
CJK_FAMILIES = ("Noto Sans CJK SC", "WenQuanYi Zen Hei", "Source Han Sans SC",
                "Noto Sans CJK JP", "Heiti SC", "Microsoft YaHei")
LATIN_FAMILIES = ("DejaVu Sans",)


def _find_font_file() -> tuple[str | None, bool]:
    """(path to a usable TTF, whether it can draw CJK). Cached for the process."""
    if "file" in _FONT_CACHE:
        return _FONT_CACHE["file"]
    found: tuple[str | None, bool] = (None, False)
    try:
        from matplotlib import font_manager

        have = {f.name for f in font_manager.fontManager.ttflist}
        for name in CJK_FAMILIES:
            if name in have:
                found = (font_manager.findfont(name, fallback_to_default=False), True)
                break
        else:
            for name in LATIN_FAMILIES:
                if name in have:
                    found = (font_manager.findfont(name, fallback_to_default=False), False)
                    break
    except Exception:  # noqa: BLE001 -- a font lookup must never take the render down
        found = (None, False)
    _FONT_CACHE["file"] = found
    return found


def font(size: int):
    """A PIL font at this size, or the bitmap default when the host has no TTF at all."""
    key = ("font", size)
    if key not in _FONT_CACHE:
        path, _ = _find_font_file()
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, size) if path else ImageFont.load_default()
        except OSError:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def cjk_ok() -> bool:
    return _find_font_file()[1]


def has_wide(text) -> bool:
    """Does this content actually need a CJK face? Warning about a font nothing needed
    is noise, and noise on something someone is about to forward reads as a defect."""
    if isinstance(text, str):
        return any(ord(ch) > 0x2E80 for ch in text)
    if isinstance(text, dict):
        return any(has_wide(v) or has_wide(k) for k, v in text.items())
    if isinstance(text, (list, tuple)):
        return any(has_wide(v) for v in text)
    return False


def text(d: ImageDraw.ImageDraw, xy, body: str, size: int, fill, anchor: str = "la") -> None:
    d.text(xy, str(body), font=font(size), fill=fill, anchor=anchor)


def width_of(body: str, size: int) -> float:
    return font(size).getlength(str(body))


def rounded(d: ImageDraw.ImageDraw, box, radius: float, fill) -> None:
    x0, y0, x1, y1 = box
    if x1 - x0 < 1:
        x1 = x0 + 1
    radius = max(0.0, min(radius, (x1 - x0) / 2, (y1 - y0) / 2))
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)


def ease(t: float) -> float:
    """Cubic in-out. Linear motion is what makes a hand-rolled animation look hand-rolled."""
    t = max(0.0, min(1.0, t))
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def measure(path: str) -> dict:
    """What the written GIF actually contains: frames, seconds, size. Never inferred."""
    total_ms, count = 0, 0
    with Image.open(path) as im:
        try:
            while True:
                im.seek(count)
                total_ms += int(im.info.get("duration") or 0)
                count += 1
        except EOFError:
            pass
    return {"frames": count, "seconds": round(total_ms / 1000.0, 1),
            "bytes": Path(path).stat().st_size}


def encode(frames: list, out_path: str, durations, *, max_bytes: int = 7_000_000,
           colours: int = 64) -> dict:
    """Write an animated GIF that FITS. Returns what it had to give up to fit.

    Degrades in the order that costs the least: palette depth first (a chart uses a dozen
    colours), then resolution, then frames. Dropping frames is last because it is the only
    one a viewer reads as broken.
    """
    report = {"frames": len(frames), "colours": colours, "scale": 1.0, "bytes": 0,
              "gave_up": []}
    if not frames:
        raise ValueError("no frames to encode")
    work, times = frames, list(durations)

    for _attempt in range(16):
        # ONE palette for the whole animation. Per-frame adaptive palettes make a GIF
        # shimmer as the colour table changes under static pixels, and cost more bytes.
        sample = work[len(work) // 2].convert("RGB")
        palette = sample.quantize(colors=report["colours"], method=Image.MEDIANCUT)
        quantised = [f.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
                     for f in work]
        buffer = io.BytesIO()
        quantised[0].save(buffer, format="GIF", save_all=True,
                          append_images=quantised[1:], duration=times, loop=0,
                          optimize=True, disposal=1)
        size = buffer.tell()
        if size <= max_bytes:
            report["bytes"] = size
            Path(out_path).write_bytes(buffer.getvalue())
            # Read the frame count back OFF THE FILE rather than trusting the list we
            # sent. The encoder folds consecutive identical frames into one with a longer
            # delay -- correct, and smaller -- so "200 frames" would be a number this
            # function made up about a file that holds 139.
            report.update(measure(out_path))
            return report
        if report["colours"] > 32:
            report["colours"] = max(32, report["colours"] // 2)
            report["gave_up"].append(f"palette down to {report['colours']} colours")
        elif report["scale"] > 0.6:
            report["scale"] = round(report["scale"] * 0.85, 3)
            size_xy = (int(frames[0].width * report["scale"]),
                       int(frames[0].height * report["scale"]))
            work = [f.resize(size_xy, Image.LANCZOS) for f in frames]
            report["gave_up"].append(f"scaled to {size_xy[0]}x{size_xy[1]}")
        elif len(work) > 24:
            # Halving the frames must NOT halve the animation: each surviving frame takes
            # over the time of the one it replaced, or a 13-second race silently becomes a
            # 6-second one and nobody can read it.
            work = work[::2]
            times = [t * 2 for t in times[::2]]
            report["gave_up"].append(f"every other frame dropped ({len(work)} left)")
        else:
            break

    # Deliberately NOT "write it anyway". run_python runs under RLIMIT_FSIZE: a file over
    # the limit does not raise, it kills the process with SIGXFSZ and the whole turn is
    # lost with no output. Refusing here costs a retry; writing costs the turn.
    raise ValueError(
        f"could not fit this animation into {max_bytes:,} bytes — smallest attempt was "
        f"{size:,} at {report['colours']} colours, {report['scale']:.2f} scale, "
        f"{len(work)} frames. Use fewer periods, fewer bars, or a smaller canvas.")
