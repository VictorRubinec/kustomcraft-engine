"""Motor 8: Validador Perceptual Anti-Alucinação (SSIM / MSE).

Compara matematicamente a fidelidade estrutural entre a imagem original e
a imagem pós-processada (upscaling ou geração por IA) para blindar o chão
de fábrica contra artefatos grotescos, rostos deformados ou tipografia ilegível.

Regra de Negócio:
Se o índice SSIM < 0.88 ou a distorção MSE ultrapassar o limiar de tolerância,
o job gráfico é automaticamente vetado com relatório de causa-raiz.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
from PIL import Image

try:
    from skimage.metrics import structural_similarity as ssim_fn
    from skimage.metrics import mean_squared_error as mse_fn
    SKIMAGE_AVAILABLE = True
except ImportError:  # pragma: no cover
    SKIMAGE_AVAILABLE = False


DEFAULT_SSIM_THRESHOLD: float = 0.88
DEFAULT_MAX_MSE_THRESHOLD: float = 500.0  # Para escala 0-255


@dataclass(frozen=True)
class ValidationResult:
    """Resultado auditável da validação perceptual."""

    approved: bool
    ssim_score: float
    mse_score: float
    psnr_score: float
    threshold: float
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)


def _compute_ssim_numpy(img1: np.ndarray, img2: np.ndarray) -> float:
    """Cálculo analítico do SSIM (Wang et al., 2004) como fallback puro em NumPy."""
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    img1 = img1.astype(np.float64)
    img2 = img2.astype(np.float64)

    mu1 = np.mean(img1)
    mu2 = np.mean(img2)
    sigma1_sq = np.var(img1)
    sigma2_sq = np.var(img2)
    sigma12 = np.mean((img1 - mu1) * (img2 - mu2))

    numerator = (2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)
    denominator = (mu1 ** 2 + mu2 ** 2 + c1) * (sigma1_sq + sigma2_sq + c2)
    return float(numerator / denominator)


def _compute_mse_numpy(img1: np.ndarray, img2: np.ndarray) -> float:
    """Calcula o Erro Quadrático Médio (MSE) entre duas matrizes."""
    return float(np.mean((img1.astype(np.float64) - img2.astype(np.float64)) ** 2))


class SSIMValidator:
    """Validador de integridade perceptual e anti-alucinação."""

    def __init__(
        self,
        min_ssim: float = DEFAULT_SSIM_THRESHOLD,
        max_mse: float = DEFAULT_MAX_MSE_THRESHOLD,
    ):
        self.min_ssim = min_ssim
        self.max_mse = max_mse

    def validate(
        self,
        reference_image: Union[Image.Image, np.ndarray],
        processed_image: Union[Image.Image, np.ndarray],
        downsample_to_reference: bool = True,
    ) -> ValidationResult:
        """Compara a imagem processada com a de referência.

        Se as imagens possuírem resoluções diferentes, a imagem processada é
        redimensionada (downscale via Lanczos) para o tamanho exato da referência,
        permitindo comparação pixel a pixel da integridade estrutural.
        """
        # Converte para Pillow Image para normalização geométrica
        if isinstance(reference_image, np.ndarray):
            ref_pil = Image.fromarray(reference_image).convert("RGB")
        else:
            ref_pil = reference_image.convert("RGB")

        if isinstance(processed_image, np.ndarray):
            proc_pil = Image.fromarray(processed_image).convert("RGB")
        else:
            proc_pil = processed_image.convert("RGB")

        # Alinhamento dimensional
        if proc_pil.size != ref_pil.size and downsample_to_reference:
            proc_pil = proc_pil.resize(ref_pil.size, Image.Resampling.LANCZOS)
        elif proc_pil.size != ref_pil.size and not downsample_to_reference:
            raise ValueError(
                f"Dimensões incompatíveis para validação SSIM: "
                f"Referência {ref_pil.size} vs Processada {proc_pil.size} "
                f"(downsample_to_reference=False)"
            )

        # Converte para matrizes numpy em uint8
        ref_arr = np.array(ref_pil)
        proc_arr = np.array(proc_pil)

        # Cálculo de MSE
        if SKIMAGE_AVAILABLE:
            mse_val = float(mse_fn(ref_arr, proc_arr))
        else:  # pragma: no cover
            mse_val = _compute_mse_numpy(ref_arr, proc_arr)

        # Cálculo de PSNR (Peak Signal-to-Noise Ratio)
        if mse_val == 0.0:
            psnr_val = 100.0  # Perfeição absoluta
        else:
            psnr_val = float(20 * math.log10(255.0 / math.sqrt(mse_val)))

        # Cálculo de SSIM
        if SKIMAGE_AVAILABLE:
            # scikit-image suporta multichannel com channel_axis=2
            ssim_val = float(ssim_fn(ref_arr, proc_arr, channel_axis=2, data_range=255))
        else:  # pragma: no cover
            # Fallback converte para escala de cinza
            ref_gray = np.array(ref_pil.convert("L"))
            proc_gray = np.array(proc_pil.convert("L"))
            ssim_val = _compute_ssim_numpy(ref_gray, proc_gray)

        # Avaliação dos Portões de Qualidade
        approved = True
        reasons = []

        if ssim_val < self.min_ssim:
            approved = False
            reasons.append(
                f"SSIM ({ssim_val:.4f}) abaixo do limiar mínimo ({self.min_ssim:.2f}). "
                f"Distorção estrutural detectada."
            )

        if mse_val > self.max_mse:
            approved = False
            reasons.append(
                f"MSE ({mse_val:.2f}) acima da tolerância máxima ({self.max_mse:.2f})."
            )

        if approved:
            reason = (
                f"Aprovado: SSIM {ssim_val:.4f} >= {self.min_ssim:.2f} e "
                f"MSE {mse_val:.2f} <= {self.max_mse:.2f}. Integridade preservada."
            )
        else:
            reason = "Reprovado no portão de fidelidade visual: " + " | ".join(reasons)

        details = {
            "reference_size": ref_pil.size,
            "processed_size": proc_pil.size,
            "skimage_used": SKIMAGE_AVAILABLE,
        }

        return ValidationResult(
            approved=approved,
            ssim_score=ssim_val,
            mse_score=mse_val,
            psnr_score=psnr_val,
            threshold=self.min_ssim,
            reason=reason,
            details=details,
        )
