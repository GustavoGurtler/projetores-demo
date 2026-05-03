from datetime import date, datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from database import conectar


DEMO_USERS = [
    {"sigla": "ANA", "senha": "demo123", "tipo": "professor"},
    {"sigla": "BIA", "senha": "demo123", "tipo": "professor"},
    {"sigla": "CAI", "senha": "demo123", "tipo": "professor"},
    {"sigla": "DIO", "senha": "demo123", "tipo": "professor"},
    {"sigla": "EVA", "senha": "demo123", "tipo": "professor"},
    {"sigla": "SUP", "senha": "admin123", "tipo": "ti"},
    {"sigla": "TEC", "senha": "admin123", "tipo": "ti"},
]

DEMO_CREDENTIALS = [
    {"sigla": "ANA", "senha": "demo123", "perfil": "Professor"},
    {"sigla": "TEC", "senha": "admin123", "perfil": "Equipe de TI"},
]

DEMO_RESET_KEY = "ultimo_reset"


def popular_dados_demo(caminho_banco, hoje=None, agora=None):
    hoje = hoje or date.today()
    agora = agora or datetime.now(timezone.utc)
    conn = conectar(caminho_banco)
    cursor = conn.cursor()

    _popular_usuarios(cursor)

    if _tabela_vazia(cursor, "reservas") and _tabela_vazia(
        cursor,
        "requisicoes_computadores",
    ):
        _popular_reservas(cursor, hoje)
        _popular_requisicoes_computadores(cursor, hoje)
        _salvar_controle(cursor, DEMO_RESET_KEY, agora.isoformat())
    elif not _buscar_controle(cursor, DEMO_RESET_KEY):
        _salvar_controle(cursor, DEMO_RESET_KEY, agora.isoformat())

    conn.commit()
    conn.close()


def manter_dados_demo(
    caminho_banco,
    intervalo_horas,
    limite_registros,
    hoje=None,
    agora=None,
):
    hoje = hoje or date.today()
    agora = agora or datetime.now(timezone.utc)
    conn = conectar(caminho_banco)
    cursor = conn.cursor()

    if _precisa_resetar_demo(cursor, agora, intervalo_horas, limite_registros):
        _resetar_registros_demo(cursor, hoje)
        _popular_usuarios(cursor)
        _salvar_controle(cursor, DEMO_RESET_KEY, agora.isoformat())

    conn.commit()
    conn.close()


def _popular_usuarios(cursor):
    siglas_demo = [usuario["sigla"] for usuario in DEMO_USERS]
    placeholders = ", ".join(["?"] * len(siglas_demo))
    cursor.execute(
        f"""
        DELETE FROM usuarios
        WHERE sigla NOT IN ({placeholders})
        """,
        siglas_demo,
    )

    for usuario in DEMO_USERS:
        senha_hash = generate_password_hash(usuario["senha"])
        cursor.execute(
            """
            SELECT id
            FROM usuarios
            WHERE sigla = ?
            """,
            (usuario["sigla"],),
        )
        existente = cursor.fetchone()

        if existente:
            cursor.execute(
                """
                UPDATE usuarios
                SET senha_hash = ?, tipo = ?
                WHERE sigla = ?
                """,
                (senha_hash, usuario["tipo"], usuario["sigla"]),
            )
            continue

        cursor.execute(
            """
            INSERT INTO usuarios (sigla, senha_hash, tipo)
            VALUES (?, ?, ?)
            """,
            (usuario["sigla"], senha_hash, usuario["tipo"]),
        )


def _popular_reservas(cursor, hoje):
    amanha = (hoje + timedelta(days=1)).isoformat()
    depois = (hoje + timedelta(days=2)).isoformat()

    reservas = [
        ("ANA", "11", amanha, "07:25", "Fundamental", "Sim"),
        ("BIA", "12", amanha, "08:15", "Fundamental", "Nao"),
        ("CAI", "1", depois, "07:00", "Medio", "Nao"),
        ("DIO", "15", depois, "08:55", "Medio", "Nao"),
    ]

    cursor.executemany(
        """
        INSERT INTO reservas (sigla, sala, data, horario, nivel, som)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        reservas,
    )


def _popular_requisicoes_computadores(cursor, hoje):
    amanha = (hoje + timedelta(days=1)).isoformat()
    depois = (hoje + timedelta(days=2)).isoformat()

    requisicoes = [
        ("ANA", "notebook_samsung", 10, "11", amanha, "07:25", "Fundamental"),
        ("BIA", "chromebook", 12, "12", amanha, "08:15", "Fundamental"),
        ("CAI", "laboratorio_sala15", 1, "LAB15", depois, "08:55", "Medio"),
    ]

    cursor.executemany(
        """
        INSERT INTO requisicoes_computadores
            (sigla, recurso, quantidade, local, data, horario, nivel)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        requisicoes,
    )


def _resetar_registros_demo(cursor, hoje):
    cursor.execute("DELETE FROM reservas")
    cursor.execute("DELETE FROM requisicoes_computadores")
    _popular_reservas(cursor, hoje)
    _popular_requisicoes_computadores(cursor, hoje)


def _precisa_resetar_demo(cursor, agora, intervalo_horas, limite_registros):
    if _tabela_vazia(cursor, "reservas") or _tabela_vazia(
        cursor,
        "requisicoes_computadores",
    ):
        return True

    if _total_registros(cursor, "reservas") > limite_registros:
        return True

    if _total_registros(cursor, "requisicoes_computadores") > limite_registros:
        return True

    ultimo_reset = _buscar_controle(cursor, DEMO_RESET_KEY)
    if not ultimo_reset:
        return True

    try:
        ultimo_reset_data = datetime.fromisoformat(ultimo_reset)
    except ValueError:
        return True

    return agora - ultimo_reset_data >= timedelta(hours=intervalo_horas)


def _buscar_controle(cursor, chave):
    cursor.execute(
        """
        SELECT valor
        FROM demo_controle
        WHERE chave = ?
        """,
        (chave,),
    )
    linha = cursor.fetchone()
    if not linha:
        return None
    return linha[0]


def _salvar_controle(cursor, chave, valor):
    cursor.execute(
        """
        INSERT INTO demo_controle (chave, valor)
        VALUES (?, ?)
        ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
        """,
        (chave, valor),
    )


def _total_registros(cursor, tabela):
    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
    return cursor.fetchone()[0]


def _tabela_vazia(cursor, tabela):
    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
    return cursor.fetchone()[0] == 0
