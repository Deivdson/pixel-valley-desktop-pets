"""
Gerenciador da Biblioteca de Avatares (persistência local de bonequinhos,
retratos, fotos de origem e exportação de Sprite Sheets).
"""

import os
import json
import uuid
import shutil
from typing import List, Optional
from PIL import Image
from photo_analyzer import AvatarConfig
from sprite_generator import generate_full_spritesheet, generate_modular_portrait


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AVATARS_DIR = os.path.join(BASE_DIR, "avatars")


class AvatarRecord:
    def __init__(
        self,
        avatar_id: str,
        config: AvatarConfig,
        folder_path: str,
        has_photo_portrait: bool = False,
    ):
        self.avatar_id = avatar_id
        self.config = config
        self.folder_path = folder_path
        self.has_photo_portrait = has_photo_portrait

    @property
    def spritesheet_path(self) -> str:
        return os.path.join(self.folder_path, "spritesheet.png")

    @property
    def portrait_path(self) -> str:
        return os.path.join(self.folder_path, "portrait.png")

    @property
    def photo_portrait_path(self) -> str:
        return os.path.join(self.folder_path, "photo_portrait.png")

    @property
    def metadata_path(self) -> str:
        return os.path.join(self.folder_path, "avatar.json")

    def load_spritesheet(self) -> Image.Image:
        if os.path.exists(self.spritesheet_path):
            return Image.open(self.spritesheet_path).convert("RGBA")
        sheet = generate_full_spritesheet(self.config)
        sheet.save(self.spritesheet_path)
        return sheet

    def load_portrait(self) -> Image.Image:
        if self.has_photo_portrait and os.path.exists(self.photo_portrait_path):
            return Image.open(self.photo_portrait_path).convert("RGBA")
        if os.path.exists(self.portrait_path):
            return Image.open(self.portrait_path).convert("RGBA")
        portrait = generate_modular_portrait(self.config)
        portrait.save(self.portrait_path)
        return portrait


class AvatarLibrary:
    def __init__(self, avatars_dir: str = AVATARS_DIR):
        self.avatars_dir = avatars_dir
        os.makedirs(self.avatars_dir, exist_ok=True)
        self._ensure_starter_avatars()

    def _ensure_starter_avatars(self):
        """Cria avatares iniciais de demonstração caso a biblioteca esteja vazia."""
        existing = [
            d for d in os.listdir(self.avatars_dir)
            if os.path.isdir(os.path.join(self.avatars_dir, d))
        ]
        if existing:
            return

        starters = [
            AvatarConfig(
                name="Fazendeiro Leo",
                is_male=True,
                skin_index=0,
                skin_color="#F9AE89",
                hair_index=0,
                hair_color="#824C27",
                hair_style="curto",
                eye_color="#462C1B",
                accessory_index=-1,
                beard_style="sem_barba",
                glasses_style="nenhum",
                shirt_index=0,
                outfit_style="jardineira",
                shirt_color="#C43B3B",
                pants_index=0,
                pants_color="#3B659C",
                hat_style="nenhum",
                scale=4,
            ),
            AvatarConfig(
                name="Abigail Dev",
                is_male=False,
                skin_index=1,
                skin_color="#F5C6A5",
                hair_index=16,
                hair_color="#8647A8",
                hair_style="longo",
                eye_color="#3F8C4F",
                accessory_index=10,
                beard_style="sem_barba",
                glasses_style="redondo",
                shirt_index=18,
                outfit_style="jaqueta",
                shirt_color="#3B659C",
                pants_index=0,
                pants_color="#2E2E38",
                hat_style="flor",
                scale=4,
            ),
            AvatarConfig(
                name="Barba Lenhador",
                is_male=True,
                skin_index=3,
                skin_color="#D4875E",
                hair_index=5,
                hair_color="#322218",
                hair_style="topete",
                eye_color="#462C1B",
                accessory_index=0,
                beard_style="barba_cheia",
                glasses_style="quadrado",
                shirt_index=12,
                outfit_style="xadrez",
                shirt_color="#3E8E4C",
                pants_index=0,
                pants_color="#8C583A",
                hat_style="nenhum",
                scale=4,
            ),
        ]
        for cfg in starters:
            self.save_avatar(cfg)

    def regenerate_all_sprites(self):
        """Regenera todas as sprites e retratos modulares da biblioteca com o renderizador oficial."""
        for rec in self.list_avatars():
            self.save_avatar(rec.config, avatar_id=rec.avatar_id)

    def list_avatars(self) -> List[AvatarRecord]:
        records: List[AvatarRecord] = []
        if not os.path.exists(self.avatars_dir):
            return records

        for entry in sorted(os.listdir(self.avatars_dir)):
            folder = os.path.join(self.avatars_dir, entry)
            meta_file = os.path.join(folder, "avatar.json")
            if os.path.isdir(folder) and os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    cfg = AvatarConfig.from_dict(data.get("config", {}))
                    has_photo = bool(data.get("has_photo_portrait", False))
                    records.append(AvatarRecord(
                        avatar_id=data.get("id", entry),
                        config=cfg,
                        folder_path=folder,
                        has_photo_portrait=has_photo,
                    ))
                except Exception:
                    continue
        return records

    def save_avatar(
        self,
        config: AvatarConfig,
        photo_portrait: Optional[Image.Image] = None,
        source_photo_path: Optional[str] = None,
        avatar_id: Optional[str] = None,
    ) -> AvatarRecord:
        if not avatar_id:
            avatar_id = str(uuid.uuid4())[:8]

        folder = os.path.join(self.avatars_dir, avatar_id)
        os.makedirs(folder, exist_ok=True)

        sheet = generate_full_spritesheet(config)
        sheet.save(os.path.join(folder, "spritesheet.png"))

        mod_portrait = generate_modular_portrait(config)
        mod_portrait.save(os.path.join(folder, "portrait.png"))

        has_photo = False
        if photo_portrait is not None:
            photo_portrait.save(os.path.join(folder, "photo_portrait.png"))
            has_photo = True
        elif os.path.exists(os.path.join(folder, "photo_portrait.png")):
            has_photo = True

        if source_photo_path and os.path.exists(source_photo_path):
            try:
                ext = os.path.splitext(source_photo_path)[1].lower() or ".png"
                shutil.copy2(source_photo_path, os.path.join(folder, f"source{ext}"))
            except Exception:
                pass

        meta = {
            "id": avatar_id,
            "config": config.to_dict(),
            "has_photo_portrait": has_photo,
            "format": "stardew-desktop-pet-v2-vanilla-layers",
            "cell_width": 24,
            "cell_height": 36,
            "columns": 4,
            "rows": 8,
        }
        with open(os.path.join(folder, "avatar.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return AvatarRecord(avatar_id, config, folder, has_photo_portrait=has_photo)

    def delete_avatar(self, avatar_id: str) -> bool:
        folder = os.path.join(self.avatars_dir, avatar_id)
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)
            return True
        return False
