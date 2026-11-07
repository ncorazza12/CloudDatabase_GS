import pandas as pd
df = pd.read_parquet("data/silver/atlas_sp_hidro_geo.parquet")
df["ev"] = pd.to_datetime(df["Data_Evento"])
d13 = df[df["ev"].dt.year == 2013]
print("2013 por mês:\n", d13["ev"].dt.month.value_counts().sort_index().to_string())
print("\n2013 por tipologia:\n", d13["descricao_tipologia"].value_counts().to_string())
print("\nMunicípios com mais registros (2013-2025):\n",
      df["Nome_Municipio"].value_counts().head(8).to_string())
