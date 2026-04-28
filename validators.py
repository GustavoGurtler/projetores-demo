from datetime import date


def normalizar_som(valor):
    if valor in {"Nao", "N\u00e3o", "N\u00c3\u00a3o"}:
        return "N\u00e3o"
    if valor in {"Sim", "sim"}:
        return "Sim"
    return valor or "N\u00e3o"


def normalizar_sigla_professor(valor):
    return "".join(letra for letra in (valor or "").strip().upper() if letra.isalpha())


def normalizar_local_requisicao_computador(recurso, local, recursos_computadores):
    configuracao = recursos_computadores.get(recurso, {})
    return configuracao.get("local_fixo", local)


def obter_quantidade_inteira(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def validar_requisicao_computador(
    nivel,
    recurso,
    local,
    data_requisicao,
    quantidade,
    *,
    salas,
    recursos_computadores,
    horarios_por_inicio,
    limite_computadores_por_reserva,
    horario=None,
):
    if nivel not in salas:
        return "Selecione um n\u00edvel v\u00e1lido.", None, None

    configuracao = recursos_computadores.get(recurso)
    if not configuracao:
        return "Selecione um recurso de computador v\u00e1lido.", None, None

    if configuracao.get("usa_quantidade", True):
        quantidade_int = obter_quantidade_inteira(quantidade)
        if quantidade_int is None or quantidade_int <= 0:
            return "Informe uma quantidade v\u00e1lida.", None, None

        limite_por_reserva = configuracao.get(
            "max_por_reserva",
            min(configuracao["total"], limite_computadores_por_reserva),
        )

        if quantidade_int > limite_por_reserva:
            return (
                f"Cada reserva de computadores pode solicitar no m\u00e1ximo {limite_por_reserva} unidades.",
                None,
                None,
            )

        if quantidade_int > configuracao["total"]:
            return (
                f"A quantidade solicitada excede o limite de {configuracao['total']} unidades para este recurso.",
                None,
                None,
            )
    else:
        quantidade_int = 1

    if not data_requisicao:
        return "Informe a data da requisi\u00e7\u00e3o.", None, None

    try:
        date.fromisoformat(data_requisicao)
    except ValueError:
        return "Informe uma data de requisi\u00e7\u00e3o v\u00e1lida.", None, None

    local_normalizado = normalizar_local_requisicao_computador(
        recurso,
        local,
        recursos_computadores,
    )
    if configuracao.get("usa_sala", True):
        if local_normalizado not in salas[nivel]:
            return (
                "Selecione uma sala v\u00e1lida para o recurso escolhido.",
                None,
                None,
            )

    if horario is not None and horario not in horarios_por_inicio[nivel]:
        return (
            "Selecione um hor\u00e1rio v\u00e1lido para o n\u00edvel escolhido.",
            None,
            None,
        )

    return None, quantidade_int, local_normalizado


def validar_reserva(
    nivel,
    sala,
    data_reserva,
    *,
    salas,
    horarios_por_inicio,
    horario=None,
):
    if nivel not in salas:
        return "Selecione um n\u00edvel v\u00e1lido."

    if sala not in salas[nivel]:
        return "Selecione uma sala v\u00e1lida para o n\u00edvel escolhido."

    if not data_reserva:
        return "Informe a data da reserva."

    try:
        date.fromisoformat(data_reserva)
    except ValueError:
        return "Informe uma data de reserva v\u00e1lida."

    if horario is not None and horario not in horarios_por_inicio[nivel]:
        return "Selecione um hor\u00e1rio v\u00e1lido para o n\u00edvel escolhido."

    return None
