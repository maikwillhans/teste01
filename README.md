# Vendas x Metas — base de dados + dashboard

Sistematiza os dois relatórios exportados do Sankhya:

- **Demonstrativo Mensal das Vendas Efetuadas**: item de nota (cliente, produto, TOP, kg, R$);
- **Resumo Geral das Metas/Vendas**: meta × vendido × carteira por região/vendedor/produto;

numa base SQLite única, com um dashboard e uma tela para atualizar a base enviando as planilhas.
A base usa os nomes de campo do Sankhya para que a origem possa passar a ser a API do ERP
sem mexer no dashboard — veja [`vendas_bi/sankhya/MAPEAMENTO.md`](vendas_bi/sankhya/MAPEAMENTO.md).

## Como usar (HTML — recomendado)

Abra o arquivo **`dashboard.html`** no navegador (Chrome, Edge ou Firefox). Não precisa instalar nada;
só precisa de internet na primeira abertura para carregar o leitor de planilhas.

1. Aba **Importar planilhas**: arraste o Demonstrativo e o Resumo de Metas como saem do Sankhya.
2. Os dados ficam guardados no próprio navegador e voltam quando você reabrir o arquivo.
3. Aba **Base de dados**: exporta CSV (colunas com nomes de campo do Sankhya) e a base completa
   em JSON, que pode ser restaurada em outro computador.

Enquanto nada é importado, o painel mostra dados de exemplo fictícios, com um aviso no topo.

### Painel já com os dados reais

```bash
python scripts/gerar_dashboard.py data/Demonstrativo*.xls data/RESUMO*.xls
```

Gera `data/painel_vendas_metas.html` com as planilhas embutidas (fica fora do git, pois tem dados
de clientes). A página **Validação** confere o painel contra as planilhas originais: linhas,
somas de cada coluna numérica, valores distintos, fórmulas do resumo de metas linha a linha e o
cruzamento entre os dois relatórios. A página **Dados completos** mostra todas as linhas e
colunas das duas planilhas, com busca e exportação.

## Versão em Python (opcional)

A mesma base em SQLite com dashboard Streamlit, útil para rodar num servidor ou agendar cargas:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Abra http://localhost:8501, vá em **Importar dados** e envie as duas planilhas como saem
do sistema (.xls, .xlsx ou .csv). O tipo é detectado sozinho.

- Cada envio **substitui o mês** que está no arquivo; reenvie durante o mês quantas vezes quiser.
- Arquivo idêntico ao último importado é ignorado.
- O resumo de metas não traz o mês: usa o mês da data de emissão, ou o que você informar.
- Pela linha de comando (para agendar): `python scripts/importar.py arquivo1.xls arquivo2.xls`

A base fica em `data/vendas.db` (fora do git, pois tem dados de clientes). Outro caminho:
variável `VENDAS_BI_DB`.

## Dashboard

| Aba | Conteúdo |
|---|---|
| Visão geral | faturado líquido, volume, % meta em kg e R$ (com e sem carteira), clientes positivados, devoluções, bonificação, faturamento diário e acumulado × meta, meta por supervisor e categoria |
| Metas | meta × vendido × carteira por vendedor, supervisor, gerente, categoria, produto ou região, com situação pelo ritmo do mês |
| Vendas | ranking por cliente, produto, UF, cidade, perfil, rede, mix, linha, TOP... |
| Importar dados | upload das planilhas e conciliação resumo de metas × demonstrativo |
| Base de dados | histórico de cargas e exportação CSV/SQLite |

Filtros de período, gerente, supervisor e vendedor ficam na barra lateral.

## Estrutura

```
dashboard.html                dashboard em HTML (arquivo único, roda no navegador)
app.py                        dashboard (Streamlit)
vendas_bi/layouts.py          de-para: coluna do relatório -> coluna da base -> campo Sankhya
vendas_bi/schema.sql          tabelas carga, fato_venda, fato_meta e views (vw_meta, dim_*)
vendas_bi/importer.py         leitura, validação e carga das planilhas
vendas_bi/consultas.py        indicadores usados no dashboard
vendas_bi/sankhya/            SQLs modelo + conector da API (fase 2) + mapeamento
scripts/importar.py           importação por linha de comando
tests/                        testes (pytest)
```

## Regras adotadas

- **Realizado** = vendas (V) + devoluções (D, já negativas). Bonificação (B) aparece à parte.
- Indicadores da meta recalculados com as fórmulas do próprio relatório
  (previsto = meta × P.M. meta; % prev. = (vendido + fechado) ÷ meta; etc.).
- Situação na aba Metas: ✔ atingiu; ▲ dentro do ritmo (≥ 90% do esperado para os dias úteis
  seg–sáb decorridos); ✖ abaixo do ritmo.

## Testes

```bash
python -m pytest
```
