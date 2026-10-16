"""Tabela oficial de formatos, dimensões milimétricas e conversões gráficas a 300 DPI.

Este módulo é a fonte única da verdade para todos os cálculos dimensionais da
Studio Kustom Engine, em conformidade estrita com o catálogo milimétrico e o
parque de máquinas real (Konica Minolta bizhub C558, Epson T3170 e prensas).
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple

# Constantes Fundamentais de Conversão Gráfica
INCH_TO_MM: float = 25.4
POINTS_PER_INCH: float = 72.0
MM_TO_PT: float = POINTS_PER_INCH / INCH_TO_MM  # ~2.83464567 pt/mm
PT_TO_MM: float = INCH_TO_MM / POINTS_PER_INCH  # ~0.35277778 mm/pt
DEFAULT_DPI: int = 300


def mm_to_px(mm: float, dpi: int = DEFAULT_DPI) -> int:
    """Converte milímetros para pixels na resolução especificada (padrão 300 DPI)."""
    return round((mm / INCH_TO_MM) * dpi)


def px_to_mm(px: int, dpi: int = DEFAULT_DPI) -> float:
    """Converte pixels para milímetros na resolução especificada."""
    return (px / dpi) * INCH_TO_MM


def mm_to_pt(mm: float) -> float:
    """Converte milímetros para pontos tipográficos PDF/ReportLab (72 pt/polegada)."""
    return (mm / INCH_TO_MM) * POINTS_PER_INCH


def pt_to_mm(pt: float) -> float:
    """Converte pontos tipográficos para milímetros."""
    return (pt / POINTS_PER_INCH) * INCH_TO_MM


class Orientation(str, Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


@dataclass(frozen=True)
class SheetPreset:
    """Especificação física de folhas de papel para alimentação da impressora."""

    name: str
    code: str
    width_mm: float
    height_mm: float
    description: str

    @property
    def width_pt(self) -> float:
        return mm_to_pt(self.width_mm)

    @property
    def height_pt(self) -> float:
        return mm_to_pt(self.height_mm)

    def size_px(self, dpi: int = DEFAULT_DPI) -> Tuple[int, int]:
        return (mm_to_px(self.width_mm, dpi), mm_to_px(self.height_mm, dpi))

    def as_landscape(self) -> SheetPreset:
        if self.width_mm >= self.height_mm:
            return self
        return SheetPreset(
            name=f"{self.name} (Horizontal)",
            code=f"{self.code}_LANDSCAPE",
            width_mm=self.height_mm,
            height_mm=self.width_mm,
            description=f"{self.description} em orientação horizontal",
        )

    def as_portrait(self) -> SheetPreset:
        if self.height_mm >= self.width_mm:
            return self
        return SheetPreset(
            name=f"{self.name} (Vertical)",
            code=f"{self.code}_PORTRAIT",
            width_mm=self.height_mm,
            height_mm=self.width_mm,
            description=f"{self.description} em orientação vertical",
        )


@dataclass(frozen=True)
class ProductPreset:
    """Especificação de produto individual com sangria, segurança e raio de canto."""

    name: str
    code: str
    width_mm: float
    height_mm: float
    bleed_mm: float = 0.0
    safe_margin_mm: float = 0.0
    corner_radius_mm: float = 0.0
    orientation: Orientation = Orientation.PORTRAIT
    description: str = ""

    @property
    def trim_width_mm(self) -> float:
        """Largura nominal final após refile."""
        return self.width_mm

    @property
    def trim_height_mm(self) -> float:
        """Altura nominal final após refile."""
        return self.height_mm

    @property
    def total_width_mm(self) -> float:
        """Largura bruta incluindo sangria industrial dos dois lados."""
        return self.width_mm + (2.0 * self.bleed_mm)

    @property
    def total_height_mm(self) -> float:
        """Altura bruta incluindo sangria industrial dos dois lados."""
        return self.height_mm + (2.0 * self.bleed_mm)

    @property
    def trim_width_pt(self) -> float:
        return mm_to_pt(self.trim_width_mm)

    @property
    def trim_height_pt(self) -> float:
        return mm_to_pt(self.trim_height_mm)

    @property
    def total_width_pt(self) -> float:
        return mm_to_pt(self.total_width_mm)

    @property
    def total_height_pt(self) -> float:
        return mm_to_pt(self.total_height_mm)

    def trim_size_px(self, dpi: int = DEFAULT_DPI) -> Tuple[int, int]:
        return (mm_to_px(self.trim_width_mm, dpi), mm_to_px(self.trim_height_mm, dpi))

    def total_size_px(self, dpi: int = DEFAULT_DPI) -> Tuple[int, int]:
        return (mm_to_px(self.total_width_mm, dpi), mm_to_px(self.total_height_mm, dpi))


# ---------------------------------------------------------------------------
# Catálogo Homologado de Folhas para Konica C558 e Plotter Epson T3170
# ---------------------------------------------------------------------------
SHEET_PRESETS: Dict[str, SheetPreset] = {
    # Formatos de Alta Produção (Duplex na Konica C558)
    "SUPER_A4": SheetPreset(
        name="Super A4 (230x315 Real)",
        code="SUPER_A4",
        width_mm=229.92,
        height_mm=315.12,
        description="Formato real calibrado do chão de fábrica da Studio Kustom (229.92 x 315.12 mm)",
    ),
    "SUPER_A4_STANDARD": SheetPreset(
        name="Super A4 Padrão (225x320)",
        code="SUPER_A4_STANDARD",
        width_mm=225.0,
        height_mm=320.0,
        description="Formato comercial genérico para Couché 300g",
    ),
    "SUPER_A3": SheetPreset(
        name="Super A3 (320x450)",
        code="SUPER_A3",
        width_mm=320.0,
        height_mm=450.0,
        description="Formato padrão de gráfica rápida para grades duplex 3x3 de TCGs",
    ),
    "SUPER_A3_EXTENDED": SheetPreset(
        name="Super A3 Estendido / A3+ (13x19 pol)",
        code="SUPER_A3_EXTENDED",
        width_mm=329.0,
        height_mm=483.0,
        description="Formato A3+ ampliado (13 x 19 polegadas) para aproveitamento máximo",
    ),
    # Formatos Padrão ISO 216
    "A4": SheetPreset(
        name="A4",
        code="A4",
        width_mm=210.0,
        height_mm=297.0,
        description="Folha ISO A4 padrão",
    ),
    "A3": SheetPreset(
        name="A3",
        code="A3",
        width_mm=297.0,
        height_mm=420.0,
        description="Folha ISO A3 padrão",
    ),
    # Grandes Formatos (Plotter Epson SureColor T3170)
    "A2": SheetPreset(
        name="A2",
        code="A2",
        width_mm=420.0,
        height_mm=594.0,
        description="Folha ISO A2 para pôsteres",
    ),
    "A1": SheetPreset(
        name="A1",
        code="A1",
        width_mm=594.0,
        height_mm=841.0,
        description="Folha ISO A1 para grandes pôsteres de alta definição",
    ),
}

# Alias para compatibilidade
SHEET_PRESETS["A3_PLUS"] = SHEET_PRESETS["SUPER_A3_EXTENDED"]
SHEET_PRESETS["SA4"] = SHEET_PRESETS["SUPER_A4"]
SHEET_PRESETS["SA3"] = SHEET_PRESETS["SUPER_A3"]


# ---------------------------------------------------------------------------
# Catálogo Homologado de Produtos da Studio Kustom
# ---------------------------------------------------------------------------
PRODUCT_PRESETS: Dict[str, ProductPreset] = {
    # Trading Cards e Colecionáveis
    "TCG_STANDARD": ProductPreset(
        name="Trading Card Standard",
        code="TCG_STANDARD",
        width_mm=63.5,
        height_mm=88.9,
        bleed_mm=5.0,
        safe_margin_mm=3.0,
        corner_radius_mm=3.0,
        orientation=Orientation.PORTRAIT,
        description="Cards oficiais Pokémon, Magic: The Gathering, One Piece (2.5x3.5 pol)",
    ),
    "TCG_STANDARD_NO_BLEED": ProductPreset(
        name="Trading Card Standard (Sem Sangria)",
        code="TCG_STANDARD_NO_BLEED",
        width_mm=63.5,
        height_mm=88.9,
        bleed_mm=0.0,
        safe_margin_mm=3.0,
        corner_radius_mm=3.0,
        orientation=Orientation.PORTRAIT,
        description="Dimensão de corte nominal de carta standard",
    ),
    "TCG_STANDARD_BACK_REAL": ProductPreset(
        name="Trading Card Verso Real com Sangria",
        code="TCG_STANDARD_BACK_REAL",
        width_mm=68.0,
        height_mm=93.0,
        bleed_mm=0.0,
        safe_margin_mm=0.0,
        orientation=Orientation.PORTRAIT,
        description="Verso real calibrado do arquivo cartas.pdf (68.0 x 93.0 mm com +2.25mm de sangria lateral)",
    ),
    "TCG_JAPANESE": ProductPreset(
        name="Trading Card Japonês",
        code="TCG_JAPANESE",
        width_mm=59.0,
        height_mm=86.0,
        bleed_mm=5.0,
        safe_margin_mm=3.0,
        corner_radius_mm=3.0,
        orientation=Orientation.PORTRAIT,
        description="Formato clássico japonês (Yu-Gi-Oh! e Cardfight!! Vanguard)",
    ),
    "TCG_JAPANESE_NO_BLEED": ProductPreset(
        name="Trading Card Japonês (Sem Sangria)",
        code="TCG_JAPANESE_NO_BLEED",
        width_mm=59.0,
        height_mm=86.0,
        bleed_mm=0.0,
        safe_margin_mm=3.0,
        corner_radius_mm=3.0,
        orientation=Orientation.PORTRAIT,
        description="Dimensão de corte nominal de carta japonesa",
    ),
    # Canecas e Sublimação Cilíndrica
    "MUG_CERAMIC": ProductPreset(
        name="Caneca de Cerâmica Panorâmica",
        code="MUG_CERAMIC",
        width_mm=220.0,
        height_mm=95.0,
        bleed_mm=0.0,
        safe_margin_mm=5.0,
        orientation=Orientation.LANDSCAPE,
        description="Gabarito panorâmico para canecas de cerâmica resinadas 11oz (325ml)",
    ),
    "MUG_MAGIC": ProductPreset(
        name="Caneca Mágica Termossensível",
        code="MUG_MAGIC",
        width_mm=220.0,
        height_mm=95.0,
        bleed_mm=0.0,
        safe_margin_mm=5.0,
        orientation=Orientation.LANDSCAPE,
        description="Caneca termossensível preta que revela arte com calor",
    ),
    "MUG_CHOPP": ProductPreset(
        name="Caneca de Chopp Jateada",
        code="MUG_CHOPP",
        width_mm=200.0,
        height_mm=90.0,
        bleed_mm=0.0,
        safe_margin_mm=5.0,
        orientation=Orientation.LANDSCAPE,
        description="Caneca de vidro jateado para sublimação",
    ),
    "MUG_POLYMER": ProductPreset(
        name="Caneca de Polímero Infantil",
        code="MUG_POLYMER",
        width_mm=205.0,
        height_mm=85.0,
        bleed_mm=0.0,
        safe_margin_mm=5.0,
        orientation=Orientation.LANDSCAPE,
        description="Caneca plástica inquebrável para linha escolar",
    ),
    # Polaroids, Retrô e Papelaria
    "POLAROID_CLASSIC": ProductPreset(
        name="Foto Polaroid Clássica",
        code="POLAROID_CLASSIC",
        width_mm=88.0,
        height_mm=107.0,
        bleed_mm=2.0,
        safe_margin_mm=3.0,
        orientation=Orientation.PORTRAIT,
        description="Foto estilo Polaroid com rodapé largo de 20mm para dedicatória",
    ),
    "POLAROID_MINI": ProductPreset(
        name="Mini Polaroid Instax",
        code="POLAROID_MINI",
        width_mm=54.0,
        height_mm=86.0,
        bleed_mm=2.0,
        safe_margin_mm=3.0,
        orientation=Orientation.PORTRAIT,
        description="Tamanho compacto estilo Instax Mini para carteiras e cases",
    ),
    "PHOTO_STRIP": ProductPreset(
        name="Tirinha Photo Strip",
        code="PHOTO_STRIP",
        width_mm=50.0,
        height_mm=150.0,
        bleed_mm=2.0,
        safe_margin_mm=3.0,
        orientation=Orientation.PORTRAIT,
        description="Tira vertical com 3 ou 4 fotos de cabine",
    ),
    "BOOKMARK": ProductPreset(
        name="Marcador de Página",
        code="BOOKMARK",
        width_mm=50.0,
        height_mm=180.0,
        bleed_mm=2.0,
        safe_margin_mm=4.0,
        orientation=Orientation.PORTRAIT,
        description="Marcador de livro com sangria e guia de furo para tassel",
    ),
    "MOUSEPAD": ProductPreset(
        name="Mousepad Retangular",
        code="MOUSEPAD",
        width_mm=220.0,
        height_mm=180.0,
        bleed_mm=5.0,
        safe_margin_mm=8.0,
        orientation=Orientation.LANDSCAPE,
        description="Mousepad em neoprene/tecido para prensagem plana 38x38",
    ),
    # Pôsteres
    "POSTER_A4_V": ProductPreset(
        name="Pôster A4 Vertical",
        code="POSTER_A4_V",
        width_mm=210.0,
        height_mm=297.0,
        bleed_mm=0.0,
        safe_margin_mm=5.0,
        orientation=Orientation.PORTRAIT,
        description="Pôster A4 padrão com recuo de segurança para moldura",
    ),
    "POSTER_A4_H": ProductPreset(
        name="Pôster A4 Horizontal",
        code="POSTER_A4_H",
        width_mm=297.0,
        height_mm=210.0,
        bleed_mm=0.0,
        safe_margin_mm=5.0,
        orientation=Orientation.LANDSCAPE,
        description="Pôster A4 horizontal",
    ),
    "POSTER_A3_V": ProductPreset(
        name="Pôster A3 Vertical",
        code="POSTER_A3_V",
        width_mm=297.0,
        height_mm=420.0,
        bleed_mm=0.0,
        safe_margin_mm=5.0,
        orientation=Orientation.PORTRAIT,
        description="Pôster A3 vertical",
    ),
    "POSTER_A3_H": ProductPreset(
        name="Pôster A3 Horizontal",
        code="POSTER_A3_H",
        width_mm=420.0,
        height_mm=297.0,
        bleed_mm=0.0,
        safe_margin_mm=5.0,
        orientation=Orientation.LANDSCAPE,
        description="Pôster A3 horizontal",
    ),
}


def get_sheet_preset(code_or_name: str) -> SheetPreset:
    """Busca um preset de folha pelo código ou nome normalizado."""
    key = code_or_name.strip().upper()
    if key in SHEET_PRESETS:
        return SHEET_PRESETS[key]
    raise KeyError(
        f"Preset de folha desconhecido: '{code_or_name}'. "
        f"Disponíveis: {list(SHEET_PRESETS.keys())}"
    )


def get_product_preset(code_or_name: str) -> ProductPreset:
    """Busca um preset de produto pelo código ou nome normalizado."""
    key = code_or_name.strip().upper()
    if key in PRODUCT_PRESETS:
        return PRODUCT_PRESETS[key]
    raise KeyError(
        f"Preset de produto desconhecido: '{code_or_name}'. "
        f"Disponíveis: {list(PRODUCT_PRESETS.keys())}"
    )
