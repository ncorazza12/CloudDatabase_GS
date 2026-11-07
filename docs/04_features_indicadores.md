# Feature Engineering e Indicadores

Base: `gold_municipio_mes` (45.708 linhas = 293 municípios x 156 meses; 120 município-meses com evento, 0,26%). Fonte da chuva: ERA5 (Open-Meteo), diária por município.

## 1. Features

| Feature | Construção | Por que existe | Contribuição observada |
|---|---|---|---|
| acc3, acc7, acc30 | Soma móvel da chuva diária em 3, 7 e 30 dias (nulo até a janela completar) | Desastres hidrológicos respondem à chuva concentrada e à antecedente, não só ao dia | Mediana de acc7 no dia do evento: 59,3 mm contra 12,8 mm em todos os dias; acc30_max é a 2ª variável mais importante no Random Forest (0,117) |
| dias_chuva, dias_ge20mm, dias_ge50mm | Contagem de dias com chuva >= 1, 20 e 50 mm | Captura frequência de dias intensos, não só o total | Taxa de evento sobe com a chuva máxima diária (ver indicadores) |
| chuva_mes_mm, chuva_max_dia_mm | Soma e máximo diário no mês | Volume e pico | chuva_max_dia_mm tem coeficiente 1,282 na logística |
| acc3_max, acc7_max, acc30_max | Máximo mensal dos acumulados | Resume a pior janela do mês | acc7_max e acc30_max entre as mais importantes no RF |
| chuva_mes_lag1 | Chuva do mês anterior | Umidade antecedente | 5ª em importância no RF (0,099) |
| anomalia_mensal | Chuva do mês / média do mesmo mês-calendário do município | Remove o efeito do clima local | Usada no modelo |
| p95_dia_chuvoso, razao_max_p95 | Percentil 95 dos dias com >= 1 mm do município; razão do máximo diário sobre ele | Mede o quão extremo é o dia para aquele local | Coeficiente -1,247 na logística |
| estacao_chuvosa, mes_sin, mes_cos | Meses 10-3 = 1; codificação cíclica do mês | Sazonalidade | Dez-mar concentram 119 dos 135 eventos (88%); removê-las não piorou o modelo (ver robustez) |
| log_pop, log_dens | log10 de população (Censo 2022) e densidade | Exposição | log_pop no RF: 0,084 |
| Rótulo `ocorrencia` | n_eventos > 0 no mês da Data_Evento | Alvo do modelo | 0,26% de positivos |

Decisões: Data_Evento (não Data_Registro) para casar chuva e evento; granularidade município-mês porque em município-dia seriam ~3,06 milhões de linhas com ~0,011% de positivos.

## 2. Indicadores

| Indicador | Definição e dados | Obtenção | Interpretação | Decisão apoiada |
|---|---|---|---|---|
| Eventos por município | Contagem de registros do Atlas (2013-2025) | Soma de n_eventos | Mais registros = mais histórico documentado | Onde há demanda comprovada. Líderes: Ferraz de Vasconcelos 10, Ibiúna 8, Francisco Morato 6 |
| Eventos por 100 mil hab. | eventos / população 2022 x 100.000 | gold_municipio | Normaliza pelo tamanho (pop. >= 20 mil): Ibiúna 10,6, Capivari 10,0 | Comparar cidades de portes distintos |
| Dias >= 50 mm por ano | Dias-município com ERA5 >= 50 mm / anos | gold_municipio_cluster | Perigo de chuva forte: Cananéia 3,2, Guarujá 3,2 | Mapeamento de perigo |
| Desabrigados + desalojados | DH_DESABRIGADOS + DH_DESALOJADOS | Soma por município (total do escopo: 21.338) | Gravidade humana | Priorizar apoio |
| Índice de prioridade (0-100) | Média dos percentis de frequência, perigo, exposição e gravidade, pesos iguais | 12_indicadores_cluster.py | Top: Caraguatatuba 95,6, Cubatão 95,5, Bertioga 91,3 | Ordem de atenção. **Pesos iguais não foram testados quanto à sensibilidade** |
| Eventos por 100 dias >= 50 mm, por mês | eventos / dias >= 50 mm x 100 | docs/eventos_por_dias_ge50_mes.csv | Mar 17,3; fev 11,0; jan 6,1; nov 0,3 | Calendário de alerta. Hipótese de solo saturado **não testada**; meses com 0-1 evento são ruidosos |
| Taxa de ocorrência por faixa de chuva máxima | % de município-meses com evento | Gold | <20 mm: 0,053%; 20-50: 0,394%; 50-100: 1,123%; >=100: 1,695% (só 2 eventos) | Limiares de alerta. Faixa >= 100 mm é frágil |
| Cluster | K-Means (k=3, silhouette 0,399) em chuva anual, dias >= 50 mm, log pop e log densidade | 12_indicadores_cluster.py | C0: 16 mun., 1.871 mm/ano, 1,06 evento/mun.; C1: 181 mun., 0,23; C2: 96 mun., urbano, 14.807 desabrigados | Estratégias por perfil. Estrutura moderada (k=2 tem silhouette maior, 0,432) |

## 3. Análises avançadas e limites

- **Validação ERA5 x INMET (23 estações):** r diário mediano 0,52; mensal 0,82; viés -0,59 mm/dia.
- **Modelo (teste 2023-2025, 21 positivos):** logística PR-AUC 0,032 (acaso ~0,002), ROC-AUC 0,884, recall top 10% = 0,667. Regra simples (chuva máxima diária): ROC-AUC 0,853.
- **Robustez:** sem 2013 no treino, ROC-AUC 0,902; sem sazonalidade, 0,920. Os ICs de 95% se sobrepõem aos da regra simples (ROC-AUC 0,814-0,940 contra 0,792-0,903), então **não se pode afirmar que o modelo supera a regra**. O bootstrap trata linhas como independentes, logo os intervalos reais tendem a ser mais largos.
- É modelo diagnóstico (usa a chuva do mesmo mês): serve para triagem, não para previsão antecipada.
