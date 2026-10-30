<#
.SYNOPSIS
    Automatiza a preparacao do ambiente e a execucao do pipeline de dados
    de viagens a servico (Portal da Transparencia).

.DESCRIPTION
    Executa a sequencia completa: verifica pre-requisitos, cria o ambiente
    virtual, instala dependencias, sobe o PostgreSQL, cria as tabelas,
    roda o pipeline e executa os testes.

.PARAMETER SemDocker
    Usa PostgreSQL local em vez de subir um container Docker.

.PARAMETER SoTestes
    Apenas roda os testes, assumindo que o ambiente ja esta configurado.

.EXAMPLE
    .\setup.ps1

.EXAMPLE
    .\setup.ps1 -SemDocker

.EXAMPLE
    .\setup.ps1 -SoTestes
#>
[CmdletBinding()]
param(
    [switch]$SemDocker,
    [switch]$SoTestes
)

$ErrorActionPreference = "Stop"

# --------------------------------------------------------------------------- #
# Configuracao
# --------------------------------------------------------------------------- #
$NomeContainer = "transparencia_postgres"
$NomeBanco = "transparencia"
$PortaPadrao = "5432"
$ArquivoEnv = ".env"
$ArquivoEnvExemplo = ".env.example"
$ArquivoDdl = "0_criar_banco.sql"

$UsarDocker = -not $SemDocker

# --------------------------------------------------------------------------- #
# Funcoes auxiliares
# --------------------------------------------------------------------------- #
function Write-Info {
    param([string]$Mensagem)
    Write-Host "[INFO] $Mensagem" -ForegroundColor Green
}

function Write-Aviso {
    param([string]$Mensagem)
    Write-Host "[AVISO] $Mensagem" -ForegroundColor Yellow
}

function Write-Erro {
    param([string]$Mensagem)
    Write-Host "[ERRO] $Mensagem" -ForegroundColor Red
}

function Stop-ComErro {
    param([string]$Mensagem)
    Write-Erro $Mensagem
    exit 1
}

function Test-Comando {
    param([string]$Nome)
    if (-not (Get-Command $Nome -ErrorAction SilentlyContinue)) {
        Stop-ComErro "Comando '$Nome' nao encontrado. Instale antes de continuar."
    }
}

# --------------------------------------------------------------------------- #
# Etapa 1 - Verificacoes de ambiente
# --------------------------------------------------------------------------- #
function Test-Ambiente {
    Write-Info "Verificando pre-requisitos..."

    Test-Comando "python"
    Test-Comando "git"

    $versaoPython = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"

    $versaoOk = python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
    if ($LASTEXITCODE -ne 0) {
        Stop-ComErro "Python 3.10+ requerido. Encontrado: $versaoPython"
    }

    Write-Info "Python $versaoPython OK"

    if ($UsarDocker) {
        Test-Comando "docker"
        Write-Info "Docker OK"
    }
    else {
        Test-Comando "psql"
        Write-Info "psql OK"
    }
}

# --------------------------------------------------------------------------- #
# Etapa 2 - Ambiente virtual
# --------------------------------------------------------------------------- #
function New-AmbienteVirtual {
    if (Test-Path ".venv") {
        Write-Info "Ambiente virtual ja existe, reaproveitando."
    }
    else {
        Write-Info "Criando ambiente virtual..."
        python -m venv .venv
    }

    $script:PythonExe = Join-Path (Get-Location) ".venv\Scripts\python.exe"
    $script:PipExe = Join-Path (Get-Location) ".venv\Scripts\pip.exe"

    if (-not (Test-Path $script:PythonExe)) {
        Stop-ComErro "Python do ambiente virtual nao encontrado em $script:PythonExe"
    }

    Write-Info "Ambiente virtual pronto."
}

# --------------------------------------------------------------------------- #
# Etapa 3 - Dependencias
# --------------------------------------------------------------------------- #
function Install-Dependencias {
    Write-Info "Atualizando pip..."
    & $script:PythonExe -m pip install --upgrade pip --quiet

    Write-Info "Instalando dependencias do requirements.txt..."
    & $script:PythonExe -m pip install -r requirements.txt --quiet

    Write-Info "Dependencias instaladas."
}

# --------------------------------------------------------------------------- #
# Etapa 4 - Credenciais
# --------------------------------------------------------------------------- #
function Set-Env {
    if (Test-Path $ArquivoEnv) {
        Write-Info "Arquivo .env ja existe, mantendo."
        return
    }

    if (-not (Test-Path $ArquivoEnvExemplo)) {
        Stop-ComErro "$ArquivoEnvExemplo nao encontrado."
    }

    Write-Info "Criando .env a partir do modelo..."
    Copy-Item $ArquivoEnvExemplo $ArquivoEnv

    Write-Aviso "Edite o arquivo .env e preencha POSTGRES_PASSWORD antes de continuar."
    Write-Aviso "Depois rode novamente: .\setup.ps1"
    exit 0
}

# --------------------------------------------------------------------------- #
# Etapa 5 - PostgreSQL
# --------------------------------------------------------------------------- #
function Start-PostgresDocker {
    $containersRodando = docker ps --format "{{.Names}}"
    if ($containersRodando -contains $NomeContainer) {
        Write-Info "Container $NomeContainer ja esta rodando."
        return
    }

    $containersExistentes = docker ps -a --format "{{.Names}}"
    if ($containersExistentes -contains $NomeContainer) {
        Write-Info "Iniciando container existente..."
        docker start $NomeContainer | Out-Null
    }
    else {
        Write-Info "Criando container PostgreSQL..."
        docker run -d `
            --name $NomeContainer `
            -e POSTGRES_PASSWORD=postgres `
            -e POSTGRES_DB=$NomeBanco `
            -p "${PortaPadrao}:5432" `
            postgres:16 | Out-Null
    }

    Write-Info "Aguardando o banco aceitar conexoes..."
    $tentativas = 0
    while ($true) {
        docker exec $NomeContainer pg_isready -U postgres 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            break
        }

        $tentativas++
        if ($tentativas -ge 30) {
            Stop-ComErro "Banco nao respondeu em 30 segundos."
        }
        Start-Sleep -Seconds 1
    }

    Write-Info "PostgreSQL pronto."
}

function Test-PostgresLocal {
    Write-Info "Verificando PostgreSQL local..."
    $env:PGPASSWORD = $env:POSTGRES_PASSWORD
    psql -h localhost -U postgres -d $NomeBanco -c "SELECT 1" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Stop-ComErro "Nao foi possivel conectar ao banco '$NomeBanco'. Crie o banco manualmente."
    }
    Write-Info "PostgreSQL local OK."
}

# --------------------------------------------------------------------------- #
# Etapa 6 - DDL
# --------------------------------------------------------------------------- #
function New-Tabelas {
    if (-not (Test-Path $ArquivoDdl)) {
        Stop-ComErro "$ArquivoDdl nao encontrado."
    }

    Write-Info "Criando as 8 tabelas..."

    if ($UsarDocker) {
        Get-Content $ArquivoDdl -Raw | docker exec -i $NomeContainer psql -U postgres -d $NomeBanco | Out-Null
    }
    else {
        psql -h localhost -U postgres -d $NomeBanco -f $ArquivoDdl | Out-Null
    }

    if ($LASTEXITCODE -ne 0) {
        Stop-ComErro "Falha ao criar as tabelas."
    }

    Write-Info "Tabelas criadas."
}

# --------------------------------------------------------------------------- #
# Etapa 7 - Pipeline
# --------------------------------------------------------------------------- #
function Invoke-Pipeline {
    Write-Info "Fase 1: extracao e carga da camada Raw..."
    & $script:PythonExe 1_extrair.py
    if ($LASTEXITCODE -ne 0) {
        Stop-ComErro "Falha na extracao."
    }

    Write-Info "Fase 2: transformacao Raw para Silver..."
    & $script:PythonExe 2_transformar.py
    if ($LASTEXITCODE -ne 0) {
        Stop-ComErro "Falha na transformacao."
    }

    Write-Info "Fase 3: analise Gold..."
    & $script:PythonExe -m jupyter nbconvert --to notebook --execute --inplace 3_analise.ipynb
    if ($LASTEXITCODE -ne 0) {
        Write-Aviso "Falha ao executar o notebook. Execute 3_analise.ipynb manualmente."
    }
    else {
        Write-Info "Notebook executado."
    }
}

# --------------------------------------------------------------------------- #
# Etapa 8 - Testes
# --------------------------------------------------------------------------- #
function Invoke-Testes {
    Write-Info "Rodando os 54 testes end-to-end..."
    & $script:PythonExe -m pytest tests/ -v
    if ($LASTEXITCODE -ne 0) {
        Stop-ComErro "Testes falharam."
    }
}

# --------------------------------------------------------------------------- #
# Fluxo principal
# --------------------------------------------------------------------------- #
function Invoke-Main {
    Write-Host ""
    Write-Host "=============================================="
    Write-Host " Pipeline de Viagens a Servico - Setup"
    Write-Host "=============================================="
    Write-Host ""

    if ($SoTestes) {
        New-AmbienteVirtual
        Invoke-Testes
        Write-Info "Concluido."
        return
    }

    Test-Ambiente
    New-AmbienteVirtual
    Install-Dependencias
    Set-Env

    if ($UsarDocker) {
        Start-PostgresDocker
    }
    else {
        Test-PostgresLocal
    }

    New-Tabelas
    Invoke-Pipeline
    Invoke-Testes

    Write-Host ""
    Write-Info "Pipeline concluido com sucesso."
    Write-Host ""
}

Invoke-Main