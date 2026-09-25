-- Base de dados de Vendas x Metas.
-- Nomes de colunas seguem o dicionário do Sankhya sempre que há equivalente
-- (ver vendas_bi/layouts.py e vendas_bi/sankhya/MAPEAMENTO.md).

-- Cada arquivo importado vira uma carga. Uma nova carga de um período
-- substitui os dados daquele período (o relatório é uma foto do mês).
CREATE TABLE IF NOT EXISTS carga (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo              TEXT NOT NULL CHECK (tipo IN ('vendas', 'metas')),
    origem            TEXT NOT NULL DEFAULT 'planilha',  -- planilha | sankhya
    arquivo           TEXT,
    sha256            TEXT,
    periodos          TEXT NOT NULL,                     -- 'AAAA-MM[,AAAA-MM]'
    linhas            INTEGER NOT NULL,
    emitido_em        TEXT,                              -- data de emissão do relatório
    usuario_relatorio TEXT,
    importado_em      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Item de nota (TGFCAB + TGFITE). Grão: uma linha por item do relatório.
CREATE TABLE IF NOT EXISTS fato_venda (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    carga_id         INTEGER NOT NULL REFERENCES carga(id),
    periodo          TEXT NOT NULL,          -- AAAA-MM de dtmov
    dtmov            TEXT NOT NULL,          -- AAAA-MM-DD
    codemp           INTEGER,
    nunota           INTEGER NOT NULL,
    numnota          INTEGER,
    codtipoper       INTEGER,
    descroper        TEXT,
    operacao         TEXT,                   -- V venda | D devolução | B bonificação
    codparc          INTEGER,
    nomeparc         TEXT,
    perfil           TEXT,
    cidade           TEXT,
    uf               TEXT,
    regiao_pais      TEXT,
    codrede          INTEGER,
    rede             TEXT,
    codreg           INTEGER,
    nomereg          TEXT,
    codvend          INTEGER,
    vendedor         TEXT,
    supervisor       TEXT,
    gerente          TEXT,
    codprod          INTEGER NOT NULL,
    descrprod        TEXT,
    codgrupoprod     INTEGER,
    grupoprod        TEXT,
    linha            TEXT,
    familia          TEXT,
    codmix_comercial INTEGER,
    mix_comercial    TEXT,
    codmix_biblia    INTEGER,
    mix_biblia       TEXT,
    qtd_kg           REAL NOT NULL DEFAULT 0,
    vlrtot           REAL NOT NULL DEFAULT 0,
    vlrsubst         REAL NOT NULL DEFAULT 0,
    vlrtot_st        REAL NOT NULL DEFAULT 0,
    nucte            INTEGER,
    ref_rvv          TEXT
);
CREATE INDEX IF NOT EXISTS ix_venda_periodo ON fato_venda (periodo);
CREATE INDEX IF NOT EXISTS ix_venda_vend_prod ON fato_venda (periodo, codreg, codprod);
CREATE INDEX IF NOT EXISTS ix_venda_parc ON fato_venda (codparc);

-- Meta por região/vendedor/produto no mês (TGFMET) + realizado e carteira.
CREATE TABLE IF NOT EXISTS fato_meta (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    carga_id        INTEGER NOT NULL REFERENCES carga(id),
    periodo         TEXT NOT NULL,
    codreg          INTEGER,
    nomereg         TEXT,
    codvend         INTEGER,                 -- resolvido pelo apelido na fato_venda
    vendedor        TEXT NOT NULL,
    vendedor_ativo  TEXT,
    supervisor      TEXT,
    gerente         TEXT,
    categoria       TEXT,
    codprod         INTEGER NOT NULL,
    descrprod       TEXT,
    qtd_meta        REAL NOT NULL DEFAULT 0, -- kg
    pm_meta         REAL NOT NULL DEFAULT 0, -- R$/kg
    qtd_vendida     REAL NOT NULL DEFAULT 0, -- kg
    vlr_faturado    REAL NOT NULL DEFAULT 0, -- R$
    qtd_fechada     REAL NOT NULL DEFAULT 0, -- kg em carteira
    vlr_fechado     REAL NOT NULL DEFAULT 0  -- R$ em carteira
);
CREATE INDEX IF NOT EXISTS ix_meta_periodo ON fato_meta (periodo);

-- Indicadores calculados da meta (mesmas fórmulas do relatório original).
DROP VIEW IF EXISTS vw_meta;
CREATE VIEW vw_meta AS
SELECT m.*,
       m.qtd_meta * m.pm_meta                                   AS vlr_previsto,
       m.qtd_meta - m.qtd_vendida                               AS diferenca,
       m.qtd_meta - m.qtd_vendida - m.qtd_fechada               AS previa,
       CASE WHEN m.qtd_meta > 0 THEN m.qtd_vendida / m.qtd_meta END              AS perc_meta,
       CASE WHEN m.qtd_meta > 0 THEN (m.qtd_vendida + m.qtd_fechada) / m.qtd_meta END AS perc_prev,
       CASE WHEN m.qtd_vendida <> 0 THEN m.vlr_faturado / m.qtd_vendida END      AS pm_real
FROM fato_meta m;

-- Cadastros derivados das movimentações (última descrição vista).
DROP VIEW IF EXISTS dim_produto;
CREATE VIEW dim_produto AS
SELECT codprod, MAX(descrprod) AS descrprod, MAX(codgrupoprod) AS codgrupoprod,
       MAX(grupoprod) AS grupoprod, MAX(linha) AS linha, MAX(familia) AS familia,
       MAX(mix_comercial) AS mix_comercial, MAX(mix_biblia) AS mix_biblia
FROM fato_venda GROUP BY codprod;

DROP VIEW IF EXISTS dim_parceiro;
CREATE VIEW dim_parceiro AS
SELECT codparc, MAX(nomeparc) AS nomeparc, MAX(cidade) AS cidade, MAX(uf) AS uf,
       MAX(perfil) AS perfil, MAX(codrede) AS codrede, MAX(rede) AS rede
FROM fato_venda GROUP BY codparc;

DROP VIEW IF EXISTS dim_vendedor;
CREATE VIEW dim_vendedor AS
SELECT codvend, MAX(vendedor) AS vendedor, MAX(supervisor) AS supervisor,
       MAX(gerente) AS gerente
FROM fato_venda WHERE codvend IS NOT NULL GROUP BY codvend;
