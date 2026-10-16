"""Testes unitários rigorosos para o Motor 5: Sangria Industrial & Outpaint."""

from pathlib import Path
import pytest
from PIL import Image, ImageDraw

from src.core.presets import get_product_preset, get_sheet_preset, mm_to_px
from src.engines.motor5_sangria_outpaint import BleedEngine, BleedResult
from src.engines.motor1_imposicao_duplex import ImpositionEngine


class TestBleedExpansionMath:
    """Valida a precisão matemática da expansão em mm e pixels a 300 DPI."""

    def test_tcg_standard_exact_5mm_expansion(self):
        """Valida que uma carta 750x1050 px (63.5x88.9mm) com +5mm expande para 868x1168 px."""
        tcg = get_product_preset("TCG_STANDARD")
        engine = BleedEngine(default_bleed_mm=5.0, dpi=300)

        # Imagem na dimensão nominal de corte (750 x 1050)
        img = Image.new("RGB", (750, 1050), color=(50, 100, 150))
        result = engine.apply_bleed(img, bleed_mm=5.0, dpi=300)

        # 5mm a 300 DPI = round(5.0 / 25.4 * 300) = 59 px por lado
        expected_pad_px = mm_to_px(5.0, 300)
        assert expected_pad_px == 59
        assert result.bleed_px_x == 59
        assert result.bleed_px_y == 59

        # Largura total esperada: 750 + (2 * 59) = 868 px
        # Altura total esperada: 1050 + (2 * 59) = 1168 px
        expected_size = (750 + 2 * 59, 1050 + 2 * 59)
        assert result.final_size_px == expected_size
        assert result.image.size == expected_size
        assert result.final_size_px == tcg.total_size_px(300)
        assert result.mode_used == "mirror_edge"

    def test_apply_bleed_for_product_preset(self):
        """Valida aplicação automática de sangria orientada a preset de produto."""
        tcg = get_product_preset("TCG_STANDARD")
        engine = BleedEngine(dpi=300)

        # Mesmo se a imagem vier em tamanho diferente, ela é ajustada para o trim do produto e sangrada
        img = Image.new("RGB", (300, 400), color=(120, 20, 20))
        result = engine.apply_bleed_for_product(img, tcg, dpi=300)

        assert result.original_size_px == (750, 1050)
        assert result.final_size_px == (868, 1168)
        assert result.bleed_mm == 5.0

    def test_zero_bleed_preserves_image(self):
        """Produtos com 0mm de sangria (como canecas) devem manter tamanho intacto."""
        mug = get_product_preset("MUG_CERAMIC")
        engine = BleedEngine(dpi=300)

        img = Image.new("RGB", (2598, 1122), color=(255, 255, 255))
        result = engine.apply_bleed_for_product(img, mug, dpi=300)

        assert result.bleed_mm == 0.0
        assert result.final_size_px == (2598, 1122)
        assert result.mode_used == "none"

    def test_mirror_edge_symmetry_and_continuity(self):
        """Valida que o espelhamento nas bordas reflete os pixels adjacentes."""
        engine = BleedEngine(dpi=300)

        # Cria uma imagem 100x100 com borda esquerda vermelha e direita azul
        img = Image.new("RGB", (100, 100), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.line([(0, 0), (0, 99)], fill=(255, 0, 0))  # Borda x=0 vermelha
        draw.line([(99, 0), (99, 99)], fill=(0, 0, 255))  # Borda x=99 azul

        pad = 10
        res = engine._mirror_edge_bleed(img, pad_x=pad, pad_y=pad, feather_px=0)

        # O pixel em x=pad é a borda original esquerda (vermelha)
        # O pixel em x=pad-1 é a reflexão da borda esquerda (deve ser vermelha)
        assert res.getpixel((pad, 50)) == (255, 0, 0)
        assert res.getpixel((pad - 1, 50)) == (255, 0, 0)

        # Borda direita em x=pad+99 e sua reflexão em x=pad+100 (devem ser azuis)
        assert res.getpixel((pad + 99, 50)) == (0, 0, 255)
        assert res.getpixel((pad + 100, 50)) == (0, 0, 255)


class TestBleedInpaintAndIntegration:
    """Valida o modo inpainting com fallback e a integração direta com o Motor 1."""

    def test_inpaint_handler_invoked(self):
        engine = BleedEngine(dpi=300)
        img = Image.new("RGB", (100, 100), (10, 20, 30))

        def custom_inpaint(image, px_x, px_y):
            # Retorna uma imagem com o padding solicitado preenchido de verde
            new_img = Image.new("RGB", (image.width + 2 * px_x, image.height + 2 * px_y), (0, 255, 0))
            new_img.paste(image, (px_x, px_y))
            return new_img

        result = engine.apply_bleed(
            img,
            bleed_mm=2.0,
            mode="gemini_inpaint",
            inpaint_handler=custom_inpaint,
        )
        assert result.mode_used == "gemini_inpaint"
        assert result.image.getpixel((0, 0)) == (0, 255, 0)

    def test_inpaint_fallback_on_exception(self):
        engine = BleedEngine(dpi=300)
        img = Image.new("RGB", (100, 100), (10, 20, 30))

        def failing_inpaint(image, px_x, px_y):
            raise ConnectionError("API Gemini fora do ar")

        result = engine.apply_bleed(
            img,
            bleed_mm=2.0,
            mode="gemini_inpaint",
            inpaint_handler=failing_inpaint,
        )
        assert "fallback" in result.mode_used
        assert result.image.size == (100 + 2 * result.bleed_px_x, 100 + 2 * result.bleed_px_y)

    def test_direct_pipeline_integration_with_motor1(self, tmp_path):
        """Valida que artes processadas pelo Motor 5 entram direto no Motor 1 gerando PDF."""
        sheet = get_sheet_preset("SUPER_A3")
        tcg = get_product_preset("TCG_STANDARD")

        bleed_engine = BleedEngine(dpi=300)
        imposition_engine = ImpositionEngine()

        # Cria carta frente e verso nominais (750x1050)
        front_raw = Image.new("RGB", (750, 1050), (30, 90, 180))
        back_raw = Image.new("RGB", (750, 1050), (180, 40, 30))

        # Aplica sangria para imposição
        front_bleed, back_bleed = bleed_engine.prepare_for_imposition(front_raw, back_raw, tcg, dpi=300)
        assert front_bleed.size == (868, 1168)
        assert back_bleed.size == (868, 1168)

        # Monta grade duplex no Motor 1
        layout = imposition_engine.create_layout(sheet, tcg, rows=3, cols=3, spacing_x_mm=2.0, spacing_y_mm=2.0)
        for slot in layout.slots:
            slot.front_item = front_bleed
            slot.back_item = back_bleed

        output_pdf = tmp_path / "tcg_bleed_duplex.pdf"
        imposition_engine.render_pdf(layout, output_pdf)

        assert output_pdf.exists()
        assert output_pdf.stat().st_size > 0

    def test_file_inputs_and_exceptions(self, tmp_path):
        engine = BleedEngine()
        file_path = tmp_path / "card_input.png"
        img = Image.new("RGB", (100, 100), (50, 50, 50))
        img.save(file_path)

        res_path = engine.apply_bleed(file_path, bleed_mm=2.0)
        assert res_path.image.size[0] > 100

        with pytest.raises(FileNotFoundError):
            engine.apply_bleed("nao_existe.png", bleed_mm=2.0)

        with pytest.raises(TypeError):
            engine.apply_bleed(12345)
