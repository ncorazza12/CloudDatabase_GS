import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="CitizenTech SP - Chuvas extremas e desastres", layout="wide")
G = Path("data/gold")


@st.cache_data
def carregar():
    gm = pd.read_parquet(G / "gold_municipio_cluster.parquet")
    p = pd.read_parquet(G / "gold_municipio_mes.parquet")
    e = pd.read_parquet(G / "gold_eventos.parquet")
    geo = json.loads(Path("data/bronze/ibge/malha_municipios_sp.geojson").read_text(encoding="utf-8"))
    return gm, p, e, geo


gm, p, e, geo = carregar()
gm["cod"] = gm["cod_ibge"].astype(str)
gm["cluster_txt"] = "Cluster " + gm["cluster"].astype(str)

st.title("Chuvas extremas e desastres no estado de SP (2013-2025)")
st.caption(f"CitizenTech | Fontes: Atlas Digital de Desastres, ERA5 (Open-Meteo), INMET, IBGE | "
           f"Escopo: {len(gm)} de 645 municípios (os com série ERA5 baixada)")

st.sidebar.header("Filtros")
clusters = sorted(gm["cluster_txt"].unique())
cl = st.sidebar.multiselect("Clusters", clusters, default=clusters)
pop_min = st.sidebar.number_input("População mínima (Censo 2022)", 0, 1_000_000, 0, step=10_000)
d = gm[gm["cluster_txt"].isin(cl) & (gm["populacao_2022"] >= pop_min)].copy()
pf = p[p["cod_ibge"].isin(d["cod_ibge"])]
ef = e[e["cod_ibge"].isin(d["cod_ibge"])]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Municípios", len(d))
k2.metric("Eventos registrados", int(d["n_eventos"].sum()))
k3.metric("Desabrigados + desalojados", f"{int(d['desabrigados_desalojados'].sum()):,}".replace(",", "."))
k4.metric("Municípios sem registro", int((d["n_eventos"] == 0).sum()))

t1, t2, t3, t4, t5 = st.tabs(["Mapa", "Prioridades", "Tempo", "Chuva x eventos", "Qualidade e limites"])

IND = {"Índice de prioridade (0-100)": "indice_prioridade", "Nº de eventos": "n_eventos",
       "Eventos por 100 mil hab.": "eventos_por_100mil_hab", "Dias >= 50 mm por ano (ERA5)": "dias_ge50_ano",
       "Desabrigados + desalojados": "desabrigados_desalojados", "Cluster": "cluster_txt"}

with t1:
    nome = st.selectbox("Indicador", list(IND))
    col = IND[nome]
    kw = {} if col == "cluster_txt" else {"color_continuous_scale": "YlOrRd"}
    fig = px.choropleth_map(d, geojson=geo, locations="cod", featureidkey="properties.codarea", color=col,
                               hover_name="municipio", hover_data={"cod": False, "n_eventos": True, "populacao_2022": True,
                                                                   "indice_prioridade": ":.1f"},
                               map_style="carto-positron", center={"lat": -22.4, "lon": -48.6}, zoom=5.3,
                               opacity=0.8, height=620, **kw)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Municípios em branco estão fora do escopo (sem série ERA5 baixada) ou foram filtrados.")
    perfil = d.groupby("cluster_txt").agg(municipios=("cod_ibge", "count"), chuva_anual_mm=("chuva_media_anual_mm", "mean"),
                                          dias_ge50_ano=("dias_ge50_ano", "mean"), pop_mediana=("populacao_2022", "median"),
                                          eventos=("n_eventos", "sum")).round(1)
    st.dataframe(perfil)

with t2:
    nome2 = st.selectbox("Ordenar por", list(IND)[:-1], key="ord")
    cols = ["municipio", "cluster_txt", "indice_prioridade", "n_eventos", "meses_com_evento", "eventos_por_100mil_hab",
            "dias_ge50_ano", "populacao_2022", "desabrigados_desalojados"]
    st.dataframe(d.sort_values(IND[nome2], ascending=False).head(20)[cols].round(2), hide_index=True)
    st.subheader("Perigo alto e nenhum registro: candidatos à verificação")
    sem = d[(d["pct_perigo"] >= 0.9) & (d["n_eventos"] == 0)].sort_values("dias_ge50_ano", ascending=False)
    st.dataframe(sem[["municipio", "dias_ge50_ano", "populacao_2022"]].round(2), hide_index=True)
    st.caption("Chuva forte no ERA5 sem registro no Atlas não prova subnotificação: o ERA5 marca muitos dias fortes que as estações não confirmam.")

with t3:
    ano = pf.groupby("ano").agg(eventos=("n_eventos", "sum"), dias_ge50mm=("dias_ge50mm", "sum")).reset_index()
    mes = pf.groupby("mes").agg(eventos=("n_eventos", "sum"), dias_ge50mm=("dias_ge50mm", "sum")).reset_index()
    mes["eventos_por_100_dias_ge50"] = (100 * mes["eventos"] / mes["dias_ge50mm"]).round(1)
    a, b = st.columns(2)
    a.plotly_chart(px.bar(ano, x="ano", y="eventos", title="Eventos registrados por ano"), use_container_width=True)
    b.plotly_chart(px.bar(ano, x="ano", y="dias_ge50mm", title="Dias-município com chuva >= 50 mm (ERA5)"), use_container_width=True)
    c, f = st.columns(2)
    c.plotly_chart(px.bar(mes, x="mes", y="eventos", title="Eventos por mês do ano"), use_container_width=True)
    f.plotly_chart(px.bar(mes, x="mes", y="eventos_por_100_dias_ge50", title="Eventos por 100 dias >= 50 mm, por mês"), use_container_width=True)

with t4:
    pf2 = pf.assign(faixa=pd.cut(pf["chuva_max_dia_mm"], [0, 20, 50, 100, 1000], right=False,
                                 labels=["< 20 mm", "20-50 mm", "50-100 mm", ">= 100 mm"]))
    taxa = pf2.groupby("faixa", observed=True).agg(meses=("ocorrencia", "size"), com_evento=("ocorrencia", "sum")).reset_index()
    taxa["taxa_pct"] = (100 * taxa["com_evento"] / taxa["meses"]).round(2)
    st.plotly_chart(px.bar(taxa, x="faixa", y="taxa_pct", text="com_evento",
                           title="% de município-meses com evento por chuva máxima diária (rótulo = nº com evento)"),
                    use_container_width=True)
    st.plotly_chart(px.histogram(ef.dropna(subset=["pct_acc7"]), x="pct_acc7", nbins=20,
                                 title="Percentil da chuva de 7 dias no dia do evento (frente ao histórico do município)"),
                    use_container_width=True)
    st.caption("A faixa >= 100 mm tem poucos casos: a taxa é estatisticamente frágil.")

with t5:
    st.markdown("""
- **Escopo:** 293 dos 645 municípios (Adamantina a Jumirim, ordem do código IBGE), por causa do limite diário da API Open-Meteo. Cobre 135 dos 339 registros do Atlas (39,8%).
- **ERA5 x INMET (23 estações):** correlação diária mediana 0,52 e mensal 0,82; viés de -0,59 mm/dia; o ERA5 marca 25,4% dos dias >= 20 mm medidos, e 54,7% dos dias ERA5 >= 20 mm não se confirmam.
- **Atlas:** depende de notificação municipal; "sem registro" não significa "sem desastre". O ano de 2013 concentra 37% dos eventos do escopo, sem explicação só pelo clima.
- **Modelo:** apenas 21 eventos no teste (2023-2025): serve para triagem, não para previsão.
- **Não integrado:** renda, saneamento e outros indicadores socioeconômicos.
""")
    arq = Path("docs/validacao_era5_inmet.csv")
    if arq.exists():
        st.subheader("Validação por estação")
        st.dataframe(pd.read_csv(arq), hide_index=True)
