"""Testes unitários rigorosos para o Motor 4: Fábrica de Cartas TCG/RPG.

Inclui o teste de esteira completa (End-to-End):
JSON/Spec -> Motor 4 (Composição) -> Motor 5 (Sangria +5mm) -> Motor 1 (Imposição Duplex Super A3).
"""

from pathlib import Path
import pytest
import fitz  # PyMuPDF
from PIL import Image

from src.core.presets import get_product_preset, get_sheet_preset
from src.engines.motor4_fabrica_tcg import (
    TCGFactoryEngine,
    PokemonCardSpec,
    MagicCardSpec,
    OnePieceCardSpec,
    OrdemParanormalCardSpec,
    GenericCardSpec,
    AttackSpec,
    FontManager,
)
from src.engines.motor5_sangria_outpaint import BleedEngine
from src.engines.motor1_imposicao_duplex import ImpositionEngine


class TestTCGSchemasAndCardComposition:
    """Valida a construção e tipagem de cada categoria de carta homologada."""

    def test_pokemon_card_composition(self):
        engine = TCGFactoryEngine(dpi=300)
        spec = PokemonCardSpec(
            name="Charizard",
            hp=120,
            energy_type="Fire",
            attacks=[
                AttackSpec(name="Fire Spin", cost="{R}{R}{R}{R}", damage="100", effect="Discarte 2 energias ligadas a este Pokémon.")
            ],
            weakness="Water",
            retreat_cost=3,
        )

        card_img = engine.build_pokemon_card(spec)
        assert card_img.size == (750, 1050)
        assert card_img.mode == "RGB"

    def test_magic_card_composition(self):
        engine = TCGFactoryEngine(dpi=300)
        dummy_art = Image.new("RGB", (200, 200), (200, 50, 50))
        spec = MagicCardSpec(
            name="Jace, o Escultor de Mentes",
            mana_cost="{2}{U}{U}",
            card_type="Planeswalker Lendário — Jace",
            text_box="+2: Olhe o card do topo do grimório de um jogador.\n0: Compre três cards e coloque dois cards da sua mão no topo.",
            power_toughness="4/4",
            frame_color="Blue",
        )

        card_img = engine.build_magic_card(spec, art_image=dummy_art)
        assert card_img.size == (750, 1050)
        assert card_img.mode == "RGB"

    def test_pokemon_with_art_and_varied_attacks(self, tmp_path):
        engine = TCGFactoryEngine(dpi=300)
        art_file = tmp_path / "pikachu_art.png"
        Image.new("RGB", (300, 300), (255, 255, 0)).save(art_file)

        spec = PokemonCardSpec(
            name="Pikachu",
            hp=60,
            energy_type="Lightning",
            attacks=[
                AttackSpec(name="Agility", cost="{L}", damage="", effect="Jogue uma moeda. Se der cara, previna todo o dano."),
                AttackSpec(name="Thunderbolt", cost="{L}{L}{C}", damage="80", effect="Discarte todas as energias.")
            ],
            weakness="Fighting",
            resistance="Metal",
            retreat_cost=1,
            art_path=str(art_file),
        )

        card_img = engine.build_pokemon_card(spec)
        assert card_img.size == (750, 1050)

    def test_onepiece_card_composition(self):
        engine = TCGFactoryEngine(dpi=300)
        spec = OnePieceCardSpec(
            name="Monkey D. Luffy",
            cost=5,
            attribute="Golpe",
            power=6000,
            effect="[Rush] (Este card pode atacar no turno em que é jogado).",
            trigger="Compre 1 carta.",
            color="Red",
        )

        card_img = engine.build_onepiece_card(spec)
        assert card_img.size == (750, 1050)
        assert card_img.mode == "RGB"

    def test_ordem_paranormal_card_composition(self):
        engine = TCGFactoryEngine(dpi=300)
        spec = OrdemParanormalCardSpec(
            name="Decadência",
            element="Morte",
            circle=1,
            pe_cost=1,
            effect="Você estende as mãos na direção do alvo, emanando espirais de tempo que apodrecem a matéria biológica.",
            range_desc="Curto",
            duration="Instantânea",
        )

        card_img = engine.build_ordem_paranormal_card(spec)
        assert card_img.size == (750, 1050)
        assert card_img.mode == "RGB"

    def test_generic_card_japanese_format(self):
        """Valida formato Japonês (59x86 mm -> 697x1016 px a 300 DPI)."""
        engine = TCGFactoryEngine(dpi=300)
        spec = GenericCardSpec(
            title="Mago Negro",
            subtitle="Monstro Normal",
            attributes={"Nível": "7", "ATK": "2500", "DEF": "2100"},
            description="O mago definitivo em termos de ataque e defesa.",
            theme_color="#5D3FD3",
        )

        card_img = engine.build_generic_card(spec, product_code="TCG_JAPANESE")
        assert card_img.size == (697, 1016)

    def test_official_card_back_rendering(self):
        engine = TCGFactoryEngine(dpi=300)
        back_img = engine.render_official_card_back(product_code="TCG_STANDARD")
        assert back_img.size == (750, 1050)
        assert back_img.mode == "RGB"

    def test_font_manager_fallback(self):
        """Garante que a ausência de uma fonte carrega o fallback padrão sem levantar exceção."""
        font = FontManager.load_font("Inexistent_Font_XYZ_123.ttf", size=24)
        assert font is not None


class TestEndToEndProductionPipeline:
    """Valida a esteira completa integrada:

    Fábrica TCG (Motor 4) -> Sangria +5mm (Motor 5) -> Imposição Duplex Super A3 (Motor 1)
    """

    def test_e2e_deck_imposition_duplex(self, tmp_path):
        sheet = get_sheet_preset("SUPER_A3")
        tcg = get_product_preset("TCG_STANDARD")

        tcg_factory = TCGFactoryEngine(dpi=300)
        bleed_engine = BleedEngine(dpi=300)
        imposition_engine = ImpositionEngine()

        # 1. Cria baralho de 9 cartas com specs reais
        card_specs = [
            PokemonCardSpec(name=f"Pokémon #{i+1}", hp=70 + (i * 10), energy_type="Water", attacks=[AttackSpec(name="Water Gun", damage=str(20 + i*5))])
            for i in range(9)
        ]

        front_images = [tcg_factory.build_pokemon_card(spec) for spec in card_specs]
        official_back = tcg_factory.render_official_card_back()

        # 2. Motor 5 aplica sangria de +5mm por lado em todas as cartas
        prepared_pairs = []
        for front in front_images:
            front_bleed, back_bleed = bleed_engine.prepare_for_imposition(front, official_back, tcg, dpi=300)
            # Confirma que a sangria expandiu para 868 x 1168 px
            assert front_bleed.size == (868, 1168)
            assert back_bleed.size == (868, 1168)
            prepared_pairs.append((front_bleed, back_bleed))

        # 3. Motor 1 aloca grade 3x3 (9 cartas) em folha Super A3 duplex
        layout = imposition_engine.create_layout(
            sheet_preset=sheet,
            product_preset=tcg,
            rows=3,
            cols=3,
            spacing_x_mm=2.0,
            spacing_y_mm=2.0,
        )

        for i, (f_img, b_img) in enumerate(prepared_pairs):
            layout.slots[i].front_item = f_img
            layout.slots[i].back_item = b_img

        # 4. Auditoria de alinhamento matemático rigoroso
        is_aligned, max_dev = layout.validate_alignment(tolerance_mm=0.2)
        assert is_aligned is True
        assert max_dev < 0.001

        # 5. Renderiza PDF duplex pronto para envio à Konica C558
        output_pdf = tmp_path / "super_a3_duplex_e2e.pdf"
        imposition_engine.render_pdf(layout, output_pdf)

        assert output_pdf.exists()
        assert output_pdf.stat().st_size > 0

        # Inspeciona páginas geradas no PyMuPDF
        doc = fitz.open(output_pdf)
        assert len(doc) == 2, "Deve conter exatamente 2 páginas: Frente e Verso"
        assert doc[0].rect.width == pytest.approx(sheet.width_pt, abs=0.5)
        assert doc[0].rect.height == pytest.approx(sheet.height_pt, abs=0.5)
        assert doc[1].rect.width == pytest.approx(sheet.width_pt, abs=0.5)
        assert doc[1].rect.height == pytest.approx(sheet.height_pt, abs=0.5)
        doc.close()
