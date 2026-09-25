"""Gera eventos.json (formato FullCalendar) a partir da planilha com colunas de anos."""
import csv, io, json, os, re, sys, urllib.request
from datetime import date, datetime, timedelta

avisos = []

def ler_linhas():
    fonte = os.environ.get("CSV_URL") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if fonte.startswith("http"):
        with urllib.request.urlopen(fonte) as r:
            texto = r.read().decode("utf-8")
    else:
        with open(fonte, encoding="utf-8") as f:
            texto = f.read()

    for n, l in enumerate(csv.DictReader(io.StringIO(texto)), start=2):
        l = {(k or "").strip(): (v or "").strip() for k, v in l.items()}
        l["_linha"] = n
        yield l

def ler_data(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    return None

def sim(v):
    return (v or "").strip().lower() in ("sim", "s", "true", "1", "x")

def hora(v):
    return v[:5] if v else ""

def norma(l):
    tipo = l.get("tipo_norma", "")
    num = l.get("numero_norma", "")
    ano = l.get("ano_norma", "")
    art = l.get("artigo", "")
    if not tipo:
        return ""
    txt = tipo
    if num:
        txt += f" nº {num}" + (f"/{ano}" if ano else "")
    elif ano:
        txt += f" de {ano}"
    if art:
        txt += f", art. {art}"
    return txt

linhas = [l for l in ler_linhas() if sim(l.get("publicar")) and l.get("titulo") and l.get("id")]
anos = sorted(k for k in (linhas[0].keys() if linhas else []) if re.fullmatch(r"\d{4}", k))

saida = []

for l in linhas:
    h_ini = hora(l.get("hora_inicio", ""))
    h_fim = hora(l.get("hora_fim", ""))

    props_base = {
        "tipo": l.get("tipo", ""),
        "categoria": l.get("categoria", ""),
        "nivel": l.get("nivel", ""),
        "tags": [t.strip() for t in l.get("tags", "").split(",") if t.strip()],
        "regra": l.get("regra_data", ""),
        "local": l.get("local", ""),
        "resumo": l.get("resumo", ""),
        "descricao": l.get("descricao", ""),
        "norma": norma(l),
        "ementa": l.get("ementa", ""),
        "link": l.get("link", ""),
        "imagem": l.get("imagem", ""),
        "fonte": l.get("fonte", ""),
        "ano_origem": int(l["ano_origem"]) if l.get("ano_origem", "").isdigit() else None,
        "evidenciar": sim(l.get("evidenciar")),
        "relembrar": sim(l.get("relembrar")),
    }

    teve_data = False

    for a in anos:
        cel = l.get(a, "")
        if not cel:
            continue

        partes = [p.strip() for p in re.split(r"\s+a\s+", cel)]
        ini = ler_data(partes[0])

        if ini:
            fim = ler_data(partes[1]) if len(partes) > 1 else None
            ev = {
                "id": f"{l['id']}-{a}",
                "title": l["titulo"],
                "allDay": not h_ini,
                "start": ini.isoformat() + (f"T{h_ini}" if h_ini else ""),
                "extendedProps": {**props_base, "precisao": "dia", "ano": int(a)},
            }
            if fim and fim > ini:
                if h_ini:
                    ev["end"] = f"{fim.isoformat()}T{h_fim or h_ini}"
                else:
                    ev["end"] = (fim + timedelta(days=1)).isoformat()
            saida.append(ev)
            teve_data = True
        elif re.fullmatch(r"\d{1,2}/\d{4}", cel):
            mes = int(cel.split("/")[0])
            saida.append({
                "id": f"{l['id']}-{a}",
                "title": l["titulo"],
                "extendedProps": {**props_base, "precisao": "mes", "ano": int(a), "mes": mes},
            })
            teve_data = True
        elif re.fullmatch(r"\d{4}", cel):
            saida.append({
                "id": f"{l['id']}-{a}",
                "title": l["titulo"],
                "extendedProps": {**props_base, "precisao": "ano", "ano": int(a)},
            })
            teve_data = True
        else:
            avisos.append(f'Linha {l["_linha"]} ({l["id"]}), coluna {a}: formato não reconhecido "{cel}"')

    if not teve_data:
        avisos.append(f'Linha {l["_linha"]} ({l["id"]}): nenhuma data válida preenchida')

def ordenacao(e):
    if "start" in e:
        return e["start"]
    p = e["extendedProps"]
    return f"{p['ano']:04d}-{(p.get('mes') or 1):02d}"

saida.sort(key=ordenacao)

with open("eventos.json", "w", encoding="utf-8") as f:
    json.dump(saida, f, ensure_ascii=False, indent=2)

for a in avisos:
    print(f"::warning::{a}")

print(f"{len(saida)} ocorrências gravadas em eventos.json")
