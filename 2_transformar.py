"""
Pipeline de transformacao da camada Silver.
 
Le as quatro tabelas raw_* carregadas pelo 1_extrair.py, aplica tipagem,
conversoes de data e decimal, calcula as colunas derivadas de silver_viagem
e carrega as quatro tabelas silver_* respeitando PK, FK e constraints.
 
Uso:
    python 2_transformar.py
"""
 
import logging
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterator
 
import psycopg2.extensions
 
from banco import BancoError, conectar, contar_linhas, executar, inserir_em_lote
 
logger = logging.getLogger(__name__)
 
TAMANHO_BLOCO = 10_000
 
FORMATO_DATA = "%d/%m/%Y"
 
SQL_INSERT_VIAGEM = """
    INSERT INTO silver_viagem (
        id_viagem, num_proposta, situacao, viagem_urgente,
        cod_orgao_superior, nome_orgao_superior, nome_viajante, cargo,
        data_inicio, data_fim, destinos, motivo,
        valor_diarias, valor_passagens, valor_devolucao,
        valor_outros_gastos, valor_total, duracao_dias
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
"""
 
SQL_INSERT_PASSAGEM = """
    INSERT INTO silver_passagem (
        id_viagem, meio_transporte,
        pais_origem_ida, uf_origem_ida, cidade_origem_ida,
        pais_destino_ida, uf_destino_ida, cidade_destino_ida,
        valor_passagem, taxa_servico, data_emissao
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
"""
 
SQL_INSERT_PAGAMENTO = """
    INSERT INTO silver_pagamento (
        id_viagem, num_proposta, nome_orgao_pagador,
        nome_ug_pagadora, tipo_pagamento, valor
    ) VALUES (%s, %s, %s, %s, %s, %s)
"""
 
SQL_INSERT_TRECHO = """
    INSERT INTO silver_trecho (
        id_viagem, sequencia_trecho,
        origem_data, origem_uf, origem_cidade,
        destino_data, destino_uf, destino_cidade,
        meio_transporte, numero_diarias
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
 
 
class TransformacaoError(Exception):
    """Erro na transformacao de dados da camada Raw para a Silver."""
 
 
def configurar_log() -> None:
    """Configura o logger para arquivo e console."""
    from config import PASTA_RAIZ
 
    pasta_logs = PASTA_RAIZ / "logs"
    pasta_logs.mkdir(parents=True, exist_ok=True)
    formato = "%(asctime)s %(levelname)s %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=formato,
        handlers=[
            logging.FileHandler(pasta_logs / "transformacao.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
 
 
def converter_data(valor: Any) -> date | None:
    """
    Converte texto DD/MM/AAAA em date.
 
    Args:
        valor: valor bruto lido da camada Raw.
 
    Returns:
        date quando a conversao e bem-sucedida, None caso contrario.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        return date(*reversed([int(p) for p in texto.split("/")]))
    except (ValueError, TypeError):
        return None
 
 
def converter_decimal(valor: Any) -> Decimal | None:
    """
    Converte texto com virgula decimal em Decimal.
 
    Args:
        valor: valor bruto lido da camada Raw (ex.: "1272,97").
 
    Returns:
        Decimal quando a conversao e bem-sucedida, None caso contrario.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        return Decimal(texto.replace(".", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
 
 
def converter_inteiro(valor: Any) -> int | None:
    """
    Converte texto em inteiro.
 
    Args:
        valor: valor bruto lido da camada Raw.
 
    Returns:
        int quando a conversao e bem-sucedida, None caso contrario.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        return int(float(texto.replace(",", ".")))
    except (ValueError, TypeError):
        return None
 
 
def texto_limpo(valor: Any, limite: int | None = None) -> str | None:
    """
    Normaliza um campo textual, truncando no limite da coluna.
 
    Args:
        valor: valor bruto lido da camada Raw.
        limite: tamanho maximo aceito pela coluna destino.
 
    Returns:
        Texto sem espacos nas pontas, ou None quando vazio.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    if limite is not None:
        return texto[:limite]
    return texto
 
 
def ler_em_blocos(
    conexao: psycopg2.extensions.connection,
    tabela: str,
    tamanho_bloco: int = TAMANHO_BLOCO,
) -> Iterator[list[tuple]]:
    """
    Le uma tabela em blocos usando cursor server-side nomeado.
 
    O cursor nomeado faz o PostgreSQL enviar as linhas sob demanda,
    mantendo o uso de memoria constante independente do volume da tabela.
 
    Args:
        conexao: conexao aberta via banco.conectar().
        tabela: nome da tabela de origem (somente nomes definidos no codigo).
        tamanho_bloco: quantidade de linhas por bloco.
 
    Yields:
        Lista de tuplas com as linhas do bloco.
    """
    cursor = conexao.cursor(name=f"cursor_{tabela}")
    try:
        cursor.itersize = tamanho_bloco
        cursor.execute(f"SELECT * FROM {tabela}")
        while True:
            bloco = cursor.fetchmany(tamanho_bloco)
            if not bloco:
                break
            yield bloco
    finally:
        cursor.close()
 
 
def transformar_viagem(linha: tuple) -> tuple | None:
    """
    Converte uma linha de raw_viagem em tupla pronta para silver_viagem.
 
    Args:
        linha: tupla na ordem das colunas de raw_viagem.
 
    Returns:
        Tupla com 18 valores, ou None quando a linha deve ser descartada.
    """
    (
        id_viagem, num_proposta, situacao, viagem_urgente,
        justificativa_urgencia, cod_orgao_superior, nome_orgao_superior,
        cod_orgao_solicitante, nome_orgao_solicitante, cpf_viajante,
        nome_viajante, cargo, funcao, descricao_funcao,
        data_inicio, data_fim, destinos, motivo,
        valor_diarias, valor_passagens, valor_devolucao, valor_outros_gastos,
    ) = linha
 
    if not texto_limpo(nome_orgao_superior):
        return None
 
    dt_inicio = converter_data(data_inicio)
    dt_fim = converter_data(data_fim)
    if dt_inicio is None or dt_fim is None:
        return None
 
    v_diarias = converter_decimal(valor_diarias) or Decimal("0")
    v_passagens = converter_decimal(valor_passagens) or Decimal("0")
    v_devolucao = converter_decimal(valor_devolucao) or Decimal("0")
    v_outros = converter_decimal(valor_outros_gastos) or Decimal("0")
 
    if v_diarias < 0:
        return None
 
    valor_total = v_diarias + v_passagens + v_devolucao + v_outros
    duracao = (dt_fim - dt_inicio).days
 
    return (
        texto_limpo(id_viagem, 20),
        texto_limpo(num_proposta, 20),
        texto_limpo(situacao, 50),
        texto_limpo(viagem_urgente, 5),
        texto_limpo(cod_orgao_superior, 20),
        texto_limpo(nome_orgao_superior, 255),
        texto_limpo(nome_viajante, 255),
        texto_limpo(cargo, 255),
        dt_inicio,
        dt_fim,
        texto_limpo(destinos, 4000),
        texto_limpo(motivo, 4000),
        v_diarias,
        v_passagens,
        v_devolucao,
        v_outros,
        valor_total,
        duracao,
    )
 
 
def transformar_passagem(linha: tuple) -> tuple | None:
    """
    Converte uma linha de raw_passagem em tupla pronta para silver_passagem.
 
    Args:
        linha: tupla na ordem das colunas de raw_passagem.
 
    Returns:
        Tupla com 11 valores, ou None quando a linha deve ser descartada.
    """
    (
        id_viagem, num_proposta, meio_transporte,
        pais_origem_ida, uf_origem_ida, cidade_origem_ida,
        pais_destino_ida, uf_destino_ida, cidade_destino_ida,
        pais_origem_volta, uf_origem_volta, cidade_origem_volta,
        pais_destino_volta, uf_destino_volta, cidade_destino_volta,
        valor_passagem, taxa_servico, data_emissao, hora_emissao,
    ) = linha
 
    dt_emissao = converter_data(data_emissao)
    if dt_emissao is None:
        return None
 
    v_passagem = converter_decimal(valor_passagem)
    v_taxa = converter_decimal(taxa_servico)
    if v_passagem is None or v_taxa is None:
        return None
    if v_passagem < 0 or v_taxa < 0:
        return None
 
    return (
        texto_limpo(id_viagem, 20),
        texto_limpo(meio_transporte, 50),
        texto_limpo(pais_origem_ida, 60),
        texto_limpo(uf_origem_ida, 40),
        texto_limpo(cidade_origem_ida, 80),
        texto_limpo(pais_destino_ida, 60),
        texto_limpo(uf_destino_ida, 40),
        texto_limpo(cidade_destino_ida, 80),
        v_passagem,
        v_taxa,
        dt_emissao,
    )
 
 
def transformar_pagamento(linha: tuple) -> tuple | None:
    """
    Converte uma linha de raw_pagamento em tupla pronta para silver_pagamento.
 
    Args:
        linha: tupla na ordem das colunas de raw_pagamento.
 
    Returns:
        Tupla com 6 valores, ou None quando a linha deve ser descartada.
    """
    (
        id_viagem, num_proposta, cod_orgao_superior, nome_orgao_superior,
        cod_orgao_pagador, nome_orgao_pagador, cod_ug_pagadora,
        nome_ug_pagadora, tipo_pagamento, valor,
    ) = linha
 
    if not texto_limpo(tipo_pagamento):
        return None
 
    v_valor = converter_decimal(valor)
    if v_valor is None or v_valor < 0:
        return None
 
    return (
        texto_limpo(id_viagem, 20),
        texto_limpo(num_proposta, 20),
        texto_limpo(nome_orgao_pagador, 255),
        texto_limpo(nome_ug_pagadora, 255),
        texto_limpo(tipo_pagamento, 50),
        v_valor,
    )
 
 
def transformar_trecho(linha: tuple) -> tuple | None:
    """
    Converte uma linha de raw_trecho em tupla pronta para silver_trecho.
 
    Args:
        linha: tupla na ordem das colunas de raw_trecho.
 
    Returns:
        Tupla com 10 valores, ou None quando a linha deve ser descartada.
    """
    (
        id_viagem, num_proposta, sequencia_trecho,
        origem_data, origem_pais, origem_uf, origem_cidade,
        destino_data, destino_pais, destino_uf, destino_cidade,
        meio_transporte, numero_diarias, missao,
    ) = linha
 
    seq = converter_inteiro(sequencia_trecho)
    if seq is None:
        return None
 
    dt_origem = converter_data(origem_data)
    dt_destino = converter_data(destino_data)
    if dt_origem is None or dt_destino is None:
        return None
 
    n_diarias = converter_decimal(numero_diarias)
    if n_diarias is None or n_diarias < 0:
        return None
 
    return (
        texto_limpo(id_viagem, 20),
        seq,
        dt_origem,
        texto_limpo(origem_uf, 40),
        texto_limpo(origem_cidade, 80),
        dt_destino,
        texto_limpo(destino_uf, 40),
        texto_limpo(destino_cidade, 80),
        texto_limpo(meio_transporte, 50),
        n_diarias,
    )
 
 
def carregar_tabela(
    conexao_leitura: psycopg2.extensions.connection,
    conexao_escrita: psycopg2.extensions.connection,
    tabela_raw: str,
    tabela_silver: str,
    sql_insert: str,
    transformador,
    chave_dedup: tuple[int, ...],
    ids_validos: set[str] | None = None,
) -> dict:
    """
    Le a tabela Raw em blocos, transforma, deduplica e insere na Silver.
 
    Args:
        conexao_leitura: conexao dedicada ao cursor server-side.
        conexao_escrita: conexao dedicada as insercoes.
        tabela_raw: nome da tabela de origem.
        tabela_silver: nome da tabela de destino.
        sql_insert: comando INSERT com placeholders %s.
        transformador: funcao que converte uma linha bruta em tupla.
        chave_dedup: posicoes dos campos que formam a chave de deduplicacao.
        ids_validos: conjunto de id_viagem existentes em silver_viagem,
            usado para descartar orfaos que violariam a FK.
 
    Returns:
        Dicionario com lidas, inseridas, descartadas e motivos.
 
    Raises:
        TransformacaoError: se a carga falhar de forma irrecuperavel.
    """
    logger.info("Transformando %s -> %s", tabela_raw, tabela_silver)
 
    executar(
    conexao_escrita,
    f"TRUNCATE TABLE {tabela_silver} RESTART IDENTITY CASCADE",
            )
 
    lidas = 0
    inseridas = 0
    descartadas = 0
    motivos: dict[str, int] = {}
    vistos: set[tuple] = set()
 
    def registrar(motivo: str) -> None:
        motivos[motivo] = motivos.get(motivo, 0) + 1
 
    for bloco in ler_em_blocos(conexao_leitura, tabela_raw):
        convertidas: list[tuple] = []
        for linha in bloco:
            lidas += 1
            convertida = transformador(linha)
            if convertida is None:
                descartadas += 1
                registrar("conversao_invalida")
                continue
 
            if ids_validos is not None:
                id_viagem = convertida[0]
                if id_viagem not in ids_validos:
                    descartadas += 1
                    registrar("fk_orfao")
                    continue
 
            chave = tuple(convertida[i] for i in chave_dedup)
            if chave in vistos:
                descartadas += 1
                registrar("duplicata")
                continue
            vistos.add(chave)
 
            convertidas.append(convertida)
 
        if convertidas:
            inseridas += inserir_em_lote(conexao_escrita, sql_insert, convertidas)
 
    logger.info(
        "%s: lidas=%d inseridas=%d descartadas=%d %s",
        tabela_silver, lidas, inseridas, descartadas,
        motivos if motivos else "",
    )
 
    return {
        "tabela": tabela_silver,
        "lidas": lidas,
        "inseridas": inseridas,
        "descartadas": descartadas,
        "motivos": motivos,
    }
 
 
def carregar_ids_viagem(conexao: psycopg2.extensions.connection) -> set[str]:
    """
    Carrega o conjunto de id_viagem presentes em silver_viagem.
 
    Args:
        conexao: conexao aberta com o banco.
 
    Returns:
        Conjunto de identificadores validos para a FK.
    """
    from banco import consultar
 
    linhas = consultar(conexao, "SELECT id_viagem FROM silver_viagem")
    return {linha[0] for linha in linhas}
 
 
def main() -> None:
    """
    Executa o pipeline completo de transformacao Raw para Silver.
 
    Raises:
        TransformacaoError: se qualquer etapa falhar.
    """
    configurar_log()
    logger.info("Inicio do pipeline de transformacao")
 
    conexao_leitura = conectar()
    conexao_escrita = conectar()
    resumos: list[dict] = []
 
    try:
        resumos.append(
            carregar_tabela(
                conexao_leitura, conexao_escrita,
                "raw_viagem", "silver_viagem",
                SQL_INSERT_VIAGEM, transformar_viagem,
                chave_dedup=(0,),
            )
        )
 
        ids_validos = carregar_ids_viagem(conexao_escrita)
        logger.info("silver_viagem: %d ids validos para FK", len(ids_validos))
 
        resumos.append(
            carregar_tabela(
                conexao_leitura, conexao_escrita,
                "raw_passagem", "silver_passagem",
                SQL_INSERT_PASSAGEM, transformar_passagem,
                chave_dedup=(0, 1, 9, 10),
                ids_validos=ids_validos,
            )
        )
 
        resumos.append(
            carregar_tabela(
                conexao_leitura, conexao_escrita,
                "raw_pagamento", "silver_pagamento",
                SQL_INSERT_PAGAMENTO, transformar_pagamento,
                chave_dedup=(0, 1, 4, 5),
                ids_validos=ids_validos,
            )
        )
 
        resumos.append(
            carregar_tabela(
                conexao_leitura, conexao_escrita,
                "raw_trecho", "silver_trecho",
                SQL_INSERT_TRECHO, transformar_trecho,
                chave_dedup=(0, 1),
                ids_validos=ids_validos,
            )
        )
    except BancoError as erro:
        raise TransformacaoError(f"Falha na transformacao: {erro}") from erro
    finally:
        conexao_leitura.close()
        conexao_escrita.close()
 
    logger.info("=" * 70)
    logger.info("RESUMO FINAL")
    logger.info("=" * 70)
    total = 0
    for resumo in resumos:
        logger.info(
            "%-18s %9d linhas | descartadas=%d %s",
            resumo["tabela"], resumo["inseridas"],
            resumo["descartadas"], resumo["motivos"] or "",
        )
        total += resumo["inseridas"]
    logger.info("-" * 70)
    logger.info("%-18s %9d linhas", "TOTAL", total)
    logger.info("Pipeline concluido com sucesso")
 
 
if __name__ == "__main__":
    main()
