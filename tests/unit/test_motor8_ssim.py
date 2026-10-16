"""Testes unitários rigorosos para o Motor 8: Validador Perceptual Anti-Alucinação (SSIM / MSE)."""

import numpy as np
import pytest
from PIL import Image, ImageDraw

from src.core.ssim_validator import (
    SSIMValidator,
    ValidationResult,
    DEFAULT_SSIM_THRESHOLD,
    _compute_ssim_numpy,
    _compute_mse_numpy,
)


class TestSSIMValidationRules:
    """Valida as regras de negócio de aceitação e reprovação visual do chão de fábrica."""

    def test_identical_images_perfect_score(self):
        """Imagens idênticas devem obter SSIM = 1.0, MSE = 0.0 e aprovação plena."""
        validator = SSIMValidator(min_ssim=0.88)
        img = Image.new("RGB", (200, 200), color=(80, 140, 200))

        result = validator.validate(reference_image=img, processed_image=img)

        assert result.approved is True
        assert result.ssim_score == pytest.approx(1.0, abs=1e-5)
        assert result.mse_score == pytest.approx(0.0, abs=1e-5)
        assert result.psnr_score == 100.0
        assert "Aprovado" in result.reason

    def test_mild_noise_acceptable_approved(self):
        """Ruído suave aceitável (como compressão sutil) deve ser aprovado (SSIM >= 0.88)."""
        validator = SSIMValidator(min_ssim=0.88)

        # Imagem base com gradiente
        arr = np.linspace(0, 255, 200 * 200, dtype=np.uint8).reshape((200, 200))
        ref_img = Image.fromarray(arr).convert("RGB")

        # Adiciona ruído gaussiano muito sutil (+/- 3 níveis de cinza)
        np.random.seed(42)
        noise = np.random.normal(0, 2.0, (200, 200, 3))
        noisy_arr = np.clip(np.array(ref_img, dtype=np.float64) + noise, 0, 255).astype(np.uint8)
        proc_img = Image.fromarray(noisy_arr)

        result = validator.validate(ref_img, proc_img)

        assert result.ssim_score >= 0.88
        assert result.approved is True
        assert "Aprovado" in result.reason

    def test_hallucination_or_distortion_rejected(self):
        """Distorção severa, texto deformado ou alucinação deve ser REPROVADA (SSIM < 0.88)."""
        validator = SSIMValidator(min_ssim=0.88)

        # Imagem de referência com desenho
        ref_img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        draw_ref = ImageDraw.Draw(ref_img)
        draw_ref.rectangle([50, 50, 150, 150], fill=(0, 0, 0))

        # Imagem com alucinação (mancha preta aleatória e inversão de cores)
        proc_img = ref_img.copy()
        draw_proc = ImageDraw.Draw(proc_img)
        draw_proc.ellipse([20, 20, 180, 180], fill=(200, 50, 50))  # Destruição visual
        draw_proc.text((60, 60), "TEXTO DEFORMADO", fill=(255, 255, 0))

        result = validator.validate(ref_img, proc_img)

        assert result.approved is False
        assert result.ssim_score < 0.88
        assert "Reprovado no portão de fidelidade visual" in result.reason
        assert "Distorção estrutural detectada" in result.reason

    def test_resolution_difference_auto_downsample(self):
        """Valida que imagem upscalada para tamanho maior é comparada via downsample 1:1."""
        validator = SSIMValidator(min_ssim=0.88)

        ref_img = Image.new("RGB", (100, 100), (40, 80, 120))
        # Processada é 4x maior (400x400) mas com o mesmo conteúdo cromático
        proc_img = Image.new("RGB", (400, 400), (40, 80, 120))

        result = validator.validate(ref_img, proc_img, downsample_to_reference=True)

        assert result.approved is True
        assert result.ssim_score == pytest.approx(1.0, abs=1e-4)

    def test_resolution_mismatch_without_downsample_raises_error(self):
        validator = SSIMValidator()
        ref = Image.new("RGB", (100, 100))
        proc = Image.new("RGB", (200, 200))

        with pytest.raises(ValueError, match="Dimensões incompatíveis"):
            validator.validate(ref, proc, downsample_to_reference=False)

    def test_numpy_array_input_support(self):
        """Valida que entradas np.ndarray funcionam perfeitamente."""
        validator = SSIMValidator()
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        arr[:, :] = [100, 150, 200]

        result = validator.validate(arr, arr)
        assert result.approved is True
        assert result.ssim_score == 1.0

    def test_numpy_math_fallbacks_coverage(self):
        """Valida a precisão das funções analíticas _compute_ssim_numpy e _compute_mse_numpy."""
        arr1 = np.ones((50, 50), dtype=np.uint8) * 128
        arr2 = np.ones((50, 50), dtype=np.uint8) * 128
        assert _compute_ssim_numpy(arr1, arr2) == pytest.approx(1.0, abs=1e-4)
        assert _compute_mse_numpy(arr1, arr2) == 0.0

        arr3 = np.ones((50, 50), dtype=np.uint8) * 200
        assert _compute_mse_numpy(arr1, arr3) == (200 - 128) ** 2
