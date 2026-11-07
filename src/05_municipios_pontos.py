import json
from pathlib import Path
import geopandas as gpd
import pandas as pd

def nested(d, caminho):
    for c in caminho:
        d = d.get(c) if isinstance(d, dict) else None
    return d

raw = json.loads(Path("data/bronze/ibge/municipios_sp.json").read_text(encoding="utf-8"))
mun = pd.DataFrame([{
    "cod_ibge": int(m["id"]), "municipio": m["nome"],
    "mesorregiao": nested(m, ["microrregiao", "mesorregiao", "nome"]),
    "regiao_imediata": nested(m, ["regiao-imediata", "nome"]),
} for m in raw])
print("Municípios no JSON:", len(mun))

g = gpd.read_file("data/bronze/ibge/malha_municipios_sp.geojson")
print("Malha -> colunas:", list(g.columns), "| CRS:", g.crs, "| feições:", len(g))
col = next((c for c in ("codarea", "CD_MUN", "id") if c in g.columns), None)
if col is None:
    raise SystemExit("Coluna de código não encontrada na malha; me envie a linha 'Malha -> colunas'.")
if g.crs is None:
    g = g.set_crs(4326)
g["cod_ibge"] = g[col].astype(str).str[:7].astype(int)

pr = g.to_crs(5880).geometry.representative_point()
pr = gpd.GeoSeries(pr, crs=5880).to_crs(4326)
g["lat"], g["lon"] = pr.y, pr.x

m = mun.merge(g[["cod_ibge", "lat", "lon"]], on="cod_ibge", how="outer", indicator=True)
print("Junção JSON x malha:\n", m["_merge"].value_counts().to_string())
m = m[m["_merge"] == "both"].drop(columns="_merge")
m.to_parquet("data/silver/municipios_sp.parquet", index=False)

est = (pd.read_parquet("data/silver/inmet_estacoes_sp.parquet")
         .sort_values("ano").drop_duplicates("codigo_wmo", keep="last")
         .dropna(subset=["latitude", "longitude"]))
pts = gpd.GeoDataFrame(est, geometry=gpd.points_from_xy(est.longitude, est.latitude), crs=4326)
j = gpd.sjoin(pts, g[["cod_ibge", "geometry"]].to_crs(4326), how="left", predicate="within")
j = j.drop(columns=["geometry", "index_right"])
j.to_parquet("data/silver/estacao_municipio.parquet", index=False)
print("Estações:", len(j), "| sem município:", j["cod_ibge"].isna().sum(),
      "| municípios com estação:", j["cod_ibge"].nunique())

pontos = pd.concat([
    pd.DataFrame({"id": m["cod_ibge"].astype(str), "tipo": "municipio", "nome": m["municipio"], "lat": m["lat"], "lon": m["lon"]}),
    pd.DataFrame({"id": j["codigo_wmo"], "tipo": "estacao", "nome": j["estacao"], "lat": j["latitude"], "lon": j["longitude"]}),
], ignore_index=True)
pontos.to_parquet("data/silver/pontos_open_meteo.parquet", index=False)
print("Pontos para a Open-Meteo:", pontos["tipo"].value_counts().to_dict())
