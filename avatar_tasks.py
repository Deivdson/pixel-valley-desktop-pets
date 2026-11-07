"""
Sistema de Tarefas de Área de Trabalho dos Avatares (Pixel Valley Desktop Pets).
Permite configurar qual avatar executa qual tarefa e inclui:
1. 🗂️ Organizar Itens e Atalhos (Área de Trabalho / Downloads) com modo Desfazer (Undo);
2. 🎣 Pescar Arquivos Grandes / Esquecidos (com classificação de raridade estilo Stardew Valley).
"""

import os
import json
import shutil
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Any, Optional, Callable, Tuple
from PIL import Image, ImageTk


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_CONFIG_PATH = os.path.join(BASE_DIR, "avatar_tasks_config.json")
UNDO_MANIFEST_PATH = os.path.join(BASE_DIR, "last_organization_undo.json")

# Paleta Stardew Valley UI
SDV_OUTER = "#5A2B11"
SDV_MID = "#B86F28"
SDV_INNER = "#E5A045"
SDV_PARCHMENT = "#F7DFB3"
SDV_PARCHMENT_DARK = "#E8C68E"
SDV_CARD = "#FFF7E4"
SDV_TEXT = "#3F1D0B"
SDV_MUTED = "#70421E"
SDV_GREEN = "#3E8E4C"
SDV_BLUE = "#3B659C"
SDV_ORANGE = "#D9822B"
SDV_RED = "#A63A2B"
SDV_PURPLE = "#5C3385"


AVAILABLE_TASKS: Dict[str, Dict[str, str]] = {
    "organize_items": {
        "id": "organize_items",
        "title": "🗂️ Organizar Itens & Atalhos",
        "short_label": "🗂️ Organizar Itens",
        "description": "Agrupa arquivos soltos da Área de Trabalho ou Downloads em pastas temáticas (com opção de Desfazer).",
        "animation": "water_crops",
        "start_speech": "🌱 Organizando os itens da fazenda...",
        "done_speech": "✨ Tudo organizado no capricho!",
    },
    "fish_large_files": {
        "id": "fish_large_files",
        "title": "🎣 Pescar Arquivos Grandes",
        "short_label": "🎣 Pescar Arquivos Grandes",
        "description": "Joga a linha de pesca em Downloads/Desktop para fisgar os arquivos mais pesados e liberar espaço.",
        "animation": "fishing",
        "start_speech": "🎣 Jogando a linha atrás de arquivos gigantes...",
        "done_speech": "🐟 Que pescaria incrível de arquivos!",
    },
}


FILE_CATEGORIES: List[Tuple[str, Tuple[str, ...]]] = [
    ("Documentos_e_PDFs", (".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xlsx", ".xls", ".csv", ".pptx", ".ppt", ".md", ".epub")),
    ("Imagens_e_Sprites", (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".ico", ".tiff", ".psd", ".xcf")),
    ("Videos_e_Audios", (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".mp3", ".wav", ".flac", ".ogg", ".m4a")),
    ("Instaladores_e_Compactados", (".zip", ".rar", ".7z", ".tar", ".gz", ".exe", ".msi", ".iso", ".apk")),
    ("Codigo_e_Dados", (".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".sql", ".ipynb", ".c", ".cpp", ".java", ".sh", ".ps1", ".yaml", ".yml")),
    ("Atalhos_da_Tela", (".lnk", ".url")),
]


def get_desktop_directory() -> str:
    """Detecta a pasta real da Área de Trabalho do usuário (incluindo OneDrive se ativo)."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "OneDrive", "Área de Trabalho"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "Área de Trabalho"),
        os.path.join(home, "Desktop"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return os.path.join(home, "Desktop")


def get_downloads_directory() -> str:
    home = os.path.expanduser("~")
    dl = os.path.join(home, "Downloads")
    return dl if os.path.isdir(dl) else home


def load_tasks_config() -> Dict[str, Any]:
    default_cfg: Dict[str, Any] = {
        "avatar_assignments": {},
        "settings": {
            "organize_target": "downloads",
            "organize_include_shortcuts": False,
            "fish_target": "downloads",
            "fish_min_size_mb": 10,
        },
    }
    if os.path.exists(TASKS_CONFIG_PATH):
        try:
            with open(TASKS_CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved.get("avatar_assignments"), dict):
                default_cfg["avatar_assignments"].update(saved["avatar_assignments"])
            if isinstance(saved.get("settings"), dict):
                default_cfg["settings"].update(saved["settings"])
        except Exception:
            pass
    return default_cfg


def save_tasks_config(cfg: Dict[str, Any]):
    try:
        with open(TASKS_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_avatar_assigned_tasks(avatar_id: str, avatar_name: str = "") -> List[str]:
    """Retorna a lista de IDs de tarefas atribuídas a um avatar específico."""
    cfg = load_tasks_config()
    assignments = cfg.get("avatar_assignments", {})
    if avatar_id in assignments:
        return list(assignments[avatar_id])

    # Padrão inicial inteligente: Deivdson já vem com ambas as tarefas habilitadas
    if "deivdson" in avatar_name.lower() or not assignments:
        return ["organize_items", "fish_large_files"]
    return ["organize_items", "fish_large_files"]


def set_avatar_assigned_tasks(avatar_id: str, task_ids: List[str]):
    cfg = load_tasks_config()
    cfg.setdefault("avatar_assignments", {})[avatar_id] = list(task_ids)
    save_tasks_config(cfg)


def format_size(num_bytes: int) -> str:
    if num_bytes >= 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 ** 3):.2f} GB"
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 ** 2):.1f} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024.0:.1f} KB"
    return f"{num_bytes} B"


def classify_file_category(filename: str, include_shortcuts: bool = False) -> Optional[str]:
    lower = filename.lower()
    if lower in ("desktop.ini", "thumbs.db", ".ds_store"):
        return None
    _, ext = os.path.splitext(lower)
    if not ext:
        return None
    if ext in (".lnk", ".url"):
        return "Atalhos_da_Tela" if include_shortcuts else None
    # Não mover o próprio atalho de execução do Stardew Pets se estiver na área de trabalho
    if "stardew" in lower and ext in (".bat", ".lnk"):
        return None
    for cat_folder, extensions in FILE_CATEGORIES:
        if ext in extensions:
            return cat_folder
    return "Outros_Arquivos"


def scan_folder_for_organization(target_mode: str, include_shortcuts: bool = False) -> List[Dict[str, Any]]:
    folders: List[Tuple[str, str]] = []
    if target_mode in ("desktop", "both"):
        folders.append(("Área de Trabalho", get_desktop_directory()))
    if target_mode in ("downloads", "both"):
        folders.append(("Downloads", get_downloads_directory()))

    items: List[Dict[str, Any]] = []
    for label, folder_path in folders:
        if not os.path.isdir(folder_path):
            continue
        try:
            for entry in sorted(os.listdir(folder_path)):
                full_path = os.path.join(folder_path, entry)
                if not os.path.isfile(full_path):
                    continue
                cat = classify_file_category(entry, include_shortcuts=include_shortcuts)
                if not cat:
                    continue
                try:
                    st = os.stat(full_path)
                    fsize = st.st_size
                except Exception:
                    fsize = 0
                dest_dir = os.path.join(folder_path, cat)
                items.append({
                    "name": entry,
                    "source_path": full_path,
                    "source_folder_label": label,
                    "base_folder": folder_path,
                    "category": cat,
                    "dest_dir": dest_dir,
                    "size_bytes": fsize,
                    "size_str": format_size(fsize),
                })
        except Exception:
            continue
    return items


def execute_organization_plan(plan_items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Move os arquivos selecionados para suas pastas de categoria e grava o manifesto de Undo.
    Retorna (quantidade_movida, bytes_totais).
    """
    moved_records: List[Dict[str, str]] = []
    total_bytes = 0

    for item in plan_items:
        src = item["source_path"]
        dest_dir = item["dest_dir"]
        if not os.path.isfile(src):
            continue
        try:
            os.makedirs(dest_dir, exist_ok=True)
            base_name = os.path.basename(src)
            dest_path = os.path.join(dest_dir, base_name)
            # Evitar sobrescrever arquivo de mesmo nome
            if os.path.exists(dest_path):
                stem, ext = os.path.splitext(base_name)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(dest_dir, f"{stem} ({counter}){ext}")
                    counter += 1
            shutil.move(src, dest_path)
            moved_records.append({"from": src, "to": dest_path})
            total_bytes += int(item.get("size_bytes", 0))
        except Exception:
            continue

    if moved_records:
        try:
            with open(UNDO_MANIFEST_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        "moves": moved_records,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception:
            pass

    return len(moved_records), total_bytes


def undo_last_organization() -> Tuple[int, str]:
    """Restaura os arquivos movidos na última organização para seus caminhos originais."""
    if not os.path.exists(UNDO_MANIFEST_PATH):
        return 0, "Nenhuma organização recente encontrada para desfazer."
    try:
        with open(UNDO_MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        moves = data.get("moves", [])
        restored = 0
        touched_dirs = set()
        for rec in reversed(moves):
            src_orig = rec.get("from", "")
            curr_path = rec.get("to", "")
            if curr_path and os.path.isfile(curr_path):
                os.makedirs(os.path.dirname(src_orig), exist_ok=True)
                shutil.move(curr_path, src_orig)
                touched_dirs.add(os.path.dirname(curr_path))
                restored += 1
        # Remover pastas de categoria que ficaram vazias
        for d in touched_dirs:
            try:
                if os.path.isdir(d) and not os.listdir(d):
                    os.rmdir(d)
            except Exception:
                pass
        os.remove(UNDO_MANIFEST_PATH)
        return restored, f"{restored} arquivo(s) voltaram exatamente para o local original!"
    except Exception as exc:
        return 0, f"Erro ao desfazer organização: {exc}"


def get_fish_rarity_badge(size_bytes: int) -> Tuple[str, str]:
    mb = size_bytes / (1024.0 * 1024.0)
    if mb >= 500:
        return "🟣 Carpa Lendária (Irídio)", "#6B2FA0"
    if mb >= 100:
        return "🟡 Dourado Real (Ouro)", "#B87A00"
    if mb >= 25:
        return "⚪ Truta Prateada (Prata)", "#3B659C"
    return "🟤 Peixe do Rio (Comum)", "#70421E"


def scan_for_large_files(target_mode: str = "downloads", min_size_mb: float = 10.0, max_results: int = 30) -> List[Dict[str, Any]]:
    """
    Vasculha Downloads e/ou Área de Trabalho (até 2 níveis de subpastas)
    em busca dos maiores arquivos ("peixes grandes").
    """
    roots: List[Tuple[str, str]] = []
    if target_mode in ("downloads", "both"):
        roots.append(("Downloads", get_downloads_directory()))
    if target_mode in ("desktop", "both"):
        roots.append(("Área de Trabalho", get_desktop_directory()))

    all_candidates: List[Dict[str, Any]] = []
    min_bytes = int(min_size_mb * 1024 * 1024)

    for label, root_dir in roots:
        if not os.path.isdir(root_dir):
            continue
        for current_root, dirs, files in os.walk(root_dir):
            # Limitar profundidade a 2 níveis e ignorar pastas de baú já arquivadas
            rel = os.path.relpath(current_root, root_dir)
            depth = 0 if rel == "." else len(rel.split(os.sep))
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "_Bau_Arquivos_Grandes" and depth < 2]

            for fname in files:
                if fname.lower() in ("desktop.ini", "thumbs.db"):
                    continue
                fpath = os.path.join(current_root, fname)
                try:
                    st = os.stat(fpath)
                    fsize = st.st_size
                    mtime = datetime.fromtimestamp(st.st_mtime).strftime("%d/%m/%Y")
                except Exception:
                    continue

                rarity_txt, rarity_color = get_fish_rarity_badge(fsize)
                all_candidates.append({
                    "name": fname,
                    "path": fpath,
                    "folder_label": label,
                    "root_dir": root_dir,
                    "size_bytes": fsize,
                    "size_str": format_size(fsize),
                    "mtime": mtime,
                    "rarity": rarity_txt,
                    "rarity_color": rarity_color,
                })

    all_candidates.sort(key=lambda x: x["size_bytes"], reverse=True)
    filtered = [c for c in all_candidates if c["size_bytes"] >= min_bytes]
    # Se houver poucos acima do limite mínimo, mostrar os Top 15 maiores arquivos encontrados
    if len(filtered) < 6:
        filtered = all_candidates[:15]
    return filtered[:max_results]


# =====================================================================
# JANELA 1: MODAL DE ORGANIZAÇÃO DE ITENS & ATALHOS
# =====================================================================
class OrganizeItemsModal:
    def __init__(
        self,
        master: tk.Misc,
        avatar_name: str,
        on_action_trigger: Optional[Callable[[str, str], None]] = None,
    ):
        self.master = master
        self.avatar_name = avatar_name
        self.on_action_trigger = on_action_trigger

        cfg = load_tasks_config()
        settings = cfg.get("settings", {})

        self.win = tk.Toplevel(master)
        self.win.title(f"🗂️ {avatar_name} — Organizador de Itens & Atalhos (Pixel Valley)")
        self.win.geometry("820x560")
        self.win.configure(bg=SDV_OUTER)
        self.win.wm_attributes("-topmost", True)

        self.target_var = tk.StringVar(value=settings.get("organize_target", "downloads"))
        self.shortcuts_var = tk.BooleanVar(value=bool(settings.get("organize_include_shortcuts", False)))
        self.detected_items: List[Dict[str, Any]] = []
        self.item_vars: List[tk.BooleanVar] = []

        if self.on_action_trigger:
            self.on_action_trigger("water_crops", f"🌱 {avatar_name} analisando arquivos...")

        self._build_ui()
        self.refresh_scan()

    def _build_ui(self):
        outer = tk.Frame(self.win, bg=SDV_OUTER, padx=6, pady=6)
        outer.pack(fill="both", expand=True)

        mid = tk.Frame(outer, bg=SDV_MID, padx=4, pady=4, bd=2, relief="raised")
        mid.pack(fill="both", expand=True)

        parchment = tk.Frame(mid, bg=SDV_PARCHMENT, padx=14, pady=12)
        parchment.pack(fill="both", expand=True)

        # Cabeçalho
        header = tk.Frame(parchment, bg="#EAD0A0", bd=1, relief="solid", padx=10, pady=6)
        header.pack(fill="x", pady=(0, 8))

        tk.Label(
            header,
            text=f"🌱 Tarefa de {self.avatar_name}: Organizar Itens & Atalhos",
            font=("Georgia", 13, "bold"),
            bg="#EAD0A0",
            fg=SDV_TEXT,
        ).pack(side="left")

        tk.Button(
            header,
            text="↩️ Desfazer Última Organização",
            command=self._on_undo_click,
            bg="#D6A868",
            fg=SDV_TEXT,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=2,
            cursor="hand2",
        ).pack(side="right")

        # Barra de Filtros / Pasta Alvo
        ctrl_bar = tk.Frame(parchment, bg=SDV_PARCHMENT_DARK, bd=1, relief="groove", padx=10, pady=6)
        ctrl_bar.pack(fill="x", pady=(0, 8))

        tk.Label(ctrl_bar, text="📂 Onde organizar:", font=("Segoe UI", 9, "bold"), bg=SDV_PARCHMENT_DARK, fg=SDV_TEXT).pack(side="left")

        for val, lbl in [("desktop", "🖥️ Área de Trabalho"), ("downloads", "📥 Pasta Downloads"), ("both", "🌟 Ambos")]:
            tk.Radiobutton(
                ctrl_bar,
                text=lbl,
                variable=self.target_var,
                value=val,
                command=self._on_filter_changed,
                bg=SDV_PARCHMENT_DARK,
                fg=SDV_TEXT,
                selectcolor="#FFF5DF",
                activebackground=SDV_PARCHMENT_DARK,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=6)

        tk.Checkbutton(
            ctrl_bar,
            text="📌 Incluir atalhos (.lnk / .url)",
            variable=self.shortcuts_var,
            command=self._on_filter_changed,
            bg=SDV_PARCHMENT_DARK,
            fg=SDV_TEXT,
            selectcolor="#FFF5DF",
            activebackground=SDV_PARCHMENT_DARK,
            font=("Segoe UI", 9),
        ).pack(side="right", padx=4)

        # Resumo de contagem
        self.summary_lbl = tk.Label(
            parchment,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg=SDV_PARCHMENT,
            fg=SDV_MUTED,
            anchor="w",
        )
        self.summary_lbl.pack(fill="x", pady=(0, 4))

        # Lista rolável de arquivos que serão organizados
        list_outer = tk.Frame(parchment, bg="#7A4419", padx=2, pady=2)
        list_outer.pack(fill="both", expand=True, pady=(0, 10))

        self.canvas = tk.Canvas(list_outer, bg=SDV_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_outer, orient="vertical", command=self.canvas.yview)
        self.list_frame = tk.Frame(self.canvas, bg=SDV_CARD, padx=8, pady=6)

        self.list_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Rodapé de Ações
        footer = tk.Frame(parchment, bg=SDV_PARCHMENT)
        footer.pack(fill="x")

        tk.Button(
            footer,
            text="☑️ Marcar Todos",
            command=lambda: self._set_all_checks(True),
            bg="#DFB77C",
            fg=SDV_TEXT,
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=4,
            cursor="hand2",
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            footer,
            text="⬜ Desmarcar Todos",
            command=lambda: self._set_all_checks(False),
            bg="#DFB77C",
            fg=SDV_TEXT,
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=4,
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            footer,
            text="✖ Fechar",
            command=self.win.destroy,
            bg=SDV_RED,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            cursor="hand2",
        ).pack(side="right")

        self.run_btn = tk.Button(
            footer,
            text=f"✅ Organizar Selecionados com {self.avatar_name}!",
            command=self._execute_selected,
            bg=SDV_GREEN,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=5,
            cursor="hand2",
        )
        self.run_btn.pack(side="right", padx=8)

    def _on_filter_changed(self):
        cfg = load_tasks_config()
        cfg.setdefault("settings", {})["organize_target"] = self.target_var.get()
        cfg.setdefault("settings", {})["organize_include_shortcuts"] = bool(self.shortcuts_var.get())
        save_tasks_config(cfg)
        self.refresh_scan()

    def _set_all_checks(self, state: bool):
        for v in self.item_vars:
            v.set(state)

    def refresh_scan(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.item_vars.clear()

        self.detected_items = scan_folder_for_organization(
            self.target_var.get(),
            include_shortcuts=self.shortcuts_var.get(),
        )

        if not self.detected_items:
            self.summary_lbl.configure(text="✨ Nenhum arquivo solto pendente de organização nesta pasta!")
            tk.Label(
                self.list_frame,
                text="🌾 Tudo limpo por aqui! Todos os arquivos já estão organizados em pastas.",
                font=("Georgia", 11),
                bg=SDV_CARD,
                fg=SDV_MUTED,
                pady=30,
            ).pack(fill="x")
            return

        # Contagem por categoria
        cat_counts: Dict[str, int] = {}
        total_sz = 0
        for it in self.detected_items:
            cat_counts[it["category"]] = cat_counts.get(it["category"], 0) + 1
            total_sz += it["size_bytes"]

        cat_summary = "  •  ".join([f"{k}: {v}" for k, v in cat_counts.items()])
        self.summary_lbl.configure(
            text=f"📦 {len(self.detected_items)} itens encontrados ({format_size(total_sz)})   |   {cat_summary}"
        )

        for idx, item in enumerate(self.detected_items):
            var = tk.BooleanVar(value=True)
            self.item_vars.append(var)
            row_bg = "#FFFDF6" if idx % 2 == 0 else "#F7EBD2"
            row = tk.Frame(self.list_frame, bg=row_bg, padx=6, pady=3)
            row.pack(fill="x", pady=1)

            tk.Checkbutton(
                row,
                variable=var,
                bg=row_bg,
                activebackground=row_bg,
            ).pack(side="left")

            tk.Label(
                row,
                text=f"[{item['source_folder_label']}]  {item['name'][:46]}",
                font=("Segoe UI", 9, "bold"),
                bg=row_bg,
                fg=SDV_TEXT,
                width=48,
                anchor="w",
            ).pack(side="left", padx=(2, 8))

            tk.Label(
                row,
                text=f"➜ 📁 {item['category']}",
                font=("Segoe UI", 9, "bold"),
                bg=row_bg,
                fg=SDV_GREEN,
                width=26,
                anchor="w",
            ).pack(side="left", padx=4)

            tk.Label(
                row,
                text=item["size_str"],
                font=("Segoe UI", 8),
                bg=row_bg,
                fg=SDV_MUTED,
                anchor="e",
            ).pack(side="right", padx=4)

    def _execute_selected(self):
        chosen = [
            item for item, var in zip(self.detected_items, self.item_vars)
            if var.get()
        ]
        if not chosen:
            messagebox.showinfo("Nenhum Item", "Marque pelo menos um arquivo para organizar!", parent=self.win)
            return

        moved_count, total_bytes = execute_organization_plan(chosen)
        if self.on_action_trigger:
            self.on_action_trigger(
                "happy_dance",
                f"✨ {moved_count} itens organizados ({format_size(total_bytes)})!",
            )
        messagebox.showinfo(
            "Colheita Organizada! 🌾✨",
            f"{self.avatar_name} organizou {moved_count} arquivo(s) ({format_size(total_bytes)}) em pastas temáticas!\n\n"
            "Dica: Se quiser reverter, basta clicar em '↩️ Desfazer Última Organização' no topo.",
            parent=self.win,
        )
        self.refresh_scan()

    def _on_undo_click(self):
        count, msg = undo_last_organization()
        if count > 0 and self.on_action_trigger:
            self.on_action_trigger("idle", f"↩️ {count} arquivos restaurados!")
        messagebox.showinfo("Desfazer Organização", msg, parent=self.win)
        self.refresh_scan()


# =====================================================================
# JANELA 2: MODAL DE PESCAR ARQUIVOS GRANDES ("CESTO DE PESCA")
# =====================================================================
class FishLargeFilesModal:
    def __init__(
        self,
        master: tk.Misc,
        avatar_name: str,
        on_action_trigger: Optional[Callable[[str, str], None]] = None,
    ):
        self.master = master
        self.avatar_name = avatar_name
        self.on_action_trigger = on_action_trigger

        cfg = load_tasks_config()
        settings = cfg.get("settings", {})

        self.win = tk.Toplevel(master)
        self.win.title(f"🎣 {avatar_name} — Pescador de Arquivos Grandes (Pixel Valley)")
        self.win.geometry("860x570")
        self.win.configure(bg=SDV_OUTER)
        self.win.wm_attributes("-topmost", True)

        self.target_var = tk.StringVar(value=settings.get("fish_target", "downloads"))
        self.min_mb_var = tk.IntVar(value=int(settings.get("fish_min_size_mb", 10)))
        self.fished_files: List[Dict[str, Any]] = []
        self.file_vars: List[tk.BooleanVar] = []

        if self.on_action_trigger:
            self.on_action_trigger("fishing", f"🎣 {avatar_name} pescando arquivos grandes...")

        self._build_ui()
        self.cast_fishing_line()

    def _build_ui(self):
        outer = tk.Frame(self.win, bg=SDV_OUTER, padx=6, pady=6)
        outer.pack(fill="both", expand=True)

        mid = tk.Frame(outer, bg=SDV_MID, padx=4, pady=4, bd=2, relief="raised")
        mid.pack(fill="both", expand=True)

        parchment = tk.Frame(mid, bg=SDV_PARCHMENT, padx=14, pady=12)
        parchment.pack(fill="both", expand=True)

        # Cabeçalho
        header = tk.Frame(parchment, bg="#EAD0A0", bd=1, relief="solid", padx=10, pady=6)
        header.pack(fill="x", pady=(0, 8))

        tk.Label(
            header,
            text=f"🎣 Pescaria de {self.avatar_name}: Caçador de Arquivos Pesados",
            font=("Georgia", 13, "bold"),
            bg="#EAD0A0",
            fg=SDV_TEXT,
        ).pack(side="left")

        tk.Button(
            header,
            text="🎣 Lançar Linha Novamente",
            command=self.cast_fishing_line,
            bg=SDV_BLUE,
            fg="white",
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=2,
            cursor="hand2",
        ).pack(side="right")

        # Controles de Pesca
        ctrl = tk.Frame(parchment, bg=SDV_PARCHMENT_DARK, bd=1, relief="groove", padx=10, pady=6)
        ctrl.pack(fill="x", pady=(0, 8))

        tk.Label(ctrl, text="🌊 Rio de Pesca:", font=("Segoe UI", 9, "bold"), bg=SDV_PARCHMENT_DARK, fg=SDV_TEXT).pack(side="left")
        for val, lbl in [("downloads", "📥 Pasta Downloads"), ("desktop", "🖥️ Área de Trabalho"), ("both", "🌊 Ambos")]:
            tk.Radiobutton(
                ctrl,
                text=lbl,
                variable=self.target_var,
                value=val,
                command=self._on_settings_change,
                bg=SDV_PARCHMENT_DARK,
                fg=SDV_TEXT,
                selectcolor="#FFF5DF",
                activebackground=SDV_PARCHMENT_DARK,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=6)

        tk.Label(ctrl, text="Peso Mínimo (MB):", font=("Segoe UI", 9, "bold"), bg=SDV_PARCHMENT_DARK, fg=SDV_TEXT).pack(side="left", padx=(14, 4))
        spin = tk.Spinbox(
            ctrl,
            from_=1,
            to=2000,
            textvariable=self.min_mb_var,
            width=6,
            font=("Segoe UI", 9, "bold"),
            command=self._on_settings_change,
        )
        spin.pack(side="left")
        spin.bind("<Return>", lambda e: self._on_settings_change())

        self.summary_lbl = tk.Label(
            parchment,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg=SDV_PARCHMENT,
            fg=SDV_MUTED,
            anchor="w",
        )
        self.summary_lbl.pack(fill="x", pady=(0, 4))

        # Lista rolável dos "Peixes" (Arquivos Grandes)
        list_outer = tk.Frame(parchment, bg="#7A4419", padx=2, pady=2)
        list_outer.pack(fill="both", expand=True, pady=(0, 10))

        self.canvas = tk.Canvas(list_outer, bg=SDV_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_outer, orient="vertical", command=self.canvas.yview)
        self.list_frame = tk.Frame(self.canvas, bg=SDV_CARD, padx=8, pady=6)

        self.list_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Rodapé de Ações
        footer = tk.Frame(parchment, bg=SDV_PARCHMENT)
        footer.pack(fill="x")

        tk.Button(
            footer,
            text="📦 Mover Selecionados p/ '_Bau_Arquivos_Grandes'",
            command=self._archive_selected_fish,
            bg=SDV_GREEN,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            footer,
            text="📂 Abrir Local no Explorer",
            command=self._reveal_first_selected,
            bg=SDV_BLUE,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            footer,
            text="🗑️ Excluir Selecionados",
            command=self._delete_selected_fish,
            bg=SDV_RED,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            footer,
            text="✖ Fechar",
            command=self.win.destroy,
            bg="#7A4419",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=5,
            cursor="hand2",
        ).pack(side="right")

    def _on_settings_change(self):
        cfg = load_tasks_config()
        cfg.setdefault("settings", {})["fish_target"] = self.target_var.get()
        try:
            mb = max(1, int(self.min_mb_var.get()))
        except Exception:
            mb = 10
        cfg.setdefault("settings", {})["fish_min_size_mb"] = mb
        save_tasks_config(cfg)
        self.cast_fishing_line()

    def cast_fishing_line(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.file_vars.clear()

        if self.on_action_trigger:
            self.on_action_trigger("fishing", f"🎣 {self.avatar_name} lançou a linha!")

        try:
            min_mb = float(self.min_mb_var.get())
        except Exception:
            min_mb = 10.0

        self.fished_files = scan_for_large_files(self.target_var.get(), min_size_mb=min_mb)
        total_bytes = sum(f["size_bytes"] for f in self.fished_files)
        self.summary_lbl.configure(
            text=f"🐟 {len(self.fished_files)} arquivo(s) fisgado(s)  •  Peso total no cesto: {format_size(total_bytes)}"
        )

        if not self.fished_files:
            tk.Label(
                self.list_frame,
                text="🌊 A água está calma! Nenhum arquivo pesado encontrado com esse filtro.",
                font=("Georgia", 11),
                bg=SDV_CARD,
                fg=SDV_MUTED,
                pady=30,
            ).pack(fill="x")
            return

        for idx, fish in enumerate(self.fished_files):
            var = tk.BooleanVar(value=False)
            self.file_vars.append(var)
            row_bg = "#FFFDF6" if idx % 2 == 0 else "#F7EBD2"
            row = tk.Frame(self.list_frame, bg=row_bg, padx=6, pady=4)
            row.pack(fill="x", pady=1)

            tk.Checkbutton(row, variable=var, bg=row_bg, activebackground=row_bg).pack(side="left")

            tk.Label(
                row,
                text=fish["size_str"],
                font=("Segoe UI", 9, "bold"),
                bg="#EAD0A0",
                fg=SDV_TEXT,
                width=11,
                padx=4,
            ).pack(side="left", padx=(2, 8))

            tk.Label(
                row,
                text=fish["rarity"],
                font=("Segoe UI", 8, "bold"),
                bg=row_bg,
                fg=fish["rarity_color"],
                width=23,
                anchor="w",
            ).pack(side="left", padx=(0, 6))

            tk.Label(
                row,
                text=fish["name"][:44],
                font=("Segoe UI", 9, "bold"),
                bg=row_bg,
                fg=SDV_TEXT,
                width=40,
                anchor="w",
            ).pack(side="left", padx=(0, 6))

            tk.Label(
                row,
                text=f"{fish['folder_label']} • {fish['mtime']}",
                font=("Segoe UI", 8),
                bg=row_bg,
                fg=SDV_MUTED,
                anchor="e",
            ).pack(side="right", padx=4)

    def _get_selected_fish(self) -> List[Dict[str, Any]]:
        return [f for f, v in zip(self.fished_files, self.file_vars) if v.get()]

    def _archive_selected_fish(self):
        selected = self._get_selected_fish()
        if not selected:
            messagebox.showinfo("Cesto Vazio", "Marque pelo menos um arquivo pescado na lista!", parent=self.win)
            return

        moved = 0
        total_b = 0
        for f in selected:
            src = f["path"]
            if not os.path.isfile(src):
                continue
            chest_dir = os.path.join(f["root_dir"], "_Bau_Arquivos_Grandes")
            os.makedirs(chest_dir, exist_ok=True)
            dest = os.path.join(chest_dir, os.path.basename(src))
            if os.path.exists(dest):
                stem, ext = os.path.splitext(os.path.basename(src))
                dest = os.path.join(chest_dir, f"{stem}_pescado{ext}")
            try:
                shutil.move(src, dest)
                moved += 1
                total_b += f["size_bytes"]
            except Exception:
                continue

        if self.on_action_trigger:
            self.on_action_trigger("happy_dance", f"🐟 Guardou {format_size(total_b)} no Baú!")
        messagebox.showinfo(
            "Guardado no Baú! 📦🐟",
            f"{self.avatar_name} guardou {moved} arquivo(s) pesado(s) ({format_size(total_b)}) na pasta '_Bau_Arquivos_Grandes'!",
            parent=self.win,
        )
        self.cast_fishing_line()

    def _reveal_first_selected(self):
        selected = self._get_selected_fish()
        target = selected[0] if selected else (self.fished_files[0] if self.fished_files else None)
        if not target:
            return
        fpath = os.path.normpath(target["path"])
        if os.path.exists(fpath):
            subprocess.Popen(["explorer", "/select,", fpath])

    def _delete_selected_fish(self):
        selected = self._get_selected_fish()
        if not selected:
            messagebox.showinfo("Seleção Vazia", "Marque os arquivos que deseja remover!", parent=self.win)
            return
        total_b = sum(f["size_bytes"] for f in selected)
        confirm = messagebox.askyesno(
            "Confirmar Exclusão",
            f"Tem certeza que deseja excluir permanentemente {len(selected)} arquivo(s) ({format_size(total_b)})?",
            parent=self.win,
        )
        if not confirm:
            return
        deleted = 0
        for f in selected:
            try:
                if os.path.isfile(f["path"]):
                    os.remove(f["path"])
                    deleted += 1
            except Exception:
                continue
        if self.on_action_trigger:
            self.on_action_trigger("happy_dance", f"🗑️ Liberou {format_size(total_b)}!")
        messagebox.showinfo("Espaço Liberado!", f"{deleted} arquivo(s) removido(s) ({format_size(total_b)} liberados)!", parent=self.win)
        self.cast_fishing_line()


# =====================================================================
# JANELA 3: CENTRAL DE CONFIGURAÇÃO (QUAL AVATAR EXECUTA QUAL TAREFA)
# =====================================================================
def open_avatar_tasks_manager_modal(
    master: tk.Misc,
    avatars: List[Any],
    on_trigger_avatar_task: Callable[[Any, str], None],
):
    """
    Abre a Central de Tarefas onde o usuário escolhe qual avatar executa qual tarefa
    e também pode disparar imediatamente qualquer tarefa com o avatar escolhido.
    """
    win = tk.Toplevel(master)
    win.title("🛠️ Central de Tarefas & Funções dos Avatares — Pixel Valley")
    win.geometry("860x540")
    win.configure(bg=SDV_OUTER)
    win.wm_attributes("-topmost", True)

    outer = tk.Frame(win, bg=SDV_OUTER, padx=6, pady=6)
    outer.pack(fill="both", expand=True)

    mid = tk.Frame(outer, bg=SDV_MID, padx=4, pady=4, bd=2, relief="raised")
    mid.pack(fill="both", expand=True)

    parchment = tk.Frame(mid, bg=SDV_PARCHMENT, padx=14, pady=12)
    parchment.pack(fill="both", expand=True)

    header = tk.Frame(parchment, bg="#EAD0A0", bd=1, relief="solid", padx=12, pady=8)
    header.pack(fill="x", pady=(0, 10))

    tk.Label(
        header,
        text="🛠️ Configurar Qual Avatar Executa Qual Tarefa na Área de Trabalho",
        font=("Georgia", 13, "bold"),
        bg="#EAD0A0",
        fg=SDV_TEXT,
    ).pack(anchor="w")

    tk.Label(
        header,
        text="Marque abaixo as funções de cada morador. As tarefas marcadas aparecem no menu de botão direito e na Caixa de Diálogo do avatar!",
        font=("Segoe UI", 9),
        bg="#EAD0A0",
        fg=SDV_MUTED,
    ).pack(anchor="w", pady=(2, 0))

    list_outer = tk.Frame(parchment, bg="#7A4419", padx=2, pady=2)
    list_outer.pack(fill="both", expand=True, pady=(0, 10))

    canvas = tk.Canvas(list_outer, bg=SDV_CARD, highlightthickness=0)
    scrollbar = ttk.Scrollbar(list_outer, orient="vertical", command=canvas.yview)
    rows_frame = tk.Frame(canvas, bg=SDV_CARD, padx=10, pady=8)

    rows_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=rows_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Manter referências de imagens para não serem coletadas pelo GC
    win._portrait_refs = []  # type: ignore
    check_matrix: Dict[str, Dict[str, tk.BooleanVar]] = {}

    for idx, rec in enumerate(avatars):
        aid = rec.avatar_id
        aname = rec.config.name
        assigned = set(get_avatar_assigned_tasks(aid, aname))
        check_matrix[aid] = {}

        card_bg = "#FFFDF6" if idx % 2 == 0 else "#F7EBD2"
        card = tk.Frame(rows_frame, bg=card_bg, bd=1, relief="groove", padx=10, pady=8)
        card.pack(fill="x", pady=4)

        # Mini retrato
        try:
            p_img = rec.load_portrait().resize((48, 48), Image.Resampling.NEAREST)
            p_tk = ImageTk.PhotoImage(p_img)
            win._portrait_refs.append(p_tk)  # type: ignore
            tk.Label(card, image=p_tk, bg=SDV_OUTER, bd=2, relief="sunken").pack(side="left", padx=(0, 10))
        except Exception:
            pass

        info_col = tk.Frame(card, bg=card_bg)
        info_col.pack(side="left", fill="x", expand=True)

        tk.Label(
            info_col,
            text=f"🌾 {aname}",
            font=("Georgia", 11, "bold"),
            bg=card_bg,
            fg=SDV_TEXT,
            anchor="w",
        ).pack(fill="x")

        tasks_row = tk.Frame(info_col, bg=card_bg)
        tasks_row.pack(fill="x", pady=(4, 0))

        def _make_save_cb(avatar_rec=rec):
            def _cb():
                selected_ids = [
                    tid for tid, tvar in check_matrix[avatar_rec.avatar_id].items()
                    if tvar.get()
                ]
                set_avatar_assigned_tasks(avatar_rec.avatar_id, selected_ids)
            return _cb

        for task_id, tinfo in AVAILABLE_TASKS.items():
            var = tk.BooleanVar(value=(task_id in assigned))
            check_matrix[aid][task_id] = var
            tk.Checkbutton(
                tasks_row,
                text=tinfo["short_label"],
                variable=var,
                command=_make_save_cb(rec),
                bg=card_bg,
                fg=SDV_TEXT,
                selectcolor="#FFF5DF",
                activebackground=card_bg,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=(0, 12))

        # Botões para disparar imediatamente com este avatar
        actions_col = tk.Frame(card, bg=card_bg)
        actions_col.pack(side="right")

        tk.Button(
            actions_col,
            text="🗂️ Organizar Agora",
            command=lambda r=rec: on_trigger_avatar_task(r, "organize_items"),
            bg=SDV_GREEN,
            fg="white",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=3,
            cursor="hand2",
        ).pack(side="left", padx=3)

        tk.Button(
            actions_col,
            text="🎣 Pescar Arquivos",
            command=lambda r=rec: on_trigger_avatar_task(r, "fish_large_files"),
            bg=SDV_BLUE,
            fg="white",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=3,
            cursor="hand2",
        ).pack(side="left", padx=3)

    footer = tk.Frame(parchment, bg=SDV_PARCHMENT)
    footer.pack(fill="x")

    tk.Label(
        footer,
        text="💡 As alterações nas caixas de seleção são salvas automaticamente!",
        font=("Segoe UI", 9, "italic"),
        bg=SDV_PARCHMENT,
        fg=SDV_MUTED,
    ).pack(side="left")

    tk.Button(
        footer,
        text="✅ Concluído",
        command=win.destroy,
        bg=SDV_GREEN,
        fg="white",
        font=("Segoe UI", 9, "bold"),
        padx=14,
        pady=4,
        cursor="hand2",
    ).pack(side="right")
