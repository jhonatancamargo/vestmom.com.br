"""Gera imagem PNG para upar no painel do VTurb como Resume Modal.

Output: 1920x1080 (cobre player full HD).
Copy: loss aversion sem mostrar tempo do video.
"""
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT.parent.parent / "vsl-v3a-tts" / "fonts"
OUT_DIR = ROOT / "assets" / "img"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_BLACK = str(FONTS / "Montserrat-Black.ttf")
FONT_BOLD = str(FONTS / "Montserrat-Bold.ttf")
FONT_EXTRA = str(FONTS / "Montserrat-ExtraBold.ttf")

# Paleta — combina com o design system da pagina V3-PREVIEW
BRAND = (255, 132, 4)       # laranja
BRAND_HOVER = (255, 106, 0)
SURFACE_DARK = (11, 26, 44)
SURFACE_DARK_2 = (17, 39, 64)
WHITE = (255, 255, 255)
INK_ON_DARK_2 = (184, 197, 214)
DANGER = (220, 38, 38)
DANGER_SOFT_BG = (60, 12, 12)  # fundo do loss block

W, H = 1920, 1080


def gradient_bg(size, c1, c2, vertical=True):
    img = Image.new("RGB", size, c1)
    draw = ImageDraw.Draw(img)
    w, h = size
    n = h if vertical else w
    for i in range(n):
        t = i / n
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        if vertical:
            draw.line([(0, i), (w, i)], fill=(r, g, b))
        else:
            draw.line([(i, 0), (i, h)], fill=(r, g, b))
    return img


def add_radial_glow(img, center, color, intensity=0.4, radius=None):
    w, h = img.size
    cx, cy = center
    if radius is None:
        radius = max(w, h)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    n_steps = 25
    for i in range(n_steps, 0, -1):
        r = int(radius * i / n_steps)
        alpha = int(255 * intensity * (1 - i / n_steps) ** 2)
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)],
                     fill=(*color, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def add_grain(img, intensity=8):
    pixels = img.load()
    w, h = img.size
    rng = random.Random(42)
    for _ in range(w * h // 80):
        x, y = rng.randint(0, w - 1), rng.randint(0, h - 1)
        r, g, b = pixels[x, y]
        n = rng.randint(-intensity, intensity)
        pixels[x, y] = (
            max(0, min(255, r + n)),
            max(0, min(255, g + n)),
            max(0, min(255, b + n)),
        )
    return img


def add_vignette(img, intensity=0.5):
    w, h = img.size
    overlay = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(overlay)
    draw.ellipse(
        [(-w // 4, -h // 4), (w + w // 4, h + h // 4)],
        fill=255,
    )
    mask = overlay.filter(ImageFilter.GaussianBlur(radius=80))
    inv = mask.point(lambda p: 255 - p)
    dark = Image.new("RGBA", (w, h), (0, 0, 0, int(255 * intensity)))
    base = img.convert("RGBA")
    return Image.composite(base, Image.alpha_composite(base, dark), mask).convert("RGB")


def draw_lightning(draw, cx, cy, height, color=BRAND, outline=WHITE):
    """Desenha um raio estilizado centrado em (cx, cy) com altura dada."""
    s = height / 100.0
    pts_norm = [
        (15, 0),   # topo direito
        (-30, 55),
        (5, 55),
        (-15, 100),
        (35, 40),
        (0, 40),
        (25, 0),
    ]
    points = [(cx + x * s, cy + y * s - height / 2) for x, y in pts_norm]
    draw.polygon(points, fill=color, outline=outline)


def draw_text_shadow(draw, pos, text, font, fill, shadow=(0, 0, 0), shadow_offset=3, blur=False):
    x, y = pos
    for dx in range(-shadow_offset, shadow_offset + 1, 2):
        for dy in range(-shadow_offset, shadow_offset + 1, 2):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, fill=shadow, font=font)
    draw.text((x, y), text, fill=fill, font=font)


def center_x(draw, text, font):
    b = draw.textbbox((0, 0), text, font=font)
    return (W - (b[2] - b[0])) // 2


def render_resume(out_path: Path):
    # Background gradiente dark
    img = gradient_bg((W, H), SURFACE_DARK_2, SURFACE_DARK, vertical=True)

    # Glow radial laranja no centro
    img = add_radial_glow(img, (W // 2, H // 2 - 100), BRAND, intensity=0.18, radius=900)

    # Vinheta
    img = add_vignette(img, intensity=0.55)

    # Granulado
    img = add_grain(img, intensity=7)

    # Layer com texto
    draw = ImageDraw.Draw(img)

    # === Raio ⚡ no topo ===
    draw_lightning(draw, W // 2, 200, 130, color=BRAND, outline=WHITE)

    # === Título "Espera!" GIGANTE ===
    font_h1 = ImageFont.truetype(FONT_BLACK, 180)
    title = "Espera!"
    x_title = center_x(draw, title, font_h1)
    y_title = 290
    draw_text_shadow(draw, (x_title, y_title), title, font_h1,
                     fill=BRAND, shadow=(60, 20, 0), shadow_offset=5)

    # === Subhead ===
    font_sub = ImageFont.truetype(FONT_BOLD, 56)
    sub_lines = [
        "Você está a UM PASSO",
        "da REVELAÇÃO.",
    ]
    y = 510
    for line in sub_lines:
        bx = center_x(draw, line, font_sub)
        # destaca palavras-chave em laranja via segmentação simples
        if "UM PASSO" in line or "REVELAÇÃO" in line:
            # render line all white, but redraw highlighted word over it
            draw_text_shadow(draw, (bx, y), line, font_sub,
                             fill=WHITE, shadow=(0, 0, 0), shadow_offset=2)
            # redraw highlighted in brand
            for hi in ("UM PASSO", "REVELAÇÃO."):
                if hi in line:
                    # measura prefixo
                    idx = line.index(hi)
                    prefix = line[:idx]
                    pb = draw.textbbox((0, 0), prefix, font=font_sub)
                    px = bx + (pb[2] - pb[0])
                    draw_text_shadow(draw, (px, y), hi, font_sub,
                                     fill=BRAND, shadow=(50, 20, 0), shadow_offset=2)
        else:
            draw_text_shadow(draw, (bx, y), line, font_sub,
                             fill=WHITE, shadow=(0, 0, 0), shadow_offset=2)
        y += 72

    # === Body ===
    font_body = ImageFont.truetype(FONT_BOLD, 36)
    body_lines = [
        "A Manuela está prestes a contar EXATAMENTE",
        "como ela transformou o corpo dela em 12 semanas —",
        "em casa, sem academia, sem dieta.",
    ]
    y = 720
    for line in body_lines:
        bx = center_x(draw, line, font_body)
        # EXATAMENTE em destaque
        if "EXATAMENTE" in line:
            idx = line.index("EXATAMENTE")
            prefix = line[:idx]
            kw = "EXATAMENTE"
            tail = line[idx + len(kw):]
            # mede pra colocar tudo
            pb = draw.textbbox((0, 0), prefix, font=font_body)
            kb = draw.textbbox((0, 0), kw, font=font_body)
            tb = draw.textbbox((0, 0), tail, font=font_body)
            total_w = (pb[2] - pb[0]) + (kb[2] - kb[0]) + (tb[2] - tb[0])
            x0 = (W - total_w) // 2
            draw.text((x0, y), prefix, fill=INK_ON_DARK_2, font=font_body)
            draw.text((x0 + (pb[2] - pb[0]), y), kw, fill=BRAND, font=font_body)
            draw.text((x0 + (pb[2] - pb[0]) + (kb[2] - kb[0]), y), tail,
                      fill=INK_ON_DARK_2, font=font_body)
        else:
            draw.text((bx, y), line, fill=INK_ON_DARK_2, font=font_body)
        y += 48

    # === Loss block ===
    font_loss = ImageFont.truetype(FONT_BLACK, 48)
    loss = "SAIR AGORA = CONTINUAR ONDE ESTÁ"
    lb = draw.textbbox((0, 0), loss, font=font_loss)
    lw, lh = lb[2] - lb[0], lb[3] - lb[1]
    pad_x, pad_y = 50, 24
    box_w = lw + pad_x * 2
    box_h = lh + pad_y * 2
    box_x = (W - box_w) // 2
    box_y = 910

    # fundo do block (vermelho semi-transparente)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rounded_rectangle(
        [box_x, box_y, box_x + box_w, box_y + box_h],
        radius=14,
        fill=(*DANGER, 60),
        outline=(*DANGER, 200),
        width=3,
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    text_x = box_x + pad_x
    text_y = box_y + pad_y - 6
    # destaca "CONTINUAR ONDE ESTÁ" mais forte
    if "CONTINUAR" in loss:
        idx = loss.index("CONTINUAR")
        prefix = loss[:idx]
        kw = loss[idx:]
        pb = draw.textbbox((0, 0), prefix, font=font_loss)
        draw.text((text_x, text_y), prefix, fill=(255, 200, 200), font=font_loss)
        draw.text((text_x + (pb[2] - pb[0]), text_y), kw, fill=WHITE, font=font_loss)
    else:
        draw.text((text_x, text_y), loss, fill=WHITE, font=font_loss)

    img.save(out_path, "PNG", optimize=True)
    print(f"[OK] {out_path}  ({out_path.stat().st_size // 1024} KB)")


def main():
    out_path = OUT_DIR / "vturb-resume-bbi.png"
    render_resume(out_path)
    print(f"\nUpar essa imagem no painel do VTurb (campo do Resume Modal).")
    print(f"Path: {out_path}")


if __name__ == "__main__":
    main()
