"""Testes unitários rigorosos para o Motor 2: Pipeline de Upscaling Universal."""

import base64
import io
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

from src.core.presets import get_product_preset
from src.core.ssim_validator import SSIMValidator
from src.engines.motor2_upscaler_gemini import GeminiUpscalerEngine, UpscaleResult


class TestOfflineLanczosUpscaling:
    """Valida o motor determinístico offline de super-resolução com Lanczos."""

    def test_default_2x_upscale(self):
        engine = GeminiUpscalerEngine(force_offline=True)
        img = Image.new("RGB", (100, 150), (40, 80, 120))

        result = engine.upscale(img, force_offline=True)

        assert result.original_size == (100, 150)
        assert result.target_size == (200, 300)
        assert result.scale_factor == 2.0
        assert result.method_used == "pillow_lanczos"
        assert result.image.size == (200, 300)

    def test_scale_factor_custom(self):
        engine = GeminiUpscalerEngine(force_offline=True)
        img = Image.new("RGB", (50, 50), (10, 20, 30))

        result = engine.upscale(img, scale_factor=3.0, force_offline=True)
        assert result.target_size == (150, 150)
        assert result.scale_factor == 3.0

    def test_target_preset_tcg_standard(self):
        """Valida upscaling direcionado à dimensão nominal 300 DPI de um preset."""
        engine = GeminiUpscalerEngine(force_offline=True)
        tcg = get_product_preset("TCG_STANDARD")

        # Imagem em baixa resolução (375x525 = metade do tamanho 300 DPI 750x1050)
        low_res = Image.new("RGB", (375, 525), (100, 150, 200))
        result = engine.upscale(low_res, target_preset=tcg, dpi=300, force_offline=True)

        assert result.target_size == (750, 1050)
        assert result.image.size == (750, 1050)
        assert result.scale_factor == 2.0

    def test_already_at_target_dimensions(self):
        engine = GeminiUpscalerEngine(force_offline=True)
        img = Image.new("RGB", (400, 400), (50, 50, 50))

        result = engine.upscale(img, target_size=(400, 400), force_offline=True)
        assert result.scale_factor == 1.0
        assert "already_at_target" in result.method_used

    def test_upscale_fidelity_with_ssim_validator(self):
        """Valida que o upscaler offline preserva fidelidade estrutural (SSIM >= 0.88)."""
        engine = GeminiUpscalerEngine(force_offline=True)
        validator = SSIMValidator(min_ssim=0.88)

        # Imagem original com formas
        img = Image.new("RGB", (100, 100), (200, 100, 50))
        result = engine.upscale(img, scale_factor=2.0, force_offline=True)

        validation = validator.validate(reference_image=img, processed_image=result.image)
        assert validation.approved is True
        assert validation.ssim_score >= 0.95

    def test_file_inputs_and_exceptions(self, tmp_path):
        engine = GeminiUpscalerEngine(force_offline=True)
        file_path = tmp_path / "low_res.png"
        img = Image.new("RGB", (50, 50), (255, 0, 0))
        img.save(file_path)

        res = engine.upscale(file_path, scale_factor=2.0, force_offline=True)
        assert res.image.size == (100, 100)

        with pytest.raises(FileNotFoundError):
            engine.upscale("arquivo_inexistente.png", force_offline=True)

        with pytest.raises(TypeError):
            engine.upscale(999, force_offline=True)

        with pytest.raises(ValueError, match="Fator de escala inválido"):
            engine.upscale(img, scale_factor=-1.0, force_offline=True)


class TestGeminiApiIntegrationAndMocks:
    """Valida a integração com a API Gemini usando mocks offline determinísticos."""

    def test_gemini_api_success_mock(self):
        """Simula resposta positiva da API Gemini com dados de imagem base64."""
        engine = GeminiUpscalerEngine(api_key="mock_valid_key", model="gemini-2.5-flash")
        img = Image.new("RGB", (50, 50), (0, 120, 240))

        # Cria imagem mockada de retorno (100x100)
        mock_ret_img = Image.new("RGB", (100, 100), (0, 120, 240))
        buf = io.BytesIO()
        mock_ret_img.save(buf, format="PNG")
        mock_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": mock_b64,
                                }
                            }
                        ]
                    }
                }
            ]
        }

        with patch("requests.post", return_value=mock_response):
            result = engine.upscale(img, target_size=(100, 100), force_offline=False)

        assert result.method_used == "gemini_api"
        assert result.image.size == (100, 100)
        assert result.details.get("model") == "gemini-2.5-flash"

    def test_gemini_api_fallback_on_error(self):
        """Simula falha de conexão (HTTP 500) e valida fallback para Lanczos."""
        engine = GeminiUpscalerEngine(api_key="mock_valid_key")
        img = Image.new("RGB", (50, 50), (0, 120, 240))

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("HTTP 500 Internal Error")

        with patch("requests.post", return_value=mock_response):
            result = engine.upscale(img, target_size=(100, 100), force_offline=False)

        assert "pillow_lanczos (fallback)" in result.method_used
        assert result.image.size == (100, 100)
        assert "fallback_reason" in result.details
