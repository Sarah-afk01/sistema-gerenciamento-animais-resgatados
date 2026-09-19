from flask import Flask, render_template, request, redirect, url_for, flash, abort
import sqlite3
from pathlib import Path
from werkzeug.utils import secure_filename
import uuid

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "resgate_animal.db"
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.secret_key = "troque-esta-chave-antes-de-publicar"
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4 MB

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS animais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            especie TEXT NOT NULL,
            raca TEXT,
            sexo TEXT,
            idade_aproximada TEXT,
            porte TEXT,
            cor TEXT,
            data_resgate TEXT,
            local_resgate TEXT,
            condicoes_resgate TEXT,
            status TEXT NOT NULL DEFAULT 'Resgatado',
            responsavel TEXT,
            contato_responsavel TEXT,
            observacoes TEXT,
            foto TEXT,
            castrado TEXT DEFAULT 'Não informado',
            vacinado TEXT DEFAULT 'Não informado',
            vermifugado TEXT DEFAULT 'Não informado',
            microchip TEXT,
            necessidades_especiais TEXT,
            adotante_nome TEXT,
            adotante_contato TEXT,
            data_adocao TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS historico_veterinario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id INTEGER NOT NULL,
            data_atendimento TEXT NOT NULL,
            tipo_atendimento TEXT NOT NULL,
            descricao TEXT NOT NULL,
            veterinario TEXT,
            FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE
        );
        """
    )

    colunas = {row["name"] for row in conn.execute("PRAGMA table_info(animais)").fetchall()}
    novas_colunas = {
        "castrado": "TEXT DEFAULT 'Não informado'",
        "vacinado": "TEXT DEFAULT 'Não informado'",
        "vermifugado": "TEXT DEFAULT 'Não informado'",
        "microchip": "TEXT",
        "necessidades_especiais": "TEXT",
        "adotante_nome": "TEXT",
        "adotante_contato": "TEXT",
        "data_adocao": "TEXT",
    }
    for nome, tipo in novas_colunas.items():
        if nome not in colunas:
            conn.execute(f"ALTER TABLE animais ADD COLUMN {nome} {tipo}")
    conn.commit()
    conn.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_photo(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    if not allowed_file(file_storage.filename):
        raise ValueError("Formato de imagem não permitido. Use PNG, JPG, JPEG ou WEBP.")

    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    destination = UPLOAD_FOLDER / filename
    file_storage.save(destination)
    return filename


def delete_photo(filename):
    if not filename:
        return
    path = UPLOAD_FOLDER / filename
    if path.exists() and path.is_file():
        path.unlink()


@app.context_processor
def inject_status_options():
    return {
        "status_options": [
            "Resgatado",
            "Em tratamento",
            "Em recuperação",
            "Disponível para adoção",
            "Em processo de adoção",
            "Adotado",
        ]
    }


@app.route("/")
def dashboard():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM animais").fetchone()[0]
    tratamento = conn.execute(
        "SELECT COUNT(*) FROM animais WHERE status IN ('Em tratamento', 'Em recuperação')"
    ).fetchone()[0]
    disponiveis = conn.execute(
        "SELECT COUNT(*) FROM animais WHERE status = 'Disponível para adoção'"
    ).fetchone()[0]
    adotados = conn.execute(
        "SELECT COUNT(*) FROM animais WHERE status = 'Adotado'"
    ).fetchone()[0]

    recentes = conn.execute(
        "SELECT * FROM animais ORDER BY id DESC LIMIT 5"
    ).fetchall()
    conn.close()

    return render_template(
        "dashboard.html",
        total=total,
        tratamento=tratamento,
        disponiveis=disponiveis,
        adotados=adotados,
        recentes=recentes,
    )


@app.route("/adocao")
def adocao():
    conn = get_db()
    animais = conn.execute(
        "SELECT * FROM animais WHERE status = 'Disponível para adoção' ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return render_template("adocao.html", animais=animais)


@app.route("/animais")
def listar_animais():
    busca = request.args.get("busca", "").strip()
    status = request.args.get("status", "").strip()

    sql = "SELECT * FROM animais WHERE 1=1"
    params = []

    if busca:
        sql += " AND (nome LIKE ? OR especie LIKE ? OR raca LIKE ? OR responsavel LIKE ?)"
        term = f"%{busca}%"
        params.extend([term, term, term, term])

    if status:
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY id DESC"

    conn = get_db()
    animais = conn.execute(sql, params).fetchall()
    conn.close()

    return render_template(
        "animais.html",
        animais=animais,
        busca=busca,
        status_filtro=status,
    )


@app.route("/animais/novo", methods=["GET", "POST"])
def novo_animal():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        especie = request.form.get("especie", "").strip()
        status = request.form.get("status", "Resgatado").strip()

        if not nome or not especie:
            flash("Nome e espécie são campos obrigatórios.", "erro")
            return render_template("animal_form.html", animal=request.form, editando=False)

        try:
            foto = save_photo(request.files.get("foto"))
        except ValueError as exc:
            flash(str(exc), "erro")
            return render_template("animal_form.html", animal=request.form, editando=False)

        dados = (
            nome,
            especie,
            request.form.get("raca", "").strip(),
            request.form.get("sexo", "").strip(),
            request.form.get("idade_aproximada", "").strip(),
            request.form.get("porte", "").strip(),
            request.form.get("cor", "").strip(),
            request.form.get("data_resgate", "").strip(),
            request.form.get("local_resgate", "").strip(),
            request.form.get("condicoes_resgate", "").strip(),
            status,
            request.form.get("responsavel", "").strip(),
            request.form.get("contato_responsavel", "").strip(),
            request.form.get("observacoes", "").strip(),
            foto,
            request.form.get("castrado", "Não informado").strip(),
            request.form.get("vacinado", "Não informado").strip(),
            request.form.get("vermifugado", "Não informado").strip(),
            request.form.get("microchip", "").strip(),
            request.form.get("necessidades_especiais", "").strip(),
            request.form.get("adotante_nome", "").strip(),
            request.form.get("adotante_contato", "").strip(),
            request.form.get("data_adocao", "").strip(),
        )

        conn = get_db()
        conn.execute(
            """
            INSERT INTO animais (
                nome, especie, raca, sexo, idade_aproximada, porte, cor,
                data_resgate, local_resgate, condicoes_resgate, status,
                responsavel, contato_responsavel, observacoes, foto,
                castrado, vacinado, vermifugado, microchip, necessidades_especiais,
                adotante_nome, adotante_contato, data_adocao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            dados,
        )
        conn.commit()
        conn.close()

        flash("Animal cadastrado com sucesso.", "sucesso")
        return redirect(url_for("listar_animais"))

    return render_template("animal_form.html", animal=None, editando=False)


@app.route("/animais/<int:animal_id>")
def detalhe_animal(animal_id):
    conn = get_db()
    animal = conn.execute(
        "SELECT * FROM animais WHERE id = ?", (animal_id,)
    ).fetchone()

    if animal is None:
        conn.close()
        abort(404)

    historico = conn.execute(
        """
        SELECT * FROM historico_veterinario
        WHERE animal_id = ?
        ORDER BY data_atendimento DESC, id DESC
        """,
        (animal_id,),
    ).fetchall()
    conn.close()

    return render_template("animal_detalhe.html", animal=animal, historico=historico)


@app.route("/animais/<int:animal_id>/editar", methods=["GET", "POST"])
def editar_animal(animal_id):
    conn = get_db()
    animal = conn.execute(
        "SELECT * FROM animais WHERE id = ?", (animal_id,)
    ).fetchone()

    if animal is None:
        conn.close()
        abort(404)

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        especie = request.form.get("especie", "").strip()

        if not nome or not especie:
            conn.close()
            flash("Nome e espécie são campos obrigatórios.", "erro")
            return render_template("animal_form.html", animal=request.form, editando=True)

        foto_atual = animal["foto"]
        foto_nova = request.files.get("foto")

        try:
            if foto_nova and foto_nova.filename:
                nova_foto = save_photo(foto_nova)
                delete_photo(foto_atual)
                foto_atual = nova_foto
        except ValueError as exc:
            conn.close()
            flash(str(exc), "erro")
            return render_template("animal_form.html", animal=animal, editando=True)

        dados = (
            nome,
            especie,
            request.form.get("raca", "").strip(),
            request.form.get("sexo", "").strip(),
            request.form.get("idade_aproximada", "").strip(),
            request.form.get("porte", "").strip(),
            request.form.get("cor", "").strip(),
            request.form.get("data_resgate", "").strip(),
            request.form.get("local_resgate", "").strip(),
            request.form.get("condicoes_resgate", "").strip(),
            request.form.get("status", "").strip(),
            request.form.get("responsavel", "").strip(),
            request.form.get("contato_responsavel", "").strip(),
            request.form.get("observacoes", "").strip(),
            foto_atual,
            request.form.get("castrado", "Não informado").strip(),
            request.form.get("vacinado", "Não informado").strip(),
            request.form.get("vermifugado", "Não informado").strip(),
            request.form.get("microchip", "").strip(),
            request.form.get("necessidades_especiais", "").strip(),
            request.form.get("adotante_nome", "").strip(),
            request.form.get("adotante_contato", "").strip(),
            request.form.get("data_adocao", "").strip(),
            animal_id,
        )

        conn.execute(
            """
            UPDATE animais
            SET nome=?, especie=?, raca=?, sexo=?, idade_aproximada=?, porte=?, cor=?,
                data_resgate=?, local_resgate=?, condicoes_resgate=?, status=?,
                responsavel=?, contato_responsavel=?, observacoes=?, foto=?,
                castrado=?, vacinado=?, vermifugado=?, microchip=?, necessidades_especiais=?,
                adotante_nome=?, adotante_contato=?, data_adocao=?
            WHERE id=?
            """,
            dados,
        )
        conn.commit()
        conn.close()

        flash("Cadastro atualizado com sucesso.", "sucesso")
        return redirect(url_for("detalhe_animal", animal_id=animal_id))

    conn.close()
    return render_template("animal_form.html", animal=animal, editando=True)


@app.route("/animais/<int:animal_id>/excluir", methods=["POST"])
def excluir_animal(animal_id):
    conn = get_db()
    animal = conn.execute(
        "SELECT * FROM animais WHERE id = ?", (animal_id,)
    ).fetchone()

    if animal is None:
        conn.close()
        abort(404)

    foto = animal["foto"]
    conn.execute("DELETE FROM animais WHERE id = ?", (animal_id,))
    conn.commit()
    conn.close()

    delete_photo(foto)
    flash("Cadastro excluído.", "sucesso")
    return redirect(url_for("listar_animais"))


@app.route("/animais/<int:animal_id>/historico/novo", methods=["POST"])
def adicionar_historico(animal_id):
    data_atendimento = request.form.get("data_atendimento", "").strip()
    tipo_atendimento = request.form.get("tipo_atendimento", "").strip()
    descricao = request.form.get("descricao", "").strip()
    veterinario = request.form.get("veterinario", "").strip()

    if not data_atendimento or not tipo_atendimento or not descricao:
        flash("Preencha data, tipo de atendimento e descrição.", "erro")
        return redirect(url_for("detalhe_animal", animal_id=animal_id))

    conn = get_db()

    animal = conn.execute(
        "SELECT id FROM animais WHERE id = ?", (animal_id,)
    ).fetchone()

    if animal is None:
        conn.close()
        abort(404)

    conn.execute(
        """
        INSERT INTO historico_veterinario
        (animal_id, data_atendimento, tipo_atendimento, descricao, veterinario)
        VALUES (?, ?, ?, ?, ?)
        """,
        (animal_id, data_atendimento, tipo_atendimento, descricao, veterinario),
    )
    conn.commit()
    conn.close()

    flash("Registro veterinário adicionado.", "sucesso")
    return redirect(url_for("detalhe_animal", animal_id=animal_id))


@app.route("/historico/<int:registro_id>/excluir", methods=["POST"])
def excluir_historico(registro_id):
    conn = get_db()
    registro = conn.execute(
        "SELECT * FROM historico_veterinario WHERE id = ?", (registro_id,)
    ).fetchone()

    if registro is None:
        conn.close()
        abort(404)

    animal_id = registro["animal_id"]
    conn.execute(
        "DELETE FROM historico_veterinario WHERE id = ?", (registro_id,)
    )
    conn.commit()
    conn.close()

    flash("Registro veterinário excluído.", "sucesso")
    return redirect(url_for("detalhe_animal", animal_id=animal_id))


@app.errorhandler(404)
def pagina_nao_encontrada(_):
    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    app.run(debug=True)
