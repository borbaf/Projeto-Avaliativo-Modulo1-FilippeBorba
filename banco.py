"""
Módulo de acesso ao banco de dados PostgreSQL do projeto.
 
Versão corrigida do template, mantendo a mesma interface
pública (conectar, executar, inserir_em_lote) e adicionando as correções:
rollback em caso de falha, retorno de contagem de linhas, separação entre
leitura e escrita e processamento em lotes menores para controlar memória.
"""
 
import logging
from typing import Any, Sequence
 
import psycopg2
import psycopg2.extensions
from psycopg2 import Error as psycopg2_Error
 
from config import POSTGRES_CONFIG

logger = logging.getLogger(__name__)
 
 
class BancoError(Exception):
    """Erro de acesso ao banco de dados, encapsulando falhas do psycopg2."""
 
 
def conectar() -> psycopg2.extensions.connection:
    """Abre uma conexão com o PostgreSQL usando POSTGRES_CONFIG.
 
    Returns:
        psycopg2.extensions.connection: conexão aberta com o banco.
 
    Raises:
        BancoError: se a conexão falhar, com mensagem clara indicando
            host, port e dbname e orientando a verificar o .env e se o
            0_criar_banco.sql foi executado.
    """
    # CORREÇÃO: captura psycopg2.Error e levanta BancoError com contexto
    # (host, port, dbname), em vez de deixar a exceção crua subir.
    try:
        conexao = psycopg2.connect(**POSTGRES_CONFIG)
    except psycopg2_Error as erro:
        host = POSTGRES_CONFIG.get("host", "?")
        port = POSTGRES_CONFIG.get("port", "?")
        dbname = POSTGRES_CONFIG.get("dbname", "?")
        logger.error("Falha ao conectar ao banco %s:%s/%s: %s", host, port, dbname, erro)
        raise BancoError(
            f"Não foi possível conectar ao banco em host={host}, port={port}, "
            f"dbname={dbname}. Verifique o arquivo .env e se o script "
            f"0_criar_banco.sql foi executado (banco/tabelas criados)."
        ) from erro
    return conexao
 
 
def executar(conexao: psycopg2.extensions.connection, sql: str, commit: bool = True) -> None:
    """Executa um comando SQL e, opcionalmente, confirma a transação.
 
    Args:
        conexao: conexão aberta com o banco de dados.
        sql: comando SQL a ser executado (INSERT, UPDATE, DELETE, DDL...).
        commit: se True, executa commit após o comando. Comandos de
            LEITURA devem passar commit=False, pois não alteram dados e
            assim a transação permanece coerente para leituras seguintes.
 
    Raises:
        BancoError: se a execução falhar; rollback é feito e a exceção
            original é preservada.
    """
    # CORREÇÃO: rollback em caso de falha e fechamento do cursor no finally.
    cursor = conexao.cursor()
    try:
        cursor.execute(sql)
        if commit:
            conexao.commit()
    except psycopg2_Error as erro:
        conexao.rollback()
        logger.error("Falha ao executar SQL: %s", erro)
        raise BancoError(f"Falha ao executar o comando SQL: {erro}") from erro
    finally:
        cursor.close()
 
 
def consultar(
    conexao: psycopg2.extensions.connection,
    sql: str,
    parametros: Sequence[Any] | None = None,
) -> list[tuple]:
    """Executa um SELECT e retorna todas as linhas encontradas.
 
    Args:
        conexao: conexão aberta com o banco de dados.
        sql: comando SELECT a ser executado (use %s como placeholders).
        parametros: valores dos placeholders, se houver.
 
    Returns:
        list[tuple]: todas as linhas retornadas pelo fetchall.
 
    Raises:
        BancoError: se a consulta falhar.
    """
    # CORREÇÃO: separação entre leitura e escrita — consultar NÃO faz
    # commit; é exclusiva para SELECT.
    cursor = conexao.cursor()
    try:
        if parametros is not None:
            cursor.execute(sql, parametros)
        else:
            cursor.execute(sql)
        linhas: list[tuple] = cursor.fetchall()
    except psycopg2_Error as erro:
        logger.error("Falha na consulta: %s", erro)
        raise BancoError(f"Falha ao executar a consulta: {erro}") from erro
    finally:
        cursor.close()
    return linhas
 
 
def inserir_em_lote(
    conexao: psycopg2.extensions.connection,
    sql_insert: str,
    linhas: Sequence[tuple],
    tamanho_lote: int = 10000,
) -> int:
    """Insere muitas linhas em lotes e retorna o total inserido.
 
    Args:
        conexao: conexão aberta com o banco de dados.
        sql_insert: comando INSERT com placeholders (%s) para uma linha.
        linhas: sequência de tuplas com os valores a inserir.
        tamanho_lote: tamanho de cada fatia processada. Lotes menores
            controlam o uso de memória em cargas grandes.
 
    Returns:
        int: número total de linhas inseridas com sucesso.
 
    Raises:
        BancoError: se alguma fatia falhar; rollback é feito e a mensagem
            informa o total já inserido antes da falha.
    """
    # CORREÇÃO: retorno de contagem do total inserido.
    if not linhas:
        return 0
 
    # CORREÇÃO: processamento em lotes menores (executemany por fatia)
    # para controlar a memória em cargas grandes.
    total_inserido = 0
    cursor = conexao.cursor()
    try:
        for inicio in range(0, len(linhas), tamanho_lote):
            fatia = linhas[inicio : inicio + tamanho_lote]
            cursor.executemany(sql_insert, fatia)
            total_inserido += len(fatia)
        conexao.commit()
    except psycopg2_Error as erro:
        conexao.rollback()
        logger.error("Falha na inserção em lote: %s", erro)
        raise BancoError(
            f"Falha na inserção em lote: {erro}. Total já inserido antes "
            f"da falha: {total_inserido} linha(s) — transação revertida."
        ) from erro
    finally:
        cursor.close()
    return total_inserido
 
 
def contar_linhas(conexao: psycopg2.extensions.connection, tabela: str) -> int:
    """Conta as linhas de uma tabela.
 
    Args:
        conexao: conexão aberta com o banco de dados.
        tabela: nome da tabela (somente nomes confiáveis/definidos no código).
 
    Returns:
        int: quantidade de linhas da tabela.
 
    Raises:
        BancoError: se a consulta falhar.
    """
    resultado = consultar(conexao, f"SELECT COUNT(*) FROM {tabela}")
    return int(resultado[0][0])

