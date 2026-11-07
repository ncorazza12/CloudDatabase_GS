# Experimentação com Spark (Databricks Free Edition)

Ambiente: Databricks Free Edition (computação serverless, só Python e SQL, arquivos em Volumes do Unity Catalog), runtime Databricks 19.13 com Photon. Executado em 07/11/2026.

Preparação: Volume `workspace.default.citizentech` com 4 arquivos enviados pela interface: `era5_chuva_diaria.parquet`, `atlas_sp_hidro_geo.parquet`, `municipios_escopo.parquet`, `municipios_demografia.parquet`.

## Código

```python
# Célula 1: leitura
from pyspark.sql import functions as F, Window
import time
V = "/Volumes/workspace/default/citizentech"
era   = spark.read.parquet(f"{V}/era5_chuva_diaria.parquet")
atlas = spark.read.parquet(f"{V}/atlas_sp_hidro_geo.parquet")
mun   = spark.read.parquet(f"{V}/municipios_escopo.parquet").filter("tem_era5")
dem   = spark.read.parquet(f"{V}/municipios_demografia.parquet")
print(era.count(), atlas.count(), mun.count())
era.printSchema()
```

```python
# Célula 2: transformações e janelas
t0 = time.time()
era = (era.filter(F.col("tipo") == "municipio")
          .withColumn("cod_ibge", F.col("id").cast("int"))
          .withColumn("dia", F.to_date("dia")))
w7  = Window.partitionBy("cod_ibge").orderBy("dia").rowsBetween(-6, 0)
w30 = Window.partitionBy("cod_ibge").orderBy("dia").rowsBetween(-29, 0)
era = (era.withColumn("acc7",  F.when(F.count("*").over(w7)  == 7,  F.sum("chuva_era5_mm").over(w7)))
          .withColumn("acc30", F.when(F.count("*").over(w30) == 30, F.sum("chuva_era5_mm").over(w30)))
          .withColumn("ym", F.trunc("dia", "month")))
mm = era.groupBy("cod_ibge", "ym").agg(
    F.sum("chuva_era5_mm").alias("chuva_mes_mm"), F.max("chuva_era5_mm").alias("chuva_max_dia_mm"),
    F.sum((F.col("chuva_era5_mm") >= 50).cast("int")).alias("dias_ge50mm"),
    F.max("acc7").alias("acc7_max"), F.max("acc30").alias("acc30_max"))
```

```python
# Célula 3: junção com o Atlas e a demografia
ev = (atlas.withColumn("cod_ibge", F.col("Cod_IBGE_Mun").cast("int"))
           .withColumn("ym", F.trunc(F.to_date("Data_Evento"), "month"))
           .groupBy("cod_ibge", "ym")
           .agg(F.count("*").alias("n_eventos"),
                F.sum((F.col("Status") == "Reconhecido").cast("int")).alias("n_reconhecidos")))
painel = (mm.join(ev, ["cod_ibge", "ym"], "left").fillna(0, subset=["n_eventos", "n_reconhecidos"])
            .join(mun.select("cod_ibge", "municipio"), "cod_ibge", "left")
            .join(dem, "cod_ibge", "left")
            .withColumn("ocorrencia", (F.col("n_eventos") > 0).cast("int")))
n = painel.count()
print("Linhas:", n, "| positivos:", painel.agg(F.sum("ocorrencia")).first()[0],
      "| eventos:", painel.agg(F.sum("n_eventos")).first()[0], "| tempo (s):", round(time.time() - t0, 1))
```

```python
# Célula 4: tabela Delta e consulta SQL
painel.write.mode("overwrite").saveAsTable("workspace.default.gold_municipio_mes")
display(spark.sql("""
  SELECT month(ym) AS mes, SUM(n_eventos) AS eventos, SUM(dias_ge50mm) AS dias_ge50,
         ROUND(100 * SUM(n_eventos) / SUM(dias_ge50mm), 1) AS eventos_por_100_dias_ge50
  FROM workspace.default.gold_municipio_mes GROUP BY month(ym) ORDER BY mes"""))
display(spark.sql("DESCRIBE HISTORY workspace.default.gold_municipio_mes"))
```

## Resultados observados
- Leitura: 1.400.660 linhas de chuva ERA5, 339 registros do Atlas, 293 municípios no escopo. Esquema da chuva: `dia` (timestamp_ntz), `chuva_era5_mm` (double), `tipo`, `id` (string).
- Painel: **45.708 linhas, 120 positivos, 135 eventos**, igual ao Gold do pandas. Tempo das células 2 e 3: 4,4 s (o Spark é preguiçoso: esse tempo inclui as três ações de contagem).
- A consulta SQL mensal reproduziu a tabela de eventos por 100 dias >= 50 mm do script 14 (jan 6,1; fev 11,0; mar 17,3; nov 0,3).
- Tabela Delta `workspace.default.gold_municipio_mes`: 1 arquivo, 343.717 bytes, 45.708 linhas; histórico registra a operação CREATE OR REPLACE TABLE AS SELECT (versão 0, 07/11/2026 16:16 UTC).

## Discussão
**Características:** o mesmo feature engineering (janelas móveis, agregação mensal, junções com o Atlas e a demografia) foi expresso em DataFrames e em SQL, e o resultado bateu com o pandas, o que valida a lógica entre os dois motores. A tabela Delta dá armazenamento em nuvem consultável por SQL e com histórico de versões.

**Possibilidades:** com dados horários do INMET (4,26 milhões de linhas só de SP; os ZIPs do país somam cerca de 1,32 GB) ou com os 645 municípios completos, as janelas e agregações poderiam ser distribuídas.

**Limitações:** para 1,4 milhão de linhas o pandas faz o mesmo sem esforço, e não medi o mesmo cálculo no pandas, então não há comparação de velocidade. A Free Edition é só serverless (sem escolha de cluster), só Python e SQL, sem RDD e sem montagens DBFS (usa Volumes). O upload dos arquivos foi manual pela interface.
