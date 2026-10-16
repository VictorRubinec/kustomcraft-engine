"""Testes unitários para o Motor 7: Gerador de Anúncios Shopee e Instagram."""

import pytest
from pathlib import Path
from PIL import Image

from src.engines.motor7_gerador_anuncios import (
    ShopeeAdGenerator,
    InstagramAdGenerator,
    AdTemplateConfig,
    BadgeStyle,
    ThemeMode,
    get_theme_colors,
)


@pytest.fixture
def sample_mockup():
    """Mockup 3D simples transparente para teste."""
    img = Image.new("RGBA", (800, 800), (0, 0, 0, 0))
    # Desenhar um círculo central opaco
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.ellipse([100, 100, 700, 700], fill=(220, 180, 50, 255))
    return img


class TestMotor7ShopeeAdGenerator:
    """Validação da geração de criativos para vitrine Shopee (1200x1200px) sob o sistema de cores sólidas."""

    def test_theme_mode_personalizado_solid_yellow(self, sample_mockup, tmp_path):
        generator = ShopeeAdGenerator()
        out_file = tmp_path / "shopee_personalizado.png"

        img = generator.gerar_capa_shopee(
            mockup_image=sample_mockup,
            title="CARTA POKÉMON CHARIZARD",
            subtitle="Edição Especial Colecionador • Foil Holográfico",
            badges=["Papel Couché 300g", "Laminação Hi-Tac", "Foil Holográfico"],
            price_tag="R$ 29,90",
            theme_mode=ThemeMode.PERSONALIZADO,
            output_path=out_file,
        )

        assert isinstance(img, Image.Image)
        assert img.size == (1200, 1200)
        assert out_file.exists()

        # Verifica que o fundo no topo é 100% Sólido Amarelo Solar (#FFD500 -> 255, 213, 0)
        pixel_bg = img.getpixel((10, 10))
        assert pixel_bg[:3] == (255, 213, 0)

        # Verifica triângulo roxo no canto inferior direito
        pixel_corner = img.getpixel((1195, 1195))
        assert pixel_corner[:3] == (114, 9, 183)

    def test_theme_mode_arte_pronta_solid_blue(self, sample_mockup, tmp_path):
        generator = ShopeeAdGenerator()
        out_file = tmp_path / "shopee_arte_pronta.png"

        img = generator.gerar_capa_shopee(
            mockup_image=sample_mockup,
            title="DECK BOX EXCLUSIVO",
            subtitle="Coleção Oficial Pronta Entrega",
            badges=["Alta Definição", "Pronta Entrega"],
            theme_mode=ThemeMode.ARTE_PRONTA,
            output_path=out_file,
        )

        assert img.size == (1200, 1200)
        # Fundo 100% Sólido Azul Cobalto (#3B59EC -> 59, 89, 236)
        pixel_bg = img.getpixel((10, 10))
        assert pixel_bg[:3] == (59, 89, 236)

        # Canto inferior direito: triângulo amarelo
        pixel_corner = img.getpixel((1195, 1195))
        assert pixel_corner[:3] == (255, 213, 0)

    def test_theme_mode_informativo_solid_purple(self, sample_mockup, tmp_path):
        generator = ShopeeAdGenerator()
        out_file = tmp_path / "shopee_informativo.png"

        img = generator.gerar_capa_shopee(
            mockup_image=sample_mockup,
            title="COMUNICADO OFICIAL",
            subtitle="Prazos de Produção e Postagem",
            badges=["Chão de Fábrica"],
            theme_mode=ThemeMode.INFORMATIVO,
            output_path=out_file,
        )

        assert img.size == (1200, 1200)
        # Fundo 100% Sólido Roxo Místico (#560BAD -> 86, 11, 173)
        pixel_bg = img.getpixel((10, 10))
        assert pixel_bg[:3] == (86, 11, 173)

        # Canto inferior direito: triângulo amarelo
        pixel_corner = img.getpixel((1195, 1195))
        assert pixel_corner[:3] == (255, 213, 0)

    def test_gerar_lamina_tecnica_shopee(self, sample_mockup, tmp_path):
        generator = ShopeeAdGenerator()
        out_file = tmp_path / "shopee_specs.png"

        specs = {
            "Material": "Papel Couché Premium 300g/m²",
            "Dimensões": "63.5 x 88.9 mm (Padrão TCG Standard)",
            "Acabamento": "Laminação Térmica Fosca Hi-Tac",
            "Corte": "Cantos Arredondados com Cantoneira 3.0mm",
            "Efeito Especial": "Película Holográfica Iridescente",
            "Produção": "Studio Kustom Chão de Fábrica",
        }

        img = generator.gerar_lamina_tecnica_shopee(
            product_type="Carta TCG Colecionável",
            title="ESPECIFICAÇÕES TÉCNICAS",
            specs_dict=specs,
            mockup_image=sample_mockup,
            notice_text="Personalizamos com sua arte em alta resolução!",
            theme_mode=ThemeMode.INFORMATIVO,
            output_path=out_file,
        )

        assert img.size == (1200, 1200)
        assert out_file.exists()
        # Verifica fundo roxo sólido
        pixel_bg = img.getpixel((10, 10))
        assert pixel_bg[:3] == (86, 11, 173)

    def test_shopee_custom_palette(self, sample_mockup):
        custom_config = AdTemplateConfig(
            theme_mode=ThemeMode.PERSONALIZADO,
            primary_color=(80, 10, 160),
            accent_color=(255, 215, 0),
            badge_style=BadgeStyle.OUTLINE,
        )
        generator = ShopeeAdGenerator(config=custom_config)
        img = generator.gerar_capa_shopee(
            mockup_image=sample_mockup,
            title="PRODUTO AUTORAL",
            subtitle="Qualidade Gráfica Industrial",
            badges=["Couché 300g"],
        )
        assert img.size == (1200, 1200)


class TestMotor7InstagramAdGenerator:
    """Validação da geração de carrosséis e posts para Instagram Feed."""

    def test_gerar_carrossel_instagram_4_5(self, sample_mockup, tmp_path):
        generator = InstagramAdGenerator()
        benefits = [
            "Fidelidade milimétrica com gramatura 300g real",
            "Película Hi-Tac anti-risco e anti-descolamento",
            "Brilho holográfico iridescente de alto impacto",
            "Cantos arredondados raio 3mm sem rebarbas",
        ]

        slides = generator.gerar_carrossel_instagram(
            mockup_images=[sample_mockup, sample_mockup, sample_mockup],
            title="TRANSFORME SUA ARTE EM CARTA COLECIONÁVEL",
            benefits_list=benefits,
            cta_text="Peça agora pelo link da bio • Enviamos para todo o Brasil",
            format_ratio="4:5",
            theme_mode=ThemeMode.PERSONALIZADO,
            output_dir=tmp_path,
        )

        assert len(slides) == 3
        for i, slide in enumerate(slides):
            assert isinstance(slide, Image.Image)
            assert slide.size == (1080, 1350)
            assert (tmp_path / f"carrossel_lamina_{i+1}.png").exists()
            # Fundo sólido amarelo (#FFD500 -> 255, 213, 0)
            assert slide.getpixel((10, 10))[:3] == (255, 213, 0)

    def test_gerar_carrossel_instagram_1_1(self, sample_mockup):
        generator = InstagramAdGenerator()
        benefits = ["Alta definição 300 DPI", "Sublimação térmica pura"]

        slides = generator.gerar_carrossel_instagram(
            mockup_images=[sample_mockup, sample_mockup],
            title="CANECA DE CERÂMICA 325ML",
            benefits_list=benefits,
            format_ratio="1:1",
            theme_mode=ThemeMode.ARTE_PRONTA,
        )

        assert len(slides) == 3  # slide 1 capa, slide 2 benefícios, slide 3 CTA
        for slide in slides:
            assert slide.size == (1080, 1080)
            # Fundo sólido azul (#3B59EC -> 59, 89, 236)
            assert slide.getpixel((10, 10))[:3] == (59, 89, 236)

    def test_input_from_file_path(self, sample_mockup, tmp_path):
        mockup_path = tmp_path / "temp_mockup.png"
        sample_mockup.save(mockup_path)

        generator = ShopeeAdGenerator()
        img = generator.gerar_capa_shopee(
            mockup_image=mockup_path,
            title="TESTE COM PATH",
            subtitle="Teste de carregamento de arquivo",
            badges=["300g"],
        )
        assert img.size == (1200, 1200)

    def test_invalid_format_ratio_raises_error(self, sample_mockup):
        generator = InstagramAdGenerator()
        with pytest.raises(ValueError, match="Formato inválido"):
            generator.gerar_carrossel_instagram(
                mockup_images=[sample_mockup],
                title="TESTE",
                benefits_list=["Benefício"],
                format_ratio="16:9",
            )

    def test_badges_collision_prevention_with_price_tag(self, sample_mockup):
        generator = ShopeeAdGenerator()
        # 3 badges com textos longos + price tag
        img = generator.gerar_capa_shopee(
            mockup_image=sample_mockup,
            title="TESTE COLISÃO",
            subtitle="Subtítulo",
            badges=["Papel Couché 300g Premium", "Laminação Hi-Tac Fosca", "Foil Holográfico Iridescente"],
            price_tag="R$ 49,90",
            theme_mode=ThemeMode.PERSONALIZADO,
        )
        assert img.size == (1200, 1200)

    def test_mockup_clearance_and_shadow_modes(self, sample_mockup):
        generator = ShopeeAdGenerator()
        # Sem sombra artificial (Three.js puro)
        img_no_shadow = generator.gerar_capa_shopee(
            mockup_image=sample_mockup,
            title="SEM SOMBRA PILLOW",
            subtitle="Subtítulo",
            badges=["Badge 1", "Badge 2"],
            apply_pillow_shadow=False,
        )
        assert img_no_shadow.size == (1200, 1200)

        # Com sombra artificial duplicada
        img_with_shadow = generator.gerar_capa_shopee(
            mockup_image=sample_mockup,
            title="COM SOMBRA PILLOW",
            subtitle="Subtítulo",
            badges=["Badge 1", "Badge 2"],
            apply_pillow_shadow=True,
        )
        assert img_with_shadow.size == (1200, 1200)
        assert img_no_shadow.tobytes() != img_with_shadow.tobytes()

