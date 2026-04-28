from permissions import usuario_eh_ti
from permissions import usuario_pode_gerenciar_por_sigla
from permissions import usuario_pode_gerenciar_reserva


def test_ti_pode_gerenciar_registro_de_qualquer_sigla():
    assert usuario_pode_gerenciar_por_sigla("ABC", "TIU", "ti")


def test_professor_pode_gerenciar_apenas_propria_sigla():
    assert usuario_pode_gerenciar_por_sigla("ABC", "ABC", "professor")
    assert not usuario_pode_gerenciar_por_sigla("ABC", "DEF", "professor")


def test_usuario_sem_sigla_nao_gerencia_registro():
    assert not usuario_pode_gerenciar_por_sigla("ABC", "", "professor")


def test_permissao_de_reserva_usa_sigla_do_registro():
    reserva = {"sigla": "ABC"}

    assert usuario_pode_gerenciar_reserva(reserva, "ABC", "professor")
    assert not usuario_pode_gerenciar_reserva(reserva, "DEF", "professor")


def test_identifica_usuario_ti():
    assert usuario_eh_ti("ti")
    assert not usuario_eh_ti("professor")
