"""
Gerador Livre de Sprites em Pixel Art (Estilo Stardew Valley 16x32) a partir de Fotos.
Cria o sprite de forma 100% livre (sem depender dos cabelos/roupas pré-existentes do jogo),
usando:
1. LLM Vision API (Google Gemini / OpenAI / Ollama Local) para desenhar a matriz 16x32 livre;
2. Escultor Pixel-a-Pixel Direto da Silhueta da Foto (Offline / Instantâneo) que extrai o
   formato exato do cabelo, rosto, barba, óculos e roupa da foto e aplica sombreado + contorno
   sel-out no padrão Stardew Valley;
3. Importação/Exportação de Matriz JSON gerada por qualquer LLM.
"""

import os
import json
import base64
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from PIL import Image, ImageOps
import httpx

from photo_analyzer import (
    AvatarConfig,
    detect_face_bbox_skin_chrominance,
    sample_median_rgb,
    rgb_to_hex,
    hex_to_rgb,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LLM_SETTINGS_PATH = os.path.join(BASE_DIR, "llm_settings.json")


DEFAULT_LLM_SETTINGS = {
    "provider": "auto",        # "auto", "gemini", "openai", "ollama", "sculptor_offline"
    "api_key": "",
    "model": "gemini-2.5-flash",
    "ollama_url": "http://localhost:11434",
    "custom_prompt_notes": "",
    # Configurações da Integração de Personalidade GPT Luna
    "luna_enabled": True,
    "luna_provider": "auto",   # "auto", "openai_luna", "gemini_luna", "ollama_luna", "custom_endpoint", "local_luna"
    "luna_model": "gpt-6-luna",
    "luna_api_key": "",
    "luna_endpoint": "https://api.openai.com/v1/chat/completions",
    "luna_mood": "Luna Clássica (Carismática, Espirituosa & Companheira)",
    "luna_autonomous_speech": True,
    "luna_custom_instructions": "",
}


def load_llm_settings() -> Dict[str, Any]:
    settings = dict(DEFAULT_LLM_SETTINGS)
    if os.path.exists(LLM_SETTINGS_PATH):
        try:
            with open(LLM_SETTINGS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            settings.update(saved)
        except Exception:
            pass
    # Também verificar variáveis de ambiente caso o usuário já tenha configurado no Windows
    if not settings["api_key"]:
        settings["api_key"] = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or ""
        )
    if not settings.get("luna_api_key"):
        settings["luna_api_key"] = (
            os.environ.get("LUNA_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or ""
        )
    return settings


def save_llm_settings(settings: Dict[str, Any]):
    with open(LLM_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


STARDEW_LLM_SYSTEM_PROMPT = """Você é um artista especialista em Pixel Art no estilo exato de Stardew Valley (ConcernedApe).
Sua tarefa é observar a foto da pessoa enviada e desenhar LIVREMENTE um personagem Chibi 16x32 pixels que seja o mais parecido possível com essa pessoa específica (capturando o formato exato do cabelo, entradas, franja, cachos, acessórios como fones/brincos/óculos, formato de barba/bigode, expressão e detalhes reais da roupa/gola/estampa), SEM usar templates pré-prontos.

Regras anatômicas obrigatórias do padrão Stardew Valley (grade 16 larg x 32 alt):
- Linhas Y=0..15: Cabeça e Cabelo (rosto ocupa X=4..11, Y=4..13; olhos ficam em Y=9..10 nos X=5..6 e X=9..10; o cabelo pode ocupar X=1..14, Y=0..16 conforme o volume real da pessoa).
- Linhas Y=14..22: Tronco, Roupa e Braços (tronco central em X=4..11, braços laterais em X=2..3 e X=12..13, mãos em Y=19..21).
- Linhas Y=23..30: Pernas/Calça (X=4..7 e X=8..11) e Botas arredondadas na base (Y=28..30).
- Estilo de cores: Use contornos escuros quentes (sel-out marrom/vinho escuro, nunca preto puro #000000) ao redor da silhueta e agrupe sombras/luzes em clusters estilo Stardew Valley.

Retorne EXCLUSIVAMENTE um objeto JSON válido no seguinte formato:
{
  "name": "Nome sugerido",
  "description": "Resumo das características únicas capturadas da pessoa",
  "palette": {
    ".": null,
    "O": "#3A1C1A",
    "S": "#F2B88B",
    "s": "#D4926A",
    "H": "#4A2E1B",
    "h": "#6E472B",
    "E": "#2B1B12",
    "W": "#FAF6F0",
    "C": "#3B659C",
    "c": "#28466E",
    "P": "#2E3545",
    "B": "#54311C"
  },
  "front_16x32": [
    "................",
    "....OOOOOO......",
    "...OHHHHHHO....."
    // Exatamente 32 linhas com 16 caracteres cada, usando as chaves de "palette"
  ],
  "side_16x32": [
    // Exatamente 32 linhas com 16 caracteres cada representando o perfil olhando para a DIREITA
  ]
}
"""


def get_copyable_llm_prompt() -> str:
    return STARDEW_LLM_SYSTEM_PROMPT.strip()


def _warm_outline(rgb: Tuple[int, int, int]) -> Tuple[int, int, int, int]:
    """Cria a cor de contorno escuro quente (sel-out) característica de ConcernedApe."""
    r, g, b = rgb
    return (
        max(18, int(r * 0.36)),
        max(12, int(g * 0.26)),
        max(16, int(b * 0.30)),
        255,
    )


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


def sculpt_freeform_sprite_from_photo(
    image_path: str,
    cfg: AvatarConfig,
) -> Tuple[Image.Image, Image.Image]:
    """
    Escultor Livre Pixel-a-Pixel Direto da Foto:
    Analisa a foto real da pessoa em uma grade de alta precisão e constrói livremente
    o quadro 16x32 frontal e o quadro 16x32 de perfil lateral no padrão Stardew Valley,
    capturando o contorno real do cabelo, formato facial, barba/bigode, óculos e estampa/gola da roupa!
    """
    pil_img = Image.open(image_path)
    pil_img = ImageOps.exif_transpose(pil_img).convert("RGB")
    pil_img.thumbnail((600, 600), Image.Resampling.LANCZOS)
    img_np = np.array(pil_img)
    h, w, _ = img_np.shape

    fx, fy, fw, fh = detect_face_bbox_skin_chrominance(img_np)

    # 1. Recortar a região expandida da cabeça/cabelo/ombros da pessoa na foto
    # Mapeamos para uma grade 14x15 que formará a cabeça/cabelo livre em X=1..14, Y=1..15
    cx = fx + fw / 2.0
    head_top = max(0, int(fy - fh * 0.38))
    head_bot = min(h, int(fy + fh * 1.08))
    head_left = max(0, int(cx - fw * 0.72))
    head_right = min(w, int(cx + fw * 0.72))

    head_crop = pil_img.crop((head_left, head_top, head_right, head_bot))
    head_grid = np.array(head_crop.resize((14, 15), Image.Resampling.BILINEAR), dtype=np.float32)

    # 2. Recortar a região real do tronco/roupa abaixo do queixo (mapeada para 8x8 no peito X=4..11, Y=14..21)
    torso_top = min(h - 4, int(fy + fh * 0.98))
    torso_bot = min(h, int(fy + fh * 1.75))
    torso_left = max(0, int(cx - fw * 0.55))
    torso_right = min(w, int(cx + fw * 0.55))
    if torso_bot - torso_top > 8 and torso_right - torso_left > 8:
        torso_crop = pil_img.crop((torso_left, torso_top, torso_right, torso_bot))
        # Quantizar o tronco para 5 cores reais da roupa da pessoa (preservando gravata, jaqueta aberta, listras ou logo!)
        torso_small = torso_crop.resize((8, 8), Image.Resampling.BILINEAR)
        torso_quant = torso_small.quantize(colors=5, method=Image.Quantize.MEDIANCUT).convert("RGB")
        torso_grid = np.array(torso_quant, dtype=np.uint8)
    else:
        sh_rgb = hex_to_rgb(cfg.shirt_color)
        torso_grid = np.full((8, 8, 3), sh_rgb, dtype=np.uint8)

    # Cores base extraídas da pessoa
    skin_rgb = hex_to_rgb(cfg.skin_color)
    skin_base = _shade_rgba(skin_rgb, 1.0)
    skin_hi = _shade_rgba(skin_rgb, 1.12)
    skin_sh = _shade_rgba(skin_rgb, 0.84)
    skin_out = _warm_outline(skin_rgb)

    hair_rgb = hex_to_rgb(cfg.hair_color)
    hair_base = _shade_rgba(hair_rgb, 1.0)
    hair_hi = _shade_rgba(hair_rgb, 1.24)
    hair_sh = _shade_rgba(hair_rgb, 0.74)
    hair_out = _warm_outline(hair_rgb)

    eye_rgb = hex_to_rgb(cfg.eye_color)
    eye_c = (eye_rgb[0], eye_rgb[1], eye_rgb[2], 255)
    eye_dark = _shade_rgba(eye_rgb, 0.55)
    white = (250, 246, 240, 255)

    pants_rgb = hex_to_rgb(cfg.pants_color)
    pants_base = _shade_rgba(pants_rgb, 1.0)
    pants_sh = _shade_rgba(pants_rgb, 0.75)
    pants_out = _warm_outline(pants_rgb)

    boots_base = (86, 48, 28, 255)
    boots_hi = (118, 68, 40, 255)
    boots_out = (42, 20, 12, 255)

    # Estimar cor do fundo nos cantos superiores do recorte para segmentar a silhueta real do cabelo/cabeça
    bg_corners = np.vstack([
        head_grid[0:2, 0:2].reshape(-1, 3),
        head_grid[0:2, -2:].reshape(-1, 3),
    ])
    bg_color = np.median(bg_corners, axis=0)

    # ==================== CONSTRUIR QUADRO 16x32 FRONTAL LIVRE ====================
    front = Image.new("RGBA", (16, 32), (0, 0, 0, 0))

    # 1. Rosto Anatômico Stardew Valley (X=4..11, Y=4..13) com queixo arredondado
    for y in range(4, 14):
        for x in range(4, 12):
            if y == 13 and x in (4, 11):
                continue
            if y in (4, 5):
                c = skin_hi
            elif y >= 11 or x in (4, 11):
                c = skin_sh
            else:
                c = skin_base
            front.putpixel((x, y), c)

    # Orelhas visíveis se o cabelo não cobrir
    front.putpixel((3, 8), skin_sh)
    front.putpixel((3, 9), skin_out)
    front.putpixel((12, 8), skin_sh)
    front.putpixel((12, 9), skin_out)

    # Contorno da mandíbula/rosto estilo Stardew Valley
    for x in range(5, 11):
        front.putpixel((x, 13), skin_out)
    front.putpixel((4, 12), skin_out)
    front.putpixel((11, 12), skin_out)

    # 2. Esculpir Cabelo, Franja, Sobrancelhas e Barba diretamente da Matriz da Foto (head_grid 14x15)
    hair_mask = np.zeros((16, 16), dtype=bool)
    for gy in range(15):
        for gx in range(14):
            px_rgb = head_grid[gy, gx]
            dist_bg = float(np.linalg.norm(px_rgb - bg_color))
            dist_hair = float(np.linalg.norm(px_rgb - np.array(hair_rgb, dtype=np.float32)))
            dist_skin = float(np.linalg.norm(px_rgb - np.array(skin_rgb, dtype=np.float32)))
            lum = 0.299 * px_rgb[0] + 0.587 * px_rgb[1] + 0.114 * px_rgb[2]

            tx = gx + 1  # X=1..14
            ty = gy + 1  # Y=1..15

            # Zona de cabelo (topo Y=1..6, laterais X=1..4 e X=11..14)
            in_hair_zone = (ty <= 6) or (tx <= 4 and ty <= 14) or (tx >= 11 and ty <= 14)
            if in_hair_zone and cfg.hair_style != "careca":
                # Pertence ao cabelo da pessoa se não for fundo e for mais próximo do cabelo (ou escuro/texturizado)
                if dist_bg > 22.0 and (dist_hair < dist_skin * 1.15 or ty <= 4):
                    # Manter dentro de uma silhueta orgânica Chibi 16x32
                    if (tx in (1, 14) and ty < 3) or (tx in (1, 14) and ty > 12):
                        continue
                    hair_mask[ty, tx] = True

    # Garantir volume mínimo natural no topo caso o fundo da foto tenha cor parecida com o cabelo
    if cfg.hair_style != "careca" and np.count_nonzero(hair_mask[:6, :]) < 12:
        for ty in range(2, 6):
            for tx in range(3, 13):
                if ty == 2 and tx in (3, 12):
                    continue
                hair_mask[ty, tx] = True

    # Pintar pixels internos do cabelo com as variações reais de luz/sombra da foto da pessoa!
    hair_lums = []
    for ty in range(1, 15):
        for tx in range(1, 15):
            if hair_mask[ty, tx]:
                rgb_p = head_grid[ty - 1, tx - 1]
                hair_lums.append(0.299 * rgb_p[0] + 0.587 * rgb_p[1] + 0.114 * rgb_p[2])
    med_hair_lum = float(np.median(hair_lums)) if hair_lums else 90.0

    for ty in range(1, 15):
        for tx in range(1, 15):
            if not hair_mask[ty, tx]:
                continue
            rgb_p = head_grid[ty - 1, tx - 1]
            lum = 0.299 * rgb_p[0] + 0.587 * rgb_p[1] + 0.114 * rgb_p[2]
            # Verificar se é borda externa do cabelo -> aplicar sel-out escuro Stardew Valley
            is_border = (
                ty == 1
                or not hair_mask[ty - 1, tx]
                or (tx <= 2)
                or (tx >= 13)
                or (not hair_mask[ty, max(0, tx - 1)] and tx <= 4)
                or (not hair_mask[ty, min(15, tx + 1)] and tx >= 11)
            )
            if is_border:
                front.putpixel((tx, ty), hair_out)
            elif lum > med_hair_lum + 14 or (ty in (3, 4) and 5 <= tx <= 10):
                front.putpixel((tx, ty), hair_hi)
            elif lum < med_hair_lum - 12 or ty >= 9:
                front.putpixel((tx, ty), hair_sh)
            else:
                front.putpixel((tx, ty), hair_base)

    # 3. Olhos Stardew Valley (2x2 em X=5..6 e X=9..10, Y=8..9) + Sobrancelhas expressivas da foto
    front.putpixel((5, 7), hair_out)
    front.putpixel((6, 7), hair_sh)
    front.putpixel((9, 7), hair_sh)
    front.putpixel((10, 7), hair_out)

    # Olho esquerdo
    front.putpixel((5, 8), white)
    front.putpixel((5, 9), skin_sh)
    front.putpixel((6, 8), eye_dark)
    front.putpixel((6, 9), eye_c)
    # Olho direito
    front.putpixel((9, 8), eye_dark)
    front.putpixel((9, 9), eye_c)
    front.putpixel((10, 8), white)
    front.putpixel((10, 9), skin_sh)

    # 4. Barba / Bigode esculpidos conforme a região inferior do rosto da foto
    for gy in range(9, 13):
        for gx in range(3, 11):
            px_rgb = head_grid[gy, gx]
            dist_skin = float(np.linalg.norm(px_rgb - np.array(skin_rgb, dtype=np.float32)))
            lum = 0.299 * px_rgb[0] + 0.587 * px_rgb[1] + 0.114 * px_rgb[2]
            skin_lum = 0.299 * skin_rgb[0] + 0.587 * skin_rgb[1] + 0.114 * skin_rgb[2]
            tx, ty = gx + 1, gy + 1
            if 4 <= tx <= 11 and 10 <= ty <= 13:
                if (skin_lum - lum) > 34 or cfg.beard_style != "sem_barba":
                    if cfg.beard_style == "sem_barba" and (skin_lum - lum) <= 44:
                        continue
                    if cfg.beard_style == "bigode" and ty > 11:
                        continue
                    if cfg.beard_style == "cavanhaque" and tx not in (6, 7, 8, 9):
                        continue
                    # Deixar 2 pixels de boca/lábio em (7, 11) e (8, 11)
                    if ty == 11 and tx in (7, 8):
                        front.putpixel((tx, ty), skin_sh)
                    else:
                        front.putpixel((tx, ty), hair_out if ty == 13 else hair_base)

    # 5. Óculos (se detectados na foto ou ativados)
    if cfg.glasses_style != "nenhum":
        g_frame = (40, 36, 45, 255)
        g_lens = (32, 38, 48, 235) if cfg.glasses_style == "escuro" else (185, 225, 250, 145)
        for ex in (4, 5, 6, 7, 8, 9, 10, 11):
            front.putpixel((ex, 7), g_frame)
        for ex in (4, 7, 8, 11):
            front.putpixel((ex, 8), g_frame)
            front.putpixel((ex, 9), g_frame)
        for ex in (5, 6, 9, 10):
            front.putpixel((ex, 10), g_frame)
            if cfg.glasses_style == "escuro":
                front.putpixel((ex, 8), g_lens)
                front.putpixel((ex, 9), g_lens)
        if cfg.glasses_style == "escuro":
            front.putpixel((5, 8), (220, 240, 255, 255))
            front.putpixel((9, 8), (220, 240, 255, 255))

    # 6. Tronco e Roupa Livre (X=4..11, Y=14..21) mapeada diretamente da roupa real da foto!
    for ty_idx in range(8):
        for tx_idx in range(8):
            x = 4 + tx_idx
            y = 14 + ty_idx
            rgb_cloth = tuple(int(v) for v in torso_grid[ty_idx, tx_idx])
            if tx_idx in (0, 7) or ty_idx == 7:
                c = _warm_outline(rgb_cloth)
            elif ty_idx == 0 and tx_idx in (3, 4):
                # Gola / pescoço com pele
                c = skin_sh
            else:
                c = (rgb_cloth[0], rgb_cloth[1], rgb_cloth[2], 255)
            front.putpixel((x, y), c)

    # Mangas e Mãos Anatômicas Stardew Valley (X=2..3 e X=12..13, Y=15..21)
    sleeve_l_rgb = tuple(int(v) for v in torso_grid[1, 1])
    sleeve_r_rgb = tuple(int(v) for v in torso_grid[1, 6])
    sl_l_out = _warm_outline(sleeve_l_rgb)
    sl_r_out = _warm_outline(sleeve_r_rgb)
    sl_l_c = (sleeve_l_rgb[0], sleeve_l_rgb[1], sleeve_l_rgb[2], 255)
    sl_r_c = (sleeve_r_rgb[0], sleeve_r_rgb[1], sleeve_r_rgb[2], 255)

    for y in range(15, 19):
        front.putpixel((2, y), sl_l_out)
        front.putpixel((3, y), sl_l_c)
        front.putpixel((12, y), sl_r_c)
        front.putpixel((13, y), sl_r_out)
    # Mãos arredondadas Chibi (Y=19..21)
    for y in (19, 20):
        front.putpixel((2, y), skin_sh)
        front.putpixel((3, y), skin_base)
        front.putpixel((12, y), skin_base)
        front.putpixel((13, y), skin_sh)
    front.putpixel((2, 21), skin_out)
    front.putpixel((3, 21), skin_out)
    front.putpixel((12, 21), skin_out)
    front.putpixel((13, 21), skin_out)

    # 7. Pernas e Botas Stardew Valley (Y=22..30)
    for y in range(22, 28):
        for x in range(4, 12):
            if x in (4, 11) or (x in (7, 8) and y >= 24):
                front.putpixel((x, y), pants_out)
            elif x in (5, 9):
                front.putpixel((x, y), pants_base)
            else:
                front.putpixel((x, y), pants_sh)

    # Botas arredondadas (Y=28..30)
    for x in (4, 5, 6, 7, 8, 9, 10, 11):
        front.putpixel((x, 28), boots_out if x in (4, 7, 8, 11) else boots_hi)
        front.putpixel((x, 29), boots_out if x in (4, 7, 8, 11) else boots_base)
        front.putpixel((x, 30), boots_out)

    # ==================== CONSTRUIR QUADRO 16x32 PERFIL DIREITO LIVRE ====================
    side = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    # Copiar base da cabeça e deslocar feições 1px para a direita (perfil olhando para a direita)
    for y in range(1, 15):
        for x in range(2, 14):
            px = front.getpixel((x, y))
            if px[3] > 0:
                side.putpixel((x, y), px)

    # Olho em perfil direito (X=9..10, Y=8..9) e nariz levemente projetado em X=12, Y=9
    for y in range(6, 13):
        for x in range(5, 12):
            if not hair_mask[y, max(0, x - 1)]:
                side.putpixel((x, y), skin_base if x >= 7 else skin_sh)
    side.putpixel((9, 8), white)
    side.putpixel((9, 9), skin_sh)
    side.putpixel((10, 8), eye_dark)
    side.putpixel((10, 9), eye_c)
    side.putpixel((12, 9), skin_base)
    side.putpixel((12, 10), skin_out)

    # Volume de cabelo na nuca (esquerda X=2..6, Y=3..12)
    if cfg.hair_style != "careca":
        for y in range(3, 12):
            for x in range(3, 7):
                if x == 3:
                    side.putpixel((x, y), hair_out)
                elif x == 4:
                    side.putpixel((x, y), hair_sh)
                else:
                    side.putpixel((x, y), hair_base)

    # Tronco em perfil (X=5..10, Y=14..21)
    for ty_idx in range(8):
        for tx_idx in range(1, 7):
            x = 4 + tx_idx
            y = 14 + ty_idx
            rgb_cloth = tuple(int(v) for v in torso_grid[ty_idx, tx_idx])
            if tx_idx in (1, 6) or ty_idx == 7:
                c = _warm_outline(rgb_cloth)
            else:
                c = (rgb_cloth[0], rgb_cloth[1], rgb_cloth[2], 255)
            side.putpixel((x, y), c)

    # Pernas e botas em perfil (X=5..10, Y=22..30)
    for y in range(22, 28):
        for x in range(5, 11):
            side.putpixel((x, y), pants_out if x in (5, 10) else pants_base)
    for x in range(5, 12):
        side.putpixel((x, 28), boots_out if x in (5, 11) else boots_hi)
        side.putpixel((x, 29), boots_out if x in (5, 11) else boots_base)
        side.putpixel((x, 30), boots_out)

    # Braço lateral centralizado no perfil (X=7..8, Y=15..21)
    for y in range(15, 19):
        side.putpixel((7, y), sl_r_out)
        side.putpixel((8, y), sl_r_c)
    side.putpixel((7, 19), skin_sh)
    side.putpixel((8, 19), skin_base)
    side.putpixel((7, 20), skin_out)
    side.putpixel((8, 20), skin_out)

    return front, side


def parse_llm_matrix_json(data: Dict[str, Any]) -> Optional[Tuple[Image.Image, Image.Image]]:
    """Converte o JSON de matriz 16x32 retornado pela LLM em duas imagens RGBA (frente e perfil)."""
    palette = data.get("palette", {})
    front_rows = data.get("front_16x32", [])
    side_rows = data.get("side_16x32", [])
    if len(front_rows) < 24:
        return None

    def _grid_to_img(rows: List[str]) -> Image.Image:
        img = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
        for y, line in enumerate(rows[:32]):
            for x, ch in enumerate(line[:16]):
                hex_c = palette.get(ch)
                if hex_c and isinstance(hex_c, str) and hex_c.startswith("#"):
                    r, g, b = hex_to_rgb(hex_c)
                    img.putpixel((x, y), (r, g, b, 255))
        return img

    front_img = _grid_to_img(front_rows)
    side_img = _grid_to_img(side_rows) if len(side_rows) >= 24 else front_img.copy()
    return front_img, side_img


def call_llm_vision_for_sprite(
    image_path: str,
    settings: Optional[Dict[str, Any]] = None,
) -> Optional[Tuple[Image.Image, Image.Image, str]]:
    """
    Chama a API de Visão configurada (Gemini / OpenAI / Ollama Local) para desenhar
    livremente os sprites 16x32 a partir da foto da pessoa.
    Retorna (front_16x32, side_16x32, description) ou None se falhar/sem chave.
    """
    if settings is None:
        settings = load_llm_settings()

    provider = settings.get("provider", "auto")
    api_key = settings.get("api_key", "").strip()
    if provider == "sculptor_offline":
        return None

    # Preparar imagem em base64 reduzida
    pil_img = Image.open(image_path)
    pil_img = ImageOps.exif_transpose(pil_img).convert("RGB")
    pil_img.thumbnail((512, 512), Image.Resampling.LANCZOS)
    buf = BytesIO()
    pil_img.save(buf, format="JPEG", quality=88)
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    extra_notes = settings.get("custom_prompt_notes", "").strip()
    prompt = STARDEW_LLM_SYSTEM_PROMPT
    if extra_notes:
        prompt += f"\nObservações extras do usuário sobre a pessoa: {extra_notes}\n"

    # 1. Tentar Google Gemini API se houver chave
    if api_key and (provider in ("auto", "gemini")) and not api_key.startswith("sk-"):
        model = settings.get("model") or "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
                    ]
                }
            ],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
        }
        r = httpx.post(url, json=payload, timeout=45.0)
        r.raise_for_status()
        resp_json = r.json()
        text_out = resp_json["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text_out)
        imgs = parse_llm_matrix_json(parsed)
        if imgs:
            return imgs[0], imgs[1], parsed.get("description", "Gerado via Gemini Vision")

    # 2. Tentar OpenAI Vision API (gpt-4o / gpt-4o-mini)
    if api_key and (provider in ("auto", "openai")):
        model = settings.get("model") if "gpt" in settings.get("model", "") else "gpt-4o-mini"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    ],
                }
            ],
        }
        r = httpx.post(url, headers=headers, json=payload, timeout=45.0)
        r.raise_for_status()
        text_out = r.json()["choices"][0]["message"]["content"]
        parsed = json.loads(text_out)
        imgs = parse_llm_matrix_json(parsed)
        if imgs:
            return imgs[0], imgs[1], parsed.get("description", "Gerado via OpenAI Vision")

    # 3. Tentar Ollama Local (se estiver rodando em localhost:11434)
    if provider in ("auto", "ollama"):
        ollama_url = settings.get("ollama_url", "http://localhost:11434").rstrip("/")
        model = settings.get("model") or "llava"
        r = httpx.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "images": [img_b64],
                "format": "json",
                "stream": False,
            },
            timeout=30.0,
        )
        if r.status_code == 200:
            parsed = json.loads(r.json().get("response", "{}"))
            imgs = parse_llm_matrix_json(parsed)
            if imgs:
                return imgs[0], imgs[1], parsed.get("description", "Gerado via Ollama Local")

    return None


def animate_freeform_frames_to_spritesheet(
    front_16x32: Image.Image,
    side_16x32: Image.Image,
    cfg: AvatarConfig,
) -> Image.Image:
    """
    A partir dos quadros 16x32 desenhados livremente (Frente e Perfil Direito),
    gera automaticamente toda a Sprite Sheet 96x288 (8 animações x 4 quadros),
    animando caminhada, balanço de braços, piscar de olhos e props do Stardew Valley!
    """
    from sprite_generator import CELL_W, CELL_H, COLS, ROWS, ANIMATION_ROWS, put_px, fill_rect

    sheet = Image.new("RGBA", (CELL_W * COLS, CELL_H * ROWS), (0, 0, 0, 0))
    skin_rgb = hex_to_rgb(cfg.skin_color)
    skin_light = _shade_rgba(skin_rgb, 1.0)
    skin_dark = _warm_outline(skin_rgb)

    for action, row_idx in ANIMATION_ROWS.items():
        for frame_idx in range(COLS):
            cell = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
            ox = 4
            oy = 3

            # Sombra no chão estilo Stardew
            for sx in range(ox + 3, ox + 13):
                put_px(cell, sx, 34, (20, 15, 25, 95))
            for sx in range(ox + 4, ox + 12):
                put_px(cell, sx, 33, (20, 15, 25, 65))

            if action in ("walk_right", "walk_left", "water_crops", "fishing"):
                base = side_16x32.copy()
                # Animação de passo nas pernas (Y=23..30) e bobbing da cabeça/tronco (Y=0..22)
                if action in ("walk_right", "walk_left") and frame_idx in (1, 3):
                    anim_frame = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
                    # Cabeça e tronco descem 1px no passo
                    upper = base.crop((0, 0, 16, 22))
                    anim_frame.paste(upper, (0, 1), upper)
                    # Pernas abrem em passo (perna da frente e perna de trás)
                    leg_slice = base.crop((5, 22, 10, 31))
                    if frame_idx == 1:
                        anim_frame.paste(leg_slice, (3, 21), leg_slice)
                        anim_frame.paste(leg_slice, (8, 22), leg_slice)
                    else:
                        anim_frame.paste(leg_slice, (4, 22), leg_slice)
                        anim_frame.paste(leg_slice, (9, 21), leg_slice)
                    base = anim_frame

                if action == "walk_left":
                    base = ImageOps.mirror(base)

                cell.paste(base, (ox, oy), base)

            else:
                # Animações frontais (idle, coffee_break, happy_dance, sleep_sit)
                base = front_16x32.copy()
                jump_y = -2 if (action == "happy_dance" and frame_idx in (1, 3)) else 0
                bob_y = 1 if (action == "idle" and frame_idx in (1, 2)) else 0

                # Piscar os olhos em idle (frame 3) ou dormindo (sleep_sit)
                if (action == "idle" and frame_idx == 3) or action == "sleep_sit":
                    for ex in (5, 6, 9, 10):
                        put_px(base, ex, 8, skin_light)
                        put_px(base, ex, 9, skin_dark)

                # Levantar os braços em happy_dance ou coffee_break
                if (action == "happy_dance" and frame_idx in (1, 3)) or (action == "coffee_break" and frame_idx in (1, 2)):
                    l_arm = base.crop((2, 15, 4, 22))
                    r_arm = base.crop((12, 15, 14, 22))
                    # Limpar braços baixos e colar levantados
                    for ay in range(15, 22):
                        for ax in (2, 3, 12, 13):
                            base.putpixel((ax, ay), (0, 0, 0, 0))
                    l_up = ImageOps.flip(l_arm)
                    r_up = ImageOps.flip(r_arm)
                    base.paste(l_up, (2, 10), l_up)
                    base.paste(r_up, (12, 10), r_up)

                cell.paste(base, (ox, oy + bob_y + jump_y), base)

            # Desenhar Props do Stardew Valley (Regador, Café, Vara de Pesca, Coração, Zzz)
            torso_y = oy + 15
            if action == "water_crops":
                can_c = (130, 155, 185, 255)
                can_sh = (75, 95, 120, 255)
                fill_rect(cell, ox + 14, torso_y + 2, 4, 4, can_c)
                fill_rect(cell, ox + 14, torso_y + 5, 4, 1, can_sh)
                put_px(cell, ox + 18, torso_y + 3, can_c)
                put_px(cell, ox + 19, torso_y + 2, (215, 65, 65, 255))
                if frame_idx in (1, 2, 3):
                    drop_c = (95, 190, 255, 255)
                    put_px(cell, ox + 18, torso_y + 5 + (frame_idx % 2), drop_c)
                    put_px(cell, ox + 19, torso_y + 6 + (frame_idx % 3), drop_c)
                sprout_g = (75, 185, 65, 255)
                put_px(cell, ox + 18, 33, sprout_g)
                put_px(cell, ox + 18, 32, sprout_g)
                if frame_idx >= 2:
                    put_px(cell, ox + 17, 31, sprout_g)
                    put_px(cell, ox + 19, 31, sprout_g)
                if frame_idx == 3:
                    put_px(cell, ox + 18, 30, (255, 215, 55, 255))

            elif action == "coffee_break":
                cup_y = oy + (9 if frame_idx in (1, 2) else 15)
                cup_x = ox + (6 if frame_idx in (1, 2) else 11)
                fill_rect(cell, cup_x, cup_y, 3, 3, (245, 238, 225, 255))
                put_px(cell, cup_x + 3, cup_y + 1, (195, 185, 175, 255))
                put_px(cell, cup_x + 1, cup_y, (95, 50, 25, 255))
                steam_y = cup_y - 2 - (frame_idx % 2)
                put_px(cell, cup_x + 1, steam_y, (255, 255, 255, 200))
                put_px(cell, cup_x + 2, steam_y - 1, (255, 255, 255, 150))

            elif action == "fishing":
                rod_c = (185, 130, 60, 255)
                for i in range(6):
                    put_px(cell, ox + 13 + i, torso_y + 2 - i, rod_c)
                line_x = ox + 18
                for ly in range(torso_y - 3, 32):
                    put_px(cell, line_x, ly, (220, 235, 245, 185))
                bobber_y = 32 + (1 if frame_idx in (1, 3) else 0)
                put_px(cell, line_x, bobber_y, (230, 55, 55, 255))
                put_px(cell, line_x, bobber_y + 1, (252, 250, 245, 255))
                if frame_idx == 3:
                    fill_rect(cell, ox + 7, 0, 2, 3, (255, 220, 40, 255))
                    fill_rect(cell, ox + 7, 4, 2, 1, (255, 220, 40, 255))

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
                    put_px(cell, ox + hx, hy + hdy, heart_c)
                put_px(cell, ox + 6, hy + 1, heart_hi)

            elif action == "sleep_sit":
                z_c = (155, 205, 255, 240)
                zy = 3 - (frame_idx % 3)
                zx = ox + 13 + (frame_idx % 2)
                for dx, dy in [(0, 0), (1, 0), (2, 0), (1, 1), (0, 2), (1, 2), (2, 2)]:
                    put_px(cell, zx + dx, zy + dy, z_c)

            sheet.paste(cell, (frame_idx * CELL_W, row_idx * CELL_H))

    return sheet
