"""
Motor de Desktop Pet Transparente (Windows / Tkinter).
Executa os bonequinhos animados estilo Stardew Valley diretamente sobre a área de trabalho,
com física de gravidade, caminhada, ações aleatórias, arrastar com o mouse e menu de contexto.
"""

import random
import ctypes
import tkinter as tk
from typing import Dict, List, Optional, Callable
from PIL import Image, ImageTk
from library_manager import AvatarRecord
from dialogue_box import StardewDialogueWindow
from gpt_luna import (
    is_gpt_luna_enabled,
    set_gpt_luna_enabled,
    get_gpt_luna_desktop_bubble,
    open_gpt_luna_settings_modal,
)
from llm_sprite_designer import load_llm_settings
from sprite_generator import (
    extract_animation_frames,
    ANIMATION_ROWS,
    ANIMATION_LABELS,
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
        self._load_scaled_frames()

        self.canvas_w = CELL_W * self.scale
        self.canvas_h = CELL_H * self.scale + 28  # Espaço extra acima para balão de fala/nome

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
        self.min_x = wl + 10
        self.max_x = max(wl + 100, wr - self.canvas_w - 10)
        self.min_y = wt + 10
        self.ground_y = max(wt + 50, wb - self.canvas_h + 4)

        self.x = float(random.randint(self.min_x + 40, max(self.min_x + 50, self.max_x - 40)))
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
        self.speech_text: Optional[str] = f"Olá! Eu sou {self.record.config.name}!"
        self.speech_timer = 35
        self.running = True
        self.dialogue_window: Optional[StardewDialogueWindow] = None
        self.on_portrait_updated_callback: Optional[Callable[[AvatarRecord], None]] = None
        self.on_open_guide_callback: Optional[Callable[[], None]] = None

        # Elementos do Canvas
        self.sprite_item = self.canvas.create_image(
            self.canvas_w // 2,
            self.canvas_h - (CELL_H * self.scale) // 2,
            image=self.tk_frames["idle"][0],
        )
        self.speech_bg_item = self.canvas.create_rectangle(
            4, 2, self.canvas_w - 4, 22,
            fill="#F7E2B8",
            outline="#6B3710",
            width=2,
            state="hidden",
        )
        self.speech_text_item = self.canvas.create_text(
            self.canvas_w // 2,
            12,
            text="",
            fill="#4A2508",
            font=("Segoe UI", 8, "bold"),
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
        self._animate_step()
        self._physics_step()

    def _load_scaled_frames(self):
        self.tk_frames.clear()
        for action in ANIMATION_ROWS.keys():
            pil_frames = extract_animation_frames(self.spritesheet, action, scale=self.scale)
            # Substituir pixels semitransparentes para evitar borda serrilhada com transparentcolor do Windows
            cleaned_frames = []
            for pf in pil_frames:
                rgba = pf.convert("RGBA")
                bg = Image.new("RGBA", rgba.size, (1, 2, 3, 255))
                # Alpha threshold limpo para pixel art
                alpha = rgba.split()[3].point(lambda a: 255 if a > 90 else 0)
                bg.paste(rgba, (0, 0), mask=alpha)
                cleaned_frames.append(ImageTk.PhotoImage(bg.convert("RGB")))
            self.tk_frames[action] = cleaned_frames

    def _build_context_menu(self):
        self.menu = tk.Menu(self.win, tearoff=0, bg="#F7E2B8", fg="#3A1E08", activebackground="#D98A2B", activeforeground="white")
        self.menu.add_command(label=f"🌾 {self.record.config.name}", state="disabled")
        self.menu.add_separator()
        self.menu.add_command(
            label="💬 Abrir Caixa de Diálogo (Interagir)",
            command=self.open_dialogue_box,
        )
        self.menu.add_separator()

        actions_menu = tk.Menu(self.menu, tearoff=0, bg="#F7E2B8", fg="#3A1E08")
        for act_key, act_label in ANIMATION_LABELS.items():
            actions_menu.add_command(
                label=act_label,
                command=lambda k=act_key: self.set_action(k, duration_ticks=65),
            )
        self.menu.add_cascade(label="🎬 Executar Ação Agora", menu=actions_menu)

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
        self.canvas_w = CELL_W * self.scale
        self.canvas_h = CELL_H * self.scale + 28
        self.canvas.config(width=self.canvas_w, height=self.canvas_h)
        self.canvas.coords(
            self.sprite_item,
            self.canvas_w // 2,
            self.canvas_h - (CELL_H * self.scale) // 2,
        )
        wl, wt, wr, wb = get_work_area()
        self.max_x = max(wl + 100, wr - self.canvas_w - 10)
        self.ground_y = max(wt + 50, wb - self.canvas_h + 4)
        if self.gravity_enabled:
            self.y = float(self.ground_y)
        self._update_geometry()

    def toggle_gravity(self):
        self.gravity_enabled = not self.gravity_enabled
        mode_txt = "Gravidade Ativada!" if self.gravity_enabled else "Modo Livre!"
        self.show_speech(mode_txt, duration=30)

    def show_speech(self, text: str, duration: int = 40):
        self.speech_text = text
        self.speech_timer = duration
        self.canvas.itemconfigure(self.speech_text_item, text=text[:26], state="normal")
        self.canvas.coords(self.speech_bg_item, 2, 2, self.canvas_w - 2, 22)
        self.canvas.coords(self.speech_text_item, self.canvas_w // 2, 12)
        self.canvas.itemconfigure(self.speech_bg_item, state="normal")

    def say_random_quote(self):
        if is_gpt_luna_enabled():
            quote = get_gpt_luna_desktop_bubble(self.record.config.name, self.current_action)
        else:
            quote = random.choice(STARDEW_QUOTES)
        self.show_speech(quote, duration=55)

    def set_action(self, action: str, duration_ticks: int = 45):
        if action in self.tk_frames:
            self.current_action = action
            self.frame_idx = 0
            self.ticks_in_state = 0
            self.state_duration_ticks = duration_ticks

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
                self.show_speech(get_gpt_luna_desktop_bubble(self.record.config.name, chosen), duration=38)
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
        )

    def _show_context_menu(self, event):
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

        frames = self.tk_frames.get(self.current_action, self.tk_frames["idle"])
        self.frame_idx = (self.frame_idx + 1) % len(frames)
        self.canvas.itemconfigure(self.sprite_item, image=frames[self.frame_idx])

        # Atualizar timer do balão de fala
        if self.speech_timer > 0:
            self.speech_timer -= 1
            if self.speech_timer == 0:
                self.canvas.itemconfigure(self.speech_bg_item, state="hidden")
                self.canvas.itemconfigure(self.speech_text_item, state="hidden")

        # Contagem de estado para próxima ação aleatória
        if not self.is_dragging:
            self.ticks_in_state += 1
            if self.ticks_in_state >= self.state_duration_ticks:
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
