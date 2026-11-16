"""
Gerador de Animação MP4 de Comemoração — Vitória Eliza ("Feliz Aniversário!")
Renderiza um vídeo MP4 (H.264 + Áudio Chiptune 16-bit) em 1280x720 (30 FPS)
apresentando todas as ações de comemoração carregadas no spritesheet da Vitória Eliza
(avatars/bf19af5f) com balão de fala em Pixel Art e Caixa de Diálogo estilo Stardew Valley.
"""

import math
import os
import random
import subprocess
import wave
from typing import List, Tuple
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


AVATAR_DIR = os.path.join("avatars", "bf19af5f")
SPRITESHEET_PATH = os.path.join(AVATAR_DIR, "spritesheet.png")
PORTRAIT_PATH = os.path.join(AVATAR_DIR, "dialog_portrait.png")

OUTPUT_MP4 = "vitoria_eliza_feliz_aniversario.mp4"
OUTPUT_AVATAR_MP4 = os.path.join(AVATAR_DIR, "vitoria_eliza_feliz_aniversario.mp4")

WIDTH = 1280
HEIGHT = 720
FPS = 30
DURATION_SEC = 16
TOTAL_FRAMES = FPS * DURATION_SEC  # 480 quadros


def load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = (
        ["segoeuib.ttf", "verdanab.ttf", "arialbd.ttf", "georgiab.ttf"]
        if bold
        else ["segoeui.ttf", "verdana.ttf", "arial.ttf", "georgia.ttf"]
    )
    for name in candidates:
        p = os.path.join(r"C:\Windows\Fonts", name)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def extract_all_rows(sheet: Image.Image, scale: int = 1) -> List[List[Image.Image]]:
    """Extrai as 8 linhas x 6 colunas (48x72 cada célula) da Vitória Eliza."""
    cols = 6
    rows = 8
    cw = sheet.width // cols   # 48
    ch = sheet.height // rows  # 72
    all_rows: List[List[Image.Image]] = []
    for r in range(rows):
        row_frames: List[Image.Image] = []
        for c in range(cols):
            cell = sheet.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)).convert("RGBA")
            if scale != 1:
                cell = cell.resize((cw * scale, ch * scale), Image.Resampling.NEAREST)
            row_frames.append(cell)
        all_rows.append(row_frames)
    return all_rows


def draw_stardew_frame(
    draw: ImageDraw.ImageDraw,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    parchment_color: Tuple[int, int, int] = (247, 223, 179),
    shade_color: Tuple[int, int, int] = (232, 198, 142),
):
    """Desenha uma moldura de madeira esculpida e pergaminho autêntica estilo Stardew Valley."""
    c_outer = (90, 43, 17)     # #5A2B11
    c_mid = (184, 111, 40)     # #B86F28
    c_inner = (229, 160, 69)   # #E5A045
    c_rivet = (122, 62, 18)
    c_hi = (255, 248, 230)

    # Borda externa chanfrada
    draw.rectangle([x1 + 4, y1, x2 - 4, y2], fill=c_outer)
    draw.rectangle([x1 + 2, y1 + 2, x2 - 2, y2 - 2], fill=c_outer)
    draw.rectangle([x1, y1 + 4, x2, y2 - 4], fill=c_outer)

    # Moldura intermediária de madeira
    draw.rectangle([x1 + 4, y1 + 4, x2 - 4, y2 - 4], fill=c_mid)
    draw.rectangle([x1 + 7, y1 + 7, x2 - 7, y2 - 7], fill=c_inner)
    draw.rectangle([x1 + 10, y1 + 10, x2 - 10, y2 - 10], fill=c_outer)

    # Pergaminho interno
    draw.rectangle([x1 + 12, y1 + 12, x2 - 12, y2 - 12], fill=parchment_color)
    draw.rectangle([x1 + 12, y1 + 12, x2 - 12, y1 + 16], fill=c_hi)
    draw.rectangle([x1 + 12, y2 - 20, x2 - 12, y2 - 12], fill=shade_color)

    # Cravos decorativos nos 4 cantos
    for rx, ry in (
        (x1 + 16, y1 + 16),
        (x2 - 20, y1 + 16),
        (x1 + 16, y2 - 20),
        (x2 - 20, y2 - 20),
    ):
        draw.rectangle([rx, ry, rx + 4, ry + 4], fill=c_rivet)
        draw.rectangle([rx, ry, rx + 1, ry + 1], fill=c_inner)


def build_pixel_speech_bubble(
    text_top: str,
    text_sub: str,
    font_main: ImageFont.FreeTypeFont,
    font_sub: ImageFont.FreeTypeFont,
    width: int = 330,
    height: int = 76,
    tail_h: int = 14,
) -> Image.Image:
    """Cria o balão de fala em Pixel Art estilo Stardew Valley com ponteiro inferior."""
    img = Image.new("RGBA", (width, height + tail_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    c_outer = (61, 27, 8, 255)
    c_wood = (186, 115, 42, 255)
    c_highlight = (255, 250, 235, 255)
    c_parchment = (252, 240, 213, 255)
    c_shade = (237, 212, 162, 255)
    c_rivet = (122, 62, 18, 255)

    w, h = width, height
    draw.rectangle([6, 0, w - 7, h - 1], fill=c_outer)
    draw.rectangle([3, 3, w - 4, h - 4], fill=c_outer)
    draw.rectangle([0, 6, w - 1, h - 7], fill=c_outer)

    draw.rectangle([6, 3, w - 7, h - 4], fill=c_wood)
    draw.rectangle([3, 6, w - 4, h - 7], fill=c_wood)

    draw.rectangle([6, 6, w - 7, h - 7], fill=c_parchment)
    draw.rectangle([8, 6, w - 9, 9], fill=c_highlight)
    draw.rectangle([6, h - 13, w - 7, h - 7], fill=c_shade)

    for rx, ry in ((10, 10), (w - 14, 10), (10, h - 14), (w - 14, h - 14)):
        draw.rectangle([rx, ry, rx + 3, ry + 3], fill=c_rivet)

    cx = w // 2
    draw.rectangle([cx - 10, h - 3, cx + 10, h + 2], fill=c_outer)
    draw.rectangle([cx - 7, h + 3, cx + 7, h + 7], fill=c_outer)
    draw.rectangle([cx - 4, h + 8, cx + 4, h + 13], fill=c_outer)
    draw.rectangle([cx - 7, h - 6, cx + 7, h + 1], fill=c_shade)
    draw.rectangle([cx - 4, h + 2, cx + 4, h + 7], fill=c_parchment)

    # Texto principal ("Feliz Aniversário!")
    bbox1 = draw.textbbox((0, 0), text_top, font=font_main)
    tw1 = bbox1[2] - bbox1[0]
    tx1 = (w - tw1) // 2
    ty1 = 10 if text_sub else (h - (bbox1[3] - bbox1[1])) // 2 - 4
    draw.text((tx1 + 1, ty1 + 1), text_top, font=font_main, fill=(229, 196, 139, 255))
    draw.text((tx1, ty1), text_top, font=font_main, fill=(168, 34, 48, 255))

    if text_sub:
        bbox2 = draw.textbbox((0, 0), text_sub, font=font_sub)
        tw2 = bbox2[2] - bbox2[0]
        tx2 = (w - tw2) // 2
        ty2 = 40
        draw.text((tx2 + 1, ty2 + 1), text_sub, font=font_sub, fill=(229, 196, 139, 255))
        draw.text((tx2, ty2), text_sub, font=font_sub, fill=(63, 29, 11, 255))

    return img


def draw_pixel_heart(draw: ImageDraw.ImageDraw, ox: int, oy: int, scale: int = 3, color=(225, 45, 70)):
    hi = (255, 175, 190)
    pattern = [
        (1, 0), (2, 0), (4, 0), (5, 0),
        (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1),
        (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2),
        (1, 3), (2, 3), (3, 3), (4, 3), (5, 3),
        (2, 4), (3, 4), (4, 4),
        (3, 5),
    ]
    for hx, hy in pattern:
        draw.rectangle(
            [ox + hx * scale, oy + hy * scale, ox + (hx + 1) * scale - 1, oy + (hy + 1) * scale - 1],
            fill=color,
        )
    draw.rectangle([ox + 1 * scale, oy + 1 * scale, ox + 2 * scale - 1, oy + 2 * scale - 1], fill=hi)


def draw_pixel_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, s: int = 3, color=(255, 220, 65)):
    for dx, dy in [(0, -2), (0, -1), (0, 0), (0, 1), (0, 2), (-2, 0), (-1, 0), (1, 0), (2, 0)]:
        draw.rectangle([cx + dx * s, cy + dy * s, cx + (dx + 1) * s - 1, cy + (dy + 1) * s - 1], fill=color)
    draw.rectangle([cx, cy, cx + s - 1, cy + s - 1], fill=(255, 255, 245))


def create_static_background() -> Tuple[Image.Image, List[Tuple[int, int, int]]]:
    """Cria o cenário base estilo Festival de Aniversário no Vale do Orvalho."""
    bg = Image.new("RGBA", (WIDTH, HEIGHT), (24, 28, 64, 255))
    draw = ImageDraw.Draw(bg)

    # Céu crepuscular mágico em faixas pixeladas (de azul noite estrelado a dourado quente no horizonte)
    sky_bands = [
        (0, 70, (22, 26, 62)),
        (70, 140, (32, 36, 82)),
        (140, 210, (48, 46, 102)),
        (210, 280, (74, 58, 118)),
        (280, 340, (112, 72, 122)),
        (340, 395, (158, 92, 114)),
        (395, 445, (204, 122, 102)),
        (445, 490, (238, 162, 106)),
    ]
    for y_start, y_end, col in sky_bands:
        draw.rectangle([0, y_start, WIDTH, y_end], fill=col)

    # Colinas distantes e pinheiros em silhueta pixel art
    for x in range(0, WIDTH, 8):
        hill_y = int(420 + 22 * math.sin(x * 0.006) + 12 * math.cos(x * 0.015))
        draw.rectangle([x, hill_y, x + 8, 490], fill=(46, 68, 74))

    # Gramado festivo do Vale do Orvalho
    draw.rectangle([0, 465, WIDTH, HEIGHT], fill=(58, 126, 66))
    draw.rectangle([0, 465, WIDTH, 475], fill=(82, 158, 78))
    draw.rectangle([0, 475, WIDTH, 483], fill=(68, 140, 70))

    # Cerca de madeira rústica ao fundo do palco
    fence_y = 432
    for fx in range(28, 770, 44):
        draw.rectangle([fx, fence_y, fx + 10, 470], fill=(112, 62, 28))
        draw.rectangle([fx + 2, fence_y + 2, fx + 8, 468], fill=(148, 86, 42))
    draw.rectangle([24, fence_y + 10, 772, fence_y + 17], fill=(134, 76, 36))
    draw.rectangle([24, fence_y + 24, 772, fence_y + 31], fill=(120, 68, 30))

    # Palco de madeira aconchegante para a Vitória Eliza (lado esquerdo/central)
    stage_x1, stage_x2 = 48, 752
    stage_y1, stage_y2 = 466, 514
    draw.rectangle([stage_x1, stage_y1, stage_x2, stage_y2], fill=(108, 56, 24))
    draw.rectangle([stage_x1 + 4, stage_y1 + 4, stage_x2 - 4, stage_y2 - 6], fill=(156, 88, 40))
    # Tábuas do palco
    for px in range(stage_x1 + 40, stage_x2 - 20, 48):
        draw.rectangle([px, stage_y1 + 4, px + 2, stage_y2 - 6], fill=(118, 64, 26))
    # Tapete vermelho/dourado de aniversário no centro do palco
    draw.rectangle([160, 470, 640, 508], fill=(178, 38, 54))
    draw.rectangle([166, 474, 634, 504], fill=(208, 54, 70))
    draw.rectangle([160, 470, 640, 474], fill=(245, 200, 72))
    draw.rectangle([160, 504, 640, 508], fill=(245, 200, 72))

    # Bandeirinhas de festa penduradas abaixo do topo
    bunting_colors = [
        (235, 65, 85),
        (255, 205, 65),
        (75, 195, 245),
        (135, 225, 95),
        (215, 115, 245),
        (255, 145, 65),
    ]
    for i, bx in enumerate(range(40, WIDTH - 40, 36)):
        by = int(96 + 14 * math.sin((bx / WIDTH) * math.pi * 3))
        c = bunting_colors[i % len(bunting_colors)]
        draw.polygon([(bx, by), (bx + 28, by), (bx + 14, by + 24)], fill=c)
        draw.line([(bx, by), (bx + 36, int(96 + 14 * math.sin(((bx + 36) / WIDTH) * math.pi * 3)))], fill=(245, 225, 185), width=2)

    # Florzinhas pixel art no gramado
    rng = random.Random(42)
    for _ in range(28):
        flx = rng.randint(20, WIDTH - 20)
        fly = rng.randint(480, 518)
        if stage_x1 - 10 <= flx <= stage_x2 + 10:
            continue
        draw.rectangle([flx, fly, flx + 4, fly + 4], fill=(255, 225, 75))
        draw.rectangle([flx - 3, fly, flx - 1, fly + 3], fill=(255, 120, 160))
        draw.rectangle([flx + 5, fly, flx + 7, fly + 3], fill=(255, 120, 160))

    # Estrelas fixas no céu para cintilar
    stars = [(rng.randint(20, WIDTH - 20), rng.randint(85, 330), rng.randint(0, 60)) for _ in range(55)]
    return bg, stars


def generate_birthday_wav(wav_path: str, duration_sec: int = DURATION_SEC):
    """
    Gera uma trilha sonora Chiptune 16-bit aconchegante estilo Stardew Valley
    tocando a melodia de 'Parabéns pra Você / Happy Birthday' com harmonia suave.
    """
    sample_rate = 44100
    total_samples = sample_rate * duration_sec
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)

    # Frequências das notas (em Dó Maior / Sol Maior)
    NOTE = {
        "G4": 392.00, "A4": 440.00, "B4": 493.88,
        "C5": 523.25, "D5": 587.33, "E5": 659.25, "F5": 698.46, "G5": 783.99,
        "C4": 261.63, "E4": 329.63, "F4": 349.23, "D4": 293.66,
    }

    # Melodia de Parabéns pra Você (nota, duração em segundos, baixo acompanhante)
    score = [
        ("G4", 0.35, "C4"), ("G4", 0.25, "C4"), ("A4", 0.60, "C4"), ("G4", 0.60, "C4"), ("C5", 0.60, "E4"), ("B4", 1.10, "D4"),
        ("G4", 0.35, "D4"), ("G4", 0.25, "D4"), ("A4", 0.60, "D4"), ("G4", 0.60, "D4"), ("D5", 0.60, "F4"), ("C5", 1.10, "C4"),
        ("G4", 0.35, "C4"), ("G4", 0.25, "C4"), ("G5", 0.60, "E4"), ("E5", 0.60, "C4"), ("C5", 0.60, "F4"), ("B4", 0.60, "F4"), ("A4", 0.90, "F4"),
        ("F5", 0.35, "F4"), ("F5", 0.25, "F4"), ("E5", 0.60, "C4"), ("C5", 0.60, "E4"), ("D5", 0.60, "D4"), ("C5", 1.25, "C4"),
        # Pequeno arpejo final festivo
        ("E5", 0.30, "C4"), ("G5", 0.30, "E4"), ("E5", 0.30, "G4"), ("C5", 0.45, "C4"), ("G5", 1.20, "C4"),
    ]

    audio = np.zeros(total_samples, dtype=np.float32)
    cursor = 0.25
    while cursor < duration_sec - 0.3:
        for mel_n, dur, bass_n in score:
            if cursor >= duration_sec - 0.2:
                break
            start_idx = int(cursor * sample_rate)
            end_idx = min(total_samples, int((cursor + dur) * sample_rate))
            length = end_idx - start_idx
            if length <= 0:
                break
            lt = np.linspace(0, dur, length, endpoint=False)
            f_mel = NOTE[mel_n]
            f_bass = NOTE[bass_n]

            # Envelope estilo caixinha de música / console 16-bit
            env = np.exp(-lt * 2.8) * np.minimum(1.0, lt / 0.015)
            # Onda híbrida (senoide + harmônicos suaves de triângulo/quadrada filtrada)
            mel_wave = (
                0.65 * np.sin(2 * np.pi * f_mel * lt)
                + 0.22 * np.sin(2 * np.pi * (f_mel * 2) * lt)
                + 0.08 * np.sin(2 * np.pi * (f_mel * 3) * lt)
            ) * env

            bass_env = np.exp(-lt * 1.8) * np.minimum(1.0, lt / 0.02)
            bass_wave = 0.30 * np.sin(2 * np.pi * f_bass * lt) * bass_env

            audio[start_idx:end_idx] += (mel_wave + bass_wave) * 0.35
            cursor += dur + 0.03

    # Fade in / fade out suaves
    fade_samples = int(0.4 * sample_rate)
    audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
    audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)
    audio = np.clip(audio, -0.95, 0.95)
    pcm16 = (audio * 32767).astype(np.int16)

    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())


def main():
    print("Carregando assets da Vitória Eliza (avatars/bf19af5f)...")
    sheet = Image.open(SPRITESHEET_PATH).convert("RGBA")
    portrait_raw = Image.open(PORTRAIT_PATH).convert("RGBA")
    portrait_156 = portrait_raw.resize((156, 156), Image.Resampling.NEAREST)

    # Extrair todas as 8 linhas em duas escalas:
    # - Escala 5x (240x360) para a Vitória Eliza protagonista no palco principal
    # - Escala 2x (96x144) para os cards das 5 ações de comemoração à direita
    rows_5x = extract_all_rows(sheet, scale=5)
    rows_2x = extract_all_rows(sheet, scale=2)

    font_banner = load_font(28, bold=True)
    font_subbanner = load_font(15, bold=False)
    font_bubble_main = load_font(22, bold=True)
    font_bubble_sub = load_font(15, bold=True)
    font_dlg_title = load_font(20, bold=True)
    font_dlg_body = load_font(21, bold=True)
    font_dlg_tag = load_font(14, bold=True)
    font_card_title = load_font(15, bold=True)
    font_card_sub = load_font(12, bold=False)

    bg_base, stars = create_static_background()

    # Configurar partículas de confete e corações flutuantes
    rng = random.Random(2026)
    confetti_palette = [
        (255, 75, 95),
        (255, 215, 60),
        (75, 200, 255),
        (130, 235, 105),
        (230, 120, 255),
        (255, 150, 65),
        (255, 245, 200),
    ]
    confetti = [
        {
            "x": rng.uniform(30, WIDTH - 30),
            "y": rng.uniform(-HEIGHT, HEIGHT),
            "vy": rng.uniform(1.8, 3.8),
            "vx": rng.uniform(-0.8, 0.8),
            "phase": rng.uniform(0, math.pi * 2),
            "color": rng.choice(confetti_palette),
            "size": rng.choice([5, 6, 8]),
        }
        for _ in range(85)
    ]

    # As 5 ações de comemoração já carregadas no spritesheet da Vitória Eliza (linhas 3 a 7)
    celebration_actions = [
        {
            "row": 3,
            "title": "1. Presente Especial",
            "subtitle": "Carinho & Surpresa",
            "bubble_sub": "Um presente especial!",
            "dialogue": "Feliz Aniversário, Vitória Eliza! Que este dia comece cheio de surpresas lindas, presentes especiais e muito carinho!",
        },
        {
            "row": 4,
            "title": "2. Bolo & Velinhas",
            "subtitle": "Hora do Pedido",
            "bubble_sub": "Hora de soprar as velinhas!",
            "dialogue": "Feliz Aniversário! Faça um pedido bem bonito antes de soprar as velinhas do bolo! Que todos os seus sonhos se realizem!",
        },
        {
            "row": 5,
            "title": "3. Festa & Confetes",
            "subtitle": "Pulos de Alegria",
            "bubble_sub": "Viva! Dia de comemorar!",
            "dialogue": "Feliz Aniversário! Hoje o Vale inteiro está em festa celebrando a sua alegria, o seu brilho e a sua conquista!",
        },
        {
            "row": 6,
            "title": "4. Chuva de Amor",
            "subtitle": "Coração Pulsando",
            "bubble_sub": "Muito amor e felicidade!",
            "dialogue": "Feliz Aniversário, Vitória Eliza! Que nunca faltem amor, saúde, paz e pessoas queridas ao seu redor em cada passo!",
        },
        {
            "row": 7,
            "title": "5. Dancinha Feliz",
            "subtitle": "Estrelas Douradas",
            "bubble_sub": "Comemorando com alegria!",
            "dialogue": "Feliz Aniversário! Continue espalhando essa energia contagiante e brilhando sempre! Parabéns pelo seu dia!",
        },
    ]

    # Pré-renderizar balões de fala em Pixel Art para cada etapa
    bubble_intro = build_pixel_speech_bubble(
        "Feliz Aniversário!",
        "Vitória Eliza chegou!",
        font_bubble_main,
        font_bubble_sub,
    )
    bubbles_by_stage = [
        build_pixel_speech_bubble(
            "Feliz Aniversário!",
            act["bubble_sub"],
            font_bubble_main,
            font_bubble_sub,
        )
        for act in celebration_actions
    ]
    bubble_finale = build_pixel_speech_bubble(
        "Feliz Aniversário!",
        "Parabéns, Vitória Eliza!",
        font_bubble_main,
        font_bubble_sub,
    )

    temp_raw_mp4 = "temp_vitoria_raw.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(temp_raw_mp4, fourcc, float(FPS), (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError("Não foi possível inicializar o cv2.VideoWriter.")

    print(f"Renderizando {TOTAL_FRAMES} quadros em HD ({WIDTH}x{HEIGHT} @ {FPS}fps)...")

    for f_idx in range(TOTAL_FRAMES):
        t_sec = f_idx / float(FPS)
        frame_img = bg_base.copy()
        draw = ImageDraw.Draw(frame_img)

        # 1. Estrelas cintilando no céu
        for sx, sy, sp in stars:
            twinkle = math.sin(t_sec * 3.5 + sp)
            if twinkle > 0.35:
                draw_pixel_star(draw, sx, sy, s=2, color=(255, 240, 150))
            else:
                draw.rectangle([sx, sy, sx + 2, sy + 2], fill=(210, 220, 255))

        # 2. Definir qual fase da animação estamos executando:
        # - 0.0s a 1.8s (0..53): Caminhada alegre entrando no palco (Row 1 walk_right -> Row 0 idle)
        # - 1.8s a 13.8s (54..413): As 5 ações de comemoração (2.4s = 72 quadros cada)
        # - 13.8s a 16.0s (414..479): Grand Finale com Bolo + Dança + Confetes intensos
        if f_idx < 54:
            active_stage_idx = -1
            if f_idx < 38:
                progress = f_idx / 38.0
                char_cx = int(170 + progress * 230)
                spr_row = 1  # walk_right
                spr_col = (f_idx // 4) % 6
            else:
                char_cx = 400
                spr_row = 0  # idle
                spr_col = (f_idx // 5) % 6
            current_bubble = bubble_intro
            dlg_text = "Feliz Aniversário, Vitória Eliza! Prepare-se: todas as suas ações especiais de comemoração estão prontas para a festa!"
            stage_local_frame = f_idx
        elif f_idx < 414:
            rel = f_idx - 54
            active_stage_idx = min(4, rel // 72)
            stage_local_frame = rel % 72
            act_info = celebration_actions[active_stage_idx]
            spr_row = act_info["row"]
            # Cada ação de comemoração tem 6 quadros; 6 quadros por segundo (5 ticks por frame) = 2 ciclos completos de 6 quadros
            spr_col = (stage_local_frame // 6) % 6
            char_cx = 400
            current_bubble = bubbles_by_stage[active_stage_idx]
            dlg_text = act_info["dialogue"]
        else:
            active_stage_idx = 5  # Finale! Todas as 5 ações acesas no painel lateral!
            stage_local_frame = f_idx - 414
            # Alterna entre o Bolo erguido (row 4) e a Festa de Confetes/Dança (row 5 / row 7)
            spr_row = 4 if stage_local_frame < 32 else 5
            spr_col = (stage_local_frame // 5) % 6
            char_cx = 400
            current_bubble = bubble_finale
            dlg_text = "FELIZ ANIVERSÁRIO, VITÓRIA ELIZA! Muita saúde, amor, paz, sucesso e alegrias hoje e sempre!"

        # 3. Topo: Placa de Madeira Stardew Valley com "FELIZ ANIVERSÁRIO, VITÓRIA ELIZA!"
        draw_stardew_frame(draw, 220, 12, WIDTH - 220, 84)
        title_str = "FELIZ ANIVERSÁRIO, VITÓRIA ELIZA!"
        tb = draw.textbbox((0, 0), title_str, font=font_banner)
        tx = (WIDTH - (tb[2] - tb[0])) // 2
        ty = 26
        draw.text((tx + 2, ty + 2), title_str, font=font_banner, fill=(224, 186, 128))
        draw.text((tx, ty), title_str, font=font_banner, fill=(142, 28, 38))

        # Corações e estrelas em pixel art nas pontas do banner superior
        heart_pulse = 3 if (f_idx // 10) % 2 == 0 else 4
        draw_pixel_heart(draw, 252, 34, scale=heart_pulse, color=(225, 45, 70))
        draw_pixel_star(draw, 290, 44, s=3, color=(240, 175, 35))
        draw_pixel_star(draw, WIDTH - 295, 44, s=3, color=(240, 175, 35))
        draw_pixel_heart(draw, WIDTH - 280, 34, scale=heart_pulse, color=(225, 45, 70))

        # 4. Sombra oval no palco sob os pés da Vitória Eliza
        shadow_w = 104
        shadow_h = 22
        draw.ellipse(
            [char_cx - shadow_w // 2, 476, char_cx + shadow_w // 2, 476 + shadow_h],
            fill=(72, 22, 28, 180),
        )

        # 5. Renderizar o Sprite Principal (5x = 240x360) da Vitória Eliza no palco
        main_sprite = rows_5x[spr_row][spr_col]
        spr_x = char_cx - main_sprite.width // 2
        spr_y = 496 - main_sprite.height
        frame_img.paste(main_sprite, (spr_x, spr_y), main_sprite)

        # Brilhos e corações extras ao redor da Vitória Eliza no palco
        for s_i in range(4):
            ang = t_sec * 2.4 + s_i * (math.pi / 2)
            gx = int(char_cx + math.cos(ang) * 118)
            gy = int(330 + math.sin(ang * 1.5) * 65)
            if (f_idx + s_i * 7) % 16 < 10:
                draw_pixel_star(draw, gx, gy, s=3, color=(255, 225, 75))

        # 6. Balão de Fala em Pixel Art flutuando acima da cabeça da Vitória Eliza
        bob_y = int(4 * math.sin(t_sec * 5.0))
        bub_x = char_cx - current_bubble.width // 2
        bub_y = spr_y - current_bubble.height + 28 + bob_y
        frame_img.paste(current_bubble, (bub_x, bub_y), current_bubble)

        # 7. Painel Direito: Galeria ao Vivo das 5 Ações de Comemoração da Vitória Eliza
        panel_x1, panel_y1, panel_x2, panel_y2 = 790, 102, 1254, 514
        draw_stardew_frame(draw, panel_x1, panel_y1, panel_x2, panel_y2)

        hdr = "AÇÕES DE COMEMORAÇÃO"
        hb = draw.textbbox((0, 0), hdr, font=font_card_title)
        hdr_x = (panel_x1 + panel_x2 - (hb[2] - hb[0])) // 2
        draw.text(
            (hdr_x, panel_y1 + 18),
            hdr,
            font=font_card_title,
            fill=(90, 43, 17),
        )
        draw_pixel_star(draw, hdr_x - 18, panel_y1 + 26, s=2, color=(235, 165, 30))
        draw_pixel_star(draw, hdr_x + (hb[2] - hb[0]) + 14, panel_y1 + 26, s=2, color=(235, 165, 30))

        # Desenhar os 5 mini-cards (em grade: 3 em cima, 2 centralizados embaixo)
        card_positions = [
            (810, 146, 946, 318),
            (954, 146, 1090, 318),
            (1098, 146, 1234, 318),
            (876, 326, 1012, 496),
            (1032, 326, 1168, 496),
        ]
        for idx, (cx1, cy1, cx2, cy2) in enumerate(card_positions):
            act = celebration_actions[idx]
            is_highlighted = (active_stage_idx == idx) or (active_stage_idx == 5)
            card_bg = (255, 245, 215) if is_highlighted else (236, 206, 156)
            border_c = (215, 55, 70) if is_highlighted else (156, 96, 38)
            border_w = 3 if is_highlighted else 2

            draw.rectangle([cx1, cy1, cx2, cy2], fill=card_bg, outline=border_c, width=border_w)
            if is_highlighted:
                draw.rectangle([cx1 + 3, cy1 + 3, cx2 - 3, cy2 - 3], outline=(255, 205, 65), width=2)

            # Mini sprite animado 2x (96x144) dentro do card
            mini_col = (f_idx // 5) % 6 if is_highlighted else (f_idx // 9) % 6
            mini_spr = rows_2x[act["row"]][mini_col]
            msx = (cx1 + cx2 - mini_spr.width) // 2
            msy = cy1 + 4
            frame_img.paste(mini_spr, (msx, msy), mini_spr)

            # Legenda da ação
            t_lbl = act["title"]
            tb_c = draw.textbbox((0, 0), t_lbl, font=font_card_sub)
            draw.text(
                ((cx1 + cx2 - (tb_c[2] - tb_c[0])) // 2, cy2 - 24),
                t_lbl,
                font=font_card_sub,
                fill=(145, 25, 38) if is_highlighted else (75, 38, 14),
            )

        # 8. Caixa de Diálogo Clássica do Stardew Valley na Parte Inferior (com Retrato e Corações)
        dlg_x1, dlg_y1, dlg_x2, dlg_y2 = 26, 524, 1254, 708
        draw_stardew_frame(draw, dlg_x1, dlg_y1, dlg_x2, dlg_y2)

        # Divisória vertical de madeira separando o texto (esquerda) e o retrato da Vitória Eliza (direita)
        div_x = 936
        draw.rectangle([div_x, dlg_y1 + 12, div_x + 8, dlg_y2 - 12], fill=(142, 82, 30))
        draw.rectangle([div_x + 2, dlg_y1 + 12, div_x + 6, dlg_y2 - 12], fill=(205, 135, 55))

        # Cabeçalho interno da caixa de diálogo: Badge "FELIZ ANIVERSÁRIO!" + 10 Corações de Amizade
        badge_x1, badge_y1, badge_x2, badge_y2 = 52, 542, 285, 574
        draw.rectangle([badge_x1, badge_y1, badge_x2, badge_y2], fill=(168, 34, 48), outline=(90, 20, 28), width=2)
        draw_pixel_star(draw, badge_x1 + 16, badge_y1 + 15, s=2, color=(255, 225, 75))
        draw.text((badge_x1 + 30, badge_y1 + 6), "FELIZ ANIVERSÁRIO!", font=font_dlg_tag, fill=(255, 245, 215))

        # 10 Corações vermelhos de amizade (Stardew Valley 10/10 Hearts)
        for h_i in range(10):
            hx = 305 + h_i * 26
            hy = 549 + (int(2 * math.sin(t_sec * 6 + h_i * 0.5)) if active_stage_idx == 5 else 0)
            draw_pixel_heart(draw, hx, hy, scale=3, color=(225, 40, 65))
        draw.text((575, 548), "10/10  •  Aniversariante do Vale", font=font_dlg_tag, fill=(112, 62, 26))

        # Efeito Typewriter na mensagem de Feliz Aniversário dentro da Caixa de Diálogo
        chars_visible = min(len(dlg_text), max(22, int(stage_local_frame * 3.4)))
        visible_dlg = dlg_text[:chars_visible]

        # Quebra de linha manual limpa para a área de diálogo
        words = visible_dlg.split(" ")
        lines: List[str] = []
        curr_line = ""
        for w in words:
            test_line = f"{curr_line} {w}".strip()
            w_box = draw.textbbox((0, 0), test_line, font=font_dlg_body)
            if (w_box[2] - w_box[0]) <= 855:
                curr_line = test_line
            else:
                lines.append(curr_line)
                curr_line = w
        if curr_line:
            lines.append(curr_line)

        for l_idx, line_str in enumerate(lines[:3]):
            ly = 586 + l_idx * 32
            draw.text((55, ly + 2), line_str, font=font_dlg_body, fill=(226, 192, 138))
            draw.text((54, ly), line_str, font=font_dlg_body, fill=(63, 29, 11))

        # Retrato da Vitória Eliza à direita da Caixa de Diálogo
        port_x = div_x + 16
        port_y = dlg_y1 + 14
        frame_img.paste(portrait_156, (port_x, port_y), portrait_156)

        # Nome e título ao lado do retrato na caixa direita
        name_x = port_x + 164
        draw.text((name_x + 1, dlg_y1 + 28 + 1), "Vitória", font=font_dlg_title, fill=(226, 192, 138))
        draw.text((name_x, dlg_y1 + 28), "Vitória", font=font_dlg_title, fill=(90, 32, 14))
        draw.text((name_x + 1, dlg_y1 + 54 + 1), "Eliza", font=font_dlg_title, fill=(226, 192, 138))
        draw.text((name_x, dlg_y1 + 54), "Eliza", font=font_dlg_title, fill=(90, 32, 14))

        draw.rectangle([name_x, dlg_y1 + 92, dlg_x2 - 18, dlg_y1 + 120], fill=(235, 195, 130), outline=(165, 105, 42))
        draw.text((name_x + 10, dlg_y1 + 97), "Dia de Festa!", font=font_card_sub, fill=(135, 32, 42))
        draw.text((name_x + 2, dlg_y1 + 130), "Pixel Valley Pets", font=font_card_sub, fill=(120, 72, 34))

        # 9. Chuva de Confetes em Pixel Art sobre a cena
        for p in confetti:
            p["y"] += p["vy"]
            p["x"] += p["vx"] + 0.6 * math.sin(t_sec * 3.0 + p["phase"])
            if p["y"] > 522:
                p["y"] = -12
                p["x"] = rng.uniform(30, WIDTH - 30)
            if p["y"] >= 0:
                px, py = int(p["x"]), int(p["y"])
                s = p["size"]
                draw.rectangle([px, py, px + s, py + max(3, s - 2)], fill=p["color"])

        # Converter RGBA (PIL) -> BGR (OpenCV) e gravar quadro
        rgb_arr = np.array(frame_img.convert("RGB"))
        bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
        writer.write(bgr_arr)

        if (f_idx + 1) % 120 == 0 or f_idx == TOTAL_FRAMES - 1:
            print(f"  -> Progresso: {f_idx + 1}/{TOTAL_FRAMES} quadros ({int((f_idx + 1) * 100 / TOTAL_FRAMES)}%)")

    writer.release()

    # Gerar trilha sonora Chiptune de Feliz Aniversário e combinar em H.264 MP4
    temp_wav = "temp_vitoria_bday.wav"
    print("Sintetizando melodia 16-bit de 'Parabéns pra Você'...")
    generate_birthday_wav(temp_wav, duration_sec=DURATION_SEC)

    ffmpeg_candidates = [
        r"C:\Users\Deivdson\AppData\Local\CapCut\Apps\8.9.1.3802\ffmpeg.exe",
        r"C:\Users\Deivdson\AppData\Local\CapCut\Apps\8.8.0.3774\ffmpeg.exe",
        "ffmpeg",
    ]
    ffmpeg_bin = None
    for cand in ffmpeg_candidates:
        if os.path.exists(cand):
            ffmpeg_bin = cand
            break

    encoded_ok = False
    if ffmpeg_bin:
        for v_codec in ("h264_nvenc", "h264_qsv", "mpeg4"):
            print(f"Codificando MP4 final ({v_codec} + AAC) via FFmpeg ({ffmpeg_bin})...")
            cmd = [
                ffmpeg_bin,
                "-y",
                "-i", temp_raw_mp4,
                "-i", temp_wav,
                "-c:v", v_codec,
                "-b:v", "5000k",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
                OUTPUT_MP4,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and os.path.exists(OUTPUT_MP4) and os.path.getsize(OUTPUT_MP4) > 50000:
                encoded_ok = True
                print(f"Codificação {v_codec} + AAC concluída com sucesso!")
                break
            else:
                print(f"Aviso FFmpeg ({v_codec}):", res.stderr[-300:] if res.stderr else "falha")

    if not encoded_ok:
        import shutil
        shutil.copyfile(temp_raw_mp4, OUTPUT_MP4)

    # Salvar cópia também dentro da pasta do avatar Vitória Eliza
    import shutil
    shutil.copyfile(OUTPUT_MP4, OUTPUT_AVATAR_MP4)

    # Limpar temporários
    for tmp in (temp_raw_mp4, temp_wav):
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass

    print(f"Vídeo MP4 gerado em:\n  1) {os.path.abspath(OUTPUT_MP4)}\n  2) {os.path.abspath(OUTPUT_AVATAR_MP4)}")


if __name__ == "__main__":
    main()
