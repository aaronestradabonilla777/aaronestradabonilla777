"""Procedural Cyberpunk Netrunner ASCII Dashboard Generator (NumPy + Pillow).

Generates the seamlessly looping animated WebP modules for the GitHub profile
README directly from the repository's existing anime SVG assets and 3D shaders:
  1. assets/haluz-ascii.webp         (960x270, 108f @ 12fps = 9s V->David->Johnny transition)
  2. assets/haluz-ascii-static.webp  (960x270 static fallback)
  3. assets/ascii-sdd.webp           (480x200, 72f @ 12fps = 6s 3D gyro core + SDD orchestrator)
  4. assets/ascii-loki.webp          (480x200, 72f @ 12fps = 6s 3D trefoil neural core + Cyber-IDE)
  5. assets/ascii-repos.webp         (480x150, 60f @ 12fps = 5s 3D torus + repo matrix console)
  6. assets/ascii-linkedin.webp      (480x150, 72f @ 12fps = 6s Harbour skyline + LinkedIn + rail)
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


SHADE_RAMP = " .,-~:;=!*#$@"
_LIGHT_DIR = np.array([-0.45, -0.65, 0.72], dtype=np.float32)
_LIGHT_DIR = _LIGHT_DIR / np.linalg.norm(_LIGHT_DIR)


def build_ambient_city_layer(
    w: int,
    h: int,
    r_top: int,
    r_bot: int,
    font,
    nc_idx: int,
    crop_box: tuple[int, int, int, int],
    tint_rgb: tuple[float, float, float],
    underlay_strength: float = 0.26,
    gain_scale: float = 0.42,
) -> tuple[Image.Image, np.ndarray, np.ndarray]:
    """Create dense tinted cyberpunk skyline ASCII backdrop from Night City artwork."""
    src = extract_webp_images(ASSETS_DIR / "night-city.svg")[nc_idx]
    sw, sh = src.size
    x0 = max(0, min(sw - 1, crop_box[0]))
    y0 = max(0, min(sh - 1, crop_box[1]))
    x1 = max(x0 + 1, min(sw, crop_box[2]))
    y1 = max(y0 + 1, min(sh, crop_box[3]))

    patch = src.crop((x0, y0, x1, y1)).resize((w, h), Image.Resampling.LANCZOS)
    arr = np.asarray(patch, dtype=np.float32) * np.array(tint_rgb, dtype=np.float32)[None, None, :]
    tinted = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")

    cols, rows = w // 4, h // 6
    rgb_g, lum_g, edg_g = quantize_ascii_grid(tinted, cols, rows, gamma=0.74, edge_weight=0.52)
    base_fg, base_gl = render_static_ascii_cache(
        w, h, cols, rows, 4, 6, r_top, r_bot, rgb_g, lum_g, edg_g, font, min_lum=0.09, gain_scale=gain_scale
    )
    return tinted, base_fg, base_gl


def draw_perspective_grid(
    fd: ImageDraw.ImageDraw,
    gd: ImageDraw.ImageDraw,
    w: int,
    h: int,
    y_horizon: int,
    y_bottom: int,
    phase: float,
    line_col: tuple[int, int, int],
    glow_col: tuple[int, int, int],
) -> None:
    """Draw a 3D receding cyberpunk floor grid clipped cleanly inside [6, w-6]."""
    vx, vy = w * 0.5, y_horizon - 28.0
    span_y = max(1.0, float(y_bottom - y_horizon))

    # Subtle horizon beam
    fd.line([(8, y_horizon), (w - 8, y_horizon)], fill=glow_col, width=1)
    gd.line([(8, y_horizon), (w - 8, y_horizon)], fill=glow_col, width=1)

    # 9 radiating perspective rays clipped cleanly against floor bounds
    for ri in range(-4, 5):
        xb = vx + ri * (w * 0.16)
        slope_x = xb - vx
        denom_y = float(y_bottom - vy)
        xh = vx + slope_x * ((y_horizon - vy) / denom_y)
        pts_y = [y_horizon, y_bottom]
        pts_x = [xh, xb]
        # Clip left/right edges at x=6 and x=w-6
        t0, t1 = 0.0, 1.0
        dx_ray = pts_x[1] - pts_x[0]
        if abs(dx_ray) > 1e-4:
            if pts_x[0] < 6.0:
                t0 = max(t0, (6.0 - pts_x[0]) / dx_ray)
            elif pts_x[0] > w - 6.0:
                t0 = max(t0, ((w - 6.0) - pts_x[0]) / dx_ray)
            if pts_x[1] < 6.0:
                t1 = min(t1, (6.0 - pts_x[0]) / dx_ray)
            elif pts_x[1] > w - 6.0:
                t1 = min(t1, ((w - 6.0) - pts_x[0]) / dx_ray)
        if t1 > t0:
            sx = int(round(pts_x[0] + dx_ray * t0))
            sy = int(round(pts_y[0] + span_y * t0))
            ex = int(round(pts_x[0] + dx_ray * t1))
            ey = int(round(pts_y[0] + span_y * t1))
            fd.line([(sx, sy), (ex, ey)], fill=line_col, width=1)

    # 6 horizontal scrolling depth lines
    for i in range(6):
        u = ((i + phase) / 6.0) ** 1.85
        ly = int(round(y_horizon + u * span_y))
        if y_horizon <= ly <= y_bottom:
            fd.line([(8, ly), (w - 8, ly)], fill=line_col, width=1)


def draw_cyber_panel(
    fd: ImageDraw.ImageDraw,
    gd: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    border_col: tuple[int, int, int],
    accent_col: tuple[int, int, int],
    fill_col: tuple[int, int, int] = (6, 15, 26),
    chamfer: int = 6,
) -> None:
    """Draw a chamfered dark-glass HUD panel with neon corner bracket highlights."""
    x0, y0, x1, y1 = box
    c = max(2, min(chamfer, (x1 - x0) // 4, (y1 - y0) // 4))
    poly = [
        (x0 + c, y0), (x1 - c, y0), (x1, y0 + c),
        (x1, y1 - c), (x1 - c, y1), (x0 + c, y1),
        (x0, y1 - c), (x0, y0 + c),
    ]
    fd.polygon(poly, fill=fill_col, outline=border_col)

    bracket = max(8, c + 6)
    tl = [(x0, y0 + bracket), (x0, y0 + c), (x0 + c, y0), (x0 + bracket, y0)]
    br = [(x1 - bracket, y1), (x1 - c, y1), (x1, y1 - c), (x1, y1 - bracket)]
    fd.line(tl, fill=accent_col, width=2)
    fd.line(br, fill=accent_col, width=2)
    gd.line(tl, fill=accent_col, width=2)
    gd.line(br, fill=accent_col, width=2)


def _sample_torus(R: float, r: float, nu: int, nv: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample points, unit normals, and parameter phase u/(2pi) on a 3D torus."""
    u = np.linspace(0.0, 2.0 * math.pi, nu, endpoint=False, dtype=np.float32)
    v = np.linspace(0.0, 2.0 * math.pi, nv, endpoint=False, dtype=np.float32)
    uu, vv = np.meshgrid(u, v, indexing="ij")
    cu, su = np.cos(uu), np.sin(uu)
    cv, sv = np.cos(vv), np.sin(vv)
    ring = R + r * cv
    pts = np.stack([ring * cu, ring * su, r * sv], axis=-1).reshape(-1, 3)
    nrm = np.stack([cv * cu, cv * su, sv], axis=-1).reshape(-1, 3)
    phase = (uu / (2.0 * math.pi)).reshape(-1)
    return pts, nrm, phase


def _sample_sphere(r: float, nu: int, nv: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample points, unit normals, and normalized angle on a 3D sphere."""
    u = np.linspace(0.0, 2.0 * math.pi, nu, endpoint=False, dtype=np.float32)
    v = np.linspace(-0.48 * math.pi, 0.48 * math.pi, nv, dtype=np.float32)
    uu, vv = np.meshgrid(u, v, indexing="ij")
    cv, sv = np.cos(vv), np.sin(vv)
    cu, su = np.cos(uu), np.sin(uu)
    nx, ny, nz = cv * cu, cv * su, sv
    nrm = np.stack([nx, ny, nz], axis=-1).reshape(-1, 3)
    pts = nrm * r
    phase = (uu / (2.0 * math.pi)).reshape(-1)
    return pts, nrm, phase


def _sample_trefoil(scale_c: float = 0.34, r_tube: float = 0.20, nu: int = 128, nv: int = 24) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample a 3D tubular trefoil neural knot using Frenet/Bishop frames."""
    u = np.linspace(0.0, 2.0 * math.pi, nu, endpoint=False, dtype=np.float32)
    cx = (np.sin(u) + 2.0 * np.sin(2.0 * u)) * scale_c
    cy = (np.cos(u) - 2.0 * np.cos(2.0 * u)) * scale_c
    cz = (-np.sin(3.0 * u)) * scale_c
    tx = (np.cos(u) + 4.0 * np.cos(2.0 * u)) * scale_c
    ty = (-np.sin(u) + 4.0 * np.sin(2.0 * u)) * scale_c
    tz = (-3.0 * np.cos(3.0 * u)) * scale_c

    T = np.stack([tx, ty, tz], axis=-1)
    T = T / np.maximum(1e-5, np.linalg.norm(T, axis=1, keepdims=True))
    up = np.array([0.0, 0.0, 1.0], dtype=np.float32)[None, :]
    B = np.cross(T, up)
    B_norm = np.linalg.norm(B, axis=1, keepdims=True)
    # Guard nearly vertical tangent
    alt = np.array([1.0, 0.0, 0.0], dtype=np.float32)[None, :]
    B = np.where(B_norm < 1e-3, np.cross(T, alt), B)
    B = B / np.maximum(1e-5, np.linalg.norm(B, axis=1, keepdims=True))
    N = np.cross(B, T)

    v = np.linspace(0.0, 2.0 * math.pi, nv, endpoint=False, dtype=np.float32)
    cv = np.cos(v)[None, :, None]
    sv = np.sin(v)[None, :, None]
    nrm = N[:, None, :] * cv + B[:, None, :] * sv
    ctr = np.stack([cx, cy, cz], axis=-1)[:, None, :]
    pts = ctr + r_tube * nrm
    phase = np.broadcast_to((u / (2.0 * math.pi))[:, None], (nu, nv)).reshape(-1)
    return pts.reshape(-1, 3), nrm.reshape(-1, 3), phase


def _build_rot_matrix(ax: float, ay: float, az: float) -> np.ndarray:
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]], dtype=np.float32)
    ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]], dtype=np.float32)
    rz = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]], dtype=np.float32)
    return rz @ ry @ rx


_SCULPTURE_CACHE: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}


def _get_sculpture_mesh(shape: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if shape not in _SCULPTURE_CACHE:
        if shape == "gyro":
            p1, n1, ph1 = _sample_torus(1.08, 0.22, 92, 24)
            # Second ring perpendicular (rotated 90 deg around X)
            p2 = np.stack([p1[:, 0], -p1[:, 2], p1[:, 1]], axis=-1)
            n2 = np.stack([n1[:, 0], -n1[:, 2], n1[:, 1]], axis=-1)
            p3, n3, ph3 = _sample_sphere(0.40, 40, 22)
            pts = np.concatenate([p1, p2, p3], axis=0)
            nrm = np.concatenate([n1, n2, n3], axis=0)
            ph = np.concatenate([ph1, (ph1 + 0.33) % 1.0, (ph3 + 0.66) % 1.0], axis=0)
            _SCULPTURE_CACHE[shape] = (pts, nrm, ph)
        elif shape == "trefoil":
            _SCULPTURE_CACHE[shape] = _sample_trefoil(scale_c=0.34, r_tube=0.20, nu=128, nv=24)
        else:
            _SCULPTURE_CACHE[shape] = _sample_torus(0.95, 0.44, 108, 38)
    return _SCULPTURE_CACHE[shape]


def render_3d_ascii_sculpture(
    fd: ImageDraw.ImageDraw,
    gd: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    scale: float,
    dx: int,
    dy: int,
    shape: str,
    ang_x: float,
    ang_y: float,
    ang_z: float,
    palette: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    font,
) -> None:
    """Vectorized NumPy 3D Z-buffered parametric ASCII surface renderer with bloom highlights."""
    pts, nrm, phase = _get_sculpture_mesh(shape)
    rot = _build_rot_matrix(ang_x, ang_y, ang_z)
    p_rot = pts @ rot.T
    n_rot = nrm @ rot.T

    # Camera looks along +Z toward origin from z = +3.6
    inv_z = 1.0 / (3.6 - p_rot[:, 2])
    cols = np.rint((cx + p_rot[:, 0] * scale * inv_z) / dx).astype(np.int32)
    rows = np.rint((cy + p_rot[:, 1] * scale * inv_z) / dy).astype(np.int32)

    # Lambertian diffuse + Phong specular term with readable rim floor
    ndotl = np.clip(n_rot @ _LIGHT_DIR, 0.0, 1.0)
    spec = np.power(np.clip(n_rot[:, 2] * 0.55 + ndotl * 0.45, 0.0, 1.0), 6.0)
    lum = np.clip(0.26 + 0.64 * ndotl + 0.30 * spec, 0.0, 1.0)

    # Keep only frontmost sample per cell using a compact lexsort Z-buffer
    z_vals = p_rot[:, 2]
    order = np.argsort(z_vals)  # back-to-front so later writes win cleanly
    c0 = np.array(palette[0], dtype=np.float32)
    c1 = np.array(palette[1], dtype=np.float32)
    c2 = np.array(palette[2], dtype=np.float32)

    cells: dict[tuple[int, int], tuple[float, float]] = {}
    for idx in order:
        col = int(cols[idx])
        row = int(rows[idx])
        if col < 2 or row < 3:
            continue
        cells[(col, row)] = (float(lum[idx]), float(phase[idx]))

    ramp_max = len(SHADE_RAMP) - 1
    for (col, row), (lv, phv) in cells.items():
        ch = SHADE_RAMP[max(1, min(ramp_max, int(lv * ramp_max)))]
        blend = 0.5 + 0.5 * math.sin(2.0 * math.pi * phv + ang_y)
        mid_col = c0 * (1.0 - blend) + c1 * blend
        final_col = mid_col * (0.42 + 0.58 * lv) + c2 * max(0.0, (lv - 0.58) * 1.45)
        rgb = (
            min(255, max(0, int(final_col[0]))),
            min(255, max(0, int(final_col[1]))),
            min(255, max(0, int(final_col[2]))),
        )
        px, py = col * dx, row * dy
        fd.text((px, py), ch, fill=rgb, font=font)
        if lv > 0.32:
            gd.text((px, py), ch, fill=rgb, font=font)


def draw_bezier_energy_arc(
    fd: ImageDraw.ImageDraw,
    gd: ImageDraw.ImageDraw,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    phase: float,
    col_track: tuple[int, int, int],
    col_pkt: tuple[int, int, int],
    col_ack: tuple[int, int, int],
    font,
) -> None:
    """Draw a curved Bezier conduit with bidirectional animated energy pulses."""
    for i in range(21):
        u = i / 20.0
        om = 1.0 - u
        x = om * om * p0[0] + 2.0 * om * u * p1[0] + u * u * p2[0]
        y = om * om * p0[1] + 2.0 * om * u * p1[1] + u * u * p2[1]
        fd.text((int(x), int(y)), "." if i % 2 == 0 else "·", fill=col_track, font=font)

    if phase < 0.48:
        u_head = phase / 0.48
        glyphs, pcol, dir_sign = ("@", "#", "*"), col_pkt, -1.0
    elif phase < 0.94:
        u_head = 1.0 - (phase - 0.48) / 0.46
        glyphs, pcol, dir_sign = ("<", "@", "#"), col_ack, 1.0
    else:
        return

    for k, ch in enumerate(glyphs):
        u = max(0.0, min(1.0, u_head + dir_sign * k * 0.045))
        om = 1.0 - u
        x = om * om * p0[0] + 2.0 * om * u * p1[0] + u * u * p2[0]
        y = om * om * p0[1] + 2.0 * om * u * p1[1] + u * u * p2[1]
        c_draw = pcol if k == 0 else (max(40, int(pcol[0] * 0.78)), max(40, int(pcol[1] * 0.78)), max(40, int(pcol[2] * 0.78)))
        fd.text((int(x) - 2, int(y) - 3), ch, fill=c_draw, font=font)
        gd.text((int(x) - 2, int(y) - 3), ch, fill=c_draw, font=font)


def gen_sdd_tile(fonts: dict) -> tuple[Image.Image, list[Image.Image]]:
    """480x200 tile: 3D Gyro Spec Core + curved conduits + 3 dark-glass Agent Cards."""
    W, H, N = 480, 200, 72
    amb_img, base_fg, base_gl = build_ambient_city_layer(
        W, H, 4, 29, fonts["tiny"], nc_idx=1, crop_box=(0, 20, 1280, 550),
        tint_rgb=(0.45, 0.90, 1.10), underlay_strength=0.26, gain_scale=0.38,
    )
    backdrop = build_hud_backdrop(
        W, H, header_y=21, footer_y=173, accent=(0, 245, 233),
        underlay_img=amb_img, underlay_strength=0.25,
    )

    rng = np.random.default_rng(202)
    sp_x = rng.uniform(12, W - 18, 28)
    sp_y = rng.uniform(26, 168, 28)
    sp_p = rng.uniform(0.0, 1.0, 28)
    sp_ch = rng.choice(["*", "+", "·", "0", "1"], size=28)
    sp_cols = ((0, 245, 233), (255, 216, 77), (255, 65, 145))

    agents = (
        ("A1 // ARCH", (255, 216, 77), "PLAN", "SCHEMA", (252, 48), (195, 52), 0.00),
        ("A2 // CODE", (255, 65, 145), "BUILD", "RUST/TS", (252, 95), (195, 92), 0.16),
        ("A3 // TEST", (98, 255, 203), "PASS", "VERIFY", (252, 142), (195, 132), 0.32),
    )
    card_ys = (29, 76, 123)

    frames = []
    for f in range(N):
        t = f / N
        tau = 2.0 * math.pi * t
        fg = Image.new("RGB", (W, H), (0, 0, 0))
        gl = Image.new("RGB", (W, H), (0, 0, 0))
        fd, gd = ImageDraw.Draw(fg), ImageDraw.Draw(gl)

        # Perspective receding cyber-floor & drifting cyber-sparks
        draw_perspective_grid(fd, gd, W, H, 126, 171, (t * 2.0) % 1.0, (14, 52, 68), (0, 130, 142))
        for k in range(len(sp_x)):
            px = int((sp_x[k] + 10.0 * math.sin(tau + k)) % (W - 20)) + 8
            py = int(26 + ((sp_y[k] - 26 - 38.0 * ((t + sp_p[k]) % 1.0)) % 140))
            if px > 246 and 28 <= py <= 165:
                continue
            scol = sp_cols[k % 3]
            fd.text((px, py), str(sp_ch[k]), fill=scol, font=fonts["tiny"])
            if k % 2 == 0:
                gd.text((px, py), str(sp_ch[k]), fill=scol, font=fonts["tiny"])

        # Left Hero: 3D Rotating ASCII Gyro Spec Core + Pill
        render_3d_ascii_sculpture(
            fd, gd, 88.0, 88.0, 112.0, 4, 6, "gyro",
            tau, tau * 2.0, 0.35, ((24, 140, 185), (0, 245, 233), (255, 224, 110)), fonts["tiny"],
        )
        draw_cyber_panel(fd, gd, (28, 148, 148, 166), (26, 92, 114), (0, 245, 233), fill_col=(5, 16, 28), chamfer=4)
        fd.text((40, 152), "SPEC.MD // CORE", fill=(215, 255, 250), font=fonts["hud"])
        gd.text((40, 152), "SPEC.MD // CORE", fill=(0, 245, 233), font=fonts["hud"])

        # Bezier Energy Arcs + Sleek Frosted Agent Cards
        for idx, ((aname, acol, act_tag, micro, p2, p1, stag), cy0) in enumerate(zip(agents, card_ys)):
            phase = (t + stag) % 1.0
            draw_bezier_energy_arc(
                fd, gd, (142.0, 88.0), p1, p2, phase,
                (26, 76, 96), acol, (98, 255, 203), fonts["tiny"],
            )

            cy1 = cy0 + 39
            draw_cyber_panel(fd, gd, (254, cy0, 468, cy1), (28, 82, 104), acol, fill_col=(6, 15, 26), chamfer=5)
            led_on = 0.5 + 0.5 * math.sin(tau * 3.0 + idx * 1.9)
            lcol = (int(acol[0] * (0.45 + 0.55 * led_on)), int(acol[1] * (0.45 + 0.55 * led_on)), int(acol[2] * (0.45 + 0.55 * led_on)))
            fd.ellipse([264, cy0 + 10, 270, cy0 + 16], fill=lcol)
            gd.ellipse([264, cy0 + 10, 270, cy0 + 16], fill=lcol)
            fd.text((276, cy0 + 7), aname, fill=(235, 252, 255), font=fonts["hud"])

            verified_burst = phase >= 0.62 and phase <= 0.92
            badge_txt = "[ OK  ]" if verified_burst else f"[{act_tag:<4}]"
            badge_col = (110, 255, 212) if verified_burst else acol
            fd.text((414, cy0 + 7), badge_txt, fill=badge_col, font=fonts["hud"])
            gd.text((414, cy0 + 7), badge_txt, fill=badge_col, font=fonts["hud"])

            # Animated 12-char wave progress bar
            filled = 3 + int(9 * (0.5 + 0.5 * math.sin(tau * 2.0 - idx * 1.1)))
            bar = "#" * filled + "." * (12 - filled)
            fd.text((264, cy0 + 23), bar, fill=acol, font=fonts["small"])
            if filled >= 9:
                gd.text((264, cy0 + 23), bar, fill=acol, font=fonts["small"])
            status_lbl = "SYNC OK" if verified_burst else micro
            fd.text((346, cy0 + 22), status_lbl, fill=(140, 218, 228) if not verified_burst else (120, 255, 212), font=fonts["hud"])

        # Header & Footer Chrome
        h_led = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(tau * 4.0))
        fd.ellipse([12, 7, 18, 13], fill=(0, int(245 * h_led), int(233 * h_led)))
        gd.ellipse([12, 7, 18, 13], fill=(0, int(245 * h_led), int(233 * h_led)))
        fd.text((24, 5), "SDD-TEMPLATE // SPEC ENGINE", fill=(164, 248, 244), font=fonts["hud"])
        fd.text((W - 88, 5), "[REPO ->]", fill=(255, 216, 77), font=fonts["hud"])
        fd.text((14, 179), "> Orquestacion multi-agente guiada por especificacion", fill=(175, 236, 240), font=fonts["hud"])

        frames.append(compose_bloom(backdrop, fg, gl, base_fg=base_fg, base_glow=base_gl))

    save_animated_webp(frames, ASSETS_DIR / "ascii-sdd.webp", FPS_MS, max_bytes=900_000)
    return frames[48], [frames[6], frames[30], frames[54]]


def gen_loki_tile(fonts: dict) -> tuple[Image.Image, list[Image.Image]]:
    """480x200 tile: 3D Neural Trefoil Core + Matrix Rain + Live Cyber-IDE Rust Patch."""
    W, H, N = 480, 200, 72
    amb_img, base_fg, base_gl = build_ambient_city_layer(
        W, H, 4, 29, fonts["tiny"], nc_idx=2, crop_box=(0, 30, 1280, 560),
        tint_rgb=(0.35, 1.05, 0.90), underlay_strength=0.25, gain_scale=0.36,
    )
    backdrop = build_hud_backdrop(
        W, H, header_y=21, footer_y=173, accent=(98, 255, 203),
        underlay_img=amb_img, underlay_strength=0.24,
    )

    rng = np.random.default_rng(404)
    m_cols = rng.integers(14, 196, 24)
    m_r0 = rng.uniform(24, 165, 24)
    m_spd = rng.choice([70.0, 105.0], size=24)
    orb_x = rng.uniform(46, 152, 18)
    orb_p = rng.uniform(0.0, 1.0, 18)

    frames = []
    for f in range(N):
        t = f / N
        tau = 2.0 * math.pi * t
        fg = Image.new("RGB", (W, H), (0, 0, 0))
        gl = Image.new("RGB", (W, H), (0, 0, 0))
        fd, gd = ImageDraw.Draw(fg), ImageDraw.Draw(gl)

        # Left Matrix Rain (x=12..196)
        for k in range(len(m_cols)):
            mx = int(m_cols[k])
            head_y = 24.0 + ((m_r0[k] - 24.0 + m_spd[k] * t) % 140.0)
            for seg in range(4):
                sy = int(24 + ((head_y - 24 - seg * 7) % 140))
                ch = RAIN_CHARS[(k + seg + f // 2) % len(RAIN_CHARS)]
                col_m = (165, 255, 224) if seg == 0 else (20, int(140 * (1 - seg / 4.2)), int(125 * (1 - seg / 4.2)))
                fd.text((mx, sy), ch, fill=col_m, font=fonts["tiny"])
                if seg == 0:
                    gd.text((mx, sy), ch, fill=(98, 255, 203), font=fonts["tiny"])

        # Glowing Holo-Emitter Rings + Rising Motes under Left Core
        fd.arc([40, 136, 156, 156], 0, 360, fill=(22, 115, 118), width=1)
        fd.arc([62, 140, 134, 152], 0, 360, fill=(98, 255, 203), width=1)
        gd.arc([62, 140, 134, 152], 0, 360, fill=(0, 245, 233), width=1)
        for k in range(len(orb_x)):
            prog = (t + orb_p[k]) % 1.0
            ox = int(orb_x[k] + 4.0 * math.sin(tau * 2.0 + k))
            oy = int(144 - prog * 96)
            fd.text((ox, oy), "*" if k % 2 == 0 else "+", fill=(98, 255, 203), font=fonts["tiny"])
            if prog > 0.25:
                gd.text((ox, oy), "*", fill=(0, 245, 233), font=fonts["tiny"])

        # Left Hero: 3D Trefoil Neural Core + Pill
        bob = 3.0 * math.sin(tau * 2.0)
        render_3d_ascii_sculpture(
            fd, gd, 98.0, 84.0 + bob, 116.0, 4, 6, "trefoil",
            tau * 0.5 + 0.4, tau, 0.25, ((18, 165, 135), (0, 245, 233), (255, 224, 110)), fonts["tiny"],
        )
        draw_cyber_panel(fd, gd, (22, 150, 176, 167), (26, 98, 102), (98, 255, 203), fill_col=(5, 16, 26), chamfer=4)
        fd.text((34, 154), "OLLAMA // NEURAL CORE", fill=(185, 255, 236), font=fonts["hud"])
        gd.text((34, 154), "OLLAMA // NEURAL CORE", fill=(98, 255, 203), font=fonts["hud"])

        # Curved Synapse Beam into IDE left edge (with golden surge during patch phase)
        if t < 0.36:
            beam_col, beam_spd = (0, 245, 233), 1.4
        elif t < 0.58:
            beam_col, beam_spd = (255, 216, 77), 3.0
        else:
            beam_col, beam_spd = (98, 255, 203), 1.6
        draw_bezier_energy_arc(
            fd, gd, (142.0, 88.0), (174.0, 68.0), (205.0, 88.0),
            (t * beam_spd) % 1.0, (42, 132, 142), beam_col, (98, 255, 203), fonts["tiny"],
        )

        # Right Cyber-IDE Panel (x0=206..468, y0=30..164)
        ide_accent = (255, 78, 130) if t < 0.36 else ((255, 216, 77) if t < 0.58 else (98, 255, 203))
        draw_cyber_panel(fd, gd, (206, 30, 468, 164), (30, 92, 106), ide_accent, fill_col=(6, 15, 26), chamfer=6)

        # Mini IDE title bar + LEDs
        fd.ellipse([216, 39, 222, 45], fill=(255, 65, 145))
        fd.ellipse([226, 39, 232, 45], fill=(255, 216, 77))
        fd.ellipse([236, 39, 242, 45], fill=(98, 255, 203))
        fd.text((250, 37), "cargo test · loki.rs", fill=(154, 228, 236), font=fonts["hud"])
        fd.line([(212, 51), (462, 51)], fill=(22, 66, 82), width=1)

        fd.text((218, 57), "$ cargo test --quiet", fill=(150, 235, 248), font=fonts["hud"])
        fd.text((218, 73), "fn add() -> i32 { 2 + 2 }", fill=(215, 245, 255), font=fonts["hud"])

        if t < 0.36:
            # Phase 1: Failing test
            fd.text((218, 90), "assert_eq!(add(), 5);", fill=(255, 78, 130), font=fonts["hud"])
            gd.text((218, 90), "assert_eq!(add(), 5);", fill=(255, 65, 118), font=fonts["hud"])
            if (f // 4) % 2 == 0:
                fd.line([(326, 103), (344, 103)], fill=(255, 65, 118), width=2)
            fd.rectangle([218, 110, 454, 130], fill=(44, 14, 28), outline=(255, 65, 118))
            fd.text((226, 114), "[FAIL] expected 5, got 4", fill=(255, 142, 174), font=fonts["hud"])
            gd.text((226, 114), "[FAIL] expected 5, got 4", fill=(255, 65, 118), font=fonts["hud"])
            fd.text((218, 139), "> loki: analizando AST...", fill=(154, 218, 226), font=fonts["hud"])
        elif t < 0.58:
            # Phase 2: Golden Ollama AI patch
            fd.text((218, 90), "assert_eq!(add(), 4);", fill=(255, 224, 95), font=fonts["hud"])
            gd.text((218, 90), "assert_eq!(add(), 4);", fill=(255, 216, 77), font=fonts["hud"])
            for sx, sy in ((334, 83), (348, 91), (330, 99)):
                fd.text((sx, sy), "*", fill=(255, 232, 130), font=fonts["tiny"])
                gd.text((sx, sy), "*", fill=(255, 216, 77), font=fonts["tiny"])
            fd.rectangle([218, 110, 454, 130], fill=(42, 32, 12), outline=(255, 216, 77))
            fd.text((226, 114), "[OLLAMA] patch -> 4", fill=(255, 234, 140), font=fonts["hud"])
            gd.text((226, 114), "[OLLAMA] patch -> 4", fill=(255, 216, 77), font=fonts["hud"])
            prog_n = max(2, min(12, int(((t - 0.36) / 0.22) * 12) + 1))
            fd.text((218, 139), f"[{'#' * prog_n}{'.' * (12 - prog_n)}] AI FIX", fill=(255, 224, 110), font=fonts["hud"])
        else:
            # Phase 3: Verified Pass
            fd.text((218, 90), "assert_eq!(add(), 4);", fill=(120, 255, 212), font=fonts["hud"])
            gd.text((218, 90), "assert_eq!(add(), 4);", fill=(98, 255, 203), font=fonts["hud"])
            fd.rectangle([218, 110, 454, 130], fill=(10, 40, 36), outline=(98, 255, 203))
            fd.text((226, 114), "[PASS] 1 passed · 0.01s", fill=(160, 255, 224), font=fonts["hud"])
            gd.text((226, 114), "[PASS] 1 passed · 0.01s", fill=(98, 255, 203), font=fonts["hud"])
            fd.text((218, 139), "> OK · verificado en local", fill=(142, 255, 218), font=fonts["hud"])
            for sp_i in range(3):
                sx = 398 + sp_i * 18
                sy = 144 - int(((t - 0.58) * 32 + sp_i * 5) % 14)
                fd.text((sx, sy), "+", fill=(142, 255, 218), font=fonts["tiny"])
                gd.text((sx, sy), "+", fill=(98, 255, 203), font=fonts["tiny"])

        h_led = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(tau * 4.0))
        fd.ellipse([12, 7, 18, 13], fill=(int(98 * h_led), int(255 * h_led), int(203 * h_led)))
        gd.ellipse([12, 7, 18, 13], fill=(int(98 * h_led), int(255 * h_led), int(203 * h_led)))
        fd.text((24, 5), "LOKI CODE GUIDE // OLLAMA", fill=(164, 248, 244), font=fonts["hud"])
        fd.text((W - 88, 5), "[REPO ->]", fill=(98, 255, 203), font=fonts["hud"])
        fd.text((14, 179), "> Tutor local en Rust e IA que corrige pruebas", fill=(175, 236, 240), font=fonts["hud"])

        frames.append(compose_bloom(backdrop, fg, gl, base_fg=base_fg, base_glow=base_gl))

    save_animated_webp(frames, ASSETS_DIR / "ascii-loki.webp", FPS_MS, max_bytes=900_000)
    return frames[48], [frames[12], frames[34], frames[56]]


def gen_repos_tile(fonts: dict) -> tuple[Image.Image, list[Image.Image]]:
    """480x150 tile: 3D Illuminated ASCII Torus + Animated Repository Matrix Console."""
    W, H, N = 480, 150, 60
    amb_img, base_fg, base_gl = build_ambient_city_layer(
        W, H, 4, 24, fonts["tiny"], nc_idx=0, crop_box=(0, 60, 1280, 460),
        tint_rgb=(0.95, 0.72, 0.85), underlay_strength=0.24, gain_scale=0.38,
    )
    backdrop = build_hud_backdrop(
        W, H, header_y=21, footer_y=None, accent=(255, 216, 77),
        underlay_img=amb_img, underlay_strength=0.22,
    )

    rng = np.random.default_rng(505)
    sp_x = rng.uniform(10, 148, 22)
    sp_y = rng.uniform(26, 142, 22)
    sp_p = rng.uniform(0.0, 1.0, 22)
    sp_ch = rng.choice(["+", "*", "·", "0", "1"], size=22)
    sp_cols = ((255, 216, 77), (0, 245, 233), (255, 65, 145))

    rows_meta = (
        ("sdd-template", "[AI SPEC]", (255, 216, 77)),
        ("Loki-code-guide", "[OLLAMA ]", (98, 255, 203)),
        ("atlantis-os", "[GIS 3D ]", (0, 245, 233)),
        ("arcadia-urano", "[RUST 3D]", (255, 192, 110)),
        ("fraud-detection", "[TOKIO  ]", (255, 65, 145)),
    )

    frames = []
    for f in range(N):
        t = f / N
        tau = 2.0 * math.pi * t
        fg = Image.new("RGB", (W, H), (0, 0, 0))
        gl = Image.new("RGB", (W, H), (0, 0, 0))
        fd, gd = ImageDraw.Draw(fg), ImageDraw.Draw(gl)

        # Warm cyber perspective floor grid + floating ASCII dust
        draw_perspective_grid(fd, gd, W, H, 102, 146, (t * 2.0) % 1.0, (54, 42, 58), (165, 128, 52))
        for k in range(len(sp_x)):
            px = int(sp_x[k] + 5.0 * math.sin(tau + k))
            py = int(26 + ((sp_y[k] - 26 - 30.0 * ((t + sp_p[k]) % 1.0)) % 116))
            scol = sp_cols[k % 3]
            fd.text((px, py), str(sp_ch[k]), fill=scol, font=fonts["tiny"])
            if k % 2 == 0:
                gd.text((px, py), str(sp_ch[k]), fill=scol, font=fonts["tiny"])

        # Left Hero: 3D Shaded ASCII Torus + Orbiting Stars
        render_3d_ascii_sculpture(
            fd, gd, 78.0, 83.0, 102.0, 4, 6, "torus",
            0.72 + 0.42 * math.sin(tau), tau, 0.28, ((255, 65, 145), (0, 245, 233), (255, 224, 110)), fonts["tiny"],
        )
        for pk in range(6):
            ang = tau * 2.0 + pk * (2.0 * math.pi / 6.0)
            ox = int(78 + 46 * math.cos(ang))
            oy = int(83 + 42 * math.sin(ang))
            if 26 <= oy <= 140:
                pcol = sp_cols[pk % 3]
                pch = "*" if pk % 2 == 0 else "+"
                fd.text((ox, oy), pch, fill=pcol, font=fonts["tiny"])
                gd.text((ox, oy), pch, fill=pcol, font=fonts["tiny"])

        # Right Frosted Dark-Glass Repository Matrix Console
        draw_cyber_panel(fd, gd, (154, 28, 468, 142), (32, 92, 114), (255, 216, 77), fill_col=(6, 15, 26), chamfer=6)

        active_idx = (f // 12) % len(rows_meta)
        for ri, (rname, rtag, tcol) in enumerate(rows_meta):
            ry = 35 + ri * 18
            if ri == active_idx:
                fd.rectangle([160, ry - 2, 462, ry + 13], fill=(14, 50, 68), outline=(0, 215, 220))
                fd.rectangle([160, ry - 2, 163, ry + 13], fill=(0, 245, 233))
                gd.rectangle([160, ry - 2, 163, ry + 13], fill=(0, 245, 233))
                fd.text((170, ry), f"> {rname}", fill=(225, 255, 252), font=fonts["hud"])
                fd.text((314, ry), ":: LIVE", fill=(0, 245, 233), font=fonts["hud"])
                fd.text((392, ry), rtag, fill=tcol, font=fonts["hud"])
                gd.text((170, ry), f"> {rname}", fill=(0, 245, 233), font=fonts["hud"])
                gd.text((392, ry), rtag, fill=tcol, font=fonts["hud"])
            else:
                fd.text((170, ry), f"  {rname}", fill=(128, 194, 212), font=fonts["hud"])
                fd.text((392, ry), rtag, fill=(84, 140, 160), font=fonts["hud"])

        fd.text((170, 125), ">> EXPLORAR TODOS LOS REPOS ->", fill=(255, 222, 110), font=fonts["hud"])
        gd.text((170, 125), ">> EXPLORAR TODOS LOS REPOS ->", fill=(255, 200, 72), font=fonts["hud"])

        h_led = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(tau * 4.0))
        fd.ellipse([12, 7, 18, 13], fill=(int(255 * h_led), int(216 * h_led), int(77 * h_led)))
        gd.ellipse([12, 7, 18, 13], fill=(int(255 * h_led), int(216 * h_led), int(77 * h_led)))
        fd.text((24, 5), "REPOSITORIOS // HALUZ", fill=(255, 224, 135), font=fonts["hud"])
        fd.text((W - 88, 5), "[TODOS ->]", fill=(0, 245, 233), font=fonts["hud"])

        frames.append(compose_bloom(backdrop, fg, gl, base_fg=base_fg, base_glow=base_gl))

    save_animated_webp(frames, ASSETS_DIR / "ascii-repos.webp", FPS_MS, max_bytes=800_000)
    return frames[10], [frames[4], frames[24], frames[48]]


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


def generate_all(preview_dir: Path | None = None, only: set[str] | None = None) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    targets = only or {"hero", "sdd", "loki", "repos", "linkedin"}
    fonts = {
        "tiny": load_mono_font(7),
        "small": load_mono_font(8),
        "hud": load_mono_font(10),
        "title": load_mono_font(18),
    }

    hero_diag = None
    if "hero" in targets:
        _, hero_diag = gen_hero_sequence(fonts)
    sdd_diag = gen_sdd_tile(fonts)[1] if "sdd" in targets else None
    loki_diag = gen_loki_tile(fonts)[1] if "loki" in targets else None
    rep_diag = gen_repos_tile(fonts)[1] if "repos" in targets else None
    if "linkedin" in targets:
        gen_linkedin_tile(fonts)

    if preview_dir is not None:
        preview_dir.mkdir(parents=True, exist_ok=True)
        if hero_diag is not None:
            sh = Image.new("RGB", (960 * 2, 270 * 3), (3, 7, 17))
            for i, im in enumerate(hero_diag[:6]):
                sh.paste(im, ((i % 2) * 960, (i // 2) * 270))
            sh.save(preview_dir / "preview_dash_hero.png")
            print(f"Saved preview_dash_hero.png in {preview_dir}")

        if sdd_diag and loki_diag and rep_diag:
            st = Image.new("RGB", (480 * 3 + 16, 200 + 200 + 150 + 16), (3, 7, 17))
            for ci, im in enumerate(sdd_diag[:3]):
                st.paste(im, (ci * 484, 0))
            for ci, im in enumerate(loki_diag[:3]):
                st.paste(im, (ci * 484, 204))
            for ci, im in enumerate(rep_diag[:3]):
                st.paste(im, (ci * 484, 408))
            st.save(preview_dir / "preview_3tiles_v2.png")
            print(f"Saved preview_3tiles_v2.png in {preview_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the Night City Interactive ASCII Dashboard WebPs.")
    parser.add_argument("--preview-dir", type=Path, default=None, help="Optional folder for diagnostic PNG sheets.")
    parser.add_argument(
        "--only",
        type=str,
        default="hero,sdd,loki,repos,linkedin",
        help="Comma-separated subset from {hero,sdd,loki,repos,linkedin}.",
    )
    args = parser.parse_args()
    only_set = {tok.strip().lower() for tok in args.only.split(",") if tok.strip()}
    generate_all(args.preview_dir, only=only_set)
