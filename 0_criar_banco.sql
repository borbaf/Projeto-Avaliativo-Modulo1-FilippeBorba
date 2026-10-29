/*
==============================================================================
 PROJETO AVALIATIVO - MODULO 1
 Turma: Analise_de_Dados_T6 - SENAI
 Aluno: Filippe Borba
 Arquitetura: MEDALLION (raw -> silver -> gold)
 
 IMPORTANTE: as colunas das tabelas RAW foram validadas contra os cabecalhos
 reais dos CSVs em 29/10/2026. A ordem das colunas segue EXATAMENTE a ordem
 dos CSVs (2025_Viagem.csv, 2025_Pagamento.csv, 2025_Passagem.csv,
 2025_Trecho.csv), porque o script 1_extrair.py insere os dados por POSICAO.
==============================================================================
*/
/* ----------------------------------------------------------------------------
 BLOCO 1 - DATABASE
 O CREATE DATABASE esta comentado porque o docker-compose ja cria o database
 via POSTGRES_DB=transparencia. Em um Postgres local, basta descomentar.
------------------------------------------------------------------------------*/
-- CREATE DATABASE transparencia;
-- \c transparencia;
 
/* ----------------------------------------------------------------------------
 BLOCO 2 - DROP DAS TABELAS (ordem inversa de dependencia)
------------------------------------------------------------------------------*/
DROP TABLE IF EXISTS silver_trecho     CASCADE;
DROP TABLE IF EXISTS silver_pagamento  CASCADE;
DROP TABLE IF EXISTS silver_passagem   CASCADE;
DROP TABLE IF EXISTS silver_viagem     CASCADE;
DROP TABLE IF EXISTS raw_trecho        CASCADE;
DROP TABLE IF EXISTS raw_pagamento     CASCADE;
DROP TABLE IF EXISTS raw_passagem      CASCADE;
DROP TABLE IF EXISTS raw_viagem        CASCADE;
 
/* ----------------------------------------------------------------------------
 BLOCO 3 - TABELAS RAW
 Todas as colunas VARCHAR, sem PK/FK/NOT NULL/CHECK/UNIQUE.
 Ordem das colunas = ordem exata dos cabecalhos dos CSVs.
------------------------------------------------------------------------------*/
CREATE TABLE raw_viagem (
    id_viagem              VARCHAR(20),
    num_proposta           VARCHAR(20),
    situacao               VARCHAR(50),
    viagem_urgente         VARCHAR(5),
    justificativa_urgencia VARCHAR(4000),
    cod_orgao_superior     VARCHAR(20),
    nome_orgao_superior    VARCHAR(255),
    cod_orgao_solicitante  VARCHAR(20),
    nome_orgao_solicitante VARCHAR(255),
    cpf_viajante           VARCHAR(20),
    nome_viajante          VARCHAR(255),
    cargo                  VARCHAR(255),
    funcao                 VARCHAR(255),
    descricao_funcao       VARCHAR(4000),
    data_inicio            VARCHAR(20),
    data_fim               VARCHAR(20),
    destinos               VARCHAR(4000),
    motivo                 VARCHAR(4000),
    valor_diarias          VARCHAR(30),
    valor_passagens        VARCHAR(30),
    valor_devolucao        VARCHAR(30),
    valor_outros_gastos    VARCHAR(30)
);
 
CREATE TABLE raw_pagamento (
    id_viagem           VARCHAR(20),
    num_proposta        VARCHAR(20),
    cod_orgao_superior  VARCHAR(20),
    nome_orgao_superior VARCHAR(255),
    cod_orgao_pagador   VARCHAR(20),
    nome_orgao_pagador  VARCHAR(255),
    cod_ug_pagadora     VARCHAR(20),
    nome_ug_pagadora    VARCHAR(255),
    tipo_pagamento      VARCHAR(50),
    valor               VARCHAR(30)
);
 
CREATE TABLE raw_passagem (
    id_viagem           VARCHAR(20),
    num_proposta        VARCHAR(20),
    meio_transporte     VARCHAR(50),
    pais_origem_ida     VARCHAR(60),
    uf_origem_ida       VARCHAR(40),
    cidade_origem_ida   VARCHAR(80),
    pais_destino_ida    VARCHAR(60),
    uf_destino_ida      VARCHAR(40),
    cidade_destino_ida  VARCHAR(80),
    pais_origem_volta   VARCHAR(60),
    uf_origem_volta     VARCHAR(40),
    cidade_origem_volta VARCHAR(80),
    pais_destino_volta  VARCHAR(60),
    uf_destino_volta    VARCHAR(40),
    cidade_destino_volta VARCHAR(80),
    valor_passagem      VARCHAR(30),
    taxa_servico        VARCHAR(30),
    data_emissao        VARCHAR(20),
    hora_emissao        VARCHAR(20)
);
 
CREATE TABLE raw_trecho (
    id_viagem        VARCHAR(20),
    num_proposta     VARCHAR(20),
    sequencia_trecho VARCHAR(10),
    origem_data      VARCHAR(20),
    origem_pais      VARCHAR(60),
    origem_uf        VARCHAR(40),
    origem_cidade    VARCHAR(80),
    destino_data     VARCHAR(20),
    destino_pais     VARCHAR(60),
    destino_uf       VARCHAR(40),
    destino_cidade   VARCHAR(80),
    meio_transporte  VARCHAR(50),
    numero_diarias   VARCHAR(30),
    missao           VARCHAR(5)
);
 
/* ----------------------------------------------------------------------------
 BLOCO 4 - TABELAS SILVER
 Tipos corretos, PK, FK, NOT NULL, CHECK e UNIQUE.
------------------------------------------------------------------------------*/
CREATE TABLE silver_viagem (
    id_viagem              VARCHAR(20) CONSTRAINT pk_silver_viagem PRIMARY KEY,
    num_proposta           VARCHAR(20),
    situacao               VARCHAR(50),
    viagem_urgente         VARCHAR(5),
    justificativa_urgencia VARCHAR(4000),
    cod_orgao_superior     VARCHAR(20),
    nome_orgao_superior    VARCHAR(255) CONSTRAINT nn_silver_viagem_orgao NOT NULL,
    cod_orgao_solicitante  VARCHAR(20),
    nome_orgao_solicitante VARCHAR(255),
    cpf_viajante           VARCHAR(20),
    nome_viajante          VARCHAR(255),
    cargo                  VARCHAR(255),
    funcao                 VARCHAR(255),
    descricao_funcao       VARCHAR(4000),
    data_inicio            DATE,
    data_fim               DATE,
    destinos               VARCHAR(4000),
    motivo                 VARCHAR(4000),
    valor_diarias          DECIMAL(10,2) CONSTRAINT ck_silver_viagem_diarias   CHECK (valor_diarias >= 0),
    valor_passagens        DECIMAL(10,2) CONSTRAINT ck_silver_viagem_passagens CHECK (valor_passagens >= 0),
    valor_devolucao        DECIMAL(10,2) CONSTRAINT ck_silver_viagem_devolucao CHECK (valor_devolucao >= 0),
    valor_outros_gastos    DECIMAL(10,2) CONSTRAINT ck_silver_viagem_outros    CHECK (valor_outros_gastos >= 0),
    valor_total            DECIMAL(12,2),
    duracao_dias           INT
);
 
CREATE TABLE silver_passagem (
    id_passagem         INT GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_silver_passagem PRIMARY KEY,
    id_viagem           VARCHAR(20) CONSTRAINT nn_silver_passagem_viagem NOT NULL
                        CONSTRAINT fk_silver_passagem_viagem REFERENCES silver_viagem(id_viagem),
    num_proposta        VARCHAR(20),
    meio_transporte     VARCHAR(50),
    pais_origem_ida     VARCHAR(60),
    uf_origem_ida       VARCHAR(40),
    cidade_origem_ida   VARCHAR(80),
    pais_destino_ida    VARCHAR(60),
    uf_destino_ida      VARCHAR(40),
    cidade_destino_ida  VARCHAR(80),
    pais_origem_volta   VARCHAR(60),
    uf_origem_volta     VARCHAR(40),
    cidade_origem_volta VARCHAR(80),
    pais_destino_volta  VARCHAR(60),
    uf_destino_volta    VARCHAR(40),
    cidade_destino_volta VARCHAR(80),
    valor_passagem      DECIMAL(10,2) CONSTRAINT ck_silver_passagem_valor CHECK (valor_passagem >= 0),
    taxa_servico        DECIMAL(10,2) CONSTRAINT ck_silver_passagem_taxa  CHECK (taxa_servico >= 0),
    data_emissao        DATE,
    hora_emissao        TIME
);
 
CREATE TABLE silver_pagamento (
    id_pagamento        INT GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_silver_pagamento PRIMARY KEY,
    id_viagem           VARCHAR(20) CONSTRAINT nn_silver_pagamento_viagem NOT NULL
                        CONSTRAINT fk_silver_pagamento_viagem REFERENCES silver_viagem(id_viagem),
    num_proposta        VARCHAR(20),
    cod_orgao_superior  VARCHAR(20),
    nome_orgao_superior VARCHAR(255),
    cod_orgao_pagador   VARCHAR(20),
    nome_orgao_pagador  VARCHAR(255),
    cod_ug_pagadora     VARCHAR(20),
    nome_ug_pagadora    VARCHAR(255),
    tipo_pagamento      VARCHAR(50) CONSTRAINT nn_silver_pagamento_tipo NOT NULL,
    valor               DECIMAL(10,2) CONSTRAINT ck_silver_pagamento_valor CHECK (valor >= 0)
);
 
CREATE TABLE silver_trecho (
    id_trecho           INT GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_silver_trecho PRIMARY KEY,
    id_viagem           VARCHAR(20) CONSTRAINT nn_silver_trecho_viagem NOT NULL
                        CONSTRAINT fk_silver_trecho_viagem REFERENCES silver_viagem(id_viagem),
    num_proposta        VARCHAR(20),
    sequencia_trecho    INT,
    origem_data         DATE,
    origem_pais         VARCHAR(60),
    origem_uf           VARCHAR(40),
    origem_cidade       VARCHAR(80),
    destino_data        DATE,
    destino_pais        VARCHAR(60),
    destino_uf          VARCHAR(40),
    destino_cidade      VARCHAR(80),
    meio_transporte     VARCHAR(50),
    numero_diarias      DECIMAL(10,2) CONSTRAINT ck_silver_trecho_diarias CHECK (numero_diarias >= 0),
    missao              VARCHAR(5),
    CONSTRAINT uq_silver_trecho_viagem_sequencia UNIQUE (id_viagem, sequencia_trecho)
);
 
/* ----------------------------------------------------------------------------
 BLOCO 5 - CHECKLIST DE CONSTRAINTS EXTRAS
 [x] 1 PK simples em silver_viagem (pk_silver_viagem)
 [x] 3 PKs identity (silver_passagem, silver_pagamento, silver_trecho)
 [x] 4 FKs para silver_viagem(id_viagem)
 [x] 1 UNIQUE composta (uq_silver_trecho_viagem_sequencia)
 [x] 2 NOT NULL adicionais (nn_silver_viagem_orgao, nn_silver_pagamento_tipo)
 [x] 6 CHECK de valores nao negativos (diarias, passagens, devolucao,
     outros, valor da passagem + taxa, pagamento, trecho diarias)
------------------------------------------------------------------------------*/
/* ----------------------------------------------------------------------------
 BLOCO 6 - DEFEITOS CONHECIDOS DO CSV ORIGINAL
 1) O cabecalho "Identificador do processo de viagem " do arquivo
    2025_Trecho.csv tem um ESPACO a direita dentro das aspas. O script
    2_transformar.py deve aplicar TRIM nesse campo antes de inserir.
 2) O cabecalho "Horada emissão/compra" do arquivo 2025_Passagem.csv e um
    erro de digitacao do arquivo original; foi mapeado para hora_emissao.
------------------------------------------------------------------------------*/
