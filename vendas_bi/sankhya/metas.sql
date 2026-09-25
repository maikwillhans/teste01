-- Extração do "Resumo Geral das Metas/Vendas" direto do Sankhya.
-- Devolve as colunas da tabela fato_meta (ver layouts.py).
--
-- ATENÇÃO: MODELO para validar com o TI/consultor Sankhya. O resumo atual
-- provavelmente é um relatório personalizado; copie a SQL dele e ajuste os
-- "AS". Referência dos objetos padrão:
--   TGFMET  -> metas (CODMETA, DTREF, CODVEND, CODPROD, QTDPREV, VLRPREV...)
--   TGFCAB/TGFITE com TIPMOV = 'P' e PENDENTE = 'S' -> carteira ("Fechado")
--   TGFCAB/TGFITE com TIPMOV IN ('V','D')          -> realizado ("Vendido")
-- Parâmetros: :DTINI e :DTFIM (primeiro e último dia do mês).

WITH REAL AS (
    SELECT PAR.CODREG, ITE.CODPROD,
           SUM(CASE WHEN CAB.TIPMOV = 'D' THEN -1 ELSE 1 END * ITE.QTDNEG * NVL(PRO.PESOLIQ, 1)) AS QTD,
           SUM(CASE WHEN CAB.TIPMOV = 'D' THEN -1 ELSE 1 END * ITE.VLRTOT)                      AS VLR
    FROM TGFCAB CAB
    JOIN TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
    JOIN TGFPRO PRO ON PRO.CODPROD = ITE.CODPROD
    JOIN TGFPAR PAR ON PAR.CODPARC = CAB.CODPARC
    WHERE CAB.TIPMOV IN ('V', 'D') AND CAB.STATUSNOTA = 'L'
      AND CAB.CODTIPOPER NOT IN (501)                 -- bonificação não conta
      AND CAB.DTMOV BETWEEN :DTINI AND :DTFIM
    GROUP BY PAR.CODREG, ITE.CODPROD
),
CART AS (
    SELECT PAR.CODREG, ITE.CODPROD,
           SUM((ITE.QTDNEG - ITE.QTDENTREGUE) * NVL(PRO.PESOLIQ, 1))              AS QTD,
           SUM((ITE.QTDNEG - ITE.QTDENTREGUE) * ITE.VLRUNIT)                      AS VLR
    FROM TGFCAB CAB
    JOIN TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
    JOIN TGFPRO PRO ON PRO.CODPROD = ITE.CODPROD
    JOIN TGFPAR PAR ON PAR.CODPARC = CAB.CODPARC
    WHERE CAB.TIPMOV = 'P' AND ITE.PENDENTE = 'S'
    GROUP BY PAR.CODREG, ITE.CODPROD
)
SELECT
    REG.CODREG                                  AS codreg,
    REG.NOMEREG                                 AS nomereg,
    VEN.APELIDO                                 AS vendedor,
    CASE WHEN VEN.ATIVO = 'S' THEN 'Sim' ELSE 'Não' END AS vendedor_ativo,
    SUP.APELIDO                                 AS supervisor,
    GER.APELIDO                                 AS gerente,
    PRO.AD_MIXCOM                               AS categoria,
    MET.CODPROD                                 AS codprod,
    PRO.DESCRPROD                               AS descrprod,
    MET.QTDPREV                                 AS qtd_meta,
    CASE WHEN MET.QTDPREV > 0 THEN MET.VLRPREV / MET.QTDPREV ELSE 0 END AS pm_meta,
    NVL(R.QTD, 0)                               AS qtd_vendida,
    NVL(R.VLR, 0)                               AS vlr_faturado,
    NVL(C.QTD, 0)                               AS qtd_fechada,
    NVL(C.VLR, 0)                               AS vlr_fechado
FROM TGFMET MET
JOIN TGFPRO PRO ON PRO.CODPROD = MET.CODPROD
JOIN TGFVEN VEN ON VEN.CODVEND = MET.CODVEND
LEFT JOIN TSIREG REG ON REG.CODREG = VEN.AD_CODREG
LEFT JOIN TGFVEN SUP ON SUP.CODVEND = VEN.AD_CODSUPERVISOR
LEFT JOIN TGFVEN GER ON GER.CODVEND = VEN.CODGER
LEFT JOIN REAL R ON R.CODREG = REG.CODREG AND R.CODPROD = MET.CODPROD
LEFT JOIN CART C ON C.CODREG = REG.CODREG AND C.CODPROD = MET.CODPROD
WHERE MET.DTREF BETWEEN :DTINI AND :DTFIM
