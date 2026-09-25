-- Extração do "Demonstrativo Mensal das Vendas Efetuadas" direto do Sankhya.
-- Devolve exatamente as colunas da tabela fato_venda (ver layouts.py).
--
-- ATENÇÃO: é um MODELO para validar com o TI/consultor Sankhya.
--   * O caminho mais seguro é abrir o relatório atual no Sankhya
--     (Construtor de Relatórios / Dashboard) e copiar a SQL dele,
--     apenas renomeando as colunas com os "AS" abaixo.
--   * Campos marcados "AD_" são campos adicionais que existem nessa base
--     (Linha, Família, Mix, Rede, Perfil); confirme os nomes no Dicionário
--     de Dados (TDDCAM).
--   * Sintaxe Oracle. Para SQL Server troque TO_CHAR/TRUNC pelos equivalentes.
--
-- Parâmetros: :DTINI e :DTFIM (primeiro e último dia do mês).

SELECT
    TO_CHAR(CAB.DTMOV, 'YYYY-MM-DD')                     AS dtmov,
    CAB.CODEMP                                           AS codemp,
    CAB.NUNOTA                                           AS nunota,
    CAB.NUMNOTA                                          AS numnota,
    CAB.CODTIPOPER                                       AS codtipoper,
    TPO.DESCROPER                                        AS descroper,
    CASE WHEN CAB.TIPMOV = 'D' THEN 'D'
         WHEN TPO.CODTIPOPER IN (501) THEN 'B'           -- TOPs de bonificação
         ELSE 'V' END                                    AS operacao,
    CAB.CODPARC                                          AS codparc,
    PAR.NOMEPARC                                         AS nomeparc,
    PAR.AD_PERFIL                                        AS perfil,
    CID.NOMECID                                          AS cidade,
    UFS.UF                                               AS uf,
    UFS.AD_REGIAOPAIS                                    AS regiao_pais,
    PAR.AD_CODREDE                                       AS codrede,
    RED.AD_DESCRREDE                                     AS rede,
    REG.CODREG                                           AS codreg,
    REG.NOMEREG                                          AS nomereg,
    CAB.CODVEND                                          AS codvend,
    VEN.APELIDO                                          AS vendedor,
    SUP.APELIDO                                          AS supervisor,
    GER.APELIDO                                          AS gerente,
    ITE.CODPROD                                          AS codprod,
    PRO.DESCRPROD                                        AS descrprod,
    PRO.CODGRUPOPROD                                     AS codgrupoprod,
    GRU.DESCRGRUPOPROD                                   AS grupoprod,
    PRO.AD_LINHA                                         AS linha,
    PRO.AD_FAMILIA                                       AS familia,
    PRO.AD_CODMIXCOM                                     AS codmix_comercial,
    PRO.AD_MIXCOM                                        AS mix_comercial,
    PRO.AD_CODMIXBIB                                     AS codmix_biblia,
    PRO.AD_MIXBIB                                        AS mix_biblia,
    -- devoluções e bonificações entram negativas, como no relatório atual
    -- (confirmar se QTDNEG já está em kg ou se precisa do peso do produto)
    CAB.SINAL * ITE.QTDNEG * NVL(PRO.PESOLIQ, 1)             AS qtd_kg,
    CAB.SINAL * ITE.VLRTOT                                   AS vlrtot,
    CAB.SINAL * ITE.VLRSUBST                                 AS vlrsubst,
    CAB.SINAL * (ITE.VLRTOT + ITE.VLRSUBST)                  AS vlrtot_st,
    NULL                                                 AS nucte,
    TO_CHAR(CAB.DTMOV, 'MM/YYYY')                        AS ref_rvv
FROM (SELECT C.*, CASE WHEN C.TIPMOV = 'D' OR C.CODTIPOPER IN (501) THEN -1 ELSE 1 END AS SINAL
      FROM TGFCAB C) CAB
JOIN TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
JOIN TGFPRO PRO ON PRO.CODPROD = ITE.CODPROD
JOIN TGFGRU GRU ON GRU.CODGRUPOPROD = PRO.CODGRUPOPROD
JOIN TGFPAR PAR ON PAR.CODPARC = CAB.CODPARC
LEFT JOIN TSICID CID ON CID.CODCID = PAR.CODCID
LEFT JOIN TSIUFS UFS ON UFS.CODUF = CID.UF
LEFT JOIN TSIREG REG ON REG.CODREG = PAR.CODREG
LEFT JOIN TGFVEN VEN ON VEN.CODVEND = CAB.CODVEND
LEFT JOIN TGFVEN SUP ON SUP.CODVEND = VEN.AD_CODSUPERVISOR
LEFT JOIN TGFVEN GER ON GER.CODVEND = VEN.CODGER
LEFT JOIN AD_REDE RED ON RED.AD_CODREDE = PAR.AD_CODREDE
JOIN TGFTOP TPO ON TPO.CODTIPOPER = CAB.CODTIPOPER AND TPO.DHALTER = CAB.DHTIPOPER
WHERE CAB.DTMOV BETWEEN :DTINI AND :DTFIM
  AND CAB.STATUSNOTA = 'L'
  AND CAB.CODTIPOPER IN (240, 241, 252, 253, 500, 501, 504, 506, 512, 513)
