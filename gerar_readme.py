# -*- coding: utf-8 -*-
"""
Gera o README.md completo do projeto.

Escreve o arquivo na raiz do repositorio, pronto para commit.
Reexecutavel: sobrescreve o README.md existente.

Uso:
    python gerar_readme.py
"""
from pathlib import Path

PASTA_RAIZ = Path(__file__).resolve().parent
ARQUIVO_README = PASTA_RAIZ / "README.md"

# Delimitador de bloco de codigo Markdown, montado em tempo de execucao.
# Evita ter crases literais no codigo-fonte, que quebram o copiar-colar.
CRASE = chr(96)
CERCA = CRASE * 3


def bloco(linguagem: str, conteudo: str) -> str:
    """
    Monta um bloco de codigo Markdown.

    Args:
        linguagem: identificador da linguagem (text, bash, powershell, env).
        conteudo: texto interno do bloco, sem as cercas.

    Returns:
        String com as cercas de abertura e fechamento.
    """
    return f"{CERCA}{linguagem}\n{conteudo}\n{CERCA}\n"


CABECALHO = """# Pipeline de Dados — Viagens a Serviço (Portal da Transparência)

Pipeline ETL completo em arquitetura **Medallion** (Raw, Silver e Gold) para os dados de viagens a serviço do Governo Federal brasileiro, referentes aos 6 primeiros meses de 2025.

**Aluno:** Filippe Borba
**Turma:** Análise de Dados T6 — SENAI
**Repositório:** [Projeto-Avaliativo-Modulo1-FilippeBorba](https://github.com/borbaf/Projeto-Avaliativo-Modulo1-FilippeBorba)
**Stack:** Python 3.10+ · PostgreSQL · psycopg2 · pandas · matplotlib · seaborn · pytest

---

## Sumário

1. [Visão Geral](#visão-geral)
2. [Arquitetura Medallion](#arquitetura-medallion)
3. [Base de Dados e Contrato Técnico](#base-de-dados-e-contrato-técnico)
4. [Dicionário de Dados](#dicionário-de-dados)
5. [Reflexão Teórica — ETL e Qualidade por Camada](#reflexão-teórica--etl-e-qualidade-por-camada)
6. [Insights de Negócio](#insights-de-negócio)
7. [Como Executar](#como-executar)
8. [Testes](#testes)
9. [Limitações Conhecidas](#limitações-conhecidas)
10. [Decisões Técnicas](#decisões-técnicas)

---

## Visão Geral

Os órgãos públicos brasileiros publicam seus dados de viagens a serviço no Portal da Transparência, permitindo o controle social sobre os gastos. Esses dados, porém, chegam como arquivos brutos que precisam virar informação confiável para análise.

Este projeto constrói o pipeline completo, da extração dos CSVs brutos até a camada analítica, com tipagem, limpeza, modelagem relacional e visualizações que respondem a sete perguntas de negócio.

### Números do projeto

| Métrica | Valor |
|---|---|
| Linhas carregadas na Raw | 1.879.385 |
| Linhas transformadas na Silver | 1.773.687 |
| Viagens analisadas | 341.860 |
| Gasto total consolidado | R$ 1.200.760.089,85 |
| Órgãos superiores distintos | 35 |
| Trechos registrados | 763.349 |
| Testes automatizados | 54 (100% aprovados) |

---
"""

DIAGRAMA_CAMADAS = """FONTE
Portal da Transparência — viagens_2025_6meses.zip (64,5 MB)
4 CSVs · separador ";" · encoding latin-1 · decimal vírgula
        |
        v
CAMADA RAW (0_criar_banco.sql + 1_extrair.py)
4 tabelas VARCHAR sem constraints, espelho fiel do CSV
raw_viagem · raw_pagamento · raw_passagem · raw_trecho
1.879.385 linhas · carga idempotente com TRUNCATE
        |
        v
CAMADA SILVER (2_transformar.py)
Tipagem, conversão de datas e decimais, deduplicação, FK
silver_viagem · silver_pagamento · silver_passagem · silver_trecho
1.773.687 linhas · PK, FK e 8 constraints explícitas
        |
        v
CAMADA GOLD (3_analise.ipynb + sql/gold_agregada.sql)
3 VIEWs agregadas por grão, sem risco de inflação de somas
gold_gastos_por_orgao · gold_pagamentos_por_orgao · gold_gastos_por_destino
7 perguntas de negócio respondidas com SQL, tabela e gráfico"""

ARVORE_PASTAS = """Projeto-Avaliativo-Modulo1-FilippeBorba/
├── 0_criar_banco.sql          # DDL das 8 tabelas (Raw + Silver)
├── 1_extrair.py               # download, extração e carga da Raw
├── 2_transformar.py           # Raw → Silver com tipagem e dedup
├── 3_analise.ipynb            # Gold, 7 perguntas e 4 gráficos
├── config.py                  # caminhos, conexão e constantes
├── banco.py                   # interface de acesso ao PostgreSQL
├── setup.sh                   # automação para Linux, macOS e Git Bash
├── setup.ps1                  # automação para Windows PowerShell
├── gerar_readme.py            # gera este README a partir do código
├── .env.example               # modelo de credenciais
├── .gitignore
├── requirements.txt
├── README.md
├── data/
│   ├── amostras/              # 4 CSVs reduzidos (2.000 linhas), versionados
│   └── raw/                   # CSVs completos, ignorados pelo Git
├── sql/
│   └── gold_agregada.sql      # DDL das VIEWs Gold, versionado
├── logs/
│   └── .gitkeep
└── tests/
    ├── conftest.py
    └── test_pipeline.py       # 54 testes end-to-end"""

ARQUITETURA = f"""
## Arquitetura Medallion

O pipeline segue a arquitetura Medallion em três camadas, cada uma com responsabilidade única e crescente em qualidade.

### Diagrama das camadas

{bloco("text", DIAGRAMA_CAMADAS)}
### Estrutura de pastas

{bloco("text", ARVORE_PASTAS)}
### Justificativas das escolhas

- Raiz achatada com arquivos numerados porque o enunciado exige a ordem de execução
- `config.py` e `banco.py` na raiz porque o roteiro os define como arquivos do projeto
- `sql/gold_agregada.sql` separado para versionar a modelagem da Gold e garantir reprodutibilidade fora do notebook
- `data/raw/` no `.gitignore` porque os CSVs completos somam 461 MB
- `data/amostras/` versionado para comprovar estrutura, encoding, separador e formato dos campos
- `tests/` fora do caminho numerado para não confundir o avaliador
- `setup.sh` e `setup.ps1` automatizam a preparação do ambiente nos dois sistemas operacionais
- `gerar_readme.py` mantém a documentação como código, permitindo regenerar este arquivo

---
"""

BASE_DADOS = """
## Base de Dados e Contrato Técnico

### Fonte

O arquivo `viagens_2025_6meses.zip` tem 64,5 MB comprimido e contém 6 meses de 2025 de viagens a serviço do Portal da Transparência. Ao descompactar, são gerados quatro arquivos CSV.

| Arquivo | Tamanho | Situação no GitHub |
|---|---|---|
| 2025_Viagem.csv | 194 MB | bloqueado, excede 100 MB |
| 2025_Trecho.csv | 118 MB | bloqueado, excede 100 MB |
| 2025_Pagamento.csv | 109 MB | bloqueado, excede 100 MB |
| 2025_Passagem.csv | 40 MB | aceito, abaixo de 50 MB |
| **Total** | **461 MB** | inviável versionar completo |

Três dos quatro arquivos excedem o limite rígido de 100 MB por arquivo do GitHub e o push seria rejeitado. A decisão foi versionar amostras representativas em `data/amostras/` (2.000 linhas de dados por arquivo, geradas preservando os bytes originais, sem reescrita por pandas) e manter os arquivos completos em `data/raw/`, pasta ignorada pelo Git e alimentada pelo `1_extrair.py`.

### Contrato técnico dos CSVs

| Propriedade | Valor |
|---|---|
| Separador | `;` (ponto e vírgula) |
| Encoding | `latin-1` |
| Decimal | vírgula (ex.: `1272,97`) |
| Datas | `DD/MM/AAAA` |
| Cabeçalho | presente na primeira linha |

O `1_extrair.py` valida o número de colunas do cabeçalho **antes** do `TRUNCATE`, abortando a carga se houver divergência. Isso protege contra desalinhamento silencioso, que corromperia os dados sem gerar erro.

### Volume por arquivo e por tabela

| CSV | Linhas de dados | Tabela Raw | Colunas |
|---|---|---|---|
| 2025_Viagem.csv | 341.860 | `raw_viagem` | 22 |
| 2025_Pagamento.csv | 606.916 | `raw_pagamento` | 10 |
| 2025_Passagem.csv | 167.260 | `raw_passagem` | 19 |
| 2025_Trecho.csv | 763.349 | `raw_trecho` | 14 |
| **Total** | **1.879.385** | — | **65** |

### Tempo de carga observado

| Tabela | Blocos | Tempo |
|---|---|---|
| raw_viagem | 7 | 0m25s |
| raw_pagamento | 13 | 0m17s |
| raw_passagem | 4 | 0m07s |
| raw_trecho | 16 | 0m25s |
| **Total** | **40** | **1m15s** |

Todas as quatro tabelas apresentaram `descartadas=0`, confirmando que o mapeamento de colunas está alinhado com os cabeçalhos reais dos CSVs.

---
"""

DICIONARIO = """
## Dicionário de Dados

### Camada Raw — 4 tabelas espelho

As tabelas Raw têm as mesmas colunas dos CSVs originais, todas `VARCHAR` e sem constraints, replicando o arquivo inteiro inclusive as colunas que a Silver descarta (`cpf_viajante`, `funcao` e dados de volta da passagem).

| Tabela | Colunas | Linhas |
|---|---|---|
| `raw_viagem` | 22 | 341.860 |
| `raw_pagamento` | 10 | 606.916 |
| `raw_passagem` | 19 | 167.260 |
| `raw_trecho` | 14 | 763.349 |
| **Total** | **65** | **1.879.385** |

### Camada Silver — 4 tabelas tipadas

#### `silver_viagem` — 341.860 linhas

| Coluna | Tipo | Restrição |
|---|---|---|
| `id_viagem` | VARCHAR(20) | PRIMARY KEY NOT NULL |
| `num_proposta` | VARCHAR(20) | — |
| `situacao` | VARCHAR(50) | — |
| `viagem_urgente` | VARCHAR(5) | — |
| `cod_orgao_superior` | VARCHAR(20) | — |
| `nome_orgao_superior` | VARCHAR(255) | NOT NULL |
| `nome_viajante` | VARCHAR(255) | — |
| `cargo` | VARCHAR(255) | — |
| `data_inicio` | DATE | convertido de DD/MM/AAAA |
| `data_fim` | DATE | convertido de DD/MM/AAAA |
| `destinos` | VARCHAR(4000) | — |
| `motivo` | VARCHAR(4000) | — |
| `valor_diarias` | DECIMAL(10,2) | CHECK >= 0 |
| `valor_passagens` | DECIMAL(10,2) | — |
| `valor_devolucao` | DECIMAL(10,2) | — |
| `valor_outros_gastos` | DECIMAL(10,2) | — |
| `valor_total` | DECIMAL(12,2) | calculado |
| `duracao_dias` | INT | calculado |

#### `silver_passagem` — 100.075 linhas

| Coluna | Tipo | Restrição |
|---|---|---|
| `id_passagem` | INT | PRIMARY KEY GENERATED ALWAYS AS IDENTITY |
| `id_viagem` | VARCHAR(20) | FOREIGN KEY → silver_viagem NOT NULL |
| `meio_transporte` | VARCHAR(50) | — |
| `pais_origem_ida` | VARCHAR(60) | — |
| `uf_origem_ida` | VARCHAR(40) | — |
| `cidade_origem_ida` | VARCHAR(80) | — |
| `pais_destino_ida` | VARCHAR(60) | — |
| `uf_destino_ida` | VARCHAR(40) | — |
| `cidade_destino_ida` | VARCHAR(80) | — |
| `valor_passagem` | DECIMAL(10,2) | CHECK >= 0 |
| `taxa_servico` | DECIMAL(10,2) | CHECK >= 0 |
| `data_emissao` | DATE | convertido de DD/MM/AAAA |

#### `silver_pagamento` — 568.403 linhas

| Coluna | Tipo | Restrição |
|---|---|---|
| `id_pagamento` | INT | PRIMARY KEY GENERATED ALWAYS AS IDENTITY |
| `id_viagem` | VARCHAR(20) | FOREIGN KEY → silver_viagem NOT NULL |
| `num_proposta` | VARCHAR(20) | — |
| `nome_orgao_pagador` | VARCHAR(255) | — |
| `nome_ug_pagadora` | VARCHAR(255) | — |
| `tipo_pagamento` | VARCHAR(50) | NOT NULL |
| `valor` | DECIMAL(10,2) | CHECK >= 0 |

#### `silver_trecho` — 763.349 linhas

| Coluna | Tipo | Restrição |
|---|---|---|
| `id_trecho` | INT | PRIMARY KEY GENERATED ALWAYS AS IDENTITY |
| `id_viagem` | VARCHAR(20) | FOREIGN KEY → silver_viagem NOT NULL |
| `sequencia_trecho` | INT | UNIQUE (id_viagem, sequencia_trecho) |
| `origem_data` | DATE | — |
| `origem_uf` | VARCHAR(40) | — |
| `origem_cidade` | VARCHAR(80) | — |
| `destino_data` | DATE | — |
| `destino_uf` | VARCHAR(40) | — |
| `destino_cidade` | VARCHAR(80) | — |
| `meio_transporte` | VARCHAR(50) | — |
| `numero_diarias` | DECIMAL(10,2) | CHECK >= 0 |

### As 8 constraints exigidas

| Tabela | Constraint 1 | Constraint 2 |
|---|---|---|
| `silver_viagem` | NOT NULL em `nome_orgao_superior` | CHECK `valor_diarias >= 0` |
| `silver_pagamento` | CHECK `valor >= 0` | NOT NULL em `tipo_pagamento` |
| `silver_passagem` | CHECK `valor_passagem >= 0` | CHECK `taxa_servico >= 0` |
| `silver_trecho` | CHECK `numero_diarias >= 0` | UNIQUE em (`id_viagem`, `sequencia_trecho`) |

> **Nota técnica:** o dicionário original usa `AUTO_INCREMENT` (sintaxe MySQL). Em PostgreSQL o equivalente é `GENERATED ALWAYS AS IDENTITY`. A tradução está registrada em comentário no topo do `0_criar_banco.sql`.

### Camada Gold — 3 VIEWs

| VIEW | Grão | Colunas principais |
|---|---|---|
| `gold_gastos_por_orgao` | 1 linha por órgão superior (35 linhas) | qtd_viagens, valor_total_gasto, valor_medio_viagem, total_diarias, total_passagens, total_devolucao, total_outros_gastos, duracao_media_dias |
| `gold_pagamentos_por_orgao` | 1 linha por órgão pagador | qtd_pagamentos, valor_total_pago, valor_medio_pago |
| `gold_gastos_por_destino` | 1 linha por destino principal | qtd_viagens, valor_total_gasto, valor_medio_viagem |

---
"""

REFLEXAO = """
## Reflexão Teórica — ETL e Qualidade por Camada

### Camada Raw — fidelidade absoluta

A Raw existe para preservar o dado exatamente como chegou da fonte. Nenhuma conversão, nenhum descarte, nenhuma interpretação. Todas as colunas são `VARCHAR`, inclusive as que serão descartadas na Silver (`cpf_viajante`, `funcao`, `descricao_funcao`).

**Por que isso importa:** se a Silver descartar uma linha por erro de conversão, a Raw permite reprocessar sem baixar o arquivo novamente. A Raw é o seguro contra perda de informação.

**Decisão de qualidade:** a carga é idempotente. Cada execução faz `TRUNCATE TABLE ... RESTART IDENTITY` antes de inserir. Reexecutar o pipeline não duplica dados.

### Camada Silver — tipagem e integridade

A Silver é onde o dado bruto vira dado confiável. Três operações acontecem aqui:

**1. Tipagem.** Datas em `DD/MM/AAAA` viram `DATE`. Decimais com vírgula viram `DECIMAL(10,2)`. Textos são truncados no limite da coluna destino.

**2. Cálculo de colunas derivadas.** `valor_total` é a soma das quatro parcelas (`diarias + passagens + devolucao + outros_gastos`). `duracao_dias` é a diferença entre `data_fim` e `data_inicio`.

**3. Deduplicação com chave explícita.** Nunca `drop_duplicates()` genérico. Cada tabela tem sua chave justificada:

| Tabela | Chave de deduplicação | Justificativa |
|---|---|---|
| `silver_viagem` | `id_viagem` | PK natural da viagem |
| `silver_passagem` | `id_viagem + num_proposta + valor_passagem + data_emissao` | Uma passagem é única por viagem, proposta, valor e data de emissão |
| `silver_pagamento` | `id_viagem + num_proposta + tipo_pagamento + valor` | Um pagamento é único por viagem, proposta, tipo e valor |
| `silver_trecho` | `id_viagem + sequencia_trecho` | A sequência do trecho é única dentro da viagem |

**Descarte de órfãos.** Antes de carregar as tabelas filhas, o pipeline carrega o conjunto de `id_viagem` válidos em `silver_viagem`. Linhas com `id_viagem` inexistente são descartadas com o motivo `fk_orfao` registrado no log. Isso evita violação de FK durante a carga.

#### Resultado da carga

| Tabela | Lidas | Inseridas | Descartadas | Motivos |
|---|---|---|---|---|
| silver_viagem | 341.860 | 341.860 | 0 | — |
| silver_passagem | 167.260 | 100.075 | 67.185 | duplicata: 66.521; conversão inválida: 664 |
| silver_pagamento | 606.916 | 568.403 | 38.513 | duplicata: 38.513 |
| silver_trecho | 763.349 | 763.349 | 0 | — |

### Camada Gold — agregação sem inflação

O risco central da Gold é o **cruzamento de grãos diferentes**. Se você juntar `silver_viagem` (1 linha por viagem) com `silver_pagamento` (0 a N por viagem) e somar `valor_total`, cada viagem com 3 pagamentos será contada 3 vezes. O total infla.

**Regra aplicada:** agregar por entidade antes de cruzar tabelas de grão diferente. Cada VIEW Gold tem um grão único e explícito:

| Tabela | Grão da linha | Cardinalidade |
|---|---|---|
| `silver_viagem` | uma linha por viagem | tabela-mãe |
| `silver_passagem` | uma linha por passagem emitida | 0 a N por viagem |
| `silver_pagamento` | uma linha por pagamento | 0 a N por viagem |
| `silver_trecho` | uma linha por trecho | único por (id_viagem, sequencia_trecho) |

**Validação aplicada:** a soma de `valor_total_gasto` em `gold_gastos_por_orgao` é idêntica à soma de `valor_total` em `silver_viagem` (`R$ 1.200.760.089,85`). Se houvesse inflação, os valores divergiriam. O teste `test_gold_orgao_soma_bate` automatiza essa verificação.

---
"""

INSIGHTS = """
## Insights de Negócio

As sete perguntas do enunciado, respondidas com evidência numérica.

### Pergunta 1 — Qual órgão superior teve o maior valor total gasto?

| # | Órgão superior | Viagens | Valor total gasto | Valor médio |
|---|---|---|---|---|
| 1 | Ministério da Justiça e Segurança Pública | 75.742 | R$ 490.813.474,85 | R$ 6.480,07 |
| 2 | Ministério da Defesa | 61.912 | R$ 157.059.698,59 | R$ 2.536,82 |
| 3 | Ministério da Educação | 65.295 | R$ 112.519.456,96 | R$ 1.723,25 |
| 4 | Ministério do Meio Ambiente e Mudança do Clima | 19.413 | R$ 50.548.377,44 | R$ 2.603,84 |
| 5 | Ministério da Previdência Social | 8.190 | R$ 40.921.476,10 | R$ 4.996,52 |

**Insight:** o Ministério da Justiça concentra **41% de todo o gasto** (`R$ 490,8 mi` de `R$ 1,2 bi`). Isso é explicável: a pasta inclui Polícia Federal, Polícia Rodoviária Federal e Força Nacional, órgãos com deslocamento intenso. O valor médio por viagem também é o mais alto do top 5 (`R$ 6.480,07`), sugerindo operações de maior duração ou destino distante.

### Pergunta 2 — Qual o valor médio das viagens por destino?

| # | Destino principal | Viagens | Valor médio | Valor total |
|---|---|---|---|---|
| 1 | Jacareacanga/PA | 105 | R$ 42.743,59 | R$ 4.488.076,61 |
| 2 | Tucumã/PA | 118 | R$ 31.297,42 | R$ 3.693.095,17 |
| 3 | Bonn/Alemanha | 77 | R$ 29.794,03 | R$ 2.294.140,45 |
| 4 | Itaituba/PA | 222 | R$ 26.569,61 | R$ 5.898.452,87 |
| 5 | Tóquio/Japão | 135 | R$ 25.727,65 | R$ 3.473.232,68 |

**Insight:** três dos cinco destinos mais caros estão no Pará (Jacareacanga, Tucumã, Itaituba), todos em áreas de garimpo ou terra indígena, com acesso aéreo obrigatório e logística complexa. Os destinos internacionais (Bonn, Tóquio, Genebra, Xangai, Pequim, Montreal) aparecem em seguida, com valores médios entre `R$ 24 mil` e `R$ 30 mil`.

### Pergunta 3 — Quais foram as viagens mais caras?

| # | Órgão | Viajante | Duração | Valor total |
|---|---|---|---|---|
| 1 | Ministério da Defesa | RENATO RODRIGUES DE AGUIAR FREIRE | 18 dias | R$ 261.287,40 |
| 2 | Ministério de Minas e Energia | PIETRO ADAMO SAMPAIO MENDES | 13 dias | R$ 245.852,80 |
| 3 | Ministério da Justiça | JULYANA DOS SANTOS COELHO | 364 dias | R$ 216.729,36 |
| 4 | Ministério da Justiça | Informações protegidas por sigilo | 295 dias | R$ 213.987,50 |
| 5 | Ministério da Justiça | BRUNO REZENDE CABRAL | 364 dias | R$ 207.220,14 |

**Insight:** a viagem mais cara custou `R$ 261.287,40` em 18 dias, média de `R$ 14.516` por dia. As viagens de 364 dias (01/01 a 31/12) correspondem a servidores em exercício fora da sede ou viagens continuadas, não a deslocamentos únicos. O valor acumulado reflete o período completo.

### Pergunta 4 — Qual o valor médio pago por tipo de pagamento?

| Tipo de pagamento | Pagamentos | Valor médio | Valor total |
|---|---|---|---|
| DIÁRIAS | 365.945 | R$ 1.794,34 | R$ 656.629.482,75 |
| PASSAGEM | 186.006 | R$ 1.856,79 | R$ 345.374.617,87 |
| Serviço correlato: seguro | 4.882 | R$ 447,72 | R$ 2.185.792,32 |
| RESTITUIÇÃO | 11.570 | R$ 245,69 | R$ 2.842.678,82 |

**Insight:** diárias concentram **65% do valor pago** (`R$ 656,6 mi`), com ticket médio de `R$ 1.794,34`. Passagens vêm em segundo com `R$ 345,4 mi` e ticket médio ligeiramente maior (`R$ 1.856,79`). Seguros e restituições são residuais.

### Pergunta 5 — Quantos trechos por meio de transporte?

| Meio de transporte | Trechos | Percentual |
|---|---|---|
| Veículo Oficial | 386.424 | 50,62% |
| Aéreo | 232.666 | 30,48% |
| Rodoviário | 64.970 | 8,51% |
| Veículo Próprio | 42.846 | 5,61% |
| Inválido | 26.659 | 3,49% |
| Fluvial | 8.429 | 1,10% |
| Ferroviário | 874 | 0,11% |
| Marítimo | 481 | 0,06% |

**Insight:** veículo oficial domina com **50,62% dos trechos**, seguido por aéreo (30,48%). A soma dos percentuais é 99,98% (arredondamento). Os 3,49% classificados como "Inválido" vêm da fonte e foram preservados pela Silver, não descartados.

### Pergunta 6 — Quantos trechos cada viagem tem, em média, e qual o recorde?

| Métrica | Valor |
|---|---|
| Média de trechos por viagem | 2,63 |
| Recorde de trechos em uma viagem | 68 |
| Mínimo de trechos | 1 |
| Viagens com trecho registrado | 290.259 |

**Insight:** a média de 2,63 trechos considera apenas as 290.259 viagens que têm trecho registrado (84,9% do total). A viagem com 68 trechos é um caso extremo, provavelmente uma comitiva com múltiplas escalas.

### Pergunta 7 — Como os gastos se distribuem ao longo do período?

| Mês | Órgão líder | Valor total |
|---|---|---|
| 2025-01 | Ministério da Justiça e Segurança Pública | R$ 235.393.238,14 |
| 2025-01 | Ministério da Defesa | R$ 11.561.908,55 |
| 2025-01 | Ministério da Educação | R$ 6.570.129,55 |

**Insight:** janeiro concentra o maior volume de gastos, com o Ministério da Justiça sozinho respondendo por `R$ 235,4 mi`. O padrão se repete nos meses seguintes, com a mesma concentração na pasta da Justiça.

### Consolidação geral

| Métrica | Valor |
|---|---|
| Viagens | 341.860 |
| Pagamentos | 568.403 |
| Passagens | 100.075 |
| Trechos | 763.349 |
| Gasto total | R$ 1.200.760.089,85 |
| Média por viagem | R$ 3.512,43 |
| Razão pagamentos/viagens | 0,84 |

**Sobre a razão 0,84:** pagamentos somam `R$ 1,007 bi` contra `R$ 1,200 bi` em viagens. Isso significa que **84% do valor das viagens tem pagamento correspondente registrado**. Os 16% restantes são viagens sem pagamento vinculado, provavelmente canceladas, pagas por outro meio, ou com pagamento ainda não processado. Não é erro: é característica do dataset.

---
"""

CMD_SETUP_SH = """chmod +x setup.sh
./setup.sh"""

CMD_SETUP_PS1 = """Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\\\\setup.ps1"""

CMD_VARIACOES_SH = """./setup.sh --sem-docker    # usa PostgreSQL local em vez de Docker
./setup.sh --so-testes     # apenas roda os testes
./setup.sh --help          # exibe a ajuda"""

CMD_VARIACOES_PS1 = """.\\\\setup.ps1 -SemDocker    # usa PostgreSQL local em vez de Docker
.\\\\setup.ps1 -SoTestes     # apenas roda os testes
Get-Help .\\\\setup.ps1 -Full"""

CMD_CLONE = """git clone https://github.com/borbaf/Projeto-Avaliativo-Modulo1-FilippeBorba.git
cd Projeto-Avaliativo-Modulo1-FilippeBorba"""

CMD_VENV_LINUX = """python3 -m venv .venv
source .venv/bin/activate"""

CMD_VENV_WIN = """python -m venv .venv
.\\\\.venv\\\\Scripts\\\\Activate.ps1"""

CMD_PIP = """pip install -r requirements.txt"""

CMD_CP_ENV = """cp .env.example .env"""

CONTEUDO_ENV = """POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua_senha
POSTGRES_DATABASE=transparencia"""

CMD_DOCKER = """docker run -d \\\\
  --name transparencia_postgres \\\\
  -e POSTGRES_PASSWORD=sua_senha \\\\
  -e POSTGRES_DB=transparencia \\\\
  -p 5432:5432 \\\\
  postgres:16"""

CMD_PSQL = """psql -h localhost -U postgres -d transparencia -f 0_criar_banco.sql"""

CMD_PSQL_DOCKER = """docker exec -i transparencia_postgres psql -U postgres -d transparencia < 0_criar_banco.sql"""

CMD_PIPELINE = """# Fase 1 — download, extração e carga da Raw (~1m15s)
python 1_extrair.py

# Fase 2 — transformação Raw → Silver (~3min)
python 2_transformar.py

# Fase 3 — Gold, perguntas e gráficos
jupyter notebook 3_analise.ipynb"""

CMD_TESTES = """python -m pytest tests/ -v"""

SAIDA_TESTES = """54 passed in 7.60s"""

ORDEM_EXECUCAO = """1. docker run (ou PostgreSQL local)
2. psql -f 0_criar_banco.sql
3. python 1_extrair.py
4. python 2_transformar.py
5. jupyter notebook 3_analise.ipynb (Restart and Run All)
6. python -m pytest tests/ -v"""

COMO_EXECUTAR = f"""
## Como Executar

### Pré-requisitos

- Python 3.10 ou superior
- PostgreSQL 14 ou superior (ou Docker)
- Git

### Execução automatizada (recomendado)

Dois scripts automatizam toda a sequência: criar o ambiente virtual, instalar as dependências, subir o PostgreSQL, criar as tabelas, rodar o pipeline e executar os testes.

**Linux, macOS ou Git Bash:**

{bloco("bash", CMD_SETUP_SH)}
**Windows PowerShell:**

{bloco("powershell", CMD_SETUP_PS1)}
**Variações disponíveis nos dois scripts:**

{bloco("bash", CMD_VARIACOES_SH)}
{bloco("powershell", CMD_VARIACOES_PS1)}
**Na primeira execução**, o script cria o `.env` a partir do `.env.example` e para, pedindo que você preencha a senha. Edite o arquivo e rode novamente.

### Execução manual passo a passo

Se preferir controlar cada etapa:

#### 1. Clonar o repositório

{bloco("bash", CMD_CLONE)}
#### 2. Criar e ativar o ambiente virtual

{bloco("bash", CMD_VENV_LINUX)}
No Windows (PowerShell):

{bloco("powershell", CMD_VENV_WIN)}
#### 3. Instalar dependências

{bloco("bash", CMD_PIP)}
#### 4. Configurar credenciais

{bloco("bash", CMD_CP_ENV)}
Conteúdo do `.env`:

{bloco("env", CONTEUDO_ENV)}
#### 5. Subir o PostgreSQL

Com Docker:

{bloco("bash", CMD_DOCKER)}
Com PostgreSQL local: crie o banco `transparencia` manualmente.

#### 6. Criar as tabelas

{bloco("bash", CMD_PSQL)}
Ou, com Docker:

{bloco("bash", CMD_PSQL_DOCKER)}
#### 7. Executar o pipeline na ordem

{bloco("bash", CMD_PIPELINE)}
No notebook, execute `Restart Kernel and Run All Cells` para garantir a ordem sequencial.

#### 8. Rodar os testes

{bloco("bash", CMD_TESTES)}
**Saída esperada:**

{bloco("text", SAIDA_TESTES)}
### Ordem completa de execução

{bloco("text", ORDEM_EXECUCAO)}
### Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| `command not found: python3` | Python não instalado ou fora do PATH | Instale Python 3.10+ |
| `psycopg2.OperationalError` | Banco não está rodando ou credenciais erradas | Verifique o `.env` e se o container está ativo |
| `BancoError: Não foi possível conectar` | `.env` ausente ou senha incorreta | Rode `cp .env.example .env` e preencha |
| `ModuleNotFoundError: banco` | Executando de fora da raiz do projeto | Rode os scripts a partir da raiz |
| `54 passed` mas notebook sem gráficos | Notebook não foi executado | Rode `Restart Kernel and Run All Cells` |
| Download do ZIP falha | Google Drive exige autenticação | Baixe manualmente para `data/raw/` |
| `execution of scripts is disabled` | Política do PowerShell bloqueia `.ps1` | Rode `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |

---
"""

CMD_TESTES_UTEIS = """# Rodar tudo com detalhes
python -m pytest tests/ -v

# Rodar só uma camada
python -m pytest tests/ -v -k "TestSilver"

# Rodar só uma pergunta
python -m pytest tests/ -v -k "test_p1"

# Parar no primeiro erro
python -m pytest tests/ -x

# Ver tempo de cada teste
python -m pytest tests/ --durations=10"""

TESTES = f"""
## Testes

O projeto tem **54 testes end-to-end** organizados em 6 classes, simulando a execução do avaliador.

| Classe | Testes | O que valida |
|---|---|---|
| `TestAmbiente` | 5 | Python 3.10+, dependências, `.env`, conexão, banco populado |
| `TestRaw` | 9 | Contagens das 4 tabelas, total e número de colunas |
| `TestSilver` | 16 | Tipagem, constraints, dedup, integridade referencial |
| `TestGold` | 6 | Existência das 3 VIEWs e consistência com a Silver |
| `TestPerguntasNegocio` | 11 | Respostas exatas das 7 perguntas |
| `TestNotebook` | 7 | Execução sequencial, 4 gráficos, ausência de erros |

### Comandos úteis

{bloco("bash", CMD_TESTES_UTEIS)}
### Validações manuais executadas

Além dos testes automatizados, cinco validações SQL foram executadas diretamente no banco:

| # | Validação | Resultado |
|---|---|---|
| V1 | Totais consolidados | 341.860 viagens, `R$ 1.200.760.089,85`, média `R$ 3.512,43` |
| V2 | Soma das partes | diferença `0,00` |
| V3 | Top órgão | Ministério da Justiça com `R$ 490,8 mi` (41%) |
| V4 | Razão pagamentos/viagens | `0,84` |
| V5 | Destinos preenchidos | 341.860 de 341.860, zero vazios |

---
"""

LIMITACOES = """
## Limitações Conhecidas

### 1. Link do Drive pode exigir autenticação

O download do ZIP depende do `DRIVE_FILE_ID` configurado em `config.py`. Em máquina limpa, o Google Drive pode exigir autenticação e falhar. Mitigado com `try/except` e mensagem orientando download manual para `data/raw/viagens_2025_6meses.zip`.

### 2. CSVs completos excedem o limite do GitHub

Três dos quatro arquivos passam de 100 MB. A solução foi versionar amostras de 2.000 linhas em `data/amostras/`. O pipeline completo exige baixar o ZIP original.

### 3. O notebook depende do estado do banco

O `3_analise.ipynb` pressupõe que `1_extrair.py` e `2_transformar.py` já rodaram. Executar o notebook em banco vazio gera erro. A ordem de execução está documentada acima e o teste `test_banco_populado` falha com mensagem clara se o banco estiver vazio.

### 4. Risco de inflação ao cruzar grãos diferentes

Cruzar tabelas de grão diferente sem agregar antes infla somas e médias. A Gold resolve isso com VIEWs separadas por grão. A validação `test_gold_orgao_soma_bate` garante que a soma da VIEW é idêntica à da Silver.

### 5. Pico de memória na carga

`executemany` com blocos de 50.000 linhas em arquivo de 194 MB eleva o pico de memória. Se necessário, reduza `TAMANHO_BLOCO` em `config.py` para 10.000 ou 20.000.

### 6. Viagens de 364 dias

Viagens com data de início `01/01` e fim `31/12` correspondem a servidores em exercício fora da sede ou viagens continuadas, não a deslocamentos únicos. O `valor_total` acumulado reflete o período completo. Isso afeta a pergunta 3 (viagens mais caras).

### 7. Trechos com meio de transporte "Inválido"

26.659 trechos (3,49%) têm `meio_transporte = "Inválido"`. O valor vem da fonte e foi preservado pela Silver, não descartado. Não é erro do pipeline.

### 8. Viagens sem trecho registrado

51.601 viagens (15,1%) não têm trecho registrado. A média de 2,63 trechos considera apenas as 290.259 viagens com trecho. Dividir por 341.860 daria 2,23, mas esse cálculo estaria errado.

---
"""

DECISOES = """
## Decisões Técnicas

### Por que PostgreSQL e não SQLite

O volume de 1,8 milhão de linhas na Raw e a necessidade de constraints explícitas (PK, FK, CHECK, UNIQUE) tornam o PostgreSQL a escolha natural. SQLite não tem `GENERATED ALWAYS AS IDENTITY` nem o mesmo rigor de tipos.

### Por que psycopg2 e não SQLAlchemy

O projeto é um pipeline ETL, não uma aplicação web. SQL puro com `psycopg2` é mais direto, mais rápido e mais fácil de auditar. SQLAlchemy adicionaria uma camada de abstração sem benefício neste contexto.

### Por que cursor server-side na transformação

O `2_transformar.py` usa `conexao.cursor(name=...)` para leitura em blocos. Isso faz o PostgreSQL enviar as linhas sob demanda, mantendo o uso de memória constante independente do volume da tabela. Sem isso, carregar 763.349 linhas de `raw_trecho` na memória consumiria mais de 1 GB.

### Por que duas conexões na transformação

Uma conexão dedicada ao cursor server-side (leitura) e outra dedicada às inserções (escrita). Isso evita conflito de transação: o cursor nomeado mantém uma transação aberta durante toda a leitura, e a escrita precisa de commits independentes.

### Por que VIEWs e não tabelas materializadas

As VIEWs Gold são calculadas sob demanda. Como o dataset é estático (6 meses de 2025), o custo de recálculo é baixo e a VIEW garante que os dados estejam sempre sincronizados com a Silver. Tabelas materializadas exigiriam `REFRESH` manual.

### Por que pytest e não unittest

O enunciado pede "funções pequenas e puras". pytest favorece exatamente isso: cada teste é uma função pura com `assert`, sem classe obrigatória. As fixtures nativas e as mensagens de erro detalhadas tornam o código mais legível.

### Por que formatação pt-BR no notebook

O `display.float_format` do pandas e o `FuncFormatter` do matplotlib foram configurados para exibir valores em pt-BR (`R$ 1.200.760.089,85` em vez de `1.200760e+09`). Isso evita notação científica e alinha a apresentação ao padrão brasileiro.

### Por que scripts de setup em duas linguagens

`setup.sh` cobre Linux, macOS e Git Bash. `setup.ps1` cobre Windows PowerShell nativo. Manter os dois garante que qualquer avaliador consiga executar o projeto no seu sistema, sem depender de WSL ou de tradução manual de comandos.

---
"""

RODAPE = """
## Autor

**Filippe Borba**
Engenheiro e Consultor de Transformação Logística
Turma Análise de Dados T6 — SENAI

---

## Licença

Projeto acadêmico desenvolvido para o Projeto Avaliativo do Módulo 1 do curso de Análise de Dados do SENAI.
"""

SECOES = [
    CABECALHO,
    ARQUITETURA,
    BASE_DADOS,
    DICIONARIO,
    REFLEXAO,
    INSIGHTS,
    COMO_EXECUTAR,
    TESTES,
    LIMITACOES,
    DECISOES,
    RODAPE,
]


def gerar_readme(destino: Path = ARQUIVO_README) -> Path:
    """
    Monta o README.md a partir das secoes definidas no modulo.

    Args:
        destino: caminho do arquivo a ser escrito.

    Returns:
        O caminho do arquivo gerado.

    Raises:
        OSError: se nao for possivel escrever o arquivo.
    """
    conteudo = "".join(SECOES)
    destino.write_text(conteudo, encoding="utf-8")
    return destino


def main() -> None:
    """Executa a geracao e reporta o resultado."""
    caminho = gerar_readme()
    texto = caminho.read_text(encoding="utf-8")
    linhas = texto.count("\n") + 1
    secoes = texto.count("\n## ")
    print(f"README gerado: {caminho}")
    print(f"Linhas: {linhas}")
    print(f"Secoes de nivel 2: {secoes}")
    print(f"Caracteres: {len(texto)}")


if __name__ == "__main__":
    main()