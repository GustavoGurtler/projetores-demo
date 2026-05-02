from datetime import date, timedelta

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


def popular_dados_demo(caminho_banco, hoje=None):
    hoje = hoje or date.today()
    conn = conectar(caminho_banco)
    cursor = conn.cursor()

    _popular_usuarios(cursor)

    if _tabela_vazia(cursor, "reservas") and _tabela_vazia(
        cursor,
        "requisicoes_computadores",
    ):
        _popular_reservas(cursor, hoje)
        _popular_requisicoes_computadores(cursor, hoje)

    conn.commit()
    conn.close()


def _popular_usuarios(cursor):
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


def _tabela_vazia(cursor, tabela):
    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
    return cursor.fetchone()[0] == 0
