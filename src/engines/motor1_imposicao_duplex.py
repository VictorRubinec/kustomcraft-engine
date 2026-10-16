"""Motor 1: Imposição Gráfica e Registro Duplex (Studio Kustom Engine).

Responsável pelo cálculo milimétrico e pela geração determinística de folhas
frente e verso alinhadas (Super A4, Super A3 e formatos ISO) para o parque
de máquinas da Studio Kustom (especialmente a impressora laser Konica Minolta bizhub C558).

Princípio de Duplex da Konica C558:
Ao imprimir frente e verso pela borda longa, a impressora espelha o eixo X da folha.
O algoritmo garante que o centro geométrico de cada carta da frente coincida exatamente
com o centro geométrico do seu respectivo verso no papel (tolerância de desvio < 0.2mm).
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union
import fitz  # PyMuPDF
from PIL import Image
import io

from src.core.presets import (
    SheetPreset,
    ProductPreset,
    get_sheet_preset,
    get_product_preset,
    mm_to_pt,
    pt_to_mm,
    mm_to_px,
    DEFAULT_DPI,
)

ImageInput = Union[Image.Image, Path, str]


@dataclass
class SlotPosition:
    """Posicionamento de um slot individual na folha (coordenadas físicas em mm)."""

    index: int
    row: int
    col: int
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    bleed_mm: float = 0.0

    @property
    def center_x_mm(self) -> float:
        return self.x_mm + (self.width_mm / 2.0)

    @property
    def center_y_mm(self) -> float:
        return self.y_mm + (self.height_mm / 2.0)

    @property
    def trim_x_mm(self) -> float:
        """Coordenada X da linha de corte nominal."""
        return self.x_mm + self.bleed_mm

    @property
    def trim_y_mm(self) -> float:
        """Coordenada Y da linha de corte nominal."""
        return self.y_mm + self.bleed_mm

    @property
    def trim_width_mm(self) -> float:
        """Largura nominal após corte."""
        return max(0.0, self.width_mm - (2.0 * self.bleed_mm))

    @property
    def trim_height_mm(self) -> float:
        """Altura nominal após corte."""
        return max(0.0, self.height_mm - (2.0 * self.bleed_mm))

    # Coordenadas em pontos tipográficos para PDF
    @property
    def x_pt(self) -> float:
        return mm_to_pt(self.x_mm)

    @property
    def y_pt(self) -> float:
        return mm_to_pt(self.y_mm)

    @property
    def width_pt(self) -> float:
        return mm_to_pt(self.width_mm)

    @property
    def height_pt(self) -> float:
        return mm_to_pt(self.height_mm)

    @property
    def trim_x_pt(self) -> float:
        return mm_to_pt(self.trim_x_mm)

    @property
    def trim_y_pt(self) -> float:
        return mm_to_pt(self.trim_y_mm)

    @property
    def trim_width_pt(self) -> float:
        return mm_to_pt(self.trim_width_mm)

    @property
    def trim_height_pt(self) -> float:
        return mm_to_pt(self.trim_height_mm)


@dataclass
class ImpositionSlot:
    """Slot casado de imposição contendo a posição de frente e de verso."""

    front_slot: SlotPosition
    back_slot: SlotPosition
    front_item: Optional[ImageInput] = None
    back_item: Optional[ImageInput] = None


@dataclass
class DuplexLayout:
    """Grade completa de imposição duplex calculada para uma folha."""

    sheet_preset: SheetPreset
    product_preset: ProductPreset
    rows: int
    cols: int
    spacing_x_mm: float
    spacing_y_mm: float
    margin_left_mm: float
    margin_top_mm: float
    slots: List[ImpositionSlot] = field(default_factory=list)
    printer_offset_x_mm: float = 0.0
    printer_offset_y_mm: float = 0.0

    def validate_alignment(self, tolerance_mm: float = 0.2) -> Tuple[bool, float]:
        """Calcula o desvio euclidiano entre o centro da frente e o verso correspondente.

        Retorna:
            (alinhado: bool, desvio_maximo_mm: float)
        """
        max_deviation = 0.0
        for slot in self.slots:
            front = slot.front_slot
            back = slot.back_slot

            # Centro teórico esperado no verso após a virada no eixo Y
            expected_back_x = (self.sheet_preset.width_mm - front.center_x_mm) + self.printer_offset_x_mm
            expected_back_y = front.center_y_mm + self.printer_offset_y_mm

            dev = math.sqrt(
                (back.center_x_mm - expected_back_x) ** 2 +
                (back.center_y_mm - expected_back_y) ** 2
            )
            if dev > max_deviation:
                max_deviation = dev

        return (max_deviation <= tolerance_mm, max_deviation)


class ImpositionEngine:
    """Motor de cálculo e renderização gráfica de imposição duplex."""

    CROP_MARK_LENGTH_MM: float = 4.0
    CROP_MARK_OFFSET_MM: float = 1.0
    STROKE_WIDTH_PT: float = 0.25  # 0.25pt ultra-fino para corte industrial
    TARGET_RADIUS_MM: float = 3.0

    def create_layout(
        self,
        sheet_preset: SheetPreset,
        product_preset: ProductPreset,
        rows: int,
        cols: int,
        spacing_x_mm: float = 0.0,
        spacing_y_mm: float = 0.0,
        printer_offset_x_mm: float = 0.0,
        printer_offset_y_mm: float = 0.0,
    ) -> DuplexLayout:
        """Calcula o posicionamento geométrico dos slots na folha.

        Aplica centralização ótica na folha e espelhamento Y rigoroso das colunas
        para a página de verso.
        """
        item_w = product_preset.total_width_mm
        item_h = product_preset.total_height_mm
        bleed = product_preset.bleed_mm

        grid_w = (cols * item_w) + ((cols - 1) * spacing_x_mm)
        grid_h = (rows * item_h) + ((rows - 1) * spacing_y_mm)

        if grid_w > sheet_preset.width_mm or grid_h > sheet_preset.height_mm:
            raise ValueError(
                f"A grade {cols}x{rows} ({grid_w:.1f}x{grid_h:.1f}mm) não cabe na folha "
                f"{sheet_preset.name} ({sheet_preset.width_mm:.1f}x{sheet_preset.height_mm:.1f}mm)."
            )

        margin_left = (sheet_preset.width_mm - grid_w) / 2.0
        margin_top = (sheet_preset.height_mm - grid_h) / 2.0

        slots: List[ImpositionSlot] = []
        idx = 0

        for r in range(rows):
            for c in range(cols):
                # Coordenadas da FRENTE
                front_x = margin_left + (c * (item_w + spacing_x_mm))
                front_y = margin_top + (r * (item_h + spacing_y_mm))

                front_pos = SlotPosition(
                    index=idx,
                    row=r,
                    col=c,
                    x_mm=front_x,
                    y_mm=front_y,
                    width_mm=item_w,
                    height_mm=item_h,
                    bleed_mm=bleed,
                )

                # Coordenadas do VERSO (Espelhamento no eixo Y para a Konica C558)
                # O centro do verso casa exatamente com o centro da frente virada
                back_center_x = (sheet_preset.width_mm - front_pos.center_x_mm) + printer_offset_x_mm
                back_center_y = front_pos.center_y_mm + printer_offset_y_mm

                back_x = back_center_x - (item_w / 2.0)
                back_y = back_center_y - (item_h / 2.0)
                back_col = (cols - 1) - c

                back_pos = SlotPosition(
                    index=idx,
                    row=r,
                    col=back_col,
                    x_mm=back_x,
                    y_mm=back_y,
                    width_mm=item_w,
                    height_mm=item_h,
                    bleed_mm=bleed,
                )

                slots.append(ImpositionSlot(front_slot=front_pos, back_slot=back_pos))
                idx += 1

        return DuplexLayout(
            sheet_preset=sheet_preset,
            product_preset=product_preset,
            rows=rows,
            cols=cols,
            spacing_x_mm=spacing_x_mm,
            spacing_y_mm=spacing_y_mm,
            margin_left_mm=margin_left,
            margin_top_mm=margin_top,
            slots=slots,
            printer_offset_x_mm=printer_offset_x_mm,
            printer_offset_y_mm=printer_offset_y_mm,
        )

    def create_super_a4_9up_layout(
        self,
        front_preset_code: str = "TCG_STANDARD_NO_BLEED",
        back_width_mm: float = 68.0,
        back_height_mm: float = 93.0,
        margin_left_mm: float = 11.0,
        margin_top_mm: float = 18.0,
        spacing_x_mm: float = 8.5,
        spacing_y_mm: float = 6.2,
        printer_offset_x_mm: float = 0.0,
        printer_offset_y_mm: float = 0.0,
    ) -> DuplexLayout:
        """Cria o layout 3x3 calibrado exatamente pelo arquivo real cartas.pdf da Studio Kustom.

        Especificações do Chão de Fábrica:
        - Folha Super A4 Real: 229.92 x 315.12 mm
        - Grade: 3 colunas x 3 linhas (9 cartas TCG)
        - Cartas da Frente: 63.5 x 88.9 mm (750 x 1050 px a 300 DPI)
        - Versos com Sangria: 68.0 x 93.0 mm (+2.25mm de sangria lateral)
        - Margens: 11.0mm (horizontal) x 18.0mm (vertical)
        - Vãos: 8.5mm (horizontal) x 6.2mm (vertical)
        - Alinhamento duplex perfeito no eixo Y para a Konica Minolta bizhub C558.
        """
        sheet = get_sheet_preset("SUPER_A4")  # 229.92 x 315.12 mm
        front_product = get_product_preset(front_preset_code)

        front_w = front_product.width_mm
        front_h = front_product.height_mm

        slots: List[ImpositionSlot] = []
        idx = 0
        cols = 3
        rows = 3

        for r in range(rows):
            for c in range(cols):
                # Coordenadas da FRENTE
                fx = margin_left_mm + (c * (front_w + spacing_x_mm))
                fy = margin_top_mm + (r * (front_h + spacing_y_mm))

                front_pos = SlotPosition(
                    index=idx,
                    row=r,
                    col=c,
                    x_mm=fx,
                    y_mm=fy,
                    width_mm=front_w,
                    height_mm=front_h,
                    bleed_mm=0.0,
                )

                # Coordenadas do VERSO com Sangria calibrada (Espelhamento no eixo Y)
                back_cx = (sheet.width_mm - front_pos.center_x_mm) + printer_offset_x_mm
                back_cy = front_pos.center_y_mm + printer_offset_y_mm

                bx = back_cx - (back_width_mm / 2.0)
                by = back_cy - (back_height_mm / 2.0)
                back_col = (cols - 1) - c

                back_pos = SlotPosition(
                    index=idx,
                    row=r,
                    col=back_col,
                    x_mm=bx,
                    y_mm=by,
                    width_mm=back_width_mm,
                    height_mm=back_height_mm,
                    bleed_mm=(back_width_mm - front_w) / 2.0,
                )

                slots.append(ImpositionSlot(front_slot=front_pos, back_slot=back_pos))
                idx += 1

        return DuplexLayout(
            sheet_preset=sheet,
            product_preset=front_product,
            rows=rows,
            cols=cols,
            spacing_x_mm=spacing_x_mm,
            spacing_y_mm=spacing_y_mm,
            margin_left_mm=margin_left_mm,
            margin_top_mm=margin_top_mm,
            slots=slots,
            printer_offset_x_mm=printer_offset_x_mm,
            printer_offset_y_mm=printer_offset_y_mm,
        )

    def _draw_crop_marks(self, shape: fitz.Shape, slot: SlotPosition) -> None:
        """Desenha marcas de corte (crop marks) nos 4 cantos do trim box a 0.25 pt."""
        tx = slot.trim_x_pt
        ty = slot.trim_y_pt
        tw = slot.trim_width_pt
        th = slot.trim_height_pt

        arm_len = mm_to_pt(self.CROP_MARK_LENGTH_MM)
        offset = mm_to_pt(self.CROP_MARK_OFFSET_MM)

        # Canto Superior Esquerdo
        shape.draw_line(fitz.Point(tx, ty - offset), fitz.Point(tx, ty - offset - arm_len))
        shape.draw_line(fitz.Point(tx - offset, ty), fitz.Point(tx - offset - arm_len, ty))

        # Canto Superior Direito
        shape.draw_line(fitz.Point(tx + tw, ty - offset), fitz.Point(tx + tw, ty - offset - arm_len))
        shape.draw_line(fitz.Point(tx + tw + offset, ty), fitz.Point(tx + tw + offset + arm_len, ty))

        # Canto Inferior Esquerdo
        shape.draw_line(fitz.Point(tx, ty + th + offset), fitz.Point(tx, ty + th + offset + arm_len))
        shape.draw_line(fitz.Point(tx - offset, ty + th), fitz.Point(tx - offset - arm_len, ty + th))

        # Canto Inferior Direito
        shape.draw_line(fitz.Point(tx + tw, ty + th + offset), fitz.Point(tx + tw, ty + th + offset + arm_len))
        shape.draw_line(fitz.Point(tx + tw + offset, ty + th), fitz.Point(tx + tw + offset + arm_len, ty + th))

    def _draw_registration_target(self, shape: fitz.Shape, center_x_pt: float, center_y_pt: float) -> None:
        """Desenha cruz de registro profissional (alvo circular e cruz a 0.25 pt)."""
        r = mm_to_pt(self.TARGET_RADIUS_MM)
        # Círculo externo
        shape.draw_circle(fitz.Point(center_x_pt, center_y_pt), r)
        # Linha vertical
        shape.draw_line(fitz.Point(center_x_pt, center_y_pt - (r * 1.5)),
                        fitz.Point(center_x_pt, center_y_pt + (r * 1.5)))
        # Linha horizontal
        shape.draw_line(fitz.Point(center_x_pt - (r * 1.5), center_y_pt),
                        fitz.Point(center_x_pt + (r * 1.5), center_y_pt))

    def _draw_sheet_targets(self, shape: fitz.Shape, sheet: SheetPreset, is_back: bool = False) -> None:
        """Desenha os 4 alvos de registro nas bordas externas da folha."""
        w_pt = sheet.width_pt
        h_pt = sheet.height_pt
        offset = mm_to_pt(8.0)

        # Centros das 4 bordas
        targets = [
            (w_pt / 2.0, offset),             # Topo centro
            (w_pt / 2.0, h_pt - offset),       # Base centro
            (offset, h_pt / 2.0),             # Esquerda centro
            (w_pt - offset, h_pt / 2.0),       # Direita centro
        ]

        for cx, cy in targets:
            final_cx = (w_pt - cx) if is_back else cx
            self._draw_registration_target(shape, final_cx, cy)

    def _draw_corner_targets(
        self,
        shape: fitz.Shape,
        sheet: SheetPreset,
        is_back: bool = False,
        corner_offset_mm: float = 5.73,
        diameter_mm: float = 8.46,
    ) -> None:
        """Desenha os 4 alvos circulares de registro nos cantos da folha a 5.73mm da borda (padrão cartas.pdf)."""
        w_pt = sheet.width_pt
        h_pt = sheet.height_pt
        radius_pt = mm_to_pt(diameter_mm / 2.0)
        c_offset_pt = mm_to_pt(corner_offset_mm)

        # Centros nos 4 cantos
        cx_left = c_offset_pt + radius_pt
        cx_right = w_pt - c_offset_pt - radius_pt
        cy_top = c_offset_pt + radius_pt
        cy_bottom = h_pt - c_offset_pt - radius_pt

        corners = [
            (cx_left, cy_top),
            (cx_right, cy_top),
            (cx_left, cy_bottom),
            (cx_right, cy_bottom),
        ]

        for cx, cy in corners:
            final_cx = (w_pt - cx) if is_back else cx
            shape.draw_circle(fitz.Point(final_cx, cy), radius_pt)
            shape.draw_line(fitz.Point(final_cx, cy - (radius_pt * 1.3)), fitz.Point(final_cx, cy + (radius_pt * 1.3)))
            shape.draw_line(fitz.Point(final_cx - (radius_pt * 1.3), cy), fitz.Point(final_cx + (radius_pt * 1.3), cy))

    def _prepare_image_bytes(self, item: ImageInput) -> bytes:
        """Converte entrada (PIL.Image, Path ou str) para bytes PNG prontos para o PyMuPDF."""
        if isinstance(item, Image.Image):
            buf = io.BytesIO()
            item.save(buf, format="PNG")
            return buf.getvalue()
        elif isinstance(item, (str, Path)):
            path = Path(item)
            if not path.exists():
                raise FileNotFoundError(f"Arquivo de imagem não encontrado: {path}")
            return path.read_bytes()
        raise TypeError(f"Tipo de item inválido: {type(item)}")

    def render_pdf(
        self,
        layout: DuplexLayout,
        output_path: Union[str, Path],
        draw_crop_marks: bool = True,
        draw_registration_marks: bool = True,
        corner_registration_marks: bool = False,
    ) -> Path:
        """Gera o arquivo PDF vetorial de duas páginas (Página 1: Frente, Página 2: Verso)."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        sheet = layout.sheet_preset
        w_pt = sheet.width_pt
        h_pt = sheet.height_pt

        doc = fitz.open()

        # ================= PAGE 1: FRENTE =================
        page1 = doc.new_page(width=w_pt, height=h_pt)
        for slot in layout.slots:
            if slot.front_item is not None:
                img_data = self._prepare_image_bytes(slot.front_item)
                rect = fitz.Rect(
                    slot.front_slot.x_pt,
                    slot.front_slot.y_pt,
                    slot.front_slot.x_pt + slot.front_slot.width_pt,
                    slot.front_slot.y_pt + slot.front_slot.height_pt,
                )
                page1.insert_image(rect, stream=img_data)

        shape1 = page1.new_shape()
        if draw_crop_marks:
            for slot in layout.slots:
                self._draw_crop_marks(shape1, slot.front_slot)
        if draw_registration_marks:
            self._draw_sheet_targets(shape1, sheet, is_back=False)
        if corner_registration_marks:
            self._draw_corner_targets(shape1, sheet, is_back=False)
        shape1.finish(width=self.STROKE_WIDTH_PT, color=(0, 0, 0))
        shape1.commit()

        # ================= PAGE 2: VERSO =================
        page2 = doc.new_page(width=w_pt, height=h_pt)
        for slot in layout.slots:
            if slot.back_item is not None:
                img_data = self._prepare_image_bytes(slot.back_item)
                rect = fitz.Rect(
                    slot.back_slot.x_pt,
                    slot.back_slot.y_pt,
                    slot.back_slot.x_pt + slot.back_slot.width_pt,
                    slot.back_slot.y_pt + slot.back_slot.height_pt,
                )
                page2.insert_image(rect, stream=img_data)

        shape2 = page2.new_shape()
        if draw_crop_marks:
            for slot in layout.slots:
                self._draw_crop_marks(shape2, slot.back_slot)
        if draw_registration_marks:
            self._draw_sheet_targets(shape2, sheet, is_back=True)
        if corner_registration_marks:
            self._draw_corner_targets(shape2, sheet, is_back=True)
        shape2.finish(width=self.STROKE_WIDTH_PT, color=(0, 0, 0))
        shape2.commit()

        doc.save(str(output_path))
        doc.close()
        return output_path

    def render_images(
        self,
        layout: DuplexLayout,
        dpi: int = DEFAULT_DPI,
        draw_crop_marks: bool = True,
        draw_registration_marks: bool = True,
    ) -> Tuple[Image.Image, Image.Image]:
        """Renderiza a folha duplex como tupla de imagens Pillow (frente, verso) a 300 DPI."""
        # Cria um PDF temporário em memória para manter fidelidade vetorial absoluta
        pdf_bytes = io.BytesIO()
        sheet = layout.sheet_preset
        w_pt = sheet.width_pt
        h_pt = sheet.height_pt

        doc = fitz.open()

        # Página 1 (Frente)
        page1 = doc.new_page(width=w_pt, height=h_pt)
        for slot in layout.slots:
            if slot.front_item is not None:
                img_data = self._prepare_image_bytes(slot.front_item)
                rect = fitz.Rect(
                    slot.front_slot.x_pt,
                    slot.front_slot.y_pt,
                    slot.front_slot.x_pt + slot.front_slot.width_pt,
                    slot.front_slot.y_pt + slot.front_slot.height_pt,
                )
                page1.insert_image(rect, stream=img_data)
        shape1 = page1.new_shape()
        if draw_crop_marks:
            for slot in layout.slots:
                self._draw_crop_marks(shape1, slot.front_slot)
        if draw_registration_marks:
            self._draw_sheet_targets(shape1, sheet, is_back=False)
        shape1.finish(width=self.STROKE_WIDTH_PT, color=(0, 0, 0))
        shape1.commit()

        # Página 2 (Verso)
        page2 = doc.new_page(width=w_pt, height=h_pt)
        for slot in layout.slots:
            if slot.back_item is not None:
                img_data = self._prepare_image_bytes(slot.back_item)
                rect = fitz.Rect(
                    slot.back_slot.x_pt,
                    slot.back_slot.y_pt,
                    slot.back_slot.x_pt + slot.back_slot.width_pt,
                    slot.back_slot.y_pt + slot.back_slot.height_pt,
                )
                page2.insert_image(rect, stream=img_data)
        shape2 = page2.new_shape()
        if draw_crop_marks:
            for slot in layout.slots:
                self._draw_crop_marks(shape2, slot.back_slot)
        if draw_registration_marks:
            self._draw_sheet_targets(shape2, sheet, is_back=True)
        shape2.finish(width=self.STROKE_WIDTH_PT, color=(0, 0, 0))
        shape2.commit()

        doc_bytes = doc.tobytes()
        doc.close()

        rendered_doc = fitz.open(stream=doc_bytes, filetype="pdf")
        target_w = mm_to_px(sheet.width_mm, dpi)
        target_h = mm_to_px(sheet.height_mm, dpi)

        # Matriz calculada para casar exatamente com target_w e target_h
        mat = fitz.Matrix(target_w / w_pt, target_h / h_pt)

        pix1 = rendered_doc[0].get_pixmap(matrix=mat, alpha=False)
        front_image = Image.frombytes("RGB", (pix1.width, pix1.height), pix1.samples)
        if front_image.size != (target_w, target_h):
            front_image = front_image.crop((0, 0, target_w, target_h))

        pix2 = rendered_doc[1].get_pixmap(matrix=mat, alpha=False)
        back_image = Image.frombytes("RGB", (pix2.width, pix2.height), pix2.samples)
        if back_image.size != (target_w, target_h):
            back_image = back_image.crop((0, 0, target_w, target_h))

        rendered_doc.close()
        return (front_image, back_image)
