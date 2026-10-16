"""Módulos de regras de negócio, presets de formatos e cálculos gráficos milimétricos."""

from .presets import (
    SheetPreset,
    ProductPreset,
    SHEET_PRESETS,
    PRODUCT_PRESETS,
    mm_to_px,
    px_to_mm,
    mm_to_pt,
    pt_to_mm,
)
from .ssim_validator import (
    SSIMValidator,
    ValidationResult,
    DEFAULT_SSIM_THRESHOLD,
)

__all__ = [
    "SheetPreset",
    "ProductPreset",
    "SHEET_PRESETS",
    "PRODUCT_PRESETS",
    "mm_to_px",
    "px_to_mm",
    "mm_to_pt",
    "pt_to_mm",
    "SSIMValidator",
    "ValidationResult",
    "DEFAULT_SSIM_THRESHOLD",
]
