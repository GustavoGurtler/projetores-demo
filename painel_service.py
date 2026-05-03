from collections import defaultdict

from domain import FAMILIAS_PROJETORES, HORARIOS, NIVEL_LABELS, ORDEM_TIPO_TAREFA
from domain import RECURSOS_COMPUTADORES, TOTAL_PROJETORES, hora_para_minutos


HORARIOS_ORDEM = {
    nivel: {faixa["inicio"]: indice for indice, faixa in enumerate(faixas)}
    for nivel, faixas in HORARIOS.items()
}


def formatar_horario(minutos):
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


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


def montar_tarefas_computadores(requisicoes):
    if not requisicoes:
        return []

    intervalos = []
    for requisicao in requisicoes:
        if not requisicao.get("horario_fim"):
            continue

        intervalos.append(
            {
                "id": str(requisicao["id"]),
                "nivel": requisicao["nivel"],
                "nivel_label": requisicao["nivel_label"],
                "recurso": requisicao["recurso"],
                "recurso_label": requisicao["recurso_label"],
                "local_label": requisicao["local_label"],
                "quantidade_label": requisicao["quantidade_label"],
                "quantidade": requisicao["quantidade"],
                "usa_quantidade": requisicao["usa_quantidade"],
                "descricao": (requisicao.get("descricao") or "").strip(),
                "inicio": hora_para_minutos(requisicao["horario"]),
                "fim": hora_para_minutos(requisicao["horario_fim"]),
                "aula_inicio": requisicao["aula_label"],
                "aula_fim": requisicao["aula_label"],
                "aula_ordem_inicio": HORARIOS_ORDEM.get(
                    requisicao["nivel"],
                    {},
                ).get(requisicao["horario"]),
                "aula_ordem_fim": HORARIOS_ORDEM.get(
                    requisicao["nivel"],
                    {},
                ).get(requisicao["horario"]),
            }
        )

    agrupados = {}
    for intervalo in intervalos:
        chave = (
            intervalo["nivel_label"],
            intervalo["recurso"],
            intervalo["local_label"],
            intervalo["quantidade_label"],
            intervalo["descricao"],
        )
        agrupados.setdefault(chave, []).append(intervalo)

    intervalos_mesclados = []
    for itens in agrupados.values():
        itens_ordenados = sorted(itens, key=lambda item: item["inicio"])
        atual = itens_ordenados[0]
        for item in itens_ordenados[1:]:
            aulas_consecutivas = (
                item["nivel"] == atual["nivel"]
                and item["aula_ordem_inicio"] is not None
                and atual["aula_ordem_fim"] is not None
                and item["aula_ordem_inicio"] == atual["aula_ordem_fim"] + 1
            )
            if item["inicio"] == atual["fim"] or aulas_consecutivas:
                atual["fim"] = item["fim"]
                atual["aula_fim"] = item["aula_fim"]
                atual["aula_ordem_fim"] = item["aula_ordem_fim"]
            else:
                intervalos_mesclados.append(atual)
                atual = item
        intervalos_mesclados.append(atual)

    tarefas = []
    tarefas_por_id = {}
    remover_ids = set()
    complemento_recurso_labels = {
        "chromebook": "CPD",
        "notebook_samsung": "carrinho",
    }

    def adicionar_tarefa(tarefa):
        tarefas.append(tarefa)
        tarefas_por_id[tarefa["id"]] = tarefa

    def ajustar_tarefa_quantidade(task_id, intervalo, quantidade_restante, tipo):
        if quantidade_restante <= 0:
            remover_ids.add(task_id)
            return

        tarefa = tarefas_por_id.get(task_id)
        if not tarefa:
            return

        if tipo == "entregar":
            tarefa["descricao"] = (
                f"Levar {quantidade_restante} de {intervalo['recurso_label']} "
                f"para {intervalo['local_label']}."
                f"{intervalo['descricao_extra']}"
            )
        else:
            tarefa["descricao"] = (
                f"Retirar {quantidade_restante} de {intervalo['recurso_label']} "
                f"da {intervalo['local_label']}."
                f"{intervalo['descricao_extra']}"
            )

    for intervalo in intervalos_mesclados:
        inicio_str = formatar_horario(intervalo["inicio"])
        fim_str = formatar_horario(intervalo["fim"])
        descricao_extra = (
            f" Obs: {intervalo['descricao']}."
            if intervalo["descricao"]
            else ""
        )
        intervalo["descricao_extra"] = descricao_extra

        if intervalo["recurso"] == "laboratorio_sala15":
            adicionar_tarefa(
                {
                    "id": f"entregar:{intervalo['id']}",
                    "tipo": "entregar",
                    "horario": inicio_str,
                    "ordem": intervalo["inicio"],
                    "momento": "Ligar Sala 15",
                    "descricao": f"Ligar Sala 15.{descricao_extra}",
                    "nivel": intervalo["nivel"],
                    "nivel_label": intervalo["nivel_label"],
                }
            )
            adicionar_tarefa(
                {
                    "id": f"guardar:{intervalo['id']}",
                    "tipo": "guardar",
                    "horario": fim_str,
                    "ordem": intervalo["fim"],
                    "momento": "Desligar Sala 15",
                    "descricao": f"Desligar Sala 15.{descricao_extra}",
                    "nivel": intervalo["nivel"],
                    "nivel_label": intervalo["nivel_label"],
                }
            )
            continue

        adicionar_tarefa(
            {
                "id": f"entregar:{intervalo['id']}",
                "tipo": "entregar",
                "horario": inicio_str,
                "ordem": intervalo["inicio"],
                "momento": f"Antes da {intervalo['aula_inicio']}",
                "descricao": (
                    f"Levar {intervalo['quantidade_label']} de "
                    f"{intervalo['recurso_label']} para {intervalo['local_label']}."
                    f"{descricao_extra}"
                ),
                "nivel": intervalo["nivel"],
                "nivel_label": intervalo["nivel_label"],
            }
        )
        adicionar_tarefa(
            {
                "id": f"guardar:{intervalo['id']}",
                "tipo": "guardar",
                "horario": fim_str,
                "ordem": intervalo["fim"],
                "momento": f"Ap\u00f3s a {intervalo['aula_fim']}",
                "descricao": (
                    f"Retirar {intervalo['quantidade_label']} de "
                    f"{intervalo['recurso_label']} da {intervalo['local_label']}."
                    f"{descricao_extra}"
                ),
                "nivel": intervalo["nivel"],
                "nivel_label": intervalo["nivel_label"],
            }
        )

    intervalos_por_recurso = {}
    for intervalo in intervalos_mesclados:
        if intervalo["recurso"] == "laboratorio_sala15":
            continue
        intervalos_por_recurso.setdefault(intervalo["recurso"], []).append(intervalo)

    for itens in intervalos_por_recurso.values():
        fins = {}
        inicios = {}
        fins_por_aula = {}
        inicios_por_aula = {}

        for intervalo in itens:
            fins.setdefault(intervalo["fim"], []).append(intervalo)
            inicios.setdefault(intervalo["inicio"], []).append(intervalo)

            if intervalo["aula_ordem_fim"] is not None:
                fins_por_aula.setdefault(
                    (intervalo["nivel"], intervalo["aula_ordem_fim"]),
                    [],
                ).append(intervalo)

            if intervalo["aula_ordem_inicio"] is not None:
                inicios_por_aula.setdefault(
                    (intervalo["nivel"], intervalo["aula_ordem_inicio"]),
                    [],
                ).append(intervalo)

        def registrar_mover(origem, destino, instante):
            if origem["local_label"] == destino["local_label"]:
                return
            if not origem["usa_quantidade"] or not destino["usa_quantidade"]:
                return

            quantidade_mover = min(origem["quantidade"], destino["quantidade"])
            if quantidade_mover <= 0:
                return

            complemento_quantidade = max(0, destino["quantidade"] - quantidade_mover)
            complemento_label = complemento_recurso_labels.get(
                destino["recurso"],
                destino["recurso_label"],
            )
            complemento_texto = (
                f" +{complemento_quantidade} do {complemento_label}"
                if complemento_quantidade and complemento_label
                else ""
            )
            descricao_extra = (
                f" Obs: {destino['descricao']}."
                if destino["descricao"]
                else ""
            )
            tarefas.append(
                {
                    "id": f"mover:{origem['id']}:{destino['id']}",
                    "tipo": "mover",
                    "horario": formatar_horario(instante),
                    "ordem": instante,
                    "momento": f"Troca para {destino['aula_inicio']}",
                    "descricao": (
                        f"Mover {quantidade_mover} de "
                        f"{origem['local_label']} para {destino['local_label']}."
                        f"{complemento_texto}"
                        f"{descricao_extra}"
                    ),
                    "nivel": destino["nivel"],
                    "nivel_label": destino["nivel_label"],
                }
            )
            ajustar_tarefa_quantidade(
                f"guardar:{origem['id']}",
                origem,
                origem["quantidade"] - quantidade_mover,
                "guardar",
            )
            remover_ids.add(f"entregar:{destino['id']}")

        for instante in set(fins.keys()) & set(inicios.keys()):
            finais = fins.get(instante, [])
            iniciais = inicios.get(instante, [])
            while finais and iniciais:
                origem = finais.pop(0)
                destino = iniciais.pop(0)
                registrar_mover(origem, destino, instante)

        for chave, finais in list(fins_por_aula.items()):
            nivel, ordem = chave
            iniciais = inicios_por_aula.get((nivel, ordem + 1), [])
            while finais and iniciais:
                origem = finais.pop(0)
                destino = iniciais.pop(0)
                if origem["fim"] == destino["inicio"]:
                    continue
                registrar_mover(origem, destino, origem["fim"])

    return [tarefa for tarefa in tarefas if tarefa["id"] not in remover_ids]
