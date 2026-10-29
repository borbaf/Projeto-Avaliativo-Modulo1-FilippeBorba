# -*- coding: utf-8 -*-
"""diagnostico.py -- Verificador de estado do projeto.

Roda no Windows (PowerShell) com Python 3.10+ e executa verificacoes
independentes de arquivos, pastas, dados, docker, banco, git e venv.
Cada verificacao e isolada: uma falha nao interrompe as demais.

Uso:
    python diagnostico.py
"""

import os
import sys
import json
import shutil
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

# psycopg2 e opcional: sem ele, a verificacao de banco retorna AVISO.
try:
    import psycopg2  # type: ignore
    DISPONIVEL_PSYCOPG2: bool = True
except ImportError:
    DISPONIVEL_PSYCOPG2 = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger("diag")

PASTA_RAIZ: Path = Path(__file__).resolve().parent

ARQUIVOS_OBRIGATORIOS: list[str] = [
    "0_criar_banco.sql", "1_extrair.py", "2_transformar.py",
    "3_analise.ipynb", "config.py", "banco.py", ".env",
    ".env.example", ".gitignore", "requirements.txt", "README.md",
    "docker-compose.yml",
]

PASTAS_OBRIGATORIAS: list[str] = [
    "data", "data/amostras", "data/raw", "sql", "logs", "tests",
]

TABELAS_ESPERADAS: list[str] = [
    "raw_viagem", "raw_pagamento", "raw_passagem", "raw_trecho",
    "silver_viagem", "silver_pagamento", "silver_passagem",
    "silver_trecho",
]

CSVS_DATA_RAW: list[str] = [
    "2025_Viagem.csv", "2025_Pagamento.csv",
    "2025_Passagem.csv", "2025_Trecho.csv",
]

CSVS_AMOSTRAS: list[str] = [
    "2025_Viagem_sample.csv", "2025_Pagamento_sample.csv",
    "2025_Passagem_sample.csv", "2025_Trecho_sample.csv",
]

PACOTES_CRITICOS: list[str] = [
    "psycopg2", "pandas", "gdown", "matplotlib", "seaborn",
]

SIMBOLOS: dict[str, str] = {"OK": "[OK]", "FALTA": "[--]", "AVISO": "[!]", "ERRO": "[X]"}

TIMEOUT_SUBPROCESS: int = 15


@dataclass
class Resultado:
    """Resultado de uma unica verificacao."""

    categoria: str
    item: str
    status: str  # "OK", "FALTA", "AVISO" ou "ERRO"
    detalhe: str = ""


@dataclass
class Relatorio:
    """Agrega resultados e produz um resumo por status."""

    resultados: list[Resultado] = field(default_factory=list)

    def adicionar(self, resultado: Resultado) -> None:
        """Adiciona um resultado ao relatorio."""
        self.resultados.append(resultado)

    def resumo(self) -> dict[str, int]:
        """Conta quantos resultados existem por status."""
        contagem: dict[str, int] = {"OK": 0, "FALTA": 0, "AVISO": 0, "ERRO": 0}
        for resultado in self.resultados:
            if resultado.status in contagem:
                contagem[resultado.status] += 1
        return contagem


def _seguro(funcao: Callable[[], list[Resultado]], categoria: str,
            relatorio: Relatorio) -> None:
    """Executa uma verificacao isolando qualquer excecao dela.

    Se a funcao levantar excecao, registra um resultado ERRO sem
    interromper as demais.
    """
    try:
        for resultado in funcao():
                       relatorio.adicionar(resultado)
    except Exception as exc:  # noqa: BLE001 - tolerancia a falhas
        relatorio.adicionar(Resultado(
            categoria=categoria, item=f"bloco '{categoria}'",
            status="ERRO",
            detalhe=f"excecao inesperada: {type(exc).__name__}: {exc}"))


def verificar_arquivos(raiz: Path) -> list[Resultado]:
    """Verifica os arquivos obrigatorios na raiz do projeto.

    Para o .env, verifica tambem se a linha ".env" esta no .gitignore;
    caso contrario, reporta ERRO de vazamento de credencial.
    """
    resultados: list[Resultado] = []
    gitignore_conteudo: str = ""
    caminho_gitignore: Path = raiz / ".gitignore"
    if caminho_gitignore.is_file():
        try:
            gitignore_conteudo = caminho_gitignore.read_text(
                encoding="utf-8", errors="replace")
        except OSError as exc:
            LOGGER.warning("Nao foi possivel ler .gitignore: %s", exc)

    for nome in ARQUIVOS_OBRIGATORIOS:
        caminho: Path = raiz / nome
        if not caminho.is_file():
            resultados.append(Resultado("ARQUIVOS", nome, "FALTA",
                                        "arquivo nao encontrado na raiz"))
            continue
        tamanho: int = caminho.stat().st_size
        detalhe: str = f"presente, {tamanho} bytes"
        if nome == ".env":
            protegido: bool = False
            for linha in gitignore_conteudo.splitlines():
                if linha.strip() == ".env":
                    protegido = True
                    break
            if protegido:
                detalhe += "; '.env' esta listado no .gitignore"
            else:
                resultados.append(Resultado(
                    "ARQUIVOS", nome, "ERRO",
                    "credencial pode vazar: '.env' nao consta no .gitignore"))
                continue
        resultados.append(Resultado("ARQUIVOS", nome, "OK", detalhe))
    return resultados


def verificar_pastas(raiz: Path) -> list[Resultado]:
    """Verifica as pastas obrigatorias do projeto."""
    resultados: list[Resultado] = []
    for relativa in PASTAS_OBRIGATORIAS:
        caminho: Path = raiz / relativa
        if caminho.is_dir():
            resultados.append(Resultado("PASTAS", relativa, "OK", "pasta presente"))
        else:
            resultados.append(Resultado(
                "PASTAS", relativa, "FALTA", "pasta nao encontrada"))
    return resultados


def _cabecalho_csv(caminho: Path) -> str:
    """Le a primeira linha de um CSV com encoding latin-1.

    Retorna o numero de colunas e os 5 primeiros nomes para validar o DDL.
    """
    with open(caminho, "r", encoding="latin-1", newline="") as handle:
        primeira: str = handle.readline().rstrip("\r\n")
    colunas: list[str] = primeira.split(";") if ";" in primeira else primeira.split(",")
    return f"{len(colunas)} colunas; 5 primeiras: {colunas[:5]}"


def verificar_dados(raiz: Path) -> list[Resultado]:
    """Verifica os CSVs completos em data/raw e amostras em data/amostras.

    Para cada CSV completo, le o cabecalho com encoding latin-1 e
    registra o numero de colunas e os 5 primeiros nomes.
    """
    resultados: list[Resultado] = []
    for nome in CSVS_DATA_RAW:
        caminho: Path = raiz / "data" / "raw" / nome
        if not caminho.is_file():
            resultados.append(Resultado("DADOS", f"data/raw/{nome}", "FALTA",
                                        "arquivo nao encontrado"))
            continue
        tamanho_mb: float = caminho.stat().st_size / (1024 * 1024)
        try:
            detalhe: str = (f"presente, {tamanho_mb:.2f} MB; "
                            f"cabecalho: {_cabecalho_csv(caminho)}")
        except OSError as exc:
            detalhe = f"presente, {tamanho_mb:.2f} MB; cabecalho ilegivel: {exc}"
        resultados.append(Resultado("DADOS", f"data/raw/{nome}", "OK", detalhe))

    for nome in CSVS_AMOSTRAS:
        caminho: Path = raiz / "data" / "amostras" / nome
        if caminho.is_file():
            tamanho_mb: float = caminho.stat().st_size / (1024 * 1024)
            resultados.append(Resultado(
                "DADOS", f"data/amostras/{nome}", "OK",
                f"presente, {tamanho_mb:.2f} MB"))
        else:
            resultados.append(Resultado(
                "DADOS", f"data/amostras/{nome}", "FALTA",
                "amostra nao encontrada"))
    return resultados


def _rodar_comando(comando: list[str],
                   timeout: int = TIMEOUT_SUBPROCESS) -> tuple[int, str, str]:
    """Executa um comando externo capturando saida, com timeout.

    Retorna (codigo_de_saida, stdout, stderr). Excecoes (comando
    ausente, timeout) retornam codigo -1.
    """
    try:
        pr = subprocess.run(comando, capture_output=True, text=True,
                      timeout=timeout, check=False)
        return pr.returncode, pr.stdout, pr.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, "", f"{type(exc).__name__}: {exc}"


def verificar_docker() -> list[Resultado]:
    """Verifica docker e o container transparencia_postgres.

    FALTA quando docker nao existe; AVISO quando existe mas o container
    nao esta rodando; OK quando esta em execucao.
    """
    resultados: list[Resultado] = []
    docker_binario: str | None = shutil.which("docker")
    if docker_binario is None:
        resultados.append(Resultado("DOCKER", "binario docker", "FALTA",
                                    "docker nao encontrado no PATH"))
        return resultados
    resultados.append(Resultado("DOCKER", "binario docker", "OK",
                                f"encontrado em {docker_binario}"))
    codigo, stdout, _ = _rodar_comando(
        ["docker", "compose", "ps", "--format", "json"])
    if codigo != 0:
        resultados.append(Resultado(
            "DOCKER", "docker compose ps", "AVISO",
            f"comando falhou (codigo {codigo})"))
        return resultados
    rodando: bool = False
    for linha in stdout.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        if linha.startswith("["):
            continue
        try:
            item: dict[str, Any] = json.loads(linha)
        except json.JSONDecodeError:
            continue
        nome: str = str(item.get("Name") or item.get("Service") or "")
        status: str = str(item.get("State") or item.get("Status") or "").lower()
        if "transparencia_postgres" in nome and ("running" in status or "up" in status):
            rodando = True
    if rodando:
        resultados.append(Resultado(
            "DOCKER", "container transparencia_postgres", "OK",
            "container em execucao"))
    else:
        resultados.append(Resultado(
            "DOCKER", "container transparencia_postgres", "AVISO",
            "docker instalado, mas container nao esta rodando"))
    return resultados


def verificar_banco() -> list[Resultado]:
    """Verifica conexao e tabelas do banco PostgreSQL.

    Sem psycopg2, retorna AVISO. Importa POSTGRES_CONFIG de config.py,
    conecta com timeout curto, compara as tabelas do schema public com
    as 8 esperadas e conta as linhas de cada tabela existente. Fecha a
    conexao no finally.
    """
    resultados: list[Resultado] = []
    if not DISPONIVEL_PSYCOPG2:
        resultados.append(Resultado(
            "BANCO", "psycopg2", "AVISO",
            "psycopg2 nao instalado; verificacao de banco ignorada"))
        return resultados
    try:
        from config import POSTGRES_CONFIG  # type: ignore
    except Exception as exc:  # noqa: BLE001 - config pode estar ausente
        resultados.append(Resultado(
            "BANCO", "config.POSTGRES_CONFIG", "ERRO",
            f"nao foi possivel importar POSTGRES_CONFIG: {exc}"))
        return resultados
    if not isinstance(POSTGRES_CONFIG, dict):
        resultados.append(Resultado(
            "BANCO", "config.POSTGRES_CONFIG", "ERRO",
            "POSTGRES_CONFIG nao e um dicionario"))
        return resultados
    conexao = None
    try:
        conexao = psycopg2.connect(connect_timeout=5, **POSTGRES_CONFIG)
        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'")
            existentes: set[str] = {str(linha[0]) for linha in cursor.fetchall()}
            for tabela in TABELAS_ESPERADAS:
                if tabela in existentes:
                    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                    total: int = int(cursor.fetchone()[0])
                    resultados.append(Resultado(
                        "BANCO", f"tabela {tabela}", "OK",
                        f"existe, {total} linha(s)"))
                else:
                    resultados.append(Resultado(
                        "BANCO", f"tabela {tabela}", "FALTA",
                        "tabela nao existe no schema public"))
    except Exception as exc:  # noqa: BLE001 - falha de conexao/consulta
        resultados.append(Resultado(
            "BANCO", "conexao/consulta", "ERRO", f"{type(exc).__name__}: {exc}"))
    finally:
        if conexao is not None:
            try:
                conexao.close()
            except Exception:  # noqa: BLE001
                LOGGER.debug("Erro ao fechar conexao", exc_info=True)
    return resultados


def verificar_git(raiz: Path) -> list[Resultado]:
    """Verifica o estado do repositorio git do projeto."""
    resultados: list[Resultado] = []
    if not (raiz / ".git").is_dir():
        resultados.append(Resultado(
            "GIT", "pasta .git", "FALTA", "pasta .git ausente; nao e repositorio"))
        return resultados
    resultados.append(Resultado("GIT", "pasta .git", "OK", "pasta .git presente"))
    codigo, _, _ = _rodar_comando(["git", "rev-parse", "--is-inside-work-tree"])
    if codigo != 0:
        resultados.append(Resultado(
            "GIT", "repositorio git", "AVISO",
            "pasta .git existe, mas git nao respondeu"))
        return resultados
    resultados.append(Resultado("GIT", "repositorio git", "OK",
                                "diretorio de trabalho valido"))
    _, branch, _ = _rodar_comando(["git", "branch", "--show-current"])
    resultados.append(Resultado("GIT", "branch atual", "OK",
                                branch.strip() or "(sem branch / detached)"))
    codigo, saida, _ = _rodar_comando(["git", "rev-list", "--count", "HEAD"])
    if codigo == 0 and saida.strip().isdigit():
        resultados.append(Resultado("GIT", "commits", "OK",
                                    f"{int(saida.strip())} commit(s)"))
    else:
        resultados.append(Resultado(
            "GIT", "commits", "AVISO", "nenhum commit ainda (HEAD invalido)"))
    codigo, remotos, _ = _rodar_comando(["git", "remote", "-v"])
    if codigo == 0 and remotos.strip():
        resultados.append(Resultado(
            "GIT", "remote", "OK", remotos.strip().splitlines()[0][:100]))
    else:
        resultados.append(Resultado("GIT", "remote", "AVISO", "nenhum remoto"))
    codigo, sujos, _ = _rodar_comando(["git", "status", "--porcelain"])
    if codigo == 0:
        pendentes: int = len(sujos.splitlines()) if sujos.strip() else 0
        if pendentes == 0:
            resultados.append(Resultado(
                "GIT", "arquivos nao commitados", "OK", "working tree limpa"))
        else:
            resultados.append(Resultado(
                "GIT", "arquivos nao commitados", "AVISO",
                f"{pendentes} arquivo(s) alterado(s) nao commitado(s)"))
    else:
        resultados.append(Resultado(
            "GIT", "arquivos nao commitados", "AVISO", "git status falhou"))
    return resultados


def _pacote_disponivel(pacote: str) -> bool:
    """Tenta importar estaticamente um pacote critico; True se existe."""
    try:
        if pacote == "psycopg2":
            import psycopg2  # noqa: F401
        elif pacote == "pandas":
            import pandas  # noqa: F401
        elif pacote == "gdown":
            import gdown  # noqa: F401
        elif pacote == "matplotlib":
            import matplotlib  # noqa: F401
        elif pacote == "seaborn":
            import seaborn  # noqa: F401
        else:
            return False
        return True
    except Exception:  # noqa: BLE001 - pacote ausente ou quebrado
        return False


def verificar_venv() -> list[Resultado]:
    """Verifica ambiente virtual ativo e pacotes criticos instalados."""
    resultados: list[Resultado] = []
    if sys.prefix != sys.base_prefix:
        resultados.append(Resultado(
            "VENV", "ambiente virtual", "OK", f"venv ativo: {sys.prefix}"))
    else:
        resultados.append(Resultado(
            "VENV", "ambiente virtual", "AVISO",
            "nenhum venv ativo (Python do sistema)"))
    for pacote in PACOTES_CRITICOS:
        if _pacote_disponivel(pacote):
            resultados.append(Resultado("VENV", f"pacote {pacote}", "OK",
                                        "importavel"))
        else:
            resultados.append(Resultado("VENV", f"pacote {pacote}", "FALTA",
                                        "nao instalado"))
    return resultados


def calcular_progresso(relatorio: Relatorio) -> float:
    """Percentual de itens OK sobre o total verificavel (sem AVISO)."""
    total: int = sum(1 for r in relatorio.resultados
                     if r.status in ("OK", "FALTA", "ERRO"))
    if total == 0:
        return 0.0
    acertos: int = sum(1 for r in relatorio.resultados if r.status == "OK")
    return 100.0 * acertos / total


def imprimir_relatorio(relatorio: Relatorio) -> None:
    """Imprime o relatorio em tabela de texto alinhada e agrupada.

    Usa simbolos ASCII ([OK], [--], [!], [X]) para evitar problemas de
    encoding em terminais Windows (PowerShell).
    """
    larg_st, larg_it, larg_det = 6, 40, 60
    largura: int = larg_st + larg_it + larg_det + 6
    linha: str = "-" * largura
    print("=" * largura)
    print("RELATORIO DE DIAGNOSTICO DO PROJETO".center(largura))
    print("=" * largura)
    categorias: list[str] = []
    for r in relatorio.resultados:
        if r.categoria not in categorias:
            categorias.append(r.categoria)
    for categoria in categorias:
        print("")
        print(f"--- {categoria} ---")
        print(linha)
        print(f"{'STATUS':<{larg_st}} {'ITEM':<{larg_it}} DETALHE")
        print(linha)
        for r in relatorio.resultados:
            if r.categoria != categoria:
                continue
            detalhe: str = r.detalhe
            if len(detalhe) > larg_det:
                detalhe = detalhe[:larg_det - 3] + "..."
            print(f"{SIMBOLOS.get(r.status, '[?]'):<{larg_st}} "
                  f"{r.item:<{larg_it}} {detalhe}")
    contagem: dict[str, int] = relatorio.resumo()
    total: int = len(relatorio.resultados)
    progresso: float = calcular_progresso(relatorio)
    preenchidos: int = int(round(progresso / 5))
    barra: str = "#" * preenchidos + "." * (20 - preenchidos)
    print("")
    print(linha)
    print(f"RESUMO: OK={contagem['OK']} FALTA={contagem['FALTA']} "
          f"AVISO={contagem['AVISO']} ERRO={contagem['ERRO']} TOTAL={total}")
    print(f"PROGRESSO: [{barra}] {progresso:.1f}% dos itens verificaveis OK")
    print(linha)


def main() -> int:
    """Executa todas as verificacoes em sequencia e imprime o relatorio.

    Cada verificacao e independente: uma falha nao interrompe as demais.
    Retorna 0 se nao houver ERRO nem FALTA, 1 caso contrario.
    """
    relatorio: Relatorio = Relatorio()
    verificacoes: list[tuple[str, Callable[[], list[Resultado]]]] = [
        ("ARQUIVOS", lambda: verificar_arquivos(PASTA_RAIZ)),
        ("PASTAS", lambda: verificar_pastas(PASTA_RAIZ)),
        ("DADOS", lambda: verificar_dados(PASTA_RAIZ)),
        ("DOCKER", verificar_docker),
        ("BANCO", verificar_banco),
        ("GIT", lambda: verificar_git(PASTA_RAIZ)),
        ("VENV", verificar_venv),
    ]
    for categoria, funcao in verificacoes:
        _seguro(funcao, categoria, relatorio)
    try:
        imprimir_relatorio(relatorio)
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("Falha ao imprimir relatorio: %s", exc)
        return 1
    contagem: dict[str, int] = relatorio.resumo()
    return 0 if (contagem["ERRO"] == 0 and contagem["FALTA"] == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
