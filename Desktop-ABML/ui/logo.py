"""
ui/logo.py — Generación programática del logo del cerebro con PIL.
"""
from PIL import Image, ImageDraw, ImageFont


def make_brain_logo(size: int = 90) -> Image.Image:
    """
    Genera el logo del cerebro con fondo verde redondeado y punto de estado.

    Parámetros
    ----------
    size : int
        Tamaño en píxeles del cuadrado resultante.

    Retorna
    -------
    PIL.Image.Image en modo RGBA.
    """
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fondo redondeado verde oscuro
    draw.rounded_rectangle(
        [0, 0, size - 1, size - 1],
        radius=int(size * 0.2),
        fill=(26, 46, 26, 255),
    )

    # Emoji 🧠 con la fuente de emoji de Windows
    emoji_px = int(size * 0.54)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", emoji_px)
        bbox = font.getbbox("🧠")
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (size - tw) // 2 - bbox[0]
        y = (size - th) // 2 - bbox[1] - int(size * 0.03)
        draw.text((x, y), "🧠", font=font, embedded_color=True)
    except Exception:
        # Fallback: dos lóbulos dibujados con arcos
        cx, cy = size // 2, size // 2 + 2
        r = int(size * 0.27)
        g = (0, 230, 118, 255)
        draw.arc([cx - r * 2, cy - r, cx,         cy + r], 180, 0, fill=g, width=3)
        draw.arc([cx,         cy - r, cx + r * 2, cy + r], 180, 0, fill=g, width=3)
        draw.line([cx, cy - r, cx, cy + r], fill=g, width=2)

    # Punto verde brillante (esquina superior derecha)
    dr   = int(size * 0.1)
    dx   = size - dr * 2 - 4
    dy   = 4
    draw.ellipse([dx, dy, dx + dr * 2, dy + dr * 2], fill=(0, 255, 65, 255))

    return img
