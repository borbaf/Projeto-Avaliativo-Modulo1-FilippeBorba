# Projeto Avaliativo Módulo 1 — Pipeline de Dados com Arquitetura Medallion
 
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![Docker](https://img.shields.io/badge/Docker-enabled-2496ED)
![Licença](https://img.shields.io/badge/Licen%C3%A7a-Educacional-lightgrey)
 
## Sobre o projeto
 
Este projeto implementa um pipeline de dados completo para analisar os gastos
com viagens a serviço do governo federal, a partir dos dados abertos
publicados no Portal da Transparência. Os dados brutos são ingeridos,
higienizados e organizados em um banco PostgreSQL seguindo a arquitetura
Medallion, respondendo 7 perguntas de negócio sobre custos, órgãos, destinos,
tipos de pagamento e duração das viagens.
 
## Arquitetura
 
O projeto segue a arquitetura Medallion, com três camadas de refinamento
progressivo dos dados:
 
| Camada | Papel |
| --- | --- |
| Raw (Bronze) | Ingestão fiel ao CSV de origem: todas as colunas VARCHAR, sem constraints, preservando 100% das linhas recebidas. |
| Silver | Dados tipados e higienizados, com PK, FK e constraints extras garantindo integridade e qualidade. |
| Gold | Camada analítica: visões e agregações prontas para responder às perguntas de negócio. |
 
## Estrutura do repositório
 
```
Projeto-Avaliativo-Modulo1-FilippeBorba/
├── .env.example
├── .gitignore
├── README.md
├── config.py
├── banco.py
├── 0_criar_banco.sql
├── 1_extrair.py
├── 2_transformar.py
├── 3_analise.ipynb
├── docker-compose.yml
├── requirements.txt
├── data/
│   ├── raw/
│   ├── amostras/
│   └── gold/
└── logs/
```
 
## Tecnologias utilizadas
 
| Tecnologia | Uso no projeto |
| --- | --- |
| Python 3.10+ | Linguagem principal do pipeline |
| PostgreSQL 16 | Banco de dados das camadas Raw/Silver/Gold |
| psycopg2 | Driver de conexão e carga no PostgreSQL |
| pandas | Manipulação e transformação dos dados |
| matplotlib | Geração de gráficos |
| seaborn | Visualizações estatísticas |
| Docker | Container do PostgreSQL |
| gdown | Download automatizado do zip do Drive |
| Git | Versionamento do código |
 
## Como executar
 
1. **Pré-requisitos**: Python 3.10+, Docker instalado e Git.
2. Clone o repositório: `git clone <url-do-repositorio>`.
3. Crie o ambiente virtual: `python -m venv .venv` e ative-o
   (`source .venv/bin/activate` no Linux/macOS ou `.venv\Scripts\activate` no Windows).
4. Instale as dependências: `pip install -r requirements.txt`.
5. Configure o `.env`: copie `.env.example` para `.env` e preencha as credenciais do PostgreSQL.
6. Suba o Docker: `docker compose up -d` (cria o database `transparencia` via `POSTGRES_DB`).
7. Crie o schema: rode `0_criar_banco.sql` no banco (psql, DBeaver ou pgAdmin).
8. Execute a extração e carga RAW: `python 1_extrair.py`.
9. Execute as transformações Silver/Gold: `python 2_transformar.py`.
10. Abra e execute o notebook de análise: `3_analise.ipynb` (Jupyter ou VS Code).
 
## Fonte dos dados
 
Os dados vêm do Portal da Transparência do governo federal, no arquivo
`viagens_2025_6meses.zip`, que contém 4 CSVs: Viagem, Pagamento, Passagem e
Trecho. Os arquivos usam separador ponto e vírgula (`;`) e encoding `latin-1`.
O download é automatizado pelo `1_extrair.py`, que busca o arquivo oficial no
Drive do curso pelo id registrado em `config.py` (DRIVE_FILE_ID).
 
## Modelo de dados
 
| Tabela | Grão |
| --- | --- |
| raw_viagem | 1 linha por viagem, como no CSV original |
| raw_pagamento | 1 linha por pagamento de viagem, como no CSV original |
| raw_passagem | 1 linha por passagem, como no CSV original |
| raw_trecho | 1 linha por trecho de viagem, como no CSV original |
| silver_viagem | 1 linha por viagem, tipada e com PK |
| silver_passagem | 1 linha por passagem, com FK para silver_viagem |
| silver_pagamento | 1 linha por pagamento, com FK para silver_viagem |
| silver_trecho | 1 linha por trecho, com FK e UNIQUE (id_viagem, sequencia_trecho) |
 
## Decisões técnicas
 
- **Raw sem constraints**: a camada Raw deve receber 100% das linhas do CSV,
  sem risco de rejeição por tipagem ou integridade — qualquer problema é
  tratado na Silver.
- **TRUNCATE antes da carga**: garante idempotência — rodar o pipeline várias
  vezes produz sempre o mesmo estado do banco, sem duplicar linhas.
- **information_schema**: as colunas do INSERT são lidas do próprio banco,
  evitando hardcode e mantendo o código aderente ao DDL.
- **Amostras em modo binário**: preservam os bytes originais dos CSVs,
  mantendo a fidelidade ao encoding latin-1 para inspeção segura.
 
## Melhorias futuras
 
- Ingestão incremental via API de Dados Abertos do Portal da Transparência.
- Orquestração do pipeline com Apache Airflow.
- Testes automatizados com pytest.
- Dashboard interativo com Streamlit.
 
## Autor
 
**Filippe Borba** — [github.com/borbaf](https://github.com/borbaf)
 
## Licença
 
Projeto de uso educacional, desenvolvido no curso de Análise de Dados do SENAI.
