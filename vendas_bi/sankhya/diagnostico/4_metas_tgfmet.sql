-- Metas no Sankhya (Oracle). SOMENTE LEITURA. Rode cada consulta separadamente.
-- O diagnóstico mostrou que a TGFMET existe, mas sem o campo VLRPREV. Estas consultas mostram
-- quais campos de valor ela tem e se é ela que alimenta o "Resumo Geral das Metas/Vendas".

-- 4.1 Todos os campos da TGFMET, com a descrição do dicionário do Sankhya
SELECT C.COLUMN_ID, C.COLUMN_NAME AS CAMPO, C.DATA_TYPE AS TIPO, D.DESCRCAMPO AS DESCRICAO
FROM ALL_TAB_COLUMNS C
LEFT JOIN TDDCAM D ON D.NOMETAB = C.TABLE_NAME AND D.NOMECAMPO = C.COLUMN_NAME
WHERE C.TABLE_NAME = 'TGFMET'
ORDER BY C.COLUMN_ID;

-- 4.2 Meta por mês na TGFMET. Em 09/2026 o resumo de metas soma 4.813.683 kg de meta;
-- se o total de 2026-09 abaixo bater, a TGFMET é a origem do relatório.
SELECT TO_CHAR(DTREF, 'YYYY-MM') AS MES, COUNT(*) AS LINHAS, SUM(QTDPREV) AS META_QTD,
       COUNT(DISTINCT CODVEND) AS VENDEDORES, COUNT(DISTINCT CODPROD) AS PRODUTOS
FROM TGFMET
WHERE DTREF >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY TO_CHAR(DTREF, 'YYYY-MM')
ORDER BY 1 DESC;
