from collections import defaultdict
from datetime import date
from functools import wraps
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from database import conectar as abrir_conexao
from database import criar_tabelas
from validators import normalizar_sigla_professor, normalizar_som
from validators import validar_requisicao_computador, validar_reserva

app = Flask(__name__)
app.config.from_object(Config)

TOTAL_PROJETORES = 4
LIMITE_COMPUTADORES_POR_RESERVA = 15
ORDEM_TIPO_TAREFA = {
    "guardar": 0,
    "mover": 1,
    "entregar": 2,
}
FAMILIAS_PROJETORES = {
    "Fundamental": "Epson",
    "Medio": "Husky",
}
LOCAL_LABORATORIO = "LAB15"
RECURSOS_COMPUTADORES = {
    "notebook_samsung": {
        "label": "Notebook Samsung",
        "total": 15,
        "usa_sala": True,
        "usa_quantidade": True,
        "max_por_reserva": min(15, LIMITE_COMPUTADORES_POR_RESERVA),
        "capacidade_label": "15 unidades no total",
    },
    "chromebook": {
        "label": "Chromebook",
        "total": 35,
        "usa_sala": True,
        "usa_quantidade": True,
        "max_por_reserva": min(35, LIMITE_COMPUTADORES_POR_RESERVA),
        "capacidade_label": "35 unidades no total",
    },
    "laboratorio_sala15": {
        "label": "Sala 15 - Inform\u00e1tica",
        "total": 1,
        "usa_sala": False,
        "usa_quantidade": False,
        "max_por_reserva": 1,
        "local_fixo": LOCAL_LABORATORIO,
        "local_label": "Sala 15 - Inform\u00e1tica",
        "capacidade_label": "Sala exclusiva por hor\u00e1rio",
    },
}
TIPOS_USUARIO = {
    "professor": "Professor",
    "ti": "Equipe de TI",
}

NIVEL_LABELS = {
    "Fundamental": "Ensino Fundamental",
    "Medio": "Ensino M\u00e9dio",
}

SALAS = {
    "Fundamental": {
        "11": "Sala 11 (F61)",
        "12": "Sala 12 (F73)",
        "13": "Sala 13 (F71)",
        "14": "Sala 14 (F63)",
        "17": "Sala 17 (F81)",
        "18": "Sala 18 (F83)",
        "I9": "Sala I9 (F91)",
        "4A": "Sala 4A (F93)",
    },
    "Medio": {
        "1": "Sala 1 (A60)",
        "2": "Sala 2 (I60)",
        "5": "Sala 5 (A50)",
        "6": "Sala 6 (I50)",
        "7": "Sala 7 (A40)",
        "8": "Sala 8 (I40)",
        "15": "Sala 15",
    },
}

HORARIOS = {
    "Medio": [
        {"label": "1\u00aa aula", "inicio": "07:00", "fim": "07:50"},
        {"label": "2\u00aa aula", "inicio": "07:50", "fim": "08:40"},
        {"label": "3\u00aa aula", "inicio": "08:55", "fim": "09:45"},
        {"label": "4\u00aa aula", "inicio": "09:45", "fim": "10:35"},
        {"label": "5\u00aa aula", "inicio": "10:45", "fim": "11:35"},
        {"label": "6\u00aa aula", "inicio": "11:35", "fim": "12:25"},
    ],
    "Fundamental": [
        {"label": "1\u00aa aula", "inicio": "07:25", "fim": "08:15"},
        {"label": "2\u00aa aula", "inicio": "08:15", "fim": "09:05"},
        {"label": "3\u00aa aula", "inicio": "09:25", "fim": "10:15"},
        {"label": "4\u00aa aula", "inicio": "10:15", "fim": "11:05"},
        {"label": "5\u00aa aula", "inicio": "11:05", "fim": "11:55"},
    ],
}

HORARIOS_POR_INICIO = {
    nivel: {faixa["inicio"]: faixa for faixa in faixas}
    for nivel, faixas in HORARIOS.items()
}


def hora_para_minutos(horario):
    horas, minutos = horario.split(":")
    return int(horas) * 60 + int(minutos)


def conectar():
    return abrir_conexao(app.config["DATABASE_PATH"])


criar_tabelas(app.config["DATABASE_PATH"])


def usuario_eh_ti(tipo_usuario=None):
    tipo_usuario = tipo_usuario or session.get("usuario_tipo")
    return tipo_usuario == "ti"


def usuario_pode_gerenciar_por_sigla(
    sigla_registro,
    sigla_usuario=None,
    tipo_usuario=None,
):
    sigla_usuario = sigla_usuario or session.get("usuario_sigla")
    tipo_usuario = tipo_usuario or session.get("usuario_tipo")

    if not sigla_usuario or not sigla_registro:
        return False

    return usuario_eh_ti(tipo_usuario) or sigla_usuario == sigla_registro


def usuario_pode_gerenciar_reserva(
    reserva,
    sigla_usuario=None,
    tipo_usuario=None,
):
    if not reserva:
        return False

    return usuario_pode_gerenciar_por_sigla(
        reserva["sigla"],
        sigla_usuario=sigla_usuario,
        tipo_usuario=tipo_usuario,
    )


def buscar_usuario_por_sigla(sigla):
    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, sigla, senha_hash, tipo
        FROM usuarios
        WHERE sigla = ?
        """,
        (sigla,),
    )
    linha = c.fetchone()
    conn.close()

    if not linha:
        return None

    return {
        "id": linha[0],
        "sigla": linha[1],
        "senha_hash": linha[2],
        "tipo": linha[3],
        "tipo_label": TIPOS_USUARIO.get(linha[3], linha[3]),
    }


def listar_usuarios():
    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        SELECT sigla, tipo
        FROM usuarios
        ORDER BY tipo, sigla
        """
    )
    usuarios = [
        {
            "sigla": linha[0],
            "tipo": linha[1],
            "tipo_label": TIPOS_USUARIO.get(linha[1], linha[1]),
        }
        for linha in c.fetchall()
    ]
    conn.close()
    return usuarios


def existe_usuario_ti():
    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        SELECT COUNT(*)
        FROM usuarios
        WHERE tipo = 'ti'
        """
    )
    total = c.fetchone()[0]
    conn.close()
    return total > 0


def criar_usuario(sigla, senha, tipo):
    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO usuarios (sigla, senha_hash, tipo)
        VALUES (?, ?, ?)
        """,
        (sigla, generate_password_hash(senha), tipo),
    )
    conn.commit()
    conn.close()


def adicionar_parametros_url(url, **params):
    partes = urlsplit(url)
    query = dict(parse_qsl(partes.query, keep_blank_values=True))

    for chave, valor in params.items():
        if valor is None:
            query.pop(chave, None)
            continue

        query[chave] = valor

    return urlunsplit(
        (
            partes.scheme,
            partes.netloc,
            partes.path,
            urlencode(query),
            partes.fragment,
        )
    )


def destino_seguro(proximo, endpoint_padrao, **valores_padrao):
    if proximo and proximo.startswith("/"):
        return proximo
    return url_for(endpoint_padrao, **valores_padrao)


def redirecionar_com_mensagem(proximo, endpoint_padrao, mensagem, tipo, **valores_padrao):
    destino = destino_seguro(proximo, endpoint_padrao, **valores_padrao)
    return redirect(adicionar_parametros_url(destino, mensagem=mensagem, tipo=tipo))


def destino_atual():
    query = request.query_string.decode().strip()
    if query:
        return f"{request.path}?{query}"
    return request.path


def login_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("usuario_sigla"):
            return redirect(
                url_for(
                    "login",
                    next=destino_atual(),
                    mensagem="Fa\u00e7a login para continuar.",
                    tipo="warning",
                )
            )
        return view(*args, **kwargs)

    return wrapper


def ti_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("usuario_sigla"):
            return redirect(
                url_for(
                    "login",
                    next=destino_atual(),
                    mensagem="Fa\u00e7a login da equipe de TI para continuar.",
                    tipo="warning",
                )
            )

        if session.get("usuario_tipo") != "ti":
            return redirect(
                url_for(
                    "home",
                    mensagem="Esta \u00e1rea interna est\u00e1 dispon\u00edvel apenas para a equipe de TI.",
                    tipo="warning",
                )
            )

        return view(*args, **kwargs)

    return wrapper


def serializar_reserva(linha):
    reserva = {
        "id": linha[0],
        "sigla": linha[1],
        "sala": linha[2],
        "data": linha[3],
        "horario": linha[4],
        "nivel": linha[5],
        "som": normalizar_som(linha[6]),
    }

    faixa = HORARIOS_POR_INICIO.get(reserva["nivel"], {}).get(reserva["horario"])
    reserva["nivel_label"] = NIVEL_LABELS.get(reserva["nivel"], reserva["nivel"])
    reserva["sala_label"] = SALAS.get(reserva["nivel"], {}).get(
        reserva["sala"],
        f"Sala {reserva['sala']}",
    )
    reserva["aula_label"] = faixa["label"] if faixa else reserva["horario"]
    reserva["horario_fim"] = faixa["fim"] if faixa else ""
    reserva["pode_gerenciar"] = False
    return reserva


def marcar_permissoes_reserva(
    reserva,
    sigla_usuario=None,
    tipo_usuario=None,
):
    if not reserva:
        return None

    reserva["pode_gerenciar"] = usuario_pode_gerenciar_reserva(
        reserva,
        sigla_usuario=sigla_usuario,
        tipo_usuario=tipo_usuario,
    )
    return reserva


def marcar_permissoes_reservas(
    reservas,
    sigla_usuario=None,
    tipo_usuario=None,
):
    return [
        marcar_permissoes_reserva(
            reserva,
            sigla_usuario=sigla_usuario,
            tipo_usuario=tipo_usuario,
        )
        for reserva in reservas
    ]


def serializar_requisicao_computador(linha):
    requisicao = {
        "id": linha[0],
        "sigla": linha[1],
        "recurso": linha[2],
        "quantidade": linha[3],
        "local": linha[4],
        "data": linha[5],
        "horario": linha[6],
        "nivel": linha[7],
    }

    faixa = HORARIOS_POR_INICIO.get(requisicao["nivel"], {}).get(requisicao["horario"])
    recurso = RECURSOS_COMPUTADORES.get(requisicao["recurso"], {})
    requisicao["nivel_label"] = NIVEL_LABELS.get(
        requisicao["nivel"],
        requisicao["nivel"],
    )
    requisicao["recurso_label"] = recurso.get("label", requisicao["recurso"])
    requisicao["recurso_total"] = recurso.get("total", 0)
    requisicao["max_por_reserva"] = recurso.get(
        "max_por_reserva",
        min(requisicao["recurso_total"], LIMITE_COMPUTADORES_POR_RESERVA),
    )
    requisicao["usa_sala"] = recurso.get("usa_sala", True)
    requisicao["usa_quantidade"] = recurso.get("usa_quantidade", True)
    requisicao["capacidade_label"] = recurso.get(
        "capacidade_label",
        f"{requisicao['recurso_total']} unidades",
    )
    requisicao["local_label"] = rotulo_local_computador(
        requisicao["nivel"],
        requisicao["recurso"],
        requisicao["local"],
    )
    requisicao["quantidade_label"] = (
        str(requisicao["quantidade"])
        if requisicao["usa_quantidade"]
        else "Sala completa"
    )
    requisicao["aula_label"] = faixa["label"] if faixa else requisicao["horario"]
    requisicao["horario_fim"] = faixa["fim"] if faixa else ""
    requisicao["pode_gerenciar"] = False
    return requisicao


def marcar_permissoes_requisicao_computador(
    requisicao,
    sigla_usuario=None,
    tipo_usuario=None,
):
    if not requisicao:
        return None

    requisicao["pode_gerenciar"] = usuario_pode_gerenciar_por_sigla(
        requisicao["sigla"],
        sigla_usuario=sigla_usuario,
        tipo_usuario=tipo_usuario,
    )
    return requisicao


def marcar_permissoes_requisicoes_computadores(
    requisicoes,
    sigla_usuario=None,
    tipo_usuario=None,
):
    return [
        marcar_permissoes_requisicao_computador(
            requisicao,
            sigla_usuario=sigla_usuario,
            tipo_usuario=tipo_usuario,
        )
        for requisicao in requisicoes
    ]


def rotulo_local_computador(nivel, recurso, local):
    configuracao = RECURSOS_COMPUTADORES.get(recurso, {})

    if local == configuracao.get("local_fixo"):
        return configuracao.get("local_label", local)

    return SALAS.get(nivel, {}).get(local, local or "Local n\u00e3o informado")


def validar_dados_requisicao_computador(
    nivel,
    recurso,
    local,
    data_requisicao,
    quantidade,
    horario=None,
):
    return validar_requisicao_computador(
        nivel,
        recurso,
        local,
        data_requisicao,
        quantidade,
        salas=SALAS,
        recursos_computadores=RECURSOS_COMPUTADORES,
        horarios_por_inicio=HORARIOS_POR_INICIO,
        limite_computadores_por_reserva=LIMITE_COMPUTADORES_POR_RESERVA,
        horario=horario,
    )


def buscar_disponibilidade_computadores_geral():
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


def buscar_requisicoes_computadores_por_data(data_filtro):
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
        serializar_requisicao_computador(linha)
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


def buscar_requisicao_computador_por_id(requisicao_id):
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

    return serializar_requisicao_computador(linha)


def obter_clausula_ignorar_id(registro_id_ignorado):
    if registro_id_ignorado is None:
        return "", ()
    return " AND id != ?", (registro_id_ignorado,)


def buscar_disponibilidade_geral():
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


def buscar_reservas_por_data(data_filtro):
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


def buscar_reserva_por_id(reserva_id):
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


def validar_dados_reserva(nivel, sala, data_reserva, horario=None):
    return validar_reserva(
        nivel,
        sala,
        data_reserva,
        salas=SALAS,
        horarios_por_inicio=HORARIOS_POR_INICIO,
        horario=horario,
    )


def obter_clausula_ignorar_reserva(reserva_id_ignorada):
    return obter_clausula_ignorar_id(reserva_id_ignorada)


def verificar_conflitos_reserva(
    cursor,
    data_reserva,
    horario,
    nivel,
    sala,
    reserva_id_ignorada=None,
):
    clausula, parametros_extra = obter_clausula_ignorar_reserva(reserva_id_ignorada)

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
    limite_atingido = cursor.fetchone()[0] >= TOTAL_PROJETORES

    return conflito_sala, limite_atingido


def verificar_conflitos_requisicao_computador(
    cursor,
    data_requisicao,
    horario,
    nivel,
    recurso,
    local,
    quantidade,
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
    total_recurso = RECURSOS_COMPUTADORES[recurso]["total"]
    limite_excedido = quantidade_ja_solicitada + quantidade > total_recurso

    return conflito_local, limite_excedido, max(0, total_recurso - quantidade_ja_solicitada)


def registrar_reservas_projetor(
    cursor,
    sigla,
    sala,
    data_reserva,
    nivel,
    aulas,
    som,
):
    resultado = {
        "inseridas": 0,
        "bloqueios_sala": 0,
        "bloqueios_limite": 0,
        "sala_label": SALAS[nivel].get(sala, f"Sala {sala}"),
    }

    for aula in aulas:
        if aula not in HORARIOS_POR_INICIO[nivel]:
            resultado["bloqueios_sala"] += 1
            continue

        conflito_sala, limite_atingido = verificar_conflitos_reserva(
            cursor,
            data_reserva,
            aula,
            nivel,
            sala,
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


def registrar_requisicoes_computador(
    cursor,
    sigla,
    recurso,
    quantidade_int,
    local_normalizado,
    data_requisicao,
    nivel,
    aulas,
):
    resultado = {
        "inseridas": 0,
        "bloqueios_local": 0,
        "bloqueios_limite": 0,
        "recurso_label": RECURSOS_COMPUTADORES[recurso]["label"],
        "local_label": rotulo_local_computador(nivel, recurso, local_normalizado),
        "quantidade": quantidade_int,
        "usa_quantidade": RECURSOS_COMPUTADORES[recurso].get("usa_quantidade", True),
    }

    for aula in aulas:
        if aula not in HORARIOS_POR_INICIO[nivel]:
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


def buscar_reservas_relatorio(data_inicial, data_final, nivel="", sigla=""):
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
        serializar_requisicao_computador(linha)
        for linha in c.fetchall()
    ]
    conn.close()
    return requisicoes


def montar_relatorio_ti(reservas):
    resumo = {
        "total_reservas": len(reservas),
        "total_professores": len({reserva["sigla"] for reserva in reservas}),
        "total_salas": len(
            {(reserva["nivel"], reserva["sala"]) for reserva in reservas}
        ),
        "total_com_som": sum(1 for reserva in reservas if reserva["som"] == "Sim"),
    }

    por_dia = {}
    por_sigla = {}
    por_nivel = {}

    for reserva in reservas:
        dados_dia = por_dia.setdefault(
            reserva["data"],
            {
                "data": reserva["data"],
                "total_reservas": 0,
                "professores": set(),
                "salas": set(),
            },
        )
        dados_dia["total_reservas"] += 1
        dados_dia["professores"].add(reserva["sigla"])
        dados_dia["salas"].add((reserva["nivel"], reserva["sala"]))

        dados_sigla = por_sigla.setdefault(
            reserva["sigla"],
            {
                "sigla": reserva["sigla"],
                "total_reservas": 0,
                "dias": set(),
                "niveis": set(),
            },
        )
        dados_sigla["total_reservas"] += 1
        dados_sigla["dias"].add(reserva["data"])
        dados_sigla["niveis"].add(reserva["nivel_label"])

        dados_nivel = por_nivel.setdefault(
            reserva["nivel"],
            {
                "nivel": reserva["nivel"],
                "nivel_label": reserva["nivel_label"],
                "total_reservas": 0,
                "total_com_som": 0,
                "professores": set(),
                "salas": set(),
            },
        )
        dados_nivel["total_reservas"] += 1
        dados_nivel["total_com_som"] += int(reserva["som"] == "Sim")
        dados_nivel["professores"].add(reserva["sigla"])
        dados_nivel["salas"].add(reserva["sala_label"])

    dias = sorted(
        (
            {
                "data": item["data"],
                "total_reservas": item["total_reservas"],
                "total_professores": len(item["professores"]),
                "total_salas": len(item["salas"]),
            }
            for item in por_dia.values()
        ),
        key=lambda item: item["data"],
    )

    siglas = sorted(
        (
            {
                "sigla": item["sigla"],
                "total_reservas": item["total_reservas"],
                "total_dias": len(item["dias"]),
                "niveis": ", ".join(sorted(item["niveis"])),
            }
            for item in por_sigla.values()
        ),
        key=lambda item: (-item["total_reservas"], item["sigla"]),
    )

    niveis = sorted(
        (
            {
                "nivel": item["nivel"],
                "nivel_label": item["nivel_label"],
                "total_reservas": item["total_reservas"],
                "total_com_som": item["total_com_som"],
                "total_professores": len(item["professores"]),
                "total_salas": len(item["salas"]),
            }
            for item in por_nivel.values()
        ),
        key=lambda item: item["nivel_label"],
    )

    return {
        "resumo": resumo,
        "por_dia": dias,
        "por_sigla": siglas,
        "por_nivel": niveis,
    }


def montar_relatorio_computadores_ti(requisicoes):
    resumo = {
        "total_requisicoes": len(requisicoes),
        "total_itens": sum(requisicao["quantidade"] for requisicao in requisicoes),
        "total_professores": len({requisicao["sigla"] for requisicao in requisicoes}),
        "total_locais": len(
            {
                (
                    requisicao["nivel"],
                    requisicao["local"],
                    requisicao["recurso"],
                )
                for requisicao in requisicoes
            }
        ),
    }

    por_dia = {}
    por_sigla = {}
    por_recurso = {}

    for requisicao in requisicoes:
        dados_dia = por_dia.setdefault(
            requisicao["data"],
            {
                "data": requisicao["data"],
                "total_requisicoes": 0,
                "total_itens": 0,
                "professores": set(),
            },
        )
        dados_dia["total_requisicoes"] += 1
        dados_dia["total_itens"] += requisicao["quantidade"]
        dados_dia["professores"].add(requisicao["sigla"])

        dados_sigla = por_sigla.setdefault(
            requisicao["sigla"],
            {
                "sigla": requisicao["sigla"],
                "total_requisicoes": 0,
                "total_itens": 0,
                "dias": set(),
                "recursos": set(),
            },
        )
        dados_sigla["total_requisicoes"] += 1
        dados_sigla["total_itens"] += requisicao["quantidade"]
        dados_sigla["dias"].add(requisicao["data"])
        dados_sigla["recursos"].add(requisicao["recurso_label"])

        dados_recurso = por_recurso.setdefault(
            requisicao["recurso"],
            {
                "recurso": requisicao["recurso"],
                "recurso_label": requisicao["recurso_label"],
                "capacidade_total": requisicao["recurso_total"],
                "capacidade_label": requisicao["capacidade_label"],
                "total_requisicoes": 0,
                "total_itens": 0,
                "professores": set(),
                "locais": set(),
            },
        )
        dados_recurso["total_requisicoes"] += 1
        dados_recurso["total_itens"] += requisicao["quantidade"]
        dados_recurso["professores"].add(requisicao["sigla"])
        dados_recurso["locais"].add(requisicao["local_label"])

    dias = sorted(
        (
            {
                "data": item["data"],
                "total_requisicoes": item["total_requisicoes"],
                "total_itens": item["total_itens"],
                "total_professores": len(item["professores"]),
            }
            for item in por_dia.values()
        ),
        key=lambda item: item["data"],
    )

    siglas = sorted(
        (
            {
                "sigla": item["sigla"],
                "total_requisicoes": item["total_requisicoes"],
                "total_itens": item["total_itens"],
                "total_dias": len(item["dias"]),
                "recursos": ", ".join(sorted(item["recursos"])),
            }
            for item in por_sigla.values()
        ),
        key=lambda item: (-item["total_itens"], item["sigla"]),
    )

    recursos = sorted(
        (
            {
                "recurso": item["recurso"],
                "recurso_label": item["recurso_label"],
                "capacidade_total": item["capacidade_total"],
                "capacidade_label": item["capacidade_label"],
                "total_requisicoes": item["total_requisicoes"],
                "total_itens": item["total_itens"],
                "total_professores": len(item["professores"]),
                "total_locais": len(item["locais"]),
            }
            for item in por_recurso.values()
        ),
        key=lambda item: item["recurso_label"],
    )

    return {
        "resumo": resumo,
        "por_dia": dias,
        "por_sigla": siglas,
        "por_recurso": recursos,
    }


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


@app.context_processor
def injetar_usuario():
    tipo = session.get("usuario_tipo")
    return {
        "usuario_sigla": session.get("usuario_sigla"),
        "usuario_tipo": tipo,
        "usuario_tipo_label": TIPOS_USUARIO.get(tipo),
        "usuario_eh_ti": tipo == "ti",
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        sigla = normalizar_sigla_professor(request.form.get("sigla", ""))
        senha = request.form.get("senha", "")
        proximo = request.form.get("next", "")
        usuario = buscar_usuario_por_sigla(sigla)

        if not usuario or not check_password_hash(usuario["senha_hash"], senha):
            return render_template(
                "login.html",
                mensagem="Sigla ou senha inv\u00e1lida.",
                tipo_mensagem="warning",
                proximo=proximo,
                primeiro_acesso_disponivel=not existe_usuario_ti(),
            )

        session["usuario_sigla"] = usuario["sigla"]
        session["usuario_tipo"] = usuario["tipo"]

        if proximo and proximo.startswith("/"):
            return redirect(proximo)

        if usuario["tipo"] == "ti":
            return redirect(url_for("painel_ti"))

        return redirect(url_for("home"))

    if session.get("usuario_sigla"):
        if session.get("usuario_tipo") == "ti":
            return redirect(url_for("painel_ti"))
        return redirect(url_for("home"))

    return render_template(
        "login.html",
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "warning"),
        proximo=request.args.get("next", ""),
        primeiro_acesso_disponivel=not existe_usuario_ti(),
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        url_for(
            "login",
            mensagem="Sess\u00e3o encerrada com sucesso.",
            tipo="success",
        )
    )


@app.route("/primeiro-acesso", methods=["GET", "POST"])
def primeiro_acesso():
    if existe_usuario_ti():
        return redirect(
            url_for(
                "login",
                mensagem="O primeiro acesso j\u00e1 foi configurado. Fa\u00e7a login.",
                tipo="warning",
            )
        )

    if request.method == "POST":
        sigla = normalizar_sigla_professor(request.form.get("sigla", ""))
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if len(sigla) != 3:
            return render_template(
                "primeiro_acesso.html",
                mensagem="Informe uma sigla com exatamente 3 letras.",
                tipo_mensagem="warning",
            )

        if buscar_usuario_por_sigla(sigla):
            return render_template(
                "primeiro_acesso.html",
                mensagem="Essa sigla j\u00e1 possui um acesso cadastrado.",
                tipo_mensagem="warning",
            )

        if len(senha) < 4:
            return render_template(
                "primeiro_acesso.html",
                mensagem="A senha precisa ter pelo menos 4 caracteres.",
                tipo_mensagem="warning",
            )

        if senha != confirmar_senha:
            return render_template(
                "primeiro_acesso.html",
                mensagem="A confirma\u00e7\u00e3o da senha n\u00e3o confere.",
                tipo_mensagem="warning",
            )

        criar_usuario(sigla, senha, "ti")
        return redirect(
            url_for(
                "login",
                mensagem="Primeiro acesso da TI criado. Agora fa\u00e7a login.",
                tipo="success",
            )
        )

    return render_template(
        "primeiro_acesso.html",
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "warning"),
    )


@app.route("/usuarios", methods=["GET", "POST"])
@ti_obrigatorio
def gerenciar_usuarios():
    mensagem = request.args.get("mensagem")
    tipo_mensagem = request.args.get("tipo", "success")

    if request.method == "POST":
        sigla = normalizar_sigla_professor(request.form.get("sigla", ""))
        senha = request.form.get("senha", "")
        tipo = request.form.get("tipo", "professor")

        if len(sigla) != 3:
            mensagem = "Informe uma sigla com exatamente 3 letras."
            tipo_mensagem = "warning"
        elif len(senha) < 4:
            mensagem = "A senha precisa ter pelo menos 4 caracteres."
            tipo_mensagem = "warning"
        elif tipo not in TIPOS_USUARIO:
            mensagem = "Selecione um tipo de acesso v\u00e1lido."
            tipo_mensagem = "warning"
        elif buscar_usuario_por_sigla(sigla):
            mensagem = "Essa sigla j\u00e1 possui um acesso cadastrado."
            tipo_mensagem = "warning"
        else:
            criar_usuario(sigla, senha, tipo)
            return redirect(
                url_for(
                    "gerenciar_usuarios",
                    mensagem=f"Acesso {TIPOS_USUARIO[tipo].lower()} criado para {sigla}.",
                    tipo="success",
                )
            )

    return render_template(
        "usuarios.html",
        usuarios=listar_usuarios(),
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem,
        tipos_usuario=TIPOS_USUARIO,
    )


@app.route("/")
@login_obrigatorio
def home():
    disponibilidade, salas_ocupadas = buscar_disponibilidade_geral()
    dados_computadores, locais_computadores_ocupados = (
        buscar_disponibilidade_computadores_geral()
    )
    return render_template(
        "home.html",
        dados=disponibilidade,
        salas_ocupadas=salas_ocupadas,
        dados_computadores=dados_computadores,
        locais_computadores_ocupados=locais_computadores_ocupados,
        recursos_computadores=RECURSOS_COMPUTADORES,
        salas=SALAS,
        horarios=HORARIOS,
        data_hoje=date.today().isoformat(),
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "warning"),
    )


@app.route("/computadores")
@login_obrigatorio
def home_computadores():
    disponibilidade, locais_ocupados = buscar_disponibilidade_computadores_geral()
    return render_template(
        "computadores.html",
        dados=disponibilidade,
        locais_ocupados=locais_ocupados,
        recursos_computadores=RECURSOS_COMPUTADORES,
        salas=SALAS,
        horarios=HORARIOS,
        data_hoje=date.today().isoformat(),
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "warning"),
    )


@app.route("/computadores/solicitar", methods=["POST"])
@login_obrigatorio
def solicitar_computadores():
    sigla = session.get("usuario_sigla")
    recurso = request.form.get("recurso", "")
    nivel = request.form.get("nivel", "")
    local = request.form.get("local", "")
    data_requisicao = request.form.get("data", "")
    quantidade = request.form.get("quantidade", "")
    aulas = request.form.getlist("aulas")

    erro_validacao, quantidade_int, local_normalizado = validar_dados_requisicao_computador(
        nivel,
        recurso,
        local,
        data_requisicao,
        quantidade,
    )
    if erro_validacao:
        return redirect(
            url_for(
                "home_computadores",
                mensagem=erro_validacao,
                tipo="warning",
            )
        )

    if not aulas:
        return redirect(
            url_for(
                "home_computadores",
                mensagem="Selecione pelo menos uma aula para solicitar os computadores.",
                tipo="warning",
            )
        )

    conn = conectar()
    c = conn.cursor()
    resultado = registrar_requisicoes_computador(
        c,
        sigla,
        recurso,
        quantidade_int,
        local_normalizado,
        data_requisicao,
        nivel,
        aulas,
    )
    conn.commit()
    conn.close()

    mensagens, tipo = montar_mensagens_requisicao_computador(resultado)

    if not mensagens:
        tipo = "warning"
        mensagens.append("Nenhum hor\u00e1rio foi solicitado.")

    return redirect(
        url_for(
            "ver_requisicoes_computadores",
            data=data_requisicao,
            mensagem=" ".join(mensagens),
            tipo=tipo,
        )
    )


@app.route("/computadores/consultar")
@login_obrigatorio
def ver_requisicoes_computadores():
    data_filtro = request.args.get("data") or date.today().isoformat()
    requisicoes, disponibilidade = buscar_requisicoes_computadores_por_data(data_filtro)
    requisicoes = marcar_permissoes_requisicoes_computadores(requisicoes)
    painel = montar_painel_disponibilidade_computadores(disponibilidade)

    return render_template(
        "computadores_consulta.html",
        requisicoes=requisicoes,
        painel=painel,
        data_selecionada=data_filtro,
        data_hoje=date.today().isoformat(),
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "success"),
    )


@app.route("/reservar", methods=["POST"])
@login_obrigatorio
def reservar():
    sigla = session.get("usuario_sigla")
    data_reserva = request.form.get("data", "")
    nivel = request.form.get("nivel", "")
    aulas = request.form.getlist("aulas")
    incluir_projetor = request.form.get("incluir_projetor") == "on"
    incluir_computador = request.form.get("incluir_computador") == "on"

    if not incluir_projetor and not incluir_computador:
        return redirect(
            url_for(
                "home",
                mensagem="Selecione pelo menos um recurso: projetor, computador ou ambos.",
                tipo="warning",
            )
        )

    if not aulas:
        return redirect(
            url_for(
                "home",
                mensagem="Selecione pelo menos uma aula para concluir a solicita\u00e7\u00e3o.",
                tipo="warning",
            )
        )

    mensagens = []
    tipo = "success"

    conn = conectar()
    c = conn.cursor()

    if incluir_projetor:
        sala = request.form.get("sala", "")
        erro_validacao = validar_dados_reserva(nivel, sala, data_reserva)
        if erro_validacao:
            conn.close()
            return redirect(
                url_for(
                    "home",
                    mensagem=erro_validacao,
                    tipo="warning",
                )
            )

        som = request.form.get("som", "N\u00e3o") if nivel == "Fundamental" else "N\u00e3o"
        resultado_projetor = registrar_reservas_projetor(
            c,
            sigla,
            sala,
            data_reserva,
            nivel,
            aulas,
            som,
        )
        mensagens_projetor, tipo_projetor = montar_mensagens_reserva_projetor(
            resultado_projetor
        )
        mensagens.extend(mensagens_projetor)
        if tipo_projetor == "warning":
            tipo = "warning"

    if incluir_computador:
        recurso = request.form.get("recurso_computador", "")
        local_computador = request.form.get("local_computador", "")
        quantidade_computador = request.form.get("quantidade_computador", "")
        erro_validacao, quantidade_int, local_normalizado = (
            validar_dados_requisicao_computador(
                nivel,
                recurso,
                local_computador,
                data_reserva,
                quantidade_computador,
            )
        )
        if erro_validacao:
            conn.close()
            return redirect(
                url_for(
                    "home",
                    mensagem=erro_validacao,
                    tipo="warning",
                )
            )

        resultado_computador = registrar_requisicoes_computador(
            c,
            sigla,
            recurso,
            quantidade_int,
            local_normalizado,
            data_reserva,
            nivel,
            aulas,
        )
        mensagens_computador, tipo_computador = montar_mensagens_requisicao_computador(
            resultado_computador
        )
        mensagens.extend(mensagens_computador)
        if tipo_computador == "warning":
            tipo = "warning"

    conn.commit()
    conn.close()

    if not mensagens:
        tipo = "warning"
        mensagens.append("Nenhum hor\u00e1rio foi reservado.")

    return redirect(
        url_for(
            "ver_reservas",
            data=data_reserva,
            mensagem=" ".join(mensagens),
            tipo=tipo,
        )
    )


@app.route("/reservas")
@login_obrigatorio
def ver_reservas():
    data_filtro = request.args.get("data") or date.today().isoformat()
    reservas, disponibilidade = buscar_reservas_por_data(data_filtro)
    reservas = marcar_permissoes_reservas(reservas)
    painel = montar_painel_disponibilidade(disponibilidade)

    return render_template(
        "reservas.html",
        reservas=reservas,
        painel=painel,
        data_selecionada=data_filtro,
        data_hoje=date.today().isoformat(),
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "success"),
    )


@app.route("/reservas/<int:reserva_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_reserva(reserva_id):
    proximo = request.values.get("next", "")
    reserva = buscar_reserva_por_id(reserva_id)

    if not reserva:
        return redirecionar_com_mensagem(
            proximo,
            "ver_reservas",
            "Reserva n\u00e3o encontrada.",
            "warning",
            data=date.today().isoformat(),
        )

    if not usuario_pode_gerenciar_reserva(reserva):
        return redirecionar_com_mensagem(
            proximo,
            "ver_reservas",
            "Voc\u00ea n\u00e3o tem permiss\u00e3o para editar esta reserva.",
            "warning",
            data=reserva["data"],
        )

    reserva = marcar_permissoes_reserva(reserva)
    dados_formulario = {
        "sigla": reserva["sigla"],
        "nivel": reserva["nivel"],
        "sala": reserva["sala"],
        "data": reserva["data"],
        "horario": reserva["horario"],
        "som": reserva["som"],
    }
    mensagem = request.args.get("mensagem")
    tipo_mensagem = request.args.get("tipo", "warning")

    if request.method == "POST":
        dados_formulario = {
            "sigla": reserva["sigla"],
            "nivel": request.form.get("nivel", ""),
            "sala": request.form.get("sala", ""),
            "data": request.form.get("data", ""),
            "horario": request.form.get("horario", ""),
            "som": request.form.get("som", "N\u00e3o"),
        }

        if dados_formulario["nivel"] != "Fundamental":
            dados_formulario["som"] = "N\u00e3o"

        erro_validacao = validar_dados_reserva(
            dados_formulario["nivel"],
            dados_formulario["sala"],
            dados_formulario["data"],
            dados_formulario["horario"],
        )

        if erro_validacao:
            mensagem = erro_validacao
            tipo_mensagem = "warning"
        else:
            conn = conectar()
            c = conn.cursor()
            conflito_sala, limite_atingido = verificar_conflitos_reserva(
                c,
                dados_formulario["data"],
                dados_formulario["horario"],
                dados_formulario["nivel"],
                dados_formulario["sala"],
                reserva_id_ignorada=reserva_id,
            )

            if conflito_sala:
                mensagem = (
                    "J\u00e1 existe um projetor reservado para essa sala nesse hor\u00e1rio."
                )
                tipo_mensagem = "warning"
            elif limite_atingido:
                mensagem = (
                    "N\u00e3o foi poss\u00edvel atualizar: os 4 projetores desse n\u00edvel "
                    "j\u00e1 est\u00e3o em uso no hor\u00e1rio escolhido."
                )
                tipo_mensagem = "warning"
            else:
                c.execute(
                    """
                    UPDATE reservas
                    SET sala = ?, data = ?, horario = ?, nivel = ?, som = ?
                    WHERE id = ?
                    """,
                    (
                        dados_formulario["sala"],
                        dados_formulario["data"],
                        dados_formulario["horario"],
                        dados_formulario["nivel"],
                        normalizar_som(dados_formulario["som"]),
                        reserva_id,
                    ),
                )
                conn.commit()
                conn.close()

                return redirecionar_com_mensagem(
                    proximo,
                    "ver_reservas",
                    "Reserva atualizada com sucesso.",
                    "success",
                    data=dados_formulario["data"],
                )

            conn.close()

    return render_template(
        "editar_reserva.html",
        reserva=reserva,
        reserva_form=dados_formulario,
        niveis=NIVEL_LABELS,
        salas=SALAS,
        horarios=HORARIOS,
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem,
        proximo=destino_seguro(proximo, "ver_reservas", data=reserva["data"]),
    )


@app.route("/reservas/<int:reserva_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_reserva(reserva_id):
    proximo = request.form.get("next", "")
    reserva = buscar_reserva_por_id(reserva_id)

    if not reserva:
        return redirecionar_com_mensagem(
            proximo,
            "ver_reservas",
            "Reserva n\u00e3o encontrada.",
            "warning",
            data=date.today().isoformat(),
        )

    if not usuario_pode_gerenciar_reserva(reserva):
        return redirecionar_com_mensagem(
            proximo,
            "ver_reservas",
            "Voc\u00ea n\u00e3o tem permiss\u00e3o para excluir esta reserva.",
            "warning",
            data=reserva["data"],
        )

    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        DELETE FROM reservas
        WHERE id = ?
        """,
        (reserva_id,),
    )
    conn.commit()
    conn.close()

    return redirecionar_com_mensagem(
        proximo,
        "ver_reservas",
        (
            f"Reserva de {reserva['sigla']} em {reserva['sala_label']} "
            f"({reserva['aula_label']}) exclu\u00edda com sucesso."
        ),
        "success",
        data=reserva["data"],
    )


@app.route("/painel-ti")
@ti_obrigatorio
def painel_ti():
    data_filtro = request.args.get("data") or date.today().isoformat()
    reservas, disponibilidade = buscar_reservas_por_data(data_filtro)
    reservas = marcar_permissoes_reservas(reservas)
    painel = montar_painel_disponibilidade(disponibilidade)
    planejamento = gerar_planejamento_ti(reservas)
    tarefas_do_dia = montar_tarefas_do_dia(planejamento)

    return render_template(
        "painel_ti.html",
        reservas=reservas,
        painel=painel,
        planejamento=planejamento,
        tarefas_do_dia=tarefas_do_dia,
        data_selecionada=data_filtro,
        data_hoje=date.today().isoformat(),
        mensagem=request.args.get("mensagem"),
        tipo_mensagem=request.args.get("tipo", "success"),
    )


@app.route("/relatorio-ti")
@ti_obrigatorio
def relatorio_ti():
    data_hoje = date.today().isoformat()
    data_inicial = request.args.get("data_inicial") or data_hoje
    data_final = request.args.get("data_final") or data_inicial
    sigla = normalizar_sigla_professor(request.args.get("sigla", ""))
    nivel = request.args.get("nivel", "")
    mensagem = request.args.get("mensagem")
    tipo_mensagem = request.args.get("tipo", "success")

    try:
        date.fromisoformat(data_inicial)
        date.fromisoformat(data_final)
    except ValueError:
        data_inicial = data_hoje
        data_final = data_hoje
        mensagem = "Per\u00edodo inv\u00e1lido. O relat\u00f3rio foi ajustado para a data de hoje."
        tipo_mensagem = "warning"

    if data_inicial > data_final:
        data_inicial, data_final = data_final, data_inicial
        mensagem = (
            "A data inicial era maior que a final. O per\u00edodo foi ajustado automaticamente."
        )
        tipo_mensagem = "warning"

    if nivel and nivel not in SALAS:
        nivel = ""
        mensagem = "Filtro de n\u00edvel inv\u00e1lido. Exibindo todos os n\u00edveis."
        tipo_mensagem = "warning"

    reservas = buscar_reservas_relatorio(data_inicial, data_final, nivel=nivel, sigla=sigla)
    reservas = marcar_permissoes_reservas(reservas)
    relatorio = montar_relatorio_ti(reservas)

    return render_template(
        "relatorio_ti.html",
        reservas=reservas,
        relatorio=relatorio,
        data_inicial=data_inicial,
        data_final=data_final,
        sigla=sigla,
        nivel=nivel,
        niveis=NIVEL_LABELS,
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem,
    )


@app.route("/computadores/<int:requisicao_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_requisicao_computador(requisicao_id):
    proximo = request.values.get("next", "")
    requisicao = buscar_requisicao_computador_por_id(requisicao_id)

    if not requisicao:
        return redirecionar_com_mensagem(
            proximo,
            "ver_requisicoes_computadores",
            "Requisi\u00e7\u00e3o de computadores n\u00e3o encontrada.",
            "warning",
            data=date.today().isoformat(),
        )

    if not usuario_pode_gerenciar_por_sigla(requisicao["sigla"]):
        return redirecionar_com_mensagem(
            proximo,
            "ver_requisicoes_computadores",
            "Voc\u00ea n\u00e3o tem permiss\u00e3o para editar esta requisi\u00e7\u00e3o.",
            "warning",
            data=requisicao["data"],
        )

    requisicao = marcar_permissoes_requisicao_computador(requisicao)
    dados_formulario = {
        "sigla": requisicao["sigla"],
        "recurso": requisicao["recurso"],
        "quantidade": requisicao["quantidade"],
        "local": requisicao["local"],
        "data": requisicao["data"],
        "horario": requisicao["horario"],
        "nivel": requisicao["nivel"],
    }
    mensagem = request.args.get("mensagem")
    tipo_mensagem = request.args.get("tipo", "warning")

    if request.method == "POST":
        dados_formulario = {
            "sigla": requisicao["sigla"],
            "recurso": request.form.get("recurso", ""),
            "quantidade": request.form.get("quantidade", ""),
            "local": request.form.get("local", ""),
            "data": request.form.get("data", ""),
            "horario": request.form.get("horario", ""),
            "nivel": request.form.get("nivel", ""),
        }

        erro_validacao, quantidade_int, local_normalizado = validar_dados_requisicao_computador(
            dados_formulario["nivel"],
            dados_formulario["recurso"],
            dados_formulario["local"],
            dados_formulario["data"],
            dados_formulario["quantidade"],
            dados_formulario["horario"],
        )

        if erro_validacao:
            mensagem = erro_validacao
            tipo_mensagem = "warning"
        else:
            conn = conectar()
            c = conn.cursor()
            conflito_local, limite_excedido, disponibilidade_restante = (
                verificar_conflitos_requisicao_computador(
                    c,
                    dados_formulario["data"],
                    dados_formulario["horario"],
                    dados_formulario["nivel"],
                    dados_formulario["recurso"],
                    local_normalizado,
                    quantidade_int,
                    requisicao_id_ignorada=requisicao_id,
                )
            )

            if conflito_local:
                mensagem = (
                    "J\u00e1 existe uma requisi\u00e7\u00e3o desse recurso para esse local "
                    "no hor\u00e1rio escolhido."
                )
                tipo_mensagem = "warning"
            elif limite_excedido:
                mensagem = (
                    "N\u00e3o foi poss\u00edvel atualizar: a quantidade solicitada ultrapassa "
                    f"a disponibilidade restante de {disponibilidade_restante} unidade(s)."
                )
                tipo_mensagem = "warning"
            else:
                c.execute(
                    """
                    UPDATE requisicoes_computadores
                    SET recurso = ?, quantidade = ?, local = ?, data = ?, horario = ?, nivel = ?
                    WHERE id = ?
                    """,
                    (
                        dados_formulario["recurso"],
                        quantidade_int,
                        local_normalizado,
                        dados_formulario["data"],
                        dados_formulario["horario"],
                        dados_formulario["nivel"],
                        requisicao_id,
                    ),
                )
                conn.commit()
                conn.close()

                return redirecionar_com_mensagem(
                    proximo,
                    "ver_requisicoes_computadores",
                    "Requisi\u00e7\u00e3o de computadores atualizada com sucesso.",
                    "success",
                    data=dados_formulario["data"],
                )

            conn.close()

            dados_formulario["quantidade"] = quantidade_int
            dados_formulario["local"] = local_normalizado

    return render_template(
        "editar_computador.html",
        requisicao=requisicao,
        requisicao_form=dados_formulario,
        niveis=NIVEL_LABELS,
        salas=SALAS,
        horarios=HORARIOS,
        recursos_computadores=RECURSOS_COMPUTADORES,
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem,
        proximo=destino_seguro(
            proximo,
            "ver_requisicoes_computadores",
            data=requisicao["data"],
        ),
    )


@app.route("/computadores/<int:requisicao_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_requisicao_computador(requisicao_id):
    proximo = request.form.get("next", "")
    requisicao = buscar_requisicao_computador_por_id(requisicao_id)

    if not requisicao:
        return redirecionar_com_mensagem(
            proximo,
            "ver_requisicoes_computadores",
            "Requisi\u00e7\u00e3o de computadores n\u00e3o encontrada.",
            "warning",
            data=date.today().isoformat(),
        )

    if not usuario_pode_gerenciar_por_sigla(requisicao["sigla"]):
        return redirecionar_com_mensagem(
            proximo,
            "ver_requisicoes_computadores",
            "Voc\u00ea n\u00e3o tem permiss\u00e3o para excluir esta requisi\u00e7\u00e3o.",
            "warning",
            data=requisicao["data"],
        )

    conn = conectar()
    c = conn.cursor()
    c.execute(
        """
        DELETE FROM requisicoes_computadores
        WHERE id = ?
        """,
        (requisicao_id,),
    )
    conn.commit()
    conn.close()

    return redirecionar_com_mensagem(
        proximo,
        "ver_requisicoes_computadores",
        (
            (
                f"Requisi\u00e7\u00e3o de {requisicao['quantidade']} unidade(s) de "
                f"{requisicao['recurso_label']} para {requisicao['local_label']} exclu\u00edda com sucesso."
            )
            if requisicao["usa_quantidade"]
            else f"Reserva de {requisicao['recurso_label']} exclu\u00edda com sucesso."
        ),
        "success",
        data=requisicao["data"],
    )


@app.route("/computadores/relatorio-ti")
@ti_obrigatorio
def relatorio_computadores_ti():
    data_hoje = date.today().isoformat()
    data_inicial = request.args.get("data_inicial") or data_hoje
    data_final = request.args.get("data_final") or data_inicial
    sigla = normalizar_sigla_professor(request.args.get("sigla", ""))
    nivel = request.args.get("nivel", "")
    recurso = request.args.get("recurso", "")
    mensagem = request.args.get("mensagem")
    tipo_mensagem = request.args.get("tipo", "success")

    try:
        date.fromisoformat(data_inicial)
        date.fromisoformat(data_final)
    except ValueError:
        data_inicial = data_hoje
        data_final = data_hoje
        mensagem = "Per\u00edodo inv\u00e1lido. O relat\u00f3rio foi ajustado para a data de hoje."
        tipo_mensagem = "warning"

    if data_inicial > data_final:
        data_inicial, data_final = data_final, data_inicial
        mensagem = (
            "A data inicial era maior que a final. O per\u00edodo foi ajustado automaticamente."
        )
        tipo_mensagem = "warning"

    if nivel and nivel not in SALAS:
        nivel = ""
        mensagem = "Filtro de n\u00edvel inv\u00e1lido. Exibindo todos os n\u00edveis."
        tipo_mensagem = "warning"

    if recurso and recurso not in RECURSOS_COMPUTADORES:
        recurso = ""
        mensagem = "Filtro de recurso inv\u00e1lido. Exibindo todos os recursos."
        tipo_mensagem = "warning"

    requisicoes = buscar_requisicoes_computadores_relatorio(
        data_inicial,
        data_final,
        nivel=nivel,
        sigla=sigla,
        recurso=recurso,
    )
    requisicoes = marcar_permissoes_requisicoes_computadores(requisicoes)
    relatorio = montar_relatorio_computadores_ti(requisicoes)

    return render_template(
        "relatorio_computadores_ti.html",
        requisicoes=requisicoes,
        relatorio=relatorio,
        data_inicial=data_inicial,
        data_final=data_final,
        sigla=sigla,
        nivel=nivel,
        recurso=recurso,
        niveis=NIVEL_LABELS,
        recursos_computadores=RECURSOS_COMPUTADORES,
        mensagem=mensagem,
        tipo_mensagem=tipo_mensagem,
    )


if __name__ == "__main__":
    app.run(debug=app.config["FLASK_DEBUG"], port=app.config["PORT"])
