"""Procedural Cyberpunk Netrunner ASCII Dashboard Generator (NumPy + Pillow).

Generates the full suite of seamlessly looping animated WebP modules for the
GitHub profile README directly from the repository's existing anime SVG assets:
  1. assets/haluz-ascii.webp         (960x270, 108f @ 12fps = 9s V->David->Johnny transition)
  2. assets/haluz-ascii-static.webp  (960x270 static fallback)
  3. assets/ascii-sdd.webp           (480x200, 72f @ 12fps = 6s SDD orchestrator)
  4. assets/ascii-loki.webp          (480x200, 72f @ 12fps = 6s Loki grimoire + Rust terminal)
  5. assets/ascii-atlantis.webp      (480x220, 72f @ 12fps = 6s Atlantis eye & ruins ASCII)
  6. assets/ascii-arcadia.webp       (480x220, 72f @ 12fps = 6s Arcadia portal & 3D cube ASCII)
  7. assets/ascii-repos.webp         (480x150, 60f @ 12fps = 5s 3D vault + repo telemetry)
  8. assets/ascii-linkedin.webp      (480x150, 72f @ 12fps = 6s Harbour skyline + LinkedIn + rail)
"""

import argparse
import base64
import glob
import io
import math
import os
import re
import sys
from pathlib import Path

if os.name == "nt":
    sys.path.extend(glob.glob(r"C:\Users\LaCom\AppData\Local\uv\cache\archive-v0\*\Lib\site-packages"))

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = REPO_ROOT / "assets"

FPS_MS = 83  # ~12 fps crisp terminal/CRT cadence
ASCII_RAMP = " .:-=+*#%@"
GLITCH_CHARS = "$#/X01%@"
RAIN_CHARS = ("|", ":", "0", "1", ".", "+")


def load_mono_font(size: int):
    """Find a crisp monospace TrueType font with clean fallback."""
    candidates = [
        r"C:\Windows\Fonts\consolab.ttf",
        r"C:\Windows\Fonts\lucon.ttf",
        r"C:\Windows\Fonts\courbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "consolab.ttf",
        "consola.ttf",
        "DejaVuSansMono-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def extract_webp_images(svg_path: Path) -> list[Image.Image]:
    """Decode embedded data:image/webp;base64 images from a repository SVG."""
    raw = svg_path.read_text(encoding="utf-8")
    matches = re.findall(r'data:image/webp;base64,([A-Za-z0-9+/=]+)', raw)
    assert matches, f"No embedded WebP found in {svg_path}"
    return [Image.open(io.BytesIO(base64.b64decode(m))).convert("RGB") for m in matches]


def quantize_ascii_grid(
    img: Image.Image,
    cols: int,
    rows: int,
    gamma: float = 0.72,
    edge_weight: float = 0.54,
    sat_boost: float = 1.24,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample an RGB image onto an ASCII grid with Sobel gradient emphasis."""
    small = img.resize((cols, rows), Image.Resampling.LANCZOS)
    rgb = np.asarray(small, dtype=np.float32)
    mean = rgb.mean(axis=2, keepdims=True)
    rgb = np.clip(mean + (rgb - mean) * sat_boost, 0, 255)

    lum = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]) / 255.0
    lum_lift = np.power(np.clip(lum, 0.0, 1.0), gamma)

    padded = np.pad(lum_lift, 1, mode="edge")
    gx = (
        padded[:-2, 2:] + 2.0 * padded[1:-1, 2:] + padded[2:, 2:]
        - padded[:-2, :-2] - 2.0 * padded[1:-1, :-2] - padded[2:, :-2]
    )
    gy = (
        padded[2:, :-2] + 2.0 * padded[2:, 1:-1] + padded[2:, 2:]
        - padded[:-2, :-2] - 2.0 * padded[:-2, 1:-1] - padded[:-2, 2:]
    )
    edges = np.clip(np.hypot(gx, gy) * 0.92, 0.0, 1.0)
    eff_lum = np.clip(lum_lift * 0.74 + edges * edge_weight, 0.0, 1.0)
    return rgb, eff_lum, edges


def build_hud_backdrop(
    w: int,
    h: int,
    header_y: int = 22,
    footer_y: int | None = None,
    accent: tuple[int, int, int] = (0, 245, 233),
    underlay_img: Image.Image | None = None,
    underlay_strength: float = 0.20,
) -> np.ndarray:
    """Create shared #030711 Netrunner terminal backdrop with chamfered HUD frame."""
    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
    r = 3.0 + 4.0 * (yy ** 1.3) + 3.0 * (xx * yy)
    g = np.broadcast_to(6.0 + 6.0 * (yy ** 1.2), (h, w))
    b = 13.0 + 14.0 * yy + 4.0 * np.exp(-((xx - 0.5) ** 2) / 0.14)

    scan = np.where((np.arange(h) % 2) == 0, 1.0, 0.87)[:, None]
    base = np.stack([r * scan, g * scan, b * scan], axis=2)

    if underlay_img is not None:
        ul = np.asarray(
            underlay_img.resize((w, h), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=3.0)),
            dtype=np.float32,
        ) * underlay_strength
        ul[:header_y, :, :] = 0.0
        if footer_y is not None:
            ul[footer_y:, :, :] = 0.0
        base = np.clip(base + ul, 0, 255)

    img = Image.fromarray(base.astype(np.uint8), mode="RGB")
    draw = ImageDraw.Draw(img)
    c = 10
    pts = [
        (c, 1), (w - c - 1, 1), (w - 2, c),
        (w - 2, h - c - 1), (w - c - 1, h - 2),
        (c, h - 2), (1, h - c - 1), (1, c), (c, 1),
    ]
    draw.line(pts, fill=(22, 64, 84), width=1)
    draw.line([(1, 22), (1, c), (c, 1), (36, 1)], fill=accent, width=2)
    draw.line([(w - 36, 1), (w - c - 1, 1), (w - 2, c), (w - 2, 22)], fill=(255, 47, 122), width=2)
    draw.line([(1, h - 22), (1, h - c - 1), (c, h - 2), (36, h - 2)], fill=accent, width=2)
    draw.line([(w - 36, h - 2), (w - c - 1, h - 2), (w - 2, h - c - 1), (w - 2, h - 22)], fill=(255, 216, 77), width=2)
    draw.line([(10, header_y), (w - 10, header_y)], fill=(18, 50, 66), width=1)
    if footer_y is not None:
        draw.line([(10, footer_y), (w - 10, footer_y)], fill=(18, 50, 66), width=1)
    return np.asarray(img, dtype=np.float32)


def render_static_ascii_cache(
    w: int,
    h: int,
    cols: int,
    rows: int,
    dx: int,
    dy: int,
    row_top: int,
    row_bot: int,
    rgb_grid: np.ndarray,
    eff_lum: np.ndarray,
    edges: np.ndarray,
    font,
    min_lum: float = 0.06,
    gain_scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Pre-rasterize static ASCII grid onto foreground & glow arrays for fast animation."""
    fg = Image.new("RGB", (w, h), (0, 0, 0))
    gl = Image.new("RGB", (w, h), (0, 0, 0))
    fd = ImageDraw.Draw(fg)
    gd = ImageDraw.Draw(gl)

    for r in range(row_top, min(row_bot, rows)):
        for c in range(1, cols - 1):
            val = float(eff_lum[r, c])
            if val < min_lum:
                continue
            ri = max(1, min(len(ASCII_RAMP) - 1, int(val * (len(ASCII_RAMP) - 1))))
            ch = ASCII_RAMP[ri]
            col = rgb_grid[r, c]
            gain = (0.82 + 0.42 * val) * gain_scale
            cr = min(255, int(max(26, col[0]) * gain))
            cg = min(255, int(max(30, col[1]) * gain))
            cb = min(255, int(max(40, col[2]) * gain))
            px, py = c * dx, r * dy
            fd.text((px, py), ch, fill=(cr, cg, cb), font=font)
            if val > 0.34 or edges[r, c] > 0.30:
                gd.text((px, py), ch, fill=(cr, cg, cb), font=font)
    return np.asarray(fg, dtype=np.float32), np.asarray(gl, dtype=np.float32)


def compose_bloom(
    backdrop: np.ndarray,
    fg_img: Image.Image,
    glow_img: Image.Image,
    base_fg: np.ndarray | None = None,
    base_glow: np.ndarray | None = None,
    hot_r: float = 1.8,
    wide_r: float = 6.2,
    hot_w: float = 0.78,
    wide_w: float = 0.48,
) -> Image.Image:
    """Combine backdrop, pre-baked ASCII layers, animated foreground, and Gaussian bloom."""
    gl_arr = np.asarray(glow_img, dtype=np.float32)
    if base_glow is not None:
        gl_arr = np.clip(base_glow + gl_arr, 0, 255)
    gl_pil = Image.fromarray(gl_arr.astype(np.uint8), mode="RGB")

    hot = np.asarray(gl_pil.filter(ImageFilter.GaussianBlur(radius=hot_r)), dtype=np.float32) * hot_w
    wide = np.asarray(gl_pil.filter(ImageFilter.GaussianBlur(radius=wide_r)), dtype=np.float32) * wide_w
    fg_arr = np.asarray(fg_img, dtype=np.float32)
    if base_fg is not None:
        fg_arr = np.clip(base_fg + fg_arr, 0, 255)

    out = np.clip(backdrop + wide + hot + fg_arr, 0, 255).astype(np.uint8)
    return Image.fromarray(out, mode="RGB")


def save_animated_webp(frames: list[Image.Image], path: Path, duration_ms: int, max_bytes: int) -> None:
    """Save WebP animation enforcing budget by stepping quality cleanly."""
    for q in (74, 66, 58, 50):
        frames[0].save(
            path,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=0,
            quality=q,
            method=4,
        )
        size = path.stat().st_size
        if size <= max_bytes or q == 50:
            print(f"Wrote {path.name:24s}: {size:>9,} bytes ({len(frames)} frames, q={q})")
            return


def make_portrait_layer(src: Image.Image, box: tuple[int, int, int, int], target_h: int) -> tuple[Image.Image, Image.Image]:
    """Crop hero portrait and smooth outer horizontal/top edges for skylight blend."""
    patch = src.crop(box)
    w, h = patch.size
    tw = max(1, round(w * (target_h / h)))
    res = patch.resize((tw, target_h), Image.Resampling.LANCZOS)
    arr = np.asarray(res, dtype=np.float32) / 255.0
    arr = np.power(np.clip(arr, 0.0, 1.0), 0.72) * 255.0
    boosted = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")

    yy = np.linspace(0.0, 1.0, target_h, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, tw, dtype=np.float32)[None, :]
    ax = np.clip((1.0 - np.abs(xx)) / 0.24, 0.0, 1.0)
    ay = np.clip(yy / 0.12, 0.0, 1.0) * np.clip((1.0 - yy) / 0.05, 0.0, 1.0)
    mask = Image.fromarray((ax * ay * 255.0).astype(np.uint8), mode="L").filter(ImageFilter.GaussianBlur(radius=4))
    return boosted, mask


def gen_hero_sequence(fonts: dict) -> tuple[list[Image.Image], list[Image.Image]]:
    """9.0s cinematic ASCII transition between V, David Martínez, and Johnny Silverhand."""
    W, H, N = 960, 270, 108
    DX, DY = 5, 7
    COLS, ROWS = W // DX, H // DY  # 192 x 38
    R_TOP, R_BOT = 3, 35
    PLAY_H = R_BOT - R_TOP

    nc_imgs = extract_webp_images(ASSETS_DIR / "night-city.svg")
    crew_imgs = extract_webp_images(ASSETS_DIR / "night-city-crew.svg")

    # Left-side dystopian skyline backdrop (x=0..520, y=0..270)
    canyon = nc_imgs[1].resize((W, 276), Image.Resampling.LANCZOS).crop((0, 0, W, H))
    sky_base = (np.asarray(canyon, dtype=np.float32) * 0.48).astype(np.uint8)
    sky_img = Image.fromarray(sky_base, mode="RGB")

    # Prepare 3 protagonist canvases pasted heroically in viewport x=70..430
    hero_specs = [
        {
            "name": "V // VALERIE",
            "tag": "AFTERLIFE MERC · MANTIS BLADES",
            "status": "SYNAPTIC LINK: ACTIVE [99.4%]",
            "color": (255, 65, 145),
            "sub": (0, 245, 233),
            "img": make_portrait_layer(crew_imgs[0], (35, 200, 365, 540), 226),
            "x": 118,
            "idx": 0,
        },
        {
            "name": "DAVID MARTINEZ",
            "tag": "EDGERUNNERS · SANDEVISTAN MK.4",
            "status": "CYBERWARE LOAD: OVERDRIVE",
            "color": (255, 216, 77),
            "sub": (0, 245, 233),
            "img": make_portrait_layer(crew_imgs[1], (215, 62, 515, 510), 228),
            "x": 150,
            "idx": 1,
        },
        {
            "name": "JOHNNY SILVERHAND",
            "tag": "SAMURAI · RELIC BIOCHIP 2077",
            "status": "ENGRAM INTEGRITY: UNSTABLE",
            "color": (0, 245, 233),
            "sub": (255, 47, 122),
            "img": make_portrait_layer(crew_imgs[0], (550, 78, 885, 540), 228),
            "x": 135,
            "idx": 2,
        },
    ]

    # Pre-bake static ASCII caches + soft underlays for V, David, Johnny (hero cols 2..103)
    pre_heroes = []
    for sp in hero_specs:
        comp = sky_img.copy()
        p_img, p_mask = sp["img"]
        comp.paste(p_img, (sp["x"], 21), p_mask)
        # Fade right edge cleanly at x=515 so dossier on right stays ultra-clean
        c_arr = np.asarray(comp, dtype=np.float32)
        fade_x = np.clip((522.0 - np.arange(W, dtype=np.float32)) / 52.0, 0.0, 1.0)[None, :, None]
        c_arr *= fade_x
        c_pil = Image.fromarray(c_arr.astype(np.uint8), mode="RGB")

        rgb_g, lum_g, edg_g = quantize_ascii_grid(c_pil, COLS, ROWS, gamma=0.70, edge_weight=0.58)
        fg_b, gl_b = render_static_ascii_cache(
            W, H, COLS, ROWS, DX, DY, R_TOP, R_BOT, rgb_g, lum_g, edg_g, fonts["small"], min_lum=0.06
        )
        backdrop = build_hud_backdrop(W, H, header_y=20, footer_y=247, underlay_img=c_pil, underlay_strength=0.22)
        pre_heroes.append((backdrop, fg_b, gl_b, lum_g, sp))

    rng = np.random.default_rng(77)
    rain_cols = rng.integers(2, 102, 46)
    rain_r0 = rng.uniform(0, PLAY_H, 46)
    rain_spd = rng.choice([1, 2], size=46)

    frames = []
    diag = []
    for f in range(N):
        t_norm = f / N
        tau = 2.0 * math.pi * t_norm

        # Hero schedule over 108 frames:
        # 0..31 V, 32..35 trans V->D, 36..67 David, 68..71 trans D->J, 72..103 Johnny, 104..107 trans J->V
        if f < 36:
            hi = 0 if f < 34 else 1
            trans_lvl = max(0.0, (f - 31) / 4.0) if f >= 32 else 0.0
            trans_mode = "sandevistan"
        elif f < 72:
            hi = 1 if f < 70 else 2
            trans_lvl = max(0.0, (f - 67) / 4.0) if f >= 68 else 0.0
            trans_mode = "relic"
        else:
            hi = 2 if f < 106 else 0
            trans_lvl = max(0.0, (f - 103) / 4.0) if f >= 104 else 0.0
            trans_mode = "crt"

        backdrop, base_fg, base_gl, lum_g, sp = pre_heroes[hi]
        fg = Image.new("RGB", (W, H), (0, 0, 0))
        gl = Image.new("RGB", (W, H), (0, 0, 0))
        fd = ImageDraw.Draw(fg)
        gd = ImageDraw.Draw(gl)

        # Falling cyber-rain in sky/gaps (cols 2..102)
        for k in range(len(rain_cols)):
            rc = int(rain_cols[k])
            rh = rain_r0[k] + rain_spd[k] * PLAY_H * t_norm
            for seg in range(4):
                rr = R_TOP + int((rh - seg) % PLAY_H)
                if lum_g[rr, rc] > 0.42:
                    continue
                col_r = (185, 255, 252) if seg == 0 else (0, int(185 * (1 - seg / 4)), int(210 * (1 - seg / 4)))
                ch = RAIN_CHARS[(k + seg + f // 2) % len(RAIN_CHARS)]
                fd.text((rc * DX, rr * DY), ch, fill=col_r, font=fonts["small"])
                if seg == 0:
                    gd.text((rc * DX, rr * DY), ch, fill=col_r, font=fonts["small"])

        # Hero-specific procedural character animations
        if hi == 1:
            # David Sandevistan multi-color ASCII trails
            pulse = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(tau * 6.0))
            for shift, col_s in ((-6, (0, int(230 * pulse), int(225 * pulse))), (6, (int(255 * pulse), int(205 * pulse), 70))):
                for r in range(R_TOP, R_BOT, 1):
                    for c in range(28, 66):
                        if lum_g[r, c] > 0.44 and lum_g[r, c + shift] < 0.32:
                            px, py = (c + shift) * DX, r * DY
                            fd.text((px, py), "*", fill=col_s, font=fonts["small"])
                            gd.text((px, py), "*", fill=col_s, font=fonts["small"])
        elif hi == 2:
            # Johnny Relic horizontal glitch interference slices
            if (f % 9) < 4:
                for gi in range(3):
                    gr = R_TOP + ((f * 5 + gi * 9) % (PLAY_H - 2))
                    gcol = (0, 245, 233) if gi % 2 == 0 else (255, 47, 122)
                    for gc in range(26, 76, 4):
                        ch = GLITCH_CHARS[(gc + f) % len(GLITCH_CHARS)]
                        fd.text((gc * DX + 8, gr * DY), ch, fill=gcol, font=fonts["small"])
                        gd.text((gc * DX + 8, gr * DY), ch, fill=gcol, font=fonts["small"])
        else:
            # V holographic neon drink & cyan collar shimmer
            spark = 0.5 + 0.5 * math.sin(tau * 8.0)
            col_sp = (int(255 * spark), int(75 * spark), int(170 * spark))
            for ox, oy in ((342, 134), (350, 140), (336, 146)):
                fd.text((ox, oy), "+", fill=col_sp, font=fonts["small"])
                gd.text((ox, oy), "+", fill=col_sp, font=fonts["small"])

        # Dramatic slice-glitch transition effect
        if trans_lvl > 0.01:
            t_col = (255, 216, 77) if trans_mode == "sandevistan" else ((0, 245, 233) if trans_mode == "relic" else (255, 47, 122))
            for r in range(R_TOP, R_BOT, 2):
                line_s = f"{'=' * 18} // {'#' * 12} // {'*' * 14}"
                x_off = 24 + ((r * 17 + f * 29) % 45)
                fd.text((x_off, r * DY), line_s, fill=t_col, font=fonts["small"])
                gd.text((x_off, r * DY), line_s, fill=t_col, font=fonts["small"])

        # Right-hand Live Netrunner Dossier Panel (x=540..944)
        fd.line([(534, 28), (534, 240)], fill=(26, 86, 108), width=1)
        accent_c = sp["color"]
        sub_c = sp["sub"]
        fd.text((552, 34), f"[ SUBJECT 0{sp['idx'] + 1} / 03 ]", fill=sub_c, font=fonts["hud"])
        fd.text((552, 54), sp["name"], fill=accent_c, font=fonts["title"])
        gd.text((552, 54), sp["name"], fill=accent_c, font=fonts["title"])
        fd.text((552, 82), f"> {sp['tag']}", fill=(215, 248, 252), font=fonts["hud"])
        fd.text((552, 100), f"> {sp['status']}", fill=sub_c, font=fonts["hud"])

        # Live ASCII Audio / Bio Equalizer Bars
        fd.text((552, 126), "NEURAL TELEMETRY //", fill=(130, 195, 210), font=fonts["hud"])
        for bi in range(22):
            amp = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(bi * 0.55 + tau * (4 + sp["idx"])))
            bh = int(amp * 30)
            bx = 552 + bi * 16
            by_top = 178 - bh
            bcol = accent_c if amp > 0.72 else sub_c
            bar_str = "#" * max(1, bh // 7)
            for si, sch in enumerate(bar_str):
                fd.text((bx, 172 - si * 8), sch, fill=bcol, font=fonts["small"])
                if amp > 0.75:
                    gd.text((bx, 172 - si * 8), sch, fill=bcol, font=fonts["small"])

        # 3-stage interactive progress timeline bar
        prog = t_norm
        bar_w = 376
        fill_w = int(prog * bar_w)
        fd.rectangle([552, 196, 552 + bar_w, 204], outline=(35, 95, 118), width=1)
        if fill_w > 2:
            fd.rectangle([553, 197, 552 + fill_w, 203], fill=accent_c)
            gd.rectangle([553, 197, 552 + fill_w, 203], fill=accent_c)
        lbl_cols = [(255, 65, 145) if hi == 0 else (80, 120, 138), (255, 216, 77) if hi == 1 else (80, 120, 138), (0, 245, 233) if hi == 2 else (80, 120, 138)]
        fd.text((552, 212), "[01 V]", fill=lbl_cols[0], font=fonts["hud"])
        fd.text((684, 212), "[02 DAVID]", fill=lbl_cols[1], font=fonts["hud"])
        fd.text((836, 212), "[03 JOHNNY]", fill=lbl_cols[2], font=fonts["hud"])

        # Header & Footer Chrome
        led = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(tau * 6.0))
        lcol = (0, int(245 * led), int(233 * led))
        fd.ellipse([14, 7, 20, 13], fill=lcol)
        gd.ellipse([14, 7, 20, 13], fill=lcol)
        fd.text((28, 5), "HALUZ // NIGHT CITY ASCII CORE · V · DAVID · JOHNNY", fill=(154, 248, 244), font=fonts["hud"])
        fd.text((W - 116, 5), f"[LOOP {f + 1:03d}/{N}]", fill=(255, 214, 110), font=fonts["hud"])
        fd.text((16, 253), "> PYTHON GENERATIVE ASCII SHADER (NUMPY + PILLOW · CLICK TO VIEW SOURCE)", fill=(132, 224, 232), font=fonts["hud"])

        img_out = compose_bloom(backdrop, fg, gl, base_fg=base_fg, base_glow=base_gl)
        frames.append(img_out)
        if f in (12, 33, 50, 69, 86, 105):
            diag.append(img_out)

    save_animated_webp(frames, ASSETS_DIR / "haluz-ascii.webp", FPS_MS, max_bytes=2_650_000)
    frames[46].save(ASSETS_DIR / "haluz-ascii-static.webp", format="WEBP", quality=86, method=6)
    print(f"Wrote haluz-ascii-static.webp: {(ASSETS_DIR / 'haluz-ascii-static.webp').stat().st_size:,} bytes")
    return frames, diag


def gen_sdd_tile(fonts: dict) -> Image.Image:
    """480x200 tile: Spec-driven Multi-Agent ASCII Orchestrator."""
    W, H, N = 480, 200, 72
    backdrop = build_hud_backdrop(W, H, header_y=21, footer_y=172, accent=(0, 245, 233))
    frames = []
    bus_ys = (54, 96, 138)
    agent_names = ("A1//ARCH", "A2//CODE", "A3//TEST")
    agent_cols = ((255, 216, 77), (255, 65, 145), (98, 255, 203))
    spin_chars = "|/-\\"

    for f in range(N):
        t = f / N
        tau = 2.0 * math.pi * t
        fg = Image.new("RGB", (W, H), (0, 0, 0))
        gl = Image.new("RGB", (W, H), (0, 0, 0))
        fd, gd = ImageDraw.Draw(fg), ImageDraw.Draw(gl)

        # Header & Footer
        fd.ellipse([12, 7, 18, 13], fill=(0, 245, 233))
        fd.text((24, 5), "SDD-TEMPLATE // SPEC ENGINE", fill=(164, 248, 244), font=fonts["hud"])
        fd.text((W - 88, 5), "[REPO ->]", fill=(255, 216, 77), font=fonts["hud"])
        fd.text((14, 179), "> Agentes coordinados por especificacion en vivo", fill=(175, 236, 240), font=fonts["hud"])

        # Central SPEC.MD ASCII Core Box
        fd.text((20, 44), "+---------+", fill=(0, 245, 233), font=fonts["small"])
        fd.text((20, 56), "| SPEC.MD |", fill=(255, 216, 77), font=fonts["small"])
        fd.text((20, 68), "+---------+", fill=(0, 245, 233), font=fonts["small"])
        gd.text((20, 56), "| SPEC.MD |", fill=(255, 216, 77), font=fonts["small"])

        # Spec progress fill lines
        prog_lines = min(3, int((t * 1.4) % 1.0 * 4))
        for li, lbl in enumerate(("## ARCH ", "## IMPL ", "## VERIF")):
            c_ok = (98, 255, 203) if li < prog_lines else (42, 95, 110)
            fd.text((24, 86 + li * 16), f"|{lbl}|", fill=c_ok, font=fonts["small"])
            if li < prog_lines:
                gd.text((24, 86 + li * 16), f"|{lbl}|", fill=c_ok, font=fonts["small"])
        fd.text((20, 134), "+---------+", fill=(0, 245, 233), font=fonts["small"])

        # 3 Agent Pods + Traveling ASCII Packets along branched circuit buses
        for idx, (by, aname, acol) in enumerate(zip(bus_ys, agent_names, agent_cols)):
            # Bus track
            fd.text((120, by), "=====================>", fill=(28, 78, 96), font=fonts["small"])
            # Agent pod (15 chars wide so left/right pipes align)
            fd.text((322, by - 10), "+-------------+", fill=acol, font=fonts["small"])
            sp = spin_chars[(f // 2 + idx) % 4]
            fd.text((322, by), f"| [{sp}] {aname}|", fill=(235, 255, 255), font=fonts["small"])
            fd.text((322, by + 10), "+-------------+", fill=acol, font=fonts["small"])
            gd.text((322, by), f"| [{sp}] {aname}|", fill=acol, font=fonts["small"])

            # Forward packet (req) & Return verification packet (rep)
            phase = (t + idx * 0.14) % 1.0
            if phase < 0.45:
                kx = int(124 + (phase / 0.45) * 170)
                fd.text((kx, by), "***>", fill=acol, font=fonts["small"])
                gd.text((kx, by), "***>", fill=acol, font=fonts["small"])
            elif phase < 0.90:
                kx = int(294 - ((phase - 0.45) / 0.45) * 170)
                fd.text((kx, by), "<###", fill=(98, 255, 203), font=fonts["small"])
                gd.text((kx, by), "<###", fill=(98, 255, 203), font=fonts["small"])

        # Sealed status burst pulse
        if math.sin(tau) > 0.2:
            fd.text((326, 154), "[ VERIFIED OK ]", fill=(110, 255, 210), font=fonts["hud"])
            gd.text((326, 154), "[ VERIFIED OK ]", fill=(98, 255, 203), font=fonts["hud"])

        frames.append(compose_bloom(backdrop, fg, gl))

    save_animated_webp(frames, ASSETS_DIR / "ascii-sdd.webp", FPS_MS, max_bytes=900_000)
    return frames[18]


def gen_loki_tile(fonts: dict) -> Image.Image:
    """480x200 tile: Loki Code Guide cyber-grimoire & live Rust terminal fix."""
    W, H, N = 480, 200, 72
    backdrop = build_hud_backdrop(W, H, header_y=21, footer_y=172, accent=(98, 255, 203))
    frames = []
    rng = np.random.default_rng(101)
    orb_x = rng.uniform(55, 215, 22)
    orb_p = rng.uniform(0, 1, 22)

    for f in range(N):
        t = f / N
        tau = 2.0 * math.pi * t
        fg = Image.new("RGB", (W, H), (0, 0, 0))
        gl = Image.new("RGB", (W, H), (0, 0, 0))
        fd, gd = ImageDraw.Draw(fg), ImageDraw.Draw(gl)

        fd.ellipse([12, 7, 18, 13], fill=(98, 255, 203))
        fd.text((24, 5), "LOKI CODE GUIDE // OLLAMA", fill=(164, 248, 244), font=fonts["hud"])
        fd.text((W - 88, 5), "[REPO ->]", fill=(98, 255, 203), font=fonts["hud"])
        fd.text((14, 179), "> Tutor local en Rust e IA que corrige pruebas", fill=(175, 236, 240), font=fonts["hud"])

        # Open Illuminated ASCII Cyber-Grimoire (bottom-left x=26..210, y=104..166)
        wave_y = int(round(math.sin(tau * 3.0) * 2.0))
        fd.text((34, 114 + wave_y), "  .-----..-----.  ", fill=(120, 248, 240), font=fonts["small"])
        fd.text((34, 124 + wave_y), " / ~~~~ || ~~~~ \\ ", fill=(0, 245, 233), font=fonts["small"])
        fd.text((34, 134 + wave_y), "|  CODE || OLLAMA|", fill=(205, 255, 248), font=fonts["small"])
        fd.text((34, 144 + wave_y), " \\_____/\\_____/ ", fill=(72, 185, 198), font=fonts["small"])
        gd.text((34, 124 + wave_y), " / ~~~~ || ~~~~ \\ ", fill=(0, 245, 233), font=fonts["small"])

        # Rising holo-projection particles streaming from book up to terminal bottom edge
        for k in range(len(orb_x)):
            prog = (t + orb_p[k]) % 1.0
            px = int(orb_x[k] * (1 - prog) + (212 + (orb_x[k] - 130) * 0.25) * prog)
            py = int(112 - prog * 52)
            if py >= 104 or px < 210:
                fd.text((px, py), "*" if k % 2 == 0 else "·", fill=(98, 255, 203), font=fonts["small"])
                if prog > 0.35:
                    gd.text((px, py), "*", fill=(0, 245, 233), font=fonts["small"])

        # Holographic Terminal Window (top-right x=215..458, y=34..122)
        fd.text((216, 34), "+-------------------------+", fill=(0, 245, 233), font=fonts["small"])
        fd.text((216, 46), "| $ cargo test            |", fill=(175, 240, 248), font=fonts["small"])
        if t < 0.38:
            # Failing 2+2 == 5 phase
            fd.text((216, 62), "| assert_eq!(2+2, 5);     |", fill=(255, 92, 138), font=fonts["small"])
            fd.text((216, 78), "| [FAIL] expected 5       |", fill=(255, 65, 118), font=fonts["small"])
            gd.text((216, 78), "| [FAIL] expected 5       |", fill=(255, 65, 118), font=fonts["small"])
        elif t < 0.56:
            # Ollama AI golden reasoning wave
            dots = "." * (1 + (f // 3) % 4)
            fd.text((216, 62), f"| > loki: fixing line{dots:<4}|", fill=(255, 216, 77), font=fonts["small"])
            fd.text((216, 78), "| [OLLAMA] 2 + 2 == 4     |", fill=(255, 216, 77), font=fonts["small"])
            gd.text((216, 78), "| [OLLAMA] 2 + 2 == 4     |", fill=(255, 216, 77), font=fonts["small"])
        else:
            # Fixed passing green glow
            fd.text((216, 62), "| assert_eq!(2+2, 4);     |", fill=(120, 255, 212), font=fonts["small"])
            fd.text((216, 78), "| [PASS] ok in 0.01s  [v] |", fill=(98, 255, 203), font=fonts["small"])
            gd.text((216, 78), "| [PASS] ok in 0.01s  [v] |", fill=(98, 255, 203), font=fonts["small"])
        fd.text((216, 94), "+-------------------------+", fill=(0, 245, 233), font=fonts["small"])

        frames.append(compose_bloom(backdrop, fg, gl))

    save_animated_webp(frames, ASSETS_DIR / "ascii-loki.webp", FPS_MS, max_bytes=900_000)
    return frames[48]


def gen_atlantis_tile(fonts: dict) -> Image.Image:
    """480x220 tile: Sunken anime Atlantis temple + awakening Golden Eye in glowing ASCII."""
    W, H, N = 480, 220, 72
    DX, DY = 4, 6
    COLS, ROWS = W // DX, H // DY  # 120 x 36
    R_TOP, R_BOT = 4, 32

    src = extract_webp_images(ASSETS_DIR / "atlantis.svg")[0]  # 1280x445
    crop = src.crop((470, 0, 1255, 445)).resize((W, H), Image.Resampling.LANCZOS)
    rgb_g, lum_g, edg_g = quantize_ascii_grid(crop, COLS, ROWS, gamma=0.68, edge_weight=0.58)
    base_fg, base_gl = render_static_ascii_cache(
        W, H, COLS, ROWS, DX, DY, R_TOP, R_BOT, rgb_g, lum_g, edg_g, fonts["tiny"], min_lum=0.05
    )
    backdrop = build_hud_backdrop(W, H, header_y=21, footer_y=192, accent=(255, 216, 77), underlay_img=crop, underlay_strength=0.22)

    rng = np.random.default_rng(303)
    b_x = rng.uniform(18, W - 20, 34)
    b_y = rng.uniform(32, 186, 34)
    b_spd = rng.integers(1, 3, 34)
    b_ch = rng.choice(["o", "·", "*", "+"], size=34)

    frames = []
    for f in range(N):
        t = f / N
        tau = 2.0 * math.pi * t
        fg = Image.new("RGB", (W, H), (0, 0, 0))
        gl = Image.new("RGB", (W, H), (0, 0, 0))
        fd, gd = ImageDraw.Draw(fg), ImageDraw.Draw(gl)

        # Gentle bioluminescent plankton rising
        for k in range(len(b_x)):
            px = int(b_x[k] + 5.0 * math.sin(tau + k))
            py = int(28 + ((b_y[k] - 28 - b_spd[k] * 158 * t) % 158))
            col_b = (155, 255, 238) if k % 3 != 0 else (255, 224, 145)
            fd.text((px, py), str(b_ch[k]), fill=col_b, font=fonts["tiny"])
            gd.text((px, py), str(b_ch[k]), fill=col_b, font=fonts["tiny"])

        # Cyan obelisk & stair rune pulse
        pulse_y = int(186 - ((t * 1.5) % 1.0) * 60)
        fd.text((104, pulse_y), "##", fill=(168, 255, 245), font=fonts["small"])
        gd.text((104, pulse_y), "##", fill=(0, 245, 233), font=fonts["small"])

        # Awakening Golden ASCII Eye in temple pediment (cx=308, cy=56)
        open_amp = 0.5 + 0.5 * math.sin(tau - math.pi / 2)
        if open_amp < 0.25:
            eye_rows = ["---===---"]
        elif open_amp < 0.65:
            eye_rows = [".--(*)--."]
        else:
            eye_rows = ["  .===.  ", "=( <@> )=", "  '==='  "]
        for ri, er in enumerate(eye_rows):
            ey = 52 + (ri - len(eye_rows) // 2) * 9
            fd.text((284, ey), er, fill=(255, 226, 130), font=fonts["small"])
            gd.text((284, ey), er, fill=(255, 210, 88), font=fonts["small"])

        fd.ellipse([12, 7, 18, 13], fill=(255, 216, 77))
        fd.text((24, 5), "ATLANTIS OS // TEMPLO SUMERGIDO", fill=(255, 228, 148), font=fonts["hud"])
        fd.text((W - 96, 5), "[VER 3D ->]", fill=(155, 255, 238), font=fonts["hud"])
        fd.text((14, 199), "> Bajo la ciudad, el ojo dorado despierta", fill=(175, 236, 240), font=fonts["hud"])

        frames.append(compose_bloom(backdrop, fg, gl, base_fg=base_fg, base_glow=base_gl))

    save_animated_webp(frames, ASSETS_DIR / "ascii-atlantis.webp", FPS_MS, max_bytes=950_000)
    return frames[36]


def gen_arcadia_tile(fonts: dict) -> Image.Image:
    """480x220 tile: Arcadia portal vista + reaching hand + live rotating 3D ASCII Cube."""
    W, H, N = 480, 220, 72
    DX, DY = 4, 6
    COLS, ROWS = W // DX, H // DY
    R_TOP, R_BOT = 4, 32

    src = extract_webp_images(ASSETS_DIR / "arcadia.svg")[0]  # 1280x603 base
    crop = src.crop((430, 15, 1278, 595)).resize((W, H), Image.Resampling.LANCZOS)
    rgb_g, lum_g, edg_g = quantize_ascii_grid(crop, COLS, ROWS, gamma=0.70, edge_weight=0.58)
    base_fg, base_gl = render_static_ascii_cache(
        W, H, COLS, ROWS, DX, DY, R_TOP, R_BOT, rgb_g, lum_g, edg_g, fonts["tiny"], min_lum=0.05
    )
    backdrop = build_hud_backdrop(W, H, header_y=21, footer_y=192, accent=(255, 185, 120), underlay_img=crop, underlay_strength=0.22)

    # Unit cube vertices & edges for crisp 3D rotating ASCII wireframe cube
    verts = np.array([
        [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
        [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],
    ], dtype=np.float32)
    edges_idx = (
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    )

    frames = []
    for f in range(N):
        t = f / N
        tau = 2.0 * math.pi * t
        fg = Image.new("RGB", (W, H), (0, 0, 0))
        gl = Image.new("RGB", (W, H), (0, 0, 0))
        fd, gd = ImageDraw.Draw(fg), ImageDraw.Draw(gl)

        # Orbiting portal ASCII sparkles
        for pk in range(10):
            ang = tau + pk * (2 * math.pi / 10)
            px = int(226 + 52 * math.cos(ang))
            py = int(66 + 44 * math.sin(ang))
            if 24 <= py <= 185:
                fd.text((px, py), "*", fill=(255, 218, 150), font=fonts["tiny"])
                gd.text((px, py), "*", fill=(255, 218, 150), font=fonts["tiny"])

        # 3D Rotating ASCII Urano Cube levitating above calibration pad (cx=238, cy=108)
        ang_y, ang_x = tau, tau * 0.5 + 0.45
        ry = np.array([[math.cos(ang_y), 0, math.sin(ang_y)], [0, 1, 0], [-math.sin(ang_y), 0, math.cos(ang_y)]], dtype=np.float32)
        rx = np.array([[1, 0, 0], [0, math.cos(ang_x), -math.sin(ang_x)], [0, math.sin(ang_x), math.cos(ang_x)]], dtype=np.float32)
        rot_v = verts @ ry.T @ rx.T
        proj = []
        cy_float = 104 + 4.0 * math.sin(tau * 2.0)
        for vx, vy, vz in rot_v:
            sc = 1.0 / (4.2 - vz)
            proj.append((238.0 + vx * 92.0 * sc, cy_float + vy * 92.0 * sc))

        for i0, i1 in edges_idx:
            x0, y0 = proj[i0]
            x1, y1 = proj[i1]
            steps = 11
            for s in range(steps + 1):
                u = s / steps
                sx = int(round((x0 + (x1 - x0) * u) / DX) * DX)
                sy = int(round((y0 + (y1 - y0) * u) / DY) * DY)
                ch = "@" if s in (0, steps) else "#"
                col_c = (158, 255, 242) if s in (0, steps) else (255, 216, 130)
                fd.text((sx, sy), ch, fill=col_c, font=fonts["tiny"])
                gd.text((sx, sy), ch, fill=col_c, font=fonts["tiny"])

        # Fingertip cyan calibration arc toward cube
        arc_x = int(265 + 48 * (0.5 + 0.5 * math.sin(tau * 2.0)))
        fd.text((arc_x, 114), "~~+", fill=(0, 245, 233), font=fonts["small"])
        gd.text((arc_x, 114), "~~+", fill=(0, 245, 233), font=fonts["small"])

        fd.ellipse([12, 7, 18, 13], fill=(255, 195, 128))
        fd.text((24, 5), "ARCADIA // URANO MOTOR 3D EN RUST", fill=(255, 224, 175), font=fonts["hud"])
        fd.text((W - 108, 5), "[MUNDOS ->]", fill=(158, 255, 242), font=fonts["hud"])
        fd.text((14, 199), "> Portales wgpu / WGSL sincronizados a 60 Hz", fill=(175, 236, 240), font=fonts["hud"])

        frames.append(compose_bloom(backdrop, fg, gl, base_fg=base_fg, base_glow=base_gl))

    save_animated_webp(frames, ASSETS_DIR / "ascii-arcadia.webp", FPS_MS, max_bytes=950_000)
    return frames[12]


def gen_repos_tile(fonts: dict) -> Image.Image:
    """480x150 tile: 3D spinning ASCII octahedron vault + scrolling repository matrix."""
    W, H, N = 480, 150, 60
    backdrop = build_hud_backdrop(W, H, header_y=21, footer_y=None, accent=(255, 216, 77))
    verts = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], dtype=np.float32)
    edges = (
        (0, 2), (2, 1), (1, 3), (3, 0),
        (4, 0), (4, 1), (4, 2), (4, 3),
        (5, 0), (5, 1), (5, 2), (5, 3),
    )
    rows_txt = (
        "> /haluz/sdd-template      [AI SPEC]",
        "> /haluz/Loki-code-guide   [OLLAMA ]",
        "> /haluz/atlantis-os       [GIS 3D ]",
        "> /haluz/arcadia-urano     [RUST   ]",
        "> /haluz/fraud-detection   [TOKIO  ]",
    )

    frames = []
    for f in range(N):
        t = f / N
        tau = 2.0 * math.pi * t
        fg = Image.new("RGB", (W, H), (0, 0, 0))
        gl = Image.new("RGB", (W, H), (0, 0, 0))
        fd, gd = ImageDraw.Draw(fg), ImageDraw.Draw(gl)

        fd.ellipse([12, 7, 18, 13], fill=(255, 216, 77))
        fd.text((24, 5), "REPOSITORIOS // HALUZ", fill=(255, 224, 135), font=fonts["hud"])
        fd.text((W - 88, 5), "[TODOS ->]", fill=(0, 245, 233), font=fonts["hud"])

        # 3D wireframe octahedron on left (cx=84, cy=84)
        ry = np.array([[math.cos(tau), 0, math.sin(tau)], [0, 1, 0], [-math.sin(tau), 0, math.cos(tau)]], dtype=np.float32)
        rot = verts @ ry.T
        pts = [(84 + vx * 36, 84 + (vy * 0.9 - vz * 0.28) * 34) for vx, vy, vz in rot]
        for i0, i1 in edges:
            x0, y0 = pts[i0]
            x1, y1 = pts[i1]
            for s in range(9):
                u = s / 8.0
                px = int(round((x0 + (x1 - x0) * u) / 5) * 5)
                py = int(round((y0 + (y1 - y0) * u) / 7) * 7)
                ch = "@" if s in (0, 8) else "*"
                col_o = (0, 245, 233) if s in (0, 8) else (255, 216, 77)
                fd.text((px, py), ch, fill=col_o, font=fonts["small"])
                gd.text((px, py), ch, fill=col_o, font=fonts["small"])

        # Active scrolling highlight row on right directory tree
        active_idx = (f // 12) % len(rows_txt)
        for ri, rtxt in enumerate(rows_txt):
            ry_px = 36 + ri * 18
            if ri == active_idx:
                fd.text((168, ry_px), rtxt, fill=(140, 255, 244), font=fonts["hud"])
                gd.text((168, ry_px), rtxt, fill=(0, 245, 233), font=fonts["hud"])
            else:
                fd.text((168, ry_px), rtxt, fill=(75, 148, 168), font=fonts["hud"])

        fd.text((168, 128), "[ VER TODOS LOS REPOSITORIOS -> ]", fill=(255, 216, 77), font=fonts["hud"])
        frames.append(compose_bloom(backdrop, fg, gl))

    save_animated_webp(frames, ASSETS_DIR / "ascii-repos.webp", FPS_MS, max_bytes=800_000)
    return frames[10]


def gen_linkedin_tile(fonts: dict) -> Image.Image:
    """480x150 tile: Cyberpunk waterfront harbour ASCII + LinkedIn beacon + bullet train."""
    W, H, N = 480, 150, 72
    DX, DY = 4, 6
    COLS, ROWS = W // DX, H // DY
    R_TOP, R_BOT = 4, 24

    src = extract_webp_images(ASSETS_DIR / "contacto.svg")[0]  # 1280x453
    crop = src.resize((W, 170), Image.Resampling.LANCZOS).crop((0, 0, W, H))
    rgb_g, lum_g, edg_g = quantize_ascii_grid(crop, COLS, ROWS, gamma=0.72, edge_weight=0.55)
    base_fg, base_gl = render_static_ascii_cache(
        W, H, COLS, ROWS, DX, DY, R_TOP, R_BOT, rgb_g, lum_g, edg_g, fonts["tiny"], min_lum=0.05
    )
    backdrop = build_hud_backdrop(W, H, header_y=21, footer_y=None, accent=(255, 65, 145), underlay_img=crop, underlay_strength=0.20)

    frames = []
    for f in range(N):
        t = f / N
        tau = 2.0 * math.pi * t
        fg = Image.new("RGB", (W, H), (0, 0, 0))
        gl = Image.new("RGB", (W, H), (0, 0, 0))
        fd, gd = ImageDraw.Draw(fg), ImageDraw.Draw(gl)

        # Glowing LinkedIn ASCII Billboard over left tower
        fd.rectangle([88, 28, 198, 72], fill=(6, 22, 34), outline=(145, 255, 248), width=1)
        fd.text((96, 34), "[in] LINKEDIN", fill=(175, 255, 248), font=fonts["hud"])
        fd.text((96, 52), "CONNECT   ->", fill=(255, 216, 77), font=fonts["hud"])
        gd.text((96, 34), "[in] LINKEDIN", fill=(0, 245, 233), font=fonts["hud"])

        # Sleek ASCII bullet light-rail streaking across the viaduct (y=118) + water reflection
        tx = int(495 - t * 590)
        fd.text((tx, 116), "===<#========>--", fill=(165, 255, 248), font=fonts["small"])
        gd.text((tx, 116), "===<#========>--", fill=(0, 245, 233), font=fonts["small"])
        fd.text((tx, 132), "~~~.~:~~~~~~:.~~", fill=(255, 95, 165), font=fonts["tiny"])

        # Shimmering neon water glints
        sh_x = int(260 + 18 * math.sin(tau * 2.0))
        fd.text((sh_x, 136), "~=*~*", fill=(255, 145, 200), font=fonts["tiny"])

        fd.ellipse([12, 7, 18, 13], fill=(255, 65, 145))
        fd.text((24, 5), "CONTACTO // LINKEDIN HARBOUR", fill=(255, 175, 210), font=fonts["hud"])
        fd.text((W - 96, 5), "[PERFIL ->]", fill=(165, 255, 248), font=fonts["hud"])
        frames.append(compose_bloom(backdrop, fg, gl, base_fg=base_fg, base_glow=base_gl))

    save_animated_webp(frames, ASSETS_DIR / "ascii-linkedin.webp", FPS_MS, max_bytes=850_000)
    return frames[24]


def generate_all(preview_dir: Path | None = None) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    fonts = {
        "tiny": load_mono_font(7),
        "small": load_mono_font(8),
        "hud": load_mono_font(10),
        "title": load_mono_font(18),
    }

    _, hero_diag = gen_hero_sequence(fonts)
    t_sdd = gen_sdd_tile(fonts)
    t_loki = gen_loki_tile(fonts)
    t_atl = gen_atlantis_tile(fonts)
    t_arc = gen_arcadia_tile(fonts)
    t_rep = gen_repos_tile(fonts)
    t_lnk = gen_linkedin_tile(fonts)

    if preview_dir is not None:
        preview_dir.mkdir(parents=True, exist_ok=True)
        # 1. Hero 2x3 transition contact sheet
        sh = Image.new("RGB", (960 * 2, 270 * 3), (3, 7, 17))
        for i, im in enumerate(hero_diag[:6]):
            sh.paste(im, ((i % 2) * 960, (i // 2) * 270))
        sh.save(preview_dir / "preview_dash_hero.png")

        # 2. All 6 interactive tiles stitched in seamless 2-column dashboard layout
        st = Image.new("RGB", (964, 200 + 220 + 150 + 8), (3, 7, 17))
        st.paste(t_sdd, (0, 0))
        st.paste(t_loki, (484, 0))
        st.paste(t_atl, (0, 204))
        st.paste(t_arc, (484, 204))
        st.paste(t_rep, (0, 428))
        st.paste(t_lnk, (484, 428))
        st.save(preview_dir / "preview_dash_tiles.png")
        print(f"Saved preview_dash_hero.png and preview_dash_tiles.png in {preview_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the Night City Interactive ASCII Dashboard WebPs.")
    parser.add_argument("--preview-dir", type=Path, default=None, help="Optional folder for diagnostic PNG sheets.")
    args = parser.parse_args()
    generate_all(args.preview_dir)
