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
from PIL import Image, ImageTk
import httpx

from library_manager import AvatarRecord
from llm_sprite_designer import load_llm_settings
from gpt_luna import (
    is_gpt_luna_enabled,
    set_gpt_luna_enabled,
    generate_gpt_luna_reply,
    _generate_local_luna_fallback,
    open_gpt_luna_settings_modal,
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
    ):
        self.master = master
        self.record = record
        self.on_action_trigger = on_action_trigger
        self.on_portrait_updated = on_portrait_updated
        self.on_close = on_close

        self.win = tk.Toplevel(master)
        self.win.title(f"💬 Conversando com {self.record.config.name} — Stardew Valley")
        self.win.configure(bg=SDV_OUTER_BORDER)
        self.win.wm_attributes("-topmost", True)
        self.win.resizable(False, False)

        # Dimensões estilo caixa de diálogo clássica do Stardew Valley (larga na parte inferior da tela)
        self.win_w = 880
        self.win_h = 370
        self._position_window()

        # Estado de interação, amizade e efeito typewriter
        self.friendship_State_path = os.path.join(self.record.folder_path, "dialogue_state.json")
        self.state = self._load_dialogue_state()
        self.full_text = ""
        self.typed_index = 0
        self.typing_after_id: Optional[str] = None
        self.portrait_tk: Optional[ImageTk.PhotoImage] = None
        self.is_waiting_llm = False

        self._build_ui()
        self._refresh_portrait_display()
        self._refresh_hearts_display()

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
            "persona_bio": "",
            "history": [],
        }
        if "deivdson" in self.record.config.name.lower():
            default_state["hearts"] = 8
            default_state["persona_bio"] = (
                "Deivdson, pesquisador e desenvolvedor apaixonado por tecnologia, inteligência artificial "
                "e pela vida tranquila no campo do Stardew Valley. Usa óculos arredondados, tem cabelo "
                "cacheado castanho com mechas douradas, bigode estiloso e cavanhaque, camisa clara com bolsa a tiracolo."
            )
        if os.path.exists(self.friendship_State_path):
            try:
                with open(self.friendship_State_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                default_state.update(saved)
            except Exception:
                pass
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
        if is_gpt_luna_enabled():
            return _generate_local_luna_fallback(
                char_name=self.record.config.name,
                hearts=int(self.state.get("hearts", 6)),
                topic=topic,
            )
        custom_list = self.state.get("custom_lines", [])
        if topic == "greeting" and custom_list and random.random() < 0.35:
            return random.choice(custom_list)
        if self._is_deivdson() and topic in DEIVDSON_SPECIAL_DIALOGUES:
            pool = DEIVDSON_SPECIAL_DIALOGUES[topic] + DEFAULT_DIALOGUES_BY_TOPIC.get(topic, [])
            return random.choice(pool)
        pool = DEFAULT_DIALOGUES_BY_TOPIC.get(topic, DEFAULT_DIALOGUES_BY_TOPIC["greeting"])
        return random.choice(pool)

    def _toggle_luna_in_dialogue(self):
        new_state = not is_gpt_luna_enabled()
        set_gpt_luna_enabled(new_state)
        self._refresh_luna_badge()
        if new_state:
            msg = _generate_local_luna_fallback(
                char_name=self.record.config.name,
                hearts=int(self.state.get("hearts", 6)),
                topic="greeting",
            )
            self.set_dialogue_text(msg, trigger_action="happy_dance", short_bubble="🌙 GPT Luna Ativado!")
        else:
            self.set_dialogue_text(
                f"Modo clássico do Vale do Orvalho ativado! Sempre que quiser ligar a personalidade GPT Luna de novo, é só clicar no botão 🌙 acima!",
                trigger_action="idle",
                short_bubble="🌾 Modo Clássico!",
            )

    def _refresh_luna_badge(self):
        luna_on = is_gpt_luna_enabled()
        if hasattr(self, "luna_toggle_btn") and self.luna_toggle_btn.winfo_exists():
            if luna_on:
                self.luna_toggle_btn.configure(
                    text="🌙 GPT Luna: ATIVO",
                    bg="#5C3385",
                    fg="#FFF5FF",
                )
                self.speaker_tag_lbl.configure(text=f"🌙 {self.record.config.name} (Personalidade GPT Luna):")
            else:
                self.luna_toggle_btn.configure(
                    text="🌾 GPT Luna: OFF",
                    bg="#B89660",
                    fg=SDV_TEXT_MAIN,
                )
                self.speaker_tag_lbl.configure(text=f"🌾 {self.record.config.name} diz:")

    def _build_ui(self):
        # Moldura tripla de madeira esculpida típica do Stardew Valley
        outer_frame = tk.Frame(self.win, bg=SDV_OUTER_BORDER, padx=6, pady=6)
        outer_frame.pack(fill="both", expand=True)

        mid_frame = tk.Frame(outer_frame, bg=SDV_MID_BORDER, padx=5, pady=5, bd=2, relief="raised")
        mid_frame.pack(fill="both", expand=True)

        inner_frame = tk.Frame(mid_frame, bg=SDV_INNER_BORDER, padx=4, pady=4)
        inner_frame.pack(fill="both", expand=True)

        parchment = tk.Frame(inner_frame, bg=SDV_PARCHMENT, padx=14, pady=12)
        parchment.pack(fill="both", expand=True)
        parchment.columnconfigure(0, weight=1)
        parchment.columnconfigure(1, weight=0)
        parchment.rowconfigure(0, weight=1)

        # ==================== COLUNA ESQUERDA: TEXTO, ESCOLHAS E CHAT ====================
        left_col = tk.Frame(parchment, bg=SDV_PARCHMENT)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # Cabeçalho sutil com status da conversa + botão de pular digitação
        top_info = tk.Frame(left_col, bg=SDV_PARCHMENT)
        top_info.pack(fill="x", pady=(0, 4))

        self.speaker_tag_lbl = tk.Label(
            top_info,
            text=f"🌾 {self.record.config.name} diz:",
            font=("Georgia", 10, "bold"),
            bg=SDV_PARCHMENT,
            fg=SDV_TEXT_MUTED,
        )
        self.speaker_tag_lbl.pack(side="left")

        tk.Button(
            top_info,
            text="🖼️ Trocar Retrato",
            command=self.change_dialogue_portrait_image,
            bg="#D6A868",
            fg=SDV_TEXT_MAIN,
            font=("Segoe UI", 8, "bold"),
            relief="groove",
            padx=6,
            pady=1,
            cursor="hand2",
        ).pack(side="right")

        tk.Button(
            top_info,
            text="⚙️",
            command=lambda: open_gpt_luna_settings_modal(self.win, on_status_changed=lambda _: self._refresh_luna_badge()),
            bg="#43285C",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="groove",
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
            relief="groove",
            padx=7,
            pady=1,
            cursor="hand2",
        )
        self.luna_toggle_btn.pack(side="right", padx=(0, 2))
        self._refresh_luna_badge()

        # Área principal do texto da fala (clicável para completar o efeito máquina de escrever)
        text_box_frame = tk.Frame(
            left_col,
            bg="#FFF5DF",
            bd=2,
            relief="sunken",
            padx=12,
            pady=10,
            highlightbackground="#C69453",
            highlightthickness=1,
        )
        text_box_frame.pack(fill="x", pady=(0, 8))

        self.dialogue_lbl = tk.Label(
            text_box_frame,
            text="",
            font=("Georgia", 13),
            bg="#FFF5DF",
            fg=SDV_TEXT_MAIN,
            justify="left",
            anchor="nw",
            wraplength=540,
            height=4,
            cursor="hand2",
        )
        self.dialogue_lbl.pack(fill="both", expand=True)
        self.dialogue_lbl.bind("<Button-1>", lambda e: self.finish_typing_immediately())

        # Opções rápidas de resposta interativa (escolhas estilo RPG Stardew Valley)
        choices_frame = tk.Frame(left_col, bg=SDV_PARCHMENT)
        choices_frame.pack(fill="x", pady=(0, 8))

        choices = [
            ("👋 Cumprimentar", self._on_choice_greet),
            ("🌾 Papo da Fazenda", self._on_choice_farm),
            ("🎁 Dar Presente", self._on_choice_gift_menu),
            ("😄 Contar Piada / Dica", self._on_choice_joke),
            ("❤️ Elogiar", self._on_choice_compliment),
        ]
        for idx, (label_txt, cmd) in enumerate(choices):
            btn = tk.Button(
                choices_frame,
                text=label_txt,
                command=cmd,
                bg=SDV_CHOICE_BG,
                fg=SDV_TEXT_MAIN,
                activebackground=SDV_CHOICE_HOVER,
                activeforeground=SDV_TEXT_MAIN,
                font=("Segoe UI", 9, "bold"),
                relief="raised",
                bd=2,
                padx=8,
                pady=4,
                cursor="hand2",
            )
            btn.pack(side="left", padx=(0, 5), fill="x", expand=True)

        # Barra de Chat Livre (digite qualquer pergunta ou mensagem para o personagem!)
        chat_row = tk.Frame(left_col, bg=SDV_PARCHMENT_DARK, bd=2, relief="groove", padx=8, pady=6)
        chat_row.pack(fill="x", side="bottom")

        tk.Label(
            chat_row,
            text="💬 Você:",
            font=("Segoe UI", 9, "bold"),
            bg=SDV_PARCHMENT_DARK,
            fg=SDV_TEXT_MAIN,
        ).pack(side="left", padx=(0, 6))

        self.user_input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            chat_row,
            textvariable=self.user_input_var,
            font=("Segoe UI", 10),
            bg="#FFFDF8",
            fg=SDV_TEXT_MAIN,
            relief="sunken",
            bd=2,
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=3)
        self.input_entry.bind("<Return>", lambda e: self.send_custom_message())

        self.send_btn = tk.Button(
            chat_row,
            text="Enviar ⏎",
            command=self.send_custom_message,
            bg=SDV_BTN_GREEN,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
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
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=2,
            cursor="hand2",
        ).pack(side="right")

        # ==================== DIVISÓRIA VERTICAL DE MADEIRA ====================
        divider_And_right = tk.Frame(parchment, bg=SDV_MID_BORDER, padx=3, pady=3, bd=2, relief="ridge")
        divider_And_right.grid(row=0, column=1, sticky="ns")

        right_col = tk.Frame(divider_And_right, bg=SDV_PARCHMENT_DARK, padx=10, pady=8)
        right_col.pack(fill="both", expand=True)

        # Moldura do Retrato da Caixa de Diálogo (185x185)
        portrait_border = tk.Frame(right_col, bg=SDV_OUTER_BORDER, padx=3, pady=3, bd=2, relief="sunken")
        portrait_border.pack(pady=(0, 6))

        self.portrait_canvas = tk.Label(
            portrait_border,
            bg=SDV_PORTRAIT_BG,
            width=184,
            height=184,
            cursor="hand2",
        )
        self.portrait_canvas.pack()
        self.portrait_canvas.bind("<Button-1>", lambda e: self._on_click_portrait())

        # Placa com o Nome do Personagem
        name_banner = tk.Frame(right_col, bg=SDV_PARCHMENT, bd=2, relief="groove", padx=8, pady=2)
        name_banner.pack(fill="x", pady=(0, 4))

        self.name_lbl = tk.Label(
            name_banner,
            text=self.record.config.name,
            font=("Georgia", 12, "bold"),
            bg=SDV_PARCHMENT,
            fg=SDV_TEXT_MAIN,
        )
        self.name_lbl.pack()

        # Medidor de Corações de Amizade (Stardew Valley Friendship Hearts)
        self.hearts_lbl = tk.Label(
            right_col,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg=SDV_PARCHMENT_DARK,
            fg="#C82838",
        )
        self.hearts_lbl.pack()

        self.stats_lbl = tk.Label(
            right_col,
            text="",
            font=("Segoe UI", 8),
            bg=SDV_PARCHMENT_DARK,
            fg=SDV_TEXT_MUTED,
        )
        self.stats_lbl.pack(pady=(1, 0))

    def _refresh_portrait_display(self):
        """Carrega o retrato de diálogo em alta definição (ou 64x64) sem perder nitidez da Pixel Art."""
        img = self.record.load_dialog_portrait()
        # Usar NEAREST quando a imagem for pequena (ex: 64x64) ou LANCZOS/NEAREST híbrido para retratos HD em pixel art
        if img.width <= 128:
            resized = img.resize((184, 184), Image.Resampling.NEAREST)
        else:
            resized = img.resize((184, 184), Image.Resampling.NEAREST)
        self.portrait_tk = ImageTk.PhotoImage(resized)
        self.portrait_canvas.configure(image=self.portrait_tk)

    def _refresh_hearts_display(self):
        hearts = max(0, min(10, int(self.state.get("hearts", 6))))
        filled = "❤️" * hearts
        empty = "🤍" * (10 - hearts)
        # Exibir em duas linhas de 5 corações para ficar compacto e elegante abaixo do retrato
        row1 = ("❤️" * min(5, hearts)) + ("🤍" * max(0, 5 - hearts))
        row2 = ("❤️" * max(0, hearts - 5)) + ("🤍" * max(0, 10 - max(5, hearts)))
        self.hearts_lbl.configure(text=f"{row1}\n{row2}")
        talks = self.state.get("talks_count", 0)
        gifts = self.state.get("gifts_count", 0)
        self.stats_lbl.configure(text=f"Amizade: {hearts}/10  |  Conversas: {talks}  |  Presentes: {gifts}")

    def set_dialogue_text(self, text: str, trigger_action: Optional[str] = None, short_bubble: Optional[str] = None):
        """Inicia o efeito de máquina de escrever clássico do Stardew Valley para exibir a fala."""
        if self.typing_after_id:
            try:
                self.win.after_cancel(self.typing_after_id)
            except Exception:
                pass
            self.typing_after_id = None

        self.full_text = text.strip()
        self.typed_index = 0
        self.dialogue_lbl.configure(text="")

        if trigger_action and self.on_action_trigger:
            bubble = short_bubble or (self.full_text[:24] + "..." if len(self.full_text) > 24 else self.full_text)
            self.on_action_trigger(trigger_action, bubble)

        self._typewriter_step()

    def _typewriter_step(self):
        if not self.win.winfo_exists():
            return
        if self.typed_index < len(self.full_text):
            self.typed_index += 2
            current_slice = self.full_text[: self.typed_index]
            self.dialogue_lbl.configure(text=current_slice)
            self.typing_after_id = self.win.after(22, self._typewriter_step)
        else:
            self.dialogue_lbl.configure(text=self.full_text)
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
            f"Haha, gostou do meu retrato na moldura do Stardew Valley? Você pode clicar em '🖼️ Trocar Imagem da Caixa de Diálogo' se quiser testar outra arte!",
            trigger_action="happy_dance",
            short_bubble="❤️ Gostou do retrato?",
        )

    def _on_choice_greet(self):
        self._increment_talk()
        msg = self._pick_dialogue("greeting")
        self.set_dialogue_text(msg, trigger_action="idle", short_bubble=f"Olá! 👋")

    def _on_choice_farm(self):
        self._increment_talk()
        msg = self._pick_dialogue("farm_talk")
        act = random.choice(["water_crops", "coffee_break", "fishing"])
        self.set_dialogue_text(msg, trigger_action=act, short_bubble="Dia na fazenda! 🌾")

    def _on_choice_joke(self):
        self._increment_talk()
        topic = random.choice(["joke", "work_tip"])
        msg = self._pick_dialogue(topic)
        self.set_dialogue_text(msg, trigger_action="idle", short_bubble="Haha! 😄")

    def _on_choice_compliment(self):
        self._increment_talk(heart_bonus=1)
        msg = self._pick_dialogue("compliment")
        self.set_dialogue_text(msg, trigger_action="happy_dance", short_bubble=f"❤️ {self.record.config.name} adorou!")

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
        pts = int(gift.get("points", 1))
        self.state["gifts_count"] = int(self.state.get("gifts_count", 0)) + 1
        self.state["hearts"] = min(10, int(self.state.get("hearts", 6)) + pts)
        self._save_dialogue_state()
        self._refresh_hearts_display()
        act = "coffee_break" if "Café" in gift["name"] else "happy_dance"
        self.set_dialogue_text(
            gift["reaction"],
            trigger_action=act,
            short_bubble=f"Ganhou {gift['name'][:16]}! ❤️",
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
        user_msg = self.user_input_var.get().strip()
        if not user_msg or self.is_waiting_llm:
            return
        self.user_input_var.set("")
        self._increment_talk()

        # Mostrar feedback imediato enquanto gera a resposta inteligente
        self.is_waiting_llm = True
        self.send_btn.configure(state="disabled", text="...")
        self.dialogue_lbl.configure(text=f"💭 {self.record.config.name} está pensando...")

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
        e possui um motor conversacional local rico no estilo Stardew Valley como fallback instantâneo.
        """
        char_name = self.record.config.name
        hearts = int(self.state.get("hearts", 6))
        persona = self.state.get("persona_bio", "") or f"Morador amigável e carismático do Vale do Orvalho chamado {char_name}."
        recent_history = self.state.get("history", [])[-4:]

        if is_gpt_luna_enabled():
            return generate_gpt_luna_reply(
                char_name=char_name,
                persona_bio=persona,
                hearts=hearts,
                user_msg=user_msg,
                history=recent_history,
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
        try:
            self.win.destroy()
        except Exception:
            pass
        if self.on_close:
            self.on_close()
