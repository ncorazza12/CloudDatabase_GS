import json, hashlib, datetime as dt
from pathlib import Path
import geopandas as gpd
import pandas as pd
import requests

BASE = "https://servicodados.ibge.gov.br/api/v3/agregados/9514"
DEST = Path("data/bronze/ibge")

meta = requests.get(f"{BASE}/metadados", timeout=60)
meta.raise_for_status()
meta = meta.json()
variavel = next(v["id"] for v in meta["variaveis"] if "residente" in v["nome"].lower())
cls = []
for c in meta["classificacoes"]:
    tot = [k for k in c["categorias"] if k["nome"].strip().lower() == "total"]
    if tot:
        cls.append(f'{c["id"]}[{tot[0]["id"]}]')
print("Variável:", variavel, "| classificações:", cls)

r = requests.get(f"{BASE}/periodos/2022/variaveis/{variavel}", timeout=180,
                 params={"localidades": "N6[N3[35]]", "classificacao": "|".join(cls)})
r.raise_for_status()
(DEST / "populacao_censo2022_sp.json").write_bytes(r.content)
(DEST / "populacao_censo2022_sp.json.meta.json").write_text(json.dumps({
    "url": r.url, "baixado_em_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest()}, indent=2), encoding="utf-8")

linhas = []
for res in r.json()[0]["resultados"]:
    for s in res["series"]:
        linhas.append({"cod_ibge": int(s["localidade"]["id"]),
                       "populacao_2022": pd.to_numeric(s["serie"].get("2022"), errors="coerce")})
pop = pd.DataFrame(linhas).drop_duplicates("cod_ibge")

g = gpd.read_file(DEST / "malha_municipios_sp.geojson")
g["cod_ibge"] = g["codarea"].astype(str).str[:7].astype(int)
g["area_km2"] = g.to_crs(5880).geometry.area / 1e6
dem = pop.merge(g[["cod_ibge", "area_km2"]], on="cod_ibge", how="outer")
dem["densidade_hab_km2"] = dem["populacao_2022"] / dem["area_km2"]
dem.to_parquet("data/silver/municipios_demografia.parquet", index=False)
print("Municípios:", len(dem), "| população total SP:", int(dem["populacao_2022"].sum()),
      "| área total (km²):", round(dem["area_km2"].sum()))
