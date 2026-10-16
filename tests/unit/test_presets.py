"""Testes unitários para o módulo de presets e conversões milimétricas."""

import pytest
from src.core.presets import (
    SHEET_PRESETS,
    PRODUCT_PRESETS,
    SheetPreset,
    ProductPreset,
    get_sheet_preset,
    get_product_preset,
    mm_to_px,
    px_to_mm,
    mm_to_pt,
    pt_to_mm,
    INCH_TO_MM,
    POINTS_PER_INCH,
)


class TestConversions:
    """Valida as fórmulas de conversão entre mm, pixels (300 DPI) e pontos tipográficos."""

    def test_mm_to_px_exact_inch(self):
        # 1 polegada = 25.4 mm deve resultar em exatamente 300 pixels a 300 DPI
        assert mm_to_px(25.4, dpi=300) == 300

    def test_px_to_mm_exact_inch(self):
        assert px_to_mm(300, dpi=300) == pytest.approx(25.4, rel=1e-5)

    def test_mm_to_pt_exact_inch(self):
        # 1 polegada = 25.4 mm deve resultar em exatamente 72 pontos tipográficos
        assert mm_to_pt(25.4) == pytest.approx(72.0, rel=1e-5)

    def test_pt_to_mm_exact_inch(self):
        assert pt_to_mm(72.0) == pytest.approx(25.4, rel=1e-5)


class TestSheetPresets:
    """Valida os formatos de folha para o parque gráfico (Konica Minolta C558 e Epson T3170)."""

    def test_super_a4_dimensions(self):
        # Folha calibrada do chão de fábrica real da Studio Kustom (cartas.pdf)
        preset = get_sheet_preset("SUPER_A4")
        assert preset.width_mm == pytest.approx(229.92, abs=0.01)
        assert preset.height_mm == pytest.approx(315.12, abs=0.01)
        assert preset.width_pt == pytest.approx(651.75, abs=0.05)
        assert preset.height_pt == pytest.approx(893.25, abs=0.05)

        # Formato comercial genérico
        standard = get_sheet_preset("SUPER_A4_STANDARD")
        assert standard.width_mm == 225.0
        assert standard.height_mm == 320.0

    def test_super_a3_dimensions(self):
        preset = get_sheet_preset("SUPER_A3")
        assert preset.width_mm == 320.0
        assert preset.height_mm == 450.0

    def test_super_a3_extended_dimensions(self):
        preset = get_sheet_preset("SUPER_A3_EXTENDED")
        assert preset.width_mm == 329.0
        assert preset.height_mm == 483.0

    def test_iso_paper_sizes(self):
        a4 = get_sheet_preset("A4")
        assert a4.width_mm == 210.0
        assert a4.height_mm == 297.0
        assert a4.size_px(300) == (2480, 3508)

        a3 = get_sheet_preset("A3")
        assert a3.width_mm == 297.0
        assert a3.height_mm == 420.0
        assert a3.size_px(300) == (3508, 4961)

    def test_sheet_orientation_toggle(self):
        sa3 = get_sheet_preset("SUPER_A3")  # 320x450
        landscape = sa3.as_landscape()
        assert landscape.width_mm == 450.0
        assert landscape.height_mm == 320.0

        portrait = landscape.as_portrait()
        assert portrait.width_mm == 320.0
        assert portrait.height_mm == 450.0

    def test_unknown_sheet_raises_keyerror(self):
        with pytest.raises(KeyError):
            get_sheet_preset("INVENTED_SHEET_XYZ")


class TestProductPresets:
    """Valida as especificações de produtos homologados da Studio Kustom."""

    def test_tcg_standard_dimensions_and_bleed(self):
        tcg = get_product_preset("TCG_STANDARD")
        # Tamanho nominal
        assert tcg.width_mm == 63.5
        assert tcg.height_mm == 88.9
        assert tcg.bleed_mm == 5.0
        assert tcg.corner_radius_mm == 3.0
        assert tcg.safe_margin_mm == 3.0

        # Pixels nominais (300 DPI)
        assert tcg.trim_size_px(300) == (750, 1050)

        # Tamanho total com sangria industrial (+5mm por lado = +10mm total)
        assert tcg.total_width_mm == 73.5
        assert tcg.total_height_mm == 98.9
        assert tcg.total_size_px(300) == (868, 1168)

    def test_tcg_japanese_dimensions(self):
        tcg_jp = get_product_preset("TCG_JAPANESE")
        assert tcg_jp.width_mm == 59.0
        assert tcg_jp.height_mm == 86.0
        assert tcg_jp.trim_size_px(300) == (697, 1016)

    def test_mug_ceramic_dimensions(self):
        mug = get_product_preset("MUG_CERAMIC")
        assert mug.width_mm == 220.0
        assert mug.height_mm == 95.0
        assert mug.trim_size_px(300) == (2598, 1122)

    def test_mug_chopp_dimensions(self):
        chopp = get_product_preset("MUG_CHOPP")
        assert chopp.width_mm == 200.0
        mug_chopp_px = chopp.trim_size_px(300)
        assert mug_chopp_px == (2362, 1063)

    def test_unknown_product_raises_keyerror(self):
        with pytest.raises(KeyError):
            get_product_preset("INEXISTENT_PRODUCT")

    def test_product_pt_properties(self):
        tcg = get_product_preset("TCG_STANDARD")
        assert tcg.trim_width_pt == pytest.approx(mm_to_pt(63.5), abs=1e-4)
        assert tcg.trim_height_pt == pytest.approx(mm_to_pt(88.9), abs=1e-4)
        assert tcg.total_width_pt == pytest.approx(mm_to_pt(73.5), abs=1e-4)
        assert tcg.total_height_pt == pytest.approx(mm_to_pt(98.9), abs=1e-4)
