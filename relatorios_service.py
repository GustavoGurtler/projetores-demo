from io import BytesIO
from xml.sax.saxutils import escape as escapar_xml
from zipfile import ZIP_DEFLATED, ZipFile

def montar_registros_relatorio_geral(reservas, requisicoes):
    registros = []

    for reserva in reservas:
        registros.append(
            {
                "id": reserva["id"],
                "origem": "projetor",
                "tipo": "Projetor",
                "sigla": reserva["sigla"],
                "recurso": "projetor",
                "recurso_label": "Projetor",
                "quantidade": 1,
                "quantidade_label": "1 projetor",
                "local_label": reserva["sala_label"],
                "data": reserva["data"],
                "horario": reserva["horario"],
                "horario_fim": reserva["horario_fim"],
                "aula_label": reserva["aula_label"],
                "nivel_label": reserva["nivel_label"],
                "detalhe": "Com som" if reserva["som"] == "Sim" else "",
            }
        )

    for requisicao in requisicoes:
        registros.append(
            {
                "id": requisicao["id"],
                "origem": "computador",
                "tipo": (
                    "Sala 15"
                    if requisicao["recurso"] == "laboratorio_sala15"
                    else "Computador"
                ),
                "sigla": requisicao["sigla"],
                "recurso": requisicao["recurso"],
                "recurso_label": requisicao["recurso_label"],
                "quantidade": requisicao["quantidade"],
                "quantidade_label": requisicao["quantidade_label"],
                "local_label": requisicao["local_label"],
                "data": requisicao["data"],
                "horario": requisicao["horario"],
                "horario_fim": requisicao["horario_fim"],
                "aula_label": requisicao["aula_label"],
                "nivel_label": requisicao["nivel_label"],
                "detalhe": requisicao.get("descricao") or "",
            }
        )

    return sorted(
        registros,
        key=lambda item: (
            item["data"],
            item["nivel_label"],
            item["horario"],
            item["tipo"],
            item["local_label"],
            item["sigla"],
        ),
    )


def montar_relatorio_geral_ti(registros):
    resumo = {
        "total_solicitacoes": len(registros),
        "total_professores": len({item["sigla"] for item in registros}),
        "solicitacoes_projetor": sum(
            1 for item in registros if item["origem"] == "projetor"
        ),
        "solicitacoes_computadores": sum(
            1 for item in registros if item["origem"] == "computador"
        ),
    }

    por_sigla = {}

    for item in registros:
        dados_sigla = por_sigla.setdefault(
            item["sigla"],
            {
                "sigla": item["sigla"],
                "total_solicitacoes": 0,
                "projetores": 0,
                "chromebooks": 0,
                "notebooks": 0,
                "sala15": 0,
                "dias": set(),
            },
        )
        dados_sigla["total_solicitacoes"] += 1
        dados_sigla["projetores"] += int(item["origem"] == "projetor")
        dados_sigla["chromebooks"] += int(item["recurso"] == "chromebook")
        dados_sigla["notebooks"] += int(item["recurso"] == "notebook_samsung")
        dados_sigla["sala15"] += int(item["recurso"] == "laboratorio_sala15")
        dados_sigla["dias"].add(item["data"])

    siglas = sorted(
        (
            {
                "sigla": item["sigla"],
                "total_solicitacoes": item["total_solicitacoes"],
                "projetores": item["projetores"],
                "chromebooks": item["chromebooks"],
                "notebooks": item["notebooks"],
                "sala15": item["sala15"],
                "total_dias": len(item["dias"]),
            }
            for item in por_sigla.values()
        ),
        key=lambda item: (-item["total_solicitacoes"], item["sigla"]),
    )

    return {
        "resumo": resumo,
        "por_sigla": siglas,
    }


def _coluna_excel(numero):
    letras = ""
    while numero:
        numero, resto = divmod(numero - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _celula_texto_excel(referencia, valor):
    texto = "" if valor is None else str(valor)
    return (
        f'<c r="{referencia}" t="inlineStr">'
        f"<is><t>{escapar_xml(texto)}</t></is>"
        "</c>"
    )


def _linhas_planilha_excel(cabecalhos, linhas):
    todas_linhas = [cabecalhos] + linhas
    linhas_xml = []

    for indice_linha, valores in enumerate(todas_linhas, start=1):
        celulas = []
        for indice_coluna, valor in enumerate(valores, start=1):
            referencia = f"{_coluna_excel(indice_coluna)}{indice_linha}"
            celulas.append(_celula_texto_excel(referencia, valor))
        linhas_xml.append(f'<row r="{indice_linha}">{"".join(celulas)}</row>')

    return "".join(linhas_xml)


def _xml_planilha_excel(cabecalhos, linhas):
    total_linhas = max(1, len(linhas) + 1)
    total_colunas = max(1, len(cabecalhos))
    dimensao = f"A1:{_coluna_excel(total_colunas)}{total_linhas}"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<dimension ref="{dimensao}"/>
<sheetViews><sheetView workbookViewId="0"/></sheetViews>
<sheetFormatPr defaultRowHeight="15"/>
<sheetData>{_linhas_planilha_excel(cabecalhos, linhas)}</sheetData>
</worksheet>"""


def gerar_xlsx_relatorio_geral_ti(registros, relatorio):
    resumo_cabecalhos = [
        "Sigla",
        "Solicitacoes",
        "Projetor",
        "Chromebook",
        "Notebook",
        "Sala 15",
        "Dias",
    ]
    resumo_linhas = [
        [
            item["sigla"],
            item["total_solicitacoes"],
            item["projetores"],
            item["chromebooks"],
            item["notebooks"],
            item["sala15"],
            item["total_dias"],
        ]
        for item in relatorio["por_sigla"]
    ]

    detalhes_cabecalhos = [
        "Data",
        "Sigla",
        "Recurso",
        "Quantidade",
        "Local",
        "Horario",
        "Aula",
        "Nivel",
    ]
    detalhes_linhas = [
        [
            item["data"],
            item["sigla"],
            item["recurso_label"],
            item["quantidade_label"],
            item["local_label"],
            (
                f"{item['horario']} - {item['horario_fim']}"
                if item["horario_fim"]
                else item["horario"]
            ),
            item["aula_label"],
            item["nivel_label"],
        ]
        for item in registros
    ]

    planilhas = [
        ("Uso por Professor", resumo_cabecalhos, resumo_linhas),
        ("Solicitacoes", detalhes_cabecalhos, detalhes_linhas),
    ]

    arquivo = BytesIO()
    with ZipFile(arquivo, "w", ZIP_DEFLATED) as xlsx:
        xlsx.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        xlsx.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        xlsx.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets>
<sheet name="Uso por Professor" sheetId="1" r:id="rId1"/>
<sheet name="Solicitacoes" sheetId="2" r:id="rId2"/>
</sheets>
</workbook>""",
        )
        xlsx.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
</Relationships>""",
        )

        for indice, (_, cabecalhos, linhas) in enumerate(planilhas, start=1):
            xlsx.writestr(
                f"xl/worksheets/sheet{indice}.xml",
                _xml_planilha_excel(cabecalhos, linhas),
            )

    arquivo.seek(0)
    return arquivo
