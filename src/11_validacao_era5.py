import numpy as np
import pandas as pd
from pathlib import Path

S = Path("data/silver")
est = pd.read_parquet(S / "estacao_municipio_valida.parquet")[["codigo_wmo", "estacao", "cod_ibge", "latitude", "longitude"]]
inm = pd.read_parquet(S / "inmet_chuva_diaria_sp.parquet")
inm = inm[inm["dia_confiavel"] & (inm["dia"] >= "2013-01-01") & (inm["dia"] <= "2025-12-31")]
inm = inm.merge(est, on="codigo_wmo", how="inner")          # exclui a CRIOSFERA

era = pd.read_parquet(S / "era5_chuva_diaria.parquet")
me = era[era["tipo"] == "municipio"].copy()
me["cod_ibge"] = me["id"].astype(int)
me = me[["cod_ibge", "dia", "chuva_era5_mm"]]
mun = pd.read_parquet(S / "municipios_escopo.parquet")[["cod_ibge", "municipio", "lat", "lon"]]

d = inm.merge(me, on=["cod_ibge", "dia"], how="inner").merge(mun, on="cod_ibge", how="left")

def km(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = np.sin((lat2 - lat1) * p / 2) ** 2 + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    return 12742 * np.arcsin(np.sqrt(a))
d["dist_km"] = km(d["latitude"], d["longitude"], d["lat"], d["lon"])

def metricas(x):
    obs, mod = x["chuva_mm"], x["chuva_era5_mm"]
    m = x.assign(ym=x["dia"].dt.to_period("M")).groupby("ym").agg(o=("chuva_mm", "sum"), e=("chuva_era5_mm", "sum"), n=("dia", "count"))
    m = m[m["n"] >= 20]
    return pd.Series({"dias": len(x), "dist_km": x["dist_km"].iloc[0],
                      "r_diario": obs.corr(mod), "rho_diario": obs.corr(mod, method="spearman"),
                      "vies_mm_dia": (mod - obs).mean(), "rmse_mm": float(np.sqrt(((mod - obs) ** 2).mean())),
                      "r_mensal": m["o"].corr(m["e"]), "dias_obs_20mm": int((obs >= 20).sum())})

res = d.groupby(["codigo_wmo", "estacao", "cod_ibge"]).apply(metricas).reset_index()
print(res.sort_values("r_diario", ascending=False).round(2).to_string(index=False))
print("\nEstações comparadas: %d | mediana r diário: %.2f | mediana r mensal: %.2f | viés mediano: %.2f mm/dia" %
      (len(res), res["r_diario"].median(), res["r_mensal"].median(), res["vies_mm_dia"].median()))
res["faixa_km"] = pd.cut(res["dist_km"], [0, 10, 25, 50, 1000])
print("\nMediana por distância estação–ponto do município:")
print(res.groupby("faixa_km", observed=True)[["r_diario", "r_mensal", "vies_mm_dia"]].median().round(2)
      .assign(estacoes=res.groupby("faixa_km", observed=True).size()).to_string())
o20, m20 = d["chuva_mm"] >= 20, d["chuva_era5_mm"] >= 20
print("\nDias com >=20 mm medidos: %d | ERA5 também >=20 mm: %.1f%% | alarmes falsos (ERA5>=20 sem medição>=20): %.1f%%" %
      (o20.sum(), 100 * (o20 & m20).sum() / o20.sum(), 100 * (~o20 & m20).sum() / m20.sum()))
res.drop(columns="faixa_km").round(3).to_csv("docs/validacao_era5_inmet.csv", index=False, encoding="utf-8-sig")

pt = era[era["tipo"] == "estacao"].rename(columns={"id": "codigo_wmo"})[["codigo_wmo", "dia", "chuva_era5_mm"]]
x = inm.merge(pt, on=["codigo_wmo", "dia"])
for cod, g in x.groupby("codigo_wmo"):
    print(f"\nMesmo ponto (ERA5 nas coordenadas da estação {cod}): dias={len(g)} | r={g['chuva_mm'].corr(g['chuva_era5_mm']):.2f} | viés={(g['chuva_era5_mm']-g['chuva_mm']).mean():.2f} mm/dia")

at = pd.read_parquet(S / "atlas_sp_hidro_geo.parquet")
at["dia"] = pd.to_datetime(at["Data_Evento"]).dt.normalize()
top = me.nlargest(15, "chuva_era5_mm").merge(mun[["cod_ibge", "municipio"]], on="cod_ibge")
top["eventos_atlas_3d"] = [int(((at["Cod_IBGE_Mun"] == r.cod_ibge) & ((at["dia"] - r.dia).abs() <= pd.Timedelta(days=3))).sum()) for r in top.itertuples()]
print("\nOs 15 maiores dias de chuva ERA5 e registros do Atlas (±3 dias, mesmo município):")
print(top[["dia", "municipio", "chuva_era5_mm", "eventos_atlas_3d"]].to_string(index=False))
