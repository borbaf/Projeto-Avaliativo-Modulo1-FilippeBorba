#!/usr/bin/env bash
#
# setup.sh
# Automatiza a preparacao completa do ambiente e a execucao do pipeline
# de dados de viagens a servico (Portal da Transparencia).
#
# Uso:
#   chmod +x setup.sh
#   ./setup.sh              # executa tudo
#   ./setup.sh --sem-docker # usa PostgreSQL local em vez de Docker
#   ./setup.sh --so-testes  # apenas roda os testes
#
# Requisitos: Python 3.10+, Git, Docker (opcional) ou PostgreSQL local.

set -euo pipefail

# --------------------------------------------------------------------------- #
# Configuracao
# --------------------------------------------------------------------------- #
VERDE='\033[0;32m'
AMARELO='\033[1;33m'
VERMELHO='\033[0;31m'
SEM_COR='\033[0m'

NOME_CONTAINER="transparencia_postgres"
NOME_BANCO="transparencia"
PORTA_PADRAO="5432"
ARQUIVO_ENV=".env"
ARQUIVO_ENV_EXEMPLO=".env.example"
ARQUIVO_DDL="0_criar_banco.sql"

USAR_DOCKER=true
SO_TESTES=false

# --------------------------------------------------------------------------- #
# Funcoes auxiliares
# --------------------------------------------------------------------------- #
info() {
    echo -e "${VERDE}[INFO]${SEM_COR} $*"
}

aviso() {
    echo -e "${AMARELO}[AVISO]${SEM_COR} $*"
}

erro() {
    echo -e "${VERMELHO}[ERRO]${SEM_COR} $*" >&2
}

falhar() {
    erro "$*"
    exit 1
}

verificar_comando() {
    if ! command -v "$1" >/dev/null 2>&1; then
        falhar "Comando '$1' nao encontrado. Instale antes de continuar."
    fi
}

# --------------------------------------------------------------------------- #
# Parse de argumentos
# --------------------------------------------------------------------------- #
while [[ $# -gt 0 ]]; do
    case "$1" in
        --sem-docker)
            USAR_DOCKER=false
            shift
            ;;
        --so-testes)
            SO_TESTES=true
            shift
            ;;
        -h|--help)
            echo "Uso: $0 [--sem-docker] [--so-testes]"
            exit 0
            ;;
        *)
            falhar "Argumento desconhecido: $1"
            ;;
    esac
done

# --------------------------------------------------------------------------- #
# Etapa 1 - Verificacoes de ambiente
# --------------------------------------------------------------------------- #
verificar_ambiente() {
    info "Verificando pre-requisitos..."

    verificar_comando python3
    verificar_comando git

    local versao_python
    versao_python=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

    if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
        falhar "Python 3.10+ requerido. Encontrado: ${versao_python}"
    fi

    info "Python ${versao_python} OK"

    if [[ "${USAR_DOCKER}" == true ]]; then
        verificar_comando docker
        info "Docker OK"
    else
        verificar_comando psql
        info "psql OK"
    fi
}

# --------------------------------------------------------------------------- #
# Etapa 2 - Ambiente virtual
# --------------------------------------------------------------------------- #
criar_venv() {
    if [[ -d ".venv" ]]; then
        info "Ambiente virtual ja existe, reaproveitando."
    else
        info "Criando ambiente virtual..."
        python3 -m venv .venv
    fi

    # shellcheck disable=SC1091
    source .venv/bin/activate
    info "Ambiente virtual ativado."
}

# --------------------------------------------------------------------------- #
# Etapa 3 - Dependencias
# --------------------------------------------------------------------------- #
instalar_dependencias() {
    info "Atualizando pip..."
    python -m pip install --upgrade pip --quiet

    info "Instalando dependencias do requirements.txt..."
    python -m pip install -r requirements.txt --quiet

    info "Dependencias instaladas."
}

# --------------------------------------------------------------------------- #
# Etapa 4 - Credenciais
# --------------------------------------------------------------------------- #
configurar_env() {
    if [[ -f "${ARQUIVO_ENV}" ]]; then
        info "Arquivo .env ja existe, mantendo."
        return
    fi

    if [[ ! -f "${ARQUIVO_ENV_EXEMPLO}" ]]; then
        falhar "${ARQUIVO_ENV_EXEMPLO} nao encontrado."
    fi

    info "Criando .env a partir do modelo..."
    cp "${ARQUIVO_ENV_EXEMPLO}" "${ARQUIVO_ENV}"

    aviso "Edite o arquivo .env e preencha POSTGRES_PASSWORD antes de continuar."
    aviso "Depois rode novamente: ./setup.sh"
    exit 0
}

# --------------------------------------------------------------------------- #
# Etapa 5 - PostgreSQL
# --------------------------------------------------------------------------- #
subir_postgres_docker() {
    if docker ps --format '{{.Names}}' | grep -q "^${NOME_CONTAINER}$"; then
        info "Container ${NOME_CONTAINER} ja esta rodando."
        return
    fi

    if docker ps -a --format '{{.Names}}' | grep -q "^${NOME_CONTAINER}$"; then
        info "Iniciando container existente..."
        docker start "${NOME_CONTAINER}" >/dev/null
    else
        info "Criando container PostgreSQL..."
        docker run -d \
            --name "${NOME_CONTAINER}" \
            -e POSTGRES_PASSWORD=postgres \
            -e POSTGRES_DB="${NOME_BANCO}" \
            -p "${PORTA_PADRAO}:5432" \
            postgres:16 >/dev/null
    fi

    info "Aguardando o banco aceitar conexoes..."
    local tentativas=0
    until docker exec "${NOME_CONTAINER}" pg_isready -U postgres >/dev/null 2>&1; do
        tentativas=$((tentativas + 1))
        if [[ ${tentativas} -ge 30 ]]; then
            falhar "Banco nao respondeu em 30 segundos."
        fi
        sleep 1
    done

    info "PostgreSQL pronto."
}

verificar_postgres_local() {
    info "Verificando PostgreSQL local..."
    if ! psql -h localhost -U postgres -d "${NOME_BANCO}" -c 'SELECT 1' >/dev/null 2>&1; then
        falhar "Nao foi possivel conectar ao banco '${NOME_BANCO}'. Crie o banco manualmente."
    fi
    info "PostgreSQL local OK."
}

# --------------------------------------------------------------------------- #
# Etapa 6 - DDL
# --------------------------------------------------------------------------- #
criar_tabelas() {
    if [[ ! -f "${ARQUIVO_DDL}" ]]; then
        falhar "${ARQUIVO_DDL} nao encontrado."
    fi

    info "Criando as 8 tabelas..."

    if [[ "${USAR_DOCKER}" == true ]]; then
        docker exec -i "${NOME_CONTAINER}" \
            psql -U postgres -d "${NOME_BANCO}" < "${ARQUIVO_DDL}" >/dev/null
    else
        psql -h localhost -U postgres -d "${NOME_BANCO}" -f "${ARQUIVO_DDL}" >/dev/null
    fi

    info "Tabelas criadas."
}

# --------------------------------------------------------------------------- #
# Etapa 7 - Pipeline
# --------------------------------------------------------------------------- #
executar_pipeline() {
    info "Fase 1: extracao e carga da camada Raw..."
    python 1_extrair.py

    info "Fase 2: transformacao Raw para Silver..."
    python 2_transformar.py

    info "Fase 3: analise Gold..."
    if command -v jupyter >/dev/null 2>&1; then
        jupyter nbconvert --to notebook --execute --inplace 3_analise.ipynb
        info "Notebook executado."
    else
        aviso "Jupyter nao encontrado. Execute 3_analise.ipynb manualmente."
    fi
}

# --------------------------------------------------------------------------- #
# Etapa 8 - Testes
# --------------------------------------------------------------------------- #
executar_testes() {
    info "Rodando os 54 testes end-to-end..."
    python -m pytest tests/ -v
}

# --------------------------------------------------------------------------- #
# Fluxo principal
# --------------------------------------------------------------------------- #
main() {
    echo ""
    echo "=============================================="
    echo " Pipeline de Viagens a Servico - Setup"
    echo "=============================================="
    echo ""

    if [[ "${SO_TESTES}" == true ]]; then
        criar_venv
        executar_testes
        info "Concluido."
        exit 0
    fi

    verificar_ambiente
    criar_venv
    instalar_dependencias
    configurar_env

    if [[ "${USAR_DOCKER}" == true ]]; then
        subir_postgres_docker
    else
        verificar_postgres_local
    fi

    criar_tabelas
    executar_pipeline
    executar_testes

    echo ""
    info "Pipeline concluido com sucesso."
    echo ""
}

main "$@"