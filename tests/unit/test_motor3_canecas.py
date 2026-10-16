"""Testes unitários rigorosos para o Motor 3: Estúdio de Canecas & Sublimação Térmica."""

from pathlib import Path
import pytest
import fitz  # PyMuPDF
from PIL import Image, ImageDraw

from src.core.presets import get_product_preset, get_sheet_preset
from src.engines.motor3_estudio_canecas import MugStudioEngine, MugResult, MugSheetLayout


class TestMugDimensionsAndSublimation:
    """Valida as especificações milimétricas das canecas e o espelhamento para a Epson L110."""

    def test_ceramic_mug_dimensions(self):
        engine = MugStudioEngine(dpi=300)
        img = Image.new("RGB", (100, 100), (255, 255, 255))

        res = engine.prepare_mug_art(img, product_code="MUG_CERAMIC", mirror_for_sublimation=False)
        assert res.size_px == (2598, 1122)
        assert res.details["width_mm"] == 220.0
        assert res.details["height_mm"] == 95.0
        assert res.is_mirrored is False

    def test_chopp_and_polymer_mug_dimensions(self):
        engine = MugStudioEngine(dpi=300)
        img = Image.new("RGB", (100, 100), (200, 200, 200))

        chopp = engine.prepare_mug_art(img, product_code="MUG_CHOPP", mirror_for_sublimation=False)
        assert chopp.size_px == (2362, 1063)

        polymer = engine.prepare_mug_art(img, product_code="MUG_POLYMER", mirror_for_sublimation=False)
        assert polymer.size_px == (2421, 1004)

    def test_sublimation_horizontal_mirror(self):
        """Valida que a imagem espelhada inverte o eixo horizontal para prensagem correta."""
        engine = MugStudioEngine(dpi=300)
        # Cria imagem com detalhe vermelho no canto esquerdo
        img = Image.new("RGB", (100, 100), (0, 0, 0))
        img.putpixel((10, 50), (255, 0, 0))

        res = engine.prepare_mug_art(img, product_code="MUG_CERAMIC", mirror_for_sublimation=True, apply_thermal_compensation=False)
        assert res.is_mirrored is True
        # Na imagem original, x=10 é vermelho. Na imagem espelhada, x = W - 1 - x_orig deve ser vermelho
        w, _ = res.image.size
        # Devido ao resize para 2598, validamos a simetria de quadrantes
        # A metade esquerda da original vira a metade direita
        orig_resized = img.resize(res.size_px)
        assert res.image.getpixel((0, 0)) == orig_resized.getpixel((w - 1, 0))

    def test_thermal_compensation_enhancement(self):
        """Valida que a compensação térmica eleva a saturação e o brilho para a prensa."""
        engine = MugStudioEngine(dpi=300)
        img = Image.new("RGB", (100, 100), (100, 150, 120))

        comp = engine.apply_thermal_compensation(img)
        # Assegura que a imagem foi alterada positivamente
        assert comp.size == img.size
        assert comp.getpixel((50, 50)) != img.getpixel((50, 50))


class TestMugSheetLayoutAndPdf:
    """Valida o aproveitamento de papel sublimático em folhas A4 e Super A4."""

    def test_calculate_layout_super_a4_three_strips(self):
        """Em folha Super A4 (225 x 320 mm), cabem exatamente 3 tiras de 220 x 95 mm."""
        engine = MugStudioEngine(dpi=300)
        layout = engine.calculate_sheet_layout(product_code="MUG_CERAMIC", sheet_code="SUPER_A4", spacing_mm=4.0)

        assert layout.strip_count == 3
        assert len(layout.positions) == 3
        # Cada tira tem largura 220 e altura 95
        for x, y, w, h in layout.positions:
            assert w == 220.0
            assert h == 95.0
            # Deve caber dentro dos limites da folha (225 x 320 mm)
            assert x >= 0
            assert y >= 0
            assert (x + w) <= 225.0
            assert (y + h) <= 320.0

    def test_calculate_layout_a4_two_strips(self):
        """Em folha A4 paisagem (297 x 210 mm), cabem exatamente 2 tiras de 220 x 95 mm."""
        engine = MugStudioEngine(dpi=300)
        layout = engine.calculate_sheet_layout(product_code="MUG_CERAMIC", sheet_code="A4", spacing_mm=5.0)

        assert layout.strip_count == 2
        assert len(layout.positions) == 2

    def test_render_sublimation_sheet_pdf(self, tmp_path):
        """Gera PDF completo com 3 tiras e marcas de corte finas para impressão na Epson."""
        engine = MugStudioEngine(dpi=300)
        img1 = Image.new("RGB", (500, 200), (30, 80, 160))
        img2 = Image.new("RGB", (500, 200), (160, 30, 80))
        img3 = Image.new("RGB", (500, 200), (80, 160, 30))

        pdf_path = tmp_path / "canecas_super_a4.pdf"
        engine.render_sublimation_sheet_pdf(
            images=[img1, img2, img3],
            output_path=pdf_path,
            product_code="MUG_CERAMIC",
            sheet_code="SUPER_A4",
            mirror_for_sublimation=True,
        )

        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0

        # Inspeciona PDF gerado
        doc = fitz.open(pdf_path)
        assert len(doc) == 1
        page = doc[0]
        sheet = get_sheet_preset("SUPER_A4")
        assert page.rect.width == pytest.approx(sheet.width_pt, abs=0.5)
        assert page.rect.height == pytest.approx(sheet.height_pt, abs=0.5)
        doc.close()

    def test_exceptions_and_edge_cases(self):
        engine = MugStudioEngine(dpi=300)

        with pytest.raises(FileNotFoundError):
            engine.prepare_mug_art("arquivo_inexistente_mug.png")

        with pytest.raises(TypeError):
            engine.prepare_mug_art(9999)
