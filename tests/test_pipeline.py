# -*- coding: utf-8 -*-
"""
Testes end-to-end do pipeline de dados (Projeto Avaliativo Modulo 1).

Simula a execucao do avaliador: valida ambiente, camada Raw, camada Silver,
camada Gold, respostas das 7 perguntas de negocio e integridade do notebook.

Pre-requisito: executar 0_criar_banco.sql, 1_extrair.py e 2_transformar.py
antes de rodar os testes.

Uso:
    python -m pytest tests/ -v
"""
import json
import sys
from pathlib import Path

import pytest

from banco import conectar, consultar, contar_linhas
from config import PASTA_RAIZ

# --------------------------------------------------------------------------- #
# Constantes esperadas (valores reais do pipeline executado)
# --------------------------------------------------------------------------- #
RAW_VIAGEM = 341_860
RAW_PAGAMENTO = 606_916
RAW_PASSAGEM = 167_260
RAW_TRECHO = 763_349
RAW_TOTAL = 1_879_385

SILVER_VIAGEM = 341_860
SILVER_PAGAMENTO = 568_403
SILVER_PASSAGEM = 100_075
SILVER_TRECHO = 763_349

GASTO_TOTAL = 1_200_760_089.85
MEDIA_VIAGEM = 3_512.43
VALOR_MAXIMO = 261_287.40

ORGAO_LIDER = "Ministério da Justiça e Segurança Pública"
ORGAO_LIDER_VALOR = 490_813_474.85
QTD_ORGAOS = 35

DESTINO_MAIS_CARO = "Jacareacanga/PA"
TIPO_PAGAMENTO_LIDER = "DIÁRIAS"
MEIO_TRANSPORTE_LIDER = "Veículo Oficial"
MEIO_TRANSPORTE_LIDER_QTD = 386_424
MEDIA_TRECHOS = 2.63
RECORDE_TRECHOS = 68
MESES_DISTINTOS = 6


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def conexao():
    """Abre uma conexao unica para toda a sessao de testes."""
    conn = conectar()
    yield conn
    conn.close()


# --------------------------------------------------------------------------- #
# Camada 0 - Ambiente
# --------------------------------------------------------------------------- #
class TestAmbiente:
    """Valida os pre-requisitos do ambiente antes de testar os dados."""

    def test_python_versao(self):
        """Python deve ser 3.10 ou superior."""
        assert sys.version_info >= (3, 10), (
            f"Python 3.10+ requerido, encontrado {sys.version_info.major}."
            f"{sys.version_info.minor}"
        )

    def test_dependencias_instaladas(self):
        """psycopg2, pandas, matplotlib e seaborn devem importar."""
        import matplotlib  # noqa: F401
        import pandas  # noqa: F401
        import psycopg2  # noqa: F401
        import seaborn  # noqa: F401

    def test_env_existe(self):
        """O arquivo .env deve existir na raiz do projeto."""
        assert (PASTA_RAIZ / ".env").exists(), (
            "Arquivo .env ausente. Copie .env.example e preencha as credenciais."
        )

    def test_conexao_banco(self, conexao):
        """A conexao com o PostgreSQL deve estar aberta."""
        assert conexao.closed == 0, "Conexao com o banco esta fechada."

    def test_banco_populado(self, conexao):
        """silver_viagem deve ter dados (pipeline executado)."""
        total = contar_linhas(conexao, "silver_viagem")
        assert total > 0, (
            "silver_viagem esta vazia. Execute 1_extrair.py e 2_transformar.py "
            "antes de rodar os testes."
        )


# --------------------------------------------------------------------------- #
# Camada 1 - Raw
# --------------------------------------------------------------------------- #
class TestRaw:
    """Valida a camada Raw carregada pelo 1_extrair.py."""

    def test_contagem_raw_viagem(self, conexao):
        """raw_viagem deve ter 341.860 linhas."""
        assert contar_linhas(conexao, "raw_viagem") == RAW_VIAGEM

    def test_contagem_raw_pagamento(self, conexao):
        """raw_pagamento deve ter 606.916 linhas."""
        assert contar_linhas(conexao, "raw_pagamento") == RAW_PAGAMENTO

    def test_contagem_raw_passagem(self, conexao):
        """raw_passagem deve ter 167.260 linhas."""
        assert contar_linhas(conexao, "raw_passagem") == RAW_PASSAGEM

    def test_contagem_raw_trecho(self, conexao):
        """raw_trecho deve ter 763.349 linhas."""
        assert contar_linhas(conexao, "raw_trecho") == RAW_TRECHO

    def test_total_raw(self, conexao):
        """A soma das 4 tabelas Raw deve ser 1.879.385."""
        total = sum(
            contar_linhas(conexao, tabela)
            for tabela in ("raw_viagem", "raw_pagamento", "raw_passagem", "raw_trecho")
        )
        assert total == RAW_TOTAL

    def test_colunas_raw_viagem(self, conexao):
        """raw_viagem deve ter exatamente 22 colunas."""
        colunas = consultar(
            conexao,
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'raw_viagem'
            """,
        )
        assert len(colunas) == 22

    def test_colunas_raw_pagamento(self, conexao):
        """raw_pagamento deve ter exatamente 10 colunas."""
        colunas = consultar(
            conexao,
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'raw_pagamento'
            """,
        )
        assert len(colunas) == 10

    def test_colunas_raw_passagem(self, conexao):
        """raw_passagem deve ter exatamente 19 colunas."""
        colunas = consultar(
            conexao,
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'raw_passagem'
            """,
        )
        assert len(colunas) == 19

    def test_colunas_raw_trecho(self, conexao):
        """raw_trecho deve ter exatamente 14 colunas."""
        colunas = consultar(
            conexao,
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'raw_trecho'
            """,
        )
        assert len(colunas) == 14


# --------------------------------------------------------------------------- #
# Camada 2 - Silver
# --------------------------------------------------------------------------- #
class TestSilver:
    """Valida a camada Silver produzida pelo 2_transformar.py."""

    def test_contagem_silver_viagem(self, conexao):
        """silver_viagem deve ter 341.860 linhas."""
        assert contar_linhas(conexao, "silver_viagem") == SILVER_VIAGEM

    def test_contagem_silver_pagamento(self, conexao):
        """silver_pagamento deve ter 568.403 linhas."""
        assert contar_linhas(conexao, "silver_pagamento") == SILVER_PAGAMENTO

    def test_contagem_silver_passagem(self, conexao):
        """silver_passagem deve ter 100.075 linhas."""
        assert contar_linhas(conexao, "silver_passagem") == SILVER_PASSAGEM

    def test_contagem_silver_trecho(self, conexao):
        """silver_trecho deve ter 763.349 linhas."""
        assert contar_linhas(conexao, "silver_trecho") == SILVER_TRECHO

    def test_soma_partes_igual_total(self, conexao):
        """valor_total deve ser a soma exata das 4 parcelas."""
        resultado = consultar(
            conexao,
            """
            SELECT COUNT(*) FROM silver_viagem
            WHERE valor_total <> valor_diarias + valor_passagens
                               + valor_devolucao + valor_outros_gastos
            """,
        )
        assert resultado[0][0] == 0, (
            f"{resultado[0][0]} viagens com valor_total inconsistente."
        )

    def test_sem_valores_negativos(self, conexao):
        """Nenhuma coluna monetaria pode ser negativa."""
        resultado = consultar(
            conexao,
            """
            SELECT COUNT(*) FROM silver_viagem
            WHERE valor_diarias < 0 OR valor_passagens < 0
               OR valor_devolucao < 0 OR valor_outros_gastos < 0
            """,
        )
        assert resultado[0][0] == 0

    def test_sem_datas_nulas(self, conexao):
        """data_inicio e data_fim nao podem ser nulas."""
        resultado = consultar(
            conexao,
            """
            SELECT COUNT(*) FROM silver_viagem
            WHERE data_inicio IS NULL OR data_fim IS NULL
            """,
        )
        assert resultado[0][0] == 0

    def test_duracao_nao_negativa(self, conexao):
        """duracao_dias nao pode ser negativa."""
        resultado = consultar(
            conexao,
            "SELECT COUNT(*) FROM silver_viagem WHERE duracao_dias < 0",
        )
        assert resultado[0][0] == 0

    def test_orgao_superior_nao_nulo(self, conexao):
        """nome_orgao_superior tem constraint NOT NULL."""
        resultado = consultar(
            conexao,
            """
            SELECT COUNT(*) FROM silver_viagem
            WHERE nome_orgao_superior IS NULL OR nome_orgao_superior = ''
            """,
        )
        assert resultado[0][0] == 0

    def test_sem_duplicata_viagem(self, conexao):
        """id_viagem deve ser unico em silver_viagem (PK)."""
        resultado = consultar(
            conexao,
            """
            SELECT COUNT(*) FROM (
                SELECT id_viagem FROM silver_viagem
                GROUP BY id_viagem HAVING COUNT(*) > 1
            ) AS dup
            """,
        )
        assert resultado[0][0] == 0

    def test_sem_duplicata_trecho(self, conexao):
        """UNIQUE (id_viagem, sequencia_trecho) deve ser respeitada."""
        resultado = consultar(
            conexao,
            """
            SELECT COUNT(*) FROM (
                SELECT id_viagem, sequencia_trecho FROM silver_trecho
                GROUP BY id_viagem, sequencia_trecho HAVING COUNT(*) > 1
            ) AS dup
            """,
        )
        assert resultado[0][0] == 0

    def test_fk_passagem_valida(self, conexao):
        """Toda passagem deve apontar para uma viagem existente."""
        resultado = consultar(
            conexao,
            """
            SELECT COUNT(*) FROM silver_passagem p
            LEFT JOIN silver_viagem v ON p.id_viagem = v.id_viagem
            WHERE v.id_viagem IS NULL
            """,
        )
        assert resultado[0][0] == 0

    def test_fk_pagamento_valida(self, conexao):
        """Todo pagamento deve apontar para uma viagem existente."""
        resultado = consultar(
            conexao,
            """
            SELECT COUNT(*) FROM silver_pagamento p
            LEFT JOIN silver_viagem v ON p.id_viagem = v.id_viagem
            WHERE v.id_viagem IS NULL
            """,
        )
        assert resultado[0][0] == 0

    def test_fk_trecho_valida(self, conexao):
        """Todo trecho deve apontar para uma viagem existente."""
        resultado = consultar(
            conexao,
            """
            SELECT COUNT(*) FROM silver_trecho t
            LEFT JOIN silver_viagem v ON t.id_viagem = v.id_viagem
            WHERE v.id_viagem IS NULL
            """,
        )
        assert resultado[0][0] == 0

    def test_tipo_pagamento_nao_nulo(self, conexao):
        """tipo_pagamento tem constraint NOT NULL."""
        resultado = consultar(
            conexao,
            """
            SELECT COUNT(*) FROM silver_pagamento
            WHERE tipo_pagamento IS NULL OR tipo_pagamento = ''
            """,
        )
        assert resultado[0][0] == 0

    def test_valor_pagamento_nao_negativo(self, conexao):
        """valor em silver_pagamento tem CHECK >= 0."""
        resultado = consultar(
            conexao,
            "SELECT COUNT(*) FROM silver_pagamento WHERE valor < 0",
        )
        assert resultado[0][0] == 0


# --------------------------------------------------------------------------- #
# Camada 3 - Gold
# --------------------------------------------------------------------------- #
class TestGold:
    """Valida as VIEWs Gold criadas pelo 3_analise.ipynb."""

    def test_views_existem(self, conexao):
        """As 3 VIEWs Gold devem existir no schema public."""
        resultado = consultar(
            conexao,
            """
            SELECT table_name FROM information_schema.views
            WHERE table_schema = 'public'
              AND table_name IN (
                  'gold_gastos_por_orgao',
                  'gold_pagamentos_por_orgao',
                  'gold_gastos_por_destino'
              )
            """,
        )
        assert len(resultado) == 3, (
            f"Esperadas 3 VIEWs, encontradas {len(resultado)}."
        )

    def test_gold_orgao_35_linhas(self, conexao):
        """gold_gastos_por_orgao deve ter 35 orgaos."""
        assert contar_linhas(conexao, "gold_gastos_por_orgao") == QTD_ORGAOS

    def test_gold_orgao_soma_bate(self, conexao):
        """A soma da VIEW por orgao deve igualar a soma da Silver."""
        gold = consultar(
            conexao, "SELECT SUM(valor_total_gasto) FROM gold_gastos_por_orgao"
        )
        silver = consultar(conexao, "SELECT SUM(valor_total) FROM silver_viagem")
        assert gold[0][0] == silver[0][0], (
            f"Gold={gold[0][0]} difere de Silver={silver[0][0]}."
        )

    def test_gold_orgao_contagem_bate(self, conexao):
        """A contagem da VIEW por orgao deve igualar a Silver."""
        gold = consultar(
            conexao, "SELECT SUM(qtd_viagens) FROM gold_gastos_por_orgao"
        )
        silver = consultar(conexao, "SELECT COUNT(*) FROM silver_viagem")
        assert gold[0][0] == silver[0][0]

    def test_gold_destino_soma_bate(self, conexao):
        """A soma da VIEW por destino deve igualar a Silver."""
        gold = consultar(
            conexao, "SELECT SUM(valor_total_gasto) FROM gold_gastos_por_destino"
        )
        silver = consultar(conexao, "SELECT SUM(valor_total) FROM silver_viagem")
        assert gold[0][0] == silver[0][0]

    def test_gold_pagamento_soma_bate(self, conexao):
        """A soma da VIEW de pagamentos deve igualar a Silver."""
        gold = consultar(
            conexao, "SELECT SUM(valor_total_pago) FROM gold_pagamentos_por_orgao"
        )
        silver = consultar(conexao, "SELECT SUM(valor) FROM silver_pagamento")
        assert gold[0][0] == silver[0][0]


# --------------------------------------------------------------------------- #
# Camada 4 - Perguntas de negocio
# --------------------------------------------------------------------------- #
class TestPerguntasNegocio:
    """Valida as respostas das 7 perguntas de negocio."""

    def test_p1_maior_orgao(self, conexao):
        """P1: Ministerio da Justica lidera com R$ 490.813.474,85."""
        resultado = consultar(
            conexao,
            """
            SELECT nome_orgao_superior, valor_total_gasto
            FROM gold_gastos_por_orgao
            ORDER BY valor_total_gasto DESC
            LIMIT 1
            """,
        )
        assert resultado[0][0] == ORGAO_LIDER
        assert float(resultado[0][1]) == ORGAO_LIDER_VALOR

    def test_p2_destino_mais_caro(self, conexao):
        """P2: Jacareacanga/PA tem o maior valor medio (50+ viagens)."""
        resultado = consultar(
            conexao,
            """
            SELECT destino_principal FROM gold_gastos_por_destino
            WHERE qtd_viagens >= 50
            ORDER BY valor_medio_viagem DESC
            LIMIT 1
            """,
        )
        assert resultado[0][0] == DESTINO_MAIS_CARO

    def test_p3_viagem_mais_cara(self, conexao):
        """P3: a viagem mais cara custou R$ 261.287,40."""
        resultado = consultar(
            conexao,
            """
            SELECT valor_total FROM silver_viagem
            ORDER BY valor_total DESC
            LIMIT 1
            """,
        )
        assert float(resultado[0][0]) == VALOR_MAXIMO

    def test_p4_tipo_pagamento(self, conexao):
        """P4: DIARIAS concentra o maior valor total pago."""
        resultado = consultar(
            conexao,
            """
            SELECT tipo_pagamento FROM silver_pagamento
            GROUP BY tipo_pagamento
            ORDER BY SUM(valor) DESC
            LIMIT 1
            """,
        )
        assert resultado[0][0] == TIPO_PAGAMENTO_LIDER

    def test_p5_meio_transporte(self, conexao):
        """P5: Veiculo Oficial lidera com 386.424 trechos."""
        resultado = consultar(
            conexao,
            """
            SELECT meio_transporte, COUNT(*) FROM silver_trecho
            GROUP BY meio_transporte
            ORDER BY COUNT(*) DESC
            LIMIT 1
            """,
        )
        assert resultado[0][0] == MEIO_TRANSPORTE_LIDER
        assert resultado[0][1] == MEIO_TRANSPORTE_LIDER_QTD

    def test_p5_percentual_soma_100(self, conexao):
        """P5: os percentuais por meio de transporte somam ~100%."""
        resultado = consultar(
            conexao,
            """
            SELECT ROUND(
                100.0 * SUM(cnt) / (SELECT COUNT(*) FROM silver_trecho), 2
            )
            FROM (
                SELECT COUNT(*) AS cnt FROM silver_trecho
                GROUP BY meio_transporte
            ) AS t
            """,
        )
        assert float(resultado[0][0]) == 100.00

    def test_p6_media_trechos(self, conexao):
        """P6: media de 2,63 trechos por viagem."""
        resultado = consultar(
            conexao,
            """
            WITH t AS (
                SELECT id_viagem, COUNT(*) AS q
                FROM silver_trecho GROUP BY id_viagem
            )
            SELECT ROUND(AVG(q), 2) FROM t
            """,
        )
        assert float(resultado[0][0]) == MEDIA_TRECHOS

    def test_p6_recorde_trechos(self, conexao):
        """P6: recorde de 68 trechos em uma viagem."""
        resultado = consultar(
            conexao,
            """
            WITH t AS (
                SELECT id_viagem, COUNT(*) AS q
                FROM silver_trecho GROUP BY id_viagem
            )
            SELECT MAX(q) FROM t
            """,
        )
        assert resultado[0][0] == RECORDE_TRECHOS

    def test_p7_meses_presentes(self, conexao):
        """P7: devem existir 6 meses distintos em 2025."""
        resultado = consultar(
            conexao,
            """
            SELECT COUNT(DISTINCT DATE_TRUNC('month', data_inicio))
            FROM silver_viagem
            """,
        )
        assert resultado[0][0] == MESES_DISTINTOS

    def test_gasto_total_consolidado(self, conexao):
        """O gasto total consolidado deve ser R$ 1.200.760.089,85."""
        resultado = consultar(conexao, "SELECT SUM(valor_total) FROM silver_viagem")
        assert float(resultado[0][0]) == GASTO_TOTAL

    def test_media_viagem(self, conexao):
        """A media por viagem deve ser R$ 3.512,43."""
        resultado = consultar(
            conexao, "SELECT ROUND(AVG(valor_total), 2) FROM silver_viagem"
        )
        assert float(resultado[0][0]) == MEDIA_VIAGEM


# --------------------------------------------------------------------------- #
# Camada 5 - Notebook
# --------------------------------------------------------------------------- #
class TestNotebook:
    """Valida a integridade do 3_analise.ipynb."""

    @pytest.fixture(scope="class")
    @classmethod
    def notebook(cls):
        caminho = PASTA_RAIZ / "3_analise.ipynb"
        assert caminho.exists(), "3_analise.ipynb nao encontrado."
        return json.loads(caminho.read_text(encoding="utf-8"))

    def test_notebook_json_valido(self, notebook):
        """O notebook deve ser JSON valido no formato nbformat 4."""
        assert notebook["nbformat"] == 4

    def test_notebook_tem_celulas(self, notebook):
        """O notebook deve ter pelo menos 20 celulas."""
        assert len(notebook["cells"]) >= 20

    def test_notebook_todas_executadas(self, notebook):
        """Todas as celulas de codigo devem ter execution_count."""
        codigo = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        sem_execucao = [c for c in codigo if c.get("execution_count") is None]
        assert len(sem_execucao) == 0, (
            f"{len(sem_execucao)} celulas sem execucao. "
            "Rode Restart Kernel and Run All Cells e salve."
        )

    def test_notebook_execucao_sequencial(self, notebook):
        """Os execution_count devem ser crescentes de 1 a N."""
        codigo = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        contadores = [c["execution_count"] for c in codigo]
        assert contadores == list(range(1, len(contadores) + 1)), (
            f"Execucao fora de ordem: {contadores}"
        )

    def test_notebook_tem_graficos(self, notebook):
        """Deve haver pelo menos 4 graficos embutidos."""
        graficos = sum(
            1
            for celula in notebook["cells"]
            if celula["cell_type"] == "code"
            for saida in celula.get("outputs", [])
            if "image/png" in saida.get("data", {})
        )
        assert graficos >= 4, f"Esperados 4 graficos, encontrados {graficos}."

    def test_notebook_sem_erros(self, notebook):
        """Nenhuma celula pode ter output de erro."""
        erros = [
            saida
            for celula in notebook["cells"]
            if celula["cell_type"] == "code"
            for saida in celula.get("outputs", [])
            if saida.get("output_type") == "error"
        ]
        assert len(erros) == 0, f"{len(erros)} celulas com erro no output."

    def test_notebook_usa_banco(self, notebook):
        """O notebook deve importar de banco.py, sem conexao propria."""
        fontes = "".join(
            "".join(c["source"])
            for c in notebook["cells"]
            if c["cell_type"] == "code"
        )
        assert "from banco import" in fontes
        assert "psycopg2.connect" not in fontes, (
            "O notebook nao deve criar conexao propria."
        )