from validators import normalizar_sigla_professor
from validators import normalizar_som
from validators import validar_requisicao_computador
from validators import validar_reserva


SALAS = {
    "Fundamental": {
        "11": "Sala 11",
    }
}

HORARIOS_POR_INICIO = {
    "Fundamental": {
        "07:25": {"label": "1a aula"},
    }
}

RECURSOS_COMPUTADORES = {
    "notebook": {
        "label": "Notebook",
        "total": 15,
        "usa_sala": True,
        "usa_quantidade": True,
        "max_por_reserva": 15,
    },
    "laboratorio": {
        "label": "Laboratorio",
        "total": 1,
        "usa_sala": False,
        "usa_quantidade": False,
        "local_fixo": "LAB15",
    },
}


def test_normaliza_sigla_do_professor():
    assert normalizar_sigla_professor(" ab-1c ") == "ABC"


def test_normaliza_resposta_de_som():
    assert normalizar_som("Nao") == "N\u00e3o"
    assert normalizar_som("sim") == "Sim"
    assert normalizar_som("") == "N\u00e3o"


def test_valida_reserva_com_dados_validos():
    erro = validar_reserva(
        "Fundamental",
        "11",
        "2026-05-04",
        salas=SALAS,
        horarios_por_inicio=HORARIOS_POR_INICIO,
        horario="07:25",
    )

    assert erro is None


def test_bloqueia_reserva_com_sala_invalida():
    erro = validar_reserva(
        "Fundamental",
        "99",
        "2026-05-04",
        salas=SALAS,
        horarios_por_inicio=HORARIOS_POR_INICIO,
    )

    assert erro == "Selecione uma sala v\u00e1lida para o n\u00edvel escolhido."


def test_valida_requisicao_de_computador_com_quantidade():
    erro, quantidade, local = validar_requisicao_computador(
        "Fundamental",
        "notebook",
        "11",
        "2026-05-04",
        "10",
        salas=SALAS,
        recursos_computadores=RECURSOS_COMPUTADORES,
        horarios_por_inicio=HORARIOS_POR_INICIO,
        limite_computadores_por_reserva=15,
        horario="07:25",
    )

    assert erro is None
    assert quantidade == 10
    assert local == "11"


def test_valida_requisicao_de_laboratorio_com_local_fixo():
    erro, quantidade, local = validar_requisicao_computador(
        "Fundamental",
        "laboratorio",
        "",
        "2026-05-04",
        "",
        salas=SALAS,
        recursos_computadores=RECURSOS_COMPUTADORES,
        horarios_por_inicio=HORARIOS_POR_INICIO,
        limite_computadores_por_reserva=15,
    )

    assert erro is None
    assert quantidade == 1
    assert local == "LAB15"
