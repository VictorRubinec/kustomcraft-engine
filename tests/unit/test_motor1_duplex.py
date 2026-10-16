"""Testes unitários rigorosos para o Motor 1: Imposição Gráfica e Registro Duplex.

Valida a precisão milimétrica exigida pela Konica Minolta bizhub C558 em folhas
Super A4 e Super A3, comprovando desvio < 0.2mm (tolerância da oficina).
"""

import math
from pathlib import Path
import pytest
import fitz  # PyMuPDF
from PIL import Image

from src.core.presets import get_sheet_preset, get_product_preset, mm_to_px
from src.engines.motor1_imposicao_duplex import (
    ImpositionEngine,
    DuplexLayout,
    SlotPosition,
)


class TestImpositionDuplexMath:
    """Valida a matemática e o alinhamento de duplex no eixo Y."""

    def test_super_a3_9up_tcg_geometric_alignment(self):
        """Valida que em Super A3 (320x450mm), 9 cartas TCG com sangria casam centro a centro."""
        sheet = get_sheet_preset("SUPER_A3")
        product = get_product_preset("TCG_STANDARD")  # 63.5x88.9 + 5mm sangria = 73.5x98.9

        engine = ImpositionEngine()
        layout = engine.create_layout(
            sheet_preset=sheet,
            product_preset=product,
            rows=3,
            cols=3,
            spacing_x_mm=2.0,
            spacing_y_mm=2.0,
        )

        assert len(layout.slots) == 9
        is_aligned, max_dev = layout.validate_alignment(tolerance_mm=0.2)
        assert is_aligned, f"Desalinhamento detectado: {max_dev}mm"
        # O desvio matemático do software deve ser virtualmente zero (< 0.001mm)
        assert max_dev < 0.001

        # Auditoria individual de cada slot
        for slot in layout.slots:
            front = slot.front_slot
            back = slot.back_slot

            # O centro no eixo Y deve ser idêntico
            assert front.center_y_mm == pytest.approx(back.center_y_mm, abs=1e-4)

            # O centro no eixo X deve ser o espelho perfeito na folha: W_sheet - front_cx
            expected_back_cx = sheet.width_mm - front.center_x_mm
            assert back.center_x_mm == pytest.approx(expected_back_cx, abs=1e-4)

            # O desvio euclidiano entre o ponto físico de frente e verso deve ser zero
            dev = math.sqrt((front.center_x_mm - (sheet.width_mm - back.center_x_mm)) ** 2 +
                            (front.center_y_mm - back.center_y_mm) ** 2)
            assert dev < 0.001

    def test_super_a4_6up_tcg_geometric_alignment(self):
        """Valida 6 cartas TCG (grade 2 colunas x 3 linhas) em folha Super A4 (225x320mm)."""
        sheet = get_sheet_preset("SUPER_A4")
        product = get_product_preset("TCG_STANDARD")

        engine = ImpositionEngine()
        layout = engine.create_layout(
            sheet_preset=sheet,
            product_preset=product,
            rows=3,
            cols=2,
            spacing_x_mm=2.0,
            spacing_y_mm=2.0,
        )

        assert len(layout.slots) == 6
        is_aligned, max_dev = layout.validate_alignment(tolerance_mm=0.2)
        assert is_aligned
        assert max_dev < 0.001

    def test_super_a4_9up_cartas_pdf_exact_alignment(self, tmp_path):
        """Valida a grade 3x3 (9 cartas) em Super A4 real calibrada pelo arquivo cartas.pdf."""
        sheet = get_sheet_preset("SUPER_A4")  # 229.92 x 315.12 mm
        engine = ImpositionEngine()

        layout = engine.create_super_a4_9up_layout(
            front_preset_code="TCG_STANDARD_NO_BLEED",
            back_width_mm=68.0,
            back_height_mm=93.0,
            margin_left_mm=11.0,
            margin_top_mm=18.0,
            spacing_x_mm=8.5,
            spacing_y_mm=6.2,
        )

        assert len(layout.slots) == 9
        is_aligned, max_dev = layout.validate_alignment(tolerance_mm=0.2)
        assert is_aligned is True
        assert max_dev < 0.001

        # Valida cantos e espelhamento
        # Slot 0 (coluna 0) da frente -> Slot 0 do verso (coluna 2 do verso)
        s0 = layout.slots[0]
        assert s0.front_slot.col == 0
        assert s0.back_slot.col == 2
        assert s0.front_slot.x_mm == 11.0
        assert s0.front_slot.y_mm == 18.0
        assert s0.front_slot.width_mm == 63.5
        assert s0.front_slot.height_mm == 88.9
        assert s0.back_slot.width_mm == 68.0
        assert s0.back_slot.height_mm == 93.0

        # Renderiza com marcas nos cantos e valida PDF
        pdf_path = tmp_path / "super_a4_9up_test.pdf"
        engine.render_pdf(layout, pdf_path, corner_registration_marks=True)
        assert pdf_path.exists()
        doc = fitz.open(pdf_path)
        assert len(doc) == 2
        assert doc[0].rect.width == pytest.approx(sheet.width_pt, abs=0.5)
        assert doc[0].rect.height == pytest.approx(sheet.height_pt, abs=0.5)
        doc.close()

    def test_column_mirroring_mapping(self):
        """Garante que a coluna 0 da frente corresponda à última coluna do verso."""
        sheet = get_sheet_preset("SUPER_A3")
        product = get_product_preset("TCG_STANDARD")

        engine = ImpositionEngine()
        layout = engine.create_layout(
            sheet_preset=sheet,
            product_preset=product,
            rows=3,
            cols=3,
            spacing_x_mm=0.0,
            spacing_y_mm=0.0,
        )

        # Mapeamento esperado de colunas para 3 colunas:
        # Coluna 0 -> Coluna 2
        # Coluna 1 -> Coluna 1
        # Coluna 2 -> Coluna 0
        for slot in layout.slots:
            assert slot.back_slot.col == (2 - slot.front_slot.col)
            assert slot.back_slot.row == slot.front_slot.row

    def test_overflow_grid_raises_error(self):
        """Garante que grade maior que a folha física levanta ValueError explicativo."""
        sheet = get_sheet_preset("SUPER_A4")  # 225 x 320 mm
        product = get_product_preset("TCG_STANDARD")  # 73.5 x 98.9 mm total

        engine = ImpositionEngine()
        # 4 colunas x 73.5 = 294mm > 225mm da folha
        with pytest.raises(ValueError, match="não cabe na folha"):
            engine.create_layout(
                sheet_preset=sheet,
                product_preset=product,
                rows=2,
                cols=4,
            )

    def test_printer_offset_calibration(self):
        """Garante que offset mecânico da Konica C558 seja aplicado corretamente no verso."""
        sheet = get_sheet_preset("SUPER_A3")
        product = get_product_preset("TCG_STANDARD")

        engine = ImpositionEngine()
        offset_x = 0.5  # 0.5mm de ajuste de pinça
        offset_y = -0.3
        layout = engine.create_layout(
            sheet_preset=sheet,
            product_preset=product,
            rows=3,
            cols=3,
            printer_offset_x_mm=offset_x,
            printer_offset_y_mm=offset_y,
        )

        for slot in layout.slots:
            front = slot.front_slot
            back = slot.back_slot
            expected_back_cx = (sheet.width_mm - front.center_x_mm) + offset_x
            expected_back_cy = front.center_y_mm + offset_y
            assert back.center_x_mm == pytest.approx(expected_back_cx, abs=1e-4)
            assert back.center_y_mm == pytest.approx(expected_back_cy, abs=1e-4)


class TestImpositionRendering:
    """Valida a renderização de PDFs vetoriais e imagens raster a 300 DPI."""

    def test_render_duplex_pdf_structure(self, tmp_path):
        """Gera PDF duplex de 2 páginas e valida dimensões físicas exatas via PyMuPDF."""
        sheet = get_sheet_preset("SUPER_A3")
        product = get_product_preset("TCG_STANDARD")

        engine = ImpositionEngine()
        layout = engine.create_layout(
            sheet_preset=sheet,
            product_preset=product,
            rows=3,
            cols=3,
            spacing_x_mm=2.0,
            spacing_y_mm=2.0,
        )

        # Injeta imagens dummy de teste nos slots
        dummy_front = Image.new("RGB", (750, 1050), (20, 40, 180))
        dummy_back = Image.new("RGB", (750, 1050), (180, 20, 20))
        for slot in layout.slots:
            slot.front_item = dummy_front
            slot.back_item = dummy_back

        pdf_path = tmp_path / "test_duplex_super_a3.pdf"
        engine.render_pdf(layout, pdf_path)

        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0

        # Abre com PyMuPDF e inspeciona
        doc = fitz.open(pdf_path)
        assert len(doc) == 2, "PDF deve conter exatamente 2 páginas (Frente e Verso)"

        page1 = doc[0]
        page2 = doc[1]

        # Tolerância de 0.5 ponto tipográfico
        assert page1.rect.width == pytest.approx(sheet.width_pt, abs=0.5)
        assert page1.rect.height == pytest.approx(sheet.height_pt, abs=0.5)
        assert page2.rect.width == pytest.approx(sheet.width_pt, abs=0.5)
        assert page2.rect.height == pytest.approx(sheet.height_pt, abs=0.5)
        doc.close()

    def test_render_images_dpi_300(self):
        """Valida a renderização raster de folha frente e verso em 300 DPI com Pillow."""
        sheet = get_sheet_preset("SUPER_A4")  # 225 x 320 mm
        product = get_product_preset("TCG_STANDARD")

        engine = ImpositionEngine()
        layout = engine.create_layout(
            sheet_preset=sheet,
            product_preset=product,
            rows=2,
            cols=2,
        )

        dummy_front = Image.new("RGB", (300, 400), (0, 200, 100))
        dummy_back = Image.new("RGB", (300, 400), (200, 100, 0))
        for slot in layout.slots:
            slot.front_item = dummy_front
            slot.back_item = dummy_back

        front_img, back_img = engine.render_images(layout, dpi=300)

        expected_w = mm_to_px(sheet.width_mm, dpi=300)
        expected_h = mm_to_px(sheet.height_mm, dpi=300)

        assert front_img.size == (expected_w, expected_h)
        assert back_img.size == (expected_w, expected_h)
        assert front_img.mode == "RGB"
        assert back_img.mode == "RGB"

    def test_render_pdf_without_marks(self, tmp_path):
        sheet = get_sheet_preset("A4")
        product = get_product_preset("POSTER_A4_V")
        engine = ImpositionEngine()
        layout = engine.create_layout(sheet, product, rows=1, cols=1)

        pdf_path = tmp_path / "poster_no_marks.pdf"
        engine.render_pdf(layout, pdf_path, draw_crop_marks=False, draw_registration_marks=False)
        assert pdf_path.exists()

    def test_image_input_from_file_path(self, tmp_path):
        dummy_file = tmp_path / "card.png"
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        img.save(dummy_file)

        engine = ImpositionEngine()
        data = engine._prepare_image_bytes(dummy_file)
        assert len(data) > 0

        data_str = engine._prepare_image_bytes(str(dummy_file))
        assert len(data_str) > 0

    def test_image_input_file_not_found(self):
        engine = ImpositionEngine()
        with pytest.raises(FileNotFoundError):
            engine._prepare_image_bytes("arquivo_inexistente_12345.png")

    def test_image_input_invalid_type(self):
        engine = ImpositionEngine()
        with pytest.raises(TypeError):
            engine._prepare_image_bytes(12345)


class TestSlotPositionProperties:
    """Valida as propriedades calculadas da classe SlotPosition."""

    def test_slot_position_pt_and_trim(self):
        slot = SlotPosition(
            index=0,
            row=0,
            col=0,
            x_mm=10.0,
            y_mm=20.0,
            width_mm=73.5,
            height_mm=98.9,
            bleed_mm=5.0,
        )
        assert slot.trim_x_mm == 15.0
        assert slot.trim_y_mm == 25.0
        assert slot.trim_width_mm == 63.5
        assert slot.trim_height_mm == 88.9

        assert slot.x_pt == pytest.approx(10.0 * 72.0 / 25.4)
        assert slot.y_pt == pytest.approx(20.0 * 72.0 / 25.4)
        assert slot.width_pt == pytest.approx(73.5 * 72.0 / 25.4)
        assert slot.height_pt == pytest.approx(98.9 * 72.0 / 25.4)
        assert slot.trim_x_pt == pytest.approx(15.0 * 72.0 / 25.4)
        assert slot.trim_y_pt == pytest.approx(25.0 * 72.0 / 25.4)
        assert slot.trim_width_pt == pytest.approx(63.5 * 72.0 / 25.4)
        assert slot.trim_height_pt == pytest.approx(88.9 * 72.0 / 25.4)

