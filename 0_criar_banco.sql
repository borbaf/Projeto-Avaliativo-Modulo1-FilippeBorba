/*
 * Projeto avaliativo Módulo 1
 * Turma: Analise_de_Dados_T6 — SENAI
 * Aluno: Filippe Borba
 *
 * Arquitetura: Medallion (Raw -> Silver -> Gold)
 *
 * Nota sobre portabilidade: a sintaxe AUTO_INCREMENT do MySQL foi traduzida
 * para o equivalente do PostgreSQL, GENERATED ALWAYS AS IDENTITY.
 *
 * Camada RAW: fidelidade total ao CSV de origem — todas as colunas VARCHAR,
 * sem constraints de qualquer tipo, para não perder uma única linha na
 * ingestão (carga "land as-is").
 *
 * Camada SILVER: dados tipados e higienizados, com PK, FK e 2 constraints
 * extras (NOT NULL/CHECK/UNIQUE) por tabela, garantindo integridade
 * relacional e qualidade para a camada analítica (Gold).
 */
 
-- --------------------------------------------------------------------------- --
-- Bloco 1: banco de dados
-- --------------------------------------------------------------------------- --
-- CREATE DATABASE está comentado porque o docker-compose já cria o database
-- via variável POSTGRES_DB=transparencia no momento da subida do container.
--
-- CREATE DATABASE transparencia;
-- \c transparencia;
--
-- Em um PostgreSQL local (fora do Docker), basta descomentar as duas linhas
-- acima para executar este script de ponta a ponta.
 
-- --------------------------------------------------------------------------- --
-- Bloco 2: limpeza — DROP em ordem inversa de dependência
-- --------------------------------------------------------------------------- --
DROP TABLE IF EXISTS silver_trecho     CASCADE;
DROP TABLE IF EXISTS silver_pagamento  CASCADE;
DROP TABLE IF EXISTS silver_passagem   CASCADE;
DROP TABLE IF EXISTS silver_viagem     CASCADE;
DROP TABLE IF EXISTS raw_trecho        CASCADE;
DROP TABLE IF EXISTS raw_pagamento     CASCADE;
DROP TABLE IF EXISTS raw_passagem      CASCADE;
DROP TABLE IF EXISTS raw_viagem        CASCADE;
 
-- --------------------------------------------------------------------------- --
-- Bloco 3: tabelas RAW (Bronze) — tudo VARCHAR, sem constraints
-- --------------------------------------------------------------------------- --
CREATE TABLE raw_viagem (
    id_viagem           VARCHAR(20),
    num_proposta        VARCHAR(20),
    situacao            VARCHAR(50),
    viagem_urgente      VARCHAR(5),
    cod_orgao_superior  VARCHAR(20),
    nome_orgao_superior VARCHAR(255),
    nome_viajante       VARCHAR(255),
    cargo               VARCHAR(255),
    data_inicio         VARCHAR(20),
    data_fim            VARCHAR(20),
    destinos            VARCHAR(4000),
    motivo              VARCHAR(4000),
    valor_diarias       VARCHAR(30),
    valor_passagens     VARCHAR(30),
    valor_devolucao     VARCHAR(30),
    valor_outros_gastos VARCHAR(30),
    cpf_viajante        VARCHAR(20),
    funcao              VARCHAR(255)
);
 
CREATE TABLE raw_pagamento (
    id_viagem           VARCHAR(20),
    num_proposta        VARCHAR(20),
    nome_orgao_pagador  VARCHAR(255),
    nome_ug_pagadora    VARCHAR(255),
    tipo_pagamento      VARCHAR(50),
    valor               VARCHAR(30)
);
 
CREATE TABLE raw_passagem (
    id_viagem           VARCHAR(20),
    meio_transporte     VARCHAR(50),
    pais_origem_ida     VARCHAR(60),
    uf_origem_ida       VARCHAR(40),
    cidade_origem_ida   VARCHAR(80),
    pais_destino_ida    VARCHAR(60),
    uf_destino_ida      VARCHAR(40),
    cidade_destino_ida  VARCHAR(80),
    valor_passagem      VARCHAR(30),
    taxa_servico        VARCHAR(30),
    data_emissao        VARCHAR(20),
    pais_origem_volta   VARCHAR(60),
    uf_origem_volta     VARCHAR(40),
    cidade_origem_volta VARCHAR(80),
    pais_destino_volta  VARCHAR(60),
    uf_destino_volta    VARCHAR(40),
    cidade_destino_volta VARCHAR(80),
    data_volta          VARCHAR(20)
);
 
CREATE TABLE raw_trecho (
    id_viagem           VARCHAR(20),
    sequencia_trecho    VARCHAR(10),
    origem_data         VARCHAR(20),
    origem_uf           VARCHAR(40),
    origem_cidade       VARCHAR(80),
    destino_data        VARCHAR(20),
    destino_uf          VARCHAR(40),
    destino_cidade      VARCHAR(80),
    meio_transporte     VARCHAR(50),
    numero_diarias      VARCHAR(30)
);
 
-- --------------------------------------------------------------------------- --
-- Bloco 4: tabelas SILVER — tipadas, com PK, FK e constraints extras
-- --------------------------------------------------------------------------- --
CREATE TABLE silver_viagem (
    id_viagem           VARCHAR(20)  CONSTRAINT pk_silver_viagem PRIMARY KEY,
    num_proposta        VARCHAR(20),
    situacao            VARCHAR(50),
    viagem_urgente      VARCHAR(5),
    cod_orgao_superior  VARCHAR(20),
    nome_orgao_superior VARCHAR(255) CONSTRAINT nn_silver_viagem_orgao NOT NULL,
    nome_viajante       VARCHAR(255),
    cargo               VARCHAR(255),
    data_inicio         DATE,
    data_fim            DATE,
    destinos            VARCHAR(4000),
    motivo              VARCHAR(4000),
    valor_diarias       DECIMAL(10, 2) CONSTRAINT ck_silver_viagem_diarias CHECK (valor_diarias >= 0),
    valor_passagens     DECIMAL(10, 2),
    valor_devolucao     DECIMAL(10, 2),
    valor_outros_gastos DECIMAL(10, 2),
    valor_total         DECIMAL(12, 2),
    duracao_dias        INT
);
 
CREATE TABLE silver_passagem (
    id_passagem         INT GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_silver_passagem PRIMARY KEY,
    id_viagem           VARCHAR(20) CONSTRAINT nn_silver_passagem_viagem NOT NULL
                        CONSTRAINT fk_silver_passagem_viagem REFERENCES silver_viagem (id_viagem),
    meio_transporte     VARCHAR(50),
    pais_origem_ida     VARCHAR(60),
    uf_origem_ida       VARCHAR(40),
    cidade_origem_ida   VARCHAR(80),
    pais_destino_ida    VARCHAR(60),
    uf_destino_ida      VARCHAR(40),
    cidade_destino_ida  VARCHAR(80),
    valor_passagem      DECIMAL(10, 2) CONSTRAINT ck_silver_passagem_valor CHECK (valor_passagem >= 0),
    taxa_servico        DECIMAL(10, 2) CONSTRAINT ck_silver_passagem_taxa CHECK (taxa_servico >= 0),
    data_emissao        DATE
);
 
CREATE TABLE silver_pagamento (
    id_pagamento        INT GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_silver_pagamento PRIMARY KEY,
    id_viagem           VARCHAR(20) CONSTRAINT nn_silver_pagamento_viagem NOT NULL
                        CONSTRAINT fk_silver_pagamento_viagem REFERENCES silver_viagem (id_viagem),
    num_proposta        VARCHAR(20),
    nome_orgao_pagador  VARCHAR(255),
    nome_ug_pagadora    VARCHAR(255),
    tipo_pagamento      VARCHAR(50) CONSTRAINT nn_silver_pagamento_tipo NOT NULL,
    valor               DECIMAL(10, 2) CONSTRAINT ck_silver_pagamento_valor CHECK (valor >= 0)
);
 
CREATE TABLE silver_trecho (
    id_trecho           INT GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_silver_trecho PRIMARY KEY,
    id_viagem           VARCHAR(20) CONSTRAINT nn_silver_trecho_viagem NOT NULL
                        CONSTRAINT fk_silver_trecho_viagem REFERENCES silver_viagem (id_viagem),
    sequencia_trecho    INT,
    origem_data         DATE,
    origem_uf           VARCHAR(40),
    origem_cidade       VARCHAR(80),
    destino_data        DATE,
    destino_uf          VARCHAR(40),
    destino_cidade      VARCHAR(80),
    meio_transporte     VARCHAR(50),
    numero_diarias      DECIMAL(10, 2) CONSTRAINT ck_silver_trecho_diarias CHECK (numero_diarias >= 0),
    CONSTRAINT uq_silver_trecho_viagem_sequencia UNIQUE (id_viagem, sequencia_trecho)
);
 
-- --------------------------------------------------------------------------- --
-- Bloco 5: checklist das 8 constraints extras da camada Silver
-- --------------------------------------------------------------------------- --
-- [ ] ck_silver_viagem_diarias      — valor_diarias >= 0
-- [ ] nn_silver_viagem_orgao        — nome_orgao_superior NOT NULL
-- [ ] ck_silver_passagem_valor      — valor_passagem >= 0
-- [ ] ck_silver_passagem_taxa       — taxa_servico >= 0
-- [ ] ck_silver_pagamento_valor     — valor >= 0
-- [ ] nn_silver_pagamento_tipo      — tipo_pagamento NOT NULL
-- [ ] ck_silver_trecho_diarias      — numero_diarias >= 0
-- [ ] uq_silver_trecho_viagem_sequencia — UNIQUE (id_viagem, sequencia_trecho)
