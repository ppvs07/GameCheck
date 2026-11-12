from flask import Flask, render_template, request, redirect, url_for, flash, abort
from pathlib import Path
import sqlite3

BASE = Path(__file__).resolve().parent
DB = BASE / "database" / "gamecheck.db"
app = Flask(__name__)
import os
app.secret_key = os.environ.get("SECRET_KEY", "gamecheck-local-dev-key")

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_db():
    DB.parent.mkdir(exist_ok=True)
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS jogos (
          id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, descricao TEXT NOT NULL,
          plataformas TEXT NOT NULL, ano INTEGER NOT NULL, genero TEXT NOT NULL,
          cor TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS avaliacoes (
          id INTEGER PRIMARY KEY AUTOINCREMENT, jogo_id INTEGER NOT NULL,
          nome TEXT NOT NULL, nota INTEGER NOT NULL CHECK(nota BETWEEN 1 AND 5),
          comentario TEXT NOT NULL, criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(jogo_id) REFERENCES jogos(id) ON DELETE CASCADE
        );
        """)
        jogos = [
          (1, "Grand Theft Auto V", "Explore Los Santos em uma aventura de mundo aberto com três protagonistas.", "PC, PS4, PS5, Xbox One, Xbox Series X|S", 2013, "Ação / Mundo aberto", "#6a9956"),
          (2, "Red Dead Redemption 2", "Uma história épica no Velho Oeste com Arthur Morgan e sua gangue.", "PC, PS4, Xbox One", 2018, "Ação / Aventura", "#ae543b"),
          (3, "Cyberpunk 2077", "Mergulhe em Night City em um RPG futurista cheio de escolhas.", "PC, PS4, PS5, Xbox One, Xbox Series X|S", 2020, "RPG / Ação", "#d4b73f"),
        ]
        con.executemany("INSERT OR IGNORE INTO jogos VALUES (?,?,?,?,?,?,?)", jogos)

@app.route("/")
def index():
    busca = request.args.get("q", "").strip()
    plataforma = request.args.get("plataforma", "").strip()
    sql = """SELECT j.*, ROUND(AVG(a.nota),1) AS media, COUNT(a.id) AS total
             FROM jogos j LEFT JOIN avaliacoes a ON a.jogo_id=j.id
             WHERE (j.titulo LIKE ? OR j.genero LIKE ?) AND j.plataformas LIKE ?
             GROUP BY j.id ORDER BY j.titulo"""
    with connect() as con:
        jogos = con.execute(sql, (f"%{busca}%",f"%{busca}%",f"%{plataforma}%")).fetchall()
    return render_template("index.html", jogos=jogos, busca=busca, plataforma=plataforma)

@app.route("/jogo/<int:jogo_id>", methods=["GET","POST"])
def jogo(jogo_id):
    with connect() as con:
        game = con.execute("SELECT * FROM jogos WHERE id=?", (jogo_id,)).fetchone()
        if not game:
            abort(404)
        if request.method == "POST":
            nome = request.form.get("nome","").strip()
            comentario = request.form.get("comentario","").strip()
            try:
                nota = int(request.form.get("nota",""))
            except ValueError:
                nota = 0
            if not (1 <= len(nome) <= 50 and 1 <= len(comentario) <= 1000 and 1 <= nota <= 5):
                flash("Preencha nome, nota de 1 a 5 e comentário (até 1000 caracteres).", "erro")
            else:
                con.execute("INSERT INTO avaliacoes (jogo_id,nome,nota,comentario) VALUES (?,?,?,?)",
                            (jogo_id,nome,nota,comentario))
                con.commit()
                flash("Avaliação publicada!", "sucesso")
                return redirect(url_for("jogo", jogo_id=jogo_id))
        avaliacoes = con.execute("SELECT * FROM avaliacoes WHERE jogo_id=? ORDER BY id DESC", (jogo_id,)).fetchall()
        stats = con.execute("SELECT ROUND(AVG(nota),1) AS media, COUNT(*) AS total FROM avaliacoes WHERE jogo_id=?", (jogo_id,)).fetchone()
    return render_template("jogo.html", jogo=game, avaliacoes=avaliacoes, stats=stats)

init_db()
if __name__ == "__main__":
    app.run(debug=True)
