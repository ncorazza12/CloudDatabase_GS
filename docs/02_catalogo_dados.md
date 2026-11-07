# Catálogo de dados

Projeto: chuvas extremas e desastres no estado de SP (2013-2025). Baixado/processado em 07/11/2026.

| Fonte | O que traz | Acesso | Formato | Período | Camada |
|---|---|---|---|---|---|
| Atlas Digital de Desastres (MDR/S2iD) | Registros de desastres e danos | https://atlasdigital.mdr.gov.br/arquivos/2026/BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv (usado o .xlsx equivalente) | XLSX | 1991-2025 (recorte 2013-2025) | Bronze: data/bronze/atlas_desastres |
| INMET, dados históricos | Precipitação horária das estações automáticas | https://portal.inmet.gov.br/uploads/dadoshistoricos/{ano}.zip | ZIP com um CSV por estação | 2013-2025 | Bronze: data/bronze/inmet (13 ZIPs, ~1,32 GB) |
| IBGE, API de localidades | 645 municípios de SP | https://servicodados.ibge.gov.br/api/v1/localidades/estados/35/municipios | JSON | atual | Bronze: data/bronze/ibge |
| IBGE, API de malhas | Polígonos municipais (645 feições, EPSG:4326) | https://servicodados.ibge.gov.br/api/v3/malhas/estados/35 (qualidade=intermediaria) | GeoJSON | atual | Bronze: data/bronze/ibge |
| IBGE, API de agregados (tabela 9514) | População, Censo 2022 | servicodados.ibge.gov.br/api/v3/agregados (variável 93) | JSON | 2022 | Bronze: data/bronze/ibge |
| Open-Meteo, Historical Weather (ERA5) | Precipitação diária reanalisada no ponto do município | https://archive-api.open-meteo.com/v1/archive (models=era5, daily=precipitation_sum) | JSON | 2013-2025 | Bronze: data/bronze/open_meteo (295 arquivos) |

## Confiabilidade e limites de cada fonte
- **Atlas:** oficial, mas depende de notificação municipal. "Sem registro" não significa "sem desastre". Recorte: Inundações, Alagamentos, Enxurradas e Movimento de Massa = 339 registros em SP (2013-2025). 0 protocolos duplicados, 0 Data_Evento nulas, Cod_IBGE_Mun de 7 dígitos (casa com o IBGE).
- **INMET:** medição direta, mas só 41 de 645 municípios (6,4%) têm estação. Usado para validar o ERA5.
- **ERA5 (Open-Meteo):** cobre todos os municípios, mas é reanálise em grade. Contra o INMET (23 estações): r diário mediano 0,52, r mensal mediano 0,82, viés mediano -0,59 mm/dia. Detecta 25,4% dos dias >= 20 mm medidos; 54,7% dos dias ERA5 >= 20 mm não se confirmam. Os 293 municípios usam 214 células distintas (65 compartilhadas, até 5 municípios por célula).
- **IBGE:** fonte oficial. A área somada da malha (249.197 km²) difere ~0,4% do valor oficial lembrado de memória (não confirmado).

## Regras de qualidade aplicadas
- INMET: leitura latin-1, separador `;`, decimal `,`, 8 linhas de metadados; valores negativos (-9999) viram nulo; hora UTC convertida para America/Sao_Paulo; `dia_confiavel` = pelo menos 20 horas válidas (79,5% dos dias de 177.602).
- Estação C891 (CRIOSFERA) excluída: UF=SP no INMET, mas coordenadas na Antártida.
- Cruzamento com a chuva pela Data_Evento (mediana de 0 dia até o registro).
- Ponto do município = `representative_point` (sempre dentro do polígono), calculado em EPSG:5880.
- ERA5 fixado em models=era5 para manter o mesmo modelo em todos os anos.

## Rastreabilidade
`docs/manifesto_bronze.csv` guarda o SHA256 de cada arquivo da Bronze. Cada download tem um `.meta.json` (url, baixado_em_utc, bytes, sha256). Os JSONs da Open-Meteo embutem `_meta`.

## Limitação de escopo
A cota diária da Open-Meteo esgotou: foram baixados 293 dos 645 municípios (Adamantina a Jumirim, ordem do código IBGE), mais 2 estações (A729 e C891; a C891 foi baixada antes de ser excluída e não entra nas análises). A amostra **não é aleatória** e cobre 135 dos 339 registros do Atlas (39,8%). Faltam 352 municípios e 41 estações. O pipeline é idempotente: baixar o restante e reexecutar os scripts 07, 08, 10, 12 e 13.

## Licenças
A Open-Meteo é gratuita para uso não comercial; a atribuição CC BY 4.0 vem de fontes secundárias (não confirmada no site oficial). Licenças do Atlas, INMET e IBGE: não verificadas neste projeto.

