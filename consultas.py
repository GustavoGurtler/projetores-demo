def buscar_disponibilidade_computadores_geral(conectar):
    conn = conectar()
    c = conn.cursor()

    c.execute(
        """
        SELECT data, horario, nivel, recurso, COALESCE(SUM(quantidade), 0)
        FROM requisicoes_computadores
        GROUP BY data, horario, nivel, recurso
        """
    )
    disponibilidade = c.fetchall()

    c.execute(
        """
        SELECT DISTINCT data, horario, nivel, recurso, local
        FROM requisicoes_computadores
        """
    )
    locais_ocupados = c.fetchall()

    conn.close()
    return disponibilidade, locais_ocupados


def buscar_requisicoes_computadores_por_data(
    conectar,
    serializar_requisicao,
    data_filtro,
):
    conn = conectar()
    c = conn.cursor()

    c.execute(
        """
        SELECT *
        FROM requisicoes_computadores
        WHERE data = ?
        ORDER BY nivel, recurso, horario, local, sigla
        """,
        (data_filtro,),
    )
    requisicoes = [
        serializar_requisicao(linha)
        for linha in c.fetchall()
    ]

    c.execute(
        """
        SELECT horario, nivel, recurso, COALESCE(SUM(quantidade), 0)
        FROM requisicoes_computadores
        WHERE data = ?
        GROUP BY horario, nivel, recurso
        """,
        (data_filtro,),
    )
    disponibilidade = c.fetchall()

    conn.close()
    return requisicoes, disponibilidade


def buscar_requisicao_computador_por_id(conectar, serializar_requisicao, requisicao_id):
    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        SELECT *
        FROM requisicoes_computadores
        WHERE id = ?
        """,
        (requisicao_id,),
    )
    linha = c.fetchone()
    conn.close()

    if not linha:
        return None

    return serializar_requisicao(linha)


def buscar_disponibilidade_geral(conectar):
    conn = conectar()
    c = conn.cursor()

    c.execute(
        """
        SELECT data, horario, nivel, COUNT(DISTINCT sala)
        FROM reservas
        GROUP BY data, horario, nivel
        """
    )

    disponibilidade = c.fetchall()

    c.execute(
        """
        SELECT DISTINCT data, horario, nivel, sala
        FROM reservas
        """
    )
    salas_ocupadas = c.fetchall()

    conn.close()
    return disponibilidade, salas_ocupadas


def buscar_reservas_por_data(conectar, serializar_reserva, data_filtro):
    conn = conectar()
    c = conn.cursor()

    c.execute(
        """
        SELECT * FROM reservas
        WHERE data = ?
        ORDER BY nivel, horario, sala, sigla
        """,
        (data_filtro,),
    )
    reservas = [serializar_reserva(linha) for linha in c.fetchall()]

    c.execute(
        """
        SELECT horario, nivel, COUNT(DISTINCT sala)
        FROM reservas
        WHERE data = ?
        GROUP BY horario, nivel
        """,
        (data_filtro,),
    )
    disponibilidade = c.fetchall()

    conn.close()
    return reservas, disponibilidade


def buscar_reserva_por_id(conectar, serializar_reserva, reserva_id):
    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        SELECT *
        FROM reservas
        WHERE id = ?
        """,
        (reserva_id,),
    )
    linha = c.fetchone()
    conn.close()

    if not linha:
        return None

    return serializar_reserva(linha)


def buscar_reservas_relatorio(
    conectar,
    serializar_reserva,
    data_inicial,
    data_final,
    nivel="",
    sigla="",
):
    filtros = ["data BETWEEN ? AND ?"]
    parametros = [data_inicial, data_final]

    if nivel:
        filtros.append("nivel = ?")
        parametros.append(nivel)

    if sigla:
        filtros.append("sigla = ?")
        parametros.append(sigla)

    conn = conectar()
    c = conn.cursor()
    c.execute(
        f"""
        SELECT *
        FROM reservas
        WHERE {' AND '.join(filtros)}
        ORDER BY data, nivel, horario, sala, sigla
        """,
        tuple(parametros),
    )
    reservas = [serializar_reserva(linha) for linha in c.fetchall()]
    conn.close()
    return reservas


def buscar_requisicoes_computadores_relatorio(
    conectar,
    serializar_requisicao,
    data_inicial,
    data_final,
    nivel="",
    sigla="",
    recurso="",
):
    filtros = ["data BETWEEN ? AND ?"]
    parametros = [data_inicial, data_final]

    if nivel:
        filtros.append("nivel = ?")
        parametros.append(nivel)

    if sigla:
        filtros.append("sigla = ?")
        parametros.append(sigla)

    if recurso:
        filtros.append("recurso = ?")
        parametros.append(recurso)

    conn = conectar()
    c = conn.cursor()
    c.execute(
        f"""
        SELECT *
        FROM requisicoes_computadores
        WHERE {' AND '.join(filtros)}
        ORDER BY data, nivel, recurso, horario, local, sigla
        """,
        tuple(parametros),
    )
    requisicoes = [
        serializar_requisicao(linha)
        for linha in c.fetchall()
    ]
    conn.close()
    return requisicoes
