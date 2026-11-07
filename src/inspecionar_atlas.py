import pandas as pd
df = pd.read_parquet("data/silver/atlas_sp_hidro_geo.parquet")
print(df.shape)
print(df.columns.tolist())
print(df.dtypes)
print(df.isna().sum())
print(df.head(3).T)
