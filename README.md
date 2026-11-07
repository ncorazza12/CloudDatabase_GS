# CitizenTech: chuvas extremas e desastres no estado de SP (2013-2025)

Trabalho individual de Cloud Database (Global Solution 2026.2). Pipeline Medallion (Bronze, Silver, Gold) com features, indicadores, clusters, modelo, dashboard Streamlit e experimento em Spark/Databricks.

**Aluno:** Nickolas Corazza Alves, RM 562265.
**Escopo processado:** 293 dos 645 municípios (limite de cota da API Open-Meteo). Veja as limitações em `docs/04_features_indicadores.md` e no relatório.

## Documentação
- `docs/01_investigacao_problema.md`: problema
- `docs/02_catalogo_dados.md`: fontes e qualidade
- `docs/03_arquitetura.md`: diagrama Medallion e fluxo
- `docs/04_features_indicadores.md`: features, indicadores e análises
- `docs/05_experimentacao_spark.md`: registro da experimentação em Spark/Databricks
- `docs/Relatorio_Executivo_CitizenTech.docx`: diagnóstico e recomendações
- `Evidencias/`: prints do dashboard (Streamlit) e do notebook Databricks

## Como reproduzir
Windows, PowerShell, Python com `.venv`, Java 17 (para pyspark). Os dados não estão no GitHub; as pastas `data/bronze|silver|gold` são geradas localmente.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Executar da raiz, nesta ordem:
1. `src\01_atlas_silver.py` (lê o XLSX do Atlas, baixado manualmente do Atlas Digital de Desastres e colocado em `data\bronze\atlas_desastres\`; URL no catálogo)
2. `src\02_inmet_estacoes_sp.py`, `src\03_inmet_chuva_diaria.py` (ZIPs do INMET em `data\bronze\inmet\`)
3. `src\04_ibge_bronze.py`, `src\05_municipios_pontos.py`
4. `src\06_open_meteo_bronze.py` (idempotente; respeita a cota diária da API)
5. `src\07_era5_silver.py`, `src\08_escopo_e_saneamento.py`, `src\09_ibge_demografia.py`
6. `src\10_gold.py`, `src\11_validacao_era5.py`, `src\12_indicadores_cluster.py`, `src\13_modelo.py`, `src\14_robustez.py`
7. `streamlit run src\dashboard.py`

Scripts auxiliares: `inspecionar_atlas.py`, `03b_perfil_atlas.py`, `03c_atlas_2013.py`.

## Fontes e datas de download
Atlas Digital de Desastres (BD_Atlas_1991_2025_v1.1), INMET dados históricos (baixados em 07/11/2026), IBGE (APIs de localidades, malhas e agregados) e Open-Meteo Historical Weather (ERA5). URLs completas em `docs/02_catalogo_dados.md`. Hashes SHA256 em `docs/manifesto_bronze.csv`.

## Spark
Notebook executado no Databricks Free Edition (serverless): recalculou o Gold (45.708 linhas, 120 positivos, 135 eventos, igual ao pandas) e salvou a tabela Delta `workspace.default.gold_municipio_mes`.



## Evidências

### Dashboard (Streamlit)

**Mapa**

![Dashboard - Mapa](Evidencias/Streamlit%20-%20Dashboard%20Mapa.jpeg)

**Prioridades**

![Dashboard - Prioridades](Evidencias/Streamlit%20-%20Dashboard%20Prioridades.jpeg)

**Tempo**

![Dashboard - Tempo](Evidencias/Streamlit%20-%20Dashboard%20Tempo.jpeg)

**Chuva x eventos**

![Dashboard - Chuva x eventos](Evidencias/Streamlit%20-%20Dashboard%20Chuva%20x%20eventos.jpeg)

**Qualidade e limites**

![Dashboard - Qualidade e limites](Evidencias/Streamlit%20-%20Dashboard%20Qualidade%20e%20limites.jpeg)

### Experimentação Spark (Databricks)

![Databricks - Notebook](Evidencias/DataBricks%20-%20Notebook%204.jpeg)
