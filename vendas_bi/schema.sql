-- Sistema Vendas x Metas — modelo de dados.
--
-- Tabelas espelham o Sankhya para facilitar a migração:
--   empresa        -> TSIEMP        regiao    -> TSIREG
--   vendedor       -> TGFVEN        parceiro  -> TGFPAR (+ TSICID/TSIUFS)
--   produto        -> TGFPRO/TGFGRU tipo_operacao -> TGFTOP
--   nota           -> TGFCAB        item      -> TGFITE
--   meta           -> TGFMET
-- Os dados entram por lançamento manual ou por importação de planilha;
-- a coluna "origem" diz de onde veio cada registro.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS carga (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo              TEXT NOT NULL CHECK (tipo IN ('vendas', 'metas')),
    origem            TEXT NOT NULL DEFAULT 'planilha',  -- planilha | sankhya
    arquivo           TEXT,
    sha256            TEXT,
    periodos          TEXT NOT NULL,                     -- 'AAAA-MM[,AAAA-MM]'
    linhas            INTEGER NOT NULL,
    emitido_em        TEXT,
    usuario_relatorio TEXT,
    controle          TEXT,                              -- JSON com os totais lidos da planilha
    importado_em      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ------------------------------------------------------------ cadastros
CREATE TABLE IF NOT EXISTS empresa (
    codemp      INTEGER PRIMARY KEY,
    nomeempresa TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS regiao (
    codreg  INTEGER PRIMARY KEY,
    nomereg TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vendedor (
    codvend    INTEGER PRIMARY KEY,
    apelido    TEXT NOT NULL UNIQUE,
    supervisor TEXT,
    gerente    TEXT,
    codreg     INTEGER REFERENCES regiao(codreg) ON UPDATE CASCADE,
    ativo      TEXT NOT NULL DEFAULT 'S' CHECK (ativo IN ('S', 'N')),
    provisorio INTEGER NOT NULL DEFAULT 0   -- 1 = código criado pelo sistema (não veio do Sankhya)
);

CREATE TABLE IF NOT EXISTS parceiro (
    codparc     INTEGER PRIMARY KEY,
    nomeparc    TEXT NOT NULL,
    perfil      TEXT,
    cidade      TEXT,
    uf          TEXT,
    regiao_pais TEXT,
    codrede     INTEGER,
    rede        TEXT
);

CREATE TABLE IF NOT EXISTS produto (
    codprod          INTEGER PRIMARY KEY,
    descrprod        TEXT NOT NULL,
    codgrupoprod     INTEGER,
    grupoprod        TEXT,
    linha            TEXT,
    familia          TEXT,
    codmix_comercial INTEGER,
    mix_comercial    TEXT,
    codmix_biblia    INTEGER,
    mix_biblia       TEXT,
    categoria        TEXT                   -- categoria usada no resumo de metas
);

CREATE TABLE IF NOT EXISTS tipo_operacao (
    codtipoper INTEGER PRIMARY KEY,
    descroper  TEXT NOT NULL,
    operacao   TEXT NOT NULL CHECK (operacao IN ('V', 'D', 'B'))  -- venda, devolução, bonificação
);

-- ------------------------------------------------------------ lançamentos
CREATE TABLE IF NOT EXISTS nota (
    nunota      INTEGER PRIMARY KEY,
    numnota     INTEGER,
    codemp      INTEGER NOT NULL REFERENCES empresa(codemp) ON UPDATE CASCADE,
    dtmov       TEXT NOT NULL,             -- AAAA-MM-DD
    codtipoper  INTEGER NOT NULL REFERENCES tipo_operacao(codtipoper) ON UPDATE CASCADE,
    codparc     INTEGER NOT NULL REFERENCES parceiro(codparc) ON UPDATE CASCADE,
    codvend     INTEGER NOT NULL REFERENCES vendedor(codvend) ON UPDATE CASCADE,
    codreg      INTEGER REFERENCES regiao(codreg) ON UPDATE CASCADE,
    ref_rvv     TEXT,                      -- MM/AAAA
    origem      TEXT NOT NULL DEFAULT 'manual',
    carga_id    INTEGER REFERENCES carga(id) ON DELETE SET NULL,
    criado_em   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    alterado_em TEXT
);
CREATE INDEX IF NOT EXISTS ix_nota_dtmov ON nota (dtmov);
CREATE INDEX IF NOT EXISTS ix_nota_carga ON nota (carga_id);

-- Quantidade e valores com sinal: devolução e bonificação são negativas.
CREATE TABLE IF NOT EXISTS item (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nunota    INTEGER NOT NULL REFERENCES nota(nunota) ON DELETE CASCADE ON UPDATE CASCADE,
    sequencia INTEGER NOT NULL,
    codprod   INTEGER NOT NULL REFERENCES produto(codprod) ON UPDATE CASCADE,
    qtd_kg    REAL NOT NULL DEFAULT 0,
    vlrtot    REAL NOT NULL DEFAULT 0,
    vlrsubst  REAL NOT NULL DEFAULT 0,
    vlrtot_st REAL NOT NULL DEFAULT 0,
    nucte     INTEGER,
    UNIQUE (nunota, sequencia)
);
CREATE INDEX IF NOT EXISTS ix_item_prod ON item (codprod);

CREATE TABLE IF NOT EXISTS meta (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    periodo     TEXT NOT NULL,             -- AAAA-MM
    codreg      INTEGER REFERENCES regiao(codreg) ON UPDATE CASCADE,
    codvend     INTEGER NOT NULL REFERENCES vendedor(codvend) ON UPDATE CASCADE,
    codprod     INTEGER NOT NULL REFERENCES produto(codprod) ON UPDATE CASCADE,
    qtd_meta    REAL NOT NULL DEFAULT 0,   -- kg
    pm_meta     REAL NOT NULL DEFAULT 0,   -- R$/kg
    qtd_fechada REAL NOT NULL DEFAULT 0,   -- carteira (pedidos fechados), kg
    vlr_fechado REAL NOT NULL DEFAULT 0,   -- carteira, R$
    vendido_rel  REAL,                     -- "Vendido" do resumo importado (conferência)
    faturado_rel REAL,                     -- "Valor Faturado" do resumo importado (conferência)
    origem      TEXT NOT NULL DEFAULT 'manual',
    carga_id    INTEGER REFERENCES carga(id) ON DELETE SET NULL,
    alterado_em TEXT,
    UNIQUE (periodo, codreg, codvend, codprod)
);
CREATE INDEX IF NOT EXISTS ix_meta_periodo ON meta (periodo);

-- ------------------------------------------------------------ visões
-- Uma linha por item, no mesmo formato do Demonstrativo Mensal.
DROP VIEW IF EXISTS vw_venda;
CREATE VIEW vw_venda AS
SELECT substr(n.dtmov, 1, 7) AS periodo, n.dtmov, n.codemp, e.nomeempresa, n.nunota, n.numnota,
       n.codtipoper, t.descroper, t.operacao,
       n.codparc, p.nomeparc, p.perfil, p.cidade, p.uf, p.regiao_pais, p.codrede, p.rede,
       n.codreg, r.nomereg, n.codvend, v.apelido AS vendedor, v.supervisor, v.gerente,
       i.id AS item_id, i.sequencia, i.codprod, pr.descrprod, pr.codgrupoprod, pr.grupoprod, pr.linha, pr.familia,
       pr.codmix_comercial, pr.mix_comercial, pr.codmix_biblia, pr.mix_biblia,
       i.qtd_kg, i.vlrtot, i.vlrsubst, i.vlrtot_st, i.nucte, n.ref_rvv, n.origem, n.carga_id
FROM item i
JOIN nota n            ON n.nunota = i.nunota
JOIN tipo_operacao t   ON t.codtipoper = n.codtipoper
JOIN parceiro p        ON p.codparc = n.codparc
JOIN vendedor v        ON v.codvend = n.codvend
JOIN produto pr        ON pr.codprod = i.codprod
LEFT JOIN empresa e    ON e.codemp = n.codemp
LEFT JOIN regiao r     ON r.codreg = n.codreg;

-- Meta com o realizado calculado das notas (vendas + devoluções, sem bonificação)
-- pela mesma chave do resumo: região + vendedor + produto no mês.
DROP VIEW IF EXISTS vw_meta;
CREATE VIEW vw_meta AS
WITH real AS (
    SELECT substr(n.dtmov, 1, 7) AS periodo, n.codreg, n.codvend, i.codprod,
           SUM(i.qtd_kg) AS qtd, SUM(i.vlrtot) AS vlr
    FROM item i JOIN nota n ON n.nunota = i.nunota
    JOIN tipo_operacao t ON t.codtipoper = n.codtipoper
    WHERE t.operacao IN ('V', 'D')
    GROUP BY 1, 2, 3, 4
)
SELECT m.id, m.periodo, m.codreg, r.nomereg, m.codvend, v.apelido AS vendedor, v.ativo AS vendedor_ativo,
       v.supervisor, v.gerente, m.codprod, pr.descrprod, pr.categoria,
       m.qtd_meta, m.pm_meta, m.qtd_fechada, m.vlr_fechado,
       COALESCE(re.qtd, 0) AS qtd_vendida, COALESCE(re.vlr, 0) AS vlr_faturado,
       m.vendido_rel, m.faturado_rel, m.origem, m.carga_id,
       m.qtd_meta * m.pm_meta                                              AS vlr_previsto,
       m.qtd_meta - COALESCE(re.qtd, 0)                                    AS diferenca,
       m.qtd_meta - COALESCE(re.qtd, 0) - m.qtd_fechada                    AS previa,
       CASE WHEN m.qtd_meta > 0 THEN COALESCE(re.qtd, 0) / m.qtd_meta END  AS perc_meta,
       CASE WHEN m.qtd_meta > 0 THEN (COALESCE(re.qtd, 0) + m.qtd_fechada) / m.qtd_meta END AS perc_prev,
       CASE WHEN COALESCE(re.qtd, 0) <> 0 THEN re.vlr / re.qtd END         AS pm_real
FROM meta m
JOIN vendedor v     ON v.codvend = m.codvend
JOIN produto pr     ON pr.codprod = m.codprod
LEFT JOIN regiao r  ON r.codreg = m.codreg
LEFT JOIN real re   ON re.periodo = m.periodo AND re.codreg IS m.codreg
                   AND re.codvend = m.codvend AND re.codprod = m.codprod;
