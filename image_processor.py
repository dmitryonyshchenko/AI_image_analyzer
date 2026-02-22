"""Shared drawing utilities used by scenario handlers."""
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ── 10-colour palette for dynamic class colouring (objects handler, etc.) ──
COLOR_PALETTE: list[str] = [
    "#FF6B6B",  # coral red
    "#4ECDC4",  # teal
    "#45B7D1",  # sky blue
    "#96CEB4",  # sage green
    "#F7DC6F",  # gold
    "#DDA0DD",  # plum
    "#F0B27A",  # peach
    "#98D8C8",  # mint
    "#BB8FCE",  # lavender
    "#F1948A",  # salmon
]


def open_image(path: str) -> Image.Image:
    image = Image.open(path)
    image = ImageOps.exif_transpose(image)
    return image.convert("RGB")


def save_image(image: Image.Image, path: str) -> None:
    image.save(path)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def get_font(size: int = 15):
    candidates = [
        "arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def build_color_map(items: list[dict], palette: list[str] | None = None) -> dict[str, str]:
    """
    Build a label → hex_color mapping by assigning palette colours in order
    of first appearance among the items.  Useful for unlimited-class scenarios.
    """
    if palette is None:
        palette = COLOR_PALETTE
    color_map: dict[str, str] = {}
    idx = 0
    for item in items:
        label = item.get("label", "unknown").lower()
        if label not in color_map:
            color_map[label] = palette[idx % len(palette)]
            idx += 1
    return color_map


def draw_boxes(
    image: Image.Image,
    items: list[dict],
    label_colors: dict[str, str],
    default_color: str = "#FF9100",
) -> Image.Image:
    """
    Draw bounding boxes with semi-transparent fill + solid border + label tags.

    items:        list of {label, bbox: [y_min, x_min, y_max, x_max] 0-1000,
                            confidence: float 0-1 (optional), description}
    label_colors: {label_name: "#RRGGBB"}
    Returns a new annotated PIL Image (original is not modified).
    """
    if not items:
        return image

    width, height = image.size
    border_width  = max(2, min(width, height) // 300)
    font          = get_font(15)

    def to_px(bbox: list[int]) -> tuple[int, int, int, int]:
        y_min, x_min, y_max, x_max = [max(0, min(1000, v)) for v in bbox]
        return (
            int(x_min / 1000 * width),
            int(y_min / 1000 * height),
            int(x_max / 1000 * width),
            int(y_max / 1000 * height),
        )

    # ── Semi-transparent fill + label tags ──────────────────────────────────
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    odraw   = ImageDraw.Draw(overlay)

    for item in items:
        bbox = item.get("bbox", [])
        if len(bbox) != 4:
            continue
        label      = item.get("label", "unknown").lower()
        confidence = item.get("confidence", 0.0)
        x1, y1, x2, y2 = to_px(bbox)
        color_hex = label_colors.get(label, default_color)
        r, g, b   = hex_to_rgb(color_hex)

        odraw.rectangle([x1, y1, x2, y2], fill=(r, g, b, 50))

        # Build label: "label 85%" (confidence shown when > 0)
        conf_str = f" {int(confidence * 100)}%" if confidence > 0 else ""
        tag      = f" {label}{conf_str} "

        tb = odraw.textbbox((0, 0), tag, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        pad = 2
        ty  = y1 - th - pad * 2 - border_width
        if ty < 0:
            ty = y1 + border_width

        odraw.rectangle(
            [x1, ty, x1 + tw + pad * 2, ty + th + pad * 2],
            fill=(r, g, b, 220),
        )
        odraw.text((x1 + pad, ty + pad), tag.strip(), fill=(255, 255, 255, 255), font=font)

    result = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

    # ── Solid borders ────────────────────────────────────────────────────────
    rdraw = ImageDraw.Draw(result)
    for item in items:
        bbox = item.get("bbox", [])
        if len(bbox) != 4:
            continue
        label     = item.get("label", "unknown").lower()
        x1, y1, x2, y2 = to_px(bbox)
        color_hex = label_colors.get(label, default_color)
        rdraw.rectangle([x1, y1, x2, y2], outline=color_hex, width=border_width)

    return result


def draw_model_label(image: Image.Image, model_name: str) -> Image.Image:
    """
    Draw a small 'AI: <model>' badge at the bottom-right corner of the image.
    Calls from handlers after draw_boxes() to stamp the model used.
    """
    if not model_name:
        return image

    result = image.copy().convert("RGB")
    draw   = ImageDraw.Draw(result)
    font   = get_font(12)
    text   = f" AI: {model_name} "

    tb     = draw.textbbox((0, 0), text, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    w, h   = result.size
    pad    = 3
    x = w - tw - pad * 2 - 6
    y = h - th - pad * 2 - 6

    draw.rectangle([x, y, x + tw + pad * 2, y + th + pad * 2], fill=(0, 0, 0))
    draw.text((x + pad, y + pad), text.strip(), fill=(255, 255, 255), font=font)
    return result
