# Studio Kustom Engine (KustomCraft)

Plataforma de automação gráfica, pré-impressão industrial e gestão de pedidos para o chão de fábrica da **Studio Kustom** (papelaria fina 300g, cartas TCG/RPG, pôsteres e canecas).

---

## 🛠️ Stack Tecnológica Homologada (Fase 1)

- **Linguagem**: Python 3.12+ (testado em Python 3.13)
- **Manipulação Vetorial de PDF**: PyMuPDF (`fitz`) >= 1.23.0
- **Processamento Gráfico Raster**: Pillow (`PIL`) >= 10.0.0
- **Modelagem de Dados**: Pydantic v2
- **Framework de Testes & TDD**: Pytest >= 8.0.0 com `pytest-cov` (99% de cobertura)

---

## 📐 Estrutura de Diretórios

```text
kustomcraft-engine/
├── .env                                 # Variáveis de ambiente locais
├── .env.example                         # Template de variáveis de ambiente
├── .gitignore                           # Exclusões de git
├── pyproject.toml                       # Configuração de build e pytest
├── requirements.txt                     # Dependências do projeto
├── README.md                            # Guia rápido
├── src/
│   ├── __init__.py
│   ├── core/                            # Regras de Negócio e Cálculos Gráficos
│   │   ├── __init__.py
│   │   ├── presets.py                   # Tabela oficial de formatos (SA4, SA3, Canecas, TCGs)
│   │   └── ssim_validator.py            # Motor 8: Validador Perceptual Anti-Alucinação (SSIM/MSE)
│   └── engines/                         # Motores Gráficos Independentes
│       ├── __init__.py
│       ├── motor1_imposicao_duplex.py   # Motor 1: Imposição Duplex com Espelhamento Y para Konica C558
│       ├── motor2_upscaler_gemini.py    # Motor 2: Pipeline de Upscaling Universal (Gemini + Lanczos)
│       ├── motor3_estudio_canecas.py    # Motor 3: Estúdio de Canecas e Sublimação (Epson L110)
│       ├── motor4_fabrica_tcg.py        # Motor 4: Fábrica de Cartas TCG/RPG (Pokémon, Magic, OP, Ordem)
│       └── motor5_sangria_outpaint.py   # Motor 5: Sangria Industrial & Outpaint (+5mm Mirror Edge)
└── tests/                               # Testes Automatizados (TDD Rigoroso)
    ├── __init__.py
    ├── conftest.py                      # Fixtures reutilizáveis
    └── unit/
        ├── __init__.py
        ├── test_presets.py              # Validação milimétrica dos presets
        ├── test_motor1_duplex.py        # Testes de duplex e desvio < 0.2mm
        ├── test_motor2_upscaler.py      # Testes de upscaler e mocks Gemini
        ├── test_motor3_canecas.py       # Testes de canecas, compensação e tiras
        ├── test_motor4_fabrica_tcg.py   # Testes da fábrica TCG e esteira End-to-End
        ├── test_motor5_sangria.py       # Testes de sangria +5mm e integração
        └── test_motor8_ssim.py          # Testes de validação perceptual SSIM
```

---

## 🚀 Como Executar os Testes

Com o ambiente Python ativo, instale as dependências e rode a suíte de testes:

```bash
pip install -r requirements.txt
pytest -v --cov=src --cov-report=term-missing
```

---

## 🖨️ Funcionamento do Motor 1 (Imposição Duplex)

A impressora laser industrial **Konica Minolta bizhub C558** ao processar papel Couché 300g frente e verso opera a virada de folha pela borda longa.

O algoritmo do `motor1_imposicao_duplex.py`:
1. Calcula a grade proporcional centralizada na folha (ex: 3x3 em Super A3, 2x3 em Super A4).
2. Para a página 1 (Frente), aloca os slots $(r, c)$ com coordenadas $(X, Y)$ exatas.
3. Para a página 2 (Verso), espelha o centro geométrico no eixo Y:
   $$\text{Center}X_{verso} = W_{folha} - \text{Center}X_{frente} + \text{offset}_x$$
   $$\text{Center}Y_{verso} = \text{Center}Y_{frente} + \text{offset}_y$$
4. As colunas são espelhadas automaticamente: a coluna $c$ da frente torna-se $(C - 1 - c)$ no verso.
5. Emite marcas de corte (*crop marks*) e cruzes de registro (*registration targets*) a **0.25 pt**, permitindo validação visual instantânea na mesa de luz.

---

## 🛡️ Motores da Fase 2

### Motor 5: Sangria Industrial & Outpaint (`motor5_sangria_outpaint.py`)
- Extensão configurável (padrão de $+5\text{ mm}$ por lado / $+10\text{ mm}$ totais a 300 DPI: $59\text{ px}$ por lado).
- Modo offline `mirror_edge` com transição suave (*feathering*) nas 4 costuras para corte perfeito na guilhotina e estilete.
- Modo generativo `gemini_inpaint` para fundos complexos com fallback automático seguro.
- Método `prepare_for_imposition` para alimentar diretamente o Motor 1.

### Motor 2: Pipeline de Upscaling Universal (`motor2_upscaler_gemini.py`)
- Integração com a API Google Gemini via `GEMINI_API_KEY` com prompt estrito de super-resolução.
- Fallback determinístico offline de alta fidelidade com Pillow Lanczos + UnsharpMask para preservar nitidez tipográfica.

### Motor 8: Validador Perceptual Anti-Alucinação (`ssim_validator.py`)
- Métricas SSIM e MSE via `scikit-image` e `numpy`.
- Downsampling de referência 1:1 para auditoria geométrica pixel a pixel.
- Portão de corte: $\text{SSIM} < 0.88$ reprova o job imediatamente com relatório de causa-raiz.

---

## 🎨 Motores da Fase 3

### Motor 3: Estúdio de Canecas & Sublimação Térmica (`motor3_estudio_canecas.py`)
- Gabaritos milimétricos oficiais: Cerâmica $220 \times 95\text{ mm}$ ($2598 \times 1122\text{ px}$ a 300 DPI), Chopp $200 \times 90\text{ mm}$ e Polímero $205 \times 85\text{ mm}$.
- Compensação térmica calibrada ($+18\%$ saturação, $+10\%$ brilho, $+12\%$ contraste) para a prensa cilíndrica a 200°C.
- Espelhamento horizontal automático para impressão sublimática na Epson L110.
- Aproveitamento inteligente de papel: 2 tiras em A4 ou 3 tiras em Super A4 com marcas de corte finas a $0.25\text{ pt}$.

### Motor 4: Fábrica de Cartas TCG e RPG (`motor4_fabrica_tcg.py`)
- Schemas formais Pydantic v2: `PokemonCardSpec`, `MagicCardSpec`, `OnePieceCardSpec`, `OrdemParanormalCardSpec` e `GenericCardSpec`.
- Composição multicamadas: Fundo temático, janela de arte central proporcional, moldura chanfrada com transparência e tipografia nítida com quebra de linha.
- Suporte aos formatos Standard ($63.5 \times 88.9\text{ mm}$) e Japonês ($59 \times 86\text{ mm}$).
- Verso oficial de baralho com padrão geométrico de segurança.
- **Esteira End-to-End**: Integração nativa com Motor 5 (sangria $+5\text{mm}$) e Motor 1 (imposição duplex Super A3 com desvio $< 0.001\text{ mm}$).


