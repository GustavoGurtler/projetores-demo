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

    conn.commit()
    conn.close()
