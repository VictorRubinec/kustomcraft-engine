"""Motores de processamento gráfico da Studio Kustom Engine."""

from .motor1_imposicao_duplex import (
    ImpositionEngine,
    DuplexLayout,
    ImpositionSlot,
    SlotPosition,
)
from .motor5_sangria_outpaint import (
    BleedEngine,
    BleedResult,
)
from .motor2_upscaler_gemini import (
    GeminiUpscalerEngine,
    UpscaleResult,
)
from .motor3_estudio_canecas import (
    MugStudioEngine,
    MugResult,
    MugSheetLayout,
)
from .motor4_fabrica_tcg import (
    TCGFactoryEngine,
    PokemonCardSpec,
    MagicCardSpec,
    OnePieceCardSpec,
    OrdemParanormalCardSpec,
    GenericCardSpec,
    AttackSpec,
    FontManager,
)

from .motor6_mockup_threejs import (
    ThreeJSMockupEngine,
    render_mug_mockup,
    render_card_mockup,
    render_poster_mockup,
)
from .motor7_gerador_anuncios import (
    ShopeeAdGenerator,
    InstagramAdGenerator,
    AdTemplateConfig,
    BadgeStyle,
    ThemeMode,
)

__all__ = [
    "ImpositionEngine",
    "DuplexLayout",
    "ImpositionSlot",
    "SlotPosition",
    "BleedEngine",
    "BleedResult",
    "GeminiUpscalerEngine",
    "UpscaleResult",
    "MugStudioEngine",
    "MugResult",
    "MugSheetLayout",
    "TCGFactoryEngine",
    "PokemonCardSpec",
    "MagicCardSpec",
    "OnePieceCardSpec",
    "OrdemParanormalCardSpec",
    "GenericCardSpec",
    "AttackSpec",
    "FontManager",
    "ThreeJSMockupEngine",
    "render_mug_mockup",
    "render_card_mockup",
    "render_poster_mockup",
    "ShopeeAdGenerator",
    "InstagramAdGenerator",
    "AdTemplateConfig",
    "BadgeStyle",
    "ThemeMode",
]

