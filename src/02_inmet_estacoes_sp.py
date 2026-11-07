import csv, io, zipfile
from pathlib import Path
import pandas as pd

BRONZE = Path("data/bronze/inmet")
CAMPOS = ["regiao", "uf", "estacao", "codigo_wmo", "latitude", "longitude", "altitude", "data_fundacao"]
estacoes, cabecalhos = [], {}

for zp in sorted(BRONZE.glob("*.zip")):
    ano = int(zp.stem)
    with zipfile.ZipFile(zp) as z:
        for nome in z.namelist():
            if not nome.lower().endswith(".csv"):
                continue
            with z.open(nome) as raw:
                f = io.TextIOWrapper(raw, encoding="latin-1", newline="")
                linhas = [next(csv.reader([f.readline()], delimiter=";"), []) for _ in range(9)]
            meta = {c: (l[1].strip() if len(l) > 1 else None) for c, l in zip(CAMPOS, linhas[:8])}
            if (meta.get("uf") or "").upper() != "SP":
                continue
            meta.update(ano=ano, arquivo=nome)
            estacoes.append(meta)
            cabecalhos.setdefault(ano, linhas[8])

df = pd.DataFrame(estacoes)
for c in ["latitude", "longitude", "altitude"]:
    df[c] = pd.to_numeric(df[c].str.replace(",", ".", regex=False), errors="coerce")
df.to_parquet("data/silver/inmet_estacoes_sp.parquet", index=False)

print("Estações de SP por ano:")
print(df.groupby("ano")["codigo_wmo"].nunique())
for ano in (2013, 2019, 2025):
    print(f"\nColunas {ano}:", cabecalhos.get(ano))
