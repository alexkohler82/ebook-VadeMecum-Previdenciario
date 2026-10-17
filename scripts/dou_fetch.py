#!/usr/bin/env python3
"""Fase 0: baixa a Seção 1 (ou outra) do DOU de um dia e lista os atos que
casam com o filtro previdenciário/assistencial. Só biblioteca padrão.

Fonte: página 'Leitura do Jornal' do in.gov.br, que embute o JSON do dia numa
tag <script id="params">. [Unverified] O formato pode mudar; o HTML bruto é
salvo em out/ para depuração.

Uso: dou_fetch.py [--data DD-MM-AAAA] [--secao do1] [--out out]
"""
import argparse, html, json, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

BRT = timezone(timedelta(hours=-3))

ORGAOS = [
    "previdência", "previdencia", "instituto nacional do seguro social",
    "desenvolvimento e assistência social", "conselho nacional de previdência",
    "conselho de recursos da previdência", "casa civil", "presidência da república",
]
TERMOS = [
    "previdenci", "aposentadoria", "pensão por morte", "auxílio-doença",
    "auxílio por incapacidade", "auxílio-acidente", "auxílio-reclusão",
    "salário-maternidade", "benefício de prestação continuada", "bpc", "loas",
    "assistência social", "cadastro único", "regime geral de previdência",
    "rgps", "rpps", "inss", "cnis", "seguro-desemprego", "bolsa família",
]

def baixar(data, secao):
    url = f"https://www.in.gov.br/leiturajornal?secao={secao}&data={data}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (vademecum-monitor)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return url, r.status, r.read().decode("utf-8", "replace")

def extrair(pagina):
    m = re.search(r'<script[^>]*id="params"[^>]*>(.*?)</script>', pagina, re.S)
    if not m:
        return None
    return json.loads(m.group(1)).get("jsonArray", [])

def limpa(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def casa(ato):
    texto = " ".join(limpa(str(ato.get(k, ""))) for k in ("title", "hierarchyStr", "content", "artType")).lower()
    return [t for t in TERMOS if t in texto], any(o in texto for o in ORGAOS)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=datetime.now(BRT).strftime("%d-%m-%Y"))
    ap.add_argument("--secao", default="do1")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    import os
    os.makedirs(a.out, exist_ok=True)

    url, status, pagina = baixar(a.data, a.secao)
    open(f"{a.out}/{a.secao}-{a.data}.html", "w", encoding="utf-8").write(pagina)
    print(f"GET {url} -> HTTP {status}, {len(pagina)} bytes")

    atos = extrair(pagina)
    if atos is None:
        print("ERRO: tag <script id=\"params\"> não encontrada; veja o HTML salvo.")
        sys.exit(2)
    print(f"{len(atos)} atos no jornal {a.secao} de {a.data}")

    achados = []
    for ato in atos:
        termos, orgao = casa(ato)
        if termos:
            achados.append({
                "titulo": limpa(ato.get("title")),
                "tipo": ato.get("artType"),
                "orgao": ato.get("hierarchyStr"),
                "url": "https://www.in.gov.br/web/dou/-/" + str(ato.get("urlTitle", "")),
                "termos": termos,
                "orgao_relevante": orgao,
            })
    json.dump(achados, open(f"{a.out}/achados-{a.secao}-{a.data}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"{len(achados)} atos casam com o filtro:")
    for x in achados[:50]:
        print(f"- [{x['tipo']}] {x['titulo']} | {x['orgao']} | {', '.join(x['termos'][:4])}\n  {x['url']}")

if __name__ == "__main__":
    main()
