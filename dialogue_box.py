"""
Sistema de Caixa de Diálogo Interativa Estilo Stardew Valley.
Permite conversar, dar presentes, acompanhar amizade (corações), escolher respostas,
conversar via IA (Gemini / Ollama / Offline) e exibir retratos de diálogo personalizados
em alta definição ou Pixel Art.
"""

import os
import json
import random
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Optional, Callable, List, Dict, Any
from PIL import Image, ImageDraw, ImageTk
import httpx

from library_manager import AvatarRecord
from llm_sprite_designer import load_llm_settings
from avatar_tasks import (
    AVAILABLE_TASKS,
    get_avatar_assigned_tasks,
    OrganizeItemsModal,
    FishLargeFilesModal,
)
from gpt_luna import (
    is_gpt_luna_enabled,
    set_gpt_luna_enabled,
    generate_gpt_luna_reply,
    _generate_local_luna_fallback,
    open_gpt_luna_settings_modal,
    load_avatar_personality,
    format_personality_summary,
    open_avatar_personality_modal,
)


# Paleta autêntica da Caixa de Diálogo do Stardew Valley
SDV_OUTER_BORDER = "#5A2B11"
SDV_MID_BORDER = "#B86F28"
SDV_INNER_BORDER = "#E5A045"
SDV_PARCHMENT = "#F7DFB3"
SDV_PARCHMENT_DARK = "#E8C68E"
SDV_PORTRAIT_BG = "#D8AE76"
SDV_TEXT_MAIN = "#3F1D0B"
SDV_TEXT_MUTED = "#70421E"
SDV_CHOICE_BG = "#EDD09A"
SDV_CHOICE_HOVER = "#DFB36B"
SDV_BTN_GREEN = "#3E8E4C"
SDV_BTN_ORANGE = "#D9822B"
SDV_BTN_BLUE = "#3B659C"


STARDEW_GIFTS = [
    {"name": "☕ Café Expresso Triplo", "points": 2, "reaction": "Uau, um Café Expresso Triplo quentinho! Era tudo o que eu precisava para programar e cuidar da fazenda hoje! Muito obrigado! ☕✨"},
    {"name": "💎 Fragmento Prismático", "points": 3, "reaction": "I-isso é um Fragmento Prismático?! Não acredito! É o presente mais incrível de todo o Vale do Orvalho! Você é demais! 💎🌈"},
    {"name": "🌻 Girassol Dourado", "points": 1, "reaction": "Que girassol lindo! Ele ilumina qualquer canto da tela. Vou colocar na minha mesa agora mesmo! 🌻💛"},
    {"name": "🍰 Bolo Rosa da Vila", "points": 2, "reaction": "Hummm! Bolo fresquinho do Saloon Fruta Estrelar! Como você sabia que é o meu favorito? 🍰❤️"},
    {"name": "🍕 Pizza do Gus", "points": 1, "reaction": "Nada supera uma fatia de pizza quentinha depois de um longo dia na mina! Valeu demais! 🍕🔥"},
    {"name": "🍓 Morango de Primavera", "points": 1, "reaction": "Morangos colhidos na hora! Docinhos e cheios de energia. Muito obrigado pelo carinho! 🍓🌱"},
]


DEFAULT_DIALOGUES_BY_TOPIC = {
    "greeting": [
        "Olá! Que bom que você veio bater um papo comigo aqui na área de trabalho! Como está sendo o seu dia?",
        "Ei! Estava justamente admirando o movimento do seu cursor. Tudo tranquilo por aí no trabalho hoje?",
        "Oi! O tempo hoje no Vale do Orvalho está perfeito para tomar um café e colocar os projetos em dia!",
        "Que alegria te ver! Se precisar de companhia enquanto usa o computador, estarei caminhando bem aqui por perto.",
    ],
    "farm_talk": [
        "Hoje cedo eu reguei todas as plantações, conferi a estufa e ainda sobrou tempo para dar uma caminhada pela sua barra de tarefas!",
        "Ouvi dizer que os Espíritos estão muito felizes hoje! É um ótimo dia para tentar projetos novos ou explorar as minas.",
        "Você já reparou como um bom Café Expresso Triplo faz a gente andar duas vezes mais rápido? Recomendo fortemente! ☕",
        "Estou planejando plantar Mirtilos e Carambolas na próxima estação. O lucro na fazenda vai ser lendário!",
    ],
    "compliment": [
        "Puxa, muito obrigado! Fico até sem jeito... Trabalhar ao seu lado aqui na tela deixa qualquer rotina mais divertida! ❤️",
        "Você sempre sabe como alegrar o meu dia! Pode contar comigo para deixar sua área de trabalho mais viva!",
        "Haha, valeu! Eu capricho no visual pixel art para fazer bonito aqui no seu computador!",
    ],
    "work_tip": [
        "Dica de fazendeiro: lembre-se de beber água, alongar os ombros e salvar seu progresso com frequência! 💧✨",
        "Um passo de cada vez! Até a maior fazenda do Stardew Valley começou limpando um pequeno pedaço de terra.",
        "Se o código ou o trabalho ficar difícil, respire fundo! Até pescar uma Carpa Lendária exige paciência e calma. 🎣",
    ],
    "joke": [
        "Por que o espantalho ganhou um prêmio na Vila Pelicanos? Porque ele era um destaque no seu campo! 🌾😄",
        "Tentei pescar no ícone da Lixeira hoje mais cedo, mas só fisguei um arquivo temporário antigo! 🎣😂",
        "Se o Prefeito Lewis perguntar, eu não vi onde foram parar aquelas bermudas roxas! 🤫🟣",
    ],
}


DEIVDSON_SPECIAL_DIALOGUES = {
    "greeting": [
        "E aí! Aqui é o Deivdson! Gostou da minha nova caixa de diálogo com retrato em pixel art, óculos, bigode e bolsa a tiracolo?",
        "Olá! Que massa conversar por essa caixa estilo Stardew Valley! Preparado para mais um dia produtivo de pesquisa e código?",
        "Opa, tudo certo? Entre uma linha de código, um artigo científico e uma colheita na fazenda, estou sempre por aqui!",
    ],
    "farm_talk": [
        "Na minha fazenda nunca faltam duas coisas: muito Café Expresso para manter o foco nos projetos e tecnologia de ponta!",
        "Essa bolsa a tiracolo está cheia de ideias, notas de pesquisa e, claro, algumas sementes de Fruta Antiga para plantar depois!",
        "Hoje os espíritos da programação estão de ótimo humor! Zero bugs e colheita abundante pela frente! ✨",
    ],
    "compliment": [
        "Valeu demais! Esse retrato com os cachos iluminados, óculos e bigode ficou no estilo clássico do ConcernedApe! 😄✨",
        "Muito obrigado! É sempre um prazer trocar uma ideia e acompanhar o seu trabalho na área de trabalho!",
    ],
}


class StardewDialogueWindow:
    """
    Janela de Caixa de Diálogo Interativa autêntica do Stardew Valley.
    Exibe o texto com efeito de máquina de escrever, o retrato do personagem à direita
    dentro da moldura clássica com nome e corações de amizade, opções de diálogo e chat livre.
    """

    def __init__(
        self,
        master: tk.Misc,
        record: AvatarRecord,
        on_action_trigger: Optional[Callable[[str, str], None]] = None,
        on_portrait_updated: Optional[Callable[[AvatarRecord], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        on_execute_task: Optional[Callable[[str], None]] = None,
        on_open_tasks_manager: Optional[Callable[[], None]] = None,
    ):
        self.master = master
        self.record = record
        self.on_action_trigger = on_action_trigger
        self.on_portrait_updated = on_portrait_updated
        self.on_close = on_close
        self.on_execute_task = on_execute_task
        self.on_open_tasks_manager = on_open_tasks_manager

        self.win = tk.Toplevel(master)
        self.win.title(f"💬 Conversando com {self.record.config.name} — Pixel Valley")
        self.win.configure(bg=SDV_OUTER_BORDER)
        self.win.wm_attributes("-topmost", True)
        self.win.resizable(False, False)

        # Dimensões estilo caixa de diálogo clássica do Stardew Valley (larga na parte inferior da tela)
        self.win_w = 960
        self.win_h = 420
        self._position_window()

        # Estado de interação, amizade, personalidade individual e efeito typewriter
        self.friendship_State_path = os.path.join(self.record.folder_path, "dialogue_state.json")
        self.personality = load_avatar_personality(
            self.record.folder_path,
            self.record.config.name,
            self.record.avatar_id,
        )
        self.state = self._load_dialogue_state()
        self.full_text = ""
        self.typed_index = 0
        self.typing_after_id: Optional[str] = None
        self.cursor_blink_after_id: Optional[str] = None
        self.cursor_blink_state = False
        self.talking_frame_toggle = False
        self.portrait_tk: Optional[ImageTk.PhotoImage] = None
        self.hearts_banner_tk: Optional[ImageTk.PhotoImage] = None
        self.is_waiting_llm = False
        self.showing_history = False
        self.current_mood_text = self.personality.get("dominant_emotion", "😊 Feliz no Vale")
        self.placeholder_text = f"Escreva uma mensagem para {self.record.config.name} e pressione Enter..."
        self.has_placeholder = False

        self._build_ui()
        self._refresh_portrait_display(talking_offset=0)
        self._refresh_hearts_display()
        self._start_continuation_cursor_anim()

        # Iniciar com saudação do personagem
        initial_msg = self._pick_dialogue("greeting")
        self.set_dialogue_text(initial_msg)

        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.bind("<Escape>", lambda e: self.close())

    def _position_window(self):
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        x = max(20, (sw - self.win_w) // 2)
        y = max(40, sh - self.win_h - 90)
        self.win.geometry(f"{self.win_w}x{self.win_h}+{x}+{y}")

    def _load_dialogue_state(self) -> Dict[str, Any]:
        default_state = {
            "hearts": 6,
            "max_hearts": 10,
            "talks_count": 0,
            "gifts_count": 0,
            "custom_lines": [],
            "persona_bio": format_personality_summary(self.personality),
            "personality": self.personality,
            "history": [],
        }
        if "deivdson" in self.record.config.name.lower():
            default_state["hearts"] = 8
        if os.path.exists(self.friendship_State_path):
            try:
                with open(self.friendship_State_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                default_state.update(saved)
            except Exception:
                pass
        if not default_state.get("persona_bio"):
            default_state["persona_bio"] = format_personality_summary(self.personality)
        return default_state

    def _save_dialogue_state(self):
        try:
            with open(self.friendship_State_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _is_deivdson(self) -> bool:
        return "deivdson" in self.record.config.name.lower()

    def _pick_dialogue(self, topic: str) -> str:
        self.personality = load_avatar_personality(
            self.record.folder_path,
            self.record.config.name,
            self.record.avatar_id,
        )
        if is_gpt_luna_enabled():
            return _generate_local_luna_fallback(
                char_name=self.record.config.name,
                hearts=int(self.state.get("hearts", 6)),
                topic=topic,
                personality=self.personality,
            )
        custom_list = self.state.get("custom_lines", [])
        if topic == "greeting" and custom_list and random.random() < 0.35:
            return random.choice(custom_list)
        if self._is_deivdson() and topic in DEIVDSON_SPECIAL_DIALOGUES:
            pool = DEIVDSON_SPECIAL_DIALOGUES[topic] + DEFAULT_DIALOGUES_BY_TOPIC.get(topic, [])
            return random.choice(pool)
        pool = DEFAULT_DIALOGUES_BY_TOPIC.get(topic, DEFAULT_DIALOGUES_BY_TOPIC["greeting"])
        return random.choice(pool)

    def open_personality_customizer_from_dialogue(self):
        """Abre o formulário de múltipla escolha para personalizar gostos e emoções deste avatar."""
        def _on_saved(rec, new_p):
            self.personality = new_p
            self.state["personality"] = new_p
            self.state["persona_bio"] = format_personality_summary(new_p)
            self._save_dialogue_state()
            self._set_mood_badge("greeting")
            likes_preview = ", ".join(new_p.get("likes", [])[:2])
            self.set_dialogue_text(
                f"🎭 [{new_p.get('dominant_emotion', '😊')}] Personalidade atualizada! "
                f"Agora meus gostos favoritos ({likes_preview}) e minhas emoções estão 100% sintonizados com você! ✨",
                trigger_action="happy_dance",
                short_bubble=f"🎭 {new_p.get('dominant_emotion', 'Personalidade Atualizada!')}",
            )

        open_avatar_personality_modal(
            parent=self.win,
            record=self.record,
            on_saved_callback=_on_saved,
        )

    def _toggle_luna_in_dialogue(self):
        new_state = not is_gpt_luna_enabled()
        set_gpt_luna_enabled(new_state)
        self._refresh_luna_badge()
        if new_state:
            msg = _generate_local_luna_fallback(
                char_name=self.record.config.name,
                hearts=int(self.state.get("hearts", 6)),
                topic="greeting",
                personality=self.personality,
            )
            self.set_dialogue_text(msg, trigger_action="happy_dance", short_bubble="🌙 GPT Luna Ativado!")
        else:
            self.set_dialogue_text(
                f"Modo clássico do Vale do Orvalho ativado! Sempre que quiser ligar a personalidade GPT Luna de novo, é só clicar no botão 🌙 acima!",
                trigger_action="idle",
                short_bubble="🌾 Modo Clássico!",
            )

    def _get_friendship_rank_title(self, hearts: int) -> str:
        if hearts >= 10:
            return "💎 Alma Gêmea do Vale"
        if hearts >= 8:
            return "🌟 Melhor Amigo(a)"
        if hearts >= 6:
            return "🌾 Grande Companheiro(a)"
        if hearts >= 4:
            return "🌻 Bom Amigo(a)"
        return "🌱 Morador(a) do Vale"

    def _refresh_luna_badge(self):
        luna_on = is_gpt_luna_enabled()
        if hasattr(self, "luna_toggle_btn") and self.luna_toggle_btn.winfo_exists():
            if luna_on:
                self.luna_toggle_btn.configure(
                    text="🌙 GPT Luna: ATIVO",
                    bg="#5C3385",
                    fg="#FFF5FF",
                )
                self.speaker_tag_lbl.configure(
                    text=f"🌙 {self.record.config.name} (Luna)"
                )
            else:
                self.luna_toggle_btn.configure(
                    text="🌾 GPT Luna: OFF",
                    bg="#C89E62",
                    fg=SDV_TEXT_MAIN,
                )
                self.speaker_tag_lbl.configure(
                    text=f"🌾 {self.record.config.name}"
                )

    def _build_ui(self):
        # Moldura quádrupla de madeira esculpida estilo Stardew Valley com chanfros quentes
        outer_frame = tk.Frame(self.win, bg=SDV_OUTER_BORDER, padx=5, pady=5)
        outer_frame.pack(fill="both", expand=True)

        mid_frame = tk.Frame(
            outer_frame,
            bg=SDV_MID_BORDER,
            padx=4,
            pady=4,
            bd=2,
            relief="raised",
        )
        mid_frame.pack(fill="both", expand=True)

        inner_frame = tk.Frame(
            mid_frame,
            bg=SDV_INNER_BORDER,
            padx=3,
            pady=3,
            highlightbackground="#743A15",
            highlightthickness=1,
        )
        inner_frame.pack(fill="both", expand=True)

        parchment = tk.Frame(inner_frame, bg=SDV_PARCHMENT, padx=14, pady=10)
        parchment.pack(fill="both", expand=True)
        parchment.columnconfigure(0, weight=1)
        parchment.columnconfigure(1, weight=0)
        parchment.rowconfigure(0, weight=1)

        # ==================== COLUNA ESQUERDA: BARRA DE TOPO, CAIXA DE FALA, ESCOLHAS E CHAT ====================
        left_col = tk.Frame(parchment, bg=SDV_PARCHMENT)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # 1. Cabeçalho superior estilo faixa de pergaminho escuro com crachás e ações
        top_info = tk.Frame(
            left_col,
            bg="#EAD0A0",
            bd=1,
            relief="solid",
            padx=8,
            pady=4,
        )
        top_info.pack(fill="x", pady=(0, 7))

        self.speaker_tag_lbl = tk.Label(
            top_info,
            text=f"🌾 {self.record.config.name}  •  Diálogo do Vale",
            font=("Georgia", 10, "bold"),
            bg="#EAD0A0",
            fg=SDV_TEXT_MAIN,
        )
        self.speaker_tag_lbl.pack(side="left")

        self.mood_badge_lbl = tk.Label(
            top_info,
            text=self.current_mood_text,
            font=("Segoe UI", 8, "bold"),
            bg="#FFF4D8",
            fg="#6E3B16",
            padx=7,
            pady=1,
            bd=1,
            relief="ridge",
        )
        self.mood_badge_lbl.pack(side="left", padx=(8, 0))

        tk.Button(
            top_info,
            text="🖼️ Retrato",
            command=self.change_dialogue_portrait_image,
            bg="#D6A868",
            fg=SDV_TEXT_MAIN,
            activebackground="#C5924E",
            font=("Segoe UI", 8, "bold"),
            relief="raised",
            bd=1,
            padx=6,
            pady=1,
            cursor="hand2",
        ).pack(side="right")

        self.history_btn = tk.Button(
            top_info,
            text="📜 Histórico",
            command=self._toggle_history_view,
            bg="#DFB77C",
            fg=SDV_TEXT_MAIN,
            activebackground="#CFA15E",
            font=("Segoe UI", 8, "bold"),
            relief="raised",
            bd=1,
            padx=6,
            pady=1,
            cursor="hand2",
        )
        self.history_btn.pack(side="right", padx=(2, 4))

        tk.Button(
            top_info,
            text="🎭 Personalidade",
            command=self.open_personality_customizer_from_dialogue,
            bg="#D9822B",
            fg="white",
            activebackground="#B8681B",
            activeforeground="white",
            font=("Segoe UI", 8, "bold"),
            relief="raised",
            bd=1,
            padx=6,
            pady=1,
            cursor="hand2",
        ).pack(side="right", padx=(2, 4))

        tk.Button(
            top_info,
            text="⚙️",
            command=lambda: open_gpt_luna_settings_modal(
                self.win, on_status_changed=lambda _: self._refresh_luna_badge()
            ),
            bg="#43285C",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="raised",
            bd=1,
            padx=5,
            pady=1,
            cursor="hand2",
        ).pack(side="right", padx=(2, 4))

        self.luna_toggle_btn = tk.Button(
            top_info,
            text="🌙 GPT Luna: ATIVO",
            command=self._toggle_luna_in_dialogue,
            bg="#5C3385",
            fg="#FFF5FF",
            font=("Segoe UI", 8, "bold"),
            relief="raised",
            bd=1,
            padx=7,
            pady=1,
            cursor="hand2",
        )
        self.luna_toggle_btn.pack(side="right", padx=(0, 2))
        self._refresh_luna_badge()

        # 2. Caixa de Fala Principal (Speech Scroll Box) com dupla borda de madeira dourada
        speech_outer = tk.Frame(
            left_col,
            bg="#7A4419",
            padx=2,
            pady=2,
        )
        speech_outer.pack(fill="both", expand=True, pady=(0, 8))

        speech_mid = tk.Frame(
            speech_outer,
            bg="#DFAC60",
            padx=2,
            pady=2,
        )
        speech_mid.pack(fill="both", expand=True)

        self.text_box_frame = tk.Frame(
            speech_mid,
            bg="#FFF8E8",
            padx=14,
            pady=10,
        )
        self.text_box_frame.pack(fill="both", expand=True)
        self.text_box_frame.pack_propagate(False)

        # Marca d'água de aspas + texto principal da fala
        quote_row = tk.Frame(self.text_box_frame, bg="#FFF8E8")
        quote_row.pack(fill="both", expand=True)

        self.quote_mark_lbl = tk.Label(
            quote_row,
            text="❝",
            font=("Georgia", 18, "bold"),
            bg="#FFF8E8",
            fg="#DFBA82",
            anchor="nw",
        )
        self.quote_mark_lbl.pack(side="left", anchor="nw", padx=(0, 4))

        self.dialogue_lbl = tk.Label(
            quote_row,
            text="",
            font=("Georgia", 12),
            bg="#FFF8E8",
            fg=SDV_TEXT_MAIN,
            justify="left",
            anchor="nw",
            wraplength=430,
            cursor="hand2",
        )
        self.dialogue_lbl.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self.dialogue_lbl.bind("<Button-1>", lambda e: self._on_speech_box_click())
        self.text_box_frame.bind("<Button-1>", lambda e: self._on_speech_box_click())

        def _update_dialogue_wrap(event):
            avail_w = max(260, event.width - 36)
            self.dialogue_lbl.configure(wraplength=avail_w)

        self.dialogue_lbl.bind("<Configure>", _update_dialogue_wrap)

        # Rodapé interno da caixa de fala: dica sutil + seta animada de continuação (▼)
        speech_footer = tk.Frame(self.text_box_frame, bg="#FFF8E8")
        speech_footer.pack(fill="x", side="bottom", pady=(2, 0))

        self.speech_hint_lbl = tk.Label(
            speech_footer,
            text="Clique na caixa para completar ou avançar a fala",
            font=("Segoe UI", 8, "italic"),
            bg="#FFF8E8",
            fg="#9E7648",
        )
        self.speech_hint_lbl.pack(side="left")

        self.cont_arrow_lbl = tk.Label(
            speech_footer,
            text="▼",
            font=("Segoe UI", 10, "bold"),
            bg="#FFF8E8",
            fg="#B86F28",
            cursor="hand2",
        )
        self.cont_arrow_lbl.pack(side="right")
        self.cont_arrow_lbl.bind("<Button-1>", lambda e: self._on_speech_box_click())

        # 3. Opções rápidas de resposta interativa (escolhas estilo RPG com cursor ▶ ao passar o mouse)
        choices_frame = tk.Frame(left_col, bg=SDV_PARCHMENT)
        choices_frame.pack(fill="x", pady=(0, 8))

        choices = [
            ("👋 Olá", self._on_choice_greet),
            ("🌾 Fazenda", self._on_choice_farm),
            ("🛠️ Tarefas", self._on_choice_tasks_menu),
            ("🎁 Presente", self._on_choice_gift_menu),
            ("😄 Piada", self._on_choice_joke),
            ("❤️ Elogiar", self._on_choice_compliment),
        ]
        self.choice_buttons: List[tk.Button] = []
        for label_txt, cmd in choices:
            btn_border = tk.Frame(choices_frame, bg="#7A4419", padx=1, pady=1)
            btn_border.pack(side="left", padx=(0, 5), fill="x", expand=True)
            btn = tk.Button(
                btn_border,
                text=label_txt,
                command=cmd,
                bg=SDV_CHOICE_BG,
                fg=SDV_TEXT_MAIN,
                activebackground=SDV_CHOICE_HOVER,
                activeforeground="#240E02",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                bd=0,
                padx=6,
                pady=5,
                cursor="hand2",
            )
            btn.pack(fill="both", expand=True)

            def _on_enter(e, b=btn, orig=label_txt, brd=btn_border):
                b.configure(bg="#F5C97B", text=f"▶ {orig}")
                brd.configure(bg="#B85D19")

            def _on_leave(e, b=btn, orig=label_txt, brd=btn_border):
                b.configure(bg=SDV_CHOICE_BG, text=orig)
                brd.configure(bg="#7A4419")

            btn.bind("<Enter>", _on_enter)
            btn.bind("<Leave>", _on_leave)
            self.choice_buttons.append(btn)

        # 4. Barra de Chat Livre (com placeholder, moldura entalhada e botões em pixel style)
        chat_outer = tk.Frame(left_col, bg="#8C5220", padx=2, pady=2)
        chat_outer.pack(fill="x", side="bottom")

        chat_row = tk.Frame(chat_outer, bg=SDV_PARCHMENT_DARK, padx=8, pady=6)
        chat_row.pack(fill="x")

        tk.Label(
            chat_row,
            text="💬 Você:",
            font=("Georgia", 9, "bold"),
            bg=SDV_PARCHMENT_DARK,
            fg=SDV_TEXT_MAIN,
        ).pack(side="left", padx=(0, 6))

        entry_border = tk.Frame(chat_row, bg="#9C642E", padx=1, pady=1)
        entry_border.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.user_input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            entry_border,
            textvariable=self.user_input_var,
            font=("Segoe UI", 10),
            bg="#FFFDF8",
            fg=SDV_TEXT_MAIN,
            insertbackground=SDV_TEXT_MAIN,
            relief="flat",
            bd=4,
        )
        self.input_entry.pack(fill="x", expand=True, ipady=2)
        self.input_entry.bind("<Return>", lambda e: self.send_custom_message())
        self.input_entry.bind("<FocusIn>", self._on_entry_focus_in)
        self.input_entry.bind("<FocusOut>", self._on_entry_focus_out)
        self._set_placeholder()

        self.send_btn = tk.Button(
            chat_row,
            text="Enviar ⏎",
            command=self.send_custom_message,
            bg=SDV_BTN_GREEN,
            fg="white",
            activebackground="#2E703A",
            activeforeground="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            bd=2,
            padx=12,
            pady=2,
            cursor="hand2",
        )
        self.send_btn.pack(side="left", padx=(0, 4))

        tk.Button(
            chat_row,
            text="✖ Fechar",
            command=self.close,
            bg="#A63A2B",
            fg="white",
            activebackground="#842A1E",
            activeforeground="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            bd=2,
            padx=9,
            pady=2,
            cursor="hand2",
        ).pack(side="right")

        # ==================== COLUNA DIREITA: MOLDURA DO RETRATO, PLACA E CORAÇÕES PIXEL ART ====================
        divider_And_right = tk.Frame(
            parchment,
            bg=SDV_MID_BORDER,
            padx=3,
            pady=3,
            bd=2,
            relief="ridge",
        )
        divider_And_right.grid(row=0, column=1, sticky="ns")

        right_col = tk.Frame(divider_And_right, bg=SDV_PARCHMENT_DARK, padx=10, pady=7)
        right_col.pack(fill="both", expand=True)

        # Moldura de Retrato em Pixel Art (200x200 renderizada via PIL com cantoneiras de madeira)
        self.portrait_canvas = tk.Label(
            right_col,
            bg=SDV_PARCHMENT_DARK,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.portrait_canvas.pack(pady=(0, 5))
        self.portrait_canvas.bind("<Button-1>", lambda e: self._on_click_portrait())

        # Placa de Pergaminho com o Nome do Personagem + Título de Amizade
        name_banner_outer = tk.Frame(right_col, bg="#6E3B16", padx=2, pady=2)
        name_banner_outer.pack(fill="x", pady=(0, 4))

        name_banner = tk.Frame(name_banner_outer, bg="#FDF0D2", padx=8, pady=3)
        name_banner.pack(fill="x")

        self.name_lbl = tk.Label(
            name_banner,
            text=self.record.config.name,
            font=("Georgia", 12, "bold"),
            bg="#FDF0D2",
            fg=SDV_TEXT_MAIN,
        )
        self.name_lbl.pack()

        self.rank_lbl = tk.Label(
            name_banner,
            text=self._get_friendship_rank_title(int(self.state.get("hearts", 6))),
            font=("Segoe UI", 8, "bold"),
            bg="#FDF0D2",
            fg="#8C4A20",
        )
        self.rank_lbl.pack()

        # Medidor de Corações de Amizade desenhado em Pixel Art 16-bit
        self.hearts_lbl = tk.Label(
            right_col,
            bg=SDV_PARCHMENT_DARK,
            bd=0,
        )
        self.hearts_lbl.pack(pady=(2, 2))

        self.stats_lbl = tk.Label(
            right_col,
            text="",
            font=("Segoe UI", 8, "bold"),
            bg=SDV_PARCHMENT_DARK,
            fg=SDV_TEXT_MUTED,
        )
        self.stats_lbl.pack(pady=(1, 0))

    def _set_placeholder(self):
        if not self.user_input_var.get():
            self.has_placeholder = True
            self.input_entry.insert(0, self.placeholder_text)
            self.input_entry.configure(fg="#9E8264")

    def _on_entry_focus_in(self, event=None):
        if self.has_placeholder:
            self.input_entry.delete(0, "end")
            self.input_entry.configure(fg=SDV_TEXT_MAIN)
            self.has_placeholder = False

    def _on_entry_focus_out(self, event=None):
        if not self.user_input_var.get().strip():
            self.input_entry.delete(0, "end")
            self._set_placeholder()

    def _build_ornate_portrait_image(self, raw_portrait: Image.Image, talking_offset: int = 0) -> ImageTk.PhotoImage:
        """
        Envolve o retrato do personagem em uma moldura de madeira esculpida 16-bit (200x200)
        com cantoneiras douradas, sombra interna e leve animação vertical ao falar.
        """
        frame_size = 198
        inner_size = 178
        canvas_img = Image.new("RGB", (frame_size, frame_size), (90, 43, 17))
        draw = ImageDraw.Draw(canvas_img)

        # Moldura externa e chanfro de madeira dourada
        draw.rectangle([0, 0, frame_size - 1, frame_size - 1], fill=(74, 34, 12))
        draw.rectangle([3, 3, frame_size - 4, frame_size - 4], fill=(184, 111, 40))
        draw.rectangle([6, 6, frame_size - 7, frame_size - 7], fill=(229, 160, 69))
        draw.rectangle([8, 8, frame_size - 9, frame_size - 9], fill=(90, 43, 17))

        # Fundo de pergaminho do retrato
        bg_box = Image.new("RGB", (inner_size, inner_size), (216, 174, 118))
        resized = raw_portrait.convert("RGBA").resize((inner_size, inner_size), Image.Resampling.NEAREST)
        bg_box.paste(resized, (0, talking_offset), mask=resized)

        canvas_img.paste(bg_box, (10, 10))

        # Sombra superior interna sutil para profundidade 16-bit
        draw.rectangle([10, 10, frame_size - 11, 12], fill=(158, 118, 72))

        # Cantoneiras esculpidas nos 4 cantos da moldura (estilo Stardew Valley)
        corner_coords = [
            (2, 2, 16, 16),
            (frame_size - 17, 2, frame_size - 3, 16),
            (2, frame_size - 17, 16, frame_size - 3),
            (frame_size - 17, frame_size - 17, frame_size - 3, frame_size - 3),
        ]
        for x0, y0, x1, y1 in corner_coords:
            draw.rectangle([x0, y0, x1, y1], fill=(112, 54, 20), outline=(58, 25, 8))
            draw.rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], fill=(235, 175, 82))
            draw.rectangle([x0 + 6, y0 + 6, x1 - 6, y1 - 6], fill=(140, 74, 32))

        return ImageTk.PhotoImage(canvas_img)

    def _refresh_portrait_display(self, talking_offset: int = 0):
        """Carrega o retrato de diálogo em alta definição (ou 64x64) dentro da moldura Pixel Art."""
        img = self.record.load_dialog_portrait()
        self.portrait_tk = self._build_ornate_portrait_image(img, talking_offset=talking_offset)
        self.portrait_canvas.configure(image=self.portrait_tk)

    def _build_pixel_hearts_banner(self, hearts: int, max_hearts: int = 10) -> ImageTk.PhotoImage:
        """
        Desenha 10 corações em Pixel Art 16-bit (2 linhas de 5 corações)
        com brilho especular branco nos preenchidos e cavidade entalhada nos vazios.
        """
        heart_pattern = [
            "01100110",
            "12211221",
            "12322221",
            "12222221",
            "01222210",
            "00122100",
            "00011000",
        ]
        scale = 3  # Cada coração fica 24x21 px
        hw = 8 * scale
        hh = 7 * scale
        gap_x = 8
        gap_y = 6
        total_w = 5 * hw + 4 * gap_x + 8
        total_h = 2 * hh + gap_y + 6

        img = Image.new("RGB", (total_w, total_h), (232, 198, 142))
        draw = ImageDraw.Draw(img)

        for idx in range(max_hearts):
            row = idx // 5
            col = idx % 5
            ox = 4 + col * (hw + gap_x)
            oy = 3 + row * (hh + gap_y)
            is_filled = idx < hearts

            for py, row_str in enumerate(heart_pattern):
                for px, ch in enumerate(row_str):
                    if ch == "0":
                        continue
                    if is_filled:
                        if ch == "1":
                            color = (78, 16, 26)      # Contorno vinho escuro
                        elif ch == "3":
                            color = (255, 245, 245)   # Brilho especular branco
                        else:
                            color = (224, 38, 62) if py < 4 else (186, 24, 46)
                    else:
                        if ch == "1":
                            color = (128, 88, 48)     # Contorno madeira escura
                        else:
                            color = (198, 158, 106)   # Interior cavidade vazia

                    x0 = ox + px * scale
                    y0 = oy + py * scale
                    draw.rectangle([x0, y0, x0 + scale - 1, y0 + scale - 1], fill=color)

        return ImageTk.PhotoImage(img)

    def _refresh_hearts_display(self):
        hearts = max(0, min(10, int(self.state.get("hearts", 6))))
        self.hearts_banner_tk = self._build_pixel_hearts_banner(hearts, 10)
        self.hearts_lbl.configure(image=self.hearts_banner_tk)
        if hasattr(self, "rank_lbl") and self.rank_lbl.winfo_exists():
            self.rank_lbl.configure(text=self._get_friendship_rank_title(hearts))
        talks = self.state.get("talks_count", 0)
        gifts = self.state.get("gifts_count", 0)
        self.stats_lbl.configure(text=f"❤️ {hearts}/10  •  💬 {talks}  •  🎁 {gifts}")

    def _set_mood_badge(self, action_or_topic: str):
        dom_emo = self.personality.get("dominant_emotion", "😊 Feliz no Vale")
        mood_map = {
            "greeting": dom_emo,
            "idle": dom_emo,
            "happy_dance": "✨ Super Animado!",
            "coffee_break": "☕ Energia do Café!",
            "water_crops": "🌱 Cuidando da Fazenda",
            "fishing": "🎣 Foco de Pescador",
            "sleep_sit": "💤 Relaxando",
            "thinking": "💭 Pensando...",
        }
        self.current_mood_text = mood_map.get(action_or_topic, dom_emo)
        if hasattr(self, "mood_badge_lbl") and self.mood_badge_lbl.winfo_exists():
            self.mood_badge_lbl.configure(text=self.current_mood_text)

    def _start_continuation_cursor_anim(self):
        if not self.win.winfo_exists():
            return
        self.cursor_blink_state = not self.cursor_blink_state
        if hasattr(self, "cont_arrow_lbl") and self.cont_arrow_lbl.winfo_exists():
            if self.typing_after_id is not None:
                self.cont_arrow_lbl.configure(text="•••", fg="#C69453")
            else:
                self.cont_arrow_lbl.configure(
                    text="▼" if self.cursor_blink_state else "▽",
                    fg="#A64B17" if self.cursor_blink_state else "#D98A2B",
                )
        self.cursor_blink_after_id = self.win.after(420, self._start_continuation_cursor_anim)

    def _on_speech_box_click(self):
        if self.showing_history:
            self._toggle_history_view()
            return
        if self.typing_after_id is not None:
            self.finish_typing_immediately()
        else:
            # Se já terminou de digitar, clicar avança para uma nova fala espontânea!
            topic = random.choice(["greeting", "farm_talk", "work_tip", "joke"])
            self._increment_talk()
            self.set_dialogue_text(self._pick_dialogue(topic), trigger_action="idle")

    def _toggle_history_view(self):
        self.showing_history = not self.showing_history
        if self.showing_history:
            self.finish_typing_immediately()
            self.history_btn.configure(text="💬 Voltar à Fala", bg="#5C3385", fg="white")
            hist = self.state.get("history", [])[-4:]
            if not hist:
                log_txt = "📜 Histórico vazio por enquanto! Envie uma mensagem abaixo ou escolha uma opção para conversar."
            else:
                lines = []
                for item in hist:
                    u = item.get("user", "")
                    n = item.get("npc", "")
                    lines.append(f"• Você: {u}\n  {self.record.config.name}: {n}")
                log_txt = "\n".join(lines)
            self.dialogue_lbl.configure(text=log_txt, font=("Segoe UI", 9))
            self.speech_hint_lbl.configure(text="📜 Exibindo últimas mensagens (clique para voltar)")
        else:
            self.history_btn.configure(text="📜 Histórico", bg="#DFB77C", fg=SDV_TEXT_MAIN)
            self.dialogue_lbl.configure(text=self.full_text, font=("Georgia", 12))
            self.speech_hint_lbl.configure(text="Clique na caixa para completar ou avançar a fala")

    def set_dialogue_text(self, text: str, trigger_action: Optional[str] = None, short_bubble: Optional[str] = None):
        """Inicia o efeito de máquina de escrever clássico do Stardew Valley para exibir a fala."""
        if self.showing_history:
            self.showing_history = False
            self.history_btn.configure(text="📜 Histórico", bg="#DFB77C", fg=SDV_TEXT_MAIN)
            self.dialogue_lbl.configure(font=("Georgia", 12))

        if self.typing_after_id:
            try:
                self.win.after_cancel(self.typing_after_id)
            except Exception:
                pass
            self.typing_after_id = None

        self.full_text = text.strip()
        self.typed_index = 0
        self.dialogue_lbl.configure(text="")
        self._set_mood_badge(trigger_action or "greeting")

        if trigger_action and self.on_action_trigger:
            bubble = short_bubble or (self.full_text[:48] + "..." if len(self.full_text) > 48 else self.full_text)
            self.on_action_trigger(trigger_action, bubble)

        self._typewriter_step()

    def _typewriter_step(self):
        if not self.win.winfo_exists():
            return
        if self.typed_index < len(self.full_text):
            self.typed_index = min(len(self.full_text), self.typed_index + 2)
            current_slice = self.full_text[: self.typed_index]
            self.dialogue_lbl.configure(text=current_slice)

            # Animação sutil do retrato falando a cada 3 passos
            if self.typed_index % 6 == 0:
                self.talking_frame_toggle = not self.talking_frame_toggle
                self._refresh_portrait_display(talking_offset=-2 if self.talking_frame_toggle else 0)

            last_char = current_slice[-1] if current_slice else ""
            delay = 65 if last_char in (".", "!", "?", ",") else 20
            self.typing_after_id = self.win.after(delay, self._typewriter_step)
        else:
            self.dialogue_lbl.configure(text=self.full_text)
            self._refresh_portrait_display(talking_offset=0)
            self.typing_after_id = None

    def finish_typing_immediately(self):
        if self.typing_after_id:
            try:
                self.win.after_cancel(self.typing_after_id)
            except Exception:
                pass
            self.typing_after_id = None
        self.typed_index = len(self.full_text)
        self.dialogue_lbl.configure(text=self.full_text)
        self._refresh_portrait_display(talking_offset=0)

    def _increment_talk(self, heart_bonus: int = 0):
        self.state["talks_count"] = int(self.state.get("talks_count", 0)) + 1
        if heart_bonus > 0:
            self.state["hearts"] = min(10, int(self.state.get("hearts", 6)) + heart_bonus)
        elif self.state["talks_count"] % 4 == 0:
            self.state["hearts"] = min(10, int(self.state.get("hearts", 6)) + 1)
        self._save_dialogue_state()
        self._refresh_hearts_display()

    def _on_click_portrait(self):
        self.set_dialogue_text(
            f"Haha, gostou do meu retrato na moldura entalhada do Pixel Valley? Você pode clicar em '🖼️ Retrato' no topo se quiser testar outra arte!",
            trigger_action="happy_dance",
            short_bubble="❤️ Gostou do meu retrato?",
        )

    def _on_choice_greet(self):
        self._increment_talk()
        msg = self._pick_dialogue("greeting")
        self.set_dialogue_text(msg, trigger_action="idle", short_bubble=f"Olá! Que bom te ver! 👋")

    def _on_choice_farm(self):
        self._increment_talk()
        msg = self._pick_dialogue("farm_talk")
        act = random.choice(["water_crops", "coffee_break", "fishing"])
        self.set_dialogue_text(msg, trigger_action=act, short_bubble="Dia produtivo na fazenda! 🌾")

    def _on_choice_joke(self):
        self._increment_talk()
        topic = random.choice(["joke", "work_tip"])
        msg = self._pick_dialogue(topic)
        self.set_dialogue_text(msg, trigger_action="idle", short_bubble="Dica & humor do Vale! 😄")

    def _on_choice_compliment(self):
        self._increment_talk(heart_bonus=1)
        msg = self._pick_dialogue("compliment")
        self.set_dialogue_text(msg, trigger_action="happy_dance", short_bubble=f"❤️ {self.record.config.name} adorou o elogio!")

    def _on_choice_tasks_menu(self):
        """Abre o menu de Tarefas de Área de Trabalho atribuídas a este avatar."""
        assigned = get_avatar_assigned_tasks(self.record.avatar_id, self.record.config.name)
        menu = tk.Menu(
            self.win,
            tearoff=0,
            bg=SDV_PARCHMENT,
            fg=SDV_TEXT_MAIN,
            activebackground=SDV_BTN_GREEN,
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
        )
        menu.add_command(label=f"🛠️ Tarefas de {self.record.config.name}:", state="disabled")
        menu.add_separator()
        if assigned:
            for tid in assigned:
                tinfo = AVAILABLE_TASKS.get(tid)
                if tinfo:
                    menu.add_command(
                        label=f"{tinfo['title']}",
                        command=lambda k=tid: self._run_dialogue_task(k),
                    )
        else:
            menu.add_command(label="(Nenhuma tarefa habilitada para este avatar)", state="disabled")

        if self.on_open_tasks_manager:
            menu.add_separator()
            menu.add_command(
                label="⚙️ Configurar Qual Avatar Executa Qual Tarefa...",
                command=self.on_open_tasks_manager,
            )
        try:
            x = self.win.winfo_rootx() + 190
            y = self.win.winfo_rooty() + 220
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _run_dialogue_task(self, task_id: str):
        tinfo = AVAILABLE_TASKS.get(task_id, {})
        self._increment_talk(heart_bonus=1)
        if task_id == "organize_items":
            self.set_dialogue_text(
                f"Deixa comigo! Vou usar meu regador e minhas ferramentas para organizar seus arquivos e atalhos em pastas bem limpinhas! 🌱🗂️",
                trigger_action="water_crops",
                short_bubble="🗂️ Organizando itens!",
            )
        elif task_id == "fish_large_files":
            self.set_dialogue_text(
                f"Hora da pescaria! Vou lançar minha vara de pesca na pasta Downloads e Área de Trabalho para fisgar os arquivos mais pesados! 🎣🐟",
                trigger_action="fishing",
                short_bubble="🎣 Pescando arquivos grandes!",
            )
        if self.on_execute_task:
            self.on_execute_task(task_id)
        else:
            if task_id == "organize_items":
                OrganizeItemsModal(self.master, self.record.config.name, on_action_trigger=self.on_action_trigger)
            elif task_id == "fish_large_files":
                FishLargeFilesModal(self.master, self.record.config.name, on_action_trigger=self.on_action_trigger)

    def _on_choice_gift_menu(self):
        """Abre um menu estilo inventário do Stardew Valley para escolher qual presente entregar."""
        menu = tk.Menu(
            self.win,
            tearoff=0,
            bg=SDV_PARCHMENT,
            fg=SDV_TEXT_MAIN,
            activebackground=SDV_MID_BORDER,
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
        )
        menu.add_command(label=f"🎁 Escolha um Presente para {self.record.config.name}:", state="disabled")
        menu.add_separator()
        for gift in STARDEW_GIFTS:
            menu.add_command(
                label=f"{gift['name']}  (+{gift['points']} ❤️)",
                command=lambda g=gift: self._give_gift(g),
            )
        try:
            x = self.win.winfo_rootx() + 260
            y = self.win.winfo_rooty() + 210
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _give_gift(self, gift: Dict[str, Any]):
        self.personality = load_avatar_personality(
            self.record.folder_path,
            self.record.config.name,
            self.record.avatar_id,
        )
        likes_joined = " ".join(self.personality.get("likes", [])).lower()
        gift_name_l = gift["name"].lower()
        is_fav_match = (
            ("café" in gift_name_l and "café" in likes_joined)
            or ("bolo" in gift_name_l and ("bolo" in likes_joined or "doce" in likes_joined))
            or ("pizza" in gift_name_l and ("pizza" in likes_joined or "lanche" in likes_joined))
            or ("girassol" in gift_name_l and ("planta" in likes_joined or "flor" in likes_joined or "sol" in likes_joined))
            or ("fragmento" in gift_name_l and ("crista" in likes_joined or "jogos" in likes_joined))
            or ("morango" in gift_name_l and ("planta" in likes_joined or "doce" in likes_joined))
        )

        pts = int(gift.get("points", 1)) + (1 if is_fav_match else 0)
        self.state["gifts_count"] = int(self.state.get("gifts_count", 0)) + 1
        self.state["hearts"] = min(10, int(self.state.get("hearts", 6)) + pts)
        self._save_dialogue_state()
        self._refresh_hearts_display()
        act = "coffee_break" if "Café" in gift["name"] else "happy_dance"
        dom_emo = self.personality.get("dominant_emotion", "🥰")
        reaction_txt = gift["reaction"]
        if is_fav_match:
            reaction_txt = (
                f"[{dom_emo}] MEU FAVORITO!! {gift['reaction']} "
                f"(Você acertou em cheio nos meus gostos pessoais: +{pts} ❤️!)"
            )
        self.set_dialogue_text(
            reaction_txt,
            trigger_action=act,
            short_bubble=f"Adorou ganhar {gift['name']}! ❤️",
        )

    def change_dialogue_portrait_image(self):
        """Permite escolher qualquer imagem (ex: 'caixa dialogo deivdson.jpg' em Downloads) como retrato da caixa de diálogo."""
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        initial_dir = downloads_dir if os.path.exists(downloads_dir) else os.path.expanduser("~")
        file_path = filedialog.askopenfilename(
            parent=self.win,
            title=f"Selecionar Imagem da Caixa de Diálogo para {self.record.config.name}",
            initialdir=initial_dir,
            filetypes=[
                ("Imagens", "*.jpg *.jpeg *.png *.webp *.bmp"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not file_path:
            return
        try:
            self.record.set_dialog_portrait_from_file(file_path)
            self._refresh_portrait_display()
            if self.on_portrait_updated:
                self.on_portrait_updated(self.record)
            self.set_dialogue_text(
                f"Uau! Minha nova foto de caixa de diálogo ('{os.path.basename(file_path)}') ficou incrível na moldura! ✨",
                trigger_action="happy_dance",
                short_bubble="Novo retrato de diálogo! 🖼️",
            )
        except Exception as exc:
            self.set_dialogue_text(f"Ops, não consegui carregar essa imagem: {exc}")

    def send_custom_message(self):
        if self.has_placeholder:
            return
        user_msg = self.user_input_var.get().strip()
        if not user_msg or self.is_waiting_llm:
            return
        self.user_input_var.set("")
        self._increment_talk()

        # Mostrar feedback imediato enquanto gera a resposta inteligente
        self.is_waiting_llm = True
        self._set_mood_badge("thinking")
        self.send_btn.configure(state="disabled", text="...")
        self.dialogue_lbl.configure(text=f"💭 {self.record.config.name} está pensando na resposta...")

        threading.Thread(
            target=self._generate_reply_thread,
            args=(user_msg,),
            daemon=True,
        ).start()

    def _generate_reply_thread(self, user_msg: str):
        reply_text = self._query_character_ai_or_fallback(user_msg)
        if self.win.winfo_exists():
            self.win.after(0, lambda: self._on_reply_ready(user_msg, reply_text))

    def _on_reply_ready(self, user_msg: str, reply_text: str):
        self.is_waiting_llm = False
        if not self.win.winfo_exists():
            return
        self.send_btn.configure(state="normal", text="Enviar ⏎")

        hist = self.state.get("history", [])
        hist.append({"user": user_msg, "npc": reply_text})
        self.state["history"] = hist[-12:]
        self._save_dialogue_state()

        # Escolher animação contextual conforme o tema da resposta
        lower_r = (user_msg + " " + reply_text).lower()
        if any(w in lower_r for w in ("café", "cafe", "expresso", "beber")):
            act = "coffee_break"
        elif any(w in lower_r for w in ("pesca", "peixe", "rio", "anzol")):
            act = "fishing"
        elif any(w in lower_r for w in ("planta", "regar", "fazenda", "colheita", "semente")):
            act = "water_crops"
        elif any(w in lower_r for w in ("dormir", "sono", "cansado", "descansar")):
            act = "sleep_sit"
        elif any(w in lower_r for w in ("obrigado", "lindo", "incrível", "amo", "parabéns", "legal")):
            act = "happy_dance"
        else:
            act = "idle"

        self.set_dialogue_text(reply_text, trigger_action=act)

    def _query_character_ai_or_fallback(self, user_msg: str) -> str:
        """
        Tenta responder interpretando o personagem via GPT Luna (se ativado) ou Gemini / Ollama,
        usando a Personalidade Individual (gostos, desgostos, traços e emoções) do avatar.
        """
        char_name = self.record.config.name
        hearts = int(self.state.get("hearts", 6))
        self.personality = load_avatar_personality(
            self.record.folder_path,
            char_name,
            self.record.avatar_id,
        )
        persona = format_personality_summary(self.personality)
        recent_history = self.state.get("history", [])[-4:]

        if is_gpt_luna_enabled():
            return generate_gpt_luna_reply(
                char_name=char_name,
                persona_bio=persona,
                hearts=hearts,
                user_msg=user_msg,
                history=recent_history,
                personality=self.personality,
            )

        settings = load_llm_settings()
        api_key = settings.get("api_key", "").strip()
        provider = settings.get("provider", "auto")
        hist_str = "\n".join([f"Jogador: {h['user']}\n{char_name}: {h['npc']}" for h in recent_history])

        sys_prompt = (
            f"Você está interpretando o personagem '{char_name}' em uma caixa de diálogo estilo Stardew Valley "
            f"na área de trabalho do computador do usuário.\n"
            f"Sobre você: {persona}\n"
            f"Nível de amizade atual com o usuário: {hearts}/10 corações.\n"
            f"Regras: Responda em português, em 1 a 3 frases curtas, acolhedoras, carismáticas e com referências "
            f"leves ao universo de Stardew Valley e ao dia a dia no computador. Não use markdown.\n"
        )
        if hist_str:
            sys_prompt += f"\nHistórico recente:\n{hist_str}\n"
        sys_prompt += f"\nMensagem do Jogador: {user_msg}\nResposta de {char_name}:"

        if api_key and provider in ("auto", "gemini") and not api_key.startswith("sk-"):
            for model_candidate in [settings.get("model", "gemini-2.5-flash"), "gemini-2.5-flash", "gemini-2.0-flash"]:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_candidate}:generateContent?key={api_key}"
                    gen_cfg: Dict[str, Any] = {"temperature": 0.7, "maxOutputTokens": 1024}
                    if "2.5" in model_candidate:
                        gen_cfg["thinkingConfig"] = {"thinkingBudget": 0}
                    payload = {
                        "contents": [{"parts": [{"text": sys_prompt}]}],
                        "generationConfig": gen_cfg,
                    }
                    r = httpx.post(url, json=payload, timeout=8.0)
                    if r.status_code == 200:
                        data = r.json()
                        txt = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        if txt:
                            return txt
                except Exception:
                    continue

        if provider in ("auto", "ollama"):
            try:
                ollama_url = settings.get("ollama_url", "http://localhost:11434").rstrip("/")
                r = httpx.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": settings.get("model") or "llama3",
                        "prompt": sys_prompt,
                        "stream": False,
                    },
                    timeout=5.0,
                )
                if r.status_code == 200:
                    txt = r.json().get("response", "").strip()
                    if txt:
                        return txt
            except Exception:
                pass

        # Resposta inteligente offline baseada em intenção (sempre funciona mesmo sem internet!)
        msg_l = user_msg.lower()
        if any(w in msg_l for w in ("oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "e ai", "e aí")):
            return self._pick_dialogue("greeting")
        if any(w in msg_l for w in ("como vai", "tudo bem", "como você está", "como esta")):
            return f"Estou ótimo por aqui! Com {hearts} corações de amizade e essa vista privilegiada da sua área de trabalho, não tem como reclamar! E você, como está?"
        if any(w in msg_l for w in ("café", "cafe", "fome", "comer", "beber")):
            return "Falou em café?! Um Café Expresso Triplo do Saloon Fruta Estrelar agora cairia perfeitamente para dar aquele gás no código! ☕✨"
        if any(w in msg_l for w in ("trabalh", "estud", "código", "codigo", "program", "artigo", "tcc", "pesquisa")):
            if self._is_deivdson():
                return "Boa! Pesquisa e código exigem foco, mas quando a gente vê os resultados tomando forma dá um orgulho danado. Vai com tudo que eu fico na torcida aqui na tela! 💻🚀"
            return self._pick_dialogue("work_tip")
        if any(w in msg_l for w in ("fazenda", "plantar", "stardew", "colheita", "chuva")):
            return self._pick_dialogue("farm_talk")
        if any(w in msg_l for w in ("piada", "engraçad", "rir")):
            return self._pick_dialogue("joke")
        if any(w in msg_l for w in ("lindo", "bonito", "gostei", "legal", "incrível", "top", "óculos", "bigode", "retrato")):
            return self._pick_dialogue("compliment")

        generic_replies = [
            f"Interessante você dizer isso! Aqui no Vale do Orvalho a gente aprende que cada conversa traz uma boa ideia. Me conta mais!",
            f"Haha, adorei conversar sobre '{user_msg[:35]}'! Sempre que quiser fazer uma pausa no computador, é só clicar em mim!",
            f"Com certeza! Entre uma caminhada pela barra de tarefas e uma regada nas plantas, adoro trocar essas ideias com você! 🌾✨",
        ]
        return random.choice(generic_replies)

    def focus(self):
        try:
            self.win.deiconify()
            self.win.lift()
            self.input_entry.focus_set()
        except Exception:
            pass

    def close(self):
        if self.typing_after_id:
            try:
                self.win.after_cancel(self.typing_after_id)
            except Exception:
                pass
            self.typing_after_id = None
        if self.cursor_blink_after_id:
            try:
                self.win.after_cancel(self.cursor_blink_after_id)
            except Exception:
                pass
            self.cursor_blink_after_id = None
        try:
            self.win.destroy()
        except Exception:
            pass
        if self.on_close:
            self.on_close()
