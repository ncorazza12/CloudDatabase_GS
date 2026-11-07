import json
from pathlib import Path
import pandas as pd

diarios, grade = [], []
for arq in sorted(Path("data/bronze/open_meteo").glob("*.json")):
    d = json.loads(arq.read_text(encoding="utf-8"))
    meta, resp = d["_meta"], d["resposta"]
    df = pd.DataFrame({"dia": pd.to_datetime(resp["daily"]["time"]),
                       "chuva_era5_mm": pd.to_numeric(resp["daily"]["precipitation_sum"], errors="coerce")})
    df["tipo"], df["id"] = meta["tipo"], meta["id"]
    diarios.append(df)
    grade.append({"tipo": meta["tipo"], "id": meta["id"], "grade_lat": resp.get("latitude"),
                  "grade_lon": resp.get("longitude"), "elevacao_m": resp.get("elevation")})

era5 = pd.concat(diarios, ignore_index=True)
era5.to_parquet("data/silver/era5_chuva_diaria.parquet", index=False)
pd.DataFrame(grade).to_parquet("data/silver/era5_grade.parquet", index=False)

print("Pontos:", era5.groupby("tipo")["id"].nunique().to_dict(), "| linhas:", len(era5))
print("Período:", era5["dia"].min().date(), "a", era5["dia"].max().date())
print("Nulos:", int(era5["chuva_era5_mm"].isna().sum()))
print("Maiores chuvas diárias ERA5 (mm):")
print(era5.nlargest(5, "chuva_era5_mm").to_string(index=False))
