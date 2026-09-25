"""Dashboard de Vendas x Metas.

Rodar:  streamlit run app.py
"""

from __future__ import annotations

import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from vendas_bi import consultas as q
from vendas_bi.db import BANCO_PADRAO, conectar
from vendas_bi.importer import ErroImportacao, importar

st.set_page_config(page_title="Vendas x Metas", page_icon="📊", layout="wide")

# ------------------------------------------------------------------ aparência
AZUL, LARANJA, VERDE_AQUA = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA_2, MUDO, GRADE, BASE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SUPERFICIE = "#fcfcfb"
STATUS = {"bom": ("✔", "Atingiu", "#0ca30c"), "atencao": ("▲", "Em curso", "#fab219"),
          "critico": ("✖", "Abaixo", "#d03b3b"), "sem": ("–", "Sem meta", MUDO)}

st.markdown(
    """<style>
    [data-testid="stMetricValue"] { font-size: 1.6rem; }
    [data-testid="stMetric"] { background: #fcfcfb; border: 1px solid rgba(11,11,11,.10);
                               border-radius: 8px; padding: 12px 14px; }
    </style>""",
    unsafe_allow_html=True,
)


def brl(v, casas=0):
    if v is None or pd.isna(v):
        return "–"
    s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def num(v, casas=0, sufixo=""):
    if v is None or pd.isna(v):
        return "–"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".") + sufixo


def brl_curto(v):
    """Valor monetário compacto para os cartões (R$ 45,06 mi / R$ 636,1 mil)."""
    if v is None or pd.isna(v):
        return "–"
    if abs(v) >= 1e6:
        return f"R$ {num(v / 1e6, 2)} mi"
    if abs(v) >= 1e4:
        return f"R$ {num(v / 1e3, 1)} mil"
    return brl(v)


def ton(kg):
    return "–" if kg is None or pd.isna(kg) else num(kg / 1000, 1, " t")


def pct(v, casas=1):
    return "–" if v is None or pd.isna(v) else num(v * 100, casas, "%")


def status(perc, esperado):
    """Compara o % atingido com o % do mês já decorrido (ritmo)."""
    if perc is None or pd.isna(perc):
        return "sem"
    if perc >= 1:
        return "bom"
    return "atencao" if perc >= esperado * 0.9 else "critico"


def layout_fig(fig, altura=360, **kw):
    fig.update_layout(
        height=altura, margin=dict(l=8, r=8, t=40, b=8), paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE, font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif",
                                           color=TINTA_2, size=12),
        hoverlabel=dict(bgcolor="white", font_color=TINTA), separators=",.",
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0), bargap=0.25, **kw,
    )
    fig.update_xaxes(gridcolor=GRADE, linecolor=BASE, tickfont_color=MUDO, zeroline=False)
    fig.update_yaxes(gridcolor=GRADE, linecolor=BASE, tickfont_color=MUDO, zeroline=False)
    return fig


def grafico_meta(df: pd.DataFrame, titulo: str, rotulo: str = "kg"):
    """Barra = realizado, traço = meta, barra clara = carteira (fechado)."""
    df = df[df.meta_kg > 0].nlargest(40, "meta_kg").sort_values("perc_meta")
    fig = go.Figure()
    fig.add_bar(y=df.grupo, x=df.vendido_kg, orientation="h", name="Vendido", marker_color=AZUL,
                marker_cornerradius=4, customdata=df[["perc_meta", "meta_kg"]],
                hovertemplate="<b>%{y}</b><br>Vendido: %{x:,.0f} kg<br>Meta: %{customdata[1]:,.0f} kg"
                              "<br>Atingido: %{customdata[0]:.1%}<extra></extra>")
    fig.add_bar(y=df.grupo, x=df.carteira_kg, orientation="h", name="Carteira (fechado)",
                marker_color="#b7d3f6", marker_cornerradius=4,
                hovertemplate="<b>%{y}</b><br>Carteira: %{x:,.0f} kg<extra></extra>")
    fig.add_scatter(y=df.grupo, x=df.meta_kg, mode="markers", name="Meta",
                    marker=dict(symbol="line-ns", size=18, line=dict(width=3, color=TINTA)),
                    hovertemplate="<b>%{y}</b><br>Meta: %{x:,.0f} kg<extra></extra>")
    fig.update_layout(barmode="stack", title=dict(text=titulo, font_color=TINTA))
    fig.update_xaxes(title_text=rotulo)
    return layout_fig(fig, altura=max(340, 30 * len(df) + 120))


def tabela_meta(df: pd.DataFrame, esperado: float, nome: str) -> pd.DataFrame:
    out = pd.DataFrame({
        nome: df.grupo,
        "Situação": [f"{STATUS[s][0]} {STATUS[s][1]}" for s in (status(p, esperado) for p in df.perc_meta)],
        "Meta (kg)": df.meta_kg, "Vendido (kg)": df.vendido_kg, "% Meta": df.perc_meta * 100,
        "Carteira (kg)": df.carteira_kg, "% c/ Carteira": df.perc_prev * 100,
        "Meta (R$)": df.meta_valor, "Faturado (R$)": df.vendido_valor,
        "% Meta R$": df.perc_meta_valor * 100,
    })
    return out


FORMATO_META = {
    "Meta (kg)": st.column_config.NumberColumn(format="%.0f"),
    "Vendido (kg)": st.column_config.NumberColumn(format="%.0f"),
    "Carteira (kg)": st.column_config.NumberColumn(format="%.0f"),
    "% Meta": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=120),
    "% c/ Carteira": st.column_config.NumberColumn(format="%.1f%%"),
    "Meta (R$)": st.column_config.NumberColumn(format="R$ %.0f"),
    "Faturado (R$)": st.column_config.NumberColumn(format="R$ %.0f"),
    "% Meta R$": st.column_config.NumberColumn(format="%.1f%%"),
}


# ------------------------------------------------------------------ dados
@st.cache_resource
def conexao():
    return conectar()


conn = conexao()
periodos = q.periodos(conn)

with st.sidebar:
    st.header("📊 Vendas x Metas")
    if periodos:
        periodo = st.selectbox("Período", periodos, format_func=lambda p: f"{p[5:]}/{p[:4]}")
        op = q.opcoes(conn, periodo)
        gerentes = st.multiselect("Gerente", op["gerente"], placeholder="Todos")
        supervisores = st.multiselect("Supervisor", op["supervisor"], placeholder="Todos")
        vendedores = st.multiselect("Vendedor", op["vendedor"], placeholder="Todos")
        filtro = q.Filtro(periodo, gerentes, supervisores, vendedores)
    else:
        filtro = None
        st.info("Base vazia. Importe as planilhas na aba **Importar dados**.")
    st.caption(f"Base: `{BANCO_PADRAO.name}`")

abas = st.tabs(["Visão geral", "Metas", "Vendas", "Importar dados", "Base de dados"])


# ------------------------------------------------------------------ visão geral
def dias_uteis_decorridos(periodo: str, ultima: str | None) -> float:
    """Fração do mês (em dias úteis seg-sáb) já decorrida até a última venda."""
    inicio = pd.Timestamp(f"{periodo}-01")
    fim = inicio + pd.offsets.MonthEnd(0)
    dias = pd.bdate_range(inicio, fim, freq="C", weekmask="Mon Tue Wed Thu Fri Sat")
    if not ultima:
        return 0.0
    return float((dias <= pd.Timestamp(ultima)).sum()) / len(dias)


def visao_geral():
    k = q.indicadores(conn, filtro)
    esperado = dias_uteis_decorridos(filtro.periodo, k["ultima_data"])
    st.caption(
        f"Movimento até **{pd.Timestamp(k['ultima_data']).strftime('%d/%m/%Y') if k['ultima_data'] else '–'}** · "
        f"{pct(esperado, 0)} do mês decorrido (dias úteis seg–sáb) · realizado = vendas − devoluções"
    )
    c = st.columns(6)
    c[0].metric("Faturado líquido", brl_curto(k["faturado"]), help="Vendas (V) menos devoluções (D), sem ST")
    c[1].metric("Volume", ton(k["kg"]))
    c[2].metric("% Meta (kg)", pct(k["perc_meta_kg"]),
                delta=f"{pct(k['perc_prev_kg'])} com carteira" if k["tem_meta"] else None,
                delta_color="off", help="Vendido do resumo de metas ÷ meta em kg")
    c[3].metric("% Meta (R$)", pct(k["perc_meta_valor"]),
                help="Valor faturado ÷ (meta kg × preço médio da meta)")
    c[4].metric("Clientes positivados", num(k["clientes"]), delta=f"{num(k['notas'])} notas", delta_color="off")
    c[5].metric("Devoluções", brl_curto(k["devolucao"]), delta=f"{pct(k['perc_devolucao'])} da venda",
                delta_color="off")

    c = st.columns(6)
    c[0].metric("Meta (R$)", brl_curto(k["meta_valor"]))
    c[1].metric("Meta (volume)", ton(k["meta_kg"]))
    c[2].metric("Carteira (fechado)", brl_curto(k["carteira_valor"]), delta=ton(k["carteira_kg"]),
                delta_color="off", help="Pedidos fechados ainda não faturados")
    c[3].metric("Falta p/ meta (R$)", brl_curto(max(k["meta_valor"] - k["vendido_valor"], 0)))
    c[4].metric("Preço médio", brl(k["preco_medio"], 2) + "/kg" if k["preco_medio"] else "–")
    c[5].metric("Bonificação", brl_curto(k["bonificacao"]))

    d = q.vendas_diarias(conn, filtro)
    esq, dir_ = st.columns(2)
    with esq:
        fig = go.Figure(go.Bar(x=d.data, y=d.faturado, marker_color=AZUL, marker_cornerradius=4,
                               hovertemplate="%{x|%d/%m}<br>R$ %{y:,.2f}<extra></extra>"))
        fig.update_layout(title=dict(text="Faturamento por dia (R$)", font_color=TINTA))
        fig.update_xaxes(tickformat="%d/%m")
        st.plotly_chart(layout_fig(fig), use_container_width=True)
    with dir_:
        fig = go.Figure(go.Scatter(x=d.data, y=d.faturado.cumsum(), mode="lines+markers", name="Acumulado",
                                   line=dict(color=AZUL, width=2), marker=dict(size=8),
                                   hovertemplate="%{x|%d/%m}<br>Acumulado: R$ %{y:,.0f}<extra></extra>"))
        if k["meta_valor"]:
            fig.add_hline(y=k["meta_valor"], line=dict(color=TINTA, width=1.5, dash="dash"),
                          annotation_text=f"Meta {brl(k['meta_valor'])}", annotation_font_color=TINTA_2)
        fig.update_layout(title=dict(text="Faturamento acumulado x meta (R$)", font_color=TINTA), showlegend=False)
        fig.update_xaxes(tickformat="%d/%m")
        st.plotly_chart(layout_fig(fig), use_container_width=True)

    if k["tem_meta"]:
        esq, dir_ = st.columns(2)
        with esq:
            st.plotly_chart(grafico_meta(q.meta_por(conn, filtro, "supervisor"), "Meta x vendido por supervisor"),
                            use_container_width=True)
        with dir_:
            st.plotly_chart(grafico_meta(q.meta_por(conn, filtro, "categoria"), "Meta x vendido por categoria"),
                            use_container_width=True)


    return esperado


# ------------------------------------------------------------------ metas
def metas(esperado):
    dims = {"Vendedor": "vendedor", "Supervisor": "supervisor", "Gerente": "gerente",
            "Categoria": "categoria", "Produto": "descrprod", "Região": "nomereg"}
    escolha = st.radio("Agrupar por", list(dims), horizontal=True)
    df = q.meta_por(conn, filtro, dims[escolha])
    if df.empty:
        st.info("Sem metas para o período. Importe o **Resumo Geral das Metas/Vendas**.")
    else:
        st.caption(f"Situação: ✔ atingiu a meta · ▲ dentro do ritmo esperado ({pct(esperado, 0)} do mês) · "
                   "✖ abaixo do ritmo")
        st.plotly_chart(grafico_meta(df, f"Meta x vendido por {escolha.lower()} (kg)"), use_container_width=True)
        st.dataframe(tabela_meta(df, esperado, escolha), hide_index=True, use_container_width=True,
                     column_config=FORMATO_META)


# ------------------------------------------------------------------ vendas
def vendas():
    dims = {"Cliente": "nomeparc", "Produto": "descrprod", "Vendedor": "vendedor", "UF": "uf",
            "Cidade": "cidade", "Perfil": "perfil", "Rede": "rede", "Mix comercial": "mix_comercial",
            "Mix bíblia": "mix_biblia", "Linha": "linha", "Grupo (conta estoque)": "grupoprod",
            "Tipo de operação (TOP)": "descroper"}
    c1, c2 = st.columns([3, 1])
    escolha = c1.selectbox("Agrupar por", list(dims))
    topn = c2.number_input("Mostrar top", 5, 100, 15, step=5)
    df = q.vendas_por(conn, filtro, dims[escolha])
    top = df.head(int(topn)).iloc[::-1]
    fig = go.Figure(go.Bar(y=top.grupo.fillna("(vazio)"), x=top.faturado, orientation="h", marker_color=AZUL,
                           marker_cornerradius=4, customdata=top[["kg", "clientes"]],
                           hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<br>%{customdata[0]:,.0f} kg"
                                         "<br>%{customdata[1]} clientes<extra></extra>"))
    fig.update_layout(title=dict(text=f"Faturamento líquido por {escolha.lower()} (R$)", font_color=TINTA))
    st.plotly_chart(layout_fig(fig, altura=max(320, 26 * len(top) + 90)), use_container_width=True)
    total = df.faturado.sum()
    tab = df.rename(columns={"grupo": escolha, "faturado": "Faturado (R$)", "kg": "Volume (kg)",
                             "devolucao": "Devolução (R$)", "clientes": "Clientes", "notas": "Notas",
                             "preco_medio": "Preço médio (R$/kg)"})
    tab.insert(2, "% do total", df.faturado / total * 100 if total else None)
    st.dataframe(tab, hide_index=True, use_container_width=True, column_config={
        "Faturado (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Volume (kg)": st.column_config.NumberColumn(format="%.1f"),
        "% do total": st.column_config.NumberColumn(format="%.1f%%"),
        "Devolução (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Preço médio (R$/kg)": st.column_config.NumberColumn(format="R$ %.2f"),
    })


# ------------------------------------------------------------------ montagem
if filtro:
    with abas[0]:
        esperado = visao_geral()
    with abas[1]:
        metas(esperado)
    with abas[2]:
        vendas()
else:
    for aba in abas[:3]:
        aba.info("Base vazia. Importe as planilhas na aba **Importar dados**.")

# ------------------------------------------------------------------ importar
with abas[3]:
    st.subheader("Atualizar a base com as planilhas do sistema")
    st.markdown(
        "Envie o **Demonstrativo Mensal das Vendas Efetuadas** e/ou o **Resumo Geral das Metas/Vendas** "
        "(.xls, .xlsx ou .csv, como exportados). O tipo é reconhecido automaticamente. Cada envio "
        "**substitui** os dados do mês correspondente — pode reenviar quantas vezes quiser durante o mês."
    )
    arquivos = st.file_uploader("Planilhas", type=["xls", "xlsx", "csv"], accept_multiple_files=True)
    c1, c2 = st.columns(2)
    periodo_meta = c1.text_input("Mês das metas (AAAA-MM)", placeholder="vazio = mês da data de emissão",
                                 help="O resumo de metas não traz o mês; por padrão usa a data de emissão.")
    forcar = c2.checkbox("Reimportar mesmo se o arquivo já foi importado")
    if st.button("Importar", type="primary", disabled=not arquivos):
        for arq in arquivos:
            try:
                r = importar(conn, arq.getvalue(), arq.name, periodo_meta.strip() or None, forcar)
            except ErroImportacao as e:
                st.error(f"**{arq.name}**: {e}")
                continue
            if r.ignorada:
                st.info(f"**{arq.name}**: já importado anteriormente, nada mudou.")
            else:
                st.success(f"**{arq.name}** → {r.tipo}, período {', '.join(r.periodos)}: "
                           f"{num(r.linhas)} linhas gravadas ({num(r.substituidas)} substituídas).")
            for aviso in r.avisos:
                st.warning(aviso)
        st.button("Atualizar painel")

    if filtro:
        with st.expander("Conciliação: Resumo de Metas x Demonstrativo"):
            conc = q.conciliacao(conn, filtro.periodo)
            st.caption("Itens (região × produto) em que o 'Vendido' do resumo de metas difere da soma do "
                       "demonstrativo. Pequenas diferenças são esperadas quando os relatórios são "
                       "extraídos em momentos diferentes.")
            st.dataframe(conc, hide_index=True, use_container_width=True)


# ------------------------------------------------------------------ base
with abas[4]:
    st.subheader("Histórico de cargas")
    st.dataframe(q.cargas(conn), hide_index=True, use_container_width=True)
    if filtro:
        st.subheader("Exportar")
        c1, c2, c3 = st.columns(3)
        c1.download_button("Vendas do período (CSV)", q.detalhe_vendas(conn, filtro).to_csv(
            index=False, sep=";", decimal=",").encode("utf-8-sig"), f"vendas_{filtro.periodo}.csv", "text/csv")
        c2.download_button("Metas do período (CSV)", q.detalhe_metas(conn, filtro).to_csv(
            index=False, sep=";", decimal=",").encode("utf-8-sig"), f"metas_{filtro.periodo}.csv", "text/csv")
        if BANCO_PADRAO.exists():
            c3.download_button("Base completa (SQLite)", BANCO_PADRAO.read_bytes(), "vendas.db")
