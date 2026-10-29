# -*- coding: utf-8 -*-
"""Configurações centrais do pipeline de dados (Projeto Avaliativo Módulo 1).
 
Este módulo concentra caminhos, parâmetros de conexão e constantes usadas
por todos os demais scripts do projeto. Também carrega variáveis de ambiente
de um arquivo .env localizado na raiz do repositório.
"""
 
import os
from pathlib import Path
 
# --------------------------------------------------------------------------- #
# Caminhos base do projeto
# --------------------------------------------------------------------------- #
PASTA_RAIZ = Path(__file__).resolve().parent
PASTA_DADOS = PASTA_RAIZ / "data"
 
 
def carregar_env() -> None:
    """Carrega variáveis de ambiente do arquivo .env da raiz do projeto.
 
    Implementação minimalista que evita a dependência externa de
    python-dotenv: lê o arquivo linha a linha, ignora linhas vazias,
    comentários (linhas iniciadas por '#') e linhas sem o caractere '=',
    e registra cada variável com os.environ.setdefault, de modo que
    variáveis já definidas no ambiente (ex.: no docker-compose) tenham
    prioridade sobre o arquivo.
    """
    caminho_env = PASTA_RAIZ / ".env"
    if not caminho_env.exists():
        # Sem .env, seguimos com os defaults e com o ambiente do sistema.
        return
    with caminho_env.open("r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip())
 
 
# Carrega o .env no nível do módulo, antes de qualquer acesso a os.environ.
carregar_env()
 
# --------------------------------------------------------------------------- #
# Configuração de conexão com o PostgreSQL
# --------------------------------------------------------------------------- #
POSTGRES_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", ""),
    "dbname": os.environ.get("POSTGRES_DATABASE", "transparencia"),
}
 
# --------------------------------------------------------------------------- #
# Constantes do projeto
# --------------------------------------------------------------------------- #
ANO = "2025"
 
# Arquivo oficial viagens_2025_6meses.zip da pasta data do Drive do curso,
# id validado em janela anônima para garantir acesso público.
DRIVE_FILE_ID = "1pQjKacyHdIsyteknQbwKGM5_4hL5V4RV"
 
# Tamanho dos blocos lidos durante a carga (controla o uso de memória).
TAMANHO_BLOCO = 50_000
 
# Mapeamento de cada arquivo CSV do conjunto de dados para a tabela raw.
ARQUIVOS = {
    "viagem": {
        "csv": f"{ANO}_Viagem.csv",
        "tabela_raw": "raw_viagem",
    },
    "pagamento": {
        "csv": f"{ANO}_Pagamento.csv",
        "tabela_raw": "raw_pagamento",
    },
    "passagem": {
        "csv": f"{ANO}_Passagem.csv",
        "tabela_raw": "raw_passagem",
    },
    "trecho": {
        "csv": f"{ANO}_Trecho.csv",
        "tabela_raw": "raw_trecho",
    },
}
 
# Formato dos CSVs publicados pelo Portal da Transparência.
CSV_SEPARADOR = ";"
CSV_ENCODING = "latin-1"
