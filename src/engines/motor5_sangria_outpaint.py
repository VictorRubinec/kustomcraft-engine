"""Motor 5: Sangria Industrial & Outpaint (Studio Kustom Engine).

Responsável por expandir as margens de produtos gráficos (+5mm por lado por padrão)
para garantir corte limpo em guilhotina ou estilete de precisão, eliminando 100% dos
filetes brancos sem comprometer a área útil da arte original.

Modos de Operação:
1. 'mirror_edge': Espelhamento simétrico suave das bordas (modo padrão ultrarrápido e offline).
2. 'gemini_inpaint': Extensão generativa de padrões complexos via API de IA.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageFilter, ImageOps

from src.core.presets import (
    ProductPreset,
    mm_to_px,
    DEFAULT_DPI,
)


@dataclass(frozen=True)
class BleedResult:
    """Resultado da aplicação de sangria industrial."""

    image: Image.Image
    original_size_px: Tuple[int, int]
    final_size_px: Tuple[int, int]
    bleed_mm: float
    bleed_px_x: int
    bleed_px_y: int
    mode_used: str
    dpi: int
    details: Dict[str, Any] = field(default_factory=dict)


class BleedEngine:
    """Motor de cálculo e aplicação de sangria industrial."""

    def __init__(self, default_bleed_mm: float = 5.0, dpi: int = DEFAULT_DPI):
        self.default_bleed_mm = default_bleed_mm
        self.dpi = dpi

    def _mirror_edge_bleed(
        self,
        image: Image.Image,
        pad_x: int,
        pad_y: int,
        feather_px: int = 4,
    ) -> Image.Image:
        """Gera sangria espelhada contínua com suavização (feathering) na junção."""
        img = image.convert("RGB")
        w, h = img.size

        new_w = w + (2 * pad_x)
        new_h = h + (2 * pad_y)
        canvas = Image.new("RGB", (new_w, new_h))

        # 1. Posiciona o conteúdo original no centro
        canvas.paste(img, (pad_x, pad_y))

        # 2. Borda Esquerda (Espelho horizontal da faixa inicial)
        slice_w_left = min(w, pad_x)
        left_slice = img.crop((0, 0, slice_w_left, h))
        left_mirrored = ImageOps.mirror(left_slice)
        # Se pad_x for maior que a largura da imagem, redimensiona para cobrir
        if slice_w_left < pad_x:
            left_mirrored = left_mirrored.resize((pad_x, h), Image.Resampling.LANCZOS)
        canvas.paste(left_mirrored, (0, pad_y))

        # 3. Borda Direita (Espelho horizontal da faixa final)
        slice_w_right = min(w, pad_x)
        right_slice = img.crop((w - slice_w_right, 0, w, h))
        right_mirrored = ImageOps.mirror(right_slice)
        if slice_w_right < pad_x:
            right_mirrored = right_mirrored.resize((pad_x, h), Image.Resampling.LANCZOS)
        canvas.paste(right_mirrored, (pad_x + w, pad_y))

        # 4. Borda Superior (Espelho vertical da faixa do topo da tela intermediária)
        # Usamos o canvas intermediário para incluir a área horizontal já espelhada
        top_slice = canvas.crop((0, pad_y, new_w, pad_y + min(h, pad_y)))
        top_flipped = ImageOps.flip(top_slice)
        if top_flipped.size[1] < pad_y:
            top_flipped = top_flipped.resize((new_w, pad_y), Image.Resampling.LANCZOS)
        canvas.paste(top_flipped, (0, 0))

        # 5. Borda Inferior (Espelho vertical da faixa da base)
        bot_slice = canvas.crop((0, pad_y + h - min(h, pad_y), new_w, pad_y + h))
        bot_flipped = ImageOps.flip(bot_slice)
        if bot_flipped.size[1] < pad_y:
            bot_flipped = bot_flipped.resize((new_w, pad_y), Image.Resampling.LANCZOS)
        canvas.paste(bot_flipped, (0, pad_y + h))

        # 6. Suavização sutil (feathering) nas 4 costuras para evitar degrau rígido
        if feather_px > 0 and pad_x >= feather_px and pad_y >= feather_px:
            # Cria cópia levemente desfocada para blend nas linhas de transição
            blurred = canvas.filter(ImageFilter.GaussianBlur(radius=feather_px / 2.0))

            # Máscara de blend cobrindo apenas a faixa de fronteira
            mask = Image.new("L", (new_w, new_h), 0)
            mask_arr = np.array(mask)

            # Faixas de fronteira (espessura de feather_px)
            half = feather_px // 2
            # Borda vertical esquerda
            mask_arr[:, max(0, pad_x - half):pad_x + half] = 128
            # Borda vertical direita
            mask_arr[:, pad_x + w - half:min(new_w, pad_x + w + half)] = 128
            # Borda horizontal superior
            mask_arr[max(0, pad_y - half):pad_y + half, :] = 128
            # Borda horizontal inferior
            mask_arr[pad_y + h - half:min(new_h, pad_y + h + half), :] = 128

            blend_mask = Image.fromarray(mask_arr)
            canvas = Image.composite(blurred, canvas, blend_mask)

        return canvas

    def apply_bleed(
        self,
        image: Union[Image.Image, Path, str],
        bleed_mm: Optional[float] = None,
        dpi: Optional[int] = None,
        mode: str = "mirror_edge",
        feather_px: int = 4,
        inpaint_handler: Optional[Any] = None,
    ) -> BleedResult:
        """Aplica sangria industrial à imagem.

        Args:
            image: Imagem de entrada (Pillow, Path ou caminho str).
            bleed_mm: Milímetros de sangria por lado (padrão: 5.0mm).
            dpi: Resolução de cálculo (padrão: 300 DPI).
            mode: 'mirror_edge' (padrão) ou 'gemini_inpaint'.
            feather_px: Raio de suavização na linha de costura.
            inpaint_handler: Callback opcional para inpainting generativo.
        """
        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {path}")
            img = Image.open(path).convert("RGB")
        elif isinstance(image, Image.Image):
            img = image.convert("RGB")
        else:
            raise TypeError(f"Tipo de entrada inválido: {type(image)}")

        target_bleed_mm = self.default_bleed_mm if bleed_mm is None else bleed_mm
        target_dpi = self.dpi if dpi is None else dpi

        if target_bleed_mm <= 0.0:
            return BleedResult(
                image=img,
                original_size_px=img.size,
                final_size_px=img.size,
                bleed_mm=0.0,
                bleed_px_x=0,
                bleed_px_y=0,
                mode_used="none",
                dpi=target_dpi,
            )

        pad_px_x = mm_to_px(target_bleed_mm, target_dpi)
        pad_px_y = mm_to_px(target_bleed_mm, target_dpi)

        mode_used = mode
        if mode == "gemini_inpaint" and inpaint_handler is not None:
            try:
                processed_img = inpaint_handler(img, pad_px_x, pad_px_y)
            except Exception as e:
                # Fallback seguro para mirror_edge caso a API falhe
                processed_img = self._mirror_edge_bleed(img, pad_px_x, pad_px_y, feather_px)
                mode_used = f"mirror_edge (fallback: {str(e)})"
        else:
            processed_img = self._mirror_edge_bleed(img, pad_px_x, pad_px_y, feather_px)
            mode_used = "mirror_edge"

        return BleedResult(
            image=processed_img,
            original_size_px=img.size,
            final_size_px=processed_img.size,
            bleed_mm=target_bleed_mm,
            bleed_px_x=pad_px_x,
            bleed_px_y=pad_px_y,
            mode_used=mode_used,
            dpi=target_dpi,
        )

    def apply_bleed_for_product(
        self,
        image: Union[Image.Image, Path, str],
        product_preset: ProductPreset,
        dpi: Optional[int] = None,
        mode: str = "mirror_edge",
    ) -> BleedResult:
        """Aplica sangria baseada estritamente nas especificações do produto."""
        target_dpi = self.dpi if dpi is None else dpi

        # Se a imagem não estiver na resolução nominal do produto, redimensiona primeiro
        if isinstance(image, (str, Path)):
            img = Image.open(image).convert("RGB")
        else:
            img = image.convert("RGB")

        trim_px = product_preset.trim_size_px(target_dpi)
        if img.size != trim_px:
            img = img.resize(trim_px, Image.Resampling.LANCZOS)

        return self.apply_bleed(
            image=img,
            bleed_mm=product_preset.bleed_mm,
            dpi=target_dpi,
            mode=mode,
        )

    def prepare_for_imposition(
        self,
        front_image: Union[Image.Image, Path, str],
        back_image: Union[Image.Image, Path, str],
        product_preset: ProductPreset,
        dpi: Optional[int] = None,
    ) -> Tuple[Image.Image, Image.Image]:
        """Processa par frente e verso com sangria industrial pronto para o Motor 1."""
        target_dpi = self.dpi if dpi is None else dpi
        front_res = self.apply_bleed_for_product(front_image, product_preset, dpi=target_dpi)
        back_res = self.apply_bleed_for_product(back_image, product_preset, dpi=target_dpi)
        return (front_res.image, back_res.image)
