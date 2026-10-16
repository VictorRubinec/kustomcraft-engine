"""Motor 3: Estúdio de Canecas & Sublimação Térmica (Studio Kustom Engine).

Responsável pelo gabarito milimétrico, compensação térmica cromática para prensa cilíndrica,
espelhamento horizontal para impressoras sublimáticas (Epson L110) e montagem de tiras
otimizadas para folhas A4 e Super A4 com guias de corte.

Formatos Atendidos:
- Caneca Cerâmica Panorâmica (11oz / 325ml): 220 x 95 mm (2598 x 1122 px a 300 DPI)
- Caneca de Chopp Vidro Jateado: 200 x 90 mm (2362 x 1063 px a 300 DPI)
- Caneca de Polímero Infantil: 205 x 85 mm (2421 x 1004 px a 300 DPI)
- Caneca Mágica Termossensível: 220 x 95 mm (2598 x 1122 px a 300 DPI)
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from src.core.presets import (
    SheetPreset,
    ProductPreset,
    get_product_preset,
    get_sheet_preset,
    mm_to_px,
    mm_to_pt,
    DEFAULT_DPI,
)


@dataclass(frozen=True)
class MugResult:
    """Resultado da preparação de arte para caneca."""

    image: Image.Image
    product_code: str
    size_px: Tuple[int, int]
    is_mirrored: bool
    thermal_compensated: bool
    dpi: int
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MugSheetLayout:
    """Disposição de tiras de caneca em folha A4 ou Super A4."""

    sheet_preset: SheetPreset
    product_preset: ProductPreset
    strip_count: int
    positions: List[Tuple[float, float, float, float]]  # (x_mm, y_mm, w_mm, h_mm)


class MugStudioEngine:
    """Motor de arte e pré-impressão sublimática para canecas."""

    # Parâmetros oficiais de compensação térmica para prensa cilíndrica a 200°C
    DEFAULT_SATURATION_BOOST: float = 1.18  # +18%
    DEFAULT_BRIGHTNESS_BOOST: float = 1.10  # +10%
    DEFAULT_CONTRAST_BOOST: float = 1.12    # +12%

    def __init__(self, dpi: int = DEFAULT_DPI):
        self.dpi = dpi

    def apply_thermal_compensation(
        self,
        image: Image.Image,
        saturation_boost: float = DEFAULT_SATURATION_BOOST,
        brightness_boost: float = DEFAULT_BRIGHTNESS_BOOST,
        contrast_boost: float = DEFAULT_CONTRAST_BOOST,
    ) -> Image.Image:
        """Aplica compensação cromática para contrabalançar perda de pigmento na prensa térmica."""
        img = image.convert("RGB")
        # 1. Realce de Saturação (+18%)
        if saturation_boost != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(saturation_boost)
        # 2. Realce de Brilho (+10%)
        if brightness_boost != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness_boost)
        # 3. Realce de Contraste (+12%)
        if contrast_boost != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast_boost)
        return img

    def prepare_mug_art(
        self,
        image: Union[Image.Image, Path, str],
        product_code: str = "MUG_CERAMIC",
        mirror_for_sublimation: bool = True,
        apply_thermal_compensation: bool = True,
        dpi: Optional[int] = None,
    ) -> MugResult:
        """Prepara arte de caneca nas dimensões exatas de catálogo a 300 DPI.

        Args:
            image: Imagem de entrada.
            product_code: 'MUG_CERAMIC', 'MUG_CHOPP', 'MUG_POLYMER', 'MUG_MAGIC'.
            mirror_for_sublimation: Se True, espelha horizontalmente para transfer Epson L110.
            apply_thermal_compensation: Se True, satura cores para a prensa térmica.
            dpi: Resolução alvo (padrão 300 DPI).
        """
        target_dpi = dpi or self.dpi
        preset = get_product_preset(product_code)

        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {path}")
            img = Image.open(path).convert("RGB")
        elif isinstance(image, Image.Image):
            img = image.convert("RGB")
        else:
            raise TypeError(f"Tipo de entrada inválido: {type(image)}")

        # Redimensiona para o tamanho de catálogo exato em pixels
        target_size = preset.trim_size_px(target_dpi)
        if img.size != target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)

        # Compensação térmica
        if apply_thermal_compensation:
            img = self.apply_thermal_compensation(img)

        # Espelhamento sublimático
        if mirror_for_sublimation:
            img = ImageOps.mirror(img)

        details = {
            "width_mm": preset.width_mm,
            "height_mm": preset.height_mm,
            "safe_margin_mm": preset.safe_margin_mm,
            "handle_gap_mm": 60.0 if "CERAMIC" in product_code or "MAGIC" in product_code else 50.0,
        }

        return MugResult(
            image=img,
            product_code=preset.code,
            size_px=target_size,
            is_mirrored=mirror_for_sublimation,
            thermal_compensated=apply_thermal_compensation,
            dpi=target_dpi,
            details=details,
        )

    def calculate_sheet_layout(
        self,
        product_code: str = "MUG_CERAMIC",
        sheet_code: str = "A4",
        spacing_mm: float = 4.0,
    ) -> MugSheetLayout:
        """Calcula a melhor distribuição de tiras de caneca na folha com marcas de corte."""
        product = get_product_preset(product_code)
        sheet = get_sheet_preset(sheet_code)

        # Orientações possíveis da folha
        # Caneca cerâmica: 220 x 95 mm
        # Em A4 paisagem (297 x 210 mm):
        # Largura 220 <= 297 mm (margem lateral 38.5 mm).
        # Altura 210 mm comporta exatamente 2 tiras de 95 mm (190 mm + 4 mm vão = 194 mm, margens 8.0 mm).
        strip_w = product.width_mm
        strip_h = product.height_mm

        # Verifica folha como está ou se precisa alternar orientação
        eval_sheet = sheet
        if strip_w > eval_sheet.width_mm:
            # Tenta orientação horizontal
            landscape_candidate = sheet.as_landscape()
            if strip_w <= landscape_candidate.width_mm:
                eval_sheet = landscape_candidate
            else:
                raise ValueError(
                    f"A tira da caneca ({strip_w}x{strip_h}mm) não cabe na folha {sheet.name}."
                )

        # Quantas tiras verticais cabem
        available_h = eval_sheet.height_mm
        max_strips = 0
        while True:
            candidate = max_strips + 1
            needed_h = (candidate * strip_h) + ((candidate - 1) * spacing_mm)
            if needed_h <= available_h:
                max_strips = candidate
            else:
                break

        if max_strips == 0:
            raise ValueError(f"Nenhuma tira cabe na folha {eval_sheet.name}.")

        total_grid_h = (max_strips * strip_h) + ((max_strips - 1) * spacing_mm)
        margin_x = (eval_sheet.width_mm - strip_w) / 2.0
        margin_y = (eval_sheet.height_mm - total_grid_h) / 2.0

        positions: List[Tuple[float, float, float, float]] = []
        for i in range(max_strips):
            y = margin_y + (i * (strip_h + spacing_mm))
            positions.append((margin_x, y, strip_w, strip_h))

        return MugSheetLayout(
            sheet_preset=eval_sheet,
            product_preset=product,
            strip_count=max_strips,
            positions=positions,
        )

    def render_sublimation_sheet_pdf(
        self,
        images: List[Union[Image.Image, Path, str]],
        output_path: Union[Path, str],
        product_code: str = "MUG_CERAMIC",
        sheet_code: str = "A4",
        mirror_for_sublimation: bool = True,
        apply_thermal_compensation: bool = True,
    ) -> Path:
        """Gera PDF de folha completa pronto para impressão na Epson L110 com marcas de corte."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        layout = self.calculate_sheet_layout(product_code, sheet_code)
        sheet = layout.sheet_preset

        # Prepara cada arte
        prepared_images = []
        for img in images[:layout.strip_count]:
            res = self.prepare_mug_art(
                img,
                product_code=product_code,
                mirror_for_sublimation=mirror_for_sublimation,
                apply_thermal_compensation=apply_thermal_compensation,
            )
            prepared_images.append(res.image)

        doc = fitz.open()
        page = doc.new_page(width=sheet.width_pt, height=sheet.height_pt)

        # Insere as tiras
        for i, (x_mm, y_mm, w_mm, h_mm) in enumerate(layout.positions):
            if i < len(prepared_images):
                img = prepared_images[i]
                buf = io_buf = Path(output_path).with_suffix(".tmp.png")
                img.save(io_buf, format="PNG")
                rect = fitz.Rect(
                    mm_to_pt(x_mm),
                    mm_to_pt(y_mm),
                    mm_to_pt(x_mm + w_mm),
                    mm_to_pt(y_mm + h_mm),
                )
                page.insert_image(rect, filename=str(io_buf))
                if io_buf.exists():
                    io_buf.unlink()

        # Desenha marcas de corte finas a 0.25pt ao redor de cada tira
        shape = page.new_shape()
        for x_mm, y_mm, w_mm, h_mm in layout.positions:
            tx = mm_to_pt(x_mm)
            ty = mm_to_pt(y_mm)
            tw = mm_to_pt(w_mm)
            th = mm_to_pt(h_mm)
            arm = mm_to_pt(5.0)

            # 4 cantos com marcas externas de 5mm
            # Top-left
            shape.draw_line(fitz.Point(tx, ty - arm), fitz.Point(tx, ty))
            shape.draw_line(fitz.Point(tx - arm, ty), fitz.Point(tx, ty))
            # Top-right
            shape.draw_line(fitz.Point(tx + tw, ty - arm), fitz.Point(tx + tw, ty))
            shape.draw_line(fitz.Point(tx + tw + arm, ty), fitz.Point(tx + tw, ty))
            # Bot-left
            shape.draw_line(fitz.Point(tx, ty + th + arm), fitz.Point(tx, ty + th))
            shape.draw_line(fitz.Point(tx - arm, ty + th), fitz.Point(tx, ty + th))
            # Bot-right
            shape.draw_line(fitz.Point(tx + tw, ty + th + arm), fitz.Point(tx + tw, ty + th))
            shape.draw_line(fitz.Point(tx + tw + arm, ty + th), fitz.Point(tx + tw, ty + th))

        shape.finish(width=0.25, color=(0, 0, 0))
        shape.commit()

        doc.save(str(output_path))
        doc.close()
        return output_path
