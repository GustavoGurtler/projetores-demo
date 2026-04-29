from collections import defaultdict

from domain import FAMILIAS_PROJETORES, HORARIOS, NIVEL_LABELS, ORDEM_TIPO_TAREFA
from domain import RECURSOS_COMPUTADORES, TOTAL_PROJETORES, hora_para_minutos


def montar_painel_disponibilidade_computadores(disponibilidade):
    ocupacao = {
        (nivel, horario, recurso): quantidade
        for horario, nivel, recurso, quantidade in disponibilidade
    }

    painel = []
    for recurso, configuracao in RECURSOS_COMPUTADORES.items():
        niveis = []
        for nivel in ("Fundamental", "Medio"):
            itens = []
            for faixa in HORARIOS[nivel]:
                solicitados = ocupacao.get((nivel, faixa["inicio"], recurso), 0)
                disponiveis = max(0, configuracao["total"] - solicitados)
                usa_quantidade = configuracao.get("usa_quantidade", True)
                itens.append(
                    {
                        "aula": faixa["label"],
                        "inicio": faixa["inicio"],
                        "fim": faixa["fim"],
                        "solicitados": solicitados,
                        "disponiveis": disponiveis,
                        "lotado": disponiveis <= 0,
                        "disponiveis_label": (
                            f"{disponiveis} livres"
                            if usa_quantidade
                            else ("Dispon\u00edvel" if disponiveis > 0 else "Reservada")
                        ),
                    }
                )

            niveis.append(
                {
                    "nivel": nivel,
                    "nivel_label": NIVEL_LABELS[nivel],
                    "itens": itens,
                }
            )

        painel.append(
            {
                "recurso": recurso,
                "recurso_label": configuracao["label"],
                "capacidade_total": configuracao["total"],
                "usa_quantidade": configuracao.get("usa_quantidade", True),
                "capacidade_label": configuracao.get(
                    "capacidade_label",
                    f"{configuracao['total']} unidades",
                ),
                "niveis": niveis,
            }
        )

    return painel


def montar_painel_disponibilidade(disponibilidade):
    ocupacao = {
        (nivel, horario): quantidade
        for horario, nivel, quantidade in disponibilidade
    }

    painel = []
    for nivel in ("Fundamental", "Medio"):
        itens = []
        for faixa in HORARIOS[nivel]:
            ocupados = ocupacao.get((nivel, faixa["inicio"]), 0)
            disponiveis = max(0, TOTAL_PROJETORES - ocupados)
            itens.append(
                {
                    "aula": faixa["label"],
                    "inicio": faixa["inicio"],
                    "fim": faixa["fim"],
                    "ocupados": ocupados,
                    "disponiveis": disponiveis,
                    "lotado": disponiveis <= 0,
                }
            )

        painel.append(
            {
                "nivel": nivel,
                "nivel_label": NIVEL_LABELS[nivel],
                "itens": itens,
            }
        )

    return painel


def ordenar_reserva(reserva):
    return (reserva["sala_label"], reserva["sigla"])


def deduplicar_reservas_para_projetor(reservas):
    reservas_unicas = {}

    for reserva in sorted(
        reservas,
        key=lambda item: (
            item["data"],
            item["nivel"],
            item["horario"],
            item["sala"],
            item["sigla"],
            item["id"],
        ),
    ):
        chave = (reserva["data"], reserva["nivel"], reserva["horario"], reserva["sala"])
        reservas_unicas.setdefault(chave, reserva)

    return list(reservas_unicas.values())


def rotulo_projetor(nivel, numero):
    familia = FAMILIAS_PROJETORES.get(nivel, "Projetor")
    return f"Projetor {familia} {numero}"


def criar_acao_ti(nivel, tipo, horario, momento, descricao):
    return {
        "tipo": tipo,
        "horario": horario,
        "ordem": hora_para_minutos(horario),
        "momento": momento,
        "descricao": descricao,
        "nivel": nivel,
        "nivel_label": NIVEL_LABELS[nivel],
    }


def atribuir_projetores(reservas_atuais, alocacao_anterior):
    alocacao_atual = {}
    projetores_usados = set()
    projetores_por_sala = defaultdict(list)

    for projetor, reserva in alocacao_anterior.items():
        projetores_por_sala[reserva["sala"]].append(projetor)

    pendentes = []

    for reserva in sorted(reservas_atuais, key=ordenar_reserva):
        projetor = None
        while projetores_por_sala[reserva["sala"]]:
            candidato = projetores_por_sala[reserva["sala"]].pop(0)
            if candidato not in projetores_usados:
                projetor = candidato
                break

        if projetor is None:
            pendentes.append(reserva)
            continue

        alocacao_atual[projetor] = reserva
        projetores_usados.add(projetor)

    livres = [
        numero
        for numero in range(1, TOTAL_PROJETORES + 1)
        if numero not in projetores_usados
    ]

    for reserva in pendentes:
        if not livres:
            break
        projetor = livres.pop(0)
        alocacao_atual[projetor] = reserva
        projetores_usados.add(projetor)

    return alocacao_atual


def descrever_troca(faixa_anterior, faixa_atual):
    if faixa_anterior["fim"] == faixa_atual["inicio"]:
        return (
            faixa_atual["inicio"],
            f"Troca para a {faixa_atual['label']}",
        )

    return (
        faixa_anterior["fim"],
        (
            f"Intervalo antes da {faixa_atual['label']} "
            f"({faixa_anterior['fim']} - {faixa_atual['inicio']})"
        ),
    )


def gerar_acoes_transicao(nivel, indice_faixa, alocacao_anterior, alocacao_atual):
    faixas = HORARIOS[nivel]
    faixa_atual = faixas[indice_faixa]
    faixa_anterior = faixas[indice_faixa - 1] if indice_faixa > 0 else None
    acoes = []

    for projetor in range(1, TOTAL_PROJETORES + 1):
        reserva_anterior = alocacao_anterior.get(projetor)
        reserva_atual = alocacao_atual.get(projetor)
        projetor_label = rotulo_projetor(nivel, projetor)

        if not reserva_anterior and reserva_atual:
            acoes.append(
                criar_acao_ti(
                    nivel=nivel,
                    tipo="entregar",
                    horario=faixa_atual["inicio"],
                    momento=f"Antes da {faixa_atual['label']}",
                    descricao=(
                        f"Levar o {projetor_label} para "
                        f"{reserva_atual['sala_label']}."
                    ),
                )
            )
            continue

        if reserva_anterior and reserva_atual:
            horario, momento = descrever_troca(faixa_anterior, faixa_atual)
            if reserva_anterior["sala"] == reserva_atual["sala"]:
                continue

            acoes.append(
                criar_acao_ti(
                    nivel=nivel,
                    tipo="mover",
                    horario=horario,
                    momento=momento,
                    descricao=(
                        f"Mover o {projetor_label} de "
                        f"{reserva_anterior['sala_label']} para "
                        f"{reserva_atual['sala_label']}."
                    ),
                )
            )
            continue

        if reserva_anterior and not reserva_atual:
            acoes.append(
                criar_acao_ti(
                    nivel=nivel,
                    tipo="guardar",
                    horario=faixa_anterior["fim"],
                    momento=f"Ap\u00f3s o fim da {faixa_anterior['label']}",
                    descricao=(
                        f"Guardar o {projetor_label}, retirando-o de "
                        f"{reserva_anterior['sala_label']}."
                    ),
                )
            )

    return acoes


def gerar_planejamento_ti(reservas):
    reservas = deduplicar_reservas_para_projetor(reservas)
    reservas_por_nivel = defaultdict(list)
    for reserva in reservas:
        reservas_por_nivel[reserva["nivel"]].append(reserva)

    planejamento = []

    for nivel in ("Fundamental", "Medio"):
        reservas_agrupadas = defaultdict(list)
        for reserva in reservas_por_nivel[nivel]:
            reservas_agrupadas[reserva["horario"]].append(reserva)

        alocacao_anterior = {}
        acoes = []
        ocupacao = []

        for indice, faixa in enumerate(HORARIOS[nivel]):
            reservas_faixa = reservas_agrupadas.get(faixa["inicio"], [])
            alocacao_atual = atribuir_projetores(reservas_faixa, alocacao_anterior)

            acoes.extend(
                gerar_acoes_transicao(nivel, indice, alocacao_anterior, alocacao_atual)
            )

            ocupacao.append(
                {
                    "aula": faixa["label"],
                    "inicio": faixa["inicio"],
                    "fim": faixa["fim"],
                    "reservas": [
                        {
                            "projetor": projetor,
                            "projetor_label": rotulo_projetor(nivel, projetor),
                            **reserva,
                        }
                        for projetor, reserva in sorted(alocacao_atual.items())
                    ],
                    "disponiveis": TOTAL_PROJETORES - len(alocacao_atual),
                }
            )

            alocacao_anterior = alocacao_atual

        planejamento.append(
            {
                "nivel": nivel,
                "nivel_label": NIVEL_LABELS[nivel],
                "tem_reservas": bool(reservas_por_nivel[nivel]),
                "acoes": acoes,
                "ocupacao": ocupacao,
            }
        )

    return planejamento


def montar_tarefas_do_dia(planejamento):
    tarefas = []

    for bloco in planejamento:
        tarefas.extend(bloco["acoes"])

    return sorted(
        tarefas,
        key=lambda tarefa: (
            tarefa["ordem"],
            ORDEM_TIPO_TAREFA.get(tarefa["tipo"], 99),
            tarefa["nivel_label"],
            tarefa["descricao"],
        ),
    )
