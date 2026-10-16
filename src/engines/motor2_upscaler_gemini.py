"""Motor 2: Pipeline de Upscaling Universal (Studio Kustom Engine).

Responsável pela super-resolução e upscaling inteligente de imagens em baixa
resolução para atingir os 300 DPI dos produtos homologados (TCGs, pôsteres e canecas).

Estratégia de Execução:
1. Online / IA: Chamada à API Google Gemini com prompt estrito de super-resolução
   fotorrealista sem alteração de fontes, geometria ou cores.
2. Offline / Fallback: Upscaling determinístico por amostragem Lanczos e filtro
   de máscara de nitidez (UnsharpMask), garantindo continuidade operacional
   independente de conexão de rede ou cotas de API.
"""

from __future__ import annotations
import base64
import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import requests
from dotenv import load_dotenv
from PIL import Image, ImageFilter

from src.core.presets import (
    ProductPreset,
    DEFAULT_DPI,
)

# Carrega variáveis do arquivo .env local se existirem
load_dotenv()


@dataclass(frozen=True)
class UpscaleResult:
    """Resultado auditável da operação de upscaling."""

    image: Image.Image
    original_size: Tuple[int, int]
    target_size: Tuple[int, int]
    scale_factor: float
    method_used: str
    dpi: int
    details: Dict[str, Any] = field(default_factory=dict)


class GeminiUpscalerEngine:
    """Motor de super-resolução via Gemini API com fallback offline Lanczos."""

    DEFAULT_MODEL: str = "gemini-2.5-flash"
    GEMINI_ENDPOINT: str = (
        "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: int = 30,
        force_offline: bool = False,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)
        self.timeout_seconds = timeout_seconds
        self.force_offline = force_offline

    def _upscale_offline_lanczos(
        self,
        image: Image.Image,
        target_size: Tuple[int, int],
        apply_unsharp_mask: bool = True,
    ) -> Image.Image:
        """Upscaling determinístico offline de alta qualidade usando Pillow Lanczos."""
        upscaled = image.resize(target_size, Image.Resampling.LANCZOS)
        if apply_unsharp_mask:
            # Máscara sutil para manter nitidez em tipografia sem criar halos artificiais
            upscaled = upscaled.filter(
                ImageFilter.UnsharpMask(radius=1.5, percent=115, threshold=3)
            )
        return upscaled

    def _call_gemini_api(
        self,
        image: Image.Image,
        target_size: Tuple[int, int],
    ) -> Image.Image:
        """Executa a requisição REST para a API do Google Gemini."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY não configurada no ambiente.")

        # Converte a imagem de entrada para JPEG/PNG em base64
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        prompt_text = (
            f"Super-resolution request: Upscale this graphic asset to {target_size[0]}x{target_size[1]} pixels. "
            f"Strict requirements: Maintain absolute fidelity to original typography, text, lines, faces, "
            f"and colors. Do NOT hallucinate new features, do NOT alter existing text or symbols."
        )

        url = self.GEMINI_ENDPOINT.format(model=self.model)
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_text},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": image_b64,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,  # Temperatura mínima para zero alucinação
            },
        }

        response = requests.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)
        response.raise_for_status()
        data = response.json()

        # Extrai bytes gerados ou imagem se retornado pelo modelo multimodal
        # Em APIs de geração multimodal que retornam texto base64 da imagem
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Nenhum candidato retornado pela API Gemini.")

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "inline_data" in part:
                img_data = base64.b64decode(part["inline_data"]["data"])
                ret_img = Image.open(io.BytesIO(img_data)).convert("RGB")
                return ret_img.resize(target_size, Image.Resampling.LANCZOS)

        # Se o modelo retornou resposta textual com dados, ou mock respondeu
        raise RuntimeError("A resposta do modelo não contém dados de imagem decodificáveis.")

    def upscale(
        self,
        image: Union[Image.Image, Path, str],
        target_size: Optional[Tuple[int, int]] = None,
        scale_factor: Optional[float] = None,
        target_preset: Optional[ProductPreset] = None,
        dpi: int = DEFAULT_DPI,
        force_offline: bool = False,
    ) -> UpscaleResult:
        """Executa o pipeline de upscaling para a dimensão solicitada.

        Args:
            image: Imagem de entrada.
            target_size: (largura_px, altura_px) desejado.
            scale_factor: Fator multiplicador (ex: 2.0x, 4.0x).
            target_preset: Preset de produto da Studio Kustom (obtém tamanho a 300 DPI).
            dpi: Resolução alvo.
            force_offline: Se True, não tenta conectar à API e usa Lanczos imediatamente.
        """
        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {path}")
            img = Image.open(path).convert("RGB")
        elif isinstance(image, Image.Image):
            img = image.convert("RGB")
        else:
            raise TypeError(f"Tipo de imagem inválido: {type(image)}")

        orig_w, orig_h = img.size

        # Determinação do tamanho final
        if target_size is not None:
            final_w, final_h = target_size
        elif target_preset is not None:
            final_w, final_h = target_preset.trim_size_px(dpi)
        elif scale_factor is not None:
            if scale_factor <= 0:
                raise ValueError(f"Fator de escala inválido: {scale_factor}")
            final_w = round(orig_w * scale_factor)
            final_h = round(orig_h * scale_factor)
        else:
            # Default: 2x upscale
            final_w = orig_w * 2
            final_h = orig_h * 2

        computed_scale = max(final_w / orig_w, final_h / orig_h)
        target_dimensions = (final_w, final_h)

        # Se a imagem já estiver no tamanho exato ou for maior, usa Lanczos diretamente
        if target_dimensions == (orig_w, orig_h):
            return UpscaleResult(
                image=img,
                original_size=(orig_w, orig_h),
                target_size=target_dimensions,
                scale_factor=1.0,
                method_used="none (already_at_target)",
                dpi=dpi,
            )

        method_used = "pillow_lanczos"
        details: Dict[str, Any] = {}

        if not force_offline and not self.force_offline and self.api_key:
            try:
                upscaled_img = self._call_gemini_api(img, target_dimensions)
                method_used = "gemini_api"
                details["model"] = self.model
            except Exception as exc:
                # Fallback transparente para offline
                upscaled_img = self._upscale_offline_lanczos(img, target_dimensions)
                method_used = "pillow_lanczos (fallback)"
                details["fallback_reason"] = str(exc)
        else:
            upscaled_img = self._upscale_offline_lanczos(img, target_dimensions)
            method_used = "pillow_lanczos"

        return UpscaleResult(
            image=upscaled_img,
            original_size=(orig_w, orig_h),
            target_size=target_dimensions,
            scale_factor=computed_scale,
            method_used=method_used,
            dpi=dpi,
            details=details,
        )
