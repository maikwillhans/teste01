-- =====================================================================================
-- ITENS FOCO DO MÊS — acompanhamento meta x previsto x realizado x pedidos do dia (Oracle)
-- SOMENTE LEITURA. Rode cada consulta (A, B, C, D) separadamente.
--
-- Regras, tiradas das planilhas que já conferimos (Demonstrativo e Resumo de Metas 09/2026):
--   * Realizado = vendas + devoluções (devolução entra negativa), bonificação (TOP 501) fica fora.
--     TOPs do Demonstrativo: venda 500, 504, 506, 512, 513 | devolução 240, 241, 252, 253.
--   * Data do realizado = TGFCAB.DTMOV (coluna "Data Mvto" do Demonstrativo). Nota confirmada: STATUSNOTA = 'L'.
--   * Quantidade em kg: QTDNEG quando o volume é KG, nos demais volumes, QTDNEG x peso líquido do produto.
--   * Pedido = TGFCAB.TIPMOV = 'P', data do pedido = DTNEG. Carteira = pedidos pendentes (QTDNEG - QTDENTREGUE).
--   * Previsto até hoje = meta x dias úteis decorridos / dias úteis do mês (segunda a sábado, sem feriados),
--     o mesmo ritmo usado no painel.
--
-- Data de referência: SYSDATE (hoje). Para olhar outro mês, troque SYSDATE por uma data fixa
-- em todo o texto (Ctrl+H), por exemplo  DATE '2026-09-30'.
--
-- Metas: a tabela de metas do Sankhya (TGFMET) está zerada nesta base, então a meta de cada item
-- é digitada no bloco "F" abaixo. Os valores de exemplo são as metas de 09/2026 do Resumo Geral
-- das Metas/Vendas (soma de todos os vendedores). Atualize a cada mês.
-- =====================================================================================


-- -------------------------------------------------------------------------------------
-- A) ACOMPANHAMENTO POR ITEM
-- -------------------------------------------------------------------------------------
SELECT F.ORDEM,
       F.CODPROD,
       PRO.DESCRPROD,
       F.META_KG,
       ROUND(F.META_KG * D.DIAS_DECORRIDOS / D.DIAS_UTEIS, 1)                         AS PREVISTO_ATE_HOJE_KG,
       ROUND(NVL(R.KG_MES, 0), 1)                                                     AS REALIZADO_KG,
       ROUND(NVL(R.VLR_MES, 0), 2)                                                    AS REALIZADO_VLR,
       ROUND(100 * NVL(R.KG_MES, 0) / NULLIF(F.META_KG, 0), 1)                         AS PERC_META,
       ROUND(100 * NVL(R.KG_MES, 0) / NULLIF(F.META_KG * D.DIAS_DECORRIDOS / D.DIAS_UTEIS, 0), 1) AS PERC_DO_PREVISTO,
       ROUND(NVL(R.KG_HOJE, 0), 1)                                                    AS FATURADO_HOJE_KG,
       NVL(P.PEDIDOS_HOJE, 0)                                                         AS PEDIDOS_HOJE,
       NVL(P.CLIENTES_HOJE, 0)                                                        AS CLIENTES_PEDIDO_HOJE,
       ROUND(NVL(P.KG_HOJE, 0), 1)                                                    AS PEDIDO_HOJE_KG,
       ROUND(NVL(P.VLR_HOJE, 0), 2)                                                   AS PEDIDO_HOJE_VLR,
       NVL(P.PEDIDOS_MES, 0)                                                          AS PEDIDOS_MES,
       ROUND(NVL(C.KG_CARTEIRA, 0), 1)                                                AS CARTEIRA_KG,
       ROUND(NVL(R.KG_MES, 0) + NVL(C.KG_CARTEIRA, 0), 1)                             AS PROJECAO_KG,
       ROUND(GREATEST(F.META_KG - NVL(R.KG_MES, 0) - NVL(C.KG_CARTEIRA, 0), 0), 1)    AS FALTA_KG,
       ROUND(GREATEST(F.META_KG - NVL(R.KG_MES, 0) - NVL(C.KG_CARTEIRA, 0), 0)
             / NULLIF(D.DIAS_UTEIS - D.DIAS_DECORRIDOS, 0), 1)                         AS NECESSARIO_POR_DIA_KG,
       D.DIAS_DECORRIDOS || ' de ' || D.DIAS_UTEIS                                     AS DIAS_UTEIS
FROM (
        -- >>> ITENS FOCO E META DO MÊS (kg) — edite aqui <<<
        SELECT 1 ORDEM, 90346 CODPROD,  68611 META_KG FROM DUAL UNION ALL   -- PERNIL DEFUMADO
        SELECT 2,         871,         324666         FROM DUAL UNION ALL   -- BACON MANTA
        SELECT 3,       32537,          30653         FROM DUAL UNION ALL   -- BACON EM PEDACOS
        SELECT 4,        3465,          30000         FROM DUAL UNION ALL   -- LINGUICA TOSCANA - 600G
        SELECT 5,         949,         939850         FROM DUAL UNION ALL   -- LINGUICA TOSCANA 5 KG
        SELECT 6,       85847,         339517         FROM DUAL UNION ALL   -- PRESUNTO EXCELENCIA
        SELECT 7,       11145,         109010         FROM DUAL             -- PRESUNTO RETANGULAR - FOOD SERVICE
     ) F
CROSS JOIN (
        SELECT SUM(CASE WHEN TO_CHAR(DIA, 'DY', 'NLS_DATE_LANGUAGE=ENGLISH') <> 'SUN' THEN 1 ELSE 0 END) AS DIAS_UTEIS,
               SUM(CASE WHEN TO_CHAR(DIA, 'DY', 'NLS_DATE_LANGUAGE=ENGLISH') <> 'SUN'
                         AND DIA <= TRUNC(SYSDATE) THEN 1 ELSE 0 END)                          AS DIAS_DECORRIDOS
        FROM (SELECT TRUNC(SYSDATE, 'MM') + LEVEL - 1 AS DIA FROM DUAL
              CONNECT BY LEVEL <= TO_NUMBER(TO_CHAR(LAST_DAY(SYSDATE), 'DD')))
     ) D
JOIN TGFPRO PRO ON PRO.CODPROD = F.CODPROD
LEFT JOIN (   -- realizado do mês (notas)
        SELECT ITE.CODPROD,
               SUM(SG.S * CASE WHEN ITE.CODVOL = 'KG' THEN ITE.QTDNEG ELSE ITE.QTDNEG * NVL(NULLIF(PR.PESOLIQ, 0), 1) END) AS KG_MES,
               SUM(SG.S * ITE.VLRTOT)                                                                                   AS VLR_MES,
               SUM(CASE WHEN TRUNC(CAB.DTMOV) = TRUNC(SYSDATE) THEN
                   SG.S * CASE WHEN ITE.CODVOL = 'KG' THEN ITE.QTDNEG ELSE ITE.QTDNEG * NVL(NULLIF(PR.PESOLIQ, 0), 1) END END) AS KG_HOJE
        FROM TGFCAB CAB
        JOIN TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
        JOIN TGFPRO PR  ON PR.CODPROD = ITE.CODPROD
        JOIN (SELECT 'V' T, 1 S FROM DUAL UNION ALL SELECT 'D', -1 FROM DUAL) SG ON SG.T = CAB.TIPMOV
        WHERE CAB.DTMOV >= TRUNC(SYSDATE, 'MM') AND CAB.DTMOV < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), 1)
          AND CAB.STATUSNOTA = 'L'
          AND CAB.CODTIPOPER IN (500, 504, 506, 512, 513, 240, 241, 252, 253)
          AND ITE.CODPROD IN (90346, 871, 32537, 3465, 949, 85847, 11145)
        GROUP BY ITE.CODPROD
     ) R ON R.CODPROD = F.CODPROD
LEFT JOIN (   -- pedidos de hoje e do mês
        SELECT ITE.CODPROD,
               COUNT(DISTINCT CASE WHEN TRUNC(CAB.DTNEG) = TRUNC(SYSDATE) THEN CAB.NUNOTA END)  AS PEDIDOS_HOJE,
               COUNT(DISTINCT CASE WHEN TRUNC(CAB.DTNEG) = TRUNC(SYSDATE) THEN CAB.CODPARC END) AS CLIENTES_HOJE,
               SUM(CASE WHEN TRUNC(CAB.DTNEG) = TRUNC(SYSDATE) THEN
                   CASE WHEN ITE.CODVOL = 'KG' THEN ITE.QTDNEG ELSE ITE.QTDNEG * NVL(NULLIF(PR.PESOLIQ, 0), 1) END END) AS KG_HOJE,
               SUM(CASE WHEN TRUNC(CAB.DTNEG) = TRUNC(SYSDATE) THEN ITE.VLRTOT END)              AS VLR_HOJE,
               COUNT(DISTINCT CAB.NUNOTA)                                                         AS PEDIDOS_MES
        FROM TGFCAB CAB
        JOIN TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
        JOIN TGFPRO PR  ON PR.CODPROD = ITE.CODPROD
        WHERE CAB.TIPMOV = 'P'
          AND CAB.DTNEG >= TRUNC(SYSDATE, 'MM') AND CAB.DTNEG < TRUNC(SYSDATE) + 1
          AND ITE.CODPROD IN (90346, 871, 32537, 3465, 949, 85847, 11145)
        GROUP BY ITE.CODPROD
     ) P ON P.CODPROD = F.CODPROD
LEFT JOIN (   -- carteira: pedidos ainda pendentes (qualquer data de pedido)
        SELECT ITE.CODPROD,
               SUM(CASE WHEN ITE.CODVOL = 'KG' THEN ITE.QTDNEG - NVL(ITE.QTDENTREGUE, 0)
                        ELSE (ITE.QTDNEG - NVL(ITE.QTDENTREGUE, 0)) * NVL(NULLIF(PR.PESOLIQ, 0), 1) END) AS KG_CARTEIRA
        FROM TGFCAB CAB
        JOIN TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
        JOIN TGFPRO PR  ON PR.CODPROD = ITE.CODPROD
        WHERE CAB.TIPMOV = 'P' AND CAB.PENDENTE = 'S' AND ITE.PENDENTE = 'S'
          AND ITE.CODPROD IN (90346, 871, 32537, 3465, 949, 85847, 11145)
        GROUP BY ITE.CODPROD
     ) C ON C.CODPROD = F.CODPROD
ORDER BY F.ORDEM;


-- -------------------------------------------------------------------------------------
-- B) POR ITEM E VENDEDOR (sem meta: a meta por vendedor não está no banco)
-- -------------------------------------------------------------------------------------
SELECT X.CODPROD, PRO.DESCRPROD, X.CODVEND, VEN.APELIDO AS VENDEDOR,
       ROUND(SUM(X.KG_MES), 1)        AS REALIZADO_KG,
       ROUND(SUM(X.VLR_MES), 2)       AS REALIZADO_VLR,
       SUM(X.PEDIDOS_HOJE)            AS PEDIDOS_HOJE,
       ROUND(SUM(X.PEDIDO_HOJE_KG), 1) AS PEDIDO_HOJE_KG,
       ROUND(SUM(X.CARTEIRA_KG), 1)   AS CARTEIRA_KG
FROM (
        SELECT ITE.CODPROD, CAB.CODVEND,
               CASE WHEN CAB.TIPMOV = 'D' THEN -1 ELSE 1 END
                 * CASE WHEN ITE.CODVOL = 'KG' THEN ITE.QTDNEG ELSE ITE.QTDNEG * NVL(NULLIF(PR.PESOLIQ, 0), 1) END AS KG_MES,
               CASE WHEN CAB.TIPMOV = 'D' THEN -1 ELSE 1 END * ITE.VLRTOT AS VLR_MES,
               0 PEDIDOS_HOJE, 0 PEDIDO_HOJE_KG, 0 CARTEIRA_KG
        FROM TGFCAB CAB JOIN TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA JOIN TGFPRO PR ON PR.CODPROD = ITE.CODPROD
        WHERE CAB.DTMOV >= TRUNC(SYSDATE, 'MM') AND CAB.DTMOV < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), 1)
          AND CAB.TIPMOV IN ('V', 'D') AND CAB.STATUSNOTA = 'L'
          AND CAB.CODTIPOPER IN (500, 504, 506, 512, 513, 240, 241, 252, 253)
          AND ITE.CODPROD IN (90346, 871, 32537, 3465, 949, 85847, 11145)
        UNION ALL
        SELECT ITE.CODPROD, CAB.CODVEND, 0, 0,
               CASE WHEN TRUNC(CAB.DTNEG) = TRUNC(SYSDATE) THEN 1 ELSE 0 END,
               CASE WHEN TRUNC(CAB.DTNEG) = TRUNC(SYSDATE) THEN
                    CASE WHEN ITE.CODVOL = 'KG' THEN ITE.QTDNEG ELSE ITE.QTDNEG * NVL(NULLIF(PR.PESOLIQ, 0), 1) END ELSE 0 END,
               CASE WHEN CAB.PENDENTE = 'S' AND ITE.PENDENTE = 'S' THEN
                    CASE WHEN ITE.CODVOL = 'KG' THEN ITE.QTDNEG - NVL(ITE.QTDENTREGUE, 0)
                         ELSE (ITE.QTDNEG - NVL(ITE.QTDENTREGUE, 0)) * NVL(NULLIF(PR.PESOLIQ, 0), 1) END ELSE 0 END
        FROM TGFCAB CAB JOIN TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA JOIN TGFPRO PR ON PR.CODPROD = ITE.CODPROD
        WHERE CAB.TIPMOV = 'P'
          AND (TRUNC(CAB.DTNEG) = TRUNC(SYSDATE) OR (CAB.PENDENTE = 'S' AND ITE.PENDENTE = 'S'))
          AND ITE.CODPROD IN (90346, 871, 32537, 3465, 949, 85847, 11145)
     ) X
JOIN TGFPRO PRO ON PRO.CODPROD = X.CODPROD
LEFT JOIN TGFVEN VEN ON VEN.CODVEND = X.CODVEND
GROUP BY X.CODPROD, PRO.DESCRPROD, X.CODVEND, VEN.APELIDO
ORDER BY X.CODPROD, REALIZADO_KG DESC;


-- -------------------------------------------------------------------------------------
-- C) PEDIDOS DO MÊS DOS ITENS FOCO — para importar no Sistema Vendas x Metas
--    Exporte o resultado (CSV ou Excel) e envie em Dados › Importar planilhas.
--    Para levar os pedidos de todos os produtos, apague a linha "AND ITE.CODPROD IN (...)".
-- -------------------------------------------------------------------------------------
SELECT CAB.NUNOTA,
       CAB.NUMNOTA,
       TO_CHAR(CAB.DTNEG, 'YYYY-MM-DD')        AS DTNEG,
       CAB.CODEMP,
       CAB.CODTIPOPER,
       CAB.CODPARC,
       PAR.NOMEPARC,
       CAB.CODVEND,
       VEN.APELIDO                             AS VENDEDOR,
       ITE.SEQUENCIA,
       ITE.CODPROD,
       PR.DESCRPROD,
       ITE.CODVOL,
       ITE.QTDNEG,
       ROUND(CASE WHEN ITE.CODVOL = 'KG' THEN ITE.QTDNEG ELSE ITE.QTDNEG * NVL(NULLIF(PR.PESOLIQ, 0), 1) END, 3) AS QTD_KG,
       ROUND(ITE.VLRTOT, 2)                    AS VLRTOT,
       ROUND(CASE WHEN CAB.PENDENTE = 'S' AND ITE.PENDENTE = 'S' THEN
             CASE WHEN ITE.CODVOL = 'KG' THEN ITE.QTDNEG - NVL(ITE.QTDENTREGUE, 0)
                  ELSE (ITE.QTDNEG - NVL(ITE.QTDENTREGUE, 0)) * NVL(NULLIF(PR.PESOLIQ, 0), 1) END ELSE 0 END, 3) AS PENDENTE_KG,
       ITE.PENDENTE
FROM TGFCAB CAB
JOIN TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
JOIN TGFPRO PR  ON PR.CODPROD = ITE.CODPROD
JOIN TGFPAR PAR ON PAR.CODPARC = CAB.CODPARC
LEFT JOIN TGFVEN VEN ON VEN.CODVEND = CAB.CODVEND
WHERE CAB.TIPMOV = 'P'
  AND CAB.DTNEG >= TRUNC(SYSDATE, 'MM') AND CAB.DTNEG < TRUNC(SYSDATE) + 1
  AND ITE.CODPROD IN (90346, 871, 32537, 3465, 949, 85847, 11145)
ORDER BY CAB.DTNEG, CAB.NUNOTA, ITE.SEQUENCIA;


-- -------------------------------------------------------------------------------------
-- D) VALIDAÇÃO COM SETEMBRO/2026 — confira contra o Demonstrativo que já validamos
--    Esperado (vendas + devoluções, sem bonificação, Demonstrativo 09/2026):
--      90346 PERNIL DEFUMADO ............  23.429,02 kg   R$   544.295,83   200 notas
--        871 BACON MANTA ................ 176.362,63 kg   R$ 3.415.771,27   646 notas
--      32537 BACON EM PEDACOS ...........  15.626,79 kg   R$   215.751,38    51 notas
--       3465 LINGUICA TOSCANA - 600G ....  15.948,00 kg   R$   252.158,33   174 notas
--        949 LINGUICA TOSCANA 5 KG ...... 609.795,00 kg   R$ 7.242.477,78 1.513 notas
--      85847 PRESUNTO EXCELENCIA ........ 192.870,11 kg   R$ 3.033.788,20   772 notas
--      11145 PRESUNTO RETANGULAR FS .....  60.250,69 kg   R$   955.595,19   413 notas
--    Se o kg não bater, compare as colunas QTDNEG_BRUTA (volume original) e KG.
--    Se o valor não bater, compare VLRTOT com VLRTOT_MENOS_DESC.
-- -------------------------------------------------------------------------------------
SELECT ITE.CODPROD,
       PR.DESCRPROD,
       MIN(ITE.CODVOL) || CASE WHEN COUNT(DISTINCT ITE.CODVOL) > 1 THEN ' (+outros)' END AS VOLUME,
       ROUND(SUM(SG.S * ITE.QTDNEG), 2)                                                     AS QTDNEG_BRUTA,
       ROUND(SUM(SG.S * CASE WHEN ITE.CODVOL = 'KG' THEN ITE.QTDNEG
                             ELSE ITE.QTDNEG * NVL(NULLIF(PR.PESOLIQ, 0), 1) END), 2)       AS KG,
       ROUND(SUM(SG.S * ITE.VLRTOT), 2)                                                     AS VLRTOT,
       ROUND(SUM(SG.S * (ITE.VLRTOT - NVL(ITE.VLRDESC, 0))), 2)                             AS VLRTOT_MENOS_DESC,
       COUNT(DISTINCT CAB.NUNOTA)                                                           AS NOTAS
FROM TGFCAB CAB
JOIN TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
JOIN TGFPRO PR  ON PR.CODPROD = ITE.CODPROD
JOIN (SELECT 'V' T, 1 S FROM DUAL UNION ALL SELECT 'D', -1 FROM DUAL) SG ON SG.T = CAB.TIPMOV
WHERE CAB.DTMOV >= DATE '2026-09-01' AND CAB.DTMOV < DATE '2026-10-01'
  AND CAB.STATUSNOTA = 'L'
  AND CAB.CODTIPOPER IN (500, 504, 506, 512, 513, 240, 241, 252, 253)
  AND ITE.CODPROD IN (90346, 871, 32537, 3465, 949, 85847, 11145)
GROUP BY ITE.CODPROD, PR.DESCRPROD
ORDER BY ITE.CODPROD;
