"""
Importador e Gerador de Animações a partir de Folhas de Sprites 4x6 (ou NxM)
geradas por IA (ex: Gemini / Imagen / ChatGPT).
Realiza:
- Remoção inteligente de fundo sólido;
- Recorte e alinhamento automático dos pés/centro de cada um dos 24 bonequinhos;
- Classificação automática de direção (frente, costas, esquerda, direita);
- Construção das 8 animações de área de trabalho com props estilo Stardew Valley.
"""

import os
from typing import List, Tuple, Dict
import numpy as np
from PIL import Image, ImageOps, ImageDraw


IMPORT_CELL_W = 48
IMPORT_CELL_H = 72
IMPORT_COLS = 4
IMPORT_ROWS = 8


def remove_solid_background(img: Image.Image, tolerance: float = 32.0) -> Image.Image:
    """
    Remove o fundo sólido de uma imagem de sprite sheet usando distância RGB
    combinada com preservação de cromaticidade (evita remover cinzas/pretos neutros
    de roupas escuras quando o fundo é colorido/esverdeado).
    """
    rgb_img = ImageOps.exif_transpose(img).convert("RGB")
    arr = np.array(rgb_img, dtype=np.float32)

    border = np.vstack([
        arr[0:8, :, :].reshape(-1, 3),
        arr[-8:, :, :].reshape(-1, 3),
        arr[:, 0:8, :].reshape(-1, 3),
        arr[:, -8:, :].reshape(-1, 3),
    ])
    bg_rgb = np.median(border, axis=0)

    dist = np.linalg.norm(arr - bg_rgb, axis=2)
    # Diferença de matiz/cromaticidade (R-G e R-B) em relação ao fundo
    rg_diff = np.abs((arr[:, :, 0] - arr[:, :, 1]) - (bg_rgb[0] - bg_rgb[1]))
    rb_diff = np.abs((arr[:, :, 0] - arr[:, :, 2]) - (bg_rgb[0] - bg_rgb[2]))
    is_bg = (dist <= tolerance) & (rg_diff <= 14.0) & (rb_diff <= 14.0)

    alpha = np.where(is_bg, 0, 255).astype(np.uint8)
    rgba = np.dstack([arr.astype(np.uint8), alpha])
    return Image.fromarray(rgba, "RGBA")


def _remove_cell_background(cell_rgb: Image.Image, tolerance: float = 34.0) -> Image.Image:
    """
    Remove o fundo local de uma única célula (suporta tanto fundo uniforme quanto
    fundos em tabuleiro/checkerboard onde cada célula tem um tom de fundo próprio).
    """
    arr = np.array(cell_rgb.convert("RGB"), dtype=np.float32)
    h, w, _ = arr.shape
    m = max(2, min(6, w // 20))
    border = np.vstack([
        arr[0:m, :, :].reshape(-1, 3),
        arr[-m:, :, :].reshape(-1, 3),
        arr[:, 0:m, :].reshape(-1, 3),
        arr[:, -m:, :].reshape(-1, 3),
    ])
    bg_rgb = np.median(border, axis=0)

    dist = np.linalg.norm(arr - bg_rgb, axis=2)
    rg_diff = np.abs((arr[:, :, 0] - arr[:, :, 1]) - (bg_rgb[0] - bg_rgb[1]))
    rb_diff = np.abs((arr[:, :, 0] - arr[:, :, 2]) - (bg_rgb[0] - bg_rgb[2]))
    is_bg = (dist <= tolerance) & (rg_diff <= 16.0) & (rb_diff <= 16.0)

    alpha = np.where(is_bg, 0, 255).astype(np.uint8)
    rgba = np.dstack([arr.astype(np.uint8), alpha])
    return Image.fromarray(rgba, "RGBA")


def extract_grid_sprites(
    sheet_rgba: Image.Image,
    grid_rows: int = 4,
    grid_cols: int = 6,
    cell_size: Tuple[int, int] = (IMPORT_CELL_W, IMPORT_CELL_H),
) -> List[List[Image.Image]]:
    """
    Divide a folha (ex: 4 linhas x 6 colunas) em 24 sprites individuais,
    removendo o fundo local de cada célula, redimensionando com Nearest Neighbor
    e alinhando todos pela linha dos pés.
    """
    W, H = sheet_rgba.size
    col_w = W / float(grid_cols)
    row_h = H / float(grid_rows)
    tw, th = cell_size

    raw_crops: List[List[Image.Image]] = []
    heights: List[int] = []

    for r in range(grid_rows):
        row_list = []
        for c in range(grid_cols):
            # Margem interna de 4px para evitar linhas divisórias entre células
            x1 = int(c * col_w) + 4
            y1 = int(r * row_h) + 4
            x2 = int((c + 1) * col_w) - 4
            y2 = int((r + 1) * row_h) - 4
            raw_cell = sheet_rgba.crop((x1, y1, x2, y2))
            cell = _remove_cell_background(raw_cell)
            bbox = cell.getbbox()
            if bbox:
                cropped = cell.crop(bbox)
                heights.append(cropped.height)
                row_list.append(cropped)
            else:
                row_list.append(Image.new("RGBA", (16, 16), (0, 0, 0, 0)))
        raw_crops.append(row_list)

    ref_h = float(np.median(heights)) if heights else 460.0
    desired_char_h = int(th * 0.78)  # ~56px de altura em uma célula de 72px
    scale_factor = desired_char_h / ref_h

    normalized_grid: List[List[Image.Image]] = []
    for r in range(grid_rows):
        norm_row = []
        for c in range(grid_cols):
            spr = raw_crops[r][c]
            nw = max(1, int(round(spr.width * scale_factor)))
            nh = max(1, int(round(spr.height * scale_factor)))
            spr_small = spr.resize((nw, nh), Image.Resampling.NEAREST)

            canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            px = (tw - nw) // 2
            py = (th - 4) - nh
            canvas.paste(spr_small, (px, py), spr_small)
            norm_row.append(canvas)
        normalized_grid.append(norm_row)

    return normalized_grid


def classify_sprite_direction(cell_rgba: Image.Image) -> str:
    """
    Classifica automaticamente para qual direção o bonequinho está olhando:
    'front', 'back', 'left' ou 'right' analisando a distribuição da pele do rosto e óculos.
    """
    arr = np.array(cell_rgba)
    bbox = cell_rgba.getbbox()
    if not bbox:
        return "front"
    x1, y1, x2, y2 = bbox
    h = y2 - y1
    hy1 = y1 + int(h * 0.14)
    hy2 = y1 + int(h * 0.43)
    head = arr[hy1:hy2, x1:x2]
    opaque = head[:, :, 3] > 128
    total_head = int(np.count_nonzero(opaque))
    if total_head == 0:
        return "front"

    r = head[:, :, 0].astype(np.float32)
    g = head[:, :, 1].astype(np.float32)
    b = head[:, :, 2].astype(np.float32)

    # 1. Pele clara/rosada (diferenciando de cabelo loiro/dourado onde G > B * 1.38)
    light_skin = opaque & (r > 185) & (g > 125) & (b > 95) & ((r - b) > 35) & (g > b * 1.12) & (g < b * 1.38)
    # 2. Pele morena/bronzeada ou lentes claras de óculos (quando não há cabelo loiro dominante)
    blond_pixels = int(np.count_nonzero(opaque & (r > 170) & (g > 125) & (b < 95) & (g > b * 1.42)))
    is_light_skin_mode = int(np.count_nonzero(light_skin)) >= max(4, int(total_head * 0.10)) or blond_pixels > int(total_head * 0.25)
    if is_light_skin_mode:
        face_mask = light_skin
    else:
        tan_skin = opaque & (r > 160) & (g > 90) & (b > 50) & ((r - b) > 45) & ((r - g) > 30)
        glasses_lens = opaque & (r > 130) & (g > 145) & (b > 145) & (np.abs(r - g) < 35) & (np.abs(g - b) < 35)
        face_mask = tan_skin | glasses_lens

    skin_count = int(np.count_nonzero(face_mask))
    skin_ratio = skin_count / float(total_head)

    if skin_ratio < 0.13:
        return "back"

    if not is_light_skin_mode:
        eyes_band = head[int(head.shape[0] * 0.28):int(head.shape[0] * 0.68), :]
        er = eyes_band[:, :, 0].astype(np.float32)
        eg = eyes_band[:, :, 1].astype(np.float32)
        eb = eyes_band[:, :, 2].astype(np.float32)
        ea = eyes_band[:, :, 3] > 128
        lens_count = int(np.count_nonzero(ea & (er > 125) & (eg > 140) & (eb > 140) & (np.abs(er - eg) < 35)))
        if lens_count >= 13:
            return "front"

    ys, xs = np.where(face_mask)
    rel_x = float(np.mean(xs)) / float(head.shape[1])
    if rel_x < 0.45:
        return "left"
    elif rel_x > 0.525:
        return "right"
    return "front"


def _put_block(img: Image.Image, bx: int, by: int, color: Tuple[int, int, int, int], block_size: int = 2):
    for dy in range(block_size):
        for dx in range(block_size):
            px, py = bx + dx, by + dy
            if 0 <= px < img.width and 0 <= py < img.height:
                img.putpixel((px, py), color)


def _draw_scaled_props(cell: Image.Image, action: str, frame_idx: int):
    """Desenha os props e emotes do Stardew Valley na escala 48x72 (blocos 2x2)."""
    tw, th = cell.size
    # Sombra oval suave aos pés do personagem
    draw = ImageDraw.Draw(cell)

    if action == "water_crops":
        # Regador à direita + gotas de água + plantinha brotando
        can_c = (130, 155, 185, 255)
        can_sh = (75, 95, 120, 255)
        ox, oy = 35, 42
        for dx in range(0, 6, 2):
            for dy in range(0, 6, 2):
                _put_block(cell, ox + dx, oy + dy, can_c if dy < 4 else can_sh)
        _put_block(cell, ox + 6, oy + 2, can_c)
        _put_block(cell, ox + 8, oy, (215, 65, 65, 255))
        if frame_idx in (1, 2, 3):
            drop_c = (95, 190, 255, 255)
            _put_block(cell, ox + 8, oy + 6 + (frame_idx % 2) * 2, drop_c)
            _put_block(cell, ox + 10, oy + 10 + (frame_idx % 3) * 2, drop_c)
        sprout_g = (75, 185, 65, 255)
        _put_block(cell, ox + 8, 66, sprout_g)
        _put_block(cell, ox + 8, 64, sprout_g)
        if frame_idx >= 2:
            _put_block(cell, ox + 6, 62, sprout_g)
            _put_block(cell, ox + 10, 62, sprout_g)
        if frame_idx == 3:
            _put_block(cell, ox + 8, 60, (255, 215, 55, 255))

    elif action == "coffee_break":
        # Caneca de Café Expresso + vapor subindo
        cup_y = 34 if frame_idx in (1, 2) else 40
        cup_x = 32
        for dx in range(0, 6, 2):
            for dy in range(0, 6, 2):
                _put_block(cell, cup_x + dx, cup_y + dy, (245, 238, 225, 255))
        _put_block(cell, cup_x + 6, cup_y + 2, (195, 185, 175, 255))
        _put_block(cell, cup_x + 2, cup_y, (95, 50, 25, 255))
        steam_y = cup_y - 4 - (frame_idx % 2) * 2
        _put_block(cell, cup_x + 2, steam_y, (255, 255, 255, 210))
        _put_block(cell, cup_x + 4, steam_y - 3, (255, 255, 255, 160))

    elif action == "fishing":
        # Vara de pesca de bambu + linha + boia + alerta !
        rod_c = (185, 130, 60, 255)
        ox, oy = 33, 42
        for i in range(5):
            _put_block(cell, ox + i * 2, oy - i * 2, rod_c)
        line_x = ox + 8
        for ly in range(oy - 6, 64, 2):
            _put_block(cell, line_x, ly, (220, 235, 245, 185), block_size=1)
        bobber_y = 64 + (2 if frame_idx in (1, 3) else 0)
        _put_block(cell, line_x - 1, bobber_y, (230, 55, 55, 255))
        _put_block(cell, line_x - 1, bobber_y + 2, (252, 250, 245, 255))
        if frame_idx == 3:
            _put_block(cell, 22, 2, (255, 220, 40, 255))
            _put_block(cell, 22, 4, (255, 220, 40, 255))
            _put_block(cell, 22, 8, (255, 220, 40, 255))

    elif action == "happy_dance":
        # Coração vermelho do Stardew Valley flutuando acima da cabeça!
        hy = 1 if frame_idx in (1, 3) else 3
        hx_base = 17
        heart_c = (235, 50, 70, 255)
        heart_hi = (255, 155, 170, 255)
        for hx, hdy in [
            (1, 0), (2, 0), (4, 0), (5, 0),
            (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1),
            (1, 2), (2, 2), (3, 2), (4, 2), (5, 2),
            (2, 3), (3, 3), (4, 3),
            (3, 4),
        ]:
            _put_block(cell, hx_base + hx * 2, hy + hdy * 2, heart_c)
        _put_block(cell, hx_base + 2, hy + 2, heart_hi)

    elif action == "sleep_sit":
        # Zzz flutuando
        z_c = (155, 205, 255, 245)
        zy = 6 - (frame_idx % 3) * 2
        zx = 34 + (frame_idx % 2) * 2
        for dx, dy in [(0, 0), (1, 0), (2, 0), (1, 1), (0, 2), (1, 2), (2, 2)]:
            _put_block(cell, zx + dx * 2, zy + dy * 2, z_c)


def build_animations_from_4x6_image(
    image_path: str,
    grid_rows: int = 4,
    grid_cols: int = 6,
) -> Tuple[Image.Image, Image.Image, Dict[str, str]]:
    """
    Carrega uma imagem de sprites 4x6 (como as geradas pelo Gemini),
    remove o fundo, classifica os 24 quadros e monta:
    1. A Sprite Sheet completa de 8 animações x 4 quadros (192 x 576 px);
    2. O Retrato 64x64 em moldura de diálogo do Stardew Valley;
    3. Um resumo das cores e contagens detectadas.
    """
    raw_img = Image.open(image_path)
    rgba_sheet = remove_solid_background(raw_img)
    grid = extract_grid_sprites(rgba_sheet, grid_rows=grid_rows, grid_cols=grid_cols)

    by_dir: Dict[str, List[Image.Image]] = {
        "front": [],
        "right": [],
        "left": [],
        "back": [],
    }
    for r in range(grid_rows):
        for c in range(grid_cols):
            cell_img = grid[r][c]
            d = classify_sprite_direction(cell_img)
            by_dir[d].append(cell_img)

    # Garantir fallbacks caso alguma direção tenha menos quadros
    if not by_dir["front"]:
        by_dir["front"] = [grid[0][0]]
    if not by_dir["right"]:
        if by_dir["left"]:
            by_dir["right"] = [ImageOps.mirror(f) for f in by_dir["left"]]
        else:
            by_dir["right"] = by_dir["front"]
    if not by_dir["left"]:
        by_dir["left"] = [ImageOps.mirror(f) for f in by_dir["right"]]
    if not by_dir["back"]:
        by_dir["back"] = by_dir["front"]

    front_list = by_dir["front"]
    right_list = by_dir["right"]
    left_list = by_dir["left"]

    if grid_rows == 4 and grid_cols == 6:
        # Nas grades 4x6 geradas pelo Gemini (prompt padrão do projeto), as posições seguem exatamente a estrutura:
        # - Linha 0, Cols 0..2: Frente (parado e passos frontais)
        # - Linha 0, Cols 3..5: 3/4 Direita
        # - Linha 1, Cols 0..3: Costas
        # - Linha 2, Cols 2..5: Ciclo completo de 4 quadros caminhando em perfil para a DIREITA
        # - Linha 2, Cols 0..1 e Linha 3, Cols 0..2: Quadros caminhando em perfil para a ESQUERDA
        idle_base = grid[0][0]
        idle_bob = Image.new("RGBA", (IMPORT_CELL_W, IMPORT_CELL_H), (0, 0, 0, 0))
        idle_bob.paste(idle_base, (0, 1), idle_base)
        idle_frames = [
            grid[0][0].copy(),
            idle_bob.copy(),
            grid[0][1].copy() if classify_sprite_direction(grid[0][1]) == "front" else grid[0][0].copy(),
            idle_bob.copy(),
        ]

        # Ciclo completo de 4 passos para a DIREITA está sempre em Row 3 Cols 3..5 + Row 2 Cols 3..5
        walk_right_frames = [grid[2][3].copy(), grid[2][4].copy(), grid[2][5].copy(), grid[3][5].copy()]

        # Para a ESQUERDA: Row 2 Col 1 e Row 3 Col 1 são perfis esquerdos com passo; completamos o ciclo com espelhamento de Row 2 Cols 4..5
        walk_left_frames = [
            grid[2][1].copy(),
            ImageOps.mirror(grid[2][4]),
            grid[3][1].copy(),
            ImageOps.mirror(grid[2][5]),
        ]

        front_list = [grid[0][0], grid[0][1], grid[0][2]]
        right_list = walk_right_frames
    else:
        # 1. Idle (usa o primeiro quadro frontal com leve respiração no quadro 1 e 2)
        idle_base = front_list[0]
        idle_bob = Image.new("RGBA", (IMPORT_CELL_W, IMPORT_CELL_H), (0, 0, 0, 0))
        idle_bob.paste(idle_base, (0, 1), idle_base)
        idle_frames = [idle_base.copy(), idle_bob.copy(), idle_base.copy(), idle_bob.copy()]

        # 2. Walk Right
        if len(right_list) >= 4:
            start_r = 2 if len(right_list) >= 6 else 0
            walk_right_frames = [right_list[(start_r + i) % len(right_list)].copy() for i in range(4)]
        else:
            walk_right_frames = [right_list[i % len(right_list)].copy() for i in range(4)]

        # 3. Walk Left
        pure_left = left_list[-3:] if len(left_list) >= 4 else left_list
        if len(pure_left) >= 4:
            walk_left_frames = [pure_left[i].copy() for i in range(4)]
        elif len(pure_left) == 3:
            walk_left_frames = [pure_left[0].copy(), pure_left[1].copy(), pure_left[2].copy(), pure_left[1].copy()]
        else:
            walk_left_frames = [ImageOps.mirror(f) for f in walk_right_frames]

    # 4. Water Crops (usa os primeiros quadros 3/4 ou perfil direito)
    water_frames = [
        right_list[0].copy(),
        right_list[min(1, len(right_list) - 1)].copy(),
        right_list[min(2, len(right_list) - 1)].copy(),
        right_list[0].copy(),
    ]

    # 5. Coffee Break (usa os quadros frontais)
    coffee_frames = [
        front_list[0].copy(),
        front_list[min(1, len(front_list) - 1)].copy(),
        front_list[min(1, len(front_list) - 1)].copy(),
        front_list[0].copy(),
    ]

    # 6. Fishing (usa quadros direitos)
    fish_frames = [
        right_list[0].copy(),
        right_list[min(1, len(right_list) - 1)].copy(),
        right_list[0].copy(),
        right_list[min(2, len(right_list) - 1)].copy(),
    ]

    # 7. Happy Dance (usa os quadros frontais/3-quartos pulando de alegria!)
    dance_frames = []
    for i in range(4):
        src = front_list[i % len(front_list)]
        cell = Image.new("RGBA", (IMPORT_CELL_W, IMPORT_CELL_H), (0, 0, 0, 0))
        jump_y = -4 if i in (1, 3) else 0
        cell.paste(src, (0, jump_y), src)
        dance_frames.append(cell)

    # 8. Sleep / Sit (repouso frontal com Zzz)
    sleep_frames = [idle_base.copy(), idle_base.copy(), idle_bob.copy(), idle_bob.copy()]

    all_rows = [
        ("idle", idle_frames),
        ("walk_right", walk_right_frames),
        ("walk_left", walk_left_frames),
        ("water_crops", water_frames),
        ("coffee_break", coffee_frames),
        ("fishing", fish_frames),
        ("happy_dance", dance_frames),
        ("sleep_sit", sleep_frames),
    ]

    full_sheet = Image.new("RGBA", (IMPORT_CELL_W * IMPORT_COLS, IMPORT_CELL_H * IMPORT_ROWS), (0, 0, 0, 0))
    for row_idx, (act_name, frames) in enumerate(all_rows):
        for col_idx, frame in enumerate(frames):
            cell_copy = frame.copy()
            _draw_scaled_props(cell_copy, act_name, col_idx)
            full_sheet.paste(cell_copy, (col_idx * IMPORT_CELL_W, row_idx * IMPORT_CELL_H))

    # Construir Retrato 64x64 em moldura de diálogo do Stardew Valley a partir do busto frontal
    portrait = Image.new("RGBA", (64, 64), (72, 40, 20, 255))
    inner = Image.new("RGBA", (60, 60), (217, 158, 91, 255))
    bg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "stardew_vanilla", "background.png")
    if os.path.exists(bg_path):
        bg = Image.open(bg_path).convert("RGBA").crop((0, 0, 128, 128)).resize((56, 56), Image.Resampling.NEAREST)
    else:
        bg = Image.new("RGBA", (56, 56), (205, 232, 248, 255))
    # Recortar busto (cabeça + colar + ombros) do primeiro quadro frontal
    bust_crop = idle_base.crop((6, 10, 42, 46)).resize((56, 56), Image.Resampling.NEAREST)
    portrait.paste(inner, (2, 2))
    portrait.paste(bg, (4, 4))
    portrait.paste(bust_crop, (4, 4), bust_crop)

    stats = {
        "front_count": str(len(front_list)),
        "right_count": str(len(right_list)),
        "left_count": str(len(left_list)),
        "back_count": str(len(by_dir["back"])),
    }
    return full_sheet, portrait, stats
