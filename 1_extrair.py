# -*- coding: utf-8 -*-
"""Extração e carga da camada RAW do pipeline Medallion.
 
Baixa o arquivo oficial de viagens do Portal da Transparência (Drive),
extrai os CSVs, gera amostras e carrega as tabelas raw em blocos,
controlando o uso de memória.
"""
 
import argparse
import csv
import logging
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Iterator, Sequence
 
import gdown
import psycopg2
 
from config import (
    ARQUIVOS,
    CSV_ENCODING,
    CSV_SEPARADOR,
    DRIVE_FILE_ID,
    PASTA_DADOS,
    TAMANHO_BLOCO,
)
from banco import conectar, executar, inserir_em_lote
 
 
# --------------------------------------------------------------------------- #
# Exceções do domínio
# --------------------------------------------------------------------------- #
class ExtracaoError(Exception):
    """Exceção base para erros do pipeline de extração."""
 
 
class DownloadError(ExtracaoError):
    """Falha no download do arquivo zip a partir do Google Drive."""
 
 
class ExtracaoZipError(ExtracaoError):
    """Arquivo zip inválido ou sem os CSVs esperados."""
 
 
class CargaRawError(ExtracaoError):
    """Falha durante a carga das tabelas raw no PostgreSQL."""
 
 
# --------------------------------------------------------------------------- #
# Constantes
# --------------------------------------------------------------------------- #
NOME_ZIP = "viagens_2025_6meses.zip"
PASTA_RAW = PASTA_DADOS / "raw"
PASTA_AMOSTRAS = PASTA_DADOS / "amostras"
LINHAS_AMOSTRA = 2000
ORDEM_CARGA = ("viagem", "pagamento", "passagem", "trecho")
 
 
# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
def configurar_logging(nivel: str) -> None:
    """Configura o logging global do script.
 
    Args:
        nivel: nível de log (DEBUG, INFO, WARNING, ERROR).
    """
    pasta_logs = Path("logs")
    pasta_logs.mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, nivel.upper()),
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(pasta_logs / "1_extrair.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
 
 
# --------------------------------------------------------------------------- #
# Download e extração
# --------------------------------------------------------------------------- #
def baixar_zip(destino: Path, file_id: str, forcar: bool = False) -> Path:
    """Baixa o zip oficial do Google Drive (reaproveita se já existir).
 
    Args:
        destino: caminho completo do arquivo zip de destino.
        file_id: id do arquivo no Google Drive.
        forcar: se True, baixa novamente mesmo que o arquivo exista.
 
    Returns:
        Caminho do arquivo zip.
 
    Raises:
        DownloadError: quando o download falha.
    """
    if destino.exists() and not forcar:
        logging.info("Reaproveitando zip já existente: %s", destino)
        return destino
    url = f"https://drive.google.com/uc?id={file_id}"
    ok = gdown.download(url=url, output=str(destino), quiet=False)
    if not ok or not destino.exists():
        raise DownloadError(
            "Falha no download. Coloque o zip manualmente em data/raw/ "
            f"com o nome {NOME_ZIP} e execute novamente."
        )
    logging.info("Download concluído: %s", destino)
    return destino
 
 
def extrair_zip(caminho_zip: Path, destino: Path) -> dict[str, Path]:
    """Extrai apenas os membros .csv do zip, preservando o nome do arquivo.
 
    Args:
        caminho_zip: caminho do arquivo zip.
        destino: pasta de destino da extração.
 
    Returns:
        Dicionário mapeando nome do CSV para o Path extraído.
 
    Raises:
        ExtracaoZipError: se o zip for inválido ou não contiver CSVs.
    """
    destino.mkdir(parents=True, exist_ok=True)
    arquivos: dict[str, Path] = {}
    try:
        with zipfile.ZipFile(caminho_zip) as zip_ref:
            membros = [m for m in zip_ref.namelist() if m.endswith(".csv")]
            if not membros:
                raise ExtracaoZipError(f"O zip {caminho_zip} não contém CSVs.")
            for membro in membros:
                nome = Path(membro).name  # preserva só o nome do arquivo
                destino_csv = destino / nome
                with zip_ref.open(membro) as origem, destino_csv.open("wb") as saida:
                    shutil.copyfileobj(origem, saida, length=1_048_576)  # blocos de 1 MB
                arquivos[nome] = destino_csv
                logging.info("Extraído: %s", destino_csv)
    except zipfile.BadZipFile as exc:
        raise ExtracaoZipError(f"Arquivo zip inválido: {caminho_zip}") from exc
    return arquivos
 
 
def gerar_amostras(
    arquivos_csv: dict[str, Path], destino: Path, linhas: int = LINHAS_AMOSTRA
) -> dict[str, Path]:
    """Gera amostras dos CSVs preservando os bytes originais.
 
    A leitura/escrita em modo binário preserva os bytes originais, garantindo
    fidelidade ao encoding (latin-1) dos arquivos do Portal da Transparência.
 
    Args:
        arquivos_csv: dicionário nome -> Path dos CSVs completos.
        destino: pasta onde as amostras serão gravadas.
        linhas: número de linhas (incluindo cabeçalho) por amostra.
 
    Returns:
        Dicionário nome da amostra -> Path.
    """
    destino.mkdir(parents=True, exist_ok=True)
    amostras: dict[str, Path] = {}
    for nome, caminho in arquivos_csv.items():
        nome_amostra = nome.replace(".csv", "_sample.csv")
        caminho_amostra = destino / nome_amostra
        copiadas = 0
        with caminho.open("rb") as origem, caminho_amostra.open("wb") as saida:
            for _ in range(linhas):
                linha = origem.readline()
                if not linha:
                    break
                saida.write(linha)
                copiadas += 1
        amostras[nome_amostra] = caminho_amostra
        logging.info("Amostra gerada (%d linhas): %s", copiadas, caminho_amostra)
    return amostras
 
 
# --------------------------------------------------------------------------- #
# Leitura e carga em blocos
# --------------------------------------------------------------------------- #
def contar_linhas_csv(caminho: Path) -> int:
    """Conta as linhas de dados do CSV (descontando o cabeçalho).
 
    Args:
        caminho: caminho do arquivo CSV.
 
    Returns:
        Número de linhas de dados.
    """
    with caminho.open("r", encoding=CSV_ENCODING, newline="") as arquivo:
        total = sum(1 for _ in arquivo)
    return max(total - 1, 0)
 
 
def ler_em_blocos(caminho: Path, tamanho_bloco: int) -> Iterator[list[tuple[str, ...]]]:
    """Lê o CSV em blocos de tamanho fixo, como tuplas de strings.
 
    A leitura em blocos mantém o consumo de memória constante, mesmo com
    arquivos de milhões de linhas.
 
    Args:
        caminho: caminho do arquivo CSV.
        tamanho_bloco: número máximo de linhas por bloco.
 
    Yields:
        Blocos (listas) de tuplas de strings.
    """
    with caminho.open("r", encoding=CSV_ENCODING, newline="") as arquivo:
        leitor = csv.reader(arquivo, delimiter=CSV_SEPARADOR)
        cabecalho = next(leitor, None)
        if cabecalho is None:
            return
        largura = len(cabecalho)
        bloco: list[tuple[str, ...]] = []
        descartes = 0
        for linha in leitor:
            if len(linha) != largura:
                descartes += 1
                continue
            bloco.append(tuple(campo for campo in linha))
            if len(bloco) >= tamanho_bloco:
                yield bloco
                bloco = []
        if descartes:
            logging.warning(
                "%s: %d linhas descartadas por número de campos diferente do cabeçalho",
                caminho.name, descartes,
            )
        if bloco:
            yield bloco
 
 
def truncar_tabela(conexao, tabela: str) -> None:
    """Esvazia a tabela raw antes da carga (idempotência da execução).
 
    Args:
        conexao: conexão psycopg2 ativa.
        tabela: nome da tabela raw.
    """
    executar(conexao, f"TRUNCATE TABLE {tabela} RESTART IDENTITY CASCADE")
 
 
def obter_colunas_tabela(conexao, tabela: str) -> list[str]:
    """Retorna as colunas reais da tabela, via information_schema.
 
    Consultar o information_schema evita hardcode da lista de colunas:
    o INSERT se adapta automaticamente ao DDL do banco.
 
    Args:
        conexao: conexão psycopg2 ativa.
        tabela: nome da tabela.
 
    Returns:
        Lista de nomes de colunas na ordem do DDL.
    """
    with conexao.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
            """,
            (tabela,),
        )
        return [registro[0] for registro in cursor.fetchall()]
 
 
def carregar_tabela(
    conexao,
    caminho_csv: Path,
    tabela: str,
    colunas: Sequence[str],
    tamanho_bloco: int,
) -> dict[str, int]:
    """Carrega um CSV na tabela raw usando INSERT em lote.
 
    Args:
        conexao: conexão psycopg2 ativa.
        caminho_csv: caminho do CSV a carregar.
        tabela: nome da tabela raw de destino.
        colunas: colunas da tabela na ordem do INSERT.
        tamanho_bloco: tamanho de cada bloco de linhas.
 
    Returns:
        Métricas da carga (linhas_lidas, linhas_inseridas,
        linhas_descartadas, blocos_processados).
 
    Raises:
        CargaRawError: quando a carga falha (rollback garantido).
    """
    metricas = {
        "linhas_lidas": 0,
        "linhas_inseridas": 0,
        "linhas_descartadas": 0,
        "blocos_processados": 0,
    }
    placeholders = ", ".join(["%s"] * len(colunas))
    lista_colunas = ", ".join(colunas)
    sql_insert = f"INSERT INTO {tabela} ({lista_colunas}) VALUES ({placeholders})"
    try:
        for bloco in ler_em_blocos(caminho_csv, tamanho_bloco):
            inserir_em_lote(conexao, sql_insert, bloco)
            metricas["linhas_lidas"] += len(bloco)
            metricas["linhas_inseridas"] += len(bloco)
            metricas["blocos_processados"] += 1
        conexao.commit()
    except Exception as exc:
        conexao.rollback()
        raise CargaRawError(f"Falha ao carregar {tabela}: {exc}") from exc
    return metricas
 
 
# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def executar_pipeline(forcar_download: bool, gerar_amostras_flag: bool, nivel_log: str) -> int:
    """Executa o pipeline completo de extração e carga RAW.
 
    Args:
        forcar_download: força novo download do zip.
        gerar_amostras_flag: gera amostras dos CSVs quando True.
        nivel_log: nível de logging configurado.
 
    Returns:
        0 em caso de sucesso, 1 em caso de falha.
    """
    configurar_logging(nivel_log)
    logging.info("Início do pipeline de extração")
 
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    PASTA_RAW.mkdir(parents=True, exist_ok=True)
 
    caminho_zip = PASTA_RAW / NOME_ZIP
    try:
        baixar_zip(caminho_zip, DRIVE_FILE_ID, forcar=forcar_download)
        arquivos_csv = extrair_zip(caminho_zip, PASTA_RAW)
        if gerar_amostras_flag:
            gerar_amostras(arquivos_csv, PASTA_AMOSTRAS)
 
        conexao = conectar()
        try:
            for chave in ORDEM_CARGA:
                # ORDEM_CARGA processa primeiro a tabela-mãe (viagem),
                # garantindo a integridade referencial da Silver.
                nome_csv = ARQUIVOS[chave]["csv"]
                tabela = ARQUIVOS[chave]["tabela_raw"]
                caminho_csv = arquivos_csv.get(nome_csv)
                if caminho_csv is None:
                    logging.warning("CSV %s não encontrado no zip — pulando %s", nome_csv, tabela)
                    continue
                colunas = obter_colunas_tabela(conexao, tabela)
                logging.info("Carregando %s -> %s", nome_csv, tabela)
                truncar_tabela(conexao, tabela)
                metricas = carregar_tabela(conexao, caminho_csv, tabela, colunas, TAMANHO_BLOCO)
                logging.info(
                    "%s: lidas=%d inseridas=%d descartadas=%d blocos=%d",
                    tabela, metricas["linhas_lidas"], metricas["linhas_inseridas"],
                    metricas["linhas_descartadas"], metricas["blocos_processados"],
                )
            logging.info("Pipeline concluído com sucesso")
            return 0
        finally:
            conexao.close()
    except Exception:
        logging.exception("Falha no pipeline de extração")
        return 1
 
 
def main() -> int:
    """Ponto de entrada do script.
 
    Returns:
        Código de saída do processo (0 sucesso, 1 falha).
    """
    parser = argparse.ArgumentParser(description="Extração e carga da camada RAW")
    parser.add_argument("--forcar-download", action="store_true", help="força novo download do zip")
    parser.add_argument("--sem-amostras", action="store_true", help="não gera amostras dos CSVs")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="nível de logging",
    )
    args = parser.parse_args()
    try:
        return executar_pipeline(
            forcar_download=args.forcar_download,
            gerar_amostras_flag=not args.sem_amostras,
            nivel_log=args.log_level,
        )
    except ExtracaoError as exc:
        logging.error("Erro de extração: %s", exc)
        return 1
    except Exception:
        logging.exception("Erro inesperado")
        return 1
 
 
if __name__ == "__main__":
    sys.exit(main())
