# Sistema Vendas x Metas

Sistema para lançar e acompanhar vendas e metas, com a mesma estrutura do Sankhya.
Os dados entram de duas formas, que convivem:

- **lançamento manual** no próprio sistema: notas de venda (cabeçalho + itens), metas do mês e
  todos os cadastros (vendedores, clientes, produtos, regiões, TOPs, empresas);
- **importação das planilhas** exportadas do Sankhya: *Demonstrativo Mensal das Vendas Efetuadas*
  e *Resumo Geral das Metas/Vendas*.

## Como rodar

**Windows (mais fácil)**

1. Instale o Python 3.11 ou mais novo em https://www.python.org/downloads/ e, na primeira tela
   do instalador, marque **"Add python.exe to PATH"**.
2. Baixe o código: no GitHub, abra o branch `claude/planilhas-dashboard-sistematizacao-j1s82p`,
   clique em **Code › Download ZIP** e extraia a pasta.
3. Dê dois cliques em **`iniciar.bat`**. Na primeira vez ele instala o que precisa (alguns minutos);
   depois abre o sistema no navegador em http://localhost:8000.
4. Deixe a janela preta aberta enquanto usa o sistema. Para encerrar, feche a janela.

**Mac/Linux:** `./iniciar.sh` no terminal, dentro da pasta.

**Manual:** `pip install -r requirements.txt` e `python sistema.py`.

A base fica em `data/sistema.db` (SQLite, fora do git porque tem dados de clientes); faça cópia
desse arquivo para ter backup.

**Acesso de outros computadores da rede**

1. Feche o `iniciar.bat` se estiver aberto.
2. Na primeira vez, clique com o botão direito em **`iniciar_rede.bat`** › **Executar como
   administrador** (libera a porta 8000 no Firewall do Windows). Das próximas vezes, dois cliques bastam.
3. A janela mostra o endereço para os outros computadores, por exemplo `http://192.168.148.231:8000`.
4. Se ainda não abrir: em Configurações › Rede e Internet, deixe a rede como **Privada** (o firewall
   não libera em rede Pública) e confira se os dois computadores estão na mesma rede.
   Em Mac/Linux: `./iniciar.sh --rede`.

Primeiro uso: **Dados › Importar planilhas** e envie as duas planilhas do mês. Os cadastros são
criados a partir delas; depois é só lançar e ajustar pelo sistema.

## Telas

| Menu | Tela | O que faz |
|---|---|---|
| Análise | Visão geral | faturado, % da meta em kg e R$, carteira, clientes, devoluções, gráficos e rankings |
| | Metas | meta x vendido x carteira por vendedor, supervisor, gerente, categoria, produto ou região |
| | Vendas | faturamento por cliente, produto, UF, rede, mix, TOP, data, origem... |
| Lançamentos | Notas de venda | lista, busca, nova nota, alterar, excluir; itens com produto, kg, valor, ST, CT-e |
| | Metas do mês | lista, nova meta, alterar, excluir, copiar metas de um mês para outro |
| Cadastros | Vendedores, Clientes, Produtos, Regiões, TOPs, Empresas | incluir, alterar (inclusive o código), excluir com checagem de uso |
| Dados | Importar planilhas | envio das planilhas do Sankhya |
| | Histórico | importações feitas, desfazer uma importação, exportar CSV e a base SQLite |
| | Validação | confere a base contra os totais de cada planilha importada, integridade e conciliação |

Tema dia/noite no rodapé do menu. Funciona no celular (menu vira gaveta).

## Regras

- **Realizado** = vendas (V) + devoluções (D). Bonificação (B) aparece à parte.
- Na nota, digite valores positivos; o sinal vem da TOP (devolução e bonificação ficam negativas).
- O realizado da meta é calculado das notas pela mesma chave do resumo: região + vendedor + produto.
  O "Vendido" do resumo importado fica guardado só para conferência (tela Validação).
- Importar uma planilha substitui as notas/metas **importadas** do mesmo mês. O que foi lançado ou
  alterado no sistema fica, a não ser que a planilha traga uma nota com o mesmo Nº Único.
- Vendedor que só aparece no resumo de metas recebe código provisório (900000+) até o código real
  chegar ou ser corrigido no cadastro. Alterar um código atualiza notas e metas.

## Estrutura

```
sistema.py                    inicia o servidor (FastAPI + interface web)
web/                          interface: index.html, app.js, app.css
vendas_bi/schema.sql          tabelas no padrão Sankhya (TGFCAB, TGFITE, TGFVEN, TGFPAR, TGFPRO, TGFTOP, TGFMET) e views
vendas_bi/api.py              rotas /api
vendas_bi/servicos.py         cadastros, notas, metas e validação
vendas_bi/importer.py         leitura das planilhas e gravação nos cadastros/lançamentos
vendas_bi/consultas.py        indicadores e agrupamentos do painel
vendas_bi/layouts.py          de-para: coluna do relatório -> coluna da base -> campo Sankhya
vendas_bi/sankhya/            SQLs e conector da API do Sankhya (fase 2) + MAPEAMENTO.md
scripts/importar.py           importação pela linha de comando (agendável)
dashboard.html                painel offline em arquivo único (não precisa do servidor)
scripts/gerar_dashboard.py    gera o painel offline com os dados das planilhas embutidos
tests/                        testes (pytest)
```

## API

A interface usa a API em `/api` (documentação interativa em http://localhost:8000/docs).
Principais rotas: `/api/cadastros/{vendedores|clientes|produtos|regioes|tops|empresas}`,
`/api/notas`, `/api/metas`, `/api/importar`, `/api/cargas`, `/api/painel`, `/api/validacao`,
`/api/exportar/{vendas|metas}.csv`, `/api/exportar/base.db`.

## Sankhya

Ver [`vendas_bi/sankhya/MAPEAMENTO.md`](vendas_bi/sankhya/MAPEAMENTO.md): tabelas equivalentes,
de-para de colunas, regras levantadas das planilhas e o plano para trocar a importação de
planilhas pela leitura direta da API do Sankhya.

## Testes

```bash
python -m pytest
```
