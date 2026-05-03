# Portal de Reservas

Sistema web interno para reservas de projetores e computadores em ambiente escolar. Substitui controles feitos em papel, planilha e WhatsApp por um fluxo digital unico.

> Versao de demonstracao com dados ficticios para teste.

---

## O que o sistema faz

**Professores** reservam projetores e computadores pelo sistema.  
**Equipe de TI** acompanha um painel com tarefas organizadas por horario e controle de disponibilidade em tempo real.

O sistema impede conflitos de horario automaticamente e controla o limite real de equipamentos disponiveis.

---

## Tecnologias

Python - Flask - SQLite - HTML - CSS - JavaScript

---

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

Acesse em `http://127.0.0.1:5001/login`

| Usuario | Senha | Perfil |
|---|---|---|
| ANA | demo123 | Professor |
| TEC | admin123 | Equipe TI |

Ao iniciar, o sistema cria o banco local e preenche dados ficticios de demonstracao.

Na versao online, a demo usa acessos fixos, bloqueia novos usuarios e refaz os dados ficticios periodicamente para manter o ambiente limpo.

---

## Autor

**Gustavo Gurtler**  
[LinkedIn](https://linkedin.com/in/gustavo-gurtler1) - [Portfolio](https://gustavogurtler.github.io/portfolio)
