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
