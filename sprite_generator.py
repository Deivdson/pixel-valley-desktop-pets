"""
Gerador Procedural 100% Autoral de Sprites em Pixel Art (16x32 dentro de célula 24x36).
Projeto de fã independente inspirado na estética de jogos de fazenda 16-bit (sem uso de
qualquer arquivo gráfico proprietário externo).
"""

import os
from typing import Tuple, Dict, List
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from photo_analyzer import (
    AvatarConfig,
    hex_to_rgb,
    HAIR_STYLE_TO_SDV_INDEX,
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


def put_px(img: Image.Image, x: int, y: int, color: Tuple[int, int, int, int]):
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), color)


def fill_rect(img: Image.Image, x1: int, y1: int, w: int, h: int, color: Tuple[int, int, int, int]):
    for yy in range(y1, y1 + h):
        for xx in range(x1, x1 + w):
            put_px(img, xx, yy, color)


def _shade_rgba(rgb: Tuple[int, int, int], factor: float) -> Tuple[int, int, int, int]:
    r, g, b = rgb
    if factor < 1.0:
        return (
            max(0, int(r * factor)),
            max(0, int(g * (factor * 0.94))),
            max(0, int(b * (factor * 0.90))),
            255,
        )
    return (
        min(255, int(r + (255 - r) * (factor - 1.0))),
        min(255, int(g + (255 - g) * (factor - 1.0))),
        min(255, int(b + (255 - b) * (factor - 1.0) * 0.85)),
        255,
    )


def _warm_outline(rgb: Tuple[int, int, int]) -> Tuple[int, int, int, int]:
    r, g, b = rgb
    return (
        max(18, int(r * 0.36)),
        max(12, int(g * 0.26)),
        max(16, int(b * 0.30)),
        255,
    )


def _render_procedural_16x32(
    cfg: AvatarConfig,
    dir_row: int,
    step_phase: int,
    arms_up: bool = False,
    bob_px: int = 0,
    blink: bool = False,
    flip_x: bool = False,
) -> Image.Image:
    """
    Desenha proceduralmente um personagem Chibi 16x32 100% original (zero arquivos externos),
    suportando tons de pele, estilos de cabelo, barba, óculos, roupas e animações de caminhada.
    """
    canvas = Image.new("RGBA", (16, 32), (0, 0, 0, 0))

    skin_rgb = hex_to_rgb(cfg.skin_color)
    s_base = _shade_rgba(skin_rgb, 1.0)
    s_hi = _shade_rgba(skin_rgb, 1.12)
    s_sh = _shade_rgba(skin_rgb, 0.82)
    s_out = _warm_outline(skin_rgb)

    hair_rgb = hex_to_rgb(cfg.hair_color)
    h_base = _shade_rgba(hair_rgb, 1.0)
    h_hi = _shade_rgba(hair_rgb, 1.22)
    h_sh = _shade_rgba(hair_rgb, 0.75)
    h_out = _warm_outline(hair_rgb)

    eye_rgb = hex_to_rgb(cfg.eye_color)
    eye_c = (eye_rgb[0], eye_rgb[1], eye_rgb[2], 255)
    eye_dark = _shade_rgba(eye_rgb, 0.55)
    white = (250, 246, 240, 255)

    shirt_rgb = hex_to_rgb(cfg.shirt_color)
    sh_base = _shade_rgba(shirt_rgb, 1.0)
    sh_hi = _shade_rgba(shirt_rgb, 1.16)
    sh_sh = _shade_rgba(shirt_rgb, 0.78)
    sh_out = _warm_outline(shirt_rgb)

    pants_rgb = hex_to_rgb(cfg.pants_color)
    p_base = _shade_rgba(pants_rgb, 1.0)
    p_sh = _shade_rgba(pants_rgb, 0.76)
    p_out = _warm_outline(pants_rgb)

    boots_base = (86, 48, 28, 255)
    boots_hi = (118, 68, 40, 255)
    boots_out = (42, 20, 12, 255)

    by = bob_px

    # ==================== 1. CABEÇA E ROSTO (Y=4..13) ====================
    for y in range(4, 14):
        for x in range(4, 12):
            if y == 13 and x in (4, 11):
                continue
            if y in (4, 5):
                c = s_hi
            elif y >= 11 or x in (4, 11):
                c = s_sh
            else:
                c = s_base
            put_px(canvas, x, y + by, c)

    for x in range(5, 11):
        put_px(canvas, x, 13 + by, s_out)
    put_px(canvas, 4, 12 + by, s_out)
    put_px(canvas, 11, 12 + by, s_out)

    # Orelhas
    if dir_row == 0:
        put_px(canvas, 3, 8 + by, s_sh)
        put_px(canvas, 3, 9 + by, s_out)
        put_px(canvas, 12, 8 + by, s_sh)
        put_px(canvas, 12, 9 + by, s_out)
    else:
        put_px(canvas, 5, 8 + by, s_sh)
        put_px(canvas, 5, 9 + by, s_out)
        put_px(canvas, 12, 9 + by, s_base)
        put_px(canvas, 12, 10 + by, s_out)

    # ==================== 2. OLHOS (Y=8..9) ====================
    if dir_row == 0:
        put_px(canvas, 5, 7 + by, h_out)
        put_px(canvas, 6, 7 + by, h_sh)
        put_px(canvas, 9, 7 + by, h_sh)
        put_px(canvas, 10, 7 + by, h_out)
        if blink:
            for ex in (5, 6, 9, 10):
                put_px(canvas, ex, 8 + by, s_base)
                put_px(canvas, ex, 9 + by, s_out)
        else:
            put_px(canvas, 5, 8 + by, white)
            put_px(canvas, 5, 9 + by, s_sh)
            put_px(canvas, 6, 8 + by, eye_dark)
            put_px(canvas, 6, 9 + by, eye_c)
            put_px(canvas, 9, 8 + by, eye_dark)
            put_px(canvas, 9, 9 + by, eye_c)
            put_px(canvas, 10, 8 + by, white)
            put_px(canvas, 10, 9 + by, s_sh)
    else:
        put_px(canvas, 9, 7 + by, h_sh)
        put_px(canvas, 10, 7 + by, h_out)
        put_px(canvas, 9, 8 + by, white)
        put_px(canvas, 9, 9 + by, s_sh)
        put_px(canvas, 10, 8 + by, eye_dark)
        put_px(canvas, 10, 9 + by, eye_c)

    # ==================== 3. BARBA / BIGODE ====================
    if cfg.beard_style != "sem_barba":
        if dir_row == 0:
            for bx_p in range(6, 10):
                put_px(canvas, bx_p, 11 + by, h_base)
            if cfg.beard_style in ("cavanhaque", "barba_cheia"):
                for bx_p in range(6, 10):
                    put_px(canvas, bx_p, 12 + by, h_sh)
                    put_px(canvas, bx_p, 13 + by, h_out)
            if cfg.beard_style == "barba_cheia":
                for bx_p in (4, 5, 10, 11):
                    put_px(canvas, bx_p, 10 + by, h_base)
                    put_px(canvas, bx_p, 11 + by, h_sh)
                    put_px(canvas, bx_p, 12 + by, h_out)
        else:
            put_px(canvas, 10, 11 + by, h_base)
            put_px(canvas, 11, 11 + by, h_out)
            if cfg.beard_style in ("cavanhaque", "barba_cheia"):
                for bx_p in range(8, 12):
                    put_px(canvas, bx_p, 12 + by, h_sh)
                    put_px(canvas, bx_p, 13 + by, h_out)

    # ==================== 4. ÓCULOS ====================
    if cfg.glasses_style != "nenhum":
        g_frame = (38, 34, 44, 255)
        g_lens = (30, 36, 46, 235) if cfg.glasses_style == "escuro" else (185, 225, 250, 150)
        if dir_row == 0:
            for gx in range(4, 12):
                put_px(canvas, gx, 7 + by, g_frame)
            for gx in (4, 7, 8, 11):
                put_px(canvas, gx, 8 + by, g_frame)
                put_px(canvas, gx, 9 + by, g_frame)
            for gx in (5, 6, 9, 10):
                put_px(canvas, gx, 10 + by, g_frame)
                if cfg.glasses_style == "escuro":
                    put_px(canvas, gx, 8 + by, g_lens)
                    put_px(canvas, gx, 9 + by, g_lens)
        else:
            for gx in range(6, 12):
                put_px(canvas, gx, 7 + by, g_frame)
            put_px(canvas, 8, 8 + by, g_frame)
            put_px(canvas, 11, 8 + by, g_frame)
            put_px(canvas, 9, 10 + by, g_frame)
            put_px(canvas, 10, 10 + by, g_frame)

    # ==================== 5. CABELO PROCEDURAL ====================
    style = cfg.hair_style
    if style == "custom":
        idx = cfg.hair_index % 6
        style = ["curto", "topete", "medio", "longo", "cacheado", "coque"][idx]

    if style != "careca":
        top_start = 1 if style in ("topete", "cacheado", "coque") else 2
        for y in range(top_start, 7):
            for x in range(3, 13):
                if y == top_start and x in (3, 12):
                    continue
                if y == 6 and x in (5, 6, 9, 10) and style != "cacheado":
                    continue
                if y == top_start or x in (3, 12):
                    c = h_out
                elif y == top_start + 1 and 5 <= x <= 10:
                    c = h_hi
                elif y >= 5:
                    c = h_sh
                else:
                    c = h_base
                put_px(canvas, x, y + by, c)

        if style == "cacheado":
            for cx_p, cy_p in [(2, 4), (2, 5), (2, 6), (2, 7), (13, 4), (13, 5), (13, 6), (13, 7), (4, 1), (7, 1), (10, 1)]:
                put_px(canvas, cx_p, cy_p + by, h_out if cx_p in (2, 13) else h_base)
        elif style == "longo":
            max_hy = 16
            for y in range(5, max_hy):
                for lx in (2, 3, 12, 13):
                    if dir_row == 1 and lx in (12, 13) and y > 8:
                        continue
                    put_px(canvas, lx, y + by, h_out if lx in (2, 13) or y == max_hy - 1 else h_base)
        elif style == "medio":
            for y in range(5, 11):
                for lx in (3, 12):
                    put_px(canvas, lx, y + by, h_out if y == 10 else h_sh)
        elif style == "coque":
            for y in range(0, 3):
                for x in range(6, 10):
                    put_px(canvas, x, y + by, h_out if y == 0 or x in (6, 9) else h_hi)

        if dir_row == 1:
            # Nuca coberta pelo cabelo no perfil
            for y in range(4, 11):
                for x in range(3, 7):
                    put_px(canvas, x, y + by, h_out if x == 3 else (h_sh if x == 4 else h_base))

    # ==================== 6. TRONCO E ROUPA (Y=14..21) ====================
    t_left, t_right = (4, 12) if dir_row == 0 else (5, 11)
    for y in range(14, 22):
        for x in range(t_left, t_right):
            if x in (t_left, t_right - 1) or y == 21:
                c = sh_out
            elif y == 14 and x in (7, 8):
                c = s_sh
            elif cfg.outfit_style == "jardineira" and y >= 17 and x in (5, 6, 7, 8, 9, 10):
                c = p_base if y < 20 else p_sh
            elif cfg.outfit_style == "jardineira" and y in (15, 16) and x in (5, 10):
                c = p_base
            elif cfg.outfit_style == "xadrez" and (x + y) % 2 == 0:
                c = sh_sh
            elif cfg.outfit_style == "jaqueta" and x in (7, 8):
                c = white
            else:
                c = sh_hi if y in (15, 16) and x in (6, 9) else sh_base
            put_px(canvas, x, y + by, c)

    # ==================== 7. PERNAS E PASSOS (Y=22..30) ====================
    if dir_row == 0 or step_phase == 0:
        p_left, p_right = (4, 12) if dir_row == 0 else (5, 11)
        for y in range(22, 28):
            for x in range(p_left, p_right):
                if x in (p_left, p_right - 1) or (dir_row == 0 and x in (7, 8) and y >= 24):
                    put_px(canvas, x, y, p_out)
                else:
                    put_px(canvas, x, y, p_base if x % 2 == 1 else p_sh)
        for x in range(p_left, p_right):
            put_px(canvas, x, 28, boots_out if x in (p_left, p_right - 1) else boots_hi)
            put_px(canvas, x, 29, boots_out if x in (p_left, p_right - 1) else boots_base)
            put_px(canvas, x, 30, boots_out)
    else:
        # Pernas abertas caminhando em perfil
        front_lx = 9 if step_phase == 1 else 4
        back_lx = 4 if step_phase == 1 else 9
        for lx_start, ly_off in [(back_lx, 0), (front_lx, -1)]:
            for y in range(22, 28):
                for dx in range(4):
                    px_x = lx_start + dx
                    py_y = y + ly_off
                    put_px(canvas, px_x, py_y, p_out if dx in (0, 3) else p_base)
            for dx in range(4):
                px_x = lx_start + dx
                put_px(canvas, px_x, 28 + ly_off, boots_out if dx in (0, 3) else boots_hi)
                put_px(canvas, px_x, 29 + ly_off, boots_base)
                put_px(canvas, px_x, 30 + ly_off, boots_out)

    # ==================== 8. BRAÇOS ANIMADOS ====================
    if dir_row == 0:
        ay_start = 10 if arms_up else 15
        for dy in range(6):
            y = ay_start + dy + by
            if dy < 4:
                put_px(canvas, 2, y, sh_out)
                put_px(canvas, 3, y, sh_base)
                put_px(canvas, 12, y, sh_base)
                put_px(canvas, 13, y, sh_out)
            else:
                put_px(canvas, 2, y, s_sh if dy == 4 else s_out)
                put_px(canvas, 3, y, s_base if dy == 4 else s_out)
                put_px(canvas, 12, y, s_base if dy == 4 else s_out)
                put_px(canvas, 13, y, s_sh if dy == 4 else s_out)
    else:
        arm_x = 7 + (2 if step_phase == 1 else (-2 if step_phase == 2 else 0))
        for dy in range(6):
            y = 15 + dy + by
            if dy < 4:
                put_px(canvas, arm_x, y, sh_out)
                put_px(canvas, arm_x + 1, y, sh_base)
            else:
                put_px(canvas, arm_x, y, s_base if dy == 4 else s_out)
                put_px(canvas, arm_x + 1, y, s_sh if dy == 4 else s_out)

    if flip_x:
        canvas = ImageOps.mirror(canvas)

    return canvas


def draw_character_frame(
    cfg: AvatarConfig,
    action: str,
    frame_idx: int,
) -> Image.Image:
    """
    Desenha um quadro 24x36 contendo o personagem procedural 16x32
    mais chapéu e ferramentas/efeitos das ações na área de trabalho.
    """
    canvas = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))

    dir_row = 0
    step_phase = 0
    arms_up = False
    bob_px = 0
    blink = False
    flip_x = False
    jump_y = 0

    if action == "idle":
        dir_row = 0
        bob_px = 1 if frame_idx in (1, 2) else 0
        blink = (frame_idx == 3)
    elif action == "walk_right":
        dir_row = 1
        walk_seq = [0, 1, 0, 2]
        step_phase = walk_seq[frame_idx % 4]
        bob_px = 1 if step_phase in (1, 2) else 0
    elif action == "walk_left":
        dir_row = 1
        walk_seq = [0, 1, 0, 2]
        step_phase = walk_seq[frame_idx % 4]
        bob_px = 1 if step_phase in (1, 2) else 0
        flip_x = True
    elif action == "water_crops":
        dir_row = 1
        step_phase = 1 if frame_idx in (1, 2) else 0
        bob_px = 1 if frame_idx in (1, 2) else 0
    elif action == "coffee_break":
        dir_row = 0
        arms_up = frame_idx in (1, 2)
    elif action == "fishing":
        dir_row = 1
        step_phase = 1 if frame_idx == 3 else 0
    elif action == "happy_dance":
        dir_row = 0
        arms_up = frame_idx in (1, 3)
        jump_y = -2 if frame_idx in (1, 3) else 0
    elif action == "sleep_sit":
        dir_row = 0
        blink = True

    char_16x32 = _render_procedural_16x32(
        cfg=cfg,
        dir_row=dir_row,
        step_phase=step_phase,
        arms_up=arms_up,
        bob_px=bob_px,
        blink=blink,
        flip_x=flip_x,
    )

    ox = 4
    oy = 3 + jump_y

    for sx in range(ox + 3, ox + 13):
        put_px(canvas, sx, 34, (20, 15, 25, 95))
    for sx in range(ox + 4, ox + 12):
        put_px(canvas, sx, 33, (20, 15, 25, 65))

    canvas.paste(char_16x32, (ox, oy), char_16x32)

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
    """
    Extrai os 4 quadros de uma animação específica da Sprite Sheet (suporta tanto
    células padrão 24x36 quanto folhas de alta densidade 48x72 importadas de IA 4x6).
    """
    row_idx = ANIMATION_ROWS.get(action, 0)
    cell_w = max(1, sheet.width // COLS)
    cell_h = max(1, sheet.height // ROWS)
    target_w = CELL_W * scale
    target_h = CELL_H * scale
    frames = []
    for col_idx in range(COLS):
        x1 = col_idx * cell_w
        y1 = row_idx * cell_h
        cell = sheet.crop((x1, y1, x1 + cell_w, y1 + cell_h))
        if (cell.width, cell.height) != (target_w, target_h):
            cell = cell.resize((target_w, target_h), Image.Resampling.NEAREST)
        frames.append(cell)
    return frames


def generate_modular_portrait(cfg: AvatarConfig) -> Image.Image:
    """
    Gera um retrato 64x64 em pixel art estilo caixa de diálogo procedural (100% original).
    """
    frame_24 = draw_character_frame(cfg, "idle", 0)
    bust = frame_24.crop((4, 2, 20, 20)).resize((56, 56), Image.Resampling.NEAREST)

    portrait = Image.new("RGBA", (64, 64), (72, 40, 20, 255))
    inner = Image.new("RGBA", (60, 60), (217, 158, 91, 255))

    bg = Image.new("RGBA", (56, 56), (205, 232, 248, 255))
    draw = ImageDraw.Draw(bg)
    draw.rectangle([0, 38, 56, 56], fill=(115, 185, 95, 255))

    portrait.paste(inner, (2, 2))
    portrait.paste(bg, (4, 4))
    portrait.paste(bust, (4, 4), bust)
    return portrait
