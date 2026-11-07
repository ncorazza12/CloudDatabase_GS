import argparse, json, time, hashlib, datetime as dt
from pathlib import Path
import pandas as pd
import requests

URL = "https://archive-api.open-meteo.com/v1/archive"
BASE = {"start_date": "2013-01-01", "end_date": "2025-12-31", "daily": "precipitation_sum",
        "timezone": "America/Sao_Paulo", "models": "era5"}
DESTINO = Path("data/bronze/open_meteo")
DESTINO.mkdir(parents=True, exist_ok=True)

ap = argparse.ArgumentParser()
ap.add_argument("--max", type=int, default=0, help="máximo de downloads nesta execução (0 = sem limite)")
args = ap.parse_args()

dias = (pd.Timestamp(BASE["end_date"]) - pd.Timestamp(BASE["start_date"])).days + 1
print(f"Peso estimado por requisição: ~{0.1 * dias / 14:.0f} (cota diária de 10.000 -> ~{int(10000 / (0.1 * dias / 14))} requisições/dia)")

pontos = pd.read_parquet("data/silver/pontos_open_meteo.parquet")
pontos["ordem"] = pontos["tipo"].map({"estacao": 0, "municipio": 1})
pontos = pontos.sort_values(["ordem", "id"]).reset_index(drop=True)
pendentes = [p for p in pontos.itertuples() if not (DESTINO / f"{p.tipo}_{p.id}.json").exists()]
print(f"Pontos: {len(pontos)} | já baixados: {len(pontos) - len(pendentes)} | pendentes: {len(pendentes)}")

sess = requests.Session()
baixados = 0
for p in pendentes:
    if args.max and baixados >= args.max:
        break
    params = {**BASE, "latitude": round(p.lat, 4), "longitude": round(p.lon, 4)}
    tentativa = 0
    while True:
        r = sess.get(URL, params=params, timeout=120)
        if r.status_code == 200:
            break
        motivo = r.text[:200]
        if r.status_code == 429:
            m = motivo.lower()
            if "daily" in m:
                print(f"Limite DIÁRIO atingido após {baixados} downloads: {motivo}")
                print("Rode novamente depois que a cota renovar; o script retoma de onde parou.")
                raise SystemExit(0)
            tentativa += 1
            if tentativa > 6:
                raise SystemExit(f"Limite persistente: {motivo}")
            espera = 900 if "hourly" in m else 65
            print(f"429: {motivo} | aguardando {espera} s")
            time.sleep(espera)
            continue
        if r.status_code >= 500 and tentativa < 5:
            tentativa += 1
            time.sleep(10 * tentativa)
            continue
        raise SystemExit(f"Erro HTTP {r.status_code}: {motivo}")
    corpo = {"_meta": {"url": r.url, "baixado_em_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                       "tipo": p.tipo, "id": str(p.id), "nome": p.nome,
                       "sha256": hashlib.sha256(r.content).hexdigest()},
             "resposta": r.json()}
    (DESTINO / f"{p.tipo}_{p.id}.json").write_text(json.dumps(corpo), encoding="utf-8")
    baixados += 1
    if baixados % 25 == 0:
        print(f"{baixados} downloads nesta execução")
    time.sleep(1.0)
print("Concluído. Novos arquivos:", baixados, "| total na pasta:", len(list(DESTINO.glob("*.json"))))
