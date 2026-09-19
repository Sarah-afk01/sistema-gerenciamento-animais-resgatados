# Sistema de Cadastro e Gerenciamento de Animais Resgatados

Projeto acadêmico de atividade extensionista desenvolvido com Python, Flask, HTML, CSS, JavaScript e SQLite.

## Funcionalidades

- Dashboard com indicadores.
- Cadastro de animais resgatados.
- Consulta e busca por nome, espécie, raça ou responsável.
- Filtro por situação.
- Edição e exclusão de cadastros.
- Upload de foto.
- Dados de resgate e responsável.
- Histórico veterinário.
- Situação de adoção.

## Requisitos

- Python 3.10 ou superior.
- VS Code recomendado.

## Como executar no Windows

Abra a pasta do projeto no VS Code e, no terminal, execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```

Depois abra no navegador:

http://127.0.0.1:5000

O arquivo `resgate_animal.db` será criado automaticamente na primeira execução.

## Estrutura

```text
resgate_animal/
├── app.py
├── requirements.txt
├── README.md
├── static/
│   ├── css/
│   │   └── style.css
│   └── uploads/
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── animais.html
    ├── animal_form.html
    ├── animal_detalhe.html
    └── 404.html
```

## Observação

Antes de publicar o sistema em um servidor real, altere a `secret_key` definida em `app.py`.

## Versão 2

- Vitrine de adoção.
- Controle de castração, vacinação e vermifugação.
- Microchip e necessidades especiais.
- Dados do adotante e data da adoção.
- Migração automática do banco da versão anterior.
