"""Motor 6: Estúdio de Mockups 3D Headless Three.js da Studio Kustom Engine.

Executa cenas Three.js fotorrealistas via Playwright headless em Chromium com aceleração WebGL,
gerando mockups de produtos (Canecas Cerâmicas, Cartas Colecionáveis TCG com Foil Holográfico
e Pôsteres Emoldurados) com fundo transparente RGBA ou ambientado.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any, Union
from PIL import Image
from playwright.sync_api import sync_playwright


ImageInput = Union[Image.Image, Path, str]


class ThreeJSMockupEngine:
    """Motor de orquestração para renderização fotorrealista de mockups 3D com Three.js."""

    VALID_SCENES = {"mug", "mug_trio", "card", "tcg", "poster", "button", "buttons", "pin"}

    def __init__(self, viewer_html_path: Path | str | None = None) -> None:
        """Inicializa o motor localizando os arquivos HTML e módulos Three.js."""
        package_dir = Path(__file__).resolve().parent

        if viewer_html_path:
            self.viewer_html_path = Path(viewer_html_path).resolve()
        else:
            self.viewer_html_path = (package_dir / "viewer.html").resolve()

        self.three_module_path = (
            self.viewer_html_path.parent / "node_modules" / "three" / "build" / "three.module.js"
        ).resolve()

    def _to_data_url(self, image_input: ImageInput | None) -> str | None:
        """Converte imagem PIL, Path ou string para Data URL base64 formatada."""
        if image_input is None:
            return None

        if isinstance(image_input, (str, Path)):
            path = Path(image_input)
            if not path.exists():
                raise FileNotFoundError(f"Arquivo de arte não encontrado: {path}")
            with Image.open(path) as img:
                return self._pil_to_data_url(img)
        elif isinstance(image_input, Image.Image):
            return self._pil_to_data_url(image_input)
        else:
            raise TypeError(f"Tipo de imagem de entrada não suportado: {type(image_input)}")

    @staticmethod
    def _pil_to_data_url(img: Image.Image) -> str:
        """Converte objeto PIL.Image para Data URL PNG."""
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"

    def render_scene(
        self,
        scene_type: str,
        art: ImageInput | list[ImageInput] | None = None,
        back_art: ImageInput | None = None,
        angle: str = "default",
        resolution: tuple[int, int] = (1024, 1024),
        transparent: bool = True,
        is_holographic: bool = True,
        frame_color: str = "black",
        size_mm: int = 44,
        mode: str = "hero",
        output_path: Path | str | None = None,
    ) -> Image.Image:
        """Renderiza uma cena 3D headless e retorna um PIL.Image."""
        if scene_type not in self.VALID_SCENES:
            raise ValueError(
                f"Cena desconhecida: '{scene_type}'. Cenas válidas: {sorted(self.VALID_SCENES)}"
            )

        width, height = resolution
        if width <= 0 or height <= 0:
            raise ValueError(f"Resolução inválida: {resolution}. Deve ser > 0.")

        arts_data_urls: list[str] = []
        if isinstance(art, (list, tuple)):
            arts_data_urls = [self._to_data_url(a) for a in art if a is not None]  # type: ignore[misc]
            art_data_url = arts_data_urls[0] if arts_data_urls else None
        else:
            art_data_url = self._to_data_url(art)

        back_art_data_url = self._to_data_url(back_art)

        scene_config = {
            "scene": scene_type,
            "width": width,
            "height": height,
            "transparent": transparent,
            "angle": angle,
            "is_holographic": is_holographic,
            "frame_color": frame_color,
            "size_mm": size_mm,
            "button_size": size_mm,
            "mode": mode,
            "art_data_url": art_data_url,
            "arts_data_urls": arts_data_urls,
            "back_art_data_url": back_art_data_url,
        }

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--allow-file-access-from-files",
                    "--enable-webgl",
                    "--use-gl=angle",
                ],
            )
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()

            import json
            # Injeta configuração no contexto antes do carregamento da página
            page.add_init_script(f"window.__SCENE_CONFIG__ = {json.dumps(scene_config)};")

            file_url = self.viewer_html_path.as_uri()
            page.goto(file_url)

            # Aguarda sinalização do Three.js
            page.wait_for_function("window.__RENDER_READY__ === true", timeout=12000)

            err = page.evaluate("window.__RENDER_ERROR__")
            if err:
                browser.close()
                raise RuntimeError(f"Erro na renderização Three.js: {err}")

            screenshot_bytes = page.screenshot(omit_background=transparent)
            browser.close()

        image = Image.open(io.BytesIO(screenshot_bytes))

        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            image.save(out, format="PNG")

        return image

    def render_mug(
        self,
        art: ImageInput,
        angle: str = "front_left",
        resolution: tuple[int, int] = (1024, 1024),
        transparent: bool = True,
        output_path: Path | str | None = None,
    ) -> Image.Image:
        """Renderiza mockup 3D de caneca de cerâmica AAA."""
        return self.render_scene(
            scene_type="mug",
            art=art,
            angle=angle,
            resolution=resolution,
            transparent=transparent,
            output_path=output_path,
        )

    def render_card(
        self,
        front_art: ImageInput,
        back_art: ImageInput | None = None,
        is_holographic: bool = True,
        angle: str = "angle_front",
        resolution: tuple[int, int] = (1024, 1024),
        transparent: bool = True,
        output_path: Path | str | None = None,
    ) -> Image.Image:
        """Renderiza mockup 3D de carta TCG com shader de foil holográfico."""
        return self.render_scene(
            scene_type="card",
            art=front_art,
            back_art=back_art,
            angle=angle,
            resolution=resolution,
            transparent=transparent,
            is_holographic=is_holographic,
            output_path=output_path,
        )

    def render_mug_trio(
        self,
        art: ImageInput,
        resolution: tuple[int, int] = (1024, 1024),
        transparent: bool = True,
        output_path: Path | str | None = None,
    ) -> Image.Image:
        """Renderiza mockup 3D panorâmico de trio de canecas (faces esquerda, central e direita)."""
        return self.render_scene(
            scene_type="mug",
            art=art,
            angle="panoramic_trio",
            resolution=resolution,
            transparent=transparent,
            output_path=output_path,
        )

    def render_poster(
        self,
        poster_art: ImageInput,
        frame_color: str = "black",
        resolution: tuple[int, int] = (1024, 1024),
        transparent: bool = True,
        output_path: Path | str | None = None,
    ) -> Image.Image:
        """Renderiza mockup 3D de pôster papel puro Couché 300g suspenso com acabamento semi-brilho e sombra flutuante."""
        return self.render_scene(
            scene_type="poster",
            art=poster_art,
            frame_color=frame_color,
            resolution=resolution,
            transparent=transparent,
            output_path=output_path,
        )

    def render_button(
        self,
        art: ImageInput,
        size_mm: int = 44,
        mode: str = "hero",
        resolution: tuple[int, int] = (1024, 1024),
        transparent: bool = True,
        output_path: Path | str | None = None,
    ) -> Image.Image:
        """Renderiza mockup 3D de botton americano colecionável com película de poliéster brilhante."""
        return self.render_scene(
            scene_type="button",
            art=art,
            angle=mode,
            size_mm=size_mm,
            mode=mode,
            resolution=resolution,
            transparent=transparent,
            output_path=output_path,
        )

    def render_buttons_grid(
        self,
        art: ImageInput | list[ImageInput],
        size_mm: int = 44,
        resolution: tuple[int, int] = (1024, 1024),
        transparent: bool = True,
        output_path: Path | str | None = None,
    ) -> Image.Image:
        """Renderiza mockup 3D de kit com 6 bottons colecionáveis em grade 2x3."""
        return self.render_scene(
            scene_type="button",
            art=art,
            size_mm=size_mm,
            mode="grid_2x3",
            angle="grid_2x3",
            resolution=resolution,
            transparent=transparent,
            output_path=output_path,
        )


def render_mug_mockup(
    art: ImageInput,
    output_path: Path | str | None = None,
    angle: str = "front_left",
    resolution: tuple[int, int] = (1024, 1024),
    transparent: bool = True,
) -> Image.Image:
    """Função utilitária para renderizar mockup de caneca."""
    engine = ThreeJSMockupEngine()
    return engine.render_mug(
        art=art,
        angle=angle,
        resolution=resolution,
        transparent=transparent,
        output_path=output_path,
    )


def render_mug_trio_mockup(
    art: ImageInput,
    output_path: Path | str | None = None,
    resolution: tuple[int, int] = (1024, 1024),
    transparent: bool = True,
) -> Image.Image:
    """Função utilitária para renderizar mockup panorâmico de trio de canecas."""
    engine = ThreeJSMockupEngine()
    return engine.render_mug_trio(
        art=art,
        resolution=resolution,
        transparent=transparent,
        output_path=output_path,
    )


def render_card_mockup(
    front_art: ImageInput,
    back_art: ImageInput | None = None,
    output_path: Path | str | None = None,
    is_holographic: bool = True,
    angle: str = "angle_front",
    resolution: tuple[int, int] = (1024, 1024),
    transparent: bool = True,
) -> Image.Image:
    """Função utilitária para renderizar mockup de carta TCG."""
    engine = ThreeJSMockupEngine()
    return engine.render_card(
        front_art=front_art,
        back_art=back_art,
        is_holographic=is_holographic,
        angle=angle,
        resolution=resolution,
        transparent=transparent,
        output_path=output_path,
    )


def render_poster_mockup(
    poster_art: ImageInput,
    output_path: Path | str | None = None,
    frame_color: str = "black",
    resolution: tuple[int, int] = (1024, 1024),
    transparent: bool = True,
) -> Image.Image:
    """Função utilitária para renderizar mockup de pôster papel puro Couché 300g."""
    engine = ThreeJSMockupEngine()
    return engine.render_poster(
        poster_art=poster_art,
        frame_color=frame_color,
        resolution=resolution,
        transparent=transparent,
        output_path=output_path,
    )


def render_button_mockup(
    art: ImageInput,
    size_mm: int = 44,
    mode: str = "hero",
    output_path: Path | str | None = None,
    resolution: tuple[int, int] = (1024, 1024),
    transparent: bool = True,
) -> Image.Image:
    """Função utilitária para renderizar mockup de botton americano individual ou grid."""
    engine = ThreeJSMockupEngine()
    return engine.render_button(
        art=art,
        size_mm=size_mm,
        mode=mode,
        resolution=resolution,
        transparent=transparent,
        output_path=output_path,
    )


def render_buttons_grid_mockup(
    art: ImageInput | list[ImageInput],
    size_mm: int = 44,
    output_path: Path | str | None = None,
    resolution: tuple[int, int] = (1024, 1024),
    transparent: bool = True,
) -> Image.Image:
    """Função utilitária para renderizar mockup de kit de 6 bottons em grade 2x3."""
    engine = ThreeJSMockupEngine()
    return engine.render_buttons_grid(
        art=art,
        size_mm=size_mm,
        resolution=resolution,
        transparent=transparent,
        output_path=output_path,
    )
