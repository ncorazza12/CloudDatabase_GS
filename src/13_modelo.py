import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

p = pd.read_parquet("data/gold/gold_municipio_mes.parquet")
p["mes_sin"] = np.sin(2 * np.pi * p["mes"] / 12)
p["mes_cos"] = np.cos(2 * np.pi * p["mes"] / 12)
p["log_pop"] = np.log10(p["populacao_2022"])
p["log_dens"] = np.log10(p["densidade_hab_km2"])
FEATS = ["chuva_mes_mm", "chuva_max_dia_mm", "dias_chuva", "dias_ge20mm", "dias_ge50mm", "acc3_max", "acc7_max", "acc30_max",
         "chuva_mes_lag1", "anomalia_mensal", "razao_max_p95", "estacao_chuvosa", "mes_sin", "mes_cos", "log_pop", "log_dens"]

tr, te = p[p["ym"] < "2023-01-01"], p[p["ym"] >= "2023-01-01"]
ytr, yte = tr["ocorrencia"].values, te["ocorrencia"].values
print("Treino: %d linhas, %d positivos (%.2f%%) | Teste: %d linhas, %d positivos (%.2f%%)" %
      (len(tr), ytr.sum(), 100 * ytr.mean(), len(te), yte.sum(), 100 * yte.mean()))

def avaliar(y, s):
    ordem = np.argsort(-s, kind="stable")
    out = {"PR_AUC": average_precision_score(y, s), "ROC_AUC": roc_auc_score(y, s)}
    for q in (0.05, 0.10):
        out[f"recall_top{int(q * 100)}pct"] = y[ordem[: int(len(y) * q)]].sum() / y.sum()
    return out

modelos = {
    "Regressão logística": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                         LogisticRegression(class_weight="balanced", max_iter=2000)),
    "Random Forest": make_pipeline(SimpleImputer(strategy="median"),
                                   RandomForestClassifier(n_estimators=300, min_samples_leaf=20, class_weight="balanced_subsample",
                                                          n_jobs=-1, random_state=42)),
}
res = {"Regra: chuva máx. diária": avaliar(yte, te["chuva_max_dia_mm"].values),
       "Aleatório (prevalência)": {"PR_AUC": yte.mean(), "ROC_AUC": 0.5, "recall_top5pct": 0.05, "recall_top10pct": 0.10}}
for nome, m in modelos.items():
    m.fit(tr[FEATS], ytr)
    res[nome] = avaliar(yte, m.predict_proba(te[FEATS])[:, 1])
tab = pd.DataFrame(res).T.round(3)
print("\nResultados no teste (2023-2025):\n", tab.to_string())
tab.to_csv("docs/resultados_modelos.csv", encoding="utf-8-sig")

rf = modelos["Random Forest"][-1]
print("\nImportância (Random Forest):")
print(pd.Series(rf.feature_importances_, index=FEATS).sort_values(ascending=False).head(8).round(3).to_string())
lr = modelos["Regressão logística"][-1]
print("\nMaiores coeficientes (logística, variáveis padronizadas):")
print(pd.Series(lr.coef_[0], index=FEATS).sort_values(key=abs, ascending=False).head(6).round(3).to_string())
