"""Testes unitários e de integração para o Motor 6: Estúdio de Mockups 3D Three.js."""

import pytest
from pathlib import Path
from PIL import Image

from src.engines.motor6_mockup_threejs import (
    ThreeJSMockupEngine,
    render_mug_mockup,
    render_mug_trio_mockup,
    render_card_mockup,
    render_poster_mockup,
    render_button_mockup,
    render_buttons_grid_mockup,
)


@pytest.fixture
def sample_art_mug():
    """Gera uma arte simples de caneca para teste (proporção 220x95)."""
    img = Image.new("RGBA", (440, 190), color=(200, 30, 30, 255))
    return img


@pytest.fixture
def sample_art_card():
    """Gera uma arte simples de carta para teste (proporção 63.5x88.9)."""
    img = Image.new("RGBA", (300, 420), color=(40, 120, 220, 255))
    return img


@pytest.fixture
def sample_art_poster():
    """Gera uma arte simples de pôster para teste (proporção A4/A3)."""
    img = Image.new("RGBA", (300, 420), color=(30, 180, 80, 255))
    return img


class TestMotor6ThreeJSMockupEngine:
    """Valida o funcionamento do motor Three.js headless com Playwright."""

    def test_engine_initialization(self):
        engine = ThreeJSMockupEngine()
        assert engine.viewer_html_path.exists()
        assert engine.three_module_path.exists()

    def test_render_mug_mockup_transparent(self, sample_art_mug):
        engine = ThreeJSMockupEngine()
        mockup = engine.render_mug(
            art=sample_art_mug,
            angle="front_left",
            resolution=(512, 512),
            transparent=True,
        )

        assert isinstance(mockup, Image.Image)
        assert mockup.size == (512, 512)
        assert mockup.mode == "RGBA"
        # Deve ter pixels opacos e pixels transparentes (fundo transparente)
        alpha = mockup.getchannel("A")
        min_a, max_a = alpha.getextrema()
        assert min_a == 0  # fundo transparente
        assert max_a > 200  # caneca visível

    def test_render_mug_angles(self, sample_art_mug):
        engine = ThreeJSMockupEngine()
        img_left = engine.render_mug(sample_art_mug, angle="front_left", resolution=(256, 256))
        img_right = engine.render_mug(sample_art_mug, angle="front_right", resolution=(256, 256))
        assert img_left.size == (256, 256)
        assert img_right.size == (256, 256)
        # As imagens de ângulos diferentes devem diferir visualmente
        assert img_left.tobytes() != img_right.tobytes()

    def test_render_card_mockup_standard_and_holo(self, sample_art_card):
        engine = ThreeJSMockupEngine()
        # Carta padrão sem foil
        card_std = engine.render_card(
            front_art=sample_art_card,
            is_holographic=False,
            angle="angle_front",
            resolution=(512, 512),
        )
        assert card_std.size == (512, 512)
        assert card_std.mode == "RGBA"

        # Carta com foil holográfico
        card_holo = engine.render_card(
            front_art=sample_art_card,
            is_holographic=True,
            angle="angle_front",
            resolution=(512, 512),
        )
        assert card_holo.size == (512, 512)
        assert card_holo.mode == "RGBA"
        # O shader de foil com iridescência altera a reflexão na renderização
        assert card_holo.tobytes() != card_std.tobytes()

    def test_render_card_with_back(self, sample_art_card):
        engine = ThreeJSMockupEngine()
        back_art = Image.new("RGBA", (300, 420), color=(180, 140, 20, 255))
        card_with_back = engine.render_card(
            front_art=sample_art_card,
            back_art=back_art,
            angle="stacked_pair",
            resolution=(512, 512),
        )
        assert card_with_back.size == (512, 512)

    def test_render_poster_mockup(self, sample_art_poster):
        engine = ThreeJSMockupEngine()
        poster = engine.render_poster(
            poster_art=sample_art_poster,
            frame_color="black",
            resolution=(512, 512),
        )
        assert poster.size == (512, 512)
        assert poster.mode == "RGBA"

    def test_helper_functions_and_save_to_path(self, sample_art_mug, tmp_path):
        out_file = tmp_path / "mockup_caneca.png"
        img = render_mug_mockup(
            art=sample_art_mug,
            output_path=out_file,
            resolution=(256, 256),
        )
        assert out_file.exists()
        assert img.size == (256, 256)

        out_card = tmp_path / "mockup_card.png"
        img_card = render_card_mockup(
            front_art=sample_art_mug,
            output_path=out_card,
            resolution=(256, 256),
        )
        assert out_card.exists()
        assert img_card.size == (256, 256)

        out_poster = tmp_path / "mockup_poster.png"
        img_poster = render_poster_mockup(
            poster_art=sample_art_mug,
            output_path=out_poster,
            resolution=(256, 256),
        )
        assert out_poster.exists()
        assert img_poster.size == (256, 256)

    def test_invalid_scene_raises_error(self, sample_art_mug):
        engine = ThreeJSMockupEngine()
        with pytest.raises(ValueError, match="Cena desconhecida"):
            engine.render_scene(scene_type="banana_scene", art=sample_art_mug)

    def test_file_not_found_raises_error(self):
        engine = ThreeJSMockupEngine()
        with pytest.raises(FileNotFoundError):
            engine.render_mug(art=Path("caminho_inexistente_12345.png"))

    def test_invalid_resolution_raises_error(self, sample_art_mug):
        engine = ThreeJSMockupEngine()
        with pytest.raises(ValueError, match="Resolução inválida"):
            engine.render_mug(art=sample_art_mug, resolution=(0, -50))

    def test_invalid_image_input_type_raises_type_error(self):
        engine = ThreeJSMockupEngine()
        with pytest.raises(TypeError, match="Tipo de imagem de entrada não suportado"):
            engine._to_data_url(12345)

    def test_custom_viewer_html_path(self):
        engine = ThreeJSMockupEngine(viewer_html_path=Path("src/engines/motor6_mockup_threejs/viewer.html"))
        assert engine.viewer_html_path.exists()

    def test_render_with_custom_background(self, sample_art_mug):
        engine = ThreeJSMockupEngine()
        img = engine.render_mug(art=sample_art_mug, resolution=(128, 128), transparent=False)
        assert img.size == (128, 128)

    def test_render_from_file_path(self, sample_art_mug, tmp_path):
        f = tmp_path / "art_input.png"
        sample_art_mug.save(f)
        engine = ThreeJSMockupEngine()
        img = engine.render_mug(art=f, resolution=(128, 128))
        assert img.size == (128, 128)

    def test_render_mug_trio(self, sample_art_mug):
        engine = ThreeJSMockupEngine()
        img_trio = engine.render_mug_trio(art=sample_art_mug, resolution=(256, 256))
        assert img_trio.size == (256, 256)
        assert img_trio.mode == "RGBA"
        # Deve ter transparência no fundo
        alpha = img_trio.getchannel("A")
        min_a, max_a = alpha.getextrema()
        assert min_a == 0
        assert max_a > 200

    def test_render_button_hero_and_sizes(self, sample_art_mug):
        engine = ThreeJSMockupEngine()
        # Teste modo hero em 44mm
        btn_44 = engine.render_button(art=sample_art_mug, size_mm=44, mode="hero", resolution=(256, 256))
        assert btn_44.size == (256, 256)
        assert btn_44.mode == "RGBA"

        # Teste modo hero em 32mm
        btn_32 = engine.render_button(art=sample_art_mug, size_mm=32, mode="hero", resolution=(256, 256))
        assert btn_32.size == (256, 256)

        # Imagens de tamanhos diferentes devem renderizar com escalas diferentes
        assert btn_44.tobytes() != btn_32.tobytes()

    def test_render_buttons_grid(self, sample_art_mug):
        engine = ThreeJSMockupEngine()
        grid = engine.render_buttons_grid(art=sample_art_mug, size_mm=44, resolution=(256, 256))
        assert grid.size == (256, 256)
        assert grid.mode == "RGBA"

    def test_new_scene_helper_functions(self, sample_art_mug, tmp_path):
        trio_file = tmp_path / "trio.png"
        btn_file = tmp_path / "btn.png"
        grid_file = tmp_path / "grid.png"

        img_trio = render_mug_trio_mockup(art=sample_art_mug, output_path=trio_file, resolution=(128, 128))
        assert trio_file.exists()
        assert img_trio.size == (128, 128)

        img_btn = render_button_mockup(art=sample_art_mug, size_mm=58, output_path=btn_file, resolution=(128, 128))
        assert btn_file.exists()
        assert img_btn.size == (128, 128)

        img_grid = render_buttons_grid_mockup(art=sample_art_mug, output_path=grid_file, resolution=(128, 128))
        assert grid_file.exists()
        assert img_grid.size == (128, 128)

