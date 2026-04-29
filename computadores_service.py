def obter_clausula_ignorar_id(registro_id_ignorado):
    if registro_id_ignorado is None:
        return "", ()
    return " AND id != ?", (registro_id_ignorado,)


def verificar_conflitos_requisicao_computador(
    cursor,
    data_requisicao,
    horario,
    nivel,
    recurso,
    local,
    quantidade,
    recursos_computadores,
    requisicao_id_ignorada=None,
):
    clausula, parametros_extra = obter_clausula_ignorar_id(requisicao_id_ignorada)

    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM requisicoes_computadores
        WHERE data = ? AND horario = ? AND nivel = ? AND recurso = ? AND local = ?{clausula}
        """,
        (data_requisicao, horario, nivel, recurso, local, *parametros_extra),
    )
    conflito_local = cursor.fetchone()[0] > 0

    cursor.execute(
        f"""
        SELECT COALESCE(SUM(quantidade), 0)
        FROM requisicoes_computadores
        WHERE data = ? AND horario = ? AND nivel = ? AND recurso = ?{clausula}
        """,
        (data_requisicao, horario, nivel, recurso, *parametros_extra),
    )
    quantidade_ja_solicitada = cursor.fetchone()[0]
    total_recurso = recursos_computadores[recurso]["total"]
    limite_excedido = quantidade_ja_solicitada + quantidade > total_recurso

    return conflito_local, limite_excedido, max(0, total_recurso - quantidade_ja_solicitada)


def registrar_requisicoes_computador(
    cursor,
    sigla,
    recurso,
    quantidade_int,
    local_normalizado,
    data_requisicao,
    nivel,
    aulas,
    *,
    recursos_computadores,
    horarios_por_inicio,
    rotulo_local,
):
    resultado = {
        "inseridas": 0,
        "bloqueios_local": 0,
        "bloqueios_limite": 0,
        "recurso_label": recursos_computadores[recurso]["label"],
        "local_label": rotulo_local(nivel, recurso, local_normalizado),
        "quantidade": quantidade_int,
        "usa_quantidade": recursos_computadores[recurso].get("usa_quantidade", True),
    }

    for aula in aulas:
        if aula not in horarios_por_inicio[nivel]:
            resultado["bloqueios_local"] += 1
            continue

        conflito_local, limite_excedido, _ = verificar_conflitos_requisicao_computador(
            cursor,
            data_requisicao,
            aula,
            nivel,
            recurso,
            local_normalizado,
            quantidade_int,
            recursos_computadores,
        )

        if conflito_local:
            resultado["bloqueios_local"] += 1
            continue

        if limite_excedido:
            resultado["bloqueios_limite"] += 1
            continue

        cursor.execute(
            """
            INSERT INTO requisicoes_computadores
                (sigla, recurso, quantidade, local, data, horario, nivel)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sigla,
                recurso,
                quantidade_int,
                local_normalizado,
                data_requisicao,
                aula,
                nivel,
            ),
        )
        resultado["inseridas"] += 1

    return resultado


def montar_mensagens_requisicao_computador(resultado):
    mensagens = []
    tipo = "success"

    if resultado["inseridas"]:
        if resultado["usa_quantidade"]:
            mensagens.append(
                (
                    f"{resultado['inseridas']} hor\u00e1rio(s) solicitados para "
                    f"{resultado['recurso_label']} em {resultado['local_label']}, "
                    f"quantidade {resultado['quantidade']}."
                )
            )
        else:
            mensagens.append(
                f"{resultado['inseridas']} hor\u00e1rio(s) reservados para {resultado['recurso_label']}."
            )

    if resultado["bloqueios_local"]:
        tipo = "warning"
        mensagens.append(
            (
                f"{resultado['bloqueios_local']} hor\u00e1rio(s) j\u00e1 tinham requisi\u00e7\u00e3o "
                "desse recurso para esse local."
            )
        )

    if resultado["bloqueios_limite"]:
        tipo = "warning"
        mensagens.append(
            (
                f"{resultado['bloqueios_limite']} hor\u00e1rio(s) n\u00e3o foram solicitados porque "
                "a quantidade ultrapassa a disponibilidade do recurso."
            )
        )

    return mensagens, tipo
