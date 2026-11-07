"""
Motor de Desktop Pet Transparente (Windows / Tkinter).
Executa os bonequinhos animados estilo Stardew Valley diretamente sobre a área de trabalho,
com física de gravidade, caminhada, ações aleatórias, arrastar com o mouse e menu de contexto.
"""

import random
import ctypes
import textwrap
import tkinter as tk
from typing import Dict, List, Optional, Callable, Tuple
from PIL import Image, ImageDraw, ImageTk
from library_manager import AvatarRecord
from dialogue_box import StardewDialogueWindow
from avatar_tasks import (
    AVAILABLE_TASKS,
    get_avatar_assigned_tasks,
    OrganizeItemsModal,
    FishLargeFilesModal,
)
from gpt_luna import (
    is_gpt_luna_enabled,
    set_gpt_luna_enabled,
    get_gpt_luna_desktop_bubble,
    open_gpt_luna_settings_modal,
    load_avatar_personality,
    open_avatar_personality_modal,
)
from llm_sprite_designer import load_llm_settings
from sprite_generator import (
    extract_animation_frames,
    extract_social_interaction_frames,
    ANIMATION_ROWS,
    ANIMATION_LABELS,
    SOCIAL_INTERACTION_ACTIONS,
    CELL_W,
    CELL_H,
)


TRANSPARENT_KEY = "#010203"

STARDEW_QUOTES = [
    "Que dia lindo na fazenda! 🌻",
    "Hora de um Café Expresso Triplo! ☕",
    "Será que hoje os espíritos estão de bom humor? ✨",
    "Preciso regar as chirivias antes das 18h! 💧",
    "Acho que fisguei uma Carpa Lendária! 🎣",
    "Encontrei um Fragmento Prismático no código! 💎",
    "Nada como descansar embaixo de uma árvore... 🌳",
    "Oi! Clique duas vezes em mim para fazer carinho! ❤️",
]


def get_work_area() -> tuple:
    """Obtém a área útil da tela do Windows (descontando a barra de tarefas)."""
    try:
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]
        rect = RECT()
        ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
        if rect.right > rect.left and rect.bottom > rect.top:
            return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception:
        pass
    return (0, 0, 1920, 1030)


class DesktopPetWindow:
    """Representa um bonequinho animado rodando sobre a área de trabalho."""

    def __init__(
        self,
        master: tk.Misc,
        record: AvatarRecord,
        on_close_callback: Optional[Callable[[str], None]] = None,
        gravity_enabled: bool = True,
    ):
        self.master = master
        self.record = record
        self.avatar_id = record.avatar_id
        self.on_close_callback = on_close_callback
        self.gravity_enabled = gravity_enabled
        self.scale = max(2, min(8, int(record.config.scale or 4)))

        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.wm_attributes("-topmost", True)
        self.win.wm_attributes("-transparentcolor", TRANSPARENT_KEY)
        self.win.configure(bg=TRANSPARENT_KEY)

        self.spritesheet: Image.Image = record.load_spritesheet()
        self.tk_frames: Dict[str, List[ImageTk.PhotoImage]] = {}
        self.tk_social_frames: Dict[Tuple[str, str], List[ImageTk.PhotoImage]] = {}
        self._load_scaled_frames()

        self.sprite_w = CELL_W * self.scale
        self.sprite_h = CELL_H * self.scale
        self.speech_area_h = 64  # Espaço amplo acima da cabeça para balão de fala em Pixel Art (1-2 linhas + cauda)
        self.canvas_w = max(268, self.sprite_w + 120)
        self.canvas_h = self.sprite_h + self.speech_area_h

        self.canvas = tk.Canvas(
            self.win,
            width=self.canvas_w,
            height=self.canvas_h,
            bg=TRANSPARENT_KEY,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        # Posição inicial acima da barra de tarefas
        wl, wt, wr, wb = get_work_area()
        self.min_x = wl + 6
        self.max_x = max(wl + 100, wr - self.canvas_w - 6)
        self.min_y = wt + 10
        self.ground_y = max(wt + 50, wb - self.canvas_h + 4)

        self.x = float(random.randint(self.min_x + 20, max(self.min_x + 40, self.max_x - 20)))
        self.y = float(self.ground_y if self.gravity_enabled else random.randint(self.min_y + 60, self.ground_y))
        self.vy = 0.0

        # Estado de animação e comportamento
        self.current_action = "idle"
        self.frame_idx = 0
        self.ticks_in_state = 0
        self.state_duration_ticks = random.randint(25, 55)
        self.is_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.speech_text: Optional[str] = None
        self.speech_full_wrapped: str = ""
        self.speech_typed_chars: int = 0
        self.speech_type_after_id: Optional[str] = None
        self.speech_timer = 0
        self.speech_bob_phase = 0
        self.speech_bubble_tk: Optional[ImageTk.PhotoImage] = None
        self.running = True
        self.dialogue_window: Optional[StardewDialogueWindow] = None
        self.on_portrait_updated_callback: Optional[Callable[[AvatarRecord], None]] = None
        self.on_open_guide_callback: Optional[Callable[[], None]] = None
        self.on_open_tasks_manager_callback: Optional[Callable[[], None]] = None
        self.on_request_social_encounter_callback: Optional[Callable[[str, Optional[str]], None]] = None

        # Estado de interação social sincronizada entre avatares (por proximidade ou manual)
        self.in_social_interaction: bool = False
        self.social_facing: str = "right"
        self.social_partner_id: Optional[str] = None
        self.social_cooldown_ticks: int = 18
        self.social_second_line: Optional[str] = None
        self.social_switch_tick: int = 0

        # Elementos do Canvas
        self.sprite_item = self.canvas.create_image(
            self.canvas_w // 2,
            self.canvas_h - self.sprite_h // 2,
            image=self.tk_frames["idle"][0],
        )
        self.speech_bg_item = self.canvas.create_image(
            self.canvas_w // 2,
            self.speech_area_h // 2,
            state="hidden",
        )
        self.speech_shadow_text_item = self.canvas.create_text(
            self.canvas_w // 2 + 1,
            self.speech_area_h // 2 - 3,
            text="",
            fill="#E5C48B",
            font=("Segoe UI", 8, "bold"),
            justify="center",
            state="hidden",
        )
        self.speech_text_item = self.canvas.create_text(
            self.canvas_w // 2,
            self.speech_area_h // 2 - 4,
            text="",
            fill="#3B1A08",
            font=("Segoe UI", 8, "bold"),
            justify="center",
            state="hidden",
        )

        # Eventos de Mouse
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_end)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Button-3>", self._show_context_menu)

        self._build_context_menu()
        self._update_geometry()
        self.show_speech(f"Olá! Eu sou {self.record.config.name}! ✨", duration=42)
        self._animate_step()
        self._physics_step()

    def _clean_pil_frames_to_tk(self, pil_frames: List[Image.Image]) -> List[ImageTk.PhotoImage]:
        """Substitui pixels semitransparentes para evitar borda serrilhada com transparentcolor do Windows."""
        cleaned_frames = []
        for pf in pil_frames:
            rgba = pf.convert("RGBA")
            bg = Image.new("RGBA", rgba.size, (1, 2, 3, 255))
            alpha = rgba.split()[3].point(lambda a: 255 if a > 90 else 0)
            bg.paste(rgba, (0, 0), mask=alpha)
            cleaned_frames.append(ImageTk.PhotoImage(bg.convert("RGB")))
        return cleaned_frames

    def _load_scaled_frames(self):
        self.tk_frames.clear()
        self.tk_social_frames.clear()
        for action in ANIMATION_ROWS.keys():
            pil_frames = extract_animation_frames(self.spritesheet, action, scale=self.scale)
            self.tk_frames[action] = self._clean_pil_frames_to_tk(pil_frames)

        # Carregar os 6 frames sincronizados de interação social entre avatares (olhando para direita e esquerda)
        for social_act in SOCIAL_INTERACTION_ACTIONS.keys():
            for facing in ("right", "left"):
                pil_social = extract_social_interaction_frames(
                    self.spritesheet,
                    social_act,
                    facing=facing,
                    scale=self.scale,
                )
                self.tk_social_frames[(social_act, facing)] = self._clean_pil_frames_to_tk(pil_social)
            self.tk_frames[social_act] = self.tk_social_frames[(social_act, "right")]

    def _build_context_menu(self):
        self.menu = tk.Menu(self.win, tearoff=0, bg="#F7E2B8", fg="#3A1E08", activebackground="#D98A2B", activeforeground="white")
        self.menu.add_command(label=f"🌾 {self.record.config.name}", state="disabled")
        self.menu.add_separator()
        self.menu.add_command(
            label="💬 Abrir Caixa de Diálogo (Interagir)",
            command=self.open_dialogue_box,
        )
        self.menu.add_separator()

        # Tarefas de Área de Trabalho atribuídas a este avatar
        assigned_tasks = get_avatar_assigned_tasks(self.avatar_id, self.record.config.name)
        tasks_menu = tk.Menu(self.menu, tearoff=0, bg="#F7E2B8", fg="#3A1E08", activebackground="#3E8E4C", activeforeground="white")
        if assigned_tasks:
            for tid in assigned_tasks:
                tinfo = AVAILABLE_TASKS.get(tid)
                if tinfo:
                    tasks_menu.add_command(
                        label=f"{tinfo['title']}",
                        command=lambda task_key=tid: self.execute_desktop_task(task_key),
                    )
                    # Adicionar também como atalho rápido direto no menu principal!
                    self.menu.add_command(
                        label=f"{tinfo['title']}",
                        command=lambda task_key=tid: self.execute_desktop_task(task_key),
                    )
            tasks_menu.add_separator()
        else:
            tasks_menu.add_command(label="(Nenhuma tarefa atribuída a este avatar)", state="disabled")
            tasks_menu.add_separator()

        if self.on_open_tasks_manager_callback:
            tasks_menu.add_command(
                label="⚙️ Configurar Qual Avatar Executa Qual Tarefa...",
                command=self.on_open_tasks_manager_callback,
            )
        self.menu.add_cascade(label="🛠️ Tarefas & Funções do Avatar", menu=tasks_menu)
        self.menu.add_separator()

        actions_menu = tk.Menu(self.menu, tearoff=0, bg="#F7E2B8", fg="#3A1E08")
        for act_key in ANIMATION_ROWS.keys():
            act_label = ANIMATION_LABELS.get(act_key, act_key)
            actions_menu.add_command(
                label=act_label,
                command=lambda k=act_key: self.set_action(k, duration_ticks=65),
            )
        self.menu.add_cascade(label="🎬 Executar Ação Agora", menu=actions_menu)

        # Submenu de Interação Sincronizada entre Avatares
        social_menu = tk.Menu(self.menu, tearoff=0, bg="#F7E2B8", fg="#3A1E08", activebackground="#7A49A5", activeforeground="white")
        social_menu.add_command(
            label="✨ Promover Encontro Automático (Baseado na Personalidade)",
            command=lambda: self.request_social_encounter(None),
        )
        social_menu.add_separator()
        for soc_key, soc_label in SOCIAL_INTERACTION_ACTIONS.items():
            social_menu.add_command(
                label=soc_label,
                command=lambda sk=soc_key: self.request_social_encounter(sk),
            )
        self.menu.add_cascade(label="🤝 Interagir em Dupla com Outro Avatar", menu=social_menu)

        self.menu.add_command(label="💭 Falar Frase Rápida", command=self.say_random_quote)
        self.menu.add_command(label="❤️ Fazer Carinho", command=self.give_pet_affection)
        self.menu.add_separator()

        scale_menu = tk.Menu(self.menu, tearoff=0, bg="#F7E2B8", fg="#3A1E08")
        for s in (3, 4, 5, 6):
            scale_menu.add_command(
                label=f"Tamanho {s}x",
                command=lambda sc=s: self.set_scale(sc),
            )
        self.menu.add_cascade(label="🔍 Tamanho do Sprite", menu=scale_menu)

        self.menu.add_command(
            label="🧲 Alternar Gravidade (Barra de Tarefas / Livre)",
            command=self.toggle_gravity,
        )
        self.menu.add_command(
            label="🔄 Recarregar Sprite / Atualizar Pet",
            command=self.reload_self_from_disk,
        )
        self.menu.add_separator()
        self.menu.add_command(
            label="🎭 Personalizar Personalidade (Gostos & Emoções)...",
            command=self.open_personality_customizer,
        )
        self.menu.add_command(
            label="🌙 Alternar Personalidade GPT Luna (ON/OFF)",
            command=self.toggle_gpt_luna_personality,
        )
        self.menu.add_command(
            label="⚙️ Configurar Personalidade GPT Luna...",
            command=lambda: open_gpt_luna_settings_modal(self.master),
        )
        if self.on_open_guide_callback:
            self.menu.add_command(
                label="📖 Guia & Prompts Gemini (Criar Skins/Diálogos)",
                command=self.on_open_guide_callback,
            )
        self.menu.add_separator()
        self.menu.add_command(label="🏠 Recolher para Biblioteca", command=self.close)

    def execute_desktop_task(self, task_id: str):
        """Executa uma tarefa real na área de trabalho com animação e fala temática do avatar."""
        assigned = get_avatar_assigned_tasks(self.avatar_id, self.record.config.name)
        if task_id not in assigned:
            self.show_speech("Ops! Essa tarefa não está atribuída a mim!", duration=40)
            return

        def _trigger_anim_and_speech(act: str, bubble_txt: str):
            self.set_action(act, duration_ticks=85)
            if bubble_txt:
                self.show_speech(bubble_txt, duration=55)

        if task_id == "organize_items":
            OrganizeItemsModal(
                master=self.master,
                avatar_name=self.record.config.name,
                on_action_trigger=_trigger_anim_and_speech,
            )
        elif task_id == "fish_large_files":
            FishLargeFilesModal(
                master=self.master,
                avatar_name=self.record.config.name,
                on_action_trigger=_trigger_anim_and_speech,
            )

    def open_personality_customizer(self):
        """Abre o formulário de múltipla escolha para personalizar gostos e emoções deste pet."""
        def _on_saved(rec, new_p):
            dom_emo = new_p.get("dominant_emotion", "😊")
            self.set_action("happy_dance", duration_ticks=45)
            self.show_speech(f"🎭 {dom_emo}!", duration=45)
            if self.on_portrait_updated_callback:
                self.on_portrait_updated_callback(self.record)

        open_avatar_personality_modal(
            parent=self.master,
            record=self.record,
            on_saved_callback=_on_saved,
        )

    def toggle_gpt_luna_personality(self):
        new_state = not is_gpt_luna_enabled()
        set_gpt_luna_enabled(new_state)
        if new_state:
            self.set_action("happy_dance", duration_ticks=45)
            self.show_speech("🌙 GPT Luna Ativado! ✨", duration=45)
        else:
            self.show_speech("🌾 Modo Clássico!", duration=35)

    def set_scale(self, new_scale: int):
        self.scale = new_scale
        self._load_scaled_frames()
        self.sprite_w = CELL_W * self.scale
        self.sprite_h = CELL_H * self.scale
        self.canvas_w = max(268, self.sprite_w + 120)
        self.canvas_h = self.sprite_h + self.speech_area_h
        self.canvas.config(width=self.canvas_w, height=self.canvas_h)
        self.canvas.coords(
            self.sprite_item,
            self.canvas_w // 2,
            self.canvas_h - self.sprite_h // 2,
        )
        wl, wt, wr, wb = get_work_area()
        self.max_x = max(wl + 100, wr - self.canvas_w - 6)
        self.ground_y = max(wt + 50, wb - self.canvas_h + 4)
        if self.gravity_enabled:
            self.y = float(self.ground_y)
        self._update_geometry()
        if self.speech_timer > 0 and self.speech_text:
            self.show_speech(self.speech_text, duration=self.speech_timer)

    def toggle_gravity(self):
        self.gravity_enabled = not self.gravity_enabled
        mode_txt = "Gravidade Ativada! 🧲" if self.gravity_enabled else "Modo Livre! 🕊️"
        self.show_speech(mode_txt, duration=32)

    def _build_pixel_bubble_image(self, width: int, height: int, tail_h: int = 8) -> ImageTk.PhotoImage:
        """
        Desenha um balão de fala autêntico em Pixel Art 16-bit estilo Stardew Valley:
        - Cantos chanfrados em degraus de 2px
        - Moldura tripla de madeira/ouro (#3D1B08 externo, #BA732A madeira média, #FFF9EB brilho interno)
        - Preenchimento pergaminho creme (#FCF0D5) com faixa de sombra quente na base (#EED6A4)
        - Cravos decorativos nos 4 cantos e cauda apontando para o personagem
        """
        img = Image.new("RGB", (width, height + tail_h), (1, 2, 3))
        draw = ImageDraw.Draw(img)

        c_outer = (61, 27, 8)       # #3D1B08 Contorno escuro pixel art
        c_wood = (186, 115, 42)     # #BA732A Moldura dourada/madeira
        c_highlight = (255, 250, 235)
        c_parchment = (252, 240, 213)
        c_shade = (237, 212, 162)
        c_rivet = (122, 62, 18)

        w = width
        h = height

        # 1. Silhueta externa chanfrada (stepped pixel corners)
        draw.rectangle([4, 0, w - 5, h - 1], fill=c_outer)
        draw.rectangle([2, 2, w - 3, h - 3], fill=c_outer)
        draw.rectangle([0, 4, w - 1, h - 5], fill=c_outer)

        # 2. Moldura intermediária de madeira esculpida
        draw.rectangle([4, 2, w - 5, h - 3], fill=c_wood)
        draw.rectangle([2, 4, w - 3, h - 5], fill=c_wood)

        # 3. Interior de pergaminho claro + brilho superior + sombra inferior
        draw.rectangle([4, 4, w - 5, h - 5], fill=c_parchment)
        draw.rectangle([5, 4, w - 6, 5], fill=c_highlight)
        draw.rectangle([4, h - 8, w - 5, h - 5], fill=c_shade)

        # 4. Cravos pixel art nos 4 cantos internos
        for rx, ry in ((6, 6), (w - 8, 6), (6, h - 8), (w - 8, h - 8)):
            draw.rectangle([rx, ry, rx + 1, ry + 1], fill=c_rivet)

        # 5. Cauda (ponteiro) centralizada apontando para a cabeça do pet
        cx = w // 2
        # Contorno escuro da cauda em degraus de 2px
        draw.rectangle([cx - 6, h - 2, cx + 6, h + 1], fill=c_outer)
        draw.rectangle([cx - 4, h + 2, cx + 4, h + 4], fill=c_outer)
        draw.rectangle([cx - 2, h + 5, cx + 2, h + 7], fill=c_outer)
        # Preenchimento interno da cauda
        draw.rectangle([cx - 4, h - 4, cx + 4, h], fill=c_shade)
        draw.rectangle([cx - 2, h + 1, cx + 2, h + 4], fill=c_parchment)

        return ImageTk.PhotoImage(img)

    def _format_speech_lines(self, raw_text: str) -> str:
        clean = " ".join(raw_text.strip().split())
        if len(clean) > 58:
            clean = clean[:55].rstrip() + "..."
        lines = textwrap.wrap(clean, width=25)
        if len(lines) > 2:
            lines = lines[:2]
            if not lines[1].endswith("..."):
                lines[1] = lines[1][:22].rstrip() + "..."
        return "\n".join(lines) if lines else clean

    def show_speech(self, text: str, duration: int = 44):
        if self.speech_type_after_id:
            try:
                self.win.after_cancel(self.speech_type_after_id)
            except Exception:
                pass
            self.speech_type_after_id = None

        self.speech_text = text
        self.speech_timer = max(duration, 38)
        self.speech_full_wrapped = self._format_speech_lines(text)
        lines = self.speech_full_wrapped.split("\n")
        max_line_len = max((len(line) for line in lines), default=10)
        num_lines = len(lines)

        # Medir exatamente a largura/altura em pixels renderizada pela fonte no Canvas
        self.canvas.itemconfigure(
            self.speech_text_item,
            text=self.speech_full_wrapped,
            width=self.canvas_w - 28,
            state="normal",
        )
        self.canvas.itemconfigure(
            self.speech_shadow_text_item,
            text=self.speech_full_wrapped,
            width=self.canvas_w - 28,
            state="normal",
        )
        bbox = self.canvas.bbox(self.speech_text_item)
        if bbox:
            measured_w = (bbox[2] - bbox[0]) + 28
            measured_h = (bbox[3] - bbox[1]) + 16
        else:
            measured_w = max_line_len * 8 + 30
            measured_h = 30 if num_lines == 1 else 46

        bubble_w = max(120, min(self.canvas_w - 4, measured_w))
        bubble_h = max(30 if num_lines == 1 else 46, min(self.speech_area_h - 10, measured_h))
        tail_h = 8

        self.speech_bubble_tk = self._build_pixel_bubble_image(bubble_w, bubble_h, tail_h=tail_h)
        cx = self.canvas_w // 2
        cy = self.speech_area_h - (bubble_h + tail_h) // 2 - 2
        text_cy = cy - tail_h // 2

        self.speech_base_cy = cy
        self.speech_text_base_cy = text_cy

        self.canvas.itemconfigure(self.speech_bg_item, image=self.speech_bubble_tk, state="normal")
        self.canvas.coords(self.speech_bg_item, cx, cy)

        self.speech_typed_chars = 0
        self.canvas.coords(self.speech_shadow_text_item, cx + 1, text_cy + 1)
        self.canvas.coords(self.speech_text_item, cx, text_cy)
        self.canvas.itemconfigure(self.speech_shadow_text_item, text="", state="normal")
        self.canvas.itemconfigure(self.speech_text_item, text="", state="normal")
        self._step_speech_typewriter()

    def _step_speech_typewriter(self):
        if not self.running or self.speech_timer <= 0:
            return
        total = len(self.speech_full_wrapped)
        if self.speech_typed_chars < total:
            self.speech_typed_chars = min(total, self.speech_typed_chars + 2)
            sub = self.speech_full_wrapped[: self.speech_typed_chars]
            self.canvas.itemconfigure(self.speech_shadow_text_item, text=sub)
            self.canvas.itemconfigure(self.speech_text_item, text=sub)
            self.speech_type_after_id = self.win.after(24, self._step_speech_typewriter)
        else:
            self.canvas.itemconfigure(self.speech_shadow_text_item, text=self.speech_full_wrapped)
            self.canvas.itemconfigure(self.speech_text_item, text=self.speech_full_wrapped)
            self.speech_type_after_id = None

    def say_random_quote(self):
        if is_gpt_luna_enabled():
            p = load_avatar_personality(self.record.folder_path, self.record.config.name, self.record.avatar_id)
            quote = get_gpt_luna_desktop_bubble(self.record.config.name, self.current_action, personality=p)
        else:
            quote = random.choice(STARDEW_QUOTES)
        self.show_speech(quote, duration=55)

    def set_action(self, action: str, duration_ticks: int = 45):
        if action in self.tk_frames:
            self.in_social_interaction = False
            self.social_partner_id = None
            self.social_second_line = None
            self.current_action = action
            self.frame_idx = 0
            self.ticks_in_state = 0
            self.state_duration_ticks = duration_ticks

    def request_social_encounter(self, forced_action: Optional[str] = None):
        """Solicita ao coordenador principal um encontro sincronizado com outro avatar ativo."""
        if self.on_request_social_encounter_callback:
            self.on_request_social_encounter_callback(self.avatar_id, forced_action)
        else:
            act = forced_action or "social_coffee_toast"
            self.set_action(act, duration_ticks=42)
            self.show_speech("🤝 Procure outro avatar na tela para interagir!", duration=40)

    def start_social_encounter_role(
        self,
        social_action: str,
        facing: str,
        partner_id: str,
        duration_ticks: int,
        first_bubble: str,
        second_bubble: str,
    ):
        """Inicia o papel sincronizado deste avatar em uma animação de encontro em dupla."""
        if (social_action, facing) not in self.tk_social_frames:
            social_action = "social_coffee_toast"
        self.in_social_interaction = True
        self.social_facing = facing
        self.social_partner_id = partner_id
        self.current_action = social_action
        self.frame_idx = 0
        self.ticks_in_state = 0
        self.state_duration_ticks = max(24, duration_ticks)
        self.social_second_line = second_bubble
        self.social_switch_tick = max(12, duration_ticks // 2)
        if first_bubble:
            self.show_speech(first_bubble, duration=max(20, self.social_switch_tick))

    def pick_random_next_action(self):
        """Escolhe uma ação autônoma aleatória com pesos naturais do Stardew Valley."""
        weighted_Pool = (
            ["idle"] * 4
            + ["walk_right"] * 4
            + ["walk_left"] * 4
            + ["water_crops"] * 2
            + ["coffee_break"] * 2
            + ["fishing"] * 2
            + ["happy_dance"] * 2
            + ["sleep_sit"] * 2
        )
        chosen = random.choice(weighted_Pool)
        # Evitar andar contra a borda da tela
        if chosen == "walk_left" and self.x <= self.min_x + 25:
            chosen = "walk_right"
        elif chosen == "walk_right" and self.x >= self.max_x - 25:
            chosen = "walk_left"

        dur = random.randint(28, 70)
        self.set_action(chosen, duration_ticks=dur)

        # Chance de mostrar um comentário fofo ao iniciar uma ação especial
        if random.random() < 0.22:
            settings = load_llm_settings()
            if settings.get("luna_enabled", True) and settings.get("luna_autonomous_speech", True):
                p = load_avatar_personality(self.record.folder_path, self.record.config.name, self.record.avatar_id)
                self.show_speech(get_gpt_luna_desktop_bubble(self.record.config.name, chosen, personality=p), duration=38)
            else:
                action_comments = {
                    "water_crops": "Regando a plantinha... 🌱",
                    "coffee_break": "Hmm, cafezinho quente! ☕",
                    "fishing": "Paciência de pescador... 🎣",
                    "happy_dance": "Uhul! Dia de festival! 🎉",
                    "sleep_sit": "Só uma sonequinha... 💤",
                }
                if chosen in action_comments:
                    self.show_speech(action_comments[chosen], duration=35)

    def _on_drag_start(self, event):
        self.is_dragging = True
        self.in_social_interaction = False
        self.social_partner_id = None
        self.social_second_line = None
        self.social_cooldown_ticks = 25
        self.vy = 0.0
        self.drag_offset_x = event.x
        self.drag_offset_y = event.y
        self.set_action("happy_dance", duration_ticks=30)
        self.show_speech(f"Uou! {self.record.config.name} voando!", duration=20)

    def _on_drag_motion(self, event):
        if not self.is_dragging:
            return
        new_x = self.win.winfo_x() + event.x - self.drag_offset_x
        new_y = self.win.winfo_y() + event.y - self.drag_offset_y
        self.x = float(new_x)
        self.y = float(new_y)
        self._update_geometry()

    def _on_drag_end(self, event):
        self.is_dragging = False

    def give_pet_affection(self):
        self.set_action("happy_dance", duration_ticks=40)
        self.show_speech(f"❤️ {self.record.config.name} adorou!", duration=38)

    def _on_double_click(self, event):
        self.open_dialogue_box()

    def open_dialogue_box(self):
        """Abre a Caixa de Diálogo estilo Stardew Valley para interagir com o personagem."""
        self.set_action("idle", duration_ticks=80)
        self.show_speech("💬 Vamos conversar!", duration=35)
        if self.dialogue_window is not None and self.dialogue_window.win.winfo_exists():
            self.dialogue_window.focus()
            return

        def _on_dlg_action(act: str, bubble_txt: str):
            self.set_action(act, duration_ticks=55)
            if bubble_txt:
                self.show_speech(bubble_txt, duration=40)

        def _on_dlg_closed():
            self.dialogue_window = None

        self.dialogue_window = StardewDialogueWindow(
            master=self.master,
            record=self.record,
            on_action_trigger=_on_dlg_action,
            on_portrait_updated=self.on_portrait_updated_callback,
            on_close=_on_dlg_closed,
            on_execute_task=self.execute_desktop_task,
            on_open_tasks_manager=self.on_open_tasks_manager_callback,
        )

    def _show_context_menu(self, event):
        self._build_context_menu()
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _update_geometry(self):
        if not self.running:
            return
        ix = int(self.x)
        iy = int(self.y)
        self.win.geometry(f"{self.canvas_w}x{self.canvas_h}+{ix}+{iy}")

    def _animate_step(self):
        if not self.running:
            return

        if self.social_cooldown_ticks > 0 and not self.in_social_interaction:
            self.social_cooldown_ticks -= 1

        if self.in_social_interaction and (self.current_action, self.social_facing) in self.tk_social_frames:
            frames = self.tk_social_frames[(self.current_action, self.social_facing)]
        else:
            frames = self.tk_frames.get(self.current_action, self.tk_frames["idle"])
        self.frame_idx = (self.frame_idx + 1) % len(frames)
        self.canvas.itemconfigure(self.sprite_item, image=frames[self.frame_idx])

        # Atualizar timer e flutuação suave do balão de fala em Pixel Art
        if self.speech_timer > 0:
            self.speech_timer -= 1
            self.speech_bob_phase = (self.speech_bob_phase + 1) % 4
            bob_offset = -1 if self.speech_bob_phase in (1, 2) else 0
            cx = self.canvas_w // 2
            base_cy = getattr(self, "speech_base_cy", self.speech_area_h // 2)
            base_tcy = getattr(self, "speech_text_base_cy", self.speech_area_h // 2 - 4)
            self.canvas.coords(self.speech_bg_item, cx, base_cy + bob_offset)
            self.canvas.coords(self.speech_shadow_text_item, cx + 1, base_tcy + 1 + bob_offset)
            self.canvas.coords(self.speech_text_item, cx, base_tcy + bob_offset)
            if self.speech_timer == 0:
                self.canvas.itemconfigure(self.speech_bg_item, state="hidden")
                self.canvas.itemconfigure(self.speech_shadow_text_item, state="hidden")
                self.canvas.itemconfigure(self.speech_text_item, state="hidden")

        # Contagem de estado para próxima ação aleatória ou segundo turno de encontro social
        if not self.is_dragging:
            self.ticks_in_state += 1
            if (
                self.in_social_interaction
                and self.social_second_line
                and self.ticks_in_state == self.social_switch_tick
            ):
                rem = max(20, self.state_duration_ticks - self.ticks_in_state + 8)
                self.show_speech(self.social_second_line, duration=rem)
                self.social_second_line = None

            if self.ticks_in_state >= self.state_duration_ticks:
                if self.in_social_interaction:
                    was_facing = self.social_facing
                    self.in_social_interaction = False
                    self.social_partner_id = None
                    self.social_second_line = None
                    self.social_cooldown_ticks = random.randint(65, 110)
                    # Após se encontrarem e interagirem, cada um segue seu caminho naturalmente
                    part_dir = "walk_left" if was_facing == "right" else "walk_right"
                    if part_dir == "walk_left" and self.x <= self.min_x + 30:
                        part_dir = "walk_right"
                    elif part_dir == "walk_right" and self.x >= self.max_x - 30:
                        part_dir = "walk_left"
                    self.set_action(part_dir, duration_ticks=random.randint(24, 42))
                else:
                    self.pick_random_next_action()

        self.win.after(180, self._animate_step)

    def _physics_step(self):
        if not self.running:
            return

        if not self.is_dragging:
            moved = False
            speed = 2.4 * (self.scale / 4.0)

            if self.current_action == "walk_right":
                self.x += speed
                moved = True
                if self.x >= self.max_x:
                    self.x = float(self.max_x)
                    self.set_action("walk_left", duration_ticks=random.randint(30, 60))
            elif self.current_action == "walk_left":
                self.x -= speed
                moved = True
                if self.x <= self.min_x:
                    self.x = float(self.min_x)
                    self.set_action("walk_right", duration_ticks=random.randint(30, 60))

            # Gravidade suave até a barra de tarefas quando ativada
            if self.gravity_enabled:
                if self.y < self.ground_y:
                    self.vy = min(18.0, self.vy + 1.2)
                    self.y += self.vy
                    if self.y >= self.ground_y:
                        self.y = float(self.ground_y)
                        self.vy = 0.0
                    moved = True
                elif self.y > self.ground_y:
                    self.y = float(self.ground_y)
                    self.vy = 0.0
                    moved = True

            if moved:
                self._update_geometry()

        self.win.after(30, self._physics_step)

    def reload_from_record(self, updated_record: AvatarRecord):
        """Atualiza o bonequinho em tempo real caso seja editado na biblioteca."""
        self.record = updated_record
        self.spritesheet = updated_record.load_spritesheet()
        self._load_scaled_frames()
        if self.dialogue_window is not None and self.dialogue_window.win.winfo_exists():
            self.dialogue_window.record = updated_record
            self.dialogue_window._refresh_portrait_display()

    def reload_self_from_disk(self):
        """Recarrega imediatamente o spritesheet e retrato do disco para este pet."""
        self.spritesheet = self.record.load_spritesheet()
        self._load_scaled_frames()
        if self.dialogue_window is not None and self.dialogue_window.win.winfo_exists():
            self.dialogue_window._refresh_portrait_display()
        self.show_speech("Sprite Recarregado! 🔄", duration=35)

    def close(self):
        if not self.running:
            return
        self.running = False
        if self.dialogue_window is not None:
            try:
                self.dialogue_window.close()
            except Exception:
                pass
            self.dialogue_window = None
        try:
            self.win.destroy()
        except Exception:
            pass
        if self.on_close_callback:
            self.on_close_callback(self.avatar_id)
