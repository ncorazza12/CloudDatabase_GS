import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

G = "data/gold/"
p = pd.read_parquet(G + "gold_municipio_mes.parquet")
gm = pd.read_parquet(G + "gold_municipio.parquet")

# ---- Evolução anual e sazonalidade
ano = p.groupby("ano").agg(eventos=("n_eventos", "sum"), meses_com_evento=("ocorrencia", "sum"),
                           dias_ge50mm=("dias_ge50mm", "sum"), chuva_mes=("chuva_mes_mm", "mean"))
ano["chuva_anual_media_mm"] = ano.pop("chuva_mes") * 12
ano["chuva_jfm_media_mm"] = p[p["mes"].isin([1, 2, 3])].groupby("ano")["chuva_mes_mm"].mean() * 3
ano = ano.round(1)
mes = p.groupby("mes").agg(eventos=("n_eventos", "sum"), dias_ge50mm=("dias_ge50mm", "sum"), chuva_media_mm=("chuva_mes_mm", "mean")).round(1)
print("Por ano:\n", ano.to_string(), "\n\nPor mês:\n", mes.to_string())
ano.to_csv("docs/tabela_ano.csv", encoding="utf-8-sig")
mes.to_csv("docs/tabela_mes.csv", encoding="utf-8-sig")

# ---- Clusterização (perigo + exposição, sem usar eventos)
gm["dias_ge50_ano"] = gm["dias_ge50mm"] / 13
gm["log_pop"] = np.log10(gm["populacao_2022"])
gm["log_dens"] = np.log10(gm["densidade_hab_km2"])
X = StandardScaler().fit_transform(gm[["chuva_media_anual_mm", "dias_ge50_ano", "log_pop", "log_dens"]])
melhor = None
print("\nSilhouette por k:")
for k in range(2, 7):
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    s = silhouette_score(X, km.labels_)
    print(" k=%d: %.3f" % (k, s))
    if k >= 3 and (melhor is None or s > melhor[0]):
        melhor = (s, k, km.labels_)
gm["cluster"] = melhor[2]
print("k escolhido (>=3):", melhor[1])
perfil = gm.groupby("cluster").agg(municipios=("cod_ibge", "count"), chuva_anual_mm=("chuva_media_anual_mm", "mean"),
    dias_ge50_ano=("dias_ge50_ano", "mean"), pop_mediana=("populacao_2022", "median"), dens_mediana=("densidade_hab_km2", "median"),
    eventos=("n_eventos", "sum"), eventos_por_municipio=("n_eventos", "mean"), desabrigados=("desabrigados_desalojados", "sum")).round(2)
print(perfil.to_string())

# ---- Índice de prioridade (0-100)
r = lambda s: s.rank(method="min", pct=True)
gm["pct_frequencia"] = r(gm["meses_com_evento"])
gm["pct_perigo"] = r(gm["dias_ge50_ano"])
gm["pct_exposicao"] = r(gm["populacao_2022"])
gm["pct_gravidade"] = r(gm["desabrigados_desalojados"])
gm["indice_prioridade"] = 100 * gm[["pct_frequencia", "pct_perigo", "pct_exposicao", "pct_gravidade"]].mean(axis=1)
cols = ["municipio", "indice_prioridade", "n_eventos", "meses_com_evento", "dias_ge50_ano", "populacao_2022"]
print("\nTop 10 por índice de prioridade:\n", gm.nlargest(10, "indice_prioridade")[cols].round(1).to_string(index=False))
print("\nTop 10 por nº de eventos:\n", gm.nlargest(10, "n_eventos")[cols].round(1).to_string(index=False))
print("\nTop 10 por eventos/100 mil hab (pop >= 20 mil):\n",
      gm[gm["populacao_2022"] >= 20000].nlargest(10, "eventos_por_100mil_hab")[cols + ["eventos_por_100mil_hab"]].round(1).to_string(index=False))
sem = gm[(gm["pct_perigo"] >= 0.9) & (gm["n_eventos"] == 0)]
print("\nPerigo alto (top 10%% em dias >=50 mm) e nenhum registro no Atlas: %d municípios" % len(sem))
print(sem.nlargest(10, "dias_ge50_ano")[["municipio", "dias_ge50_ano", "populacao_2022"]].round(1).to_string(index=False))
gm.to_parquet(G + "gold_municipio_cluster.parquet", index=False)
