"""Script de geração de amostras visuais oficiais da Studio Kustom Engine.

Gera os seguintes entregáveis na pasta output/:
1. output/amostra_super_a4_9up_duplex.pdf
   - Grade 3x3 de 9 cartas Pokémon/TCG em folha Super A4 real (229.92 x 315.12 mm)
   - Versos calibrados a 68.0 x 93.0 mm com +2.25mm de sangria
   - Alvos circulares de registro a 5.73mm dos cantos da folha
   - Espelhamento duplex Konica Minolta C558
2. output/amostra_folha_canecas.pdf
   - Folha A4 Paisagem (297 x 210 mm) com EXATAMENTE 2 tiras de 220x95mm
   - Espelhadas horizontalmente para a prensa sublimática e a Epson EcoTank L110
   - Marcas de corte finas a 0.25pt
3. output/amostra_caneca_arte_plana.png
   - Arte panorâmica realista de caneca 325ml (220 x 95 mm / 2598 x 1122 px a 300 DPI)
   - Face Esquerda: Ilustração de Pokémon com moldura dourada
   - Centro: Padrão geométrico contínuo (oposto à alça)
   - Face Direita: Tipografia premium Studio Kustom Limited Edition
4. output/amostra_carta_pokemon.png
   - Carta Pokémon individual de alta resolução a 300 DPI
"""

from pathlib import Path
import sys
import numpy as np

# Garante importações a partir da raiz do repositório
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.engines.motor4_fabrica_tcg import (
    TCGFactoryEngine,
    PokemonCardSpec,
    AttackSpec,
    FontManager,
)
from src.engines.motor1_imposicao_duplex import ImpositionEngine
from src.engines.motor3_estudio_canecas import MugStudioEngine
from src.engines.motor6_mockup_threejs import (
    ThreeJSMockupEngine,
    render_mug_mockup,
    render_card_mockup,
)
from src.engines.motor7_gerador_anuncios import (
    ShopeeAdGenerator,
    InstagramAdGenerator,
    ThemeMode,
)
from PIL import Image, ImageDraw, ImageFilter, ImageOps



def build_realistic_mug_artwork() -> Image.Image:
    """Cria uma arte panorâmica de caneca fotorrealista com duas faces (2598 x 1122 px a 300 DPI)."""
    w, h = 2598, 1122
    # Fundo gradiente profundo de alta densidade (grafite/azul escuro cósmico)
    art = Image.new("RGB", (w, h), color=(15, 20, 32))
    draw = ImageDraw.Draw(art)

    # Criação de textura suave de fundo
    for y in range(0, h, 4):
        alpha = int(15 + 18 * (y / h))
        draw.line([(0, y), (w, y)], fill=(12 + alpha // 2, 18 + alpha, 30 + alpha))

    # Moldura externa geral de segurança (recuo de 5mm topo/base = 59px, 15mm alça = 177px)
    margin_top = 59
    margin_side = 177
    draw.rounded_rectangle(
        [margin_side, margin_top, w - margin_side, h - margin_top],
        radius=24,
        outline=(212, 175, 55),
        width=4,
    )
    draw.rounded_rectangle(
        [margin_side + 10, margin_top + 10, w - margin_side - 10, h - margin_top - 10],
        radius=18,
        outline=(60, 80, 110),
        width=2,
    )

    # =========================================================================
    # FACE ESQUERDA: TIPOGRAFIA DE LUXO STUDIO KUSTOM (Centro x ≈ 660)
    # =========================================================================
    left_cx, left_cy = 660, h // 2
    box_w, box_h = 700, 860
    lx1, ly1 = left_cx - box_w // 2, left_cy - box_h // 2
    lx2, ly2 = left_cx + box_w // 2, left_cy + box_h // 2

    draw.rounded_rectangle([lx1, ly1, lx2, ly2], radius=20, fill=(20, 28, 44), outline=(212, 175, 55), width=3)
    draw.rounded_rectangle([lx1 + 8, ly1 + 8, lx2 - 8, ly2 - 8], radius=14, outline=(50, 75, 110), width=2)

    font_brand = FontManager.load_font("RetroByte.ttf", 60)
    font_sub_title = FontManager.load_font("Montserrat-Bold.ttf", 24)
    font_emblem = FontManager.load_font("RetroByte.ttf", 68)
    font_edition = FontManager.load_font("Montserrat-Bold.ttf", 30)
    font_bottom = FontManager.load_font("Montserrat-Bold.ttf", 22)
    font_body_light = FontManager.load_font("Montserrat-Regular.ttf", 22)

    draw.text((left_cx, ly1 + 105), "STUDIO KUSTOM", fill=(212, 175, 55), font=font_brand, anchor="mm")
    draw.line([(lx1 + 70, ly1 + 155), (lx2 - 70, ly1 + 155)], fill=(212, 175, 55), width=2)
    draw.text((left_cx, ly1 + 195), "OFICINA DE ARTE & PERSONALIZADOS", fill=(180, 205, 240), font=font_sub_title, anchor="mm")

    crest_cy = left_cy + 30
    draw.ellipse([left_cx - 110, crest_cy - 110, left_cx + 110, crest_cy + 110], fill=(15, 22, 35), outline=(212, 175, 55), width=4)
    draw.ellipse([left_cx - 95, crest_cy - 95, left_cx + 95, crest_cy + 95], outline=(60, 90, 130), width=2)
    draw.text((left_cx, crest_cy), "SK", fill=(212, 175, 55), font=font_emblem, anchor="mm")

    draw.text((left_cx, ly2 - 115), "ARTE EXCLUSIVA", fill=(255, 255, 255), font=font_edition, anchor="mm")
    draw.text((left_cx, ly2 - 70), "COLECIONÁVEL • PREMIUM", fill=(212, 175, 55), font=font_bottom, anchor="mm")

    # =========================================================================
    # CENTRO ABSOLUTO: ILUSTRAÇÃO HERO DO CHARIZARD (Centro x = 1299, U = 0.5)
    # =========================================================================
    center_cx, center_cy = w // 2, h // 2
    cx1, cy1 = center_cx - box_w // 2, center_cy - box_h // 2
    cx2, cy2 = center_cx + box_w // 2, center_cy + box_h // 2

    # Fundo temático de fogo da face central
    draw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=20, fill=(38, 18, 18), outline=(212, 175, 55), width=4)
    draw.rounded_rectangle([cx1 + 8, cy1 + 8, cx2 - 8, cy2 - 8], radius=14, outline=(226, 66, 66), width=2)

    # Janela de arte interna
    art_inner = (cx1 + 25, cy1 + 70, cx2 - 25, cy2 - 120)
    draw.rounded_rectangle(art_inner, radius=12, fill=(52, 20, 20), outline=(212, 175, 55), width=2)

    # Brilho central solar
    ix_c = (art_inner[0] + art_inner[2]) // 2
    iy_c = (art_inner[1] + art_inner[3]) // 2
    for rad in range(30, 210, 25):
        draw.ellipse([ix_c - rad, iy_c - rad, ix_c + rad, iy_c + rad], outline=(226, 66, 66), width=2)

    font_pkmn_name = FontManager.load_font("Montserrat-Bold.ttf", 46)
    font_pkmn_sub = FontManager.load_font("Montserrat-Bold.ttf", 26)

    # Cabeçalho da face hero central
    draw.text((center_cx, cy1 + 40), "CHARIZARD  #006", fill=(255, 255, 255), font=font_pkmn_name, anchor="mm")
    draw.text((ix_c, iy_c - 20), "FIRE BREATH", fill=(255, 180, 50), font=font_pkmn_name, anchor="mm")
    draw.text((ix_c, iy_c + 30), "FLAME POKÉMON • 120 HP", fill=(255, 220, 150), font=font_pkmn_sub, anchor="mm")

    # Rodapé da face central
    draw.text((center_cx, cy2 - 60), "TYPE: FIRE / FLYING • WEAKNESS: WATER", fill=(240, 200, 200), font=font_pkmn_sub, anchor="mm")

    # =========================================================================
    # FACE DIREITA: ESPECIFICAÇÕES TÉCNICAS E SELO DE QUALIDADE (Centro x ≈ 1940)
    # =========================================================================
    right_cx, right_cy = 1940, h // 2
    rx1, ry1 = right_cx - box_w // 2, right_cy - box_h // 2
    rx2, ry2 = right_cx + box_w // 2, right_cy + box_h // 2

    draw.rounded_rectangle([rx1, ry1, rx2, ry2], radius=20, fill=(20, 28, 44), outline=(212, 175, 55), width=3)
    draw.rounded_rectangle([rx1 + 8, ry1 + 8, rx2 - 8, ry2 - 8], radius=14, outline=(50, 75, 110), width=2)

    draw.text((right_cx, ry1 + 95), "CANECO PREMIUM", fill=(212, 175, 55), font=font_brand, anchor="mm")
    draw.line([(rx1 + 70, ry1 + 145), (rx2 - 70, ry1 + 145)], fill=(212, 175, 55), width=2)
    draw.text((right_cx, ry1 + 185), "ESPECIFICAÇÕES & CUIDADOS", fill=(180, 205, 240), font=font_sub_title, anchor="mm")

    # Selos Técnicos em Grid
    spec_cy = right_cy + 30
    draw.ellipse([right_cx - 100, spec_cy - 100, right_cx + 100, spec_cy + 100], fill=(15, 22, 35), outline=(212, 175, 55), width=3)
    draw.ellipse([right_cx - 85, spec_cy - 85, right_cx + 85, spec_cy + 85], outline=(60, 90, 130), width=2)
    draw.text((right_cx, spec_cy - 15), "325 ML", fill=(255, 255, 255), font=font_edition, anchor="mm")
    draw.text((right_cx, spec_cy + 22), "PORCELANA AAA", fill=(212, 175, 55), font=font_bottom, anchor="mm")

    # Rodapé Técnico
    draw.text((right_cx, ry2 - 115), "MICRO-ONDAS & LAVA-LOUÇAS", fill=(255, 255, 255), font=font_sub_title, anchor="mm")
    draw.text((right_cx, ry2 - 70), "ALTA DURABILIDADE • RESINA DUPLA", fill=(212, 175, 55), font=font_bottom, anchor="mm")

    # =========================================================================
    # MARCADORES DE ALÇA E LINHAS GUIA
    # =========================================================================
    # Respiro das bordas externas (perto da alça)
    draw.text((margin_side // 2, h // 2), "ÁREA DE\nALÇA", fill=(80, 95, 120), font=font_body_light, anchor="mm", align="center")
    draw.text((w - margin_side // 2, h // 2), "ÁREA DE\nALÇA", fill=(80, 95, 120), font=font_body_light, anchor="mm", align="center")

    return art


def build_button_artwork() -> Image.Image:
    """Gera uma arte redonda vetorial de alta definição para bottons colecionáveis cobrindo 94%+ da área frontal."""
    size = 1200
    img = Image.new("RGBA", (size, size), (18, 24, 38, 255))
    draw = ImageDraw.Draw(img)

    # Anéis decorativos cobrindo 94%+ da área frontal visível
    draw.ellipse([20, 20, size - 20, size - 20], outline=(212, 175, 55), width=6)
    draw.ellipse([38, 38, size - 38, size - 38], outline=(59, 89, 236), width=3)

    # Círculo central com textura suave
    draw.ellipse([80, 80, size - 80, size - 80], fill=(12, 16, 26))

    # Tipografia e brasão central
    f_brand = FontManager.load_font("RetroByte.ttf", 74)
    f_sub = FontManager.load_font("Montserrat-Bold.ttf", 36)
    f_mini = FontManager.load_font("Montserrat-Bold.ttf", 24)

    draw.text((size // 2, 260), "STUDIO KUSTOM", fill=(212, 175, 55), font=f_brand, anchor="mm")
    draw.line([(size // 2 - 240, 315), (size // 2 + 240, 315)], fill=(212, 175, 55), width=3)

    # Monograma SK estilizado central ampliado
    crest_cy = size // 2 + 35
    draw.ellipse([size // 2 - 160, crest_cy - 160, size // 2 + 160, crest_cy + 160], fill=(22, 30, 48), outline=(212, 175, 55), width=5)
    draw.ellipse([size // 2 - 142, crest_cy - 142, size // 2 + 142, crest_cy + 142], outline=(59, 89, 236), width=2)
    f_logo = FontManager.load_font("RetroByte.ttf", 110)
    draw.text((size // 2, crest_cy), "SK", fill=(212, 175, 55), font=f_logo, anchor="mm")

    # Rodapé do botton com destaque
    draw.text((size // 2, size - 280), "COLLECTOR PIN", fill=(255, 255, 255), font=f_sub, anchor="mm")
    draw.text((size // 2, size - 225), "CHÃO DE FÁBRICA • 2026", fill=(180, 205, 240), font=f_mini, anchor="mm")

    return img


def build_poster_artwork() -> Image.Image:
    """Gera uma arte de pôster de alta resolução (proporção A4/A3) para demonstrar papel Couché 300g."""
    w, h = 1414, 2000
    img = Image.new("RGBA", (w, h), (18, 22, 34, 255))
    draw = ImageDraw.Draw(img)

    # Moldura gráfica impressa interna
    margin = 80
    draw.rectangle([margin, margin, w - margin, h - margin], outline=(212, 175, 55), width=6)
    draw.rectangle([margin + 20, margin + 20, w - margin - 20, h - margin - 20], outline=(60, 90, 140), width=2)

    # Topo
    f_title = FontManager.load_font("RetroByte.ttf", 84)
    f_sub = FontManager.load_font("Montserrat-Bold.ttf", 38)
    f_body = FontManager.load_font("Montserrat-Regular.ttf", 28)

    draw.text((w // 2, 280), "STUDIO KUSTOM", fill=(212, 175, 55), font=f_title, anchor="mm")
    draw.text((w // 2, 360), "FINE ART PRINT • COUCHÉ 300G", fill=(180, 205, 240), font=f_sub, anchor="mm")

    # Área central com ilustração de arte
    art_box = [200, 460, w - 200, h - 420]
    draw.rectangle(art_box, fill=(12, 16, 26), outline=(212, 175, 55), width=4)

    # Círculos concêntricos e arte central
    cx, cy = w // 2, 940
    for r in range(40, 360, 40):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(35, 50, 75), width=2)
    draw.ellipse([cx - 160, cy - 160, cx + 160, cy + 160], fill=(22, 30, 48), outline=(212, 175, 55), width=4)

    f_hero = FontManager.load_font("RetroByte.ttf", 110)
    draw.text((cx, cy), "SK", fill=(212, 175, 55), font=f_hero, anchor="mm")

    draw.text((w // 2, 1340), "EDIÇÃO COLECIONADOR LIMITADA", fill=(255, 255, 255), font=f_sub, anchor="mm")
    draw.text((w // 2, 1400), "IMPRESSÃO INDUSTRIAL 300 DPI COM ACABAMENTO SEMI-BRILHO", fill=(180, 190, 210), font=f_body, anchor="mm")

    # Rodapé
    draw.line([(200, h - 260), (w - 200, h - 260)], fill=(212, 175, 55), width=3)
    draw.text((w // 2, h - 200), "PRODUZIDO NO CHÃO DE FÁBRICA DA STUDIO KUSTOM", fill=(212, 175, 55), font=f_sub, anchor="mm")

    return img


def main():
    output_dir = ROOT_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] Diretório de saída: {output_dir}")

    tcg_factory = TCGFactoryEngine(dpi=300)
    imposition_engine = ImpositionEngine()
    mug_engine = MugStudioEngine(dpi=300)

    # =========================================================================
    # 1. GERAÇÃO DE 9 CARTAS POKÉMON PARA A GRADE 3x3
    # =========================================================================
    print("[1/3] Gerando baralho com 9 cartas Pokémon...")
    pokemon_roster = [
        ("Charizard", 120, "Fire", [AttackSpec(name="Fire Spin", cost="{R}{R}{R}{R}", damage="100", effect="Discarte 2 cartas de energia Fire.")]),
        ("Blastoise", 100, "Water", [AttackSpec(name="Hydro Pump", cost="{W}{W}{W}", damage="60+", effect="Causa +10 de dano para cada energia extra.")]),
        ("Venusaur", 100, "Grass", [AttackSpec(name="Solar Beam", cost="{G}{G}{G}{G}", damage="60", effect="Dispare um feixe de luz solar concentrado.")]),
        ("Pikachu", 60, "Lightning", [AttackSpec(name="Thunderbolt", cost="{L}{L}{C}", damage="80", effect="Discarte todas as energias ligadas a este Pokémon.")]),
        ("Gengar", 80, "Psychic", [AttackSpec(name="Shadow Ball", cost="{P}{P}", damage="50", effect="Pode causar confusão no alvo.")]),
        ("Mewtwo", 130, "Psychic", [AttackSpec(name="Psystrike", cost="{P}{P}{C}{C}", damage="110", effect="Ignora a fraqueza do oponente.")]),
        ("Lucario", 90, "Fighting", [AttackSpec(name="Aura Sphere", cost="{F}{F}", damage="70", effect="Este ataque nunca erra o alvo.")]),
        ("Rayquaza", 140, "Dragon", [AttackSpec(name="Dragon Ascent", cost="{G}{R}{C}", damage="130", effect="Reduz a defesa do atacante no próximo turno.")]),
        ("Eevee", 50, "Colorless", [AttackSpec(name="Quick Attack", cost="{C}", damage="20", effect="Jogue uma moeda para dano extra.")]),
    ]

    front_cards = []
    for name, hp, energy, attacks in pokemon_roster:
        spec = PokemonCardSpec(
            name=name,
            hp=hp,
            energy_type=energy,
            attacks=attacks,
            illustrator="Studio Kustom",
            collection_number=f"00{len(front_cards)+1}/009",
        )
        card_img = tcg_factory.build_pokemon_card(spec)
        front_cards.append(card_img)

    # Salva uma amostra individual de alta definição (300 DPI)
    pokemon_sample_path = output_dir / "amostra_carta_pokemon.png"
    front_cards[0].save(pokemon_sample_path, dpi=(300, 300))
    print(f"  -> Salvo: {pokemon_sample_path} ({front_cards[0].size[0]}x{front_cards[0].size[1]} px)")

    # Renderiza verso oficial dimensionado exatamente para o verso com sangria (68.0 x 93.0 mm -> 803 x 1098 px a 300 DPI)
    base_back = tcg_factory.render_official_card_back()
    back_bleed_img = base_back.resize((803, 1098), Image.Resampling.LANCZOS)

    # =========================================================================
    # 2. MONTAGEM DO PDF DUPLEX SUPER A4 (9-UP) CALIBRADO
    # =========================================================================
    print("[2/3] Montando imposição duplex Super A4 9-Up (229.92 x 315.12 mm)...")
    layout = imposition_engine.create_super_a4_9up_layout(
        front_preset_code="TCG_STANDARD_NO_BLEED",
        back_width_mm=68.0,
        back_height_mm=93.0,
        margin_left_mm=11.0,
        margin_top_mm=18.0,
        spacing_x_mm=8.5,
        spacing_y_mm=6.2,
    )

    for i in range(9):
        layout.slots[i].front_item = front_cards[i]
        layout.slots[i].back_item = back_bleed_img

    duplex_pdf_path = output_dir / "amostra_super_a4_9up_duplex.pdf"
    imposition_engine.render_pdf(
        layout=layout,
        output_path=duplex_pdf_path,
        draw_crop_marks=True,
        draw_registration_marks=False,
        corner_registration_marks=True,  # Alvos a 5.73mm dos cantos
    )
    print(f"  -> Salvo: {duplex_pdf_path}")

    # =========================================================================
    # 3. GERAÇÃO DE ARTE REALISTA DE CANECA E FOLHA A4 SUBLIMÁTICA (2 TIRAS)
    # =========================================================================
    print("[3/3] Gerando arte realista de caneca com 2 faces (2598 x 1122 px a 300 DPI)...")
    realistic_mug_art = build_realistic_mug_artwork()

    # Salva a arte plana em alta definição sem espelhamento para inspeção
    mug_art_path = output_dir / "amostra_caneca_arte_plana.png"
    realistic_mug_art.save(mug_art_path, dpi=(300, 300))
    print(f"  -> Salvo: {mug_art_path} ({realistic_mug_art.size[0]}x{realistic_mug_art.size[1]} px)")

    # Monta a folha A4 Paisagem (297 x 210 mm) com EXATAMENTE 2 tiras para a Epson L110
    print("  -> Montando folha A4 Paisagem (297 x 210 mm) com 2 tiras espelhadas...")
    mug_sheet_layout = mug_engine.calculate_sheet_layout(product_code="MUG_CERAMIC", sheet_code="A4", spacing_mm=4.0)
    print(f"  -> Tiras calculadas na folha A4: {mug_sheet_layout.strip_count} tiras.")

    mug_pdf_path = output_dir / "amostra_folha_canecas.pdf"
    mug_engine.render_sublimation_sheet_pdf(
        images=[realistic_mug_art, realistic_mug_art],
        output_path=mug_pdf_path,
        product_code="MUG_CERAMIC",
        sheet_code="A4",
        mirror_for_sublimation=True,
        apply_thermal_compensation=True,
    )
    print(f"  -> Salvo: {mug_pdf_path}")

    # =========================================================================
    # 4. GERAÇÃO DE MOCKUPS 3D FOTORREALISTAS (MOTOR 6 - THREE.JS)
    # =========================================================================
    print("\n[4/5] Renderizando mockups 3D headless com Three.js / Playwright...")
    mockup_engine = ThreeJSMockupEngine()

    # 4.1 Mockup 3D da Caneca de Cerâmica AAA (Individual)
    mockup_mug_path = output_dir / "mockup_3d_caneca.png"
    print("  -> Renderizando Mockup 3D da Caneca Individual (2048x2048 px, transparência RGBA)...")
    mockup_mug_img = mockup_engine.render_mug(
        art=realistic_mug_art,
        angle="front_left",
        resolution=(2048, 2048),
        transparent=True,
        output_path=mockup_mug_path,
    )
    print(f"  -> Salvo: {mockup_mug_path}")

    # 4.2 Mockup 3D Panorâmico de Trio de Canecas (Faces Esquerda, Central e Direita)
    mockup_mug_trio_path = output_dir / "mockup_3d_caneca_trio.png"
    print("  -> Renderizando Mockup 3D Panorâmico de Trio de Canecas (2048x2048 px)...")
    mockup_mug_trio_img = mockup_engine.render_mug_trio(
        art=realistic_mug_art,
        resolution=(2048, 2048),
        transparent=True,
        output_path=mockup_mug_trio_path,
    )
    print(f"  -> Salvo: {mockup_mug_trio_path}")

    # 4.3 Mockup 3D da Carta Pokémon com Foil Holográfico
    mockup_card_path = output_dir / "mockup_3d_carta_tcg.png"
    print("  -> Renderizando Mockup 3D de Carta TCG com Foil Holográfico (2048x2048 px)...")
    mockup_card_img = mockup_engine.render_card(
        front_art=front_cards[0],
        back_art=back_bleed_img,
        is_holographic=True,
        angle="stacked_pair",
        resolution=(2048, 2048),
        transparent=True,
        output_path=mockup_card_path,
    )
    print(f"  -> Salvo: {mockup_card_path}")

    # 4.4 Mockup 3D de Pôster Papel Puro Couché 300g Suspenso (sem moldura/vidro)
    poster_art = build_poster_artwork()
    mockup_poster_path = output_dir / "mockup_3d_poster_couche300g.png"
    print("  -> Renderizando Mockup 3D de Pôster Papel Puro Couché 300g Suspenso (2048x2048 px)...")
    mockup_poster_img = mockup_engine.render_poster(
        poster_art=poster_art,
        resolution=(2048, 2048),
        transparent=True,
        output_path=mockup_poster_path,
    )
    print(f"  -> Salvo: {mockup_poster_path}")

    # 4.5 Mockup 3D de Botton Americano Colecionável (Hero Individual 44mm)
    button_art = build_button_artwork()
    mockup_button_path = output_dir / "mockup_3d_botton_hero.png"
    print("  -> Renderizando Mockup 3D de Botton Colecionável Hero 44mm (2048x2048 px)...")
    mockup_button_img = mockup_engine.render_button(
        art=button_art,
        size_mm=44,
        mode="hero",
        resolution=(2048, 2048),
        transparent=True,
        output_path=mockup_button_path,
    )
    print(f"  -> Salvo: {mockup_button_path}")

    # 4.6 Mockup 3D de Kit com 6 Bottons Colecionáveis em Grade 2x3
    mockup_buttons_grid_path = output_dir / "mockup_3d_bottons_grid.png"
    print("  -> Renderizando Mockup 3D de Kit com 6 Bottons em Grade 2x3 (2048x2048 px)...")

    # Carrega kit com 6 artes reais de bottons (Gatos Bobos 44mm da Studio Kustom)
    cat_assets_dir = Path(r"D:/Desktop/Studio Kustom/03 - Produtos e Modelos/Produtos/Minhas Artes/Bottom/Gatos Bobos 44mm/gatos-bobos")
    kit_arts: list[Image.Image] = []
    if cat_assets_dir.exists():
        for fname in ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png"]:
            p = cat_assets_dir / fname
            if p.exists():
                try:
                    kit_arts.append(Image.open(p).convert("RGBA"))
                except Exception:
                    pass
    if len(kit_arts) < 6:
        kit_arts = [button_art] * 6

    mockup_buttons_grid_img = mockup_engine.render_buttons_grid(
        art=kit_arts,
        size_mm=44,
        resolution=(2048, 2048),
        transparent=True,
        output_path=mockup_buttons_grid_path,
    )
    print(f"  -> Salvo: {mockup_buttons_grid_path}")

    # =========================================================================
    # 5. GERAÇÃO DE ANÚNCIOS SHOPEE NOS 3 MODOS DE TEMA (MOTOR 7)
    # =========================================================================
    print("\n[5/5] Gerando criativos de marketing no Sistema Oficial de Cores Sólidas (Motor 7)...")
    shopee_gen = ShopeeAdGenerator()
    insta_gen = InstagramAdGenerator()

    # 5.1 Modo PERSONALIZADO (Fundo Amarelo Solar #FFD500, Triângulo Roxo #7209B7 com Lâmpada Amarela)
    capa_pers_path = output_dir / "capa_personalizado.png"
    shopee_gen.gerar_capa_shopee(
        mockup_image=mockup_card_img,
        title="CARTA POKÉMON CHARIZARD",
        subtitle="Edição Especial Colecionador • Foil Holográfico • Couché 300g",
        badges=["Papel Couché 300g", "Laminação Hi-Tac", "Foil Holográfico"],
        price_tag="R$ 29,90",
        theme_mode=ThemeMode.PERSONALIZADO,
        output_path=capa_pers_path,
    )
    print(f"  -> Salvo: {capa_pers_path} (Modo PERSONALIZADO - Amarelo Solar #FFD500)")

    # Mantém anuncio_shopee_capa.png sincronizado com o modo principal
    shopee_cover_path = output_dir / "anuncio_shopee_capa.png"
    import shutil
    shutil.copy2(capa_pers_path, shopee_cover_path)
    print(f"  -> Salvo: {shopee_cover_path}")

    # 5.2 Modo ARTE_PRONTA (Fundo Azul Cobalto #3B59EC, Triângulo Amarelo #FFD500 com Lâmpada Azul)
    capa_arte_path = output_dir / "capa_arte_pronta.png"
    shopee_gen.gerar_capa_shopee(
        mockup_image=mockup_mug_img,
        title="CANECA POKÉMON CHARIZARD",
        subtitle="Coleção Oficial Pronta Entrega • Cerâmica AAA 325ml",
        badges=["Sublimação HD", "Cerâmica AAA", "Pronta Entrega"],
        price_tag="R$ 39,90",
        theme_mode=ThemeMode.ARTE_PRONTA,
        output_path=capa_arte_path,
    )
    print(f"  -> Salvo: {capa_arte_path} (Modo ARTE_PRONTA - Azul Cobalto #3B59EC)")

    # 5.3 Modo INFORMATIVO (Fundo Roxo Místico #560BAD, Triângulo Amarelo #FFD500 com Lâmpada Roxa)
    capa_info_path = output_dir / "capa_informativo.png"
    specs_dict = {
        "Gramatura": "Papel Couché Premium 300g/m² Real",
        "Formato": "63.5 x 88.9 mm (Padrão TCG Standard)",
        "Acabamento": "Laminação Térmica Fosca Hi-Tac",
        "Cantos": "Arredondados com Cantoneira Raio 3.0mm",
        "Efeito Especial": "Película Holográfica Iridescente",
        "Produção": "Chão de Fábrica Studio Kustom",
    }
    shopee_gen.gerar_lamina_tecnica_shopee(
        product_type="Guia de Qualidade & Acabamento",
        title="ESPECIFICAÇÕES TÉCNICAS INDUSTRIAIS",
        specs_dict=specs_dict,
        mockup_image=mockup_card_img,
        notice_text="Garantia Studio Kustom: desvio de corte < 0.2mm e fidelidade SSIM >= 0.88.",
        theme_mode=ThemeMode.INFORMATIVO,
        output_path=capa_info_path,
    )
    print(f"  -> Salvo: {capa_info_path} (Modo INFORMATIVO - Roxo Místico #560BAD)")

    # 5.4 Carrossel de 3 Lâminas para Instagram (1080x1350 px / 4:5 Retrato)
    print("  -> Gerando carrossel de 3 lâminas para Instagram Feed (4:5)...")
    benefits = [
        "Papel Couché 300g real com rigidez de fábrica",
        "Película Hi-Tac anti-risco e anti-descolamento",
        "Brilho iridescente holográfico de alto impacto",
        "Cantos arredondados raio 3mm sem rebarbas",
    ]
    insta_gen.gerar_carrossel_instagram(
        mockup_images=[mockup_card_img, mockup_mug_img, mockup_card_img],
        title="TRANSFORME SUA ARTE EM CARTA COLECIONÁVEL",
        benefits_list=benefits,
        cta_text="Peça agora pelo link da bio • Enviamos para todo o Brasil",
        format_ratio="4:5",
        theme_mode=ThemeMode.PERSONALIZADO,
        output_dir=output_dir,
    )
    print(f"  -> Salvo: {output_dir / 'carrossel_lamina_1.png'}")
    print(f"  -> Salvo: {output_dir / 'carrossel_lamina_2.png'}")
    print(f"  -> Salvo: {output_dir / 'carrossel_lamina_3.png'}")

    print("\n[OK] Todas as amostras de cores oficiais da Studio Kustom geradas com sucesso absoluto na pasta output/!")


if __name__ == "__main__":
    main()


