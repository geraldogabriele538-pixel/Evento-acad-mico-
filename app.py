#!/usr/bin/env python3
"""
Sistema de Organização de Evento Acadêmico - Caso 2
Backend em Python puro (biblioteca padrão apenas: http.server + sqlite3)
Nao exige instalar nada (sem Flask, sem pip install).

Como rodar:
    python3 app.py
Depois abra no navegador:
    http://localhost:8000
"""

import json
import sqlite3
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "evento.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

PORT = int(os.environ.get("PORT", 8000))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    first_time = not os.path.exists(DB_PATH)
    conn = get_conn()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    if first_time:
        print("Banco de dados criado em", DB_PATH)


def rows_to_list(rows):
    return [dict(r) for r in rows]


# ------------------------------------------------------------------
# Camada de acesso a dados / regras de cada endpoint
# ------------------------------------------------------------------

def q(conn, sql, params=()):
    return rows_to_list(conn.execute(sql, params).fetchall())


def api_router(method, path, query, body):
    conn = get_conn()
    try:
        # ---------- listas auxiliares para selects ----------
        if path == "/api/instituicoes" and method == "GET":
            return 200, q(conn, "SELECT * FROM instituicoes ORDER BY nome")
        if path == "/api/instituicoes" and method == "POST":
            conn.execute("INSERT OR IGNORE INTO instituicoes(nome) VALUES (?)", (body["nome"],))
            conn.commit()
            return 201, {"ok": True}

        if path == "/api/vinculos" and method == "GET":
            return 200, q(conn, "SELECT * FROM tipos_vinculo ORDER BY vinculo")
        if path == "/api/vinculos" and method == "POST":
            conn.execute("INSERT OR IGNORE INTO tipos_vinculo(vinculo) VALUES (?)", (body["vinculo"],))
            conn.commit()
            return 201, {"ok": True}

        if path == "/api/tipos_atividade" and method == "GET":
            return 200, q(conn, "SELECT * FROM tipos_atividade ORDER BY tipo")
        if path == "/api/tipos_atividade" and method == "POST":
            conn.execute(
                "INSERT OR IGNORE INTO tipos_atividade(tipo, tem_premiacao) VALUES (?,?)",
                (body["tipo"], body.get("tem_premiacao", "N")),
            )
            conn.commit()
            return 201, {"ok": True}

        # ---------- pessoas ----------
        if path == "/api/pessoas" and method == "POST":
            conn.execute(
                """INSERT INTO pessoas(cpf, nome, telefone, email, sexo, instituicao_origem, vinculo)
                   VALUES (?,?,?,?,?,?,?)""",
                (body["cpf"], body["nome"], body.get("telefone"), body.get("email"),
                 body.get("sexo"), body.get("instituicao_origem"), body.get("vinculo")),
            )
            conn.commit()
            return 201, {"ok": True}
        if path == "/api/pessoas" and method == "GET":
            cpf = query.get("cpf", [""])[0]
            nome = query.get("nome", [""])[0]
            sql = "SELECT * FROM pessoas WHERE 1=1"
            params = []
            if cpf:
                sql += " AND cpf LIKE ?"
                params.append(f"%{cpf}%")
            if nome:
                sql += " AND nome LIKE ?"
                params.append(f"%{nome}%")
            sql += " ORDER BY nome"
            return 200, q(conn, sql, params)

        # ---------- inscritos ----------
        if path == "/api/inscritos" and method == "POST":
            conn.execute(
                "INSERT INTO inscritos(cpf, data_inscricao, pagamento_inscricao) VALUES (?,?,?)",
                (body["cpf"], body["data_inscricao"], body.get("pagamento_inscricao")),
            )
            conn.commit()
            return 201, {"ok": True}
        if path == "/api/inscritos" and method == "GET":
            return 200, q(conn, """
                SELECT i.cpf, p.nome, i.data_inscricao, i.pagamento_inscricao
                FROM inscritos i JOIN pessoas p ON p.cpf = i.cpf
                ORDER BY p.nome
            """)

        # ---------- equipe organizadora / apoio ----------
        if path == "/api/equipe_organizadora" and method == "POST":
            conn.execute(
                "INSERT INTO equipe_organizadora(cpf, data_ingresso) VALUES (?,?)",
                (body["cpf"], body["data_ingresso"]),
            )
            conn.commit()
            return 201, {"ok": True}
        if path == "/api/equipe_organizadora" and method == "GET":
            return 200, q(conn, """
                SELECT e.cpf, p.nome, e.data_ingresso
                FROM equipe_organizadora e JOIN pessoas p ON p.cpf = e.cpf
                ORDER BY p.nome
            """)

        if path == "/api/equipe_apoio" and method == "POST":
            conn.execute(
                "INSERT INTO equipe_apoio(cpf, data_ingresso) VALUES (?,?)",
                (body["cpf"], body["data_ingresso"]),
            )
            conn.commit()
            return 201, {"ok": True}
        if path == "/api/equipe_apoio" and method == "GET":
            return 200, q(conn, """
                SELECT e.cpf, p.nome, e.data_ingresso
                FROM equipe_apoio e JOIN pessoas p ON p.cpf = e.cpf
                ORDER BY p.nome
            """)

        # ---------- atividades ----------
        if path == "/api/atividades" and method == "POST":
            cur = conn.execute(
                "INSERT INTO atividades(tipo, nome, dia, hora, vagas) VALUES (?,?,?,?,?)",
                (body["tipo"], body["nome"], body["dia"], body["hora"], body["vagas"]),
            )
            atividade_id = cur.lastrowid
            for cpf in body.get("organizadores", []):
                conn.execute(
                    "INSERT OR IGNORE INTO atividade_organizadores(id_atividade, cpf) VALUES (?,?)",
                    (atividade_id, cpf),
                )
            for cpf in body.get("apoio", []):
                conn.execute(
                    "INSERT OR IGNORE INTO atividade_apoio(id_atividade, cpf) VALUES (?,?)",
                    (atividade_id, cpf),
                )
            conn.commit()
            return 201, {"ok": True, "id": atividade_id}
        if path == "/api/atividades" and method == "GET":
            nome = query.get("nome", [""])[0]
            sql = "SELECT * FROM atividades WHERE 1=1"
            params = []
            if nome:
                sql += " AND nome LIKE ?"
                params.append(f"%{nome}%")
            sql += " ORDER BY dia, hora"
            atividades = q(conn, sql, params)
            for a in atividades:
                a["organizadores"] = q(conn, """
                    SELECT p.cpf, p.nome FROM atividade_organizadores ao
                    JOIN pessoas p ON p.cpf = ao.cpf WHERE ao.id_atividade=?""", (a["id"],))
                a["apoio"] = q(conn, """
                    SELECT p.cpf, p.nome FROM atividade_apoio aa
                    JOIN pessoas p ON p.cpf = aa.cpf WHERE aa.id_atividade=?""", (a["id"],))
                a["ministrantes"] = q(conn, """
                    SELECT p.cpf, p.nome FROM ministrante m
                    JOIN pessoas p ON p.cpf = m.cpf WHERE m.id_atividade=?""", (a["id"],))
                a["inscritos_confirmados"] = q(conn, """
                    SELECT COUNT(*) as total FROM presenca_atividade WHERE id_atividade=?""",
                    (a["id"],))[0]["total"]
            return 200, atividades

        # ---------- ministrante ----------
        if path == "/api/ministrantes" and method == "POST":
            conn.execute(
                "INSERT INTO ministrante(cpf, id_atividade) VALUES (?,?)",
                (body["cpf"], body["id_atividade"]),
            )
            conn.commit()
            return 201, {"ok": True}
        if path == "/api/ministrantes" and method == "GET":
            return 200, q(conn, """
                SELECT m.id, p.nome, p.cpf, a.nome as atividade, a.id as id_atividade
                FROM ministrante m
                JOIN pessoas p ON p.cpf = m.cpf
                JOIN atividades a ON a.id = m.id_atividade
            """)

        # ---------- presenca ----------
        if path == "/api/presencas" and method == "POST":
            conn.execute(
                "INSERT OR IGNORE INTO presenca_atividade(id_atividade, cpf) VALUES (?,?)",
                (body["id_atividade"], body["cpf"]),
            )
            conn.commit()
            return 201, {"ok": True}
        if path == "/api/presencas" and method == "GET":
            id_atividade = query.get("id_atividade", [""])[0]
            sql = """SELECT pa.id_atividade, a.nome as atividade, pa.cpf, p.nome
                      FROM presenca_atividade pa
                      JOIN pessoas p ON p.cpf = pa.cpf
                      JOIN atividades a ON a.id = pa.id_atividade WHERE 1=1"""
            params = []
            if id_atividade:
                sql += " AND pa.id_atividade=?"
                params.append(id_atividade)
            return 200, q(conn, sql, params)

        # ---------- hotel ----------
        if path == "/api/hoteis" and method == "POST":
            conn.execute(
                "INSERT INTO hotel(nome, endereco, telefone, numero_quartos, pessoas_por_quarto) VALUES (?,?,?,?,?)",
                (body["nome"], body.get("endereco"), body.get("telefone"),
                 body.get("numero_quartos"), body.get("pessoas_por_quarto")),
            )
            conn.commit()
            return 201, {"ok": True}
        if path == "/api/hoteis" and method == "GET":
            return 200, q(conn, "SELECT * FROM hotel ORDER BY nome")

        if path == "/api/quartos_hotel" and method == "POST":
            conn.execute(
                "INSERT OR IGNORE INTO quartos_hotel(nome_hotel, quarto) VALUES (?,?)",
                (body["nome_hotel"], body["quarto"]),
            )
            conn.commit()
            return 201, {"ok": True}
        if path == "/api/quartos_hotel" and method == "GET":
            hotel = query.get("hotel", [""])[0]
            sql = """SELECT qh.*,
                       (SELECT COUNT(*) FROM inscritos_alocados ia
                        WHERE ia.nome_hotel = qh.nome_hotel AND ia.quarto = qh.quarto) as ocupantes
                      FROM quartos_hotel qh WHERE 1=1"""
            params = []
            if hotel:
                sql += " AND nome_hotel=?"
                params.append(hotel)
            return 200, q(conn, sql, params)

        # ---------- alocacao ----------
        if path == "/api/alocacoes" and method == "POST":
            conn.execute(
                "INSERT OR REPLACE INTO inscritos_alocados(cpf, nome_hotel, quarto) VALUES (?,?,?)",
                (body["cpf"], body["nome_hotel"], body["quarto"]),
            )
            conn.commit()
            return 201, {"ok": True}
        if path == "/api/alocacoes" and method == "GET":
            return 200, q(conn, """
                SELECT ia.cpf, p.nome, p.instituicao_origem, ia.nome_hotel, ia.quarto
                FROM inscritos_alocados ia
                JOIN pessoas p ON p.cpf = ia.cpf
                ORDER BY ia.nome_hotel, ia.quarto
            """)

        # ---------- RELATORIOS ----------
        if path == "/api/relatorios/inscritos_excedentes" and method == "GET":
            atividades = q(conn, "SELECT * FROM atividades ORDER BY dia, hora")
            resultado = []
            for a in atividades:
                inscritos = q(conn, """
                    SELECT p.cpf, p.nome FROM presenca_atividade pa
                    JOIN pessoas p ON p.cpf = pa.cpf WHERE pa.id_atividade=?""", (a["id"],))
                total = len(inscritos)
                vagas = a["vagas"]
                resultado.append({
                    "atividade": a["nome"], "dia": a["dia"], "hora": a["hora"],
                    "vagas": vagas, "total_inscritos": total,
                    "excedentes": max(0, total - vagas),
                    "inscritos": inscritos,
                })
            return 200, resultado

        if path == "/api/relatorios/ministrantes_apoio" and method == "GET":
            atividades = q(conn, "SELECT * FROM atividades ORDER BY dia, hora")
            for a in atividades:
                a["ministrantes"] = q(conn, """
                    SELECT p.nome, p.cpf FROM ministrante m
                    JOIN pessoas p ON p.cpf = m.cpf WHERE m.id_atividade=?""", (a["id"],))
                a["equipe_apoio"] = q(conn, """
                    SELECT p.nome, p.cpf FROM atividade_apoio aa
                    JOIN pessoas p ON p.cpf = aa.cpf WHERE aa.id_atividade=?""", (a["id"],))
            return 200, atividades

        if path == "/api/relatorios/presentes_confirmados" and method == "GET":
            return 200, q(conn, """
                SELECT a.nome as atividade, a.dia, a.hora, p.cpf, p.nome
                FROM presenca_atividade pa
                JOIN atividades a ON a.id = pa.id_atividade
                JOIN pessoas p ON p.cpf = pa.cpf
                ORDER BY a.dia, a.hora, p.nome
            """)

        if path == "/api/relatorios/certificados" and method == "GET":
            return 200, q(conn, """
                SELECT p.nome, p.cpf, a.nome as atividade, a.tipo, a.dia
                FROM presenca_atividade pa
                JOIN pessoas p ON p.cpf = pa.cpf
                JOIN atividades a ON a.id = pa.id_atividade
                ORDER BY p.nome, a.dia
            """)

        if path == "/api/relatorios/hotel_quartos" and method == "GET":
            return 200, q(conn, """
                SELECT h.nome as hotel, qh.quarto, p.nome as pessoa, p.instituicao_origem
                FROM quartos_hotel qh
                JOIN hotel h ON h.nome = qh.nome_hotel
                LEFT JOIN inscritos_alocados ia
                  ON ia.nome_hotel = qh.nome_hotel AND ia.quarto = qh.quarto
                LEFT JOIN pessoas p ON p.cpf = ia.cpf
                ORDER BY h.nome, qh.quarto
            """)

        return 404, {"error": "rota nao encontrada"}
    finally:
        conn.close()


# ------------------------------------------------------------------
# HTTP server
# ------------------------------------------------------------------

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silencia log padrao (deixa o terminal limpo)

    def _send_json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _send_static(self, path):
        if path == "/":
            path = "/index.html"
        fs_path = os.path.join(STATIC_DIR, path.lstrip("/"))
        if not os.path.abspath(fs_path).startswith(STATIC_DIR) or not os.path.isfile(fs_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return
        ext = os.path.splitext(fs_path)[1]
        with open(fs_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            query = parse_qs(parsed.query)
            status, payload = api_router("GET", parsed.path, query, None)
            self._send_json(status, payload)
        else:
            self._send_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "JSON invalido"})
            return
        try:
            status, payload = api_router("POST", parsed.path, {}, body)
        except sqlite3.IntegrityError as e:
            status, payload = 400, {"error": f"Erro de integridade no banco: {e}"}
        except KeyError as e:
            status, payload = 400, {"error": f"Campo obrigatorio ausente: {e}"}
        self._send_json(status, payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def main():
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Servidor rodando na porta {PORT}  (Ctrl+C para parar)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
        server.shutdown()


if __name__ == "__main__":
    main()
