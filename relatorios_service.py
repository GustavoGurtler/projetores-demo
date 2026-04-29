def montar_relatorio_ti(reservas):
    resumo = {
        "total_reservas": len(reservas),
        "total_professores": len({reserva["sigla"] for reserva in reservas}),
        "total_salas": len(
            {(reserva["nivel"], reserva["sala"]) for reserva in reservas}
        ),
        "total_com_som": sum(1 for reserva in reservas if reserva["som"] == "Sim"),
    }

    por_dia = {}
    por_sigla = {}
    por_nivel = {}

    for reserva in reservas:
        dados_dia = por_dia.setdefault(
            reserva["data"],
            {
                "data": reserva["data"],
                "total_reservas": 0,
                "professores": set(),
                "salas": set(),
            },
        )
        dados_dia["total_reservas"] += 1
        dados_dia["professores"].add(reserva["sigla"])
        dados_dia["salas"].add((reserva["nivel"], reserva["sala"]))

        dados_sigla = por_sigla.setdefault(
            reserva["sigla"],
            {
                "sigla": reserva["sigla"],
                "total_reservas": 0,
                "dias": set(),
                "niveis": set(),
            },
        )
        dados_sigla["total_reservas"] += 1
        dados_sigla["dias"].add(reserva["data"])
        dados_sigla["niveis"].add(reserva["nivel_label"])

        dados_nivel = por_nivel.setdefault(
            reserva["nivel"],
            {
                "nivel": reserva["nivel"],
                "nivel_label": reserva["nivel_label"],
                "total_reservas": 0,
                "total_com_som": 0,
                "professores": set(),
                "salas": set(),
            },
        )
        dados_nivel["total_reservas"] += 1
        dados_nivel["total_com_som"] += int(reserva["som"] == "Sim")
        dados_nivel["professores"].add(reserva["sigla"])
        dados_nivel["salas"].add(reserva["sala_label"])

    dias = sorted(
        (
            {
                "data": item["data"],
                "total_reservas": item["total_reservas"],
                "total_professores": len(item["professores"]),
                "total_salas": len(item["salas"]),
            }
            for item in por_dia.values()
        ),
        key=lambda item: item["data"],
    )

    siglas = sorted(
        (
            {
                "sigla": item["sigla"],
                "total_reservas": item["total_reservas"],
                "total_dias": len(item["dias"]),
                "niveis": ", ".join(sorted(item["niveis"])),
            }
            for item in por_sigla.values()
        ),
        key=lambda item: (-item["total_reservas"], item["sigla"]),
    )

    niveis = sorted(
        (
            {
                "nivel": item["nivel"],
                "nivel_label": item["nivel_label"],
                "total_reservas": item["total_reservas"],
                "total_com_som": item["total_com_som"],
                "total_professores": len(item["professores"]),
                "total_salas": len(item["salas"]),
            }
            for item in por_nivel.values()
        ),
        key=lambda item: item["nivel_label"],
    )

    return {
        "resumo": resumo,
        "por_dia": dias,
        "por_sigla": siglas,
        "por_nivel": niveis,
    }


def montar_relatorio_computadores_ti(requisicoes):
    resumo = {
        "total_requisicoes": len(requisicoes),
        "total_itens": sum(requisicao["quantidade"] for requisicao in requisicoes),
        "total_professores": len({requisicao["sigla"] for requisicao in requisicoes}),
        "total_locais": len(
            {
                (
                    requisicao["nivel"],
                    requisicao["local"],
                    requisicao["recurso"],
                )
                for requisicao in requisicoes
            }
        ),
    }

    por_dia = {}
    por_sigla = {}
    por_recurso = {}

    for requisicao in requisicoes:
        dados_dia = por_dia.setdefault(
            requisicao["data"],
            {
                "data": requisicao["data"],
                "total_requisicoes": 0,
                "total_itens": 0,
                "professores": set(),
            },
        )
        dados_dia["total_requisicoes"] += 1
        dados_dia["total_itens"] += requisicao["quantidade"]
        dados_dia["professores"].add(requisicao["sigla"])

        dados_sigla = por_sigla.setdefault(
            requisicao["sigla"],
            {
                "sigla": requisicao["sigla"],
                "total_requisicoes": 0,
                "total_itens": 0,
                "dias": set(),
                "recursos": set(),
            },
        )
        dados_sigla["total_requisicoes"] += 1
        dados_sigla["total_itens"] += requisicao["quantidade"]
        dados_sigla["dias"].add(requisicao["data"])
        dados_sigla["recursos"].add(requisicao["recurso_label"])

        dados_recurso = por_recurso.setdefault(
            requisicao["recurso"],
            {
                "recurso": requisicao["recurso"],
                "recurso_label": requisicao["recurso_label"],
                "capacidade_total": requisicao["recurso_total"],
                "capacidade_label": requisicao["capacidade_label"],
                "total_requisicoes": 0,
                "total_itens": 0,
                "professores": set(),
                "locais": set(),
            },
        )
        dados_recurso["total_requisicoes"] += 1
        dados_recurso["total_itens"] += requisicao["quantidade"]
        dados_recurso["professores"].add(requisicao["sigla"])
        dados_recurso["locais"].add(requisicao["local_label"])

    dias = sorted(
        (
            {
                "data": item["data"],
                "total_requisicoes": item["total_requisicoes"],
                "total_itens": item["total_itens"],
                "total_professores": len(item["professores"]),
            }
            for item in por_dia.values()
        ),
        key=lambda item: item["data"],
    )

    siglas = sorted(
        (
            {
                "sigla": item["sigla"],
                "total_requisicoes": item["total_requisicoes"],
                "total_itens": item["total_itens"],
                "total_dias": len(item["dias"]),
                "recursos": ", ".join(sorted(item["recursos"])),
            }
            for item in por_sigla.values()
        ),
        key=lambda item: (-item["total_itens"], item["sigla"]),
    )

    recursos = sorted(
        (
            {
                "recurso": item["recurso"],
                "recurso_label": item["recurso_label"],
                "capacidade_total": item["capacidade_total"],
                "capacidade_label": item["capacidade_label"],
                "total_requisicoes": item["total_requisicoes"],
                "total_itens": item["total_itens"],
                "total_professores": len(item["professores"]),
                "total_locais": len(item["locais"]),
            }
            for item in por_recurso.values()
        ),
        key=lambda item: item["recurso_label"],
    )

    return {
        "resumo": resumo,
        "por_dia": dias,
        "por_sigla": siglas,
        "por_recurso": recursos,
    }
