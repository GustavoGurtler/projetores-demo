def obter_clausula_ignorar_id(registro_id_ignorado):
    if registro_id_ignorado is None:
        return "", ()
    return " AND id != ?", (registro_id_ignorado,)


def verificar_conflitos_reserva(
    cursor,
    data_reserva,
    horario,
    nivel,
    sala,
    total_projetores,
    reserva_id_ignorada=None,
):
    clausula, parametros_extra = obter_clausula_ignorar_id(reserva_id_ignorada)

    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM reservas
        WHERE data = ? AND horario = ? AND nivel = ? AND sala = ?{clausula}
        """,
        (data_reserva, horario, nivel, sala, *parametros_extra),
    )
    conflito_sala = cursor.fetchone()[0] > 0

    cursor.execute(
        f"""
        SELECT COUNT(DISTINCT sala)
        FROM reservas
        WHERE data = ? AND horario = ? AND nivel = ?{clausula}
        """,
        (data_reserva, horario, nivel, *parametros_extra),
    )
    limite_atingido = cursor.fetchone()[0] >= total_projetores

    return conflito_sala, limite_atingido


def registrar_reservas_projetor(
    cursor,
    sigla,
    sala,
    data_reserva,
    nivel,
    aulas,
    som,
    *,
    salas,
    horarios_por_inicio,
    total_projetores,
):
    resultado = {
        "inseridas": 0,
        "bloqueios_sala": 0,
        "bloqueios_limite": 0,
        "sala_label": salas[nivel].get(sala, f"Sala {sala}"),
    }

    for aula in aulas:
        if aula not in horarios_por_inicio[nivel]:
            resultado["bloqueios_sala"] += 1
            continue

        conflito_sala, limite_atingido = verificar_conflitos_reserva(
            cursor,
            data_reserva,
            aula,
            nivel,
            sala,
            total_projetores,
        )

        if conflito_sala:
            resultado["bloqueios_sala"] += 1
            continue

        if limite_atingido:
            resultado["bloqueios_limite"] += 1
            continue

        cursor.execute(
            """
            INSERT INTO reservas (sigla, sala, data, horario, nivel, som)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (sigla, sala, data_reserva, aula, nivel, som),
        )
        resultado["inseridas"] += 1

    return resultado


def montar_mensagens_reserva_projetor(resultado):
    mensagens = []
    tipo = "success"

    if resultado["inseridas"]:
        mensagens.append(
            f"{resultado['inseridas']} hor\u00e1rio(s) reservado(s) de projetor para {resultado['sala_label']}."
        )

    if resultado["bloqueios_sala"]:
        tipo = "warning"
        mensagens.append(
            f"{resultado['bloqueios_sala']} hor\u00e1rio(s) j\u00e1 tinham projetor reservado nessa sala."
        )

    if resultado["bloqueios_limite"]:
        tipo = "warning"
        mensagens.append(
            f"{resultado['bloqueios_limite']} hor\u00e1rio(s) n\u00e3o foram reservados porque os 4 projetores do n\u00edvel j\u00e1 estavam em uso."
        )

    return mensagens, tipo
