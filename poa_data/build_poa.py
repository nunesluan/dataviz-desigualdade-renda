"""
Recorta os setores censitários de Porto Alegre (Censo 2010, IBGE) e junta
renda + composição por cor/raça. Gera arquivos pequenos para o dashboard:

  poa_data/poa_setores.geojson  — geometria dos setores de POA (SIRGAS 2000)
  poa_data/poa_setores.csv      — atributos por setor (renda per capita, % negra…)

Fontes (Censo Demográfico 2010 — Resultados do Universo):
  - Malha de setores censitários (shapefile) — geoftp.ibge.gov.br
  - Agregados por setor: DomicilioRenda (V003 = rendimento total dos domicílios)
    e Pessoa03 (V001 total; V002 branca, V003 preta, V004 amarela, V005 parda,
    V006 indígena).

Uso:  uv run --with pyshp python poa_data/build_poa.py
"""
import csv
import json
import os

import shapefile  # pyshp

BASE = os.path.dirname(__file__)
RAW = os.path.join(BASE, "raw")
MUN_POA = "4314902"  # código IBGE do município de Porto Alegre


def _num(x):
    x = (x or "").strip().replace(",", ".")
    try:
        return float(x)
    except ValueError:
        return None  # setores com dado suprimido ("X") ou vazio


def carregar_renda():
    """Cod_setor -> rendimento total mensal dos domicílios (DomicilioRenda V003)."""
    out = {}
    with open(os.path.join(RAW, "agreg", "DomicilioRenda_RS.csv"),
             encoding="latin-1") as f:
        rd = csv.DictReader(f, delimiter=";")
        for row in rd:
            cod = row["Cod_setor"].strip()
            if cod[:7] == MUN_POA:
                out[cod] = _num(row.get("V003"))
    return out


def carregar_raca():
    """Cod_setor -> (pop, branca, preta, parda) a partir de Pessoa03."""
    out = {}
    with open(os.path.join(RAW, "agreg", "Pessoa03_RS.csv"),
             encoding="latin-1") as f:
        rd = csv.DictReader(f, delimiter=";")
        for row in rd:
            cod = row["Cod_setor"].strip()
            if cod[:7] == MUN_POA:
                out[cod] = (
                    _num(row.get("V001")), _num(row.get("V002")),
                    _num(row.get("V003")), _num(row.get("V005")),
                )
    return out


def _round_geom(geom, nd=5):
    """Arredonda coordenadas para reduzir o tamanho do GeoJSON."""
    def r(c):
        if isinstance(c, (list, tuple)):
            if c and isinstance(c[0], (int, float)):
                return [round(float(c[0]), nd), round(float(c[1]), nd)]
            return [r(x) for x in c]
        return c
    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}


def main():
    renda = carregar_renda()
    raca = carregar_raca()
    print(f"setores POA — renda: {len(renda)}, raça: {len(raca)}")

    sf = shapefile.Reader(os.path.join(RAW, "geom", "43SEE250GC_SIR"),
                          encoding="latin-1")
    flds = [f[0] for f in sf.fields[1:]]
    i_cod = flds.index("CD_GEOCODI")
    i_mun = flds.index("CD_GEOCODM")
    i_bairro = flds.index("NM_BAIRRO")

    feats, rows = [], []
    for sr in sf.iterShapeRecords():
        rec = sr.record
        if rec[i_mun] != MUN_POA:
            continue
        cod = rec[i_cod].strip()
        bairro = (rec[i_bairro] or "").strip().title() or "—"

        pop, branca, preta, parda = raca.get(cod, (None, None, None, None))
        rtot = renda.get(cod)
        renda_pc = (rtot / pop) if (rtot and pop) else None
        negra = (preta or 0) + (parda or 0)
        pct_negra = (negra / pop * 100) if pop else None
        pct_branca = (branca / pop * 100) if (branca is not None and pop) else None

        feats.append({
            "type": "Feature",
            "id": cod,
            "properties": {"cod": cod, "bairro": bairro},
            "geometry": _round_geom(sr.shape.__geo_interface__),
        })
        rows.append({
            "cod": cod, "bairro": bairro, "pop": pop or 0,
            "renda_total": rtot or 0, "renda_pc": renda_pc,
            "pct_negra": pct_negra, "pct_branca": pct_branca,
        })

    gj = {"type": "FeatureCollection", "features": feats}
    with open(os.path.join(BASE, "poa_setores.geojson"), "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False)

    cols = ["cod", "bairro", "pop", "renda_total", "renda_pc", "pct_negra", "pct_branca"]
    with open(os.path.join(BASE, "poa_setores.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    com_renda = sum(1 for r in rows if r["renda_pc"] is not None)
    sz = os.path.getsize(os.path.join(BASE, "poa_setores.geojson")) / 1024
    print(f"setores no shapefile (POA): {len(feats)} | com renda válida: {com_renda}")
    print(f"geojson: {sz:.0f} KB  |  csv: {len(rows)} linhas")


if __name__ == "__main__":
    main()
