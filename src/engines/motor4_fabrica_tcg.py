"""Motor 4: Fábrica de Cartas TCG e RPG (Studio Kustom Engine).

Responsável pela composição paramétrica em camadas de cartas colecionáveis, proxies
e baralhos de RPG, atendendo aos formatos Standard (Pokémon, Magic, One Piece) e
Japonês (Yu-Gi-Oh!), com tipografia nítida e gabaritos milimétricos a 300 DPI.

Franquias Homologadas:
- Pokémon TCG: HP, Energias, Ataques com dano/custo, Fraqueza, Resistência e Recuo.
- Magic: The Gathering: Custo de mana, Tipo, Caixa de texto, Poder/Resistência.
- One Piece Card Game: Custo, Atributo, Poder, Efeito, Trigger.
- Ordem Paranormal RPG: Rituais/Itens, Elemento (Sangue, Morte, Conhecimento, Energia, Medo), Círculo, PE.
- Generic RPG / Custom: Título, Atributos flexíveis e descrição.
"""

from __future__ import annotations
import os
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pydantic import BaseModel, Field

from src.core.presets import (
    ProductPreset,
    get_product_preset,
    DEFAULT_DPI,
)

# ---------------------------------------------------------------------------
# Schemas Formais Pydantic v2
# ---------------------------------------------------------------------------

class AttackSpec(BaseModel):
    name: str
    cost: str = ""
    damage: str = ""
    effect: str = ""


class PokemonCardSpec(BaseModel):
    name: str
    hp: int
    energy_type: str = "Colorless"  # Fire, Water, Grass, Lightning, Psychic, Fighting, Darkness, Metal, Dragon, Colorless
    attacks: List[AttackSpec] = Field(default_factory=list)
    weakness: Optional[str] = None
    resistance: Optional[str] = None
    retreat_cost: int = 1
    illustrator: str = "Studio Kustom"
    collection_number: str = "001/100"
    art_path: Optional[str] = None


class MagicCardSpec(BaseModel):
    name: str
    mana_cost: str = "{1}"
    card_type: str = "Criatura"
    text_box: str = ""
    power_toughness: Optional[str] = None  # Ex: "4/4"
    frame_color: str = "Blue"  # White, Blue, Black, Red, Green, Multi, Artifact, Land
    illustrator: str = "Studio Kustom"
    art_path: Optional[str] = None


class OnePieceCardSpec(BaseModel):
    name: str
    cost: int = 1
    attribute: str = "Golpe"  # Golpe, Corte, Tiro, Especial
    power: int = 1000
    effect: str = ""
    trigger: Optional[str] = None
    color: str = "Red"  # Red, Green, Blue, Purple, Black, Yellow
    art_path: Optional[str] = None


class OrdemParanormalCardSpec(BaseModel):
    name: str
    element: str = "Sangue"  # Sangue, Morte, Conhecimento, Energia, Medo
    circle: int = 1
    pe_cost: int = 1
    effect: str = ""
    range_desc: str = "Curto"
    duration: str = "Instantânea"
    art_path: Optional[str] = None


class GenericCardSpec(BaseModel):
    title: str
    subtitle: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    theme_color: str = "#2B2D42"
    art_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Gerenciador de Fontes do Chão de Fábrica
# ---------------------------------------------------------------------------

class FontManager:
    """Localiza fontes oficiais da Studio Kustom (Montserrat, RetroByte) com fallback gracioso."""

    @classmethod
    def get_font_paths(cls) -> List[Path]:
        candidates: List[Path] = []
        env_font_dir = os.getenv("FONTS_DIR")
        if env_font_dir:
            candidates.append(Path(env_font_dir))

        env_studio_dir = os.getenv("STUDIO_KUSTOM_DATA_DIR")
        if env_studio_dir:
            candidates.append(
                Path(env_studio_dir) / "02 - Design e Marca" / "Design de Marca" / "fontes"
            )

        # Caminho relativo padrão ou local
        candidates.append(Path("assets/fonts"))
        return candidates

    @classmethod
    def load_font(cls, font_name: str, size: int) -> ImageFont.ImageFont:
        for folder in cls.get_font_paths():
            # Busca direta
            direct = folder / font_name
            if direct.exists():
                try:
                    return ImageFont.truetype(str(direct), size)
                except Exception:
                    pass

            # Busca recursiva no diretório
            if folder.exists():
                for f in folder.rglob("*.ttf"):
                    if font_name.lower() in f.name.lower():
                        try:
                            return ImageFont.truetype(str(f), size)
                        except Exception:
                            pass

        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Motor Gráfico de Composição de Cartas
# ---------------------------------------------------------------------------

class TCGFactoryEngine:
    """Fábrica gráfica de geração de cartas TCG e RPG a 300 DPI."""

    COLOR_PALETTES = {
        # Pokémon
        "pokemon": {
            "Fire": (226, 66, 66),
            "Water": (46, 134, 222),
            "Grass": (46, 204, 113),
            "Lightning": (241, 196, 15),
            "Psychic": (155, 89, 182),
            "Fighting": (175, 96, 26),
            "Darkness": (44, 62, 80),
            "Metal": (149, 165, 166),
            "Dragon": (192, 57, 43),
            "Colorless": (236, 240, 241),
        },
        # Magic
        "magic": {
            "White": (245, 245, 240),
            "Blue": (14, 104, 171),
            "Black": (33, 33, 33),
            "Red": (211, 32, 42),
            "Green": (0, 115, 62),
            "Multi": (216, 176, 74),
            "Artifact": (160, 162, 167),
            "Land": (163, 130, 89),
        },
        # One Piece
        "one_piece": {
            "Red": (217, 30, 36),
            "Green": (14, 158, 74),
            "Blue": (30, 112, 186),
            "Purple": (111, 44, 145),
            "Black": (30, 30, 30),
            "Yellow": (242, 182, 0),
        },
        # Ordem Paranormal
        "ordem": {
            "Sangue": (139, 0, 0),
            "Morte": (20, 20, 20),
            "Conhecimento": (212, 172, 13),
            "Energia": (125, 60, 152),
            "Medo": (240, 240, 240),
        },
    }

    def __init__(self, dpi: int = DEFAULT_DPI):
        self.dpi = dpi

    def _create_base_card(self, product_preset: ProductPreset, bg_color: Tuple[int, int, int]) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
        w, h = product_preset.trim_size_px(self.dpi)
        img = Image.new("RGB", (w, h), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)

        # Moldura externa Chanfrada
        border_margin = int(12 * (self.dpi / 300))
        draw.rounded_rectangle(
            [border_margin, border_margin, w - border_margin, h - border_margin],
            radius=int(24 * (self.dpi / 300)),
            fill=bg_color,
            outline=(240, 240, 240),
            width=int(4 * (self.dpi / 300)),
        )

        # Moldura interna decorativa
        inner_m = border_margin + int(14 * (self.dpi / 300))
        draw.rounded_rectangle(
            [inner_m, inner_m, w - inner_m, h - inner_m],
            radius=int(16 * (self.dpi / 300)),
            outline=(20, 20, 20),
            width=int(2 * (self.dpi / 300)),
        )

        return img, draw

    def _paste_art_window(
        self,
        base_img: Image.Image,
        art_source: Optional[Union[Image.Image, Path, str]],
        rect: Tuple[int, int, int, int],
    ) -> None:
        """Cola ou gera a arte central dentro da janela retangular."""
        x1, y1, x2, y2 = rect
        win_w = x2 - x1
        win_h = y2 - y1

        if art_source is not None:
            if isinstance(art_source, (str, Path)):
                if Path(art_source).exists():
                    art = Image.open(art_source).convert("RGB")
                else:
                    art = None
            elif isinstance(art_source, Image.Image):
                art = art_source.convert("RGB")
            else:
                art = None

            if art is not None:
                # Resize proporcional com crop central
                fitted = ImageOps.fit(art, (win_w, win_h), method=Image.Resampling.LANCZOS)
                base_img.paste(fitted, (x1, y1))
                return

        # Fallback artístico gerado proceduralmente
        art_placeholder = Image.new("RGB", (win_w, win_h), color=(35, 45, 60))
        draw_p = ImageDraw.Draw(art_placeholder)
        draw_p.rectangle([10, 10, win_w - 10, win_h - 10], outline=(80, 100, 130), width=2)
        font = FontManager.load_font("Montserrat-Bold.ttf", 28)
        draw_p.text((win_w // 2, win_h // 2), "ARTE CENTRAL", fill=(180, 200, 220), font=font, anchor="mm")
        base_img.paste(art_placeholder, (x1, y1))

    # -----------------------------------------------------------------------
    # Geradores Específicos por Franquia
    # -----------------------------------------------------------------------

    def build_pokemon_card(
        self,
        spec: PokemonCardSpec,
        art_image: Optional[Image.Image] = None,
        product_code: str = "TCG_STANDARD",
    ) -> Image.Image:
        """Compõe uma carta completa estilo Pokémon TCG."""
        preset = get_product_preset(product_code)
        theme_color = self.COLOR_PALETTES["pokemon"].get(spec.energy_type, (180, 180, 180))
        img, draw = self._create_base_card(preset, theme_color)
        w, h = img.size

        # 1. Cabeçalho (Nome e HP)
        font_title = FontManager.load_font("Montserrat-Bold.ttf", int(36 * (self.dpi / 300)))
        font_sub = FontManager.load_font("Montserrat-Bold.ttf", int(28 * (self.dpi / 300)))
        font_body = FontManager.load_font("Montserrat-Regular.ttf", int(22 * (self.dpi / 300)))

        # Header box
        draw.rounded_rectangle([45, 45, w - 45, 110], radius=10, fill=(250, 250, 250), outline=(20, 20, 20), width=2)
        draw.text((60, 77), spec.name.upper(), fill=(20, 20, 20), font=font_title, anchor="lm")
        hp_text = f"HP {spec.hp}"
        draw.text((w - 60, 77), hp_text, fill=(200, 30, 30), font=font_title, anchor="rm")

        # 2. Janela de Arte Central
        art_rect = (55, 130, w - 55, 520)
        self._paste_art_window(img, art_image or spec.art_path, art_rect)
        draw.rectangle(art_rect, outline=(20, 20, 20), width=3)

        # 3. Caixa de Regras / Ataques
        text_box_rect = [50, 540, w - 50, h - 110]
        draw.rounded_rectangle(text_box_rect, radius=12, fill=(255, 255, 255), outline=(30, 30, 30), width=2)

        curr_y = 560
        for atk in spec.attacks:
            atk_header = f"{atk.cost}  {atk.name}"
            draw.text((70, curr_y), atk_header, fill=(10, 10, 10), font=font_sub)
            if atk.damage:
                draw.text((w - 70, curr_y), str(atk.damage), fill=(10, 10, 10), font=font_title, anchor="ra")
            curr_y += 38

            if atk.effect:
                wrapped = textwrap.wrap(atk.effect, width=45)
                for line in wrapped:
                    draw.text((70, curr_y), line, fill=(60, 60, 60), font=font_body)
                    curr_y += 28
            curr_y += 20

        # 4. Rodapé Técnico
        footer_text = f"Illus. {spec.illustrator} • {spec.collection_number} • Studio Kustom Fan Proxy"
        draw.text((w // 2, h - 70), footer_text, fill=(230, 230, 230), font=font_body, anchor="mm")

        return img

    def build_magic_card(
        self,
        spec: MagicCardSpec,
        art_image: Optional[Image.Image] = None,
        product_code: str = "TCG_STANDARD",
    ) -> Image.Image:
        """Compõe uma carta completa estilo Magic: The Gathering."""
        preset = get_product_preset(product_code)
        theme_color = self.COLOR_PALETTES["magic"].get(spec.frame_color, (140, 140, 140))
        img, draw = self._create_base_card(preset, theme_color)
        w, h = img.size

        font_name = FontManager.load_font("Montserrat-Bold.ttf", int(34 * (self.dpi / 300)))
        font_type = FontManager.load_font("Montserrat-Bold.ttf", int(24 * (self.dpi / 300)))
        font_body = FontManager.load_font("Montserrat-Regular.ttf", int(21 * (self.dpi / 300)))

        # 1. Barra de Título
        draw.rounded_rectangle([45, 45, w - 45, 105], radius=8, fill=(245, 245, 245), outline=(0, 0, 0), width=2)
        draw.text((60, 75), spec.name, fill=(0, 0, 0), font=font_name, anchor="lm")
        draw.text((w - 60, 75), spec.mana_cost, fill=(30, 30, 30), font=font_name, anchor="rm")

        # 2. Janela de Arte
        art_rect = (50, 115, w - 50, 520)
        self._paste_art_window(img, art_image or spec.art_path, art_rect)
        draw.rectangle(art_rect, outline=(0, 0, 0), width=2)

        # 3. Barra de Tipo
        draw.rounded_rectangle([45, 530, w - 45, 585], radius=6, fill=(245, 245, 245), outline=(0, 0, 0), width=2)
        draw.text((60, 557), spec.card_type, fill=(0, 0, 0), font=font_type, anchor="lm")

        # 4. Caixa de Regras
        rules_rect = [50, 600, w - 50, h - 90]
        draw.rounded_rectangle(rules_rect, radius=8, fill=(255, 255, 255), outline=(0, 0, 0), width=2)

        text_y = 620
        for line in textwrap.wrap(spec.text_box, width=42):
            draw.text((70, text_y), line, fill=(20, 20, 20), font=font_body)
            text_y += 30

        # Poder / Resistência
        if spec.power_toughness:
            pt_box = [w - 150, h - 130, w - 45, h - 75]
            draw.rounded_rectangle(pt_box, radius=8, fill=(240, 240, 240), outline=(0, 0, 0), width=2)
            draw.text(((pt_box[0] + pt_box[2]) // 2, (pt_box[1] + pt_box[3]) // 2), spec.power_toughness, fill=(0, 0, 0), font=font_name, anchor="mm")

        # Rodapé
        draw.text((70, h - 50), f"Illus. {spec.illustrator} | Studio Kustom", fill=(220, 220, 220), font=font_body)
        return img

    def build_onepiece_card(
        self,
        spec: OnePieceCardSpec,
        art_image: Optional[Image.Image] = None,
        product_code: str = "TCG_STANDARD",
    ) -> Image.Image:
        """Compõe uma carta estilo One Piece Card Game."""
        preset = get_product_preset(product_code)
        theme_color = self.COLOR_PALETTES["one_piece"].get(spec.color, (180, 30, 30))
        img, draw = self._create_base_card(preset, theme_color)
        w, h = img.size

        font_large = FontManager.load_font("Montserrat-Bold.ttf", int(38 * (self.dpi / 300)))
        font_sub = FontManager.load_font("Montserrat-Bold.ttf", int(26 * (self.dpi / 300)))
        font_body = FontManager.load_font("Montserrat-Regular.ttf", int(22 * (self.dpi / 300)))

        # Custo Superior Esquerdo
        draw.ellipse([45, 45, 125, 125], fill=(255, 215, 0), outline=(0, 0, 0), width=3)
        draw.text((85, 85), str(spec.cost), fill=(0, 0, 0), font=font_large, anchor="mm")

        # Nome e Atributo
        draw.text((145, 70), spec.name.upper(), fill=(255, 255, 255), font=font_large, anchor="lm")
        draw.text((145, 110), f"Atributo: {spec.attribute}", fill=(240, 240, 240), font=font_sub, anchor="lm")

        # Arte Central
        art_rect = (50, 140, w - 50, 600)
        self._paste_art_window(img, art_image or spec.art_path, art_rect)
        draw.rectangle(art_rect, outline=(0, 0, 0), width=2)

        # Poder
        draw.rounded_rectangle([w - 220, 560, w - 50, 630], radius=8, fill=(255, 215, 0), outline=(0, 0, 0), width=2)
        draw.text((w - 135, 595), f"{spec.power}", fill=(0, 0, 0), font=font_large, anchor="mm")

        # Caixa de Efeito
        box_rect = [50, 645, w - 50, h - 80]
        draw.rounded_rectangle(box_rect, radius=10, fill=(255, 255, 255), outline=(0, 0, 0), width=2)

        y_pos = 665
        for line in textwrap.wrap(spec.effect, width=42):
            draw.text((70, y_pos), line, fill=(20, 20, 20), font=font_body)
            y_pos += 30

        if spec.trigger:
            draw.text((70, y_pos + 10), f"TRIGGER: {spec.trigger}", fill=(200, 40, 40), font=font_sub)

        return img

    def build_ordem_paranormal_card(
        self,
        spec: OrdemParanormalCardSpec,
        art_image: Optional[Image.Image] = None,
        product_code: str = "TCG_STANDARD",
    ) -> Image.Image:
        """Compõe uma carta de Ritual/Item do universo Ordem Paranormal."""
        preset = get_product_preset(product_code)
        theme_color = self.COLOR_PALETTES["ordem"].get(spec.element, (40, 40, 40))
        img, draw = self._create_base_card(preset, theme_color)
        w, h = img.size

        font_title = FontManager.load_font("Montserrat-Bold.ttf", int(34 * (self.dpi / 300)))
        font_sub = FontManager.load_font("Montserrat-Bold.ttf", int(24 * (self.dpi / 300)))
        font_body = FontManager.load_font("Montserrat-Regular.ttf", int(22 * (self.dpi / 300)))

        # Barra do Ritual
        draw.rounded_rectangle([45, 45, w - 45, 110], radius=6, fill=(15, 15, 15), outline=(200, 200, 200), width=2)
        draw.text((60, 77), spec.name.upper(), fill=(255, 255, 255), font=font_title, anchor="lm")
        draw.text((w - 60, 77), f"{spec.pe_cost} PE", fill=(212, 172, 13), font=font_title, anchor="rm")

        # Janela de Arte
        art_rect = (50, 125, w - 50, 520)
        self._paste_art_window(img, art_image or spec.art_path, art_rect)
        draw.rectangle(art_rect, outline=(200, 200, 200), width=2)

        # Dados do Ritual
        info_rect = [45, 530, w - 45, 580]
        draw.rounded_rectangle(info_rect, radius=6, fill=(25, 25, 25), outline=(150, 150, 150), width=1)
        sub_info = f"Elemento: {spec.element} • {spec.circle}º Círculo • Alcance: {spec.range_desc}"
        draw.text((w // 2, 555), sub_info, fill=(240, 240, 240), font=font_sub, anchor="mm")

        # Descrição do Efeito
        desc_rect = [45, 595, w - 45, h - 80]
        draw.rounded_rectangle(desc_rect, radius=8, fill=(245, 245, 245), outline=(0, 0, 0), width=2)

        y_pos = 615
        for line in textwrap.wrap(spec.effect, width=42):
            draw.text((65, y_pos), line, fill=(15, 15, 15), font=font_body)
            y_pos += 30

        return img

    def build_generic_card(
        self,
        spec: GenericCardSpec,
        art_image: Optional[Image.Image] = None,
        product_code: str = "TCG_STANDARD",
    ) -> Image.Image:
        """Compõe uma carta genérica para RPGs e customizados."""
        preset = get_product_preset(product_code)
        # Converte hex para RGB
        hex_c = spec.theme_color.lstrip("#")
        bg_rgb = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4)) if len(hex_c) == 6 else (50, 50, 70)
        img, draw = self._create_base_card(preset, bg_rgb)
        w, h = img.size

        font_title = FontManager.load_font("Montserrat-Bold.ttf", int(34 * (self.dpi / 300)))
        font_sub = FontManager.load_font("Montserrat-Bold.ttf", int(24 * (self.dpi / 300)))
        font_body = FontManager.load_font("Montserrat-Regular.ttf", int(22 * (self.dpi / 300)))

        # Cabeçalho
        draw.rounded_rectangle([45, 45, w - 45, 110], radius=8, fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        draw.text((60, 77), spec.title, fill=(0, 0, 0), font=font_title, anchor="lm")
        if spec.subtitle:
            draw.text((w - 60, 77), spec.subtitle, fill=(80, 80, 80), font=font_sub, anchor="rm")

        # Arte
        art_rect = (50, 125, w - 50, 530)
        self._paste_art_window(img, art_image or spec.art_path, art_rect)
        draw.rectangle(art_rect, outline=(0, 0, 0), width=2)

        # Caixa de Atributos e Texto
        box_rect = [45, 545, w - 45, h - 80]
        draw.rounded_rectangle(box_rect, radius=8, fill=(255, 255, 255), outline=(0, 0, 0), width=2)

        y_pos = 565
        for k, v in spec.attributes.items():
            draw.text((65, y_pos), f"{k}: {v}", fill=(10, 10, 10), font=font_sub)
            y_pos += 32

        if spec.description:
            y_pos += 10
            for line in textwrap.wrap(spec.description, width=42):
                draw.text((65, y_pos), line, fill=(40, 40, 40), font=font_body)
                y_pos += 30

        return img

    def render_official_card_back(
        self,
        product_code: str = "TCG_STANDARD",
    ) -> Image.Image:
        """Gera o verso oficial de baralho Studio Kustom com padrão geométrico de segurança."""
        preset = get_product_preset(product_code)
        w, h = preset.trim_size_px(self.dpi)

        back = Image.new("RGB", (w, h), color=(18, 24, 38))
        draw = ImageDraw.Draw(back)

        # Moldura externa azul/ouro
        m = int(25 * (self.dpi / 300))
        draw.rounded_rectangle([m, m, w - m, h - m], radius=20, outline=(212, 175, 55), width=int(6 * (self.dpi / 300)))

        inner_m = m + int(15 * (self.dpi / 300))
        draw.rounded_rectangle([inner_m, inner_m, w - inner_m, h - inner_m], radius=15, outline=(40, 60, 95), width=int(3 * (self.dpi / 300)))

        # Padrão geométrico central (círculos concêntricos de segurança anti-marcação)
        cx, cy = w // 2, h // 2
        for r in range(40, 220, 25):
            radius = int(r * (self.dpi / 300))
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=(212, 175, 55, 120), width=2)

        font_logo = FontManager.load_font("RetroByte.ttf", int(36 * (self.dpi / 300)))
        draw.text((cx, cy), "STUDIO KUSTOM", fill=(212, 175, 55), font=font_logo, anchor="mm")
        font_sub = FontManager.load_font("Montserrat-Bold.ttf", int(18 * (self.dpi / 300)))
        draw.text((cx, cy + int(45 * (self.dpi / 300))), "COLLECTIBLE CARD GAME", fill=(180, 200, 230), font=font_sub, anchor="mm")

        return back
