import pandas as pd

mun = pd.read_parquet("data/silver/municipios_sp.parquet")
grade = pd.read_parquet("data/silver/era5_grade.parquet")
com = set(grade.loc[grade["tipo"] == "municipio", "id"].astype(int))
mun["tem_era5"] = mun["cod_ibge"].isin(com)
mun.to_parquet("data/silver/municipios_escopo.parquet", index=False)
no = mun[mun["tem_era5"]].sort_values("cod_ibge")
print(f"Municípios no escopo (com ERA5): {len(no)} de {len(mun)}")
print("Primeiro / último do escopo:", no.iloc[0]["municipio"], "/", no.iloc[-1]["municipio"])

at = pd.read_parquet("data/silver/atlas_sp_hidro_geo.parquet")
at["no_escopo"] = at["Cod_IBGE_Mun"].isin(com)
print(f"Registros do Atlas no escopo: {int(at['no_escopo'].sum())} de {len(at)} ({100*at['no_escopo'].mean():.1f}%)")
rec = at[at["Status"] == "Reconhecido"]
print(f"Reconhecidos no escopo: {int(rec['no_escopo'].sum())} de {len(rec)}")
print(f"Municípios com registro no escopo: {at.loc[at['no_escopo'], 'Cod_IBGE_Mun'].nunique()} de {at['Cod_IBGE_Mun'].nunique()}")
print("Maiores ausências do Atlas (sem ERA5):")
print(at.loc[~at["no_escopo"], "Nome_Municipio"].value_counts().head(8).to_string())

est = pd.read_parquet("data/silver/estacao_municipio.parquet")
ok = est["cod_ibge"].notna()
print("Estações removidas por estarem fora de SP:", est.loc[~ok, ["codigo_wmo", "estacao"]].values.tolist())
est = est[ok].copy()
est["cod_ibge"] = est["cod_ibge"].astype(int)
est.to_parquet("data/silver/estacao_municipio_valida.parquet", index=False)
print("Estações válidas:", len(est), "| em municípios com ERA5:", int(est["cod_ibge"].isin(com).sum()))

era = pd.read_parquet("data/silver/era5_chuva_diaria.parquet")
top = era[era["tipo"] == "municipio"].nlargest(5, "chuva_era5_mm").copy()
top["cod_ibge"] = top["id"].astype(int)
print("Maiores chuvas ERA5:")
print(top.merge(mun[["cod_ibge", "municipio"]], on="cod_ibge")[["dia", "chuva_era5_mm", "municipio"]].to_string(index=False))
