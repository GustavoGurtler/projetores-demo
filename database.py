import sqlite3


def conectar(caminho_banco):
    return sqlite3.connect(caminho_banco)


def criar_tabelas(caminho_banco):
    conn = conectar(caminho_banco)
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS reservas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sigla TEXT,
            sala TEXT,
            data TEXT,
            horario TEXT,
            nivel TEXT,
            som TEXT
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sigla TEXT UNIQUE,
            senha_hash TEXT,
            tipo TEXT
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS requisicoes_computadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sigla TEXT,
            recurso TEXT,
            quantidade INTEGER,
            local TEXT,
            data TEXT,
            horario TEXT,
            nivel TEXT
        )
        """
    )

    c.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_reservas_data_horario_nivel
        ON reservas (data, horario, nivel)
        """
    )

    c.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_reservas_sigla
        ON reservas (sigla)
        """
    )

    c.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_requisicoes_computadores_data_horario
        ON requisicoes_computadores (data, horario, recurso, nivel)
        """
    )

    c.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_requisicoes_computadores_sigla
        ON requisicoes_computadores (sigla)
        """
    )

    conn.commit()
    conn.close()
