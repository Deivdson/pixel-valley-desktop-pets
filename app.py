"""
Stardew Valley Desktop Pets — Conversor de Foto com Geração Livre por IA/LLM,
Editor em Camadas Originais, Biblioteca de Avatares e Motor de Área de Trabalho.
"""

import os
import json
import random
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
from llm_sprite_designer import (
    load_llm_settings,
    save_llm_settings,
    get_copyable_llm_prompt,
    parse_llm_matrix_json,
    call_llm_vision_for_sprite,
    sculpt_freeform_sprite_from_photo,
    animate_freeform_frames_to_spritesheet,
)
from library_manager import AvatarLibrary, AvatarRecord
from desktop_pet import DesktopPetWindow


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


class StardewDesktopPetApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🌾 Stardew Valley Desktop Pets — Gerador Livre por IA & Biblioteca de Avatares")
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
        self.current_freeform_sheet: Optional[Image.Image] = None
        self.current_config = AvatarConfig(name="Novo Fazendeiro")
        self.render_mode_var = tk.StringVar(value="freeform")  # "freeform" ou "vanilla_layers"

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
            text="🌾 Stardew Valley Desktop Pets — Geração Livre por IA/Foto & Biblioteca",
            font=("Segoe UI", 15, "bold"),
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
            text="✨ Criador de Sprite por Foto (Livre IA) & Customizador",
            font=("Segoe UI", 11, "bold"),
            bg=BG_PARCHMENT,
            fg=TEXT_DARK,
        ).pack(side="left")

        tk.Button(
            top_bar,
            text="🤖 Configurar LLM / Matriz IA",
            command=self.open_llm_dialog,
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

        # Botão Principal: Carregar Foto com Geração Livre IA / Escultor Pixel-a-Pixel
        photo_btn = tk.Button(
            panel,
            text="📷 Carregar Foto de Pessoa (Desenhar Sprite 16x32 Livre Sem Depender de Peças Prontas)",
            command=self.load_photo_and_convert,
            bg=BTN_ORANGE,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            pady=7,
            relief="raised",
            cursor="hand2",
        )
        photo_btn.pack(fill="x", pady=(0, 6))

        # Seletor de Modo de Renderização (Livre da Foto/LLM vs. Camadas Existentes do Jogo)
        mode_row = tk.Frame(panel, bg="#EFE0B9", bd=1, relief="groove", padx=8, pady=4)
        mode_row.pack(fill="x", pady=(0, 8))
        tk.Label(mode_row, text="Modo do Sprite:", font=("Segoe UI", 9, "bold"), bg="#EFE0B9", fg=TEXT_DARK).pack(side="left")
        tk.Radiobutton(
            mode_row,
            text="🎨 Criação Livre da Foto / LLM (Fiel à Pessoa)",
            variable=self.render_mode_var,
            value="freeform",
            command=self._on_switch_render_mode,
            bg="#EFE0B9",
            fg=TEXT_DARK,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=8)
        tk.Radiobutton(
            mode_row,
            text="🧩 Peças Pré-Existentes do Jogo",
            variable=self.render_mode_var,
            value="vanilla_layers",
            command=self._on_switch_render_mode,
            bg="#EFE0B9",
            fg=TEXT_DARK,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=4)

        preview_box = tk.Frame(panel, bg=BG_CARD, bd=2, relief="groove", padx=10, pady=6)
        preview_box.pack(fill="x", pady=(0, 8))

        # Coluna 1: Sprite Animado
        anim_col = tk.Frame(preview_box, bg=BG_CARD)
        anim_col.pack(side="left", padx=8)
        tk.Label(anim_col, text="Sprite Stardew (16x32)", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_DARK).pack()
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

        # Coluna 2: Retrato 64x64 Pixel Art
        port_col = tk.Frame(preview_box, bg=BG_CARD)
        port_col.pack(side="left", padx=12)
        tk.Label(port_col, text="Retrato Diálogo (64x64)", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_DARK).pack()
        self.portrait_label = tk.Label(port_col, bg=BG_CARD, bd=2, relief="sunken")
        self.portrait_label.pack(pady=6)
        self.photo_status_lbl = tk.Label(
            port_col,
            text="Retrato Oficial",
            font=("Segoe UI", 8),
            bg=BG_CARD,
            fg="#6E4720",
        )
        self.photo_status_lbl.pack()

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
        name_entry.bind("<KeyRelease>", lambda e: self._on_form_change())

        tk.Label(form, text="Corpo Base:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=0, column=2, sticky="w", padx=(8, 0), pady=2)
        gender_cb = ttk.Combobox(form, textvariable=self.gender_var, values=["Masculino", "Feminino"], state="readonly")
        gender_cb.grid(row=0, column=3, sticky="ew", padx=4, pady=2)
        gender_cb.bind("<<ComboboxSelected>>", lambda e: self._on_form_change())

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
        beard_cb.bind("<<ComboboxSelected>>", lambda e: self._on_form_change())

        tk.Label(form, text="Óculos:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=2, column=2, sticky="w", padx=(8, 0), pady=2)
        glasses_cb = ttk.Combobox(
            form,
            textvariable=self.glasses_style_var,
            values=["nenhum", "redondo", "quadrado", "escuro"],
            state="readonly",
        )
        glasses_cb.grid(row=2, column=3, sticky="ew", padx=4, pady=2)
        glasses_cb.bind("<<ComboboxSelected>>", lambda e: self._on_form_change())

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
        shirt_spin = tk.Spinbox(form, from_=0, to=111, textvariable=self.shirt_idx_var, command=lambda: self._on_form_change(), font=("Segoe UI", 9))
        shirt_spin.grid(row=3, column=3, sticky="ew", padx=4, pady=2)
        shirt_spin.bind("<Return>", lambda e: self._on_form_change())

        tk.Label(form, text="Chapéu:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=4, column=0, sticky="w", pady=2)
        hat_cb = ttk.Combobox(
            form,
            textvariable=self.hat_style_var,
            values=["nenhum", "palha", "bone", "flor"],
            state="readonly",
        )
        hat_cb.grid(row=4, column=1, sticky="ew", padx=4, pady=2)
        hat_cb.bind("<<ComboboxSelected>>", lambda e: self._on_form_change())

        tk.Label(form, text="Tamanho:", font=("Segoe UI", 9, "bold"), bg=BG_PARCHMENT, fg=TEXT_DARK).grid(row=4, column=2, sticky="w", padx=(8, 0), pady=2)
        scale_cb = ttk.Combobox(form, textvariable=self.scale_var, values=[3, 4, 5, 6], state="readonly")
        scale_cb.grid(row=4, column=3, sticky="ew", padx=4, pady=2)
        scale_cb.bind("<<ComboboxSelected>>", lambda e: self._on_form_change())

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
            text="💡 Dica: Nos bonequinhos na área de trabalho, arraste com o botão esquerdo, dê duplo clique para fazer carinho ❤️ ou clique com o botão direito para escolher ações!",
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

    def open_llm_dialog(self):
        """Janela para configurar a API de Visão (Gemini / OpenAI / Ollama) ou colar JSON gerado por qualquer LLM."""
        dlg = tk.Toplevel(self.root)
        dlg.title("🤖 Configuração da LLM Vision & Importador de Matriz 16x32 Livre")
        dlg.geometry("680x580")
        dlg.configure(bg=BG_PARCHMENT)
        dlg.transient(self.root)

        settings = load_llm_settings()

        f_top = tk.LabelFrame(dlg, text="1. Provedor de IA para Desenho Livre de Fotos", bg=BG_PARCHMENT, fg=TEXT_DARK, font=("Segoe UI", 10, "bold"), padx=10, pady=8)
        f_top.pack(fill="x", padx=12, pady=8)

        prov_var = tk.StringVar(value=settings.get("provider", "auto"))
        key_var = tk.StringVar(value=settings.get("api_key", ""))
        model_var = tk.StringVar(value=settings.get("model", "gemini-2.5-flash"))
        notes_var = tk.StringVar(value=settings.get("custom_prompt_notes", ""))

        tk.Label(f_top, text="Motor:", bg=BG_PARCHMENT, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Combobox(
            f_top,
            textvariable=prov_var,
            values=["auto", "gemini", "openai", "ollama", "sculptor_offline"],
            state="readonly",
            width=25,
        ).grid(row=0, column=1, sticky="w", padx=6, pady=2)

        tk.Label(f_top, text="Modelo:", bg=BG_PARCHMENT, font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=6, pady=2)
        tk.Entry(f_top, textvariable=model_var, width=22).grid(row=0, column=3, sticky="ew", pady=2)

        tk.Label(f_top, text="API Key (Gemini/OpenAI):", bg=BG_PARCHMENT, font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        tk.Entry(f_top, textvariable=key_var, show="*", width=48).grid(row=1, column=1, columnspan=3, sticky="ew", padx=6, pady=2)

        tk.Label(f_top, text="Instrução Extra p/ IA:", bg=BG_PARCHMENT, font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        tk.Entry(f_top, textvariable=notes_var, width=48).grid(row=2, column=1, columnspan=3, sticky="ew", padx=6, pady=2)

        def _save_cfg():
            settings["provider"] = prov_var.get()
            settings["api_key"] = key_var.get().strip()
            settings["model"] = model_var.get().strip()
            settings["custom_prompt_notes"] = notes_var.get().strip()
            save_llm_settings(settings)
            messagebox.showinfo("Salvo!", "Configurações de LLM salvas com sucesso!", parent=dlg)

        tk.Button(f_top, text="💾 Salvar Configuração de API", command=_save_cfg, bg=BTN_GREEN, fg="white", font=("Segoe UI", 9, "bold"), padx=10).grid(row=3, column=1, columnspan=3, sticky="e", pady=(6, 0))

        # Parte 2: Copiar Prompt / Colar Matriz 16x32 JSON de qualquer LLM
        f_bot = tk.LabelFrame(dlg, text="2. Usar Qualquer Chat IA (Copiar Prompt + Colar JSON 16x32 da LLM)", bg=BG_PARCHMENT, fg=TEXT_DARK, font=("Segoe UI", 10, "bold"), padx=10, pady=8)
        f_bot.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        def _copy_prompt():
            self.root.clipboard_clear()
            self.root.clipboard_append(get_copyable_llm_prompt())
            messagebox.showinfo(
                "Prompt Copiado! 📋",
                "O Prompt de Pixel Art 16x32 Stardew Valley foi copiado para a sua área de transferência!\n\n"
                "Envie a foto da pessoa junto com esse prompt em qualquer LLM (ou aqui no nosso chat) e cole o JSON gerado abaixo!",
                parent=dlg,
            )

        tk.Button(
            f_bot,
            text="📋 Copiar Prompt Stardew 16x32 para enviar junto com a Foto em qualquer LLM",
            command=_copy_prompt,
            bg=BTN_ORANGE,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            pady=5,
        ).pack(fill="x", pady=(0, 6))

        tk.Label(f_bot, text="Cole abaixo o JSON retornado pela LLM (contendo palette, front_16x32 e side_16x32):", bg=BG_PARCHMENT, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        json_txt = tk.Text(f_bot, height=12, font=("Consolas", 9), bg="#FFFDF7")
        json_txt.pack(fill="both", expand=True, pady=4)

        def _apply_pasted_json():
            raw = json_txt.get("1.0", "end").strip()
            if not raw:
                return
            try:
                # Limpar cercas markdown ```json se houver
                if "```" in raw:
                    parts = raw.split("```")
                    for p in parts:
                        if "{" in p and "front_16x32" in p:
                            raw = p.lstrip("json").strip()
                            break
                data = json.loads(raw)
                res = parse_llm_matrix_json(data)
                if not res:
                    raise ValueError("JSON não contém 'front_16x32' válido com 24-32 linhas.")
                front_img, side_img = res
                if data.get("name"):
                    self.name_var.set(data["name"])
                self._sync_config_from_vars()
                self.current_freeform_sheet = animate_freeform_frames_to_spritesheet(front_img, side_img, self.current_config)
                self.render_mode_var.set("freeform")
                self._refresh_live_preview()
                dlg.destroy()
                messagebox.showinfo("Sprite Livre Aplicado! 🎨", "A matriz 16x32 gerada pela LLM foi convertida em todas as 8 animações com sucesso!")
            except Exception as exc:
                messagebox.showerror("Erro no JSON", f"Não foi possível ler a matriz JSON:\n{exc}", parent=dlg)

        tk.Button(
            f_bot,
            text="✨ Gerar Todas as Animações a partir do JSON Colado",
            command=_apply_pasted_json,
            bg=BTN_PURPLE,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            pady=6,
        ).pack(fill="x", pady=(4, 0))

    def _on_switch_render_mode(self):
        if self.render_mode_var.get() == "freeform" and self.current_freeform_sheet is None and self.current_source_photo_path:
            front_img, side_img = sculpt_freeform_sprite_from_photo(self.current_source_photo_path, self.current_config)
            self.current_freeform_sheet = animate_freeform_frames_to_spritesheet(front_img, side_img, self.current_config)
        self._refresh_live_preview()

    def _on_hair_preset_selected(self, event=None):
        st = self.hair_style_var.get()
        if st in HAIR_STYLE_TO_SDV_INDEX:
            self.hair_idx_var.set(HAIR_STYLE_TO_SDV_INDEX[st])
        self._on_form_change()

    def _on_hair_spin_changed(self):
        self.hair_style_var.set("custom")
        self.render_mode_var.set("vanilla_layers")
        self._on_form_change()

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
        self._on_form_change()

    def randomize_avatar(self):
        self.render_mode_var.set("vanilla_layers")
        self.current_freeform_sheet = None
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
        self._on_form_change()

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
        self._on_form_change()

    def _set_quick_color(self, var: tk.StringVar, hex_val: str):
        var.set(hex_val)
        self._on_form_change()

    def _pick_color(self, var: tk.StringVar):
        _, hex_val = colorchooser.askcolor(color=var.get(), title="Escolher Cor Stardew Valley")
        if hex_val:
            var.set(hex_val.upper())
            self._on_form_change()

    def _on_form_change(self):
        self._sync_config_from_vars()
        self._update_color_buttons()
        # Se houver foto de origem carregada e estiver no modo livre, re-esculpir com os novos ajustes de cor/barba/óculos
        if self.render_mode_var.get() == "freeform" and self.current_source_photo_path and os.path.exists(self.current_source_photo_path):
            front_img, side_img = sculpt_freeform_sprite_from_photo(self.current_source_photo_path, self.current_config)
            self.current_freeform_sheet = animate_freeform_frames_to_spritesheet(front_img, side_img, self.current_config)
        self._refresh_live_preview()

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

        if self.current_photo_portrait is not None:
            port_img = self.current_photo_portrait.resize((96, 96), Image.Resampling.NEAREST)
            self.photo_status_lbl.configure(text="📷 Retrato Pixel da Foto")
        else:
            bust = sheet.crop((4, 2, 20, 20)).resize((56, 56), Image.Resampling.NEAREST)
            mod_port = generate_modular_portrait(self.current_config)
            mod_port.paste(bust, (4, 4), bust)
            port_img = mod_port.resize((96, 96), Image.Resampling.NEAREST)
            self.photo_status_lbl.configure(text="🎨 Retrato Stardew")
        self.portrait_tk = ImageTk.PhotoImage(port_img)
        self.portrait_label.configure(image=self.portrait_tk)

        sheet_thumb = sheet.resize((48, 144), Image.Resampling.NEAREST)
        self.sheet_preview_tk = ImageTk.PhotoImage(sheet_thumb)
        self.sheet_label.configure(image=self.sheet_preview_tk)

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
            self.current_config = cfg
            self.render_mode_var.set("freeform")

            # 1. Tentar geração via LLM Vision API se houver chave/servidor configurado
            llm_result = None
            engine_used = "Escultor Livre Pixel-a-Pixel da Silhueta da Foto"
            try:
                llm_result = call_llm_vision_for_sprite(file_path)
            except Exception:
                llm_result = None

            if llm_result is not None:
                front_16x32, side_16x32, desc = llm_result
                engine_used = f"LLM Vision ({desc})"
            else:
                # 2. Esculpir livremente pixel-a-pixel direto da silhueta real da foto (sem depender de elementos prontos!)
                front_16x32, side_16x32 = sculpt_freeform_sprite_from_photo(file_path, cfg)

            self.current_freeform_sheet = animate_freeform_frames_to_spritesheet(front_16x32, side_16x32, cfg)
            self._sync_vars_from_config()
            self._refresh_live_preview()

            messagebox.showinfo(
                "Sprite Livre Criado a partir da Foto! 🎨🌾",
                f"O bonequinho 16x32 de '{os.path.basename(file_path)}' foi desenhado livremente "
                f"(sem ficar preso aos cabelos/roupas pré-existentes do jogo)!\n\n"
                f"• Motor utilizado: {engine_used}\n"
                f"• Contorno real do cabelo, rosto e roupa esculpidos no padrão Stardew Valley\n\n"
                "Dica: Você pode alternar entre '🎨 Criação Livre da Foto / LLM' e '🧩 Peças Pré-Existentes do Jogo' "
                "a qualquer momento, ou clicar em '🤖 Configurar LLM / Matriz IA'!",
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
        self.active_pets[record.avatar_id] = pet
        self._refresh_library_grid()

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
            mode_badge = "🎨 Livre IA/Foto" if rec.is_freeform_sprite else "🧩 Camadas Stardew"
            tk.Label(
                info,
                text=f"{rec.config.name}   [{mode_badge}]   ({status_badge})",
                font=("Segoe UI", 10, "bold"),
                bg=card_bg,
                fg=TEXT_DARK,
                anchor="w",
            ).pack(fill="x")

            details_txt = (
                f"Pele: {rec.config.skin_color} | Cabelo: {rec.config.hair_color} | "
                f"Barba: {rec.config.beard_style} | Óculos: {rec.config.glasses_style}"
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
                text="✏️ Editar",
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
        app.spawn_avatar(avatars[0])
    root.mainloop()


if __name__ == "__main__":
    main()
