# Arquitetura da solução

Pipeline Medallion (Bronze, Silver, Gold) para chuvas extremas e desastres no estado de SP, 2013-2025. Escopo processado: 293 dos 645 municípios (ver limitações).

## Diagrama

```mermaid
flowchart LR
  subgraph FONTES
    A1[Atlas Digital de Desastres<br/>XLSX]
    A2[INMET<br/>13 ZIPs, ~1,32 GB]
    A3[IBGE<br/>municípios, malha, Censo 2022]
    A4[Open-Meteo ERA5<br/>295 JSONs]
  end
  subgraph BRONZE[BRONZE: dado original + SHA256 + meta.json]
    B1[atlas_desastres]
    B2[inmet]
    B3[ibge]
    B4[open_meteo]
  end
  subgraph SILVER[SILVER: limpeza, padronização, integração]
    S1[atlas_sp_hidro_geo<br/>339 x 70]
    S2[inmet_chuva_diaria_sp<br/>177.602 linhas]
    S3[municipios_sp, municipios_demografia]
    S4[era5_chuva_diaria<br/>1.400.660 linhas]
  end
  subgraph GOLD[GOLD: features e indicadores]
    G1[gold_municipio_mes<br/>45.708 x 32]
    G2[gold_municipio]
    G3[gold_eventos<br/>135]
    G4[gold_municipio_cluster]
  end
  A1-->B1-->S1
  A2-->B2-->S2
  A3-->B3-->S3
  A4-->B4-->S4
  S1 & S3 & S4-->G1
  G1-->G2-->G4
  S1 & S4-->G3
  S2 -. validação .-> S4
  G1 & G3 & G4-->D[Dashboard Streamlit]
  G1-->M[Modelo: logística e Random Forest]
  S4 & S1 & S3-->SP[Spark/Databricks: Gold em Delta]
```

## Camadas

| Camada | Conteúdo | Regras principais |
|---|---|---|
| Bronze | Arquivos como baixados | Sem alteração; SHA256 em `docs/manifesto_bronze.csv`; `.meta.json` com URL, data UTC, bytes |
| Silver | Parquet limpo e padronizado | Filtro de tipologias do Atlas; INMET com -9999 nulo, UTC para America/Sao_Paulo, `dia_confiavel` (>= 20 h); C891 excluída; chaves por código IBGE |
| Gold | Painel município-mês e indicadores | Features de chuva, eventos do Atlas pelo mês de Data_Evento, população, clusters, índice de prioridade |

## Fluxo e ordem de execução

Scripts em `src/`, executados da raiz do repositório: 01 a 05 (Atlas, INMET, IBGE, pontos), 06 (download Open-Meteo, idempotente), 07 (ERA5 Silver), 08 (escopo), 09 (demografia), 10 (Gold), 11 (validação ERA5 x INMET), 12 (indicadores e clusters), 13 (modelo), 14 (robustez), `dashboard.py`.

## Qualidade, rastreabilidade, atualização, confiabilidade

- **Qualidade:** validações descritas no catálogo (duplicados 0, datas nulas 0, chaves IBGE conferidas, 645 municípios e 645 feições).
- **Rastreabilidade:** hash SHA256 de cada arquivo da Bronze e metadados de download.
- **Atualização:** scripts idempotentes. Para ampliar o escopo, baixar os municípios faltantes e reexecutar 07, 08, 10, 12 e 13.
- **Confiabilidade:** ERA5 validado contra 23 estações do INMET (r diário mediano 0,52; r mensal 0,82).
- **Reprodutibilidade entre motores:** o Gold foi recalculado em Spark e bateu com o pandas: 45.708 linhas, 120 positivos, 135 eventos.

## Decisões técnicas

- Chuva por município via ERA5, pois só 41 de 645 municípios (6,4%) têm estação INMET.
- Modelagem em município-mês: em município-dia seriam cerca de 3,06 milhões de linhas com ~0,011% de positivos.
- Parquet em vez de CSV (tipos preservados, compactação).
- Dados fora do GitHub (`.gitignore`); só código e documentação são versionados.

## Limitações

- Escopo de 293 municípios por limite de cota da API; amostra não aleatória.
- 214 células ERA5 distintas para 293 municípios.
- Camadas em disco local; apenas o Gold foi publicado em tabela Delta no Databricks (`workspace.default.gold_municipio_mes`).
