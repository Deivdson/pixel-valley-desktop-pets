"""
Stardew Valley Desktop Pets — Importador de Folhas de Sprites 4x6 (Gemini IA),
Editor em Camadas Originais, Biblioteca de Avatares e Motor de Área de Trabalho.
"""

import os
import sys
import glob
import json
import random
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from typing import Dict, Optional, List
from PIL import Image, ImageTk

from photo_analyzer import (
    AvatarConfig,
    analyze_person_photo,
    STARDEW_SKIN_PALETTE,
    STARDEW_HAIR_PALETTE,
    HAIR_STYLE_TO_SDV_INDEX,
)
from sprite_generator import (
    generate_full_spritesheet,
    generate_modular_portrait,
    extract_animation_frames,
    ANIMATION_LABELS,
)
from spritesheet_importer import build_animations_from_4x6_image
from library_manager import AvatarLibrary, AvatarRecord
from desktop_pet import DesktopPetWindow
from dialogue_box import StardewDialogueWindow


BG_WOOD_DARK = "#5A2E14"
BG_WOOD_MED = "#8C4A20"
BG_PARCHMENT = "#F7E2B8"
BG_CARD = "#FFF3D6"
TEXT_DARK = "#3A1E08"
BTN_GREEN = "#3E8E4C"
BTN_ORANGE = "#D9822B"
BTN_BLUE = "#3B659C"
BTN_PURPLE = "#6C3B8C"
BTN_RED = "#B83B2A"

GEMINI_4X6_PROMPT_TEMPLATE = (
    "Crie uma sprite sheet em pixel art no estilo exato do jogo Stardew Valley "
    "baseada na pessoa da foto enviada, organizada em uma grade de 4 linhas por 6 colunas "
    "(24 poses de corpo inteiro) sobre um fundo sólido uniforme verde-escuro (#3E5652). "
    "Mantenha exatamente as características reais da pessoa (cabelo, rosto, acessórios e roupa). "
    "Linha 1: 3 poses de frente (parado e caminhando) e 3 poses 3/4 direita. "
    "Linha 2: 6 poses de costas caminhando. "
    "Linha 3: 2 poses perfil esquerdo e 4 poses caminhando para a direita. "
    "Linha 4: 3 poses caminhando para a esquerda e 3 poses caminhando para a direita."
)

GEMINI_DIALOGUE_PORTRAIT_PROMPT = (
    "Crie um retrato de busto em pixel art no estilo exato das caixas de diálogo do jogo Stardew Valley "
    "(proporção quadrada 1:1) baseado na pessoa da foto enviada (ou no sprite enviado). "
    "Mantenha fielmente todas as características da pessoa: formato e cor do cabelo/cachos, tom de pele, "
    "expressão amigável, barba/bigode, óculos, acessórios e a mesma roupa/camisa. "
    "Coloque o personagem centralizado do peito/ombros para cima, sobre um fundo de pergaminho bege suave "
    "envelhecido (#D8AE76) cercado por uma moldura clássica de madeira esculpida marrom-alaranjada nos 4 cantos, "
    "com contornos escuros quentes e sombreamento autêntico de pixel art 16-bit."
)


class StardewDesktopPetApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🌾 Pixel Valley Desktop Pets — Animador de Sprites 4x6 & Biblioteca (Fan Project)")
        self.root.geometry("1220x810")
        self.root.minsize(1080, 730)
        self.root.configure(bg=BG_WOOD_DARK)

        self.library = AvatarLibrary()
        self.library.regenerate_all_sprites()

        self.active_pets: Dict[str, DesktopPetWindow] = {}
        self.gravity_var = tk.BooleanVar(value=True)

        self.editing_avatar_id: Optional[str] = None
        self.current_source_photo_path: Optional[str] = None
        self.current_photo_portrait: Optional[Image.Image] = None
        self.current_dialog_portrait: Optional[Image.Image] = None
        self.current_freeform_sheet: Optional[Image.Image] = None
        self.current_config = AvatarConfig(name="Novo Fazendeiro")
        self.render_mode_var = tk.StringVar(value="freeform")
        self.standalone_dialogues: Dict[str, StardewDialogueWindow] = {}

        self.preview_action_key = "idle"
        self.preview_frame_idx = 0
        self.preview_frames_tk: List[ImageTk.PhotoImage] = []
        self.portrait_tk: Optional[ImageTk.PhotoImage] = None
        self.sheet_preview_tk: Optional[ImageTk.PhotoImage] = None
        self.card_images_refs: List[ImageTk.PhotoImage] = []

        self._build_ui()
        self._sync_vars_from_config()
        self._refresh_live_preview()
        self._refresh_library_grid()
        self._animate_editor_preview()

    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG_WOOD_MED, bd=3, relief="ridge", padx=14, pady=8)
        header.pack(fill="x", padx=10, pady=(10, 6))

        title_lbl = tk.Label(
            header,
            text="🌾 Pixel Valley Desktop Pets — Animador 4x6 & Biblioteca (Projeto de Fã Independente)",
            font=("Segoe UI", 14, "bold"),
            bg=BG_WOOD_MED,
            fg="#FFF6E0",
        )
        title_lbl.pack(side="left")

        global_ctrl = tk.Frame(header, bg=BG_WOOD_MED)
        global_ctrl.pack(side="right")

        grav_chk = tk.Checkbutton(
            global_ctrl,
            text="🧲 Gravidade na Barra de Tarefas",
            variable=self.gravity_var,
            command=self._on_toggle_global_gravity,
            bg=BG_WOOD_MED,
            fg="#FFF6E0",
            selectcolor=BG_WOOD_DARK,
            activebackground=BG_WOOD_MED,
            activeforeground="#FFF6E0",
            font=("Segoe UI", 10, "bold"),
        )
        grav_chk.pack(side="left", padx=10)

        tk.Button(
            global_ctrl,
            text="🌟 Soltar Todos na Área de Trabalho",
            command=self.spawn_all_avatars,
            bg=BTN_GREEN,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="raised",
            padx=10,
            pady=4,
            cursor="hand2",
        ).pack(side="left", padx=4)

        tk.Button(
            global_ctrl,
            text="🏠 Recolher Todos",
            command=self.despawn_all_avatars,
            bg=BTN_RED,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="raised",
            padx=10,
            pady=4,
            cursor="hand2",
        ).pack(side="left", padx=4)

        tk.Button(
            global_ctrl,
            text="🔄 Atualizar Programa",
            command=self.update_and_reload_program,
            bg=BTN_BLUE,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="raised",
            padx=10,
            pady=4,
            cursor="hand2",
        ).pack(side="left", padx=4)

        tk.Button(
            global_ctrl,
            text="📖 Guia & Prompts Gemini",
            command=self.open_gemini_guide_window,
            bg=BTN_PURPLE,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="raised",
            padx=10,
            pady=4,
            cursor="hand2",
        ).pack(side="left", padx=4)

        main_body = tk.Frame(self.root, bg=BG_WOOD_DARK)
        main_body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        main_body.columnconfigure(0, weight=5)
        main_body.columnconfigure(1, weight=6)
        main_body.rowconfigure(0, weight=1)

        self._build_converter_panel(main_body)
        self._build_library_panel(main_body)

    def _build_converter_panel(self, parent: tk.Frame):
        panel = tk.Frame(parent, bg=BG_PARCHMENT, bd=4, relief="ridge", padx=12, pady=10)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        top_bar = tk.Frame(panel, bg=BG_PARCHMENT)
        top_bar.pack(fill="x", pady=(0, 6))

        tk.Label(
            top_bar,
            text="✨ Importador de Sprites 4x6 (IA) & Customizador",
            font=("Segoe UI", 11, "bold"),
            bg=BG_PARCHMENT,
            fg=TEXT_DARK,
        ).pack(side="left")

        tk.Button(
            top_bar,
            text="📖 Guia & Prompts Gemini",
            command=self.open_gemini_guide_window,
            bg=BTN_PURPLE,
            fg="white",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            cursor="hand2",
        ).pack(side="right", padx=(4, 0))

        tk.Button(
            top_bar,
            text="🎲 Sortear",
            command=self.randomize_avatar,
            bg="#D9822B",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            padx=6,
            cursor="hand2",
        ).pack(side="right", padx=(4, 0))

        tk.Button(
            top_bar,
            text="➕ Novo",
            command=self.reset_new_avatar,
            bg="#C99E67",
            fg=TEXT_DARK,
            font=("Segoe UI", 8, "bold"),
            padx=6,
            cursor="hand2",
        ).pack(side="right")

        # Botão Principal: Importar Imagem de Sprites 4x6 gerada por IA (ex: Gemini)
        import_4x6_btn = tk.Button(
            panel,
            text="🖼️ Importar Imagem de Sprites 4x6 (ex: Gemini_Generated_Image) & Gerar Animações",
            command=self.import_4x6_spritesheet_image,
            bg=BTN_ORANGE,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            pady=7,
            relief="raised",
            cursor="hand2",
        )
        import_4x6_btn.pack(fill="x", pady=(0, 6))

        # Seletor de Grade + Modo
        mode_row = tk.Frame(panel, bg="#EFE0B9", bd=1, relief="groove", padx=8, pady=4)
        mode_row.pack(fill="x", pady=(0, 8))

        tk.Label(mode_row, text="Grade da Imagem:", font=("Segoe UI", 8, "bold"), bg="#EFE0B9", fg=TEXT_DARK).pack(side="left")
        self.grid_layout_var = tk.StringVar(value="4x6 (24 sprites - Padrão Gemini)")
        ttk.Combobox(
            mode_row,
            textvariable=self.grid_layout_var,
            values=[
                "4x6 (24 sprites - Padrão Gemini)",
                "4x4 (16 sprites)",
                "3x4 (12 sprites)",
            ],
            state="readonly",
            width=26,
        ).pack(side="left", padx=6)

        tk.Button(
            mode_row,
            text="📷 Ou Analisar Foto Comum",
            command=self.load_photo_and_convert,
            bg="#8C583A",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            cursor="hand2",
        ).pack(side="right")

        preview_box = tk.Frame(panel, bg=BG_CARD, bd=2, relief="groove", padx=10, pady=6)
        preview_box.pack(fill="x", pady=(0, 8))

        # Coluna 1: Sprite Animado
        anim_col = tk.Frame(preview_box, bg=BG_CARD)
        anim_col.pack(side="left", padx=8)
        tk.Label(anim_col, text="Sprite Animado", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_DARK).pack()
        self.preview_canvas = tk.Canvas(anim_col, width=120, height=150, bg="#CFE8F7", bd=2, relief="sunken", highlightthickness=0)
        self.preview_canvas.pack(pady=4)
        self.preview_canvas.create_rectangle(0, 120, 125, 155, fill="#73B95F", outline="#4E8A3D")
        self.preview_sprite_item = self.preview_canvas.create_image(60, 76, image=None)

        self.preview_action_var = tk.StringVar(value="Parado / Respirando")
        action_cb = ttk.Combobox(
            anim_col,
            textvariable=self.preview_action_var,
            values=list(ANIMATION_LABELS.values()),
            state="readonly",
            width=19,
        )
        action_cb.pack(pady=2)
        action_cb.bind("<<ComboboxSelected>>", self._on_change_preview_action)

        # Coluna 2: Retrato Caixa de Diálogo Pixel Art
        port_col = tk.Frame(preview_box, bg=BG_CARD)
        port_col.pack(side="left", padx=12)
        tk.Label(port_col, text="Retrato Caixa de Diálogo", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_DARK).pack()
        self.portrait_label = tk.Label(port_col, bg=BG_CARD, bd=2, relief="sunken", cursor="hand2")
        self.portrait_label.pack(pady=4)
        self.portrait_label.bind("<Button-1>", lambda e: self.import_dialog_portrait_for_current())
        self.photo_status_lbl = tk.Label(
            port_col,
            text="Retrato Stardew",
            font=("Segoe UI", 8),
            bg=BG_CARD,
            fg="#6E4720",
        )
        self.photo_status_lbl.pack()
        tk.Button(
            port_col,
            text="🖼️ Importar Caixa de Diálogo",
            command=self.import_dialog_portrait_for_current,
            bg="#C97A2B",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            padx=6,
            pady=1,
            cursor="hand2",
        ).pack(pady=(2, 0))

        # Coluna 3: Folha de Sprites Completa (8x4)
        sheet_col = tk.Frame(preview_box, bg=BG_CARD)
        sheet_col.pack(side="left", padx=8, expand=True)
        tk.Label(sheet_col, text="Sprite Sheet (8x4)", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_DARK).pack()
        self.sheet_label = tk.Label(sheet_col, bg="#E8D8B8", bd=1, relief="solid")
        self.sheet_label.pack(pady=4)

        # Formulário de Ajustes
        form = tk.Frame(panel, bg=BG_PARCHMENT)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        self.name_var = tk.StringVar()
        self.gender_var = tk.StringVar(value="Masculino")
        self.hair_style_var = tk.StringVar()
        self.hair_idx_var = tk.IntVar(value=0)
        self.shirt_idx_var = tk.IntVar(value=0)
        self.skin_idx_var = tk.IntVar(value=0)
        self.beard_style_var = tk.StringVar()
        self.glasses_style_var = tk.StringVar()
        self.outfit_style_var = tk.StringVar()
        self.hat_style_var = tk.StringVar()
        self.scale_var = tk.IntVar(value=4)

        self.skin_color_var = tk.StringVar()
        self.hair_color_var = tk.StringVar()
        self.eye_color_var = tk.StringVar()
        self.shirt_color_var = tk.StringVar()
        self.pants_color_var = tk.StringVar()

        tk.Label(form, text="Nome:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=0, column=0, sticky="w", pady=2)
        name_entry = tk.Entry(form, textvariable=self.name_var, font=("Segoe UI", 10), bg="#FFFDF7")
        name_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        name_entry.bind("<KeyRelease>", lambda e: self._on_name_or_scale_change())

        tk.Label(form, text="Corpo Base:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=0, column=2, sticky="w", padx=(8, 0), pady=2)
        gender_cb = ttk.Combobox(form, textvariable=self.gender_var, values=["Masculino", "Feminino"], state="readonly")
        gender_cb.grid(row=0, column=3, sticky="ew", padx=4, pady=2)
        gender_cb.bind("<<ComboboxSelected>>", lambda e: self._on_modular_layer_change())

        tk.Label(form, text="Cabelo:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=1, column=0, sticky="w", pady=2)
        hair_cb = ttk.Combobox(
            form,
            textvariable=self.hair_style_var,
            values=["curto", "topete", "medio", "longo", "cacheado", "coque", "careca", "custom"],
            state="readonly",
        )
        hair_cb.grid(row=1, column=1, sticky="ew", padx=4, pady=2)
        hair_cb.bind("<<ComboboxSelected>>", self._on_hair_preset_selected)

        tk.Label(form, text="Cabelo ID (0-72):", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=1, column=2, sticky="w", padx=(8, 0), pady=2)
        hair_spin = tk.Spinbox(form, from_=0, to=72, textvariable=self.hair_idx_var, command=self._on_hair_spin_changed, font=("Segoe UI", 9))
        hair_spin.grid(row=1, column=3, sticky="ew", padx=4, pady=2)
        hair_spin.bind("<Return>", lambda e: self._on_hair_spin_changed())

        tk.Label(form, text="Barba:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=2, column=0, sticky="w", pady=2)
        beard_cb = ttk.Combobox(
            form,
            textvariable=self.beard_style_var,
            values=["sem_barba", "bigode", "cavanhaque", "barba_cheia"],
            state="readonly",
        )
        beard_cb.grid(row=2, column=1, sticky="ew", padx=4, pady=2)
        beard_cb.bind("<<ComboboxSelected>>", lambda e: self._on_modular_layer_change())

        tk.Label(form, text="Óculos:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=2, column=2, sticky="w", padx=(8, 0), pady=2)
        glasses_cb = ttk.Combobox(
            form,
            textvariable=self.glasses_style_var,
            values=["nenhum", "redondo", "quadrado", "escuro"],
            state="readonly",
        )
        glasses_cb.grid(row=2, column=3, sticky="ew", padx=4, pady=2)
        glasses_cb.bind("<<ComboboxSelected>>", lambda e: self._on_modular_layer_change())

        tk.Label(form, text="Estilo Roupa:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=3, column=0, sticky="w", pady=2)
        outfit_cb = ttk.Combobox(
            form,
            textvariable=self.outfit_style_var,
            values=["jardineira", "camiseta", "moletom", "xadrez", "jaqueta"],
            state="readonly",
        )
        outfit_cb.grid(row=3, column=1, sticky="ew", padx=4, pady=2)
        outfit_cb.bind("<<ComboboxSelected>>", self._on_outfit_preset_selected)

        tk.Label(form, text="Camisa ID (0-111):", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=3, column=2, sticky="w", padx=(8, 0), pady=2)
        shirt_spin = tk.Spinbox(form, from_=0, to=111, textvariable=self.shirt_idx_var, command=lambda: self._on_modular_layer_change(), font=("Segoe UI", 9))
        shirt_spin.grid(row=3, column=3, sticky="ew", padx=4, pady=2)
        shirt_spin.bind("<Return>", lambda e: self._on_modular_layer_change())

        tk.Label(form, text="Chapéu:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=4, column=0, sticky="w", pady=2)
        hat_cb = ttk.Combobox(
            form,
            textvariable=self.hat_style_var,
            values=["nenhum", "palha", "bone", "flor"],
            state="readonly",
        )
        hat_cb.grid(row=4, column=1, sticky="ew", padx=4, pady=2)
        hat_cb.bind("<<ComboboxSelected>>", lambda e: self._on_modular_layer_change())

        tk.Label(form, text="Tamanho:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=4, column=2, sticky="w", padx=(8, 0), pady=2)
        scale_cb = ttk.Combobox(form, textvariable=self.scale_var, values=[3, 4, 5, 6], state="readonly")
        scale_cb.grid(row=4, column=3, sticky="ew", padx=4, pady=2)
        scale_cb.bind("<<ComboboxSelected>>", lambda e: self._on_name_or_scale_change())

        tk.Label(form, text="Tom Pele:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=5, column=0, sticky="w", pady=2)
        self.skin_btn = tk.Button(form, text="Tom de Pele", command=lambda: self._pick_color(self.skin_color_var), font=("Segoe UI", 8, "bold"))
        self.skin_btn.grid(row=5, column=1, sticky="ew", padx=4, pady=2)

        tk.Label(form, text="Cor Cabelo:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=5, column=2, sticky="w", padx=(8, 0), pady=2)
        self.hair_btn = tk.Button(form, text="Cor do Cabelo", command=lambda: self._pick_color(self.hair_color_var), font=("Segoe UI", 8, "bold"))
        self.hair_btn.grid(row=5, column=3, sticky="ew", padx=4, pady=2)

        tk.Label(form, text="Cor Camisa:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=6, column=0, sticky="w", pady=2)
        self.shirt_btn = tk.Button(form, text="Cor da Camisa", command=lambda: self._pick_color(self.shirt_color_var), font=("Segoe UI", 8, "bold"))
        self.shirt_btn.grid(row=6, column=1, sticky="ew", padx=4, pady=2)

        tk.Label(form, text="Cor Calça:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=6, column=2, sticky="w", padx=(8, 0), pady=2)
        self.pants_btn = tk.Button(form, text="Cor da Calça", command=lambda: self._pick_color(self.pants_color_var), font=("Segoe UI", 8, "bold"))
        self.pants_btn.grid(row=6, column=3, sticky="ew", padx=4, pady=2)

        swatch_frame = tk.Frame(panel, bg=BG_PARCHMENT, pady=3)
        swatch_frame.pack(fill="x")
        tk.Label(swatch_frame, text="🎨 Paleta (Pele / Cabelo):", font=("Segoe UI", 8, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).pack(side="left", padx=(0, 4))
        for idx_s, (hex_val, _) in enumerate(STARDEW_SKIN_PALETTE):
            b = tk.Button(
                swatch_frame,
                bg=hex_val,
                width=2,
                height=1,
                relief="groove",
                command=lambda hv=hex_val, si=idx_s: self._set_quick_skin(si, hv),
            )
            b.pack(side="left", padx=1)
        tk.Label(swatch_frame, text="|", bg=BG_PARCHMENT, fg=TEXT_DARK).pack(side="left", padx=3)
        for hex_val, _ in STARDEW_HAIR_PALETTE[:8]:
            b = tk.Button(
                swatch_frame,
                bg=hex_val,
                width=2,
                height=1,
                relief="groove",
                command=lambda hv=hex_val: self._set_quick_color(self.hair_color_var, hv),
            )
            b.pack(side="left", padx=1)

        btn_row = tk.Frame(panel, bg=BG_PARCHMENT, pady=5)
        btn_row.pack(fill="x", side="bottom")

        tk.Button(
            btn_row,
            text="💾 Salvar na Biblioteca & Soltar na Área de Trabalho",
            command=self.save_and_spawn_current,
            bg=BTN_GREEN,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            pady=7,
            cursor="hand2",
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        tk.Button(
            btn_row,
            text="📤 Exportar Sprite Sheet (.PNG)",
            command=self.export_current_spritesheet,
            bg=BTN_BLUE,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            pady=7,
            padx=10,
            cursor="hand2",
        ).pack(side="right")

    def _build_library_panel(self, parent: tk.Frame):
        panel = tk.Frame(parent, bg=BG_PARCHMENT, bd=4, relief="ridge", padx=12, pady=10)
        panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        top_bar = tk.Frame(panel, bg=BG_PARCHMENT)
        top_bar.pack(fill="x", pady=(0, 8))

        tk.Label(
            top_bar,
            text="📚 Biblioteca de Pessoas / Avatares Stardew Valley",
            font=("Segoe UI", 13, "bold"),
            bg=BG_PARCHMENT,
            fg=TEXT_DARK,
        ).pack(side="left")

        self.count_lbl = tk.Label(
            top_bar,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg=BG_PARCHMENT,
            fg="#6E4720",
        )
        self.count_lbl.pack(side="right")

        tip_lbl = tk.Label(
            panel,
            text="💡 Dica: Nos bonequinhos na área de trabalho, dê DUPLO CLIQUE ou clique em '💬 Interagir / Diálogo' para abrir a Caixa de Diálogo estilo Stardew Valley!",
            font=("Segoe UI", 8, "italic"),
            bg="#EFE0B9",
            fg=TEXT_DARK,
            anchor="w",
            padx=6,
            pady=4,
            relief="groove",
        )
        tip_lbl.pack(fill="x", pady=(0, 8))

        scroll_container = tk.Frame(panel, bg=BG_PARCHMENT)
        scroll_container.pack(fill="both", expand=True)

        self.lib_canvas = tk.Canvas(scroll_container, bg=BG_PARCHMENT, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=self.lib_canvas.yview)
        self.lib_inner = tk.Frame(self.lib_canvas, bg=BG_PARCHMENT)

        self.lib_inner.bind(
            "<Configure>",
            lambda e: self.lib_canvas.configure(scrollregion=self.lib_canvas.bbox("all")),
        )
        self.lib_window_id = self.lib_canvas.create_window((0, 0), window=self.lib_inner, anchor="nw")
        self.lib_canvas.bind(
            "<Configure>",
            lambda e: self.lib_canvas.itemconfigure(self.lib_window_id, width=e.width),
        )
        self.lib_canvas.configure(yscrollcommand=scrollbar.set)

        self.lib_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def copy_gemini_4x6_prompt(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(GEMINI_4X6_PROMPT_TEMPLATE)
        messagebox.showinfo(
            "Prompt 4x6 Copiado! 📋",
            "O prompt para gerar folhas de sprites 4x6 no Gemini foi copiado para a sua área de transferência!\n\n"
            f"Prompt:\n\"{GEMINI_4X6_PROMPT_TEMPLATE}\"\n\n"
            "Basta enviar a foto da pessoa no Gemini com esse prompt, baixar a imagem gerada e clicar em '🖼️ Importar Imagem de Sprites 4x6'!",
        )

    def copy_gemini_dialogue_prompt(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(GEMINI_DIALOGUE_PORTRAIT_PROMPT)
        messagebox.showinfo(
            "Prompt da Caixa de Diálogo Copiado! 📋",
            "O prompt para gerar o Retrato da Caixa de Diálogo no Gemini foi copiado para a sua área de transferência!\n\n"
            f"Prompt:\n\"{GEMINI_DIALOGUE_PORTRAIT_PROMPT}\"\n\n"
            "Envie a foto da pessoa (ou a própria sprite sheet já gerada) no Gemini com esse prompt, baixe a imagem quadrada e clique em '🖼️ Importar Caixa de Diálogo'!",
        )

    def open_gemini_guide_window(self):
        """
        Abre uma janela estilo Pergaminho do Stardew Valley com o Guia Passo a Passo completo
        para criar (1) a Folha de Sprites 4x6 e (2) o Quadro de Retrato da Caixa de Diálogo no Gemini,
        com botões de copiar os dois prompts e abrir o Gemini no navegador.
        """
        import webbrowser

        win = tk.Toplevel(self.root)
        win.title("📖 Guia de Criação de Skins e Caixas de Diálogo no Gemini IA")
        win.geometry("820x690")
        win.configure(bg=BG_WOOD_DARK)
        win.wm_attributes("-topmost", True)

        outer = tk.Frame(win, bg=BG_WOOD_MED, bd=4, relief="ridge", padx=12, pady=10)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        hdr = tk.Frame(outer, bg=BG_WOOD_MED)
        hdr.pack(fill="x", pady=(0, 8))

        tk.Label(
            hdr,
            text="📖 Guia Passo a Passo: Como Criar Skins 4x6 e Retratos de Diálogo no Gemini",
            font=("Segoe UI", 13, "bold"),
            bg=BG_WOOD_MED,
            fg="#FFF6E0",
        ).pack(side="left")

        tk.Button(
            hdr,
            text="🌐 Abrir Google Gemini",
            command=lambda: webbrowser.open("https://gemini.google.com/"),
            bg=BTN_GREEN,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=3,
            cursor="hand2",
        ).pack(side="right")

        body = tk.Frame(outer, bg=BG_PARCHMENT, bd=3, relief="sunken", padx=14, pady=10)
        body.pack(fill="both", expand=True)

        # ==================== CASO 1: FOLHA DE SPRITES 4x6 ====================
        sec1 = tk.LabelFrame(
            body,
            text=" 🏃‍♂️ CASO 1: Criar a Folha de Sprites Animada (Grade 4x6 com 24 Poses) ",
            font=("Segoe UI", 10, "bold"),
            bg=BG_CARD,
            fg=TEXT_DARK,
            padx=10,
            pady=8,
        )
        sec1.pack(fill="x", pady=(0, 10))

        steps1 = (
            "1. Acesse o Google Gemini (gemini.google.com) e anexe uma foto nítida da pessoa (rosto e roupa visíveis).\n"
            "2. Clique no botão roxo abaixo para copiar o Prompt de Sprites 4x6 e cole junto com a foto no Gemini.\n"
            "3. Baixe a imagem gerada (grade 4 linhas x 6 colunas) para a sua pasta Downloads.\n"
            "4. Aqui no programa, clique no botão laranja '🖼️ Importar Imagem de Sprites 4x6' e selecione a imagem:\n"
            "   o sistema removerá o fundo automaticamente e criará todas as 8 animações (andar p/ esquerda, direita, café, pesca, etc.)!"
        )
        tk.Label(
            sec1,
            text=steps1,
            font=("Segoe UI", 9),
            bg=BG_CARD,
            fg=TEXT_DARK,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        p1_txt = tk.Text(sec1, height=4, font=("Consolas", 9), bg="#FFFDF8", fg="#2B1506", wrap="word", bd=2, relief="sunken")
        p1_txt.insert("1.0", GEMINI_4X6_PROMPT_TEMPLATE)
        p1_txt.configure(state="disabled")
        p1_txt.pack(fill="x", pady=(0, 6))

        btn_row1 = tk.Frame(sec1, bg=BG_CARD)
        btn_row1.pack(fill="x")
        tk.Button(
            btn_row1,
            text="📋 Copiar Prompt 1 (Folha de Sprites 4x6)",
            command=self.copy_gemini_4x6_prompt,
            bg=BTN_PURPLE,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            btn_row1,
            text="🖼️ Já gerei! Importar Folha 4x6 Agora",
            command=lambda: [win.destroy(), self.import_4x6_spritesheet_image()],
            bg=BTN_ORANGE,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            cursor="hand2",
        ).pack(side="right")

        # ==================== CASO 2: QUADRO DE RETRATO DA CAIXA DE DIÁLOGO ====================
        sec2 = tk.LabelFrame(
            body,
            text=" 💬 CASO 2: Criar o Quadro de Retrato da Caixa de Diálogo (Busto 1:1 com Moldura) ",
            font=("Segoe UI", 10, "bold"),
            bg=BG_CARD,
            fg=TEXT_DARK,
            padx=10,
            pady=8,
        )
        sec2.pack(fill="x", pady=(0, 8))

        steps2 = (
            "1. No mesmo chat do Gemini (após gerar os sprites 4x6) OU enviando a foto da pessoa + a sprite sheet gerada:\n"
            "2. Clique no botão azul abaixo para copiar o Prompt do Retrato da Caixa de Diálogo e envie no Gemini.\n"
            "   (Dica: pedir no mesmo chat faz o Gemini manter exatamente a mesma roupa, óculos, barba e penteado do sprite!).\n"
            "3. Baixe a imagem quadrada gerada com a moldura de madeira.\n"
            "4. Clique em '🖼️ Importar Caixa de Diálogo' no painel do avatar (ou dentro da própria janela de conversa)!"
        )
        tk.Label(
            sec2,
            text=steps2,
            font=("Segoe UI", 9),
            bg=BG_CARD,
            fg=TEXT_DARK,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        p2_txt = tk.Text(sec2, height=4, font=("Consolas", 9), bg="#FFFDF8", fg="#2B1506", wrap="word", bd=2, relief="sunken")
        p2_txt.insert("1.0", GEMINI_DIALOGUE_PORTRAIT_PROMPT)
        p2_txt.configure(state="disabled")
        p2_txt.pack(fill="x", pady=(0, 6))

        btn_row2 = tk.Frame(sec2, bg=BG_CARD)
        btn_row2.pack(fill="x")
        tk.Button(
            btn_row2,
            text="📋 Copiar Prompt 2 (Retrato da Caixa de Diálogo)",
            command=self.copy_gemini_dialogue_prompt,
            bg=BTN_BLUE,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            btn_row2,
            text="🖼️ Já gerei! Importar Retrato de Diálogo Agora",
            command=lambda: [win.destroy(), self.import_dialog_portrait_for_current()],
            bg=BTN_GREEN,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            cursor="hand2",
        ).pack(side="right")

        tk.Button(
            outer,
            text="✖ Fechar Guia",
            command=win.destroy,
            bg=BTN_RED,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=16,
            pady=4,
            cursor="hand2",
        ).pack( pady=(8, 0))

    def _get_selected_grid_dims(self):
        val = self.grid_layout_var.get()
        if "4x4" in val:
            return (4, 4)
        if "3x4" in val:
            return (3, 4)
        return (4, 6)

    def import_4x6_spritesheet_image(self):
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        initial_dir = downloads_dir if os.path.exists(downloads_dir) else os.path.expanduser("~")
        file_path = filedialog.askopenfilename(
            title="Selecione a Imagem de Sprites 4x6 (ex: Gemini_Generated_Image)",
            initialdir=initial_dir,
            filetypes=[
                ("Imagens", "*.jpg *.jpeg *.png *.webp *.bmp"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not file_path:
            return
        try:
            g_rows, g_cols = self._get_selected_grid_dims()
            full_sheet, portrait, stats = build_animations_from_4x6_image(
                file_path,
                grid_rows=g_rows,
                grid_cols=g_cols,
            )
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            if "Gemini_Generated_Image" in base_name:
                base_name = "Avatar Gemini " + base_name.split("_")[-1][:4]
            else:
                base_name = base_name.replace("_", " ").replace("-", " ").title()[:22]

            self.editing_avatar_id = None
            self.current_source_photo_path = file_path
            self.current_photo_portrait = portrait
            self.current_freeform_sheet = full_sheet
            self.render_mode_var.set("freeform")
            self.current_config = AvatarConfig(name=base_name, is_male=False, scale=4)
            self._sync_vars_from_config()
            self._refresh_live_preview()

            messagebox.showinfo(
                "Sprites 4x6 Importados e Animados! 🎉",
                f"A folha '{os.path.basename(file_path)}' ({g_rows}x{g_cols}) foi recortada, "
                "teve o fundo removido e gerou todas as 8 animações!\n\n"
                f"• Quadros Frontais detectados: {stats['front_count']}\n"
                f"• Quadros Direita detectados: {stats['right_count']}\n"
                f"• Quadros Esquerda detectados: {stats['left_count']}\n"
                f"• Quadros Costas detectados: {stats['back_count']}\n\n"
                "Clique em '💾 Salvar na Biblioteca & Soltar na Área de Trabalho' para ver o bonequinho andando!",
            )
        except Exception as exc:
            messagebox.showerror("Erro ao Importar Folha 4x6", f"Não foi possível processar a folha de sprites:\n{exc}")

    def _on_name_or_scale_change(self):
        self._sync_config_from_vars()
        self._refresh_live_preview()

    def _on_modular_layer_change(self):
        self.render_mode_var.set("vanilla_layers")
        self.current_freeform_sheet = None
        self.current_photo_portrait = None
        self._sync_config_from_vars()
        self._update_color_buttons()
        self._refresh_live_preview()

    def _on_hair_preset_selected(self, event=None):
        st = self.hair_style_var.get()
        if st in HAIR_STYLE_TO_SDV_INDEX:
            self.hair_idx_var.set(HAIR_STYLE_TO_SDV_INDEX[st])
        self._on_modular_layer_change()

    def _on_hair_spin_changed(self):
        self.hair_style_var.set("custom")
        self._on_modular_layer_change()

    def _on_outfit_preset_selected(self, event=None):
        outfit_defaults = {
            "jardineira": 0,
            "camiseta": 13,
            "xadrez": 12,
            "moletom": 21,
            "jaqueta": 18,
        }
        st = self.outfit_style_var.get()
        if st in outfit_defaults:
            self.shirt_idx_var.set(outfit_defaults[st])
        self._on_modular_layer_change()

    def randomize_avatar(self):
        self.render_mode_var.set("vanilla_layers")
        self.current_freeform_sheet = None
        self.current_photo_portrait = None
        self.gender_var.set(random.choice(["Masculino", "Feminino"]))
        self.hair_style_var.set("custom")
        self.hair_idx_var.set(random.randint(0, 55))
        self.shirt_idx_var.set(random.randint(0, 60))
        skin_idx = random.randint(0, len(STARDEW_SKIN_PALETTE) - 1)
        self.skin_idx_var.set(skin_idx)
        self.skin_color_var.set(STARDEW_SKIN_PALETTE[skin_idx][0])
        self.hair_color_var.set(random.choice(STARDEW_HAIR_PALETTE)[0])
        self.shirt_color_var.set(random.choice(["#C43B3B", "#3B659C", "#3E8E4C", "#D98A2B", "#76428A", "#4CA6A6"]))
        self.pants_color_var.set(random.choice(["#3B659C", "#2E2E38", "#8C583A", "#3E8E4C"]))
        self.beard_style_var.set(random.choice(["sem_barba", "sem_barba", "bigode", "barba_cheia"]) if self.gender_var.get() == "Masculino" else "sem_barba")
        self.glasses_style_var.set(random.choice(["nenhum", "nenhum", "redondo", "quadrado", "escuro"]))
        self.hat_style_var.set(random.choice(["nenhum", "nenhum", "palha", "bone", "flor"]))
        self._on_modular_layer_change()

    def _sync_vars_from_config(self):
        cfg = self.current_config
        self.name_var.set(cfg.name)
        self.gender_var.set("Masculino" if cfg.is_male else "Feminino")
        self.hair_style_var.set(cfg.hair_style)
        self.hair_idx_var.set(cfg.hair_index)
        self.shirt_idx_var.set(cfg.shirt_index)
        self.skin_idx_var.set(cfg.skin_index)
        self.beard_style_var.set(cfg.beard_style)
        self.glasses_style_var.set(cfg.glasses_style)
        self.outfit_style_var.set(cfg.outfit_style)
        self.hat_style_var.set(cfg.hat_style)
        self.scale_var.set(cfg.scale)

        self.skin_color_var.set(cfg.skin_color)
        self.hair_color_var.set(cfg.hair_color)
        self.eye_color_var.set(cfg.eye_color)
        self.shirt_color_var.set(cfg.shirt_color)
        self.pants_color_var.set(cfg.pants_color)
        self._update_color_buttons()

    def _sync_config_from_vars(self):
        try:
            h_idx = int(self.hair_idx_var.get())
        except Exception:
            h_idx = 0
        try:
            s_idx = int(self.shirt_idx_var.get())
        except Exception:
            s_idx = 0
        try:
            sk_idx = int(self.skin_idx_var.get())
        except Exception:
            sk_idx = 0

        self.current_config = AvatarConfig(
            name=self.name_var.get().strip() or "Aldeão Stardew",
            is_male=(self.gender_var.get() == "Masculino"),
            skin_index=sk_idx,
            skin_color=self.skin_color_var.get(),
            hair_index=h_idx,
            hair_color=self.hair_color_var.get(),
            hair_style=self.hair_style_var.get(),
            eye_color=self.eye_color_var.get(),
            beard_style=self.beard_style_var.get(),
            glasses_style=self.glasses_style_var.get(),
            shirt_index=s_idx,
            outfit_style=self.outfit_style_var.get(),
            shirt_color=self.shirt_color_var.get(),
            pants_color=self.pants_color_var.get(),
            hat_style=self.hat_style_var.get(),
            scale=int(self.scale_var.get() or 4),
        )

    def _update_color_buttons(self):
        for btn, var in [
            (self.skin_btn, self.skin_color_var),
            (self.hair_btn, self.hair_color_var),
            (self.shirt_btn, self.shirt_color_var),
            (self.pants_btn, self.pants_color_var),
        ]:
            hex_c = var.get()
            btn.configure(bg=hex_c, text=hex_c, fg="#FFFFFF" if self._is_dark(hex_c) else "#221100")

    @staticmethod
    def _is_dark(hex_color: str) -> bool:
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return False
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (0.299 * r + 0.587 * g + 0.114 * b) < 135

    def _set_quick_skin(self, skin_idx: int, hex_val: str):
        self.skin_idx_var.set(skin_idx)
        self.skin_color_var.set(hex_val)
        self._on_modular_layer_change()

    def _set_quick_color(self, var: tk.StringVar, hex_val: str):
        var.set(hex_val)
        self._on_modular_layer_change()

    def _pick_color(self, var: tk.StringVar):
        _, hex_val = colorchooser.askcolor(color=var.get(), title="Escolher Cor Stardew Valley")
        if hex_val:
            var.set(hex_val.upper())
            self._on_modular_layer_change()

    def _on_change_preview_action(self, event=None):
        selected_label = self.preview_action_var.get()
        for k, v in ANIMATION_LABELS.items():
            if v == selected_label:
                self.preview_action_key = k
                break
        self._refresh_live_preview()

    def _get_active_preview_sheet(self) -> Image.Image:
        if self.render_mode_var.get() == "freeform" and self.current_freeform_sheet is not None:
            return self.current_freeform_sheet
        return generate_full_spritesheet(self.current_config)

    def _refresh_live_preview(self):
        sheet = self._get_active_preview_sheet()
        pil_frames = extract_animation_frames(sheet, self.preview_action_key, scale=4)
        self.preview_frames_tk = [ImageTk.PhotoImage(f) for f in pil_frames]

        if self.current_dialog_portrait is not None:
            port_img = self.current_dialog_portrait.resize((96, 96), Image.Resampling.NEAREST)
            self.photo_status_lbl.configure(text="💬 Caixa de Diálogo HD")
        elif self.current_photo_portrait is not None:
            port_img = self.current_photo_portrait.resize((96, 96), Image.Resampling.NEAREST)
            self.photo_status_lbl.configure(text="🖼️ Retrato do Sprite 4x6")
        else:
            port_img = generate_modular_portrait(self.current_config).resize((96, 96), Image.Resampling.NEAREST)
            self.photo_status_lbl.configure(text="🎨 Retrato Stardew")
        self.portrait_tk = ImageTk.PhotoImage(port_img)
        self.portrait_label.configure(image=self.portrait_tk)

        sheet_thumb = sheet.resize((48, 144), Image.Resampling.NEAREST)
        self.sheet_preview_tk = ImageTk.PhotoImage(sheet_thumb)
        self.sheet_label.configure(image=self.sheet_preview_tk)

    def import_dialog_portrait_for_current(self):
        """Importa uma imagem de caixa de diálogo (ex: 'caixa dialogo deivdson.jpg') para o avatar atual no editor."""
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        initial_dir = downloads_dir if os.path.exists(downloads_dir) else os.path.expanduser("~")
        file_path = filedialog.askopenfilename(
            title="Selecione a Imagem da Caixa de Diálogo (ex: caixa dialogo deivdson.jpg)",
            initialdir=initial_dir,
            filetypes=[
                ("Imagens", "*.jpg *.jpeg *.png *.webp *.bmp"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not file_path:
            return
        try:
            img = Image.open(file_path).convert("RGBA")
            w, h = img.size
            if w != h:
                side = min(w, h)
                img = img.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
            self.current_dialog_portrait = img.resize((256, 256), Image.Resampling.NEAREST)
            self.current_photo_portrait = self.current_dialog_portrait.resize((64, 64), Image.Resampling.NEAREST)

            if self.editing_avatar_id:
                for rec in self.library.list_avatars():
                    if rec.avatar_id == self.editing_avatar_id:
                        rec.set_dialog_portrait_from_file(file_path)
                        if rec.avatar_id in self.active_pets:
                            self.active_pets[rec.avatar_id].reload_from_record(rec)
                        break
                self._refresh_library_grid()

            self._refresh_live_preview()
        except Exception as exc:
            messagebox.showerror("Erro ao Importar Retrato", f"Não foi possível carregar a imagem:\n{exc}")

    def _animate_editor_preview(self):
        if self.preview_frames_tk:
            self.preview_frame_idx = (self.preview_frame_idx + 1) % len(self.preview_frames_tk)
            self.preview_canvas.itemconfigure(
                self.preview_sprite_item,
                image=self.preview_frames_tk[self.preview_frame_idx],
            )
        self.root.after(200, self._animate_editor_preview)

    def reset_new_avatar(self):
        self.editing_avatar_id = None
        self.current_source_photo_path = None
        self.current_photo_portrait = None
        self.current_dialog_portrait = None
        self.current_freeform_sheet = None
        self.render_mode_var.set("vanilla_layers")
        self.current_config = AvatarConfig(name="Novo Fazendeiro")
        self._sync_vars_from_config()
        self._refresh_live_preview()

    def load_photo_and_convert(self):
        file_path = filedialog.askopenfilename(
            title="Selecione a Foto de uma Pessoa",
            filetypes=[
                ("Imagens", "*.jpg *.jpeg *.png *.webp *.bmp"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not file_path:
            return
        try:
            cfg, portrait_img = analyze_person_photo(file_path)
            self.editing_avatar_id = None
            self.current_source_photo_path = file_path
            self.current_photo_portrait = portrait_img
            self.current_freeform_sheet = None
            self.render_mode_var.set("vanilla_layers")
            self.current_config = cfg
            self._sync_vars_from_config()
            self._refresh_live_preview()
            messagebox.showinfo(
                "Foto Analisada! 🌾",
                f"Características extraídas de '{os.path.basename(file_path)}' e aplicadas às camadas do Stardew Valley.\n\n"
                "Dica: Para avatares personalizados idênticos à pessoa, use o botão '🖼️ Importar Imagem de Sprites 4x6'!",
            )
        except Exception as exc:
            messagebox.showerror("Erro ao Analisar Foto", f"Não foi possível processar a imagem:\n{exc}")

    def save_and_spawn_current(self):
        self._sync_config_from_vars()
        custom_sheet = self.current_freeform_sheet if self.render_mode_var.get() == "freeform" else None
        record = self.library.save_avatar(
            config=self.current_config,
            photo_portrait=self.current_photo_portrait,
            source_photo_path=self.current_source_photo_path,
            avatar_id=self.editing_avatar_id,
            custom_spritesheet=custom_sheet,
            dialog_portrait=self.current_dialog_portrait,
        )
        self.editing_avatar_id = record.avatar_id
        self.spawn_avatar(record)
        self._refresh_library_grid()

    def export_current_spritesheet(self):
        self._sync_config_from_vars()
        default_name = f"{self.current_config.name.lower().replace(' ', '_')}_spritesheet.png"
        save_path = filedialog.asksaveasfilename(
            title="Exportar Sprite Sheet em Pixel Art (.PNG)",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG Image", "*.png")],
        )
        if not save_path:
            return
        sheet = self._get_active_preview_sheet()
        sheet.save(save_path)
        messagebox.showinfo("Exportado!", f"Sprite Sheet salva em:\n{save_path}")

    def spawn_avatar(self, record: AvatarRecord):
        if record.avatar_id in self.active_pets:
            self.active_pets[record.avatar_id].reload_from_record(record)
            self.active_pets[record.avatar_id].show_speech("Visual atualizado! ✨", duration=35)
            return

        pet = DesktopPetWindow(
            master=self.root,
            record=record,
            on_close_callback=self._on_pet_closed,
            gravity_enabled=self.gravity_var.get(),
        )
        pet.on_portrait_updated_callback = lambda rec: self._refresh_library_grid()
        pet.on_open_guide_callback = self.open_gemini_guide_window
        pet._build_context_menu()
        self.active_pets[record.avatar_id] = pet
        self._refresh_library_grid()

    def open_dialogue_for_record(self, record: AvatarRecord):
        """Abre a Caixa de Diálogo interativa para o personagem (e o solta na área de trabalho se ainda não estiver)."""
        if record.avatar_id not in self.active_pets:
            self.spawn_avatar(record)
        pet = self.active_pets.get(record.avatar_id)
        if pet:
            pet.open_dialogue_box()

    def despawn_avatar(self, avatar_id: str):
        pet = self.active_pets.pop(avatar_id, None)
        if pet:
            pet.close()
        self._refresh_library_grid()

    def _on_pet_closed(self, avatar_id: str):
        self.active_pets.pop(avatar_id, None)
        self._refresh_library_grid()

    def spawn_all_avatars(self):
        for rec in self.library.list_avatars():
            self.spawn_avatar(rec)

    def despawn_all_avatars(self):
        for aid in list(self.active_pets.keys()):
            self.despawn_avatar(aid)

    def update_and_reload_program(self):
        """
        Atualiza o programa automaticamente:
        1. Sincroniza com o repositório Git (se houver remote configurado);
        2. Regenera as folhas de sprites (incluindo os avatares 4x6 a partir de source.*) e recarrega todos os pets ativos;
        3. Permite reiniciar o processo Python automaticamente com 1 clique para aplicar alterações de código.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        git_msg = "Repositório Git local sincronizado."
        try:
            rem = subprocess.run(
                ["git", "remote"],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if rem.returncode == 0 and rem.stdout.strip():
                pull = subprocess.run(
                    ["git", "pull", "--rebase", "--autostash"],
                    cwd=base_dir,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                git_msg = (pull.stdout or pull.stderr or "Git pull concluído.").strip()
            else:
                st = subprocess.run(
                    ["git", "log", "-1", "--oneline"],
                    cwd=base_dir,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if st.returncode == 0 and st.stdout.strip():
                    git_msg = f"Versão Git atual: {st.stdout.strip()}"
        except Exception as exc:
            git_msg = f"Verificação Git local: {exc}"

        # Regenerar todos os sprites de camadas e também reprocessar os 4x6 que possuam source.*
        self.library.regenerate_all_sprites()
        rebuilt_count = 0
        for rec in self.library.list_avatars():
            if rec.is_freeform_sprite:
                sources = glob.glob(os.path.join(rec.folder_path, "source.*"))
                if sources:
                    try:
                        full_sheet, _, _ = build_animations_from_4x6_image(sources[0], 4, 6)
                        full_sheet.save(rec.spritesheet_path)
                        rebuilt_count += 1
                    except Exception:
                        pass

        # Atualizar em tempo real os pets abertos na área de trabalho
        updated_records = {r.avatar_id: r for r in self.library.list_avatars()}
        for aid, pet in list(self.active_pets.items()):
            if aid in updated_records:
                pet.reload_from_record(updated_records[aid])
                pet.show_speech("Programa Atualizado! 🔄", duration=40)

        if self.editing_avatar_id and self.editing_avatar_id in updated_records:
            self.edit_avatar_from_library(updated_records[self.editing_avatar_id])
        else:
            self._refresh_live_preview()
        self._refresh_library_grid()

        restart = messagebox.askyesno(
            "Programa e Sprites Atualizados! 🔄",
            f"{git_msg}\n\n"
            f"• {rebuilt_count} folhas de sprites 4x6 reprocessadas com sucesso!\n"
            f"• {len(self.active_pets)} pets ativos na tela recarregados!\n\n"
            "Deseja reiniciar a janela do programa agora para recarregar todos os módulos Python?",
        )
        if restart:
            self._restart_application()

    def _restart_application(self):
        try:
            for aid in list(self.active_pets.keys()):
                self.despawn_avatar(aid)
            script_path = os.path.abspath(__file__)
            subprocess.Popen([sys.executable, script_path], cwd=os.path.dirname(script_path))
            self.root.destroy()
        except Exception as exc:
            messagebox.showerror("Erro ao Reiniciar", f"Não foi possível reiniciar automaticamente:\n{exc}")

    def _on_toggle_global_gravity(self):
        g = self.gravity_var.get()
        for pet in self.active_pets.values():
            pet.gravity_enabled = g

    def edit_avatar_from_library(self, record: AvatarRecord):
        self.editing_avatar_id = record.avatar_id
        self.current_config = record.config
        self.current_source_photo_path = None
        if record.is_freeform_sprite and os.path.exists(record.spritesheet_path):
            self.current_freeform_sheet = Image.open(record.spritesheet_path).convert("RGBA")
            self.render_mode_var.set("freeform")
        else:
            self.current_freeform_sheet = None
            self.render_mode_var.set("vanilla_layers")

        if os.path.exists(record.dialog_portrait_path):
            self.current_dialog_portrait = Image.open(record.dialog_portrait_path).convert("RGBA")
        else:
            self.current_dialog_portrait = None

        if record.has_photo_portrait and os.path.exists(record.photo_portrait_path):
            self.current_photo_portrait = Image.open(record.photo_portrait_path).convert("RGBA")
        else:
            self.current_photo_portrait = None
        self._sync_vars_from_config()
        self._refresh_live_preview()

    def delete_avatar_from_library(self, record: AvatarRecord):
        if not messagebox.askyesno("Excluir Avatar", f"Deseja excluir '{record.config.name}' da biblioteca?"):
            return
        self.despawn_avatar(record.avatar_id)
        self.library.delete_avatar(record.avatar_id)
        if self.editing_avatar_id == record.avatar_id:
            self.reset_new_avatar()
        self._refresh_library_grid()

    def _refresh_library_grid(self):
        for child in self.lib_inner.winfo_children():
            child.destroy()
        self.card_images_refs.clear()

        records = self.library.list_avatars()
        active_count = len(self.active_pets)
        self.count_lbl.configure(text=f"{len(records)} avatares | {active_count} ativos na tela")

        for rec in records:
            is_active = rec.avatar_id in self.active_pets
            card_bg = "#E6F7DF" if is_active else BG_CARD
            border_c = BTN_GREEN if is_active else "#C99E67"

            card = tk.Frame(
                self.lib_inner,
                bg=card_bg,
                bd=2,
                relief="raised" if is_active else "groove",
                padx=10,
                pady=8,
                highlightbackground=border_c,
                highlightthickness=2,
            )
            card.pack(fill="x", padx=6, pady=5)

            port_img = rec.load_portrait().resize((64, 64), Image.Resampling.NEAREST)
            port_tk = ImageTk.PhotoImage(port_img)
            self.card_images_refs.append(port_tk)
            tk.Label(card, image=port_tk, bg=card_bg).pack(side="left", padx=(0, 8))

            sheet_img = rec.load_spritesheet()
            idle_frame = extract_animation_frames(sheet_img, "idle", scale=2)[0]
            idle_tk = ImageTk.PhotoImage(idle_frame)
            self.card_images_refs.append(idle_tk)
            tk.Label(card, image=idle_tk, bg=card_bg).pack(side="left", padx=(0, 10))

            info = tk.Frame(card, bg=card_bg)
            info.pack(side="left", fill="both", expand=True)

            status_badge = "🟢 Ativo na Área de Trabalho" if is_active else "⚪ Na Biblioteca"
            mode_badge = "🖼️ Sprite 4x6 IA" if rec.is_freeform_sprite else "🧩 Camadas Stardew"
            tk.Label(
                info,
                text=f"{rec.config.name}   [{mode_badge}]   ({status_badge})",
                font=("Segoe UI", 10, "bold"),
                bg=card_bg,
                fg=TEXT_DARK,
                anchor="w",
            ).pack(fill="x")

            details_txt = (
                "Importado de Folha de Sprites 4x6 (8 Animações Ativas)"
                if rec.is_freeform_sprite
                else f"Cabelo #{rec.config.hair_index} | Camisa #{rec.config.shirt_index} | Barba: {rec.config.beard_style}"
            )
            tk.Label(
                info,
                text=details_txt,
                font=("Segoe UI", 8),
                bg=card_bg,
                fg="#5E3B18",
                anchor="w",
            ).pack(fill="x", pady=(2, 6))

            btns = tk.Frame(info, bg=card_bg)
            btns.pack(fill="x")

            if is_active:
                tk.Button(
                    btns,
                    text="🏠 Recolher",
                    command=lambda r=rec: self.despawn_avatar(r.avatar_id),
                    bg=BTN_ORANGE,
                    fg="white",
                    font=("Segoe UI", 9, "bold"),
                    padx=8,
                    cursor="hand2",
                ).pack(side="left", padx=(0, 6))
            else:
                tk.Button(
                    btns,
                    text="🚀 Soltar na Área de Trabalho",
                    command=lambda r=rec: self.spawn_avatar(r),
                    bg=BTN_GREEN,
                    fg="white",
                    font=("Segoe UI", 9, "bold"),
                    padx=8,
                    cursor="hand2",
                ).pack(side="left", padx=(0, 6))

            tk.Button(
                btns,
                text="💬 Interagir / Diálogo",
                command=lambda r=rec: self.open_dialogue_for_record(r),
                bg=BTN_PURPLE,
                fg="white",
                font=("Segoe UI", 9, "bold"),
                padx=8,
                cursor="hand2",
            ).pack(side="left", padx=(0, 6))

            tk.Button(
                btns,
                text="✏️ Editar / Visualizar",
                command=lambda r=rec: self.edit_avatar_from_library(r),
                bg=BTN_BLUE,
                fg="white",
                font=("Segoe UI", 9, "bold"),
                padx=8,
                cursor="hand2",
            ).pack(side="left", padx=(0, 6))

            tk.Button(
                btns,
                text="🗑️ Excluir",
                command=lambda r=rec: self.delete_avatar_from_library(r),
                bg=BTN_RED,
                fg="white",
                font=("Segoe UI", 9),
                padx=6,
                cursor="hand2",
            ).pack(side="left")


def main():
    root = tk.Tk()
    app = StardewDesktopPetApp(root)
    avatars = app.library.list_avatars()
    if avatars:
        # Priorizar o avatar do Deivdson caso exista para já testar a caixa de diálogo!
        deivdson_rec = next((a for a in avatars if "deivdson" in a.config.name.lower()), None)
        target_rec = deivdson_rec or avatars[0]
        app.edit_avatar_from_library(target_rec)
        app.spawn_avatar(target_rec)
    root.mainloop()


if __name__ == "__main__":
    main()
