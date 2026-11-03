"""
Analisador inteligente de fotos de pessoas para extração de características
faciais e mapeamento direto para as camadas oficiais do Stardew Valley
(skinColors.png, hairstyles.png, shirts.png, accessories.png, pants.png).
"""

import os
from dataclasses import dataclass, asdict
from typing import Tuple, Dict, Any, List
import numpy as np
from PIL import Image, ImageOps


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VANILLA_DIR = os.path.join(BASE_DIR, "assets", "stardew_vanilla")

# Paletas oficiais inspiradas em Stardew Valley (tons quentes e naturais)
STARDEW_SKIN_PALETTE = [
    ("#F9AE89", "Pele Stardew 1 (Clara)"),
    ("#F5C6A5", "Pele Stardew 2 (Muito Clara)"),
    ("#E89B72", "Pele Stardew 3 (Pêssego)"),
    ("#D4875E", "Pele Stardew 4 (Média)"),
    ("#B86B43", "Pele Stardew 5 (Morena)"),
    ("#94502E", "Pele Stardew 6 (Morena Escura)"),
    ("#6B371E", "Pele Stardew 7 (Negra)"),
    ("#4D2514", "Pele Stardew 8 (Negra Intensa)"),
]

STARDEW_HAIR_PALETTE = [
    ("#322218", "Preto Carvão"),
    ("#5A351D", "Castanho Escuro"),
    ("#824C27", "Castanho Médio"),
    ("#A86B3C", "Castanho Claro / Mel"),
    ("#E6B84C", "Loiro Dourado"),
    ("#F2DA91", "Loiro Platinado"),
    ("#C44229", "Ruivo Robin / Leah"),
    ("#E06D3B", "Ruivo Acobreado"),
    ("#92949E", "Grisalho / Prata"),
    ("#4668A6", "Azul Emily"),
    ("#8647A8", "Roxo Abigail"),
    ("#43945B", "Verde Caroline"),
]

STARDEW_EYE_PALETTE = [
    ("#462C1B", "Castanho Escuro"),
    ("#75492B", "Castanho Mel"),
    ("#3978A8", "Azul"),
    ("#3F8C4F", "Verde"),
    ("#636C75", "Cinza"),
]

STARDEW_CLOTH_PALETTE = [
    ("#3B659C", "Azul Fazendeiro"),
    ("#C43B3B", "Vermelho Clássico"),
    ("#3E8E4C", "Verde Floresta"),
    ("#D98A2B", "Laranja Outono"),
    ("#76428A", "Roxo Místico"),
    ("#2E2E38", "Preto Urbano"),
    ("#E8E0D5", "Branco Creme"),
    ("#8C583A", "Marrom Couro"),
    ("#D46A92", "Rosa"),
    ("#4CA6A6", "Turquesa"),
]

# Mapeamento de presets de cabelo para índices oficiais do hairstyles.png do Stardew Valley
HAIR_STYLE_TO_SDV_INDEX = {
    "curto": 0,       # Clássico curto masculino
    "topete": 5,      # Topete moderno / undercut
    "medio": 3,       # Médio repartido
    "longo": 16,      # Longo com franja lateral
    "cacheado": 32,   # Cacheado / Afro volumoso
    "coque": 18,      # Preso / Longo estilizado
    "careca": 52,     # Careca / Raspado oficial
}

# Mapeamento de barba e óculos para índices oficiais de accessories.png (0..18)
ACCESSORY_PRESETS = {
    "nenhum": -1,
    "barba_cheia": 0,
    "cavanhaque": 1,
    "bigode": 2,
    "bigode_curvo": 3,
    "costeletas": 5,
    "oculos_quadrado": 8,
    "oculos_redondo": 10,
    "oculos_escuro": 12,
    "monoculo": 11,
}


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (200, 150, 120)
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        int(np.clip(rgb[0], 0, 255)),
        int(np.clip(rgb[1], 0, 255)),
        int(np.clip(rgb[2], 0, 255)),
    )


def perceptual_color_dist(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    r1, g1, b1 = rgb1
    r2, g2, b2 = rgb2
    rmean = (r1 + r2) / 2.0
    dr = r1 - r2
    dg = g1 - g2
    db = b1 - b2
    return ((2 + rmean / 256.0) * (dr ** 2)) + 4 * (dg ** 2) + ((2 + (255 - rmean) / 256.0) * (db ** 2))


def closest_palette_color(rgb: Tuple[int, int, int], palette_list: list) -> str:
    best_hex = palette_list[0][0]
    best_dist = float("inf")
    for hex_val, _ in palette_list:
        dist = perceptual_color_dist(rgb, hex_to_rgb(hex_val))
        if dist < best_dist:
            best_dist = dist
            best_hex = hex_val
    return best_hex


def match_closest_sdv_skin_index(rgb: Tuple[int, int, int]) -> Tuple[int, str]:
    """Encontra qual dos 24 tons de pele oficiais de skinColors.png é mais próximo do RGB."""
    skin_path = os.path.join(VANILLA_DIR, "skinColors.png")
    if not os.path.exists(skin_path):
        return 0, "#F9AE89"
    img = Image.open(skin_path).convert("RGBA")
    w, h = img.size
    best_idx = 0
    best_hex = "#F9AE89"
    best_dist = float("inf")
    for row in range(h):
        # Coluna 2 (lightest/base) representa o tom principal do rosto em skinColors.png
        px = img.getpixel((2, row))[:3]
        d = perceptual_color_dist(rgb, px)
        if d < best_dist:
            best_dist = d
            best_idx = row
            best_hex = rgb_to_hex(px)
    return best_idx, best_hex


def match_closest_sdv_shirt_index(rgb: Tuple[int, int, int]) -> int:
    """Encontra a camisa oficial em shirts.png cuja cor predominante mais se aproxima da roupa da foto."""
    shirts_path = os.path.join(VANILLA_DIR, "shirts.png")
    if not os.path.exists(shirts_path):
        return 0
    img = Image.open(shirts_path).convert("RGBA")
    best_idx = 0
    best_dist = float("inf")
    # Explorar as primeiras 64 camisas clássicas de shirts.png
    for idx in range(64):
        sx = (idx % 16) * 8
        sy = (idx // 16) * 32
        crop = img.crop((sx, sy, sx + 8, sy + 8))
        arr = np.array(crop)
        opaque = arr[arr[:, :, 3] > 128][:, :3]
        if len(opaque) == 0:
            continue
        med_rgb = tuple(int(v) for v in np.median(opaque, axis=0))
        d = perceptual_color_dist(rgb, med_rgb)
        if d < best_dist:
            best_dist = d
            best_idx = idx
    return best_idx


def sample_median_rgb(region: np.ndarray, filter_extremes: bool = True) -> Tuple[int, int, int]:
    if region.size == 0:
        return (180, 140, 110)
    pixels = region.reshape(-1, 3).astype(np.float32)
    if filter_extremes and len(pixels) > 20:
        lum = 0.299 * pixels[:, 0] + 0.587 * pixels[:, 1] + 0.114 * pixels[:, 2]
        low, high = np.percentile(lum, [15, 85])
        mask = (lum >= low) & (lum <= high)
        if np.any(mask):
            pixels = pixels[mask]
    med = np.median(pixels, axis=0)
    return (int(med[0]), int(med[1]), int(med[2]))


def detect_face_bbox_skin_chrominance(img_np: np.ndarray) -> Tuple[int, int, int, int]:
    h, w, _ = img_np.shape
    r = img_np[:, :, 0].astype(np.float32)
    g = img_np[:, :, 1].astype(np.float32)
    b = img_np[:, :, 2].astype(np.float32)

    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = 128.0 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128.0 + 0.5 * r - 0.418688 * g - 0.081312 * b

    skin_mask = (cb >= 77) & (cb <= 135) & (cr >= 131) & (cr <= 178) & (y > 35)
    yy, xx = np.ogrid[:h, :w]
    spatial_mask = (yy >= int(h * 0.05)) & (yy <= int(h * 0.78)) & (xx >= int(w * 0.10)) & (xx <= int(w * 0.90))
    valid_skin = skin_mask & spatial_mask

    if np.count_nonzero(valid_skin) > (h * w * 0.02):
        ys, xs = np.where(valid_skin)
        x1, x2 = int(np.percentile(xs, 8)), int(np.percentile(xs, 92))
        y1, y2 = int(np.percentile(ys, 8)), int(np.percentile(ys, 90))
        fw = max(int(w * 0.22), x2 - x1)
        fh = max(int(h * 0.22), min(int(fw * 1.35), y2 - y1))
        fx = max(0, min(w - fw, x1))
        fy = max(0, min(h - fh, y1))
        return (fx, fy, fw, fh)

    fw = int(w * 0.42)
    fh = int(h * 0.44)
    fx = int((w - fw) // 2)
    fy = int(h * 0.16)
    return (fx, fy, fw, fh)


def compute_edge_strength(gray_region: np.ndarray) -> float:
    if gray_region.shape[0] < 3 or gray_region.shape[1] < 3:
        return 0.0
    gx = np.diff(gray_region.astype(np.float32), axis=1)
    gy = np.diff(gray_region.astype(np.float32), axis=0)
    return float(np.std(gx) + np.std(gy))


@dataclass
class AvatarConfig:
    name: str = "Fazendeiro Leo"
    is_male: bool = True
    skin_index: int = 0               # 0..23 em skinColors.png
    skin_color: str = "#F9AE89"
    hair_index: int = 0               # 0..72 em hairstyles.png / hairstyles2.png
    hair_color: str = "#824C27"
    hair_style: str = "curto"         # curto, medio, longo, cacheado, topete, coque, careca
    eye_color: str = "#462C1B"
    accessory_index: int = -1         # -1=nenhum, 0..5=barbas, 6..18=óculos/acessórios
    beard_style: str = "sem_barba"
    glasses_style: str = "nenhum"
    shirt_index: int = 0              # 0..111 em shirts.png
    outfit_style: str = "jardineira"
    shirt_color: str = "#C43B3B"
    pants_index: int = 0              # 0..3 em pants.png (0=calça comprida, 1=shorts, 2=saia/vestido)
    pants_color: str = "#3B659C"
    hat_style: str = "nenhum"         # nenhum, palha, bone, flor
    scale: int = 4

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AvatarConfig":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        cfg = cls(**filtered)
        # Sincronizar índices caso venha de versão anterior do JSON
        if "hair_index" not in data and cfg.hair_style in HAIR_STYLE_TO_SDV_INDEX:
            cfg.hair_index = HAIR_STYLE_TO_SDV_INDEX[cfg.hair_style]
        if "accessory_index" not in data:
            if cfg.beard_style == "barba_cheia":
                cfg.accessory_index = 0
            elif cfg.beard_style == "cavanhaque":
                cfg.accessory_index = 1
            elif cfg.beard_style == "bigode":
                cfg.accessory_index = 2
            elif cfg.glasses_style == "escuro":
                cfg.accessory_index = 12
            elif cfg.glasses_style == "redondo":
                cfg.accessory_index = 10
            elif cfg.glasses_style == "quadrado":
                cfg.accessory_index = 8
        return cfg


def analyze_person_photo(image_path: str) -> Tuple[AvatarConfig, Image.Image]:
    """
    Analisa uma foto de pessoa e mapeia automaticamente para as camadas
    e índices oficiais do Stardew Valley.
    """
    pil_img = Image.open(image_path)
    pil_img = ImageOps.exif_transpose(pil_img).convert("RGB")

    pil_img.thumbnail((600, 600), Image.Resampling.LANCZOS)
    img_np = np.array(pil_img)
    h, w, _ = img_np.shape

    gray = (
        0.299 * img_np[:, :, 0]
        + 0.587 * img_np[:, :, 1]
        + 0.114 * img_np[:, :, 2]
    ).astype(np.uint8)

    # 1. Detectar caixa do rosto
    fx, fy, fw, fh = detect_face_bbox_skin_chrominance(img_np)

    # 2. Amostrar tom de pele e mapear para os 24 tons oficiais de skinColors.png
    cheek_left = img_np[
        max(0, int(fy + fh * 0.45)):min(h, int(fy + fh * 0.68)),
        max(0, int(fx + fw * 0.18)):min(w, int(fx + fw * 0.38))
    ]
    cheek_right = img_np[
        max(0, int(fy + fh * 0.45)):min(h, int(fy + fh * 0.68)),
        max(0, int(fx + fw * 0.62)):min(w, int(fx + fw * 0.82))
    ]
    forehead = img_np[
        max(0, int(fy + fh * 0.15)):min(h, int(fy + fh * 0.32)),
        max(0, int(fx + fw * 0.30)):min(w, int(fx + fw * 0.70))
    ]
    skin_samples = [s.reshape(-1, 3) for s in (cheek_left, cheek_right, forehead) if s.size > 0]
    raw_skin_rgb = sample_median_rgb(np.vstack(skin_samples)) if skin_samples else (230, 180, 140)
    skin_idx, skin_hex = match_closest_sdv_skin_index(raw_skin_rgb)

    # 3. Amostrar cabelo e estimar corte oficial
    hair_top = img_np[
        max(0, int(fy - fh * 0.25)):max(1, int(fy + fh * 0.14)),
        max(0, int(fx + fw * 0.15)):min(w, int(fx + fw * 0.85))
    ]
    raw_hair_rgb = sample_median_rgb(hair_top, filter_extremes=False)
    hair_hex = closest_palette_color(raw_hair_rgb, STARDEW_HAIR_PALETTE)

    skin_vec = np.array(raw_skin_rgb, dtype=np.float32)
    hair_vec = np.array(raw_hair_rgb, dtype=np.float32)
    top_skin_diff = float(np.linalg.norm(hair_vec - skin_vec))

    side_left = img_np[
        max(0, int(fy + fh * 0.45)):min(h, int(fy + fh * 1.05)),
        max(0, int(fx - fw * 0.22)):max(1, int(fx + fw * 0.12))
    ]
    side_right = img_np[
        max(0, int(fy + fh * 0.45)):min(h, int(fy + fh * 1.05)),
        min(w - 1, int(fx + fw * 0.88)):min(w, int(fx + fw * 1.22))
    ]
    side_samples = [s.reshape(-1, 3) for s in (side_left, side_right) if s.size > 0]
    side_hair_similarity = 999.0
    if side_samples:
        side_rgb = np.array(sample_median_rgb(np.vstack(side_samples)), dtype=np.float32)
        side_hair_similarity = float(np.linalg.norm(side_rgb - hair_vec))

    hair_gray = gray[
        max(0, int(fy - fh * 0.25)):max(1, int(fy + fh * 0.15)),
        max(0, int(fx + fw * 0.1)):min(w, int(fx + fw * 0.9))
    ]
    hair_edges = compute_edge_strength(hair_gray)

    is_male = True
    if top_skin_diff < 22.0 and hair_edges < 16.0:
        hair_style = "careca"
    elif side_hair_similarity < 42.0:
        hair_style = "longo"
        is_male = False
    elif side_hair_similarity < 62.0:
        hair_style = "medio"
    elif hair_edges > 38.0:
        hair_style = "cacheado"
    elif int(raw_hair_rgb[0]) % 2 == 0:
        hair_style = "curto"
    else:
        hair_style = "topete"

    hair_idx = HAIR_STYLE_TO_SDV_INDEX.get(hair_style, 0)

    # 4. Detectar óculos e cor dos olhos
    eye_region_gray = gray[
        max(0, int(fy + fh * 0.24)):min(h, int(fy + fh * 0.48)),
        max(0, int(fx + fw * 0.15)):min(w, int(fx + fw * 0.85))
    ]
    eye_region_rgb = img_np[
        max(0, int(fy + fh * 0.28)):min(h, int(fy + fh * 0.46)),
        max(0, int(fx + fw * 0.20)):min(w, int(fx + fw * 0.80))
    ]

    glasses_style = "nenhum"
    if eye_region_gray.size > 0:
        bridge = eye_region_gray[
            int(eye_region_gray.shape[0] * 0.20):int(eye_region_gray.shape[0] * 0.80),
            int(eye_region_gray.shape[1] * 0.42):int(eye_region_gray.shape[1] * 0.58)
        ]
        bridge_edges = compute_edge_strength(bridge)
        if bridge_edges > 34.0:
            eye_lum = float(np.mean(eye_region_gray))
            glasses_style = "escuro" if eye_lum < 68 else "quadrado"

    if eye_region_rgb.size > 0:
        pixels = eye_region_rgb.reshape(-1, 3)
        lum = 0.299 * pixels[:, 0] + 0.587 * pixels[:, 1] + 0.114 * pixels[:, 2]
        iris_mask = (lum > 20) & (lum < 110)
        if np.any(iris_mask):
            iris_rgb = tuple(int(v) for v in np.median(pixels[iris_mask], axis=0))
        else:
            iris_rgb = (70, 45, 25)
    else:
        iris_rgb = (70, 45, 25)
    eye_hex = closest_palette_color(iris_rgb, STARDEW_EYE_PALETTE)

    # 5. Detectar barba / bigode
    chin_region = img_np[
        max(0, int(fy + fh * 0.72)):min(h, int(fy + fh * 0.98)),
        max(0, int(fx + fw * 0.25)):min(w, int(fx + fw * 0.75))
    ]
    mustache_region = img_np[
        max(0, int(fy + fh * 0.60)):min(h, int(fy + fh * 0.72)),
        max(0, int(fx + fw * 0.32)):min(w, int(fx + fw * 0.68))
    ]
    skin_lum = 0.299 * raw_skin_rgb[0] + 0.587 * raw_skin_rgb[1] + 0.114 * raw_skin_rgb[2]
    chin_rgb = sample_median_rgb(chin_region) if chin_region.size > 0 else raw_skin_rgb
    must_rgb = sample_median_rgb(mustache_region) if mustache_region.size > 0 else raw_skin_rgb
    chin_lum = 0.299 * chin_rgb[0] + 0.587 * chin_rgb[1] + 0.114 * chin_rgb[2]
    must_lum = 0.299 * must_rgb[0] + 0.587 * must_rgb[1] + 0.114 * must_rgb[2]

    beard_style = "sem_barba"
    if hair_style != "longo":
        if (skin_lum - chin_lum) > 36 and (skin_lum - must_lum) > 28:
            beard_style = "barba_cheia"
            is_male = True
        elif (skin_lum - chin_lum) > 32:
            beard_style = "cavanhaque"
            is_male = True
        elif (skin_lum - must_lum) > 32:
            beard_style = "bigode"
            is_male = True

    # Determinar accessory_index oficial do Stardew Valley
    accessory_idx = -1
    if beard_style == "barba_cheia":
        accessory_idx = 0
    elif beard_style == "cavanhaque":
        accessory_idx = 1
    elif beard_style == "bigode":
        accessory_idx = 2
    elif glasses_style == "escuro":
        accessory_idx = 12
    elif glasses_style == "quadrado":
        accessory_idx = 8
    elif glasses_style == "redondo":
        accessory_idx = 10

    # 6. Amostrar roupa e encontrar a camisa oficial mais próxima em shirts.png
    torso_region = img_np[
        min(h - 2, int(fy + fh * 1.05)):min(h, int(fy + fh * 1.65)),
        max(0, int(fx + fw * 0.10)):min(w, int(fx + fw * 0.90))
    ]
    if torso_region.size > 0:
        raw_shirt_rgb = sample_median_rgb(torso_region)
        shirt_hex = closest_palette_color(raw_shirt_rgb, STARDEW_CLOTH_PALETTE)
        shirt_idx = match_closest_sdv_shirt_index(raw_shirt_rgb)
    else:
        shirt_hex = "#C43B3B"
        shirt_idx = 0

    pants_hex = "#3B659C" if shirt_hex != "#3B659C" else "#2E2E38"

    base_name = os.path.splitext(os.path.basename(image_path))[0].replace("_", " ").replace("-", " ").title()
    if not base_name or len(base_name) > 20:
        base_name = "Aldeão Stardew"

    config = AvatarConfig(
        name=base_name,
        is_male=is_male,
        skin_index=skin_idx,
        skin_color=skin_hex,
        hair_index=hair_idx,
        hair_color=hair_hex,
        hair_style=hair_style,
        eye_color=eye_hex,
        accessory_index=accessory_idx,
        beard_style=beard_style,
        glasses_style=glasses_style,
        shirt_index=shirt_idx,
        outfit_style="jardineira",
        shirt_color=shirt_hex,
        pants_index=0,
        pants_color=pants_hex,
        hat_style="nenhum",
        scale=4,
    )

    portrait_img = generate_stardew_portrait(pil_img, (fx, fy, fw, fh))
    return config, portrait_img


def generate_stardew_portrait(pil_img: Image.Image, face_box: Tuple[int, int, int, int]) -> Image.Image:
    """
    Recorta ao redor do rosto e converte em um retrato 64x64 em Pixel Art
    com moldura e quantização de cores estilo Stardew Valley.
    """
    w, h = pil_img.size
    fx, fy, fw, fh = face_box

    cx = fx + fw / 2.0
    cy = fy + fh * 0.48
    side = max(fw, fh) * 1.65
    left = int(max(0, cx - side / 2))
    top = int(max(0, cy - side / 2))
    right = int(min(w, cx + side / 2))
    bottom = int(min(h, cy + side / 2))

    crop = pil_img.crop((left, top, right, bottom))
    small = crop.resize((56, 56), Image.Resampling.BILINEAR)
    quantized = small.quantize(colors=20, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).convert("RGBA")

    frame = Image.new("RGBA", (64, 64), (72, 40, 20, 255))
    inner_border = Image.new("RGBA", (60, 60), (217, 158, 91, 255))
    bg = Image.new("RGBA", (56, 56), (245, 224, 181, 255))
    frame.paste(inner_border, (2, 2))
    frame.paste(bg, (4, 4))
    frame.paste(quantized, (4, 4))
    return frame
