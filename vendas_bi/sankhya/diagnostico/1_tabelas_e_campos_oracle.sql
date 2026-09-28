-- Diagnóstico do banco Sankhya (Oracle) para o Sistema Vendas x Metas.
-- SOMENTE LEITURA: consulta o catálogo do banco, não altera nada.
-- Resultado: uma linha por campo, com STATUS = OK, CAMPO NAO ENCONTRADO ou TABELA NAO ENCONTRADA.
-- Exporte o resultado para Excel e envie. "Não encontrado" pode ser só outro nome de campo
-- na sua versão; a consulta 3 (campos_adicionais.sql) ajuda a achar o equivalente.

SELECT N.BLOCO, N.TABELA, N.CAMPO, N.USO,
       CASE
         WHEN EXISTS (SELECT 1 FROM ALL_TAB_COLUMNS C WHERE C.TABLE_NAME = N.TABELA AND C.COLUMN_NAME = N.CAMPO) THEN 'OK'
         WHEN EXISTS (SELECT 1 FROM ALL_TABLES T WHERE T.TABLE_NAME = N.TABELA)
           OR EXISTS (SELECT 1 FROM ALL_VIEWS V WHERE V.VIEW_NAME = N.TABELA) THEN 'CAMPO NAO ENCONTRADO'
         ELSE 'TABELA NAO ENCONTRADA'
       END AS STATUS
FROM (
  SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'NUNOTA' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'NUMNOTA' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'CODEMP' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'DTNEG' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'DTMOV' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'DTFATUR' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'CODTIPOPER' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'DHTIPOPER' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'TIPMOV' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'STATUSNOTA' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'CODPARC' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'CODVEND' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'CODTIPVENDA' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'VLRNOTA' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'VLRFRETE' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'PENDENTE' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'DTENTSAI' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFCAB' TABELA, 'ORDEMCARGA' CAMPO, 'cabecalho da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'NUNOTA' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'SEQUENCIA' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'CODPROD' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'QTDNEG' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'QTDENTREGUE' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'VLRUNIT' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'VLRTOT' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'VLRDESC' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'VLRICMS' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'VLRIPI' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'VLRSUBST' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'CUSTO' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'CODVOL' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'CONTROLE' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'CODVEND' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFITE' TABELA, 'PENDENTE' CAMPO, 'itens da nota / pedido' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFTOP' TABELA, 'CODTIPOPER' CAMPO, 'tipos de operacao' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFTOP' TABELA, 'DHALTER' CAMPO, 'tipos de operacao' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFTOP' TABELA, 'DESCROPER' CAMPO, 'tipos de operacao' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFTOP' TABELA, 'TIPMOV' CAMPO, 'tipos de operacao' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFTOP' TABELA, 'ATUALEST' CAMPO, 'tipos de operacao' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFTOP' TABELA, 'ATUALFIN' CAMPO, 'tipos de operacao' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPRO' TABELA, 'CODPROD' CAMPO, 'produtos' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPRO' TABELA, 'DESCRPROD' CAMPO, 'produtos' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPRO' TABELA, 'CODGRUPOPROD' CAMPO, 'produtos' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPRO' TABELA, 'PESOLIQ' CAMPO, 'produtos' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPRO' TABELA, 'PESOBRUTO' CAMPO, 'produtos' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPRO' TABELA, 'CODVOL' CAMPO, 'produtos' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPRO' TABELA, 'ATIVO' CAMPO, 'produtos' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPRO' TABELA, 'MARCA' CAMPO, 'produtos' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFGRU' TABELA, 'CODGRUPOPROD' CAMPO, 'grupos de produto' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFGRU' TABELA, 'DESCRGRUPOPROD' CAMPO, 'grupos de produto' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFGRU' TABELA, 'CODGRUPAI' CAMPO, 'grupos de produto' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPAR' TABELA, 'CODPARC' CAMPO, 'clientes / parceiros' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPAR' TABELA, 'NOMEPARC' CAMPO, 'clientes / parceiros' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPAR' TABELA, 'RAZAOSOCIAL' CAMPO, 'clientes / parceiros' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPAR' TABELA, 'CGC_CPF' CAMPO, 'clientes / parceiros' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPAR' TABELA, 'CODCID' CAMPO, 'clientes / parceiros' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPAR' TABELA, 'CODREG' CAMPO, 'clientes / parceiros' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPAR' TABELA, 'CODVEND' CAMPO, 'clientes / parceiros' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPAR' TABELA, 'LIMCRED' CAMPO, 'clientes / parceiros' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPAR' TABELA, 'DTCAD' CAMPO, 'clientes / parceiros' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPAR' TABELA, 'ATIVO' CAMPO, 'clientes / parceiros' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPAR' TABELA, 'CLIENTE' CAMPO, 'clientes / parceiros' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFPAR' TABELA, 'BLOQUEAR' CAMPO, 'clientes / parceiros' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TSICID' TABELA, 'CODCID' CAMPO, 'cidades' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TSICID' TABELA, 'NOMECID' CAMPO, 'cidades' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TSICID' TABELA, 'UF' CAMPO, 'cidades' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TSIUFS' TABELA, 'CODUF' CAMPO, 'estados' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TSIUFS' TABELA, 'UF' CAMPO, 'estados' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TSIUFS' TABELA, 'DESCRICAO' CAMPO, 'estados' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TSIREG' TABELA, 'CODREG' CAMPO, 'regioes (hierarquia)' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TSIREG' TABELA, 'NOMEREG' CAMPO, 'regioes (hierarquia)' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TSIREG' TABELA, 'CODREGPAI' CAMPO, 'regioes (hierarquia)' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFVEN' TABELA, 'CODVEND' CAMPO, 'vendedores / supervisores / gerentes' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFVEN' TABELA, 'APELIDO' CAMPO, 'vendedores / supervisores / gerentes' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFVEN' TABELA, 'TIPVEND' CAMPO, 'vendedores / supervisores / gerentes' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFVEN' TABELA, 'CODGER' CAMPO, 'vendedores / supervisores / gerentes' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFVEN' TABELA, 'CODREG' CAMPO, 'vendedores / supervisores / gerentes' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TGFVEN' TABELA, 'ATIVO' CAMPO, 'vendedores / supervisores / gerentes' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TSIEMP' TABELA, 'CODEMP' CAMPO, 'empresas' USO FROM DUAL
  UNION ALL SELECT '1 Vendas (ja usado)' BLOCO, 'TSIEMP' TABELA, 'NOMEFANTASIA' CAMPO, 'empresas' USO FROM DUAL
  UNION ALL SELECT '2 Metas' BLOCO, 'TGFMET' TABELA, 'CODMETA' CAMPO, 'metas (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '2 Metas' BLOCO, 'TGFMET' TABELA, 'DTREF' CAMPO, 'metas (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '2 Metas' BLOCO, 'TGFMET' TABELA, 'CODVEND' CAMPO, 'metas (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '2 Metas' BLOCO, 'TGFMET' TABELA, 'CODPROD' CAMPO, 'metas (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '2 Metas' BLOCO, 'TGFMET' TABELA, 'CODGRUPOPROD' CAMPO, 'metas (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '2 Metas' BLOCO, 'TGFMET' TABELA, 'CODPARC' CAMPO, 'metas (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '2 Metas' BLOCO, 'TGFMET' TABELA, 'QTDPREV' CAMPO, 'metas (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '2 Metas' BLOCO, 'TGFMET' TABELA, 'VLRPREV' CAMPO, 'metas (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '3 Margem' BLOCO, 'TGFCUS' TABELA, 'CODPROD' CAMPO, 'custo do produto (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '3 Margem' BLOCO, 'TGFCUS' TABELA, 'CODEMP' CAMPO, 'custo do produto (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '3 Margem' BLOCO, 'TGFCUS' TABELA, 'DTATUAL' CAMPO, 'custo do produto (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '3 Margem' BLOCO, 'TGFCUS' TABELA, 'CUSREP' CAMPO, 'custo do produto (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '3 Margem' BLOCO, 'TGFCUS' TABELA, 'CUSMED' CAMPO, 'custo do produto (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '3 Margem' BLOCO, 'TGFCUS' TABELA, 'CUSGER' CAMPO, 'custo do produto (confirmar campos)' USO FROM DUAL
  UNION ALL SELECT '3 Margem' BLOCO, 'TGFDIN' TABELA, 'NUNOTA' CAMPO, 'impostos por item' USO FROM DUAL
  UNION ALL SELECT '3 Margem' BLOCO, 'TGFDIN' TABELA, 'SEQUENCIA' CAMPO, 'impostos por item' USO FROM DUAL
  UNION ALL SELECT '3 Margem' BLOCO, 'TGFDIN' TABELA, 'CODIMP' CAMPO, 'impostos por item' USO FROM DUAL
  UNION ALL SELECT '3 Margem' BLOCO, 'TGFDIN' TABELA, 'BASE' CAMPO, 'impostos por item' USO FROM DUAL
  UNION ALL SELECT '3 Margem' BLOCO, 'TGFDIN' TABELA, 'VALOR' CAMPO, 'impostos por item' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'NUFIN' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'NUNOTA' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'CODEMP' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'CODPARC' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'CODVEND' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'RECDESP' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'DTNEG' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'DTVENC' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'DHBAIXA' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'VLRDESDOB' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'VLRBAIXA' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'CODTIPTIT' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFFIN' TABELA, 'PROVISAO' CAMPO, 'titulos a receber' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFTPV' TABELA, 'CODTIPVENDA' CAMPO, 'condicao de pagamento' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFTPV' TABELA, 'DHALTER' CAMPO, 'condicao de pagamento' USO FROM DUAL
  UNION ALL SELECT '4 Financeiro' BLOCO, 'TGFTPV' TABELA, 'DESCRTIPVENDA' CAMPO, 'condicao de pagamento' USO FROM DUAL
  UNION ALL SELECT '5 Estoque' BLOCO, 'TGFEST' TABELA, 'CODEMP' CAMPO, 'estoque, lote e validade' USO FROM DUAL
  UNION ALL SELECT '5 Estoque' BLOCO, 'TGFEST' TABELA, 'CODPROD' CAMPO, 'estoque, lote e validade' USO FROM DUAL
  UNION ALL SELECT '5 Estoque' BLOCO, 'TGFEST' TABELA, 'CODLOCAL' CAMPO, 'estoque, lote e validade' USO FROM DUAL
  UNION ALL SELECT '5 Estoque' BLOCO, 'TGFEST' TABELA, 'CONTROLE' CAMPO, 'estoque, lote e validade' USO FROM DUAL
  UNION ALL SELECT '5 Estoque' BLOCO, 'TGFEST' TABELA, 'ESTOQUE' CAMPO, 'estoque, lote e validade' USO FROM DUAL
  UNION ALL SELECT '5 Estoque' BLOCO, 'TGFEST' TABELA, 'RESERVADO' CAMPO, 'estoque, lote e validade' USO FROM DUAL
  UNION ALL SELECT '5 Estoque' BLOCO, 'TGFEST' TABELA, 'DTVAL' CAMPO, 'estoque, lote e validade' USO FROM DUAL
  UNION ALL SELECT '6 Pedidos e atendimento' BLOCO, 'TGFVAR' TABELA, 'NUNOTA' CAMPO, 'vinculo pedido -> nota (cortes)' USO FROM DUAL
  UNION ALL SELECT '6 Pedidos e atendimento' BLOCO, 'TGFVAR' TABELA, 'SEQUENCIA' CAMPO, 'vinculo pedido -> nota (cortes)' USO FROM DUAL
  UNION ALL SELECT '6 Pedidos e atendimento' BLOCO, 'TGFVAR' TABELA, 'NUNOTAORIG' CAMPO, 'vinculo pedido -> nota (cortes)' USO FROM DUAL
  UNION ALL SELECT '6 Pedidos e atendimento' BLOCO, 'TGFVAR' TABELA, 'SEQUENCIAORIG' CAMPO, 'vinculo pedido -> nota (cortes)' USO FROM DUAL
  UNION ALL SELECT '6 Pedidos e atendimento' BLOCO, 'TGFVAR' TABELA, 'QTDATENDIDA' CAMPO, 'vinculo pedido -> nota (cortes)' USO FROM DUAL
  UNION ALL SELECT '6 Pedidos e atendimento' BLOCO, 'TGFORD' TABELA, 'ORDEMCARGA' CAMPO, 'ordens de carga / rotas' USO FROM DUAL
  UNION ALL SELECT '6 Pedidos e atendimento' BLOCO, 'TGFORD' TABELA, 'CODEMP' CAMPO, 'ordens de carga / rotas' USO FROM DUAL
  UNION ALL SELECT '6 Pedidos e atendimento' BLOCO, 'TGFORD' TABELA, 'DTINIC' CAMPO, 'ordens de carga / rotas' USO FROM DUAL
  UNION ALL SELECT '6 Pedidos e atendimento' BLOCO, 'TGFORD' TABELA, 'CODVEICULO' CAMPO, 'ordens de carga / rotas' USO FROM DUAL
  UNION ALL SELECT '7 Preco' BLOCO, 'TGFTAB' TABELA, 'NUTAB' CAMPO, 'tabelas de preco' USO FROM DUAL
  UNION ALL SELECT '7 Preco' BLOCO, 'TGFTAB' TABELA, 'CODTAB' CAMPO, 'tabelas de preco' USO FROM DUAL
  UNION ALL SELECT '7 Preco' BLOCO, 'TGFTAB' TABELA, 'DTVIGOR' CAMPO, 'tabelas de preco' USO FROM DUAL
  UNION ALL SELECT '7 Preco' BLOCO, 'TGFEXC' TABELA, 'NUTAB' CAMPO, 'preco por produto na tabela' USO FROM DUAL
  UNION ALL SELECT '7 Preco' BLOCO, 'TGFEXC' TABELA, 'CODPROD' CAMPO, 'preco por produto na tabela' USO FROM DUAL
  UNION ALL SELECT '7 Preco' BLOCO, 'TGFEXC' TABELA, 'VLRVENDA' CAMPO, 'preco por produto na tabela' USO FROM DUAL
  UNION ALL SELECT '8 Dicionario' BLOCO, 'TDDTAB' TABELA, 'NOMETAB' CAMPO, 'dicionario de tabelas do Sankhya' USO FROM DUAL
  UNION ALL SELECT '8 Dicionario' BLOCO, 'TDDTAB' TABELA, 'DESCRTAB' CAMPO, 'dicionario de tabelas do Sankhya' USO FROM DUAL
  UNION ALL SELECT '8 Dicionario' BLOCO, 'TDDCAM' TABELA, 'NOMETAB' CAMPO, 'dicionario de campos (acha os AD_)' USO FROM DUAL
  UNION ALL SELECT '8 Dicionario' BLOCO, 'TDDCAM' TABELA, 'NOMECAMPO' CAMPO, 'dicionario de campos (acha os AD_)' USO FROM DUAL
  UNION ALL SELECT '8 Dicionario' BLOCO, 'TDDCAM' TABELA, 'DESCRCAMPO' CAMPO, 'dicionario de campos (acha os AD_)' USO FROM DUAL
  UNION ALL SELECT '8 Dicionario' BLOCO, 'TDDCAM' TABELA, 'TIPCAMPO' CAMPO, 'dicionario de campos (acha os AD_)' USO FROM DUAL
) N
ORDER BY N.BLOCO, N.TABELA, N.CAMPO
