import io, zipfile
from pathlib import Path
import pandas as pd

BRONZE = Path("data/bronze/inmet")
SAIDA = Path("data/silver/inmet_chuva_diaria_sp.parquet")
partes = []

for zp in sorted(BRONZE.glob("*.zip")):
    ano = int(zp.stem)
    invalidos = linhas = 0
    with zipfile.ZipFile(zp) as z:
        for nome in z.namelist():
            if not nome.lower().endswith(".csv"):
                continue
            with z.open(nome) as raw:
                f = io.TextIOWrapper(raw, encoding="latin-1", newline="")
                meta = [f.readline().strip().split(";") for _ in range(8)]
                uf = meta[1][1].strip().upper() if len(meta[1]) > 1 else ""
                if uf != "SP":
                    continue
                codigo = meta[3][1].strip()
                df = pd.read_csv(f, sep=";", dtype=str, usecols=[0, 1, 2],
                                 header=0, names=["data", "hora", "chuva_mm"])
            df["chuva_mm"] = pd.to_numeric(df["chuva_mm"].str.replace(",", ".", regex=False), errors="coerce")
            df.loc[df["chuva_mm"] < 0, "chuva_mm"] = float("nan")   # -9999 = sem medição
            data = df["data"].str.strip().str.replace("/", "-", regex=False)
            hh = df["hora"].str.extract(r"(\d{2})", expand=False)
            ts = pd.to_datetime(data + " " + hh + ":00", errors="coerce", utc=True)
            invalidos += ts.isna().sum(); linhas += len(df)
            df["dia"] = ts.dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None).dt.normalize()
            g = df.dropna(subset=["dia"]).groupby("dia")["chuva_mm"]
            d = pd.DataFrame({"chuva_mm": g.sum(min_count=1), "horas_validas": g.count()}).reset_index()
            d["codigo_wmo"] = codigo
            partes.append(d)
    print(f"{ano}: {linhas} linhas lidas, {invalidos} com data/hora inválida")

todos = pd.concat(partes, ignore_index=True)
final = (todos.groupby(["codigo_wmo", "dia"], as_index=False)
              .agg(chuva_mm=("chuva_mm", "sum"), horas_validas=("horas_validas", "sum")))
final.loc[final["horas_validas"] == 0, "chuva_mm"] = float("nan")
final["dia_confiavel"] = final["horas_validas"] >= 20
final.to_parquet(SAIDA, index=False)

print("\nLinhas:", len(final), "| Estações:", final["codigo_wmo"].nunique())
print("Período:", final["dia"].min().date(), "a", final["dia"].max().date())
print("Dias confiáveis (>=20 h válidas): %.1f%%" % (100 * final["dia_confiavel"].mean()))
print("Maiores chuvas diárias (mm):")
print(final.nlargest(5, "chuva_mm")[["codigo_wmo", "dia", "chuva_mm", "horas_validas"]])
