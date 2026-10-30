-- ===========================================================================
-- gold_agregada.sql
-- Camada Gold do pipeline de viagens a servico (Portal da Transparencia).
-- Cria as VIEWs agregadas usadas pelo notebook 3_analise.ipynb.
-- Execucao: psql -U postgres -d transparencia -f sql/gold_agregada.sql
-- ===========================================================================
 
-- ---------------------------------------------------------------------------
-- VIEW 1: gastos por orgao superior
-- Grao: uma linha por orgao superior.
-- Fonte: silver_viagem (uma linha por viagem), portanto SUM(valor_total)
-- nao infla: cada viagem entra exatamente uma vez.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold_gastos_por_orgao AS
SELECT
    nome_orgao_superior,
    COUNT(*)                        AS qtd_viagens,
    SUM(valor_total)                AS valor_total_gasto,
    ROUND(AVG(valor_total), 2)      AS valor_medio_viagem,
    SUM(valor_diarias)              AS total_diarias,
    SUM(valor_passagens)            AS total_passagens,
    SUM(valor_devolucao)            AS total_devolucao,
    SUM(valor_outros_gastos)        AS total_outros_gastos,
    ROUND(AVG(duracao_dias), 1)     AS duracao_media_dias
FROM silver_viagem
GROUP BY nome_orgao_superior
ORDER BY valor_total_gasto DESC;
 
-- ---------------------------------------------------------------------------
-- VIEW 2: pagamentos por orgao pagador
-- Grao: uma linha por orgao pagador.
-- Fonte: silver_pagamento (uma linha por pagamento). Mantida separada da
-- VIEW 1 para nao cruzar graos diferentes e inflar as somas.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold_pagamentos_por_orgao AS
SELECT
    nome_orgao_pagador,
    COUNT(*)                        AS qtd_pagamentos,
    SUM(valor)                      AS valor_total_pago,
    ROUND(AVG(valor), 2)            AS valor_medio_pagamento,
    COUNT(DISTINCT tipo_pagamento)  AS tipos_distintos
FROM silver_pagamento
GROUP BY nome_orgao_pagador
ORDER BY valor_total_pago DESC;
 
-- ---------------------------------------------------------------------------
-- VIEW 3: gastos por destino
-- Grao: uma linha por destino. Usa a primeira cidade do campo destinos,
-- que pode conter varios destinos separados por virgula.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold_gastos_por_destino AS
SELECT
    TRIM(SPLIT_PART(destinos, ',', 1))  AS destino_principal,
    COUNT(*)                            AS qtd_viagens,
    SUM(valor_total)                    AS valor_total_gasto,
    ROUND(AVG(valor_total), 2)          AS valor_medio_viagem
FROM silver_viagem
WHERE destinos IS NOT NULL
GROUP BY TRIM(SPLIT_PART(destinos, ',', 1))
ORDER BY valor_total_gasto DESC;
