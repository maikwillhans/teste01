# Migração para o Sankhya

Os dois relatórios (Demonstrativo Mensal das Vendas e Resumo Geral das Metas)
já saem do Sankhya — o usuário `172 - PDEGANI` aparece no cabeçalho e os
campos são os do ERP (TOP, Nº Único, Cód. Parceiro...). Por isso a base foi
desenhada com os **mesmos nomes de campo do dicionário do Sankhya**, e a
migração acontece em etapas sem refazer o dashboard.

## Etapas

| Fase | Como os dados chegam | O que muda |
|---|---|---|
| 1 (agora) | Lançamento manual no sistema e/ou planilhas exportadas do Sankhya em **Dados › Importar planilhas** | nada |
| 2 | `python -m vendas_bi.sankhya.conector AAAA-MM` busca direto na API do Sankhya (agendável) | só a origem da carga; base e dashboard iguais |
| 3 | Dashboard dentro do Sankhya (Construtor de Componentes de BI / Dashboards) | reaproveita as SQLs de `vendas.sql` e `metas.sql` e os indicadores de `consultas.py` |

Na fase 2 cada carga fica registrada em `carga.origem = 'sankhya'`, então dá
para rodar planilha e API em paralelo por um mês e comparar.

## Tabelas do sistema x Sankhya

| Sistema | Sankhya | Conteúdo |
|---|---|---|
| `empresa` | TSIEMP | empresas |
| `regiao` | TSIREG | regiões de venda |
| `vendedor` | TGFVEN | vendedores, com supervisor e gerente |
| `parceiro` | TGFPAR (+ TSICID/TSIUFS) | clientes |
| `produto` | TGFPRO / TGFGRU | produtos e grupos |
| `tipo_operacao` | TGFTOP | TOPs, com a operação V/D/B |
| `nota` | TGFCAB | cabeçalho da nota |
| `item` | TGFITE | itens da nota |
| `meta` | TGFMET | meta por região, vendedor e produto no mês |

A view `vw_venda` reproduz o Demonstrativo Mensal linha a linha e a
`vw_meta` reproduz o Resumo Geral das Metas, com o realizado calculado das
notas. Vendedores que aparecem só no resumo de metas recebem um código
provisório (a partir de 900000); quando o código real chega por uma
planilha de vendas, ou é corrigido em Cadastros › Vendedores, notas e metas
acompanham. Notas lançadas no sistema usam Nº Único a partir de
900.000.000, faixa que não colide com o Sankhya.

## De-para das colunas

O de-para completo (cabeçalho do relatório → coluna da base → campo Sankhya)
está em [`../layouts.py`](../layouts.py). Resumo:

| Base | Sankhya | Relatório |
|---|---|---|
| `nunota` | TGFCAB.NUNOTA | Nº Único Nota |
| `numnota` | TGFCAB.NUMNOTA | Nota Fiscal |
| `codemp` | TGFCAB.CODEMP | Empresa |
| `dtmov` | TGFCAB.DTMOV | Data Mvto |
| `codtipoper` / `descroper` | TGFCAB.CODTIPOPER / TGFTOP.DESCROPER | TOP / Nome da TOP |
| `codparc` / `nomeparc` | TGFCAB.CODPARC / TGFPAR.NOMEPARC | Cód. Cliente / Cliente |
| `cidade` / `uf` | TSICID.NOMECID / TSIUFS.UF | Cidade / Uf |
| `codreg` / `nomereg` | TSIREG.CODREG / NOMEREG | Região (`101003026 - ZV131 - VILMAR`) |
| `codvend` / `vendedor` | TGFCAB.CODVEND / TGFVEN.APELIDO | Cód. Vendedor / Vendedor |
| `gerente` | TGFVEN.CODGER → APELIDO | Gerente |
| `codprod` / `descrprod` | TGFITE.CODPROD / TGFPRO.DESCRPROD | Cód.Produto / Descrição |
| `codgrupoprod` / `grupoprod` | TGFPRO.CODGRUPOPROD / TGFGRU.DESCRGRUPOPROD | Cód.Conta / Conta Estoque |
| `qtd_kg` | TGFITE.QTDNEG (× peso) | Qtde Kg |
| `vlrtot` / `vlrsubst` | TGFITE.VLRTOT / VLRSUBST | Valor Total Produto / Valor ST |
| `qtd_meta`, `pm_meta` | TGFMET.QTDPREV, VLRPREV/QTDPREV | Meta, P.M. Meta |
| `qtd_fechada`, `vlr_fechado` | pedidos (TIPMOV='P') pendentes | Fechado, Valor Fechado |

Campos como Linha, Família, Mix Comercial, Mix Bíblia, Rede e Perfil são
**campos adicionais (AD_)** desta instalação — confirme os nomes no
Dicionário de Dados (tabela TDDCAM) antes da fase 2.

## Regras de negócio levantadas das planilhas

- **Operação**: `V` venda, `D` devolução, `B` bonificação. Devolução e
  bonificação vêm com quantidade e valor **negativos**.
- **Realizado (Vendido)** = vendas + devoluções (bonificação fica fora).
  Com essa regra o demonstrativo de 09/2026 soma 3.082,7 t / R$ 45,06 mi
  contra 3.073,3 t / R$ 44,93 mi do "Vendido" do resumo de metas (≈0,3%).
  As diferenças por região × produto aparecem na tela de conciliação
  (aba Importar dados); a hipótese é notas lançadas entre uma extração e
  outra ou atribuídas a região diferente — vale confirmar com o TI qual
  regra exata o resumo usa.
- **TOPs** encontradas: 500 venda, 501 bonificação, 504/512 refaturamento,
  506 conta e ordem, 513 zona franca, 240/241/252/253 devoluções.
- **Fórmulas do resumo de metas** (conferidas linha a linha, recalculadas na
  view `vw_meta`):
  - Valor Fat. Previsto = Meta × P.M. Meta
  - Diferença = Meta − Vendido
  - Prévia = Meta − Vendido − Fechado
  - % Meta = Vendido ÷ Meta
  - % Prev. = (Vendido + Fechado) ÷ Meta
  - P.M. Real. = Valor Faturado ÷ Vendido
  - Quando Meta = 0 o relatório mostra 100%; a base grava vazio (sem meta).
- O resumo de metas **não traz o código do vendedor nem o mês**: o código é
  resolvido pelo apelido e o mês vem da data de emissão (ou é informado no
  upload). Na fase 2 ambos vêm direto da TGFMET.
- Vendedores com meta e sem venda no mês: JAIRO SOUSA, MARIA HELENA.

## Checklist para o TI antes da fase 2

1. Criar usuário de integração com acesso de leitura e liberar a API
   (token + appkey do gateway Sankhya).
2. Abrir os dois relatórios atuais no Sankhya e copiar a SQL de cada um
   para `vendas.sql` / `metas.sql`, mantendo os `AS` das colunas.
3. Confirmar nomes dos campos AD_ e as TOPs de bonificação.
4. Rodar o conector para um mês já importado por planilha e comparar os
   totais na tela de conciliação.
