import json, hashlib, datetime as dt
from pathlib import Path
import requests

DESTINO = Path("data/bronze/ibge")
DESTINO.mkdir(parents=True, exist_ok=True)

FONTES = {
    "municipios_sp.json": ("https://servicodados.ibge.gov.br/api/v1/localidades/estados/35/municipios", {}),
    "malha_municipios_sp.geojson": ("https://servicodados.ibge.gov.br/api/v3/malhas/estados/35",
        {"formato": "application/vnd.geo+json", "qualidade": "intermediaria", "intrarregiao": "municipio"}),
}

for nome, (url, params) in FONTES.items():
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    (DESTINO / nome).write_bytes(r.content)
    meta = {"url": r.url, "baixado_em_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "http_status": r.status_code, "bytes": len(r.content),
            "sha256": hashlib.sha256(r.content).hexdigest()}
    (DESTINO / (nome + ".meta.json")).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(nome, "->", len(r.content), "bytes")
