"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path
import pytest
from PIL import Image

# Garante que 'src' esteja no sys.path para importações limpas
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture
def sample_card_front_image():
    """Gera uma imagem de teste para a frente de uma carta (RGB 750x1050 px)."""
    img = Image.new("RGB", (750, 1050), color=(30, 80, 180))
    return img


@pytest.fixture
def sample_card_back_image():
    """Gera uma imagem de teste para o verso de uma carta (RGB 750x1050 px)."""
    img = Image.new("RGB", (750, 1050), color=(180, 40, 30))
    return img
