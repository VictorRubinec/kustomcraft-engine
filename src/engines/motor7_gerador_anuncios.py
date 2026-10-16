"""Motor 7: Gerador de Anúncios e Carrosséis (Shopee e Instagram) da Studio Kustom Engine.

Implementa o Sistema de Cores Oficiais da Studio Kustom baseado em fundos 100% sólidos:
- PERSONALIZADO: Fundo Amarelo Solar (#FFD500), Destaques Roxo Elétrico (#560BAD / #7209B7),
  canto inferior direito com triângulo em #7209B7 e lâmpada mágica em #FFD500.
- ARTE_PRONTA: Fundo Azul Cobalto (#3B59EC), Destaques Amarelo Solar (#FFD500),
  canto inferior direito com triângulo em #FFD500 e lâmpada mágica em #3B59EC.
- INFORMATIVO: Fundo Roxo Místico (#560BAD), Destaques Amarelo Solar (#FFD500),
  canto inferior direito com triângulo em #FFD500 e lâmpada mágica em #560BAD.

Composição com mockups 3D do Motor 6 com sombra de contato suave (drop shadow preta com blur e 25% de opacidade).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from src.engines.motor4_fabrica_tcg import FontManager

ImageInput = Union[Image.Image, Path, str]


class ThemeMode(str, enum.Enum):
    """Modos de tema oficiais da Studio Kustom."""

    PERSONALIZADO = "personalizado"  # Encomendas / artes enviadas pelo cliente
    ARTE_PRONTA = "arte_pronta"      # Catálogo oficial / coleções prontas
    INFORMATIVO = "informativo"      # Comunicados / institucional / fichas técnicas


class BadgeStyle(str, enum.Enum):
    """Estilo dos selos/pílulas de acabamento."""

    SOLID = "solid"
    OUTLINE = "outline"
    GOLD_METALLIC = "gold_metallic"


@dataclass
class ThemeColors:
    """Conjunto de cores correspondente a um ThemeMode."""

    bg_color: tuple[int, int, int]
    title_color: tuple[int, int, int]
    subtitle_color: tuple[int, int, int]
    accent_color: tuple[int, int, int]
    triangle_color: tuple[int, int, int]
    lamp_color: tuple[int, int, int]
    badge_bg: tuple[int, int, int]
    badge_text: tuple[int, int, int]
    badge_border: tuple[int, int, int]
    banner_bg: tuple[int, int, int]
    banner_text: tuple[int, int, int]
    price_tag_bg: tuple[int, int, int]
    price_tag_text: tuple[int, int, int]


def get_theme_colors(theme: ThemeMode) -> ThemeColors:
    """Retorna as cores exatas do manual de identidade da Studio Kustom."""
    if theme == ThemeMode.PERSONALIZADO:
        # Fundo Amarelo Solar, Destaques Roxo Elétrico
        return ThemeColors(
            bg_color=(255, 213, 0),         # #FFD500
            title_color=(86, 11, 173),      # #560BAD
            subtitle_color=(114, 9, 183),   # #7209B7
            accent_color=(114, 9, 183),     # #7209B7
            triangle_color=(114, 9, 183),   # #7209B7
            lamp_color=(255, 213, 0),       # #FFD500
            badge_bg=(114, 9, 183),         # #7209B7
            badge_text=(255, 213, 0),       # #FFD500
            badge_border=(86, 11, 173),     # #560BAD
            banner_bg=(86, 11, 173),        # #560BAD
            banner_text=(255, 255, 255),
            price_tag_bg=(114, 9, 183),     # #7209B7
            price_tag_text=(255, 213, 0),   # #FFD500
        )
    elif theme == ThemeMode.ARTE_PRONTA:
        # Fundo Azul Cobalto, Destaques Amarelo Solar
        return ThemeColors(
            bg_color=(59, 89, 236),         # #3B59EC
            title_color=(255, 213, 0),      # #FFD500
            subtitle_color=(255, 255, 255),
            accent_color=(255, 213, 0),     # #FFD500
            triangle_color=(255, 213, 0),   # #FFD500
            lamp_color=(59, 89, 236),       # #3B59EC
            badge_bg=(255, 213, 0),         # #FFD500
            badge_text=(25, 40, 110),
            badge_border=(255, 255, 255),
            banner_bg=(25, 40, 110),
            banner_text=(255, 255, 255),
            price_tag_bg=(255, 213, 0),     # #FFD500
            price_tag_text=(25, 40, 110),
        )
    else:  # INFORMATIVO
        # Fundo Roxo Místico, Destaques Amarelo Solar
        return ThemeColors(
            bg_color=(86, 11, 173),         # #560BAD
            title_color=(255, 213, 0),      # #FFD500
            subtitle_color=(255, 255, 255),
            accent_color=(255, 213, 0),     # #FFD500
            triangle_color=(255, 213, 0),   # #FFD500
            lamp_color=(86, 11, 173),       # #560BAD
            badge_bg=(255, 213, 0),         # #FFD500
            badge_text=(86, 11, 173),       # #560BAD
            badge_border=(255, 213, 0),
            banner_bg=(50, 6, 105),
            banner_text=(255, 255, 255),
            price_tag_bg=(255, 213, 0),     # #FFD500
            price_tag_text=(86, 11, 173),
        )


@dataclass
class AdTemplateConfig:
    """Configuração personalizada ou padrão para o gerador de anúncios."""

    theme_mode: ThemeMode = ThemeMode.PERSONALIZADO
    badge_style: BadgeStyle = BadgeStyle.SOLID
    # Cores opcionais de sobreposição direta se fornecidas
    primary_color: tuple[int, int, int] | None = None
    accent_color: tuple[int, int, int] | None = None
    highlight_color: tuple[int, int, int] | None = None


class BaseAdGenerator:
    """Classe base compartilhada com utilitários gráficos de chão de fábrica."""

    def __init__(self, config: AdTemplateConfig | None = None) -> None:
        self.config = config or AdTemplateConfig()
        self.font_mgr = FontManager()
        self._logo_image = self._find_logo_image()
        self._lamp_silhouette = self._find_lamp_silhouette()

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """Carrega fonte Montserrat com fallback gracioso para padrão Pillow."""
        font_name = "Montserrat-Bold.ttf" if bold else "Montserrat-Regular.ttf"
        return self.font_mgr.load_font(font_name, size)

    def _find_logo_image(self) -> Image.Image | None:
        """Localiza a logo oficial nos diretórios da Studio Kustom se disponível."""
        candidates = [
            Path(r"D:\Desktop\Studio Kustom\02 - Design e Marca\Logos e Identidade\Logo olho branco.png"),
            Path(r"D:\Desktop\Studio Kustom\02 - Design e Marca\Logos e Identidade\Studio_Kustom_-_Insta-1024.png"),
            Path("assets/logos/logo_olho_branco.png"),
        ]
        for p in candidates:
            if p.exists():
                try:
                    return Image.open(p).convert("RGBA")
                except Exception:
                    continue
        return None

    def _find_lamp_silhouette(self) -> Image.Image | None:
        """Localiza a silhueta da lâmpada mágica da identidade visual."""
        candidates = [
            Path(r"D:\Desktop\Studio Kustom\02 - Design e Marca\Design de Marca\identidade visual\PNG\icon\icon branco.png"),
            Path(r"D:\Desktop\Studio Kustom\02 - Design e Marca\Logos e Identidade\Logo olho branco.png"),
            Path("assets/icons/icon_branco.png"),
        ]
        for p in candidates:
            if p.exists():
                try:
                    return Image.open(p).convert("RGBA")
                except Exception:
                    continue
        return None

    def _load_image(self, img_input: ImageInput) -> Image.Image:
        """Normaliza ImageInput para PIL Image RGBA."""
        if isinstance(img_input, (str, Path)):
            p = Path(img_input)
            if not p.exists():
                raise FileNotFoundError(f"Arquivo de imagem não encontrado: {p}")
            return Image.open(p).convert("RGBA")
        elif isinstance(img_input, Image.Image):
            return img_input.convert("RGBA")
        else:
            raise TypeError(f"Tipo não suportado para imagem: {type(img_input)}")

    def _create_solid_background(self, width: int, height: int, colors: ThemeColors) -> Image.Image:
        """Cria fundo 100% SÓLIDO e UNIFORME via draw.rectangle, sem degradês escuros."""
        bg = Image.new("RGBA", (width, height), (*colors.bg_color, 255))
        draw = ImageDraw.Draw(bg)
        draw.rectangle([(0, 0), (width, height)], fill=(*colors.bg_color, 255))
        return bg

    def _draw_corner_triangle_with_lamp(
        self,
        canvas: Image.Image,
        colors: ThemeColors,
        size: int = 240,
    ) -> None:
        """Desenha o triângulo geométrico no canto inferior direito com a lâmpada mágica."""
        w, h = canvas.size
        draw = ImageDraw.Draw(canvas)

        # 1. Triângulo no canto inferior direito
        tri_pts = [(w - size, h), (w, h - size), (w, h)]
        draw.polygon(tri_pts, fill=(*colors.triangle_color, 255))

        # 2. Inserção da Lâmpada Mágica dentro do triângulo
        lamp_w, lamp_h = int(size * 0.40), int(size * 0.40)
        lamp_x = w - int(size * 0.46)
        lamp_y = h - int(size * 0.46)

        if self._lamp_silhouette:
            lamp_copy = self._lamp_silhouette.copy()
            lamp_copy.thumbnail((lamp_w, lamp_h), Image.Resampling.LANCZOS)
            r, g, b, a = lamp_copy.split()
            tinted = Image.new("RGBA", lamp_copy.size, (*colors.lamp_color, 255))
            tinted.putalpha(a)
            canvas.alpha_composite(tinted, (lamp_x, lamp_y))
        else:
            # Fallback vetorial da lâmpada mágica com lâmpada e nuvem
            lw, lh = lamp_w, lamp_h
            lx, ly = lamp_x, lamp_y
            # Base da lâmpada
            draw.ellipse([lx + 10, ly + lh - 18, lx + lw - 20, ly + lh - 4], fill=colors.lamp_color)
            # Corpo bojudo
            draw.ellipse([lx + 16, ly + lh // 2, lx + lw - 24, ly + lh - 12], fill=colors.lamp_color)
            # Bico
            draw.polygon([(lx + 6, ly + lh // 2 + 4), (lx + 20, ly + lh // 2 + 10), (lx + 20, ly + lh // 2 - 2)], fill=colors.lamp_color)
            # Alça
            draw.arc([lx + lw - 32, ly + lh // 2 - 4, lx + lw - 8, ly + lh - 10], start=-90, end=90, fill=colors.lamp_color, width=4)
            # Fumaça mágica superior
            draw.ellipse([lx + 12, ly + 8, lx + 28, ly + 24], fill=colors.lamp_color)
            draw.ellipse([lx + 22, ly + 2, lx + 42, ly + 18], fill=colors.lamp_color)

    def _apply_mockup_with_shadow(
        self,
        canvas: Image.Image,
        mockup: Image.Image,
        pos: tuple[int, int],
        offset: tuple[int, int] = (0, 18),
        blur_radius: float = 24.0,
        opacity: float = 0.25,
    ) -> None:
        """Insere o mockup 3D com fundo transparente sobre o canvas aplicando sombra suave (25% opacidade)."""
        alpha = mockup.getchannel("A")
        # Máscara correspondente a 25% de opacidade
        shadow_mask = alpha.point(lambda p: int(p * opacity))

        pad = int(blur_radius * 2)
        expanded = Image.new("RGBA", (mockup.width + pad * 2, mockup.height + pad * 2), (0, 0, 0, 0))

        black_shape = Image.new("RGBA", mockup.size, (0, 0, 0, 0))
        black_fill = Image.new("RGBA", mockup.size, (0, 0, 0, 255))
        black_shape.paste(black_fill, mask=shadow_mask)

        expanded.paste(black_shape, (pad, pad))
        blurred_shadow = expanded.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        sx = pos[0] + offset[0] - pad
        sy = pos[1] + offset[1] - pad

        canvas.alpha_composite(blurred_shadow, (sx, sy))
        canvas.alpha_composite(mockup, pos)

    def _draw_brand_header(
        self,
        canvas: Image.Image,
        colors: ThemeColors,
        x: int,
        y: int,
        size: int = 56,
    ) -> None:
        """Desenha a marca Studio Kustom no topo do anúncio em harmonia com o tema."""
        draw = ImageDraw.Draw(canvas)
        if self._logo_image:
            logo = self._logo_image.copy()
            aspect = logo.width / logo.height
            new_w = int(size * aspect)
            logo = logo.resize((new_w, size), Image.Resampling.LANCZOS)
            canvas.alpha_composite(logo, (x, y))
            text_x = x + new_w + 16
        else:
            # Fallback vetorial geométrico elegante
            draw.ellipse([x, y + 4, x + size - 8, y + size - 4], outline=colors.title_color, width=3)
            draw.ellipse([x + 14, y + 18, x + size - 22, y + size - 18], fill=colors.title_color)
            text_x = x + size + 16

        font_brand = self._get_font(28, bold=True)
        font_sub = self._get_font(16, bold=True)
        draw.text((text_x, y + 2), "STUDIO KUSTOM", fill=colors.title_color, font=font_brand)
        draw.text((text_x, y + 32), "CHÃO DE FÁBRICA • PREMIUM PRINT", fill=colors.subtitle_color, font=font_sub)

    def _draw_badge(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        colors: ThemeColors,
        style: BadgeStyle | None = None,
    ) -> int:
        """Desenha um selo/pílula de qualidade com ícone de diamante vetorial e retorna a largura ocupada."""
        badge_style = style or self.config.badge_style
        font = self._get_font(24, bold=True)
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        pad_x = 24
        icon_space = 24
        bh = 48
        bw = tw + pad_x * 2 + icon_space
        radius = 24

        if badge_style == BadgeStyle.SOLID:
            fill_color = (*colors.badge_bg, 255)
            outline_color = (*colors.badge_border, 255)
            text_color = colors.badge_text
            diamond_color = colors.badge_text
        elif badge_style == BadgeStyle.OUTLINE:
            fill_color = (*colors.bg_color, 255)
            outline_color = (*colors.title_color, 255)
            text_color = colors.title_color
            diamond_color = colors.title_color
        else:  # GOLD_METALLIC
            fill_color = (255, 213, 0, 255)
            outline_color = (86, 11, 173, 255)
            text_color = (86, 11, 173)
            diamond_color = (86, 11, 173)

        draw.rounded_rectangle(
            [x, y, x + bw, y + bh],
            radius=radius,
            fill=fill_color,
            outline=outline_color,
            width=2,
        )

        # Diamante vetorial nítido
        d_cx = x + pad_x + 6
        d_cy = y + bh // 2
        draw.polygon(
            [(d_cx, d_cy - 7), (d_cx + 6, d_cy), (d_cx, d_cy + 7), (d_cx - 6, d_cy)],
            fill=diamond_color,
        )

        draw.text((x + pad_x + icon_space, y + (bh - th) // 2 - 2), text, fill=text_color, font=font)
        return bw


class ShopeeAdGenerator(BaseAdGenerator):
    """Gerador de capas e lâminas de alta conversão para Shopee Feed (1200x1200px)."""

    CANVAS_SIZE = (1200, 1200)

    def gerar_capa_shopee(
        self,
        mockup_image: ImageInput,
        title: str,
        subtitle: str,
        badges: list[str],
        price_tag: str | None = None,
        theme_mode: ThemeMode | None = None,
        output_path: Path | str | None = None,
        apply_pillow_shadow: bool = False,
    ) -> Image.Image:
        """Gera a imagem de capa principal 1:1 quadrada (1200x1200px) sob o sistema de cores sólidas."""
        theme = theme_mode or self.config.theme_mode
        colors = get_theme_colors(theme)

        # Sobrescrita pontual se configurada manualmente no AdTemplateConfig
        if self.config.primary_color:
            colors.title_color = self.config.primary_color
        if self.config.accent_color:
            colors.accent_color = self.config.accent_color

        w, h = self.CANVAS_SIZE
        # 1. Fundo 100% Sólido
        canvas = self._create_solid_background(w, h, colors)

        # 2. Cabeçalho com Logo
        self._draw_brand_header(canvas, colors, x=60, y=55, size=64)

        # 3. Badges no Topo com prevenção de colisão contra o preço (máx 2 por linha, máx 860px se houver preço)
        draw = ImageDraw.Draw(canvas)
        pt_box_w = 260
        max_line1_w = (w - pt_box_w - 80) if price_tag else (w - 120)

        badge_x = 60
        badge_y = 145
        count_in_row = 0
        badges_to_draw = badges[:2]
        has_wrapped_row = False

        for badge_text in badges_to_draw:
            badge_font = self._get_font(24, bold=True)
            bbox = badge_font.getbbox(badge_text)
            bw = (bbox[2] - bbox[0]) + 24 * 2 + 24

            if count_in_row >= 2 or (badge_x + bw > max_line1_w):
                badge_x = 60
                badge_y += 56
                count_in_row = 0
                has_wrapped_row = True

            self._draw_badge(draw, badge_text, badge_x, badge_y, colors)
            badge_x += bw + 16
            count_in_row += 1

        # 4. Preço / Tag Promocional no Canto Direito Superior se presente
        if price_tag:
            pt_font = self._get_font(28, bold=True)
            pt_sub = self._get_font(16, bold=True)
            pt_box_h = 90
            pt_x = w - pt_box_w - 60
            pt_y = 55
            draw.rounded_rectangle(
                [pt_x, pt_y, pt_x + pt_box_w, pt_y + pt_box_h],
                radius=18,
                fill=(*colors.price_tag_bg, 255),
                outline=(*colors.title_color, 255) if theme == ThemeMode.PERSONALIZADO else (255, 255, 255, 255),
                width=2,
            )
            draw.text((pt_x + 20, pt_y + 12), "A PARTIR DE", fill=colors.price_tag_text, font=pt_sub)
            draw.text((pt_x + 20, pt_y + 36), price_tag, fill=colors.price_tag_text, font=pt_font)

        # 5. Mockup 3D Centralizado com respiro >= 100px da barra inferior e sombra limpa
        banner_h = 210
        banner_y = h - banner_h

        mockup = self._load_image(mockup_image)
        target_size = 680
        mockup.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)

        usable_top = 255 if has_wrapped_row else 210
        usable_bottom = banner_y - 100  # Limite rígido: no mínimo 100px da barra inferior
        mx = (w - mockup.width) // 2
        my = usable_top + (usable_bottom - usable_top - mockup.height) // 2
        my = min(my, usable_bottom - mockup.height)

        if apply_pillow_shadow:
            self._apply_mockup_with_shadow(canvas, mockup, pos=(mx, my), offset=(0, 18), blur_radius=22.0, opacity=0.25)
        else:
            canvas.alpha_composite(mockup, (mx, my))

        # 6. Barra Inferior de Título e Benefício
        banner_overlay = Image.new("RGBA", (w, banner_h), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(banner_overlay)

        # Fundo do banner inferior com destaque temático
        b_draw.rectangle([0, 0, w, banner_h], fill=(*colors.banner_bg, 255))
        b_draw.line([(0, 0), (w, 0)], fill=(*colors.title_color, 255) if theme != ThemeMode.PERSONALIZADO else (*colors.bg_color, 255), width=4)
        canvas.alpha_composite(banner_overlay, (0, banner_y))

        draw = ImageDraw.Draw(canvas)
        title_font = self._get_font(54, bold=True)
        sub_font = self._get_font(28, bold=True)

        draw.text((60, banner_y + 36), title.upper(), fill=colors.banner_text, font=title_font)
        draw.text((60, banner_y + 115), subtitle, fill=(255, 213, 0) if theme == ThemeMode.PERSONALIZADO else colors.subtitle_color, font=sub_font)

        # 7. Triângulo no Canto Inferior Direito com a Lâmpada Mágica
        self._draw_corner_triangle_with_lamp(canvas, colors, size=220)

        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(out, format="PNG")

        return canvas

    def gerar_lamina_tecnica_shopee(
        self,
        product_type: str,
        title: str,
        specs_dict: dict[str, str],
        mockup_image: ImageInput | None = None,
        notice_text: str = "Personalizamos com sua arte em altíssima resolução!",
        theme_mode: ThemeMode | None = None,
        output_path: Path | str | None = None,
    ) -> Image.Image:
        """Gera lâmina informativa de especificações técnicas milimétricas para o anúncio."""
        theme = theme_mode or ThemeMode.INFORMATIVO
        colors = get_theme_colors(theme)

        w, h = self.CANVAS_SIZE
        # Fundo 100% Sólido
        canvas = self._create_solid_background(w, h, colors)

        # Cabeçalho
        self._draw_brand_header(canvas, colors, x=60, y=55, size=64)

        draw = ImageDraw.Draw(canvas)
        t_font = self._get_font(40, bold=True)
        pt_font = self._get_font(20, bold=True)

        draw.text((60, 140), product_type.upper(), fill=colors.title_color, font=pt_font)
        draw.text((60, 170), title.upper(), fill=colors.subtitle_color if theme != ThemeMode.PERSONALIZADO else colors.title_color, font=t_font)
        draw.line([(60, 230), (w - 60, 230)], fill=(*colors.title_color, 255), width=3)

        # Grid com as Especificações Técnicas (Lado Esquerdo)
        spec_x = 60
        spec_y = 260
        spec_w = 640 if mockup_image else w - 120
        row_h = 76

        for key, val in specs_dict.items():
            draw.rounded_rectangle(
                [spec_x, spec_y, spec_x + spec_w, spec_y + row_h - 10],
                radius=14,
                fill=(*colors.banner_bg, 255) if theme == ThemeMode.INFORMATIVO else (*colors.badge_bg, 255),
                outline=(*colors.title_color, 255),
                width=1,
            )
            key_font = self._get_font(20, bold=True)
            val_font = self._get_font(22)

            draw.text((spec_x + 24, spec_y + 12), key.upper(), fill=colors.title_color, font=key_font)
            draw.text((spec_x + 24, spec_y + 36), val, fill=(255, 255, 255), font=val_font)
            spec_y += row_h

        # Mockup 3D Lateral se fornecido (Lado Direito) com Sombra Suave
        if mockup_image:
            mockup = self._load_image(mockup_image)
            mockup.thumbnail((440, 520), Image.Resampling.LANCZOS)
            m_pos = (w - mockup.width - 60, 260)
            self._apply_mockup_with_shadow(canvas, mockup, pos=m_pos, offset=(0, 14), blur_radius=18.0, opacity=0.25)

        # Banner de Aviso / CTA no Rodapé
        notice_y = h - 170
        draw.rounded_rectangle(
            [60, notice_y, w - 240, notice_y + 110],
            radius=20,
            fill=(*colors.banner_bg, 255),
            outline=(*colors.title_color, 255),
            width=2,
        )
        n_font_title = self._get_font(24, bold=True)
        n_font_sub = self._get_font(20)

        draw.text((90, notice_y + 22), "• COMO ENVIAR SUA ARTE", fill=colors.title_color, font=n_font_title)
        draw.text((90, notice_y + 58), notice_text, fill=(255, 255, 255), font=n_font_sub)

        # Triângulo no Canto Inferior Direito com a Lâmpada Mágica
        self._draw_corner_triangle_with_lamp(canvas, colors, size=220)

        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(out, format="PNG")

        return canvas


class InstagramAdGenerator(BaseAdGenerator):
    """Gerador de carrosséis e posts para Instagram Feed (4:5 e 1:1) sob o sistema de cores sólidas."""

    def gerar_carrossel_instagram(
        self,
        mockup_images: list[ImageInput],
        title: str,
        benefits_list: list[str],
        cta_text: str = "Peça agora pelo link da bio • Enviamos para todo o Brasil",
        format_ratio: str = "4:5",
        theme_mode: ThemeMode | None = None,
        output_dir: Path | str | None = None,
    ) -> list[Image.Image]:
        """Gera carrossel de 3 lâminas com sequência de alta conversão: Gancho -> Detalhes -> CTA."""
        if format_ratio == "4:5":
            width, height = (1080, 1350)
        elif format_ratio == "1:1":
            width, height = (1080, 1080)
        else:
            raise ValueError(f"Formato inválido: '{format_ratio}'. Use '4:5' ou '1:1'.")

        theme = theme_mode or self.config.theme_mode
        colors = get_theme_colors(theme)
        slides: list[Image.Image] = []

        # ==================== LÂMINA 1: GANCHO & CAPA ====================
        slide1 = self._create_solid_background(width, height, colors)
        self._draw_brand_header(slide1, colors, x=50, y=50, size=56)

        draw1 = ImageDraw.Draw(slide1)
        font_hook_sub = self._get_font(20, bold=True)

        if len(title) > 30 and " EM " in title:
            title_lines = title.split(" EM ", 1)
            title_text = title_lines[0] + " EM\n" + title_lines[1]
            font_hook_title = self._get_font(32, bold=True)
        else:
            title_text = title
            font_hook_title = self._get_font(34, bold=True)

        draw1.text((50, 135), "NOVIDADE EXCLUSIVA", fill=colors.title_color, font=font_hook_sub)
        draw1.text((50, 165), title_text.upper(), fill=colors.subtitle_color if theme != ThemeMode.PERSONALIZADO else colors.title_color, font=font_hook_title)

        if mockup_images:
            m1 = self._load_image(mockup_images[0])
            m1_size = int(width * 0.78)
            m1.thumbnail((m1_size, m1_size), Image.Resampling.LANCZOS)
            m1_x = (width - m1.width) // 2
            m1_y = (height - m1.height) // 2 + 35
            self._apply_mockup_with_shadow(slide1, m1, pos=(m1_x, m1_y), offset=(0, 18), blur_radius=22.0, opacity=0.25)

        # Indicador de deslizar
        draw1 = ImageDraw.Draw(slide1)
        font_swipe = self._get_font(20, bold=True)
        draw1.text((width - 340, height - 70), "DESLIZE PARA VER MAIS >", fill=colors.title_color, font=font_swipe)

        # Canto inferior direito com triângulo e lâmpada
        self._draw_corner_triangle_with_lamp(slide1, colors, size=200)
        slides.append(slide1)

        # ==================== LÂMINA 2: DETALHES & BENEFÍCIOS ====================
        slide2 = self._create_solid_background(width, height, colors)
        self._draw_brand_header(slide2, colors, x=50, y=50, size=56)

        draw2 = ImageDraw.Draw(slide2)
        font_s2_title = self._get_font(34, bold=True)
        draw2.text((50, 140), "POR QUE ESCOLHER A STUDIO KUSTOM?", fill=colors.title_color, font=font_s2_title)
        draw2.line([(50, 195), (width - 50, 195)], fill=(*colors.title_color, 255), width=3)

        # Benefícios em Cards
        card_y = 220
        card_w = width - 100
        card_h = 88
        for i, benefit in enumerate(benefits_list[:4]):
            draw2.rounded_rectangle(
                [50, card_y, 50 + card_w, card_y + card_h],
                radius=16,
                fill=(*colors.banner_bg, 255),
                outline=(*colors.title_color, 255),
                width=1,
            )
            b_num_font = self._get_font(24, bold=True)
            b_text_font = self._get_font(22)

            draw2.ellipse([70, card_y + 24, 110, card_y + 64], fill=colors.title_color)
            draw2.text((82, card_y + 28), str(i + 1), fill=colors.bg_color, font=b_num_font)
            draw2.text((130, card_y + 28), benefit, fill=(255, 255, 255), font=b_text_font)
            card_y += card_h + 18

        # Mockup secundário na base da lâmina 2 se disponível
        if len(mockup_images) > 1:
            m2 = self._load_image(mockup_images[1])
            m2.thumbnail((width - 240, height - card_y - 120), Image.Resampling.LANCZOS)
            m2_x = (width - m2.width) // 2
            self._apply_mockup_with_shadow(slide2, m2, pos=(m2_x, card_y + 20), offset=(0, 16), blur_radius=20.0, opacity=0.25)

        # Indicador de página 02 / 03
        draw2 = ImageDraw.Draw(slide2)
        page_font = self._get_font(18, bold=True)
        draw2.text((width - 320, height - 70), "02 / 03 >", fill=colors.title_color, font=page_font)

        # Canto inferior direito
        self._draw_corner_triangle_with_lamp(slide2, colors, size=200)
        slides.append(slide2)

        # ==================== LÂMINA 3: CHAMADA PARA AÇÃO (CTA) ====================
        slide3 = self._create_solid_background(width, height, colors)
        self._draw_brand_header(slide3, colors, x=50, y=50, size=56)

        if len(mockup_images) > 2:
            m3 = self._load_image(mockup_images[2])
        elif mockup_images:
            m3 = self._load_image(mockup_images[0])
        else:
            m3 = None

        if m3:
            m3_sized = m3.copy()
            m3_sized.thumbnail((400, 400), Image.Resampling.LANCZOS)
            m3_x = (width - m3_sized.width) // 2
            self._apply_mockup_with_shadow(slide3, m3_sized, pos=(m3_x, 170), offset=(0, 14), blur_radius=18.0, opacity=0.25)

        draw3 = ImageDraw.Draw(slide3)
        cta_box_w = width - 120
        cta_box_h = 360
        cta_box_y = height - cta_box_h - 100
        cta_box_x = 60

        draw3.rounded_rectangle(
            [cta_box_x, cta_box_y, cta_box_x + cta_box_w, cta_box_y + cta_box_h],
            radius=24,
            fill=(*colors.banner_bg, 255),
            outline=(*colors.title_color, 255),
            width=3,
        )

        font_cta_head = self._get_font(30, bold=True)
        font_cta_body = self._get_font(22)
        font_cta_button = self._get_font(24, bold=True)

        draw3.text((cta_box_x + 40, cta_box_y + 40), "TRANSFORME SUA IDEIA EM REALIDADE", fill=colors.title_color, font=font_cta_head)
        draw3.text((cta_box_x + 40, cta_box_y + 90), cta_text, fill=(255, 255, 255), font=font_cta_body)

        # Botão Chamativo de Ação
        btn_y = cta_box_y + 190
        btn_w = cta_box_w - 80
        btn_h = 75
        draw3.rounded_rectangle(
            [cta_box_x + 40, btn_y, cta_box_x + 40 + btn_w, btn_y + btn_h],
            radius=18,
            fill=(*colors.title_color, 255) if theme == ThemeMode.PERSONALIZADO else (*colors.bg_color, 255),
        )
        draw3.text(
            (cta_box_x + 70, btn_y + 22),
            "SOLICITAR ORÇAMENTO NO CHAT / WHATSAPP >",
            fill=(255, 213, 0) if theme == ThemeMode.PERSONALIZADO else (255, 255, 255),
            font=font_cta_button,
        )

        # Selos de Rodapé
        font_footer = self._get_font(18)
        draw3.text((cta_box_x + 40, cta_box_y + 295), "• Embalagem com DTF Têxtil Exclusiva • Envio para todo o Brasil", fill=colors.title_color if theme == ThemeMode.PERSONALIZADO else (255, 213, 0), font=font_footer)

        draw3.text((width - 320, height - 70), "03 / 03 •", fill=colors.title_color, font=page_font)

        # Canto inferior direito
        self._draw_corner_triangle_with_lamp(slide3, colors, size=200)
        slides.append(slide3)

        # Salva em pasta se solicitado
        if output_dir:
            out_d = Path(output_dir)
            out_d.mkdir(parents=True, exist_ok=True)
            for idx, slide_img in enumerate(slides):
                slide_img.save(out_d / f"carrossel_lamina_{idx + 1}.png", format="PNG")

        return slides
