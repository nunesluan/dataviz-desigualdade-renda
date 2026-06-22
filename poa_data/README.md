# Dados intraurbanos de Porto Alegre (Censo 2010 / IBGE)

Segunda fonte do trabalho, usada **apenas na aba "Porto Alegre"** para descer ao
recorte intraurbano (por **setor censitário**) que a PNAD Contínua por UF não
alcança. As demais páginas seguem usando exclusivamente a PNAD/SIDRA.

## Arquivos versionados (saída do processamento)
- `poa_setores.geojson` — geometria dos 2.433 setores censitários de Porto Alegre
  (município 4314902), SIRGAS 2000 (lat/lon). ~1,4 MB.
- `poa_setores.csv` — atributos por setor: `bairro`, `pop`, `renda_total`,
  `renda_pc` (renda per capita mensal), `pct_negra` (preta+parda), `pct_branca`.
- `build_poa.py` — script que gera os dois arquivos acima a partir dos brutos.

## Fontes (Censo Demográfico 2010 — Resultados do Universo)
1. **Malha de setores censitários** (shapefile, RS):
   `geoftp.ibge.gov.br/.../censo_2010/setores_censitarios_shp/rs/rs_setores_censitarios.zip`
2. **Agregados por setor censitário** (RS):
   `ftp.ibge.gov.br/Censos/Censo_Demografico_2010/Resultados_do_Universo/Agregados_por_Setores_Censitarios/`
   - `DomicilioRenda_RS.csv` → **V003** = rendimento nominal mensal total dos
     domicílios particulares permanentes do setor.
   - `Pessoa03_RS.csv` → **V001** total de pessoas; **V002** branca, **V003** preta,
     **V004** amarela, **V005** parda, **V006** indígena.

Métricas derivadas: `renda_pc = V003 / V001`; `pct_negra = (preta+parda)/V001`.

## Reproduzir
```bash
# baixar os brutos para poa_data/raw/ (≈150 MB, ignorados pelo git) e extrair, depois:
uv run --with pyshp python poa_data/build_poa.py
```
A pasta `poa_data/raw/` é **gitignorada** e pode ser apagada após gerar os arquivos
de saída (basta rebaixar para reprocessar).

## Observação para o artigo
Declarar esta 2ª fonte em "Descrição dos dados": *Censo Demográfico 2010 (IBGE),
agregados por setor censitário de Porto Alegre*. A aba mostra a **desigualdade de
renda no território** da cidade e sua forte associação com a composição por cor/raça
(correlação renda per capita × % população negra ≈ −0,70), conectando o recorte
urbano ao tema de gênero/raça do trabalho.
