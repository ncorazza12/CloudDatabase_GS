import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

gr = pd.read_parquet("data/silver/era5_grade.parquet")
gr = gr[gr["tipo"] == "municipio"]
cel = gr.groupby(["grade_lat", "grade_lon"]).size()
print(f"Municípios: {len(gr)} | células ERA5 distintas: {len(cel)} | células compartilhadas: {(cel > 1).sum()} | máx. municípios por célula: {cel.max()}")

p = pd.read_parquet("data/gold/gold_municipio_mes.parquet")
m = p.groupby("mes").agg(eventos=("n_eventos", "sum"), dias_ge50=("dias_ge50mm", "sum"))
m["eventos_por_100_dias_ge50"] = (100 * m["eventos"] / m["dias_ge50"]).round(1)
print("\nEventos por 100 dias >= 50 mm, por mês:\n", m.to_string())
m.to_csv("docs/eventos_por_dias_ge50_mes.csv", encoding="utf-8-sig")

p["mes_sin"] = np.sin(2 * np.pi * p["mes"] / 12)
p["mes_cos"] = np.cos(2 * np.pi * p["mes"] / 12)
p["log_pop"] = np.log10(p["populacao_2022"])
p["log_dens"] = np.log10(p["densidade_hab_km2"])
FEATS = ["chuva_mes_mm", "chuva_max_dia_mm", "dias_chuva", "dias_ge20mm", "dias_ge50mm", "acc3_max", "acc7_max", "acc30_max",
         "chuva_mes_lag1", "anomalia_mensal", "razao_max_p95", "estacao_chuvosa", "mes_sin", "mes_cos", "log_pop", "log_dens"]
SEM_SAZON = [f for f in FEATS if f not in ("mes_sin", "mes_cos", "estacao_chuvosa")]

def avaliar(y, s):
    ordem = np.argsort(-s, kind="stable")
    out = {"PR_AUC": average_precision_score(y, s), "ROC_AUC": roc_auc_score(y, s)}
    for q in (0.05, 0.10):
        out[f"recall_top{int(q * 100)}pct"] = y[ordem[: int(len(y) * q)]].sum() / y.sum()
    return out

def modelo(nome):
    if nome == "Logística":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             LogisticRegression(class_weight="balanced", max_iter=2000))
    return make_pipeline(SimpleImputer(strategy="median"),
                         RandomForestClassifier(n_estimators=300, min_samples_leaf=20,
                                                class_weight="balanced_subsample", n_jobs=-1, random_state=42))

teste = p[p["ym"] >= "2023-01-01"]
yte = teste["ocorrencia"].values
base = p["ym"] < "2023-01-01"
variantes = {"completo": (base, FEATS), "treino sem 2013": (base & (p["ano"] != 2013), FEATS), "sem sazonalidade": (base, SEM_SAZON)}
linhas = []
for var, (mask, feats) in variantes.items():
    tr = p[mask]
    for nome in ("Logística", "Random Forest"):
        mod = modelo(nome).fit(tr[feats], tr["ocorrencia"])
        r = avaliar(yte, mod.predict_proba(teste[feats])[:, 1])
        r.update(variante=var, modelo=nome, positivos_treino=int(tr["ocorrencia"].sum()))
        linhas.append(r)
tab = pd.DataFrame(linhas).set_index(["variante", "modelo"]).round(3)
print("\nRobustez do modelo (teste 2023-2025):\n", tab.to_string())
tab.to_csv("docs/robustez_modelos.csv", encoding="utf-8-sig")

rng = np.random.default_rng(42)
def ic(y, s, B=300):
    res = []
    for _ in range(B):
        i = rng.integers(0, len(y), len(y))
        if y[i].sum() > 0:
            res.append(avaliar(y[i], s[i]))
    return pd.DataFrame(res).quantile([0.025, 0.975]).round(3)

tr = p[base]
lg = modelo("Logística").fit(tr[FEATS], tr["ocorrencia"])
print("\nIC 95% (bootstrap) - Logística:\n", ic(yte, lg.predict_proba(teste[FEATS])[:, 1]).to_string())
print("\nIC 95% (bootstrap) - Regra chuva máx. diária:\n", ic(yte, teste["chuva_max_dia_mm"].values).to_string())
