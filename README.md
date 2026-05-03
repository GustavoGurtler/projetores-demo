# Portal de Reservas de Equipamentos

Sistema web para organizar reservas de projetores, computadores e sala de informatica em ambiente escolar.

A ideia do projeto e tirar esse controle de planilhas, papel e mensagens soltas, deixando professores e equipe de TI trabalhando no mesmo fluxo.

Demo online: [projetores-demo.onrender.com](https://projetores-demo.onrender.com/login)

## Acessos de teste

| Perfil | Usuario | Senha |
|---|---|---|
| Professor | ANA | demo123 |
| Equipe de TI | TEC | admin123 |

Os dados da demo sao ficticios. O ambiente online usa acessos fixos e refaz os dados periodicamente para manter a demonstracao limpa.

## O que o sistema faz

- Permite reservar projetores, notebooks, Chromebooks e a Sala 15.
- Bloqueia conflitos de horario, sala e disponibilidade de equipamentos.
- Mostra ao professor as proprias reservas em uma tela separada.
- Gera um monitor operacional para a equipe de TI acompanhar entregas, trocas e retiradas.
- Consolida as solicitacoes em um relatorio geral com exportacao para Excel.

## Tecnologias

- Python
- Flask
- SQLite
- HTML, CSS e JavaScript
- Gunicorn
- Render

## Como rodar localmente

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Depois acesse:

```txt
http://127.0.0.1:5001/login
```

Ao iniciar, o sistema cria o banco local automaticamente e preenche dados ficticios para teste.

## Autor

Gustavo Gurtler  
[LinkedIn](https://linkedin.com/in/gustavo-gurtler1) - [Portfolio](https://gustavogurtler.github.io/portfolio)
