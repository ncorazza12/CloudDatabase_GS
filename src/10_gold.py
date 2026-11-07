from pathlib import Path
import numpy as np
import pandas as pd

S, G = Path("data/silver"), Path("data/gold")
G.mkdir(parents=True, exist_ok=True)

mun = pd.read_parquet(S / "municipios_escopo.parquet")
mun = mun[mun["tem_era5"]]
era = pd.read_parquet(S / "era5_chuva_diaria.parquet")
era = era[era["tipo"] == "municipio"].copy()
era["cod_ibge"] = era["id"].astype(int)
era = era.sort_values(["cod_ibge", "dia"]).reset_index(drop=True)

# ---- Features diárias: acumulados móveis
g = era.groupby("cod_ibge")["chuva_era5_mm"]
for n in (3, 7, 30):
    era[f"acc{n}"] = g.transform(lambda s, n=n: s.rolling(n).sum())
era["mes"] = era["dia"].dt.month
era["ym"] = era["dia"].dt.to_period("M").dt.to_timestamp()
era["dia_chuva"] = era["chuva_era5_mm"] >= 1
era["ge20"] = era["chuva_era5_mm"] >= 20
era["ge50"] = era["chuva_era5_mm"] >= 50

# ---- Agregação município-mês
mm = era.groupby(["cod_ibge", "ym"], as_index=False).agg(
    chuva_mes_mm=("chuva_era5_mm", "sum"), chuva_max_dia_mm=("chuva_era5_mm", "max"),
    dias_chuva=("dia_chuva", "sum"), dias_ge20mm=("ge20", "sum"), dias_ge50mm=("ge50", "sum"),
    acc3_max=("acc3", "max"), acc7_max=("acc7", "max"), acc30_max=("acc30", "max"))
mm["ano"], mm["mes"] = mm["ym"].dt.year, mm["ym"].dt.month
mm = mm.sort_values(["cod_ibge", "ym"])
mm["chuva_mes_lag1"] = mm.groupby("cod_ibge")["chuva_mes_mm"].shift(1)
clim = mm.groupby(["cod_ibge", "mes"])["chuva_mes_mm"].transform("mean")
mm["anomalia_mensal"] = mm["chuva_mes_mm"] / clim.replace(0, np.nan)
p95 = era.loc[era["dia_chuva"]].groupby("cod_ibge")["chuva_era5_mm"].quantile(0.95).rename("p95_dia_chuvoso").reset_index()
mm = mm.merge(p95, on="cod_ibge", how="left")
mm["razao_max_p95"] = mm["chuva_max_dia_mm"] / mm["p95_dia_chuvoso"]
mm["estacao_chuvosa"] = mm["mes"].isin([10, 11, 12, 1, 2, 3]).astype(int)

# ---- Eventos do Atlas
at = pd.read_parquet(S / "atlas_sp_hidro_geo.parquet")
at["cod_ibge"] = at["Cod_IBGE_Mun"].astype(int)
at["dia"] = pd.to_datetime(at["Data_Evento"]).dt.normalize()
at["ym"] = at["dia"].dt.to_period("M").dt.to_timestamp()
at["reconhecido"] = (at["Status"] == "Reconhecido").astype(int)
at["desabrigados_desalojados"] = at["DH_DESABRIGADOS"].fillna(0) + at["DH_DESALOJADOS"].fillna(0)
ev = at.groupby(["cod_ibge", "ym"], as_index=False).agg(
    n_eventos=("Protocolo_S2iD", "count"), n_reconhecidos=("reconhecido", "sum"),
    mortos=("DH_MORTOS", "sum"), desabrigados_desalojados=("desabrigados_desalojados", "sum"),
    danos_humanos=("DH_total_danos_humanos_diretos", "sum"),
    danos_materiais_rs=("DM_total_danos_materiais", "sum"), prejuizos_rs=("PE_PLePR", "sum"))

painel = mm.merge(ev, on=["cod_ibge", "ym"], how="left")
for c in ev.columns[2:]:
    painel[c] = painel[c].fillna(0)
painel["ocorrencia"] = (painel["n_eventos"] > 0).astype(int)
painel = painel.merge(mun[["cod_ibge", "municipio", "mesorregiao", "lat", "lon"]], on="cod_ibge", how="left")
dem_arq = S / "municipios_demografia.parquet"
dem = pd.read_parquet(dem_arq) if dem_arq.exists() else None
if dem is not None:
    painel = painel.merge(dem, on="cod_ibge", how="left")
painel.to_parquet(G / "gold_municipio_mes.parquet", index=False)

# ---- Perfil por município
gm = painel.groupby("cod_ibge", as_index=False).agg(
    municipio=("municipio", "first"), mesorregiao=("mesorregiao", "first"), lat=("lat", "first"), lon=("lon", "first"),
    chuva_total_mm=("chuva_mes_mm", "sum"), dias_ge50mm=("dias_ge50mm", "sum"),
    meses_com_evento=("ocorrencia", "sum"), n_eventos=("n_eventos", "sum"), n_reconhecidos=("n_reconhecidos", "sum"),
    desabrigados_desalojados=("desabrigados_desalojados", "sum"), danos_materiais_rs=("danos_materiais_rs", "sum"))
gm["chuva_media_anual_mm"] = gm["chuva_total_mm"] / 13
if dem is not None:
    gm = gm.merge(dem, on="cod_ibge", how="left")
    gm["eventos_por_100mil_hab"] = gm["n_eventos"] / gm["populacao_2022"] * 1e5
gm.to_parquet(G / "gold_municipio.parquet", index=False)

# ---- Chuva que precedeu cada evento
e = at[["Protocolo_S2iD", "cod_ibge", "Nome_Municipio", "dia", "descricao_tipologia", "Status", "reconhecido",
        "desabrigados_desalojados", "DH_MORTOS", "DM_total_danos_materiais", "PE_PLePR"]].merge(
    era[["cod_ibge", "dia", "chuva_era5_mm", "acc3", "acc7", "acc30"]], on=["cod_ibge", "dia"], how="inner")
hist = era.dropna(subset=["acc7"]).groupby("cod_ibge")["acc7"]
e["pct_acc7"] = [np.nan if pd.isna(v) else float((hist.get_group(c) <= v).mean()) for c, v in zip(e["cod_ibge"], e["acc7"])]
e.to_parquet(G / "gold_eventos.parquet", index=False)

print("Painel:", painel.shape, "| municípios:", painel["cod_ibge"].nunique(), "| meses:", painel["ym"].nunique())
print("Município-meses com evento: %d (%.2f%%) | eventos no painel: %d" % (painel["ocorrencia"].sum(), 100 * painel["ocorrencia"].mean(), painel["n_eventos"].sum()))
print("Eventos com chuva associada:", len(e), "| sem acumulados (início de jan/2013):", int(e["acc7"].isna().sum()))
print("Mediana de chuva acumulada em 7 dias (mm): eventos = %.1f | todos os dias = %.1f" % (e["acc7"].median(), era["acc7"].median()))
print("Mediana do percentil de acc7 nos eventos: %.2f" % e["pct_acc7"].median())
print("Spearman chuva_mes x n_eventos: %.3f" % painel[["chuva_mes_mm", "n_eventos"]].corr(method="spearman").iloc[0, 1])
print("Taxa de ocorrência por faixa de chuva máxima diária (mm):")
print(painel.groupby(pd.cut(painel["chuva_max_dia_mm"], [0, 20, 50, 100, 1000], right=False), observed=True)["ocorrencia"].agg(["mean", "size"]).to_string())
