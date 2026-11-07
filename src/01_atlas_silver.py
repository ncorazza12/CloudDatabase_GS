import os
import pandas as pd

file_path = r"data\bronze\atlas_desastres\BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.xlsx"

print("Lendo a planilha do Atlas de Desastres...")
df = pd.read_excel(file_path, sheet_name="Atlas Valores Originais")
print(f"Total de registros na base nacional: {len(df)}")

# 1. Filtra estritamente para o estado de São Paulo (Sigla_UF)
df_sp = df[df["Sigla_UF"].astype(str).str.upper() == "SP"].copy()
print(f"Registros encontrados para SP (total histórico): {len(df_sp)}")

# 2. Termos estritos conforme o COBRADE:
# Hidrológicos: Inundações, Enxurradas, Alagamentos
# Geológicos (Deslizamentos): Movimento de Massa
termos_estritos = [
    "Inundação",
    "Inundações",
    "Enxurrada",
    "Enxurradas",
    "Alagamento",
    "Alagamentos",
    "Movimento de Massa",
    "Deslizamento",
    "Deslizamentos",
]

padrao_regex = "|".join(termos_estritos)
df_tipos = df_sp[
    df_sp["descricao_tipologia"].astype(str).str.contains(padrao_regex, case=False, na=False)
].copy()

# 3. Corte temporal: 2013 a 2025 (Instrução Normativa nº 1/2012)
df_tipos["Data_Evento"] = pd.to_datetime(df_tipos["Data_Evento"], errors="coerce")

df_filtrado = df_tipos[
    (df_tipos["Data_Evento"].dt.year >= 2013) & 
    (df_tipos["Data_Evento"].dt.year <= 2025)
].copy()

print(f"Total de registros filtrados (Hidro + Geo, Período 2013-2025): {len(df_filtrado)}")

# Exibe o resumo detalhado das tipologias capturadas
if len(df_filtrado) > 0:
    print("\nResumo das descrições capturadas (2013-2025):")
    print(df_filtrado["descricao_tipologia"].value_counts(dropna=False))

# 4. Cria o diretório 'data/silver' se não existir
os.makedirs("data/silver", exist_ok=True)

# 5. Salva o resultado final tratado em formato Parquet
output_path = "data/silver/atlas_sp_hidro_geo.parquet"
df_filtrado.to_parquet(output_path, index=False)
print(f"\nArquivo final salvo com sucesso em: {output_path}")