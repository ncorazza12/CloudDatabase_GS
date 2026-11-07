# Investigação do problema: CitizenTech

**Aluno:** Nickolas Corazza Alves | **RM:** 562265 | **Disciplina:** Cloud Database (trabalho individual)

## 1. Problema
Chuvas extremas e desastres hidrológicos e geológicos (inundações, alagamentos, enxurradas e movimentos de massa) no estado de São Paulo, 2013-2025. Pergunta central: **onde e quando a chuva forte se converte em desastre registrado, e quais municípios merecem atenção primeiro?**

## 2. Quem é afetado
Moradores de áreas urbanas e de encostas e as Defesas Civis municipais. No escopo analisado, os registros do Atlas somam 21.338 desabrigados e desalojados. O grupo de municípios urbanos de chuva média concentra 14.807 deles.

## 3. Dimensão
- Atlas Digital de Desastres: 339 registros em SP (2013-2025) nas quatro tipologias, em 185 dos 645 municípios.
- 2013 concentra 154 desses 339 registros.
- Dezembro a março somam 88% dos eventos do escopo (119 de 135).

## 4. Decisões que a análise apoia
1. Onde priorizar vistoria, obras e recursos de prevenção.
2. Quando reforçar a prontidão da Defesa Civil (calendário e limiares de chuva).
3. Onde verificar possível subnotificação de ocorrências.
4. Que perfil de município pede que tipo de estratégia.

## 5. Informações necessárias
Registros de desastres (Atlas/S2iD), chuva por município e por dia (ERA5, validada com o INMET), população e área (IBGE Censo 2022) e a malha municipal. Fontes, URLs e confiabilidade estão em `02_catalogo_dados.md`.

## 6. Justificativa
O tema reúne dados públicos de várias fontes, tem impacto social direto, permite cruzar chuva medida com registros oficiais e admite análise estatística e preditiva. O período começa em 2013 porque o S2iD só tem dados a partir daí.

## 7. Escopo real e limites
- **293 dos 645 municípios** (Adamantina a Jumirim, na ordem do código IBGE), porque a cota diária da API Open-Meteo esgotou. A amostra não é aleatória e cobre 135 dos 339 registros (39,8%).
- Só 41 de 645 municípios (6,4%) têm estação INMET; por isso a chuva vem do ERA5, validado contra 23 estações (r mensal mediano 0,82; r diário 0,52).
- O Atlas depende de notificação municipal: "sem registro" não é "sem desastre".
- Renda, saneamento e outros indicadores socioeconômicos não foram integrados.

## 8. Alternativas consideradas
Mobilidade urbana e desperdício de alimentos foram citados e descartados em favor deste tema.
