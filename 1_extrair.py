"""
Pipeline de extracao da camada Raw.
 
Baixa o arquivo ZIP com os CSVs de viagens a servico, extrai os arquivos,
gera amostras e carrega tudo no PostgreSQL em blocos de 50 mil linhas.
 
Uso:
    python 1_extrair.py
"""
 
import csv
import logging
import sys
import time
import zipfile
from pathlib import Path
from typing import Iterator

import psycopg2
from psycopg2.extras import execute_values

from banco import conectar
from config import (
    CSV_ENCODING,
    CSV_SEPARADOR,
    DRIVE_FILE_ID,
    PASTA_DADOS,
    PASTA_RAIZ,
    TAMANHO_BLOCO,
)

# Logger do modulo. configurar_log() ajusta handlers e nivel.
logger = logging.getLogger(__name__)

TAMANHO_AMOSTRA = 2_000

# Aliases locais para legibilidade no corpo do script.
ENCODING_CSV = CSV_ENCODING
DELIMITADOR_CSV = CSV_SEPARADOR

# Pastas derivadas de PASTA_DADOS / PASTA_RAIZ (nao existem no config.py).
PASTA_RAW = PASTA_DADOS / "raw"
PASTA_AMOSTRAS = PASTA_DADOS / "amostras"
PASTA_LOGS = PASTA_RAIZ / "logs"

# URL montada a partir do DRIVE_FILE_ID real do config.py.
URL_ZIP = f"https://drive.google.com/uc?id={DRIVE_FILE_ID}"
ARQUIVO_ZIP = PASTA_RAW / "viagens_2025_6meses.zip"
 
# As listas abaixo seguem a ORDEM EXATA dos cabecalhos dos CSVs.
# Qualquer divergencia de tamanho e detectada por validar_cabecalho(),
# que aborta ANTES do TRUNCATE para nao apagar dados sem necessidade.
TABELAS = {
    "2025_Viagem.csv": (
        "raw_viagem",
        [
            "id_viagem",
            "num_proposta",
            "situacao",
            "viagem_urgente",
            "justificativa_urgencia",
            "cod_orgao_superior",
            "nome_orgao_superior",
            "cod_orgao_solicitante",
            "nome_orgao_solicitante",
            "cpf_viajante",
            "nome_viajante",
            "cargo",
            "funcao",
            "descricao_funcao",
            "data_inicio",
            "data_fim",
            "destinos",
            "motivo",
            "valor_diarias",
            "valor_passagens",
            "valor_devolucao",
            "valor_outros_gastos",
        ],
    ),
    "2025_Pagamento.csv": (
        "raw_pagamento",
        [
            "id_viagem",
            "num_proposta",
            "cod_orgao_superior",
            "nome_orgao_superior",
            "cod_orgao_pagador",
            "nome_orgao_pagador",
            "cod_ug_pagadora",
            "nome_ug_pagadora",
            "tipo_pagamento",
            "valor",
        ],
    ),
    "2025_Passagem.csv": (
        "raw_passagem",
        [
            "id_viagem",
            "num_proposta",
            "meio_transporte",
            "pais_origem_ida",
            "uf_origem_ida",
            "cidade_origem_ida",
            "pais_destino_ida",
            "uf_destino_ida",
            "cidade_destino_ida",
            "pais_origem_volta",
            "uf_origem_volta",
            "cidade_origem_volta",
            "pais_destino_volta",
            "uf_destino_volta",
            "cidade_destino_volta",
            "valor_passagem",
            "taxa_servico",
            "data_emissao",
            "hora_emissao",
        ],
    ),
    "2025_Trecho.csv": (
        "raw_trecho",
        [
            "id_viagem",
            "num_proposta",
            "sequencia_trecho",
            "origem_data",
            "origem_pais",
            "origem_uf",
            "origem_cidade",
            "destino_data",
            "destino_pais",
            "destino_uf",
            "destino_cidade",
            "meio_transporte",
            "numero_diarias",
            "missao",
        ],
    ),
}
 
 
def configurar_log() -> None:
    """Configura o logger para arquivo e console."""
    PASTA_LOGS.mkdir(parents=True, exist_ok=True)
    formato = "%(asctime)s %(levelname)s %(message)s"
 
    logging.basicConfig(
        level=logging.INFO,
        format=formato,
        handlers=[
            logging.FileHandler(PASTA_LOGS / "extracao.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
 
 
def contar_linhas(caminho: Path) -> int:
    """
    Conta as linhas de dados do CSV, descontando o cabecalho.
 
    Args:
        caminho: Caminho do arquivo CSV.
 
    Returns:
        Numero de linhas de dados.
    """
    with open(caminho, "r", encoding=ENCODING_CSV, errors="replace") as arquivo:
        total = sum(1 for _ in arquivo)
    return max(total - 1, 0)
 
 
def formatar_duracao(segundos: float) -> str:
    """
    Formata segundos em mm:ss ou hh:mm:ss.
 
    Args:
        segundos: Duracao em segundos.
 
    Returns:
        String formatada.
    """
    segundos = int(segundos)
    horas, resto = divmod(segundos, 3600)
    minutos, seg = divmod(resto, 60)
    if horas:
        return f"{horas}h{minutos:02d}m{seg:02d}s"
    return f"{minutos}m{seg:02d}s"
 
 
def barra_progresso(percentual: float, largura: int = 30) -> str:
    """
    Gera uma barra de progresso textual.
 
    Args:
        percentual: Valor de 0 a 100.
        largura: Numero de caracteres da barra.
 
    Returns:
        String com a barra preenchida.
    """
    preenchido = int(largura * percentual / 100)
    return "#" * preenchido + "." * (largura - preenchido)
 
 
def validar_cabecalho(caminho: Path, colunas: list[str]) -> None:
    """
    Valida que o cabecalho do CSV tem exatamente o numero de colunas esperado.
 
    Protege contra desalinhamento silencioso: se o CSV tiver mais colunas
    do que a lista, os valores seriam deslocados e o dado corrompido.
    Roda ANTES do TRUNCATE, para nao apagar dados sem necessidade.
 
    Args:
        caminho: Caminho do arquivo CSV.
        colunas: Lista de colunas esperadas.
 
    Raises:
        ValueError: Se a contagem de colunas do cabecalho divergir.
    """
    with open(
        caminho, "r", encoding=ENCODING_CSV, errors="replace", newline=""
    ) as arquivo:
        leitor = csv.reader(arquivo, delimiter=DELIMITADOR_CSV)
        cabecalho = next(leitor, [])
 
    if len(cabecalho) != len(colunas):
        raise ValueError(
            f"{caminho.name}: cabecalho tem {len(cabecalho)} colunas, "
            f"mas a lista espera {len(colunas)}. "
            f"Ajuste TABELAS antes de carregar."
        )
 
 
def baixar_zip() -> None:
    """
    Baixa o arquivo ZIP se ainda nao existir.

    Reaproveita o arquivo local quando presente, evitando download
    redundante em reexecucoes do pipeline.

    Raises:
        RuntimeError: Se o download falhar ou nao gerar o arquivo esperado.
    """
    PASTA_RAW.mkdir(parents=True, exist_ok=True)

    if ARQUIVO_ZIP.exists():
        logger.info("Reaproveitando zip ja existente: %s", ARQUIVO_ZIP)
        return

    logger.info("Baixando arquivo de %s", URL_ZIP)
    try:
        import gdown

        gdown.download(URL_ZIP, str(ARQUIVO_ZIP), quiet=False)
    except Exception as erro:
        raise RuntimeError(
            f"Falha ao baixar o arquivo de {URL_ZIP}: {erro}. "
            f"Verifique a conexao ou baixe manualmente para {ARQUIVO_ZIP}."
        ) from erro

    if not ARQUIVO_ZIP.exists():
        raise RuntimeError(
            f"Download nao gerou o arquivo esperado: {ARQUIVO_ZIP}"
        )
 
 
def extrair_csvs() -> None:
    """Extrai os CSVs do ZIP para a pasta raw."""
    with zipfile.ZipFile(ARQUIVO_ZIP) as pacote:
        for nome in pacote.namelist():
            if not nome.lower().endswith(".csv"):
                continue
            destino = PASTA_RAW / Path(nome).name
            with pacote.open(nome) as origem, open(destino, "wb") as saida:
                saida.write(origem.read())
            logger.info("Extraido: %s", destino)
 
 
def gerar_amostras() -> None:
    """Gera amostras de aproximadamente TAMANHO_AMOSTRA linhas de cada CSV."""
    PASTA_AMOSTRAS.mkdir(parents=True, exist_ok=True)
    for nome_arquivo in TABELAS:
        origem = PASTA_RAW / nome_arquivo
        if not origem.exists():
            continue
        destino = PASTA_AMOSTRAS / nome_arquivo.replace(".csv", "_sample.csv")
        escritas = 0
        with open(
            origem, "r", encoding=ENCODING_CSV, errors="replace"
        ) as entrada, open(
            destino, "w", encoding=ENCODING_CSV, newline=""
        ) as saida:
            for indice, linha in enumerate(entrada):
                if indice > TAMANHO_AMOSTRA:
                    break
                saida.write(linha)
                escritas += 1
        logger.info("Amostra gerada (%d linhas): %s", escritas, destino)
 
 
def ler_em_blocos(caminho: Path, colunas: list[str]) -> Iterator[list[tuple]]:
    """
    Le o CSV em blocos de TAMANHO_BLOCO linhas.
 
    Args:
        caminho: Caminho do CSV.
        colunas: Lista de colunas esperadas.
 
    Yields:
        Lista de tuplas prontas para insercao.
    """
    with open(
        caminho, "r", encoding=ENCODING_CSV, errors="replace", newline=""
    ) as arquivo:
        leitor = csv.reader(arquivo, delimiter=DELIMITADOR_CSV)
        next(leitor, None)
 
        bloco: list[tuple] = []
        for linha in leitor:
            if len(linha) < len(colunas):
                linha = linha + [""] * (len(colunas) - len(linha))
            bloco.append(tuple(linha[: len(colunas)]))
 
            if len(bloco) >= TAMANHO_BLOCO:
                yield bloco
                bloco = []
 
        if bloco:
            yield bloco
 
 
def inserir_bloco(
    conexao,
    tabela: str,
    colunas: list[str],
    bloco: list[tuple],
) -> tuple[int, int, int]:
    """
    Insere um bloco de linhas na tabela.
 
    Args:
        conexao: Conexao ativa com o PostgreSQL.
        tabela: Nome da tabela destino.
        colunas: Lista de colunas.
        bloco: Linhas a inserir.
 
    Returns:
        Tupla (lidas, inseridas, descartadas).
    """
    sql = f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES %s"
    try:
        with conexao.cursor() as cursor:
            execute_values(cursor, sql, bloco, page_size=1000)
        conexao.commit()
        return len(bloco), len(bloco), 0
    except psycopg2.Error as erro:
        conexao.rollback()
        logger.error("%s: bloco descartado (%s)", tabela, erro)
        return len(bloco), 0, len(bloco)
 
 
def carregar_csv(
    conexao,
    caminho: Path,
    tabela: str,
    colunas: list[str],
) -> dict:
    """
    Carrega um CSV inteiro na tabela, com log de progresso por bloco.
 
    Args:
        conexao: Conexao ativa.
        caminho: Caminho do CSV.
        tabela: Nome da tabela destino.
        colunas: Lista de colunas.
 
    Returns:
        Dicionario com o resumo da carga.
    """
    logger.info("Carregando %s -> %s", caminho.name, tabela)
 
    validar_cabecalho(caminho, colunas)
 
    total_linhas = contar_linhas(caminho)
    logger.info("%s: %d linhas a carregar", tabela, total_linhas)
 
    total_lidas = 0
    total_inseridas = 0
    total_descartadas = 0
    blocos = 0
    inicio = time.time()
 
    with conexao.cursor() as cursor:
        cursor.execute(f"TRUNCATE TABLE {tabela} RESTART IDENTITY")
    conexao.commit()
 
    for bloco in ler_em_blocos(caminho, colunas):
        blocos += 1
        lidas, inseridas, descartadas = inserir_bloco(
            conexao, tabela, colunas, bloco
        )
        total_lidas += lidas
        total_inseridas += inseridas
        total_descartadas += descartadas
 
        decorrido = time.time() - inicio
        percentual = (
            min(total_lidas / total_linhas * 100, 100.0) if total_linhas else 100.0
        )
        velocidade = total_lidas / decorrido if decorrido > 0 else 0
        restante = (
            (total_linhas - total_lidas) / velocidade if velocidade > 0 else 0
        )
 
        logger.info(
            "%s [%s] %5.1f%% | bloco %d | %d/%d linhas | %s decorrido | ~%s restante",
            tabela,
            barra_progresso(percentual),
            percentual,
            blocos,
            total_lidas,
            total_linhas,
            formatar_duracao(decorrido),
            formatar_duracao(restante),
        )
 
    duracao = time.time() - inicio
    logger.info(
        "%s: lidas=%d inseridas=%d descartadas=%d blocos=%d tempo=%s",
        tabela,
        total_lidas,
        total_inseridas,
        total_descartadas,
        blocos,
        formatar_duracao(duracao),
    )
 
    return {
        "tabela": tabela,
        "lidas": total_lidas,
        "inseridas": total_inseridas,
        "descartadas": total_descartadas,
        "blocos": blocos,
        "duracao": duracao,
    }
 
 
def main() -> None:
    """Executa o pipeline completo de extracao."""
    configurar_log()
    logger.info("Inicio do pipeline de extracao")
 
    baixar_zip()
    extrair_csvs()
    gerar_amostras()
 
    conexao = conectar()
    resumos = []
 
    try:
        for nome_arquivo, (tabela, colunas) in TABELAS.items():
            caminho = PASTA_RAW / nome_arquivo
            if not caminho.exists():
                logger.warning("Arquivo ausente: %s", caminho)
                continue
            resumos.append(carregar_csv(conexao, caminho, tabela, colunas))
    finally:
        conexao.close()
 
    logger.info("=" * 70)
    logger.info("RESUMO FINAL")
    logger.info("=" * 70)
 
    total_geral = 0
    tempo_geral = 0.0
 
    for resumo in resumos:
        logger.info(
            "%-16s %9d linhas | %2d blocos | %s",
            resumo["tabela"],
            resumo["inseridas"],
            resumo["blocos"],
            formatar_duracao(resumo["duracao"]),
        )
        total_geral += resumo["inseridas"]
        tempo_geral += resumo["duracao"]
 
    logger.info("-" * 70)
    logger.info(
        "%-16s %9d linhas | %s",
        "TOTAL",
        total_geral,
        formatar_duracao(tempo_geral),
    )
    logger.info("Pipeline concluido com sucesso")
 
 
if __name__ == "__main__":
    main()
