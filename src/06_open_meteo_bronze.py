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
ap.add_argument("--teste", action="store_true")
args = ap.parse_args()

pontos = pd.read_parquet("data/silver/pontos_open_meteo.parquet")
if args.teste:
    pontos = pontos.groupby("tipo").head(2)

sess = requests.Session()
baixados = 0
for i, p in enumerate(pontos.itertuples(), 1):
    arq = DESTINO / f"{p.tipo}_{p.id}.json"
    if arq.exists():
        continue
    params = {**BASE, "latitude": round(p.lat, 4), "longitude": round(p.lon, 4)}
    for tentativa in range(1, 7):
        r = sess.get(URL, params=params, timeout=120)
        if r.status_code == 200:
            break
        if r.status_code == 429 or r.status_code >= 500:
            print(f"[{i}] HTTP {r.status_code}; aguardando 65 s (tentativa {tentativa})")
            time.sleep(65)
            continue
        raise SystemExit(f"Erro HTTP {r.status_code}: {r.text[:300]}")
    else:
        raise SystemExit("Limite atingido. Rode novamente mais tarde: o script retoma de onde parou.")
    corpo = {"_meta": {"url": r.url, "baixado_em_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                       "tipo": p.tipo, "id": str(p.id), "nome": p.nome,
                       "sha256": hashlib.sha256(r.content).hexdigest()},
             "resposta": r.json()}
    arq.write_text(json.dumps(corpo), encoding="utf-8")
    baixados += 1
    if args.teste:
        d = corpo["resposta"]
        s = pd.Series(d["daily"]["precipitation_sum"], dtype="float")
        print(f"{p.tipo} {p.id} {p.nome}: grade=({d['latitude']}, {d['longitude']}) "
              f"alt={d.get('elevation')} dias={len(s)} nulos={s.isna().sum()} total={s.sum():.0f} mm")
    time.sleep(1.0)
print("Concluído. Novos arquivos:", baixados, "| total na pasta:", len(list(DESTINO.glob('*.json'))))
