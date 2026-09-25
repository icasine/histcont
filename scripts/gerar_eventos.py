"""
Gera eventos.json (formato FullCalendar) a partir da planilha publicada em CSV.

Uso:
    CSV_URL=<link csv> python scripts/gerar_eventos.py
    python scripts/gerar_eventos.py arquivo.csv

Colunas esperadas:
    id_hist_cont, titulo, grupo, tipo, categoria, nivel, tags, regra_data,
    ano_2024 ... ano_2035, hora_inicio, hora_fim, local, resumo, descricao,
    tipo_norma, numero_norma, ano_norma, artigo, ementa, link, imagem, fonte,
    ano_origem, evidenciar, relembrar, publicar, obs_internas

Cada coluna ano_AAAA vira uma ocorrência. Para acrescentar um ano,
basta criar a coluna (ex.: ano_2036). Formatos aceitos na célula:
    dd/mm/aaaa | dd/mm/aaaa a dd/mm/aaaa | mm/aaaa | aaaa
Célula vazia: não acontece naquele ano ou ainda não tem data.

Somente linhas com publicar = sim entram. obs_internas nunca vai para o JSON.
"""

import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta

avisos = []


def ler_linhas():
    fonte = os.environ.get("CSV_URL") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not fonte:
        raise RuntimeError("Informe CSV_URL ou um arquivo CSV.")
    if fonte.startswith("http"):
        with urllib.request.urlopen(fonte) as r:
            dados = r.read()
        try:
            texto = dados.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = dados.decode("latin-1")
    else:
        with open(fonte, encoding="utf-8-sig") as f:
            texto = f.read()
    for n, linha in enumerate(csv.DictReader(io.StringIO(texto)), start=2):
        linha = {(k or "").strip(): (v or "").strip() for k, v in linha.items()}
        linha["_linha"] = n
        yield linha


def ler_data(valor):
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor.strip(), formato).date()
        except ValueError:
            pass
    return None


def sim(valor):
    return (valor or "").strip().lower() in ("sim", "s", "true", "1", "x")


def hora(valor):
    valor = (valor or "").strip()
    m = re.match(r"(\d{1,2}):(\d{2})", valor)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else ""


def norma(linha):
    tipo = linha.get("tipo_norma", "")
    numero = linha.get("numero_norma", "")
    ano = linha.get("ano_norma", "")
    artigo = linha.get("artigo", "")
    if not tipo:
        return ""
    texto = tipo
    if numero:
        texto += f" nº {numero}" + (f"/{ano}" if ano else "")
    elif ano:
        texto += f" de {ano}"
    if artigo:
        texto += f", art. {artigo}"
    return texto


todas = list(ler_linhas())

# Colunas ano_2024, ano_2025... (aceita também 2024, 2025...)
colunas_ano = sorted(
    (int(m.group(1)), k)
    for k in (todas[0].keys() if todas else [])
    for m in [re.fullmatch(r"(?:ano_)?(\d{4})", k)]
    if m
)

linhas = [
    l for l in todas
    if sim(l.get("publicar")) and l.get("titulo") and l.get("id_hist_cont")
]

saida = []
ids_vistos = set()

for linha in linhas:
    n = linha["_linha"]
    id_base = linha["id_hist_cont"]
    if id_base in ids_vistos:
        avisos.append(f'Linha {n}: id_hist_cont repetido "{id_base}"')
    ids_vistos.add(id_base)

    hora_inicio = hora(linha.get("hora_inicio"))
    hora_fim = hora(linha.get("hora_fim"))

    props_base = {
        "grupo": linha.get("grupo", ""),
        "tipo": linha.get("tipo", ""),
        "categoria": linha.get("categoria", ""),
        "nivel": linha.get("nivel", ""),
        "tags": [t.strip() for t in linha.get("tags", "").split(",") if t.strip()],
        "regra": linha.get("regra_data", ""),
        "local": linha.get("local", ""),
        "resumo": linha.get("resumo", ""),
        "descricao": linha.get("descricao", ""),
        "norma": norma(linha),
        "ementa": linha.get("ementa", ""),
        "link": linha.get("link", ""),
        "imagem": linha.get("imagem", ""),
        "fonte": linha.get("fonte", ""),
        "ano_origem": int(linha["ano_origem"]) if linha.get("ano_origem", "").isdigit() else None,
        "evidenciar": sim(linha.get("evidenciar")),
        "relembrar": sim(linha.get("relembrar")),
    }

    teve_data = False

    for ano, coluna in colunas_ano:
        celula = linha.get(coluna, "")
        if not celula:
            continue
        base = {"id": f"{id_base}-{ano}", "title": linha["titulo"]}
        partes = [p.strip() for p in re.split(r"\s+a\s+", celula, flags=re.IGNORECASE)]
        inicio = ler_data(partes[0])

        if inicio:
            fim = ler_data(partes[1]) if len(partes) > 1 else None
            evento = {
                **base,
                "allDay": not hora_inicio,
                "start": inicio.isoformat() + (f"T{hora_inicio}" if hora_inicio else ""),
                "extendedProps": {**props_base, "precisao": "dia", "ano": ano},
            }
            if fim and fim > inicio:
                if hora_inicio:
                    evento["end"] = f"{fim.isoformat()}T{hora_fim or hora_inicio}"
                else:
                    evento["end"] = (fim + timedelta(days=1)).isoformat()  # fim exclusivo
            elif hora_inicio and hora_fim:
                evento["end"] = f"{inicio.isoformat()}T{hora_fim}"
            saida.append(evento)
            teve_data = True
        elif re.fullmatch(r"\d{1,2}/\d{4}", celula):
            mes = int(celula.split("/")[0])
            saida.append({**base, "extendedProps": {**props_base, "precisao": "mes", "ano": ano, "mes": mes}})
            teve_data = True
        elif re.fullmatch(r"\d{4}", celula):
            saida.append({**base, "extendedProps": {**props_base, "precisao": "ano", "ano": ano}})
            teve_data = True
        else:
            avisos.append(f'Linha {n} ({id_base}), coluna {coluna}: formato não reconhecido "{celula}"')

    if not teve_data:
        avisos.append(f"Linha {n} ({id_base}): nenhuma data válida preenchida")


def ordenacao(evento):
    if "start" in evento:
        return evento["start"]
    p = evento["extendedProps"]
    return f"{p['ano']:04d}-{p.get('mes', 1):02d}"


saida.sort(key=ordenacao)

with open("eventos.json", "w", encoding="utf-8") as arquivo:
    json.dump(saida, arquivo, ensure_ascii=False, indent=2)

if not colunas_ano:
    avisos.append("Nenhuma coluna de ano (ano_AAAA) encontrada na planilha")

for aviso in avisos:
    print(f"::warning::{aviso}")

print(f"{len(saida)} ocorrências gravadas em eventos.json ({len(linhas)} linhas publicadas)")
