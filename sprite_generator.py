"""
Renderizador Oficial em Camadas do Stardew Valley (16x32 base dentro de célula 24x36).
Monta o personagem usando as folhas originais do jogo:
- farmer_base.png / farmer_girl_base.png
- skinColors.png
- hairstyles.png / hairstyles2.png
- shirts.png
- pants.png
- accessories.png
"""

import os
from typing import Tuple, Dict, List, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from photo_analyzer import (
    AvatarConfig,
    hex_to_rgb,
    HAIR_STYLE_TO_SDV_INDEX,
    VANILLA_DIR,
)


CELL_W = 24
CELL_H = 36
COLS = 4
ROWS = 8

ANIMATION_ROWS: Dict[str, int] = {
    "idle": 0,
    "walk_right": 1,
    "walk_left": 2,
    "water_crops": 3,
    "coffee_break": 4,
    "fishing": 5,
    "happy_dance": 6,
    "sleep_sit": 7,
}

ANIMATION_LABELS: Dict[str, str] = {
    "idle": "Parado / Respirando",
    "walk_right": "Andando (Direita)",
    "walk_left": "Andando (Esquerda)",
    "water_crops": "Regando Plantinha",
    "coffee_break": "Tomando Café Expresso",
    "fishing": "Pescando",
    "happy_dance": "Comemorando / Feliz",
    "sleep_sit": "Sentado / Cochilando",
}


class _StardewAssetsCache:
    """Cache em memória das folhas de sprites originais do Stardew Valley."""

    def __init__(self):
        self.loaded = False
        self.male_base: Optional[Image.Image] = None
        self.female_base: Optional[Image.Image] = None
        self.hairs1: Optional[Image.Image] = None
        self.hairs2: Optional[Image.Image] = None
        self.accessories: Optional[Image.Image] = None
        self.shirts: Optional[Image.Image] = None
        self.pants: Optional[Image.Image] = None
        self.skins: Optional[Image.Image] = None
        self.palette_refs: Dict[str, Tuple[int, int, int, int]] = {}

    def ensure_loaded(self):
        if self.loaded:
            return
        self.male_base = Image.open(os.path.join(VANILLA_DIR, "farmer_base.png")).convert("RGBA")
        self.female_base = Image.open(os.path.join(VANILLA_DIR, "farmer_girl_base.png")).convert("RGBA")
        self.hairs1 = Image.open(os.path.join(VANILLA_DIR, "hairstyles.png")).convert("RGBA")
        self.hairs2 = Image.open(os.path.join(VANILLA_DIR, "hairstyles2.png")).convert("RGBA")
        self.accessories = Image.open(os.path.join(VANILLA_DIR, "accessories.png")).convert("RGBA")
        self.shirts = Image.open(os.path.join(VANILLA_DIR, "shirts.png")).convert("RGBA")
        self.pants = Image.open(os.path.join(VANILLA_DIR, "pants.png")).convert("RGBA")
        self.skins = Image.open(os.path.join(VANILLA_DIR, "skinColors.png")).convert("RGBA")

        # Extrair as cores-chave de substituição na linha 0, coluna 16 (índices 256..277) de farmer_base.png
        arr = np.array(self.male_base).reshape(-1, 4)
        self.palette_refs = {
            "sleeve_dark": tuple(int(v) for v in arr[256]),
            "sleeve_med": tuple(int(v) for v in arr[257]),
            "sleeve_light": tuple(int(v) for v in arr[258]),
            "skin_dark": tuple(int(v) for v in arr[260]),
            "skin_med": tuple(int(v) for v in arr[261]),
            "skin_light": tuple(int(v) for v in arr[262]),
            "eye_bright": tuple(int(v) for v in arr[276]),
            "eye_dark": tuple(int(v) for v in arr[277]),
        }
        self.loaded = True


_CACHE = _StardewAssetsCache()


def put_px(img: Image.Image, x: int, y: int, color: Tuple[int, int, int, int]):
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), color)


def fill_rect(img: Image.Image, x1: int, y1: int, w: int, h: int, color: Tuple[int, int, int, int]):
    for yy in range(y1, y1 + h):
        for xx in range(x1, x1 + w):
            put_px(img, xx, yy, color)


def tint_stardew_sprite(img: Image.Image, target_rgb: Tuple[int, int, int]) -> Image.Image:
    """
    Aplica tingimento ao estilo Multiplicação / Colorize do Stardew Valley,
    preservando contornos escuros, sombras e brilhos originais da pixel art.
    """
    arr = np.array(img, dtype=np.float32)
    alpha = arr[:, :, 3:4]
    # No Stardew Valley, os assets de cabelo/calça são desenhados em tons de cinza (0..255)
    # Multiplicar pelo target_rgb normalizado (com leve boost para preservar os highlights)
    r, g, b = target_rgb
    lum = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]) / 255.0
    # Curva suave para manter o contorno escuro de ConcernedApe bem definido
    contrast_lum = np.power(lum, 0.92)
    out = np.zeros_like(arr)
    out[:, :, 0] = np.clip(contrast_lum * r * 1.18, 0, 255)
    out[:, :, 1] = np.clip(contrast_lum * g * 1.18, 0, 255)
    out[:, :, 2] = np.clip(contrast_lum * b * 1.18, 0, 255)
    out[:, :, 3] = alpha[:, :, 0]
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def _get_skin_3tones(cfg: AvatarConfig) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int], Tuple[int, int, int, int]]:
    """Retorna os 3 tons de pele (escuro/contorno, médio, claro) a partir de skinColors.png ou cor customizada."""
    _CACHE.ensure_loaded()
    skins_img = _CACHE.skins
    idx = max(0, min(skins_img.height - 1, int(cfg.skin_index)))

    # Verificar se a cor customizada bate com o tom oficial ou se o usuário escolheu outra cor no seletor
    official_light = skins_img.getpixel((2, idx))[:3]
    user_rgb = hex_to_rgb(cfg.skin_color)
    if sum(abs(a - b) for a, b in zip(official_light, user_rgb)) <= 18:
        s_dark = skins_img.getpixel((0, idx))
        s_med = skins_img.getpixel((1, idx))
        s_light = skins_img.getpixel((2, idx))
        return (s_dark, s_med, s_light)

    # Derivar 3 tons ao estilo Stardew Valley (sombra avermelhada/quente) a partir da cor escolhida
    r, g, b = user_rgb
    s_light = (r, g, b, 255)
    s_med = (max(0, int(r * 0.86)), max(0, int(g * 0.72)), max(0, int(b * 0.68)), 255)
    s_dark = (max(0, int(r * 0.52)), max(0, int(g * 0.25)), max(0, int(b * 0.32)), 255)
    return (s_dark, s_med, s_light)


def _recolor_base_patch(
    patch: Image.Image,
    skin_tones: Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int], Tuple[int, int, int, int]],
    sleeve_rgb: Tuple[int, int, int],
    eye_rgb: Tuple[int, int, int],
) -> Image.Image:
    """Substitui os canais de pele, mangas e olhos em um recorte 16x32 de farmer_base.png."""
    _CACHE.ensure_loaded()
    refs = _CACHE.palette_refs
    s_dark, s_med, s_light = skin_tones

    sr, sg, sb = sleeve_rgb
    sl_light = (sr, sg, sb, 255)
    sl_med = (max(0, int(sr * 0.78)), max(0, int(sg * 0.75)), max(0, int(sb * 0.75)), 255)
    sl_dark = (max(0, int(sr * 0.48)), max(0, int(sg * 0.44)), max(0, int(sb * 0.44)), 255)

    er, eg, eb = eye_rgb
    e_bright = (er, eg, eb, 255)
    e_dark = (max(0, er - 70), max(0, eg - 70), max(0, eb - 60), 255)

    arr = np.array(patch)
    out = arr.copy()

    replacements = [
        (refs["skin_dark"], s_dark),
        (refs["skin_med"], s_med),
        (refs["skin_light"], s_light),
        (refs["sleeve_dark"], sl_dark),
        (refs["sleeve_med"], sl_med),
        (refs["sleeve_light"], sl_light),
        (refs["eye_bright"], e_bright),
        (refs["eye_dark"], e_dark),
    ]
    for src_rgba, dst_rgba in replacements:
        mask = (
            (arr[:, :, 0] == src_rgba[0])
            & (arr[:, :, 1] == src_rgba[1])
            & (arr[:, :, 2] == src_rgba[2])
            & (arr[:, :, 3] > 0)
        )
        out[mask] = dst_rgba

    return Image.fromarray(out, "RGBA")


def _resolve_shirt_index(cfg: AvatarConfig) -> int:
    """Determina o índice da camisa oficial em shirts.png ou mapeia pelo estilo de roupa."""
    outfit_defaults = {
        "jardineira": 0,   # Clássica com suspensórios/macacão
        "camiseta": 13,    # Camiseta limpa
        "xadrez": 12,      # Camisa listrada/xadrez
        "moletom": 21,     # Moletom aconchegante
        "jaqueta": 18,     # Jaqueta aberta com camisa interna
    }
    if cfg.shirt_index > 0:
        return min(111, cfg.shirt_index)
    return outfit_defaults.get(cfg.outfit_style, 0)


def _resolve_hair_index(cfg: AvatarConfig) -> int:
    if cfg.hair_style == "careca":
        return -1
    if cfg.hair_index >= 0 and cfg.hair_style == "custom":
        return cfg.hair_index
    return HAIR_STYLE_TO_SDV_INDEX.get(cfg.hair_style, cfg.hair_index)


def _render_sdv_16x32(
    cfg: AvatarConfig,
    dir_row: int,
    base_col: int,
    arm_col: int,
    bob_px: int = 0,
    blink: bool = False,
    flip_x: bool = False,
) -> Image.Image:
    """
    Monta um quadro 16x32 autêntico do Stardew Valley seguindo a hierarquia exata do FarmerRenderer:
    1. Corpo Base (farmer_base.png / farmer_girl_base.png)
    2. Calça (pants.png)
    3. Camisa (shirts.png 8x8)
    4. Barba e/ou Óculos (accessories.png 16x16)
    5. Cabelo (hairstyles.png / hairstyles2.png 16x32)
    6. Chapéu
    7. Braços (farmer_base.png colunas 6..17)
    """
    _CACHE.ensure_loaded()
    base_sheet = _CACHE.male_base if cfg.is_male else _CACHE.female_base
    female_offset = 0 if cfg.is_male else 1

    skin_tones = _get_skin_3tones(cfg)
    eye_rgb = hex_to_rgb(cfg.eye_color)
    hair_rgb = hex_to_rgb(cfg.hair_color)
    pants_rgb = hex_to_rgb(cfg.pants_color)
    shirt_rgb = hex_to_rgb(cfg.shirt_color)

    # 1. Recortar camisa (8x8) original de shirts.png (mantendo as cores e detalhes multi-coloridos de ConcernedApe)
    shirt_idx = _resolve_shirt_index(cfg)
    sx = (shirt_idx % 16) * 8
    sy = (shirt_idx // 16) * 32 + (dir_row * 8)
    shirt_crop = _CACHE.shirts.crop((sx, sy, sx + 8, sy + 8))
    # Extrair a cor predominante da camisa para pintar as mangas dos braços
    s_arr = np.array(shirt_crop)
    opaque_px = s_arr[s_arr[:, :, 3] > 128][:, :3]
    if len(opaque_px) > 0:
        sleeve_rgb = tuple(int(v) for v in np.median(opaque_px, axis=0))
    else:
        sleeve_rgb = shirt_rgb
    shirt_tinted = shirt_crop

    # 2. Corpo Base (16x32)
    bx = base_col * 16
    by = dir_row * 32
    raw_body = base_sheet.crop((bx, by, bx + 16, by + 32))
    body_frame = _recolor_base_patch(raw_body, skin_tones, sleeve_rgb, eye_rgb)

    # Piscar os olhos (fechar pálpebra com tom de pele médio/escuro quando blink=True)
    if blink and dir_row == 0:
        s_dark, s_med, s_light = skin_tones
        ey = 10 + female_offset + bob_px
        for ex in (5, 6, 9, 10):
            put_px(body_frame, ex, ey, s_light)
            put_px(body_frame, ex, ey + 1, s_dark)

    canvas = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    canvas.paste(body_frame, (0, 0), body_frame)

    # 3. Calça (16x32 de pants.png)
    p_type = max(0, min(3, cfg.pants_index))
    px_origin = (p_type % 10) * 192 + (0 if cfg.is_male else 96)
    py_origin = (p_type // 10) * 688
    pant_crop = _CACHE.pants.crop((px_origin + bx, py_origin + by, px_origin + bx + 16, py_origin + by + 32))
    pant_tinted = tint_stardew_sprite(pant_crop, pants_rgb)
    canvas.paste(pant_tinted, (0, 0), pant_tinted)

    # 4. Camisa (8x8 posicionada em X=4, Y=15 + female_offset + bob_px)
    shirt_y = 15 + female_offset + bob_px
    canvas.paste(shirt_tinted, (4, shirt_y), shirt_tinted)

    # 5. Acessórios Faciais (Barba e Óculos de accessories.png)
    # Permitimos combinar barba E óculos simultaneamente!
    acc_indices_to_draw = []
    if cfg.beard_style == "barba_cheia":
        acc_indices_to_draw.append(0)
    elif cfg.beard_style == "cavanhaque":
        acc_indices_to_draw.append(1)
    elif cfg.beard_style == "bigode":
        acc_indices_to_draw.append(2)

    if cfg.glasses_style == "quadrado":
        acc_indices_to_draw.append(8)
    elif cfg.glasses_style == "redondo":
        acc_indices_to_draw.append(10)
    elif cfg.glasses_style == "escuro":
        acc_indices_to_draw.append(12)

    if cfg.accessory_index >= 0 and cfg.accessory_index not in acc_indices_to_draw:
        acc_indices_to_draw.append(cfg.accessory_index)

    if dir_row in (0, 1):  # Acessórios faciais aparecem de frente (0) e de perfil (1)
        for acc_id in acc_indices_to_draw:
            if 0 <= acc_id <= 18:
                ax = (acc_id % 8) * 16
                ay = (acc_id // 8) * 32 + (dir_row * 16)
                acc_crop = _CACHE.accessories.crop((ax, ay, ax + 16, ay + 16))
                if acc_id <= 5:  # Índices 0..5 são barbas/bigodes -> recebem a cor do cabelo
                    acc_crop = tint_stardew_sprite(acc_crop, hair_rgb)
                acc_y = (1 if cfg.is_male else 2) + bob_px
                canvas.paste(acc_crop, (0, acc_y), acc_crop)

    # 6. Cabelo (16x32 de hairstyles.png ou hairstyles2.png)
    hair_id = _resolve_hair_index(cfg)
    if hair_id >= 0:
        if hair_id < 56:
            h_sheet = _CACHE.hairs1
            local_id = hair_id
        else:
            h_sheet = _CACHE.hairs2
            local_id = hair_id - 56
        hx = (local_id % 8) * 16
        hy = (local_id // 8) * 96 + (dir_row * 32)
        if hy + 32 <= h_sheet.height:
            hair_crop = h_sheet.crop((hx, hy, hx + 16, hy + 32))
            hair_tinted = tint_stardew_sprite(hair_crop, hair_rgb)
            hair_y_off = (0 if hair_id >= 16 else 1) + female_offset + bob_px
            canvas.paste(hair_tinted, (0, hair_y_off), hair_tinted)

    # 7. Braços Animados (Colunas 6..17 de farmer_base.png)
    ax_col = arm_col * 16
    raw_arms = base_sheet.crop((ax_col, by, ax_col + 16, by + 32))
    arms_frame = _recolor_base_patch(raw_arms, skin_tones, sleeve_rgb, eye_rgb)
    canvas.paste(arms_frame, (0, 0), arms_frame)

    # Espelhar horizontalmente para caminhada para a esquerda (exatamente como o motor do Stardew Valley faz)
    if flip_x:
        canvas = ImageOps.mirror(canvas)

    return canvas


def draw_character_frame(
    cfg: AvatarConfig,
    action: str,
    frame_idx: int,
) -> Image.Image:
    """
    Desenha um quadro 24x36 contendo o personagem autêntico 16x32 do Stardew Valley
    mais chapéu e ferramentas/efeitos das ações na área de trabalho.
    """
    canvas = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))

    # Mapear ação e frame_idx (0..3) para as poses reais de farmer_base.png
    dir_row = 0
    base_col = 0
    arm_col = 6
    bob_px = 0
    blink = False
    flip_x = False
    jump_y = 0

    if action == "idle":
        dir_row = 0
        base_col = 0
        arm_col = 6
        bob_px = 0
        blink = (frame_idx == 3)
    elif action == "walk_right":
        dir_row = 1
        # Ciclo oficial de caminhada do Stardew Valley: Col 0 -> Col 1 -> Col 0 -> Col 2
        walk_seq = [0, 1, 0, 2]
        base_col = walk_seq[frame_idx % 4]
        arm_col = 6 + base_col
        bob_px = 1 if base_col in (1, 2) else 0
    elif action == "walk_left":
        dir_row = 1
        walk_seq = [0, 1, 0, 2]
        base_col = walk_seq[frame_idx % 4]
        arm_col = 6 + base_col
        bob_px = 1 if base_col in (1, 2) else 0
        flip_x = True
    elif action == "water_crops":
        dir_row = 1
        # Pose de usar ferramenta lateral (Col 3/4 de Row 1)
        base_col = 3 if frame_idx in (1, 2) else 0
        arm_col = 10 if frame_idx in (1, 2) else 6
        bob_px = 1 if frame_idx in (1, 2) else 0
    elif action == "coffee_break":
        dir_row = 0
        # Pose segurando item / bebendo (braços levantados cols 12/13)
        base_col = 0
        arm_col = 12 if frame_idx in (1, 2) else 6
    elif action == "fishing":
        dir_row = 1
        base_col = 3 if frame_idx == 3 else 0
        arm_col = 10 if frame_idx in (1, 2, 3) else 6
    elif action == "happy_dance":
        dir_row = 0
        # Pose comemorando com braços erguidos (Col 3 + Arm 14)
        base_col = 3 if frame_idx in (1, 3) else 0
        arm_col = 14 if frame_idx in (1, 3) else 6
        jump_y = -2 if frame_idx in (1, 3) else 0
    elif action == "sleep_sit":
        dir_row = 0
        base_col = 0
        arm_col = 6
        bob_px = 0
        blink = True

    sdv_16x32 = _render_sdv_16x32(
        cfg=cfg,
        dir_row=dir_row,
        base_col=base_col,
        arm_col=arm_col,
        bob_px=bob_px,
        blink=blink,
        flip_x=flip_x,
    )

    ox = 4
    oy = 3 + jump_y

    # Sombra oval suave no chão (estilo Stardew Valley)
    for sx in range(ox + 3, ox + 13):
        put_px(canvas, sx, 34, (20, 15, 25, 95))
    for sx in range(ox + 4, ox + 12):
        put_px(canvas, sx, 33, (20, 15, 25, 65))

    canvas.paste(sdv_16x32, (ox, oy), sdv_16x32)

    # Chapéu / Acessório de Cabeça
    head_top_y = oy + 2 + bob_px
    if cfg.hat_style == "palha":
        straw_out = (110, 68, 24, 255)
        straw = (242, 206, 116, 255)
        straw_sh = (204, 158, 72, 255)
        ribbon = (198, 52, 52, 255)
        fill_rect(canvas, ox + 1, head_top_y + 1, 14, 2, straw_out)
        fill_rect(canvas, ox + 2, head_top_y + 1, 12, 1, straw)
        fill_rect(canvas, ox + 3, head_top_y - 2, 10, 3, straw_out)
        fill_rect(canvas, ox + 4, head_top_y - 1, 8, 2, straw)
        fill_rect(canvas, ox + 4, head_top_y, 8, 1, ribbon)
        put_px(canvas, ox + 2, head_top_y + 2, straw_sh)
        put_px(canvas, ox + 13, head_top_y + 2, straw_sh)
    elif cfg.hat_style == "bone":
        cap_rgb = hex_to_rgb(cfg.shirt_color)
        cap_c = (cap_rgb[0], cap_rgb[1], cap_rgb[2], 255)
        cap_sh = (max(0, int(cap_rgb[0] * 0.65)), max(0, int(cap_rgb[1] * 0.65)), max(0, int(cap_rgb[2] * 0.65)), 255)
        fill_rect(canvas, ox + 3, head_top_y - 1, 10, 3, cap_sh)
        fill_rect(canvas, ox + 4, head_top_y - 1, 8, 2, cap_c)
        visor_x = ox + 2 if flip_x else ox + 5
        fill_rect(canvas, visor_x, head_top_y + 1, 9, 1, cap_sh)
    elif cfg.hat_style == "flor":
        fx = ox + 4 if flip_x else ox + 11
        fy = head_top_y + 2
        put_px(canvas, fx, fy, (255, 215, 50, 255))
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            put_px(canvas, fx + dx, fy + dy, (255, 250, 250, 255))

    # Props e Efeitos das Ações Stardew Valley
    torso_y = oy + 15
    if action == "water_crops":
        can_c = (130, 155, 185, 255)
        can_sh = (75, 95, 120, 255)
        fill_rect(canvas, ox + 14, torso_y + 2, 4, 4, can_c)
        fill_rect(canvas, ox + 14, torso_y + 5, 4, 1, can_sh)
        put_px(canvas, ox + 18, torso_y + 3, can_c)
        put_px(canvas, ox + 19, torso_y + 2, (215, 65, 65, 255))
        if frame_idx in (1, 2, 3):
            drop_c = (95, 190, 255, 255)
            put_px(canvas, ox + 18, torso_y + 5 + (frame_idx % 2), drop_c)
            put_px(canvas, ox + 19, torso_y + 6 + (frame_idx % 3), drop_c)
        sprout_g = (75, 185, 65, 255)
        put_px(canvas, ox + 18, 33, sprout_g)
        put_px(canvas, ox + 18, 32, sprout_g)
        if frame_idx >= 2:
            put_px(canvas, ox + 17, 31, sprout_g)
            put_px(canvas, ox + 19, 31, sprout_g)
        if frame_idx == 3:
            put_px(canvas, ox + 18, 30, (255, 215, 55, 255))

    elif action == "coffee_break":
        cup_y = oy + (9 if frame_idx in (1, 2) else 15)
        cup_x = ox + (6 if frame_idx in (1, 2) else 11)
        fill_rect(canvas, cup_x, cup_y, 3, 3, (245, 238, 225, 255))
        put_px(canvas, cup_x + 3, cup_y + 1, (195, 185, 175, 255))
        put_px(canvas, cup_x + 1, cup_y, (95, 50, 25, 255))
        steam_y = cup_y - 2 - (frame_idx % 2)
        put_px(canvas, cup_x + 1, steam_y, (255, 255, 255, 200))
        put_px(canvas, cup_x + 2, steam_y - 1, (255, 255, 255, 150))

    elif action == "fishing":
        rod_c = (185, 130, 60, 255)
        for i in range(6):
            put_px(canvas, ox + 13 + i, torso_y + 2 - i, rod_c)
        line_x = ox + 18
        for ly in range(torso_y - 3, 32):
            put_px(canvas, line_x, ly, (220, 235, 245, 185))
        bobber_y = 32 + (1 if frame_idx in (1, 3) else 0)
        put_px(canvas, line_x, bobber_y, (230, 55, 55, 255))
        put_px(canvas, line_x, bobber_y + 1, (252, 250, 245, 255))
        if frame_idx == 3:
            fill_rect(canvas, ox + 7, 0, 2, 3, (255, 220, 40, 255))
            fill_rect(canvas, ox + 7, 4, 2, 1, (255, 220, 40, 255))

    elif action == "happy_dance":
        hy = 0 if frame_idx in (1, 3) else 1
        heart_c = (235, 50, 70, 255)
        heart_hi = (255, 155, 170, 255)
        for hx, hdy in [
            (6, 0), (7, 0), (9, 0), (10, 0),
            (5, 1), (6, 1), (7, 1), (8, 1), (9, 1), (10, 1), (11, 1),
            (6, 2), (7, 2), (8, 2), (9, 2), (10, 2),
            (7, 3), (8, 3), (9, 3),
            (8, 4),
        ]:
            put_px(canvas, ox + hx, hy + hdy, heart_c)
        put_px(canvas, ox + 6, hy + 1, heart_hi)

    elif action == "sleep_sit":
        z_c = (155, 205, 255, 240)
        zy = 3 - (frame_idx % 3)
        zx = ox + 13 + (frame_idx % 2)
        for dx, dy in [(0, 0), (1, 0), (2, 0), (1, 1), (0, 2), (1, 2), (2, 2)]:
            put_px(canvas, zx + dx, zy + dy, z_c)

    return canvas


def generate_full_spritesheet(cfg: AvatarConfig) -> Image.Image:
    """
    Gera a Sprite Sheet completa contendo todas as 8 animações x 4 quadros (96 x 288 px).
    """
    sheet = Image.new("RGBA", (CELL_W * COLS, CELL_H * ROWS), (0, 0, 0, 0))
    for action, row_idx in ANIMATION_ROWS.items():
        for col_idx in range(COLS):
            frame = draw_character_frame(cfg, action, col_idx)
            sheet.paste(frame, (col_idx * CELL_W, row_idx * CELL_H))
    return sheet


def extract_animation_frames(sheet: Image.Image, action: str, scale: int = 4) -> List[Image.Image]:
    row_idx = ANIMATION_ROWS.get(action, 0)
    frames = []
    for col_idx in range(COLS):
        x1 = col_idx * CELL_W
        y1 = row_idx * CELL_H
        cell = sheet.crop((x1, y1, x1 + CELL_W, y1 + CELL_H))
        if scale != 1:
            cell = cell.resize((CELL_W * scale, CELL_H * scale), Image.Resampling.NEAREST)
        frames.append(cell)
    return frames


def generate_modular_portrait(cfg: AvatarConfig) -> Image.Image:
    """
    Gera um retrato 64x64 em pixel art estilo caixa de diálogo do Stardew Valley
    usando o fundo diurno oficial (background.png) e o busto autêntico do personagem.
    """
    frame_24 = draw_character_frame(cfg, "idle", 0)
    bust = frame_24.crop((4, 2, 20, 20)).resize((56, 56), Image.Resampling.NEAREST)

    portrait = Image.new("RGBA", (64, 64), (72, 40, 20, 255))
    inner = Image.new("RGBA", (60, 60), (217, 158, 91, 255))

    bg_path = os.path.join(VANILLA_DIR, "background.png")
    if os.path.exists(bg_path):
        bg = Image.open(bg_path).convert("RGBA").crop((0, 0, 128, 128)).resize((56, 56), Image.Resampling.NEAREST)
    else:
        bg = Image.new("RGBA", (56, 56), (205, 232, 248, 255))
        draw = ImageDraw.Draw(bg)
        draw.rectangle([0, 40, 56, 56], fill=(115, 185, 95, 255))

    portrait.paste(inner, (2, 2))
    portrait.paste(bg, (4, 4))
    portrait.paste(bust, (4, 4), bust)
    return portrait
