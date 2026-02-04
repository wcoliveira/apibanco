from flask import Flask, jsonify, request
import sqlite3
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
DATABASE = "banco.db"

# ---------------------------
# Função para conexão
# ---------------------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # permite acessar colunas por nome
    return conn

# ---------------------------
# Criar tabela (1ª execução)
# ---------------------------
def criar_tabela():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL UNIQUE,
            saldo REAL NOT NULL DEFAULT 0.0
        )
    """)

    conn.commit()
    conn.close()

# ---------------------------
# Validação de CPF (função simples)
# ---------------------------
def validar_cpf(cpf: str) -> bool:
    if len(cpf) != 11 or not cpf.isdigit():
        return False
    def calcula_dv(nums):
        s = sum((i+2)*int(n) for i, n in enumerate(reversed(nums)))
        dv = s % 11
        return 0 if dv < 2 else 11 - dv
    base = cpf[:-2]
    dv1 = calcula_dv(base)
    dv2 = calcula_dv(base + str(dv1))
    return cpf == f"{base}{dv1}{dv2}"

# ---------------------------
# Verifica se CPF já existe
# ---------------------------
def cpf_existe(cpf: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM clientes WHERE cpf = ?", (cpf,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

# ---------------------------
# GET - listar clientes (nome e cpf)
# ---------------------------
@app.route("/clientes", methods=["GET"])
def listar_clientes():
    conn = get_db_connection()
    rows = conn.execute("SELECT nome, cpf FROM clientes").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

# ---------------------------
# GET - listar cliente por ID
# ---------------------------
@app.route("/clientes/<int:cliente_id>", methods=["GET"])
def listar_cliente_por_id(cliente_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Cliente não encontrado"}), 404
    return jsonify(dict(row))

# ---------------------------
# POST - cadastrar cliente - Passar no Body em json os campos {"nome":"nome", "cpf":"000000000"}
# ---------------------------
@app.route("/clientes", methods=["POST"])
def cadastrar_cliente():
    data = request.get_json()
    nome = data.get("nome")
    cpf = data.get("cpf")
    saldo = data.get("saldo", 0.0)

    if not nome or not cpf:
        return jsonify({"error": "Nome e CPF são obrigatórios"}), 400
    if not validar_cpf(cpf):
        return jsonify({"error": "CPF inválido"}), 400
    if cpf_existe(cpf):
        return jsonify({"error": "CPF já cadastrado"}), 409

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clientes (nome, cpf, saldo) VALUES (?, ?, ?)",
        (nome, cpf, saldo)
    )
    conn.commit()
    cliente_id = cursor.lastrowid
    conn.close()

    return jsonify({"id": cliente_id, "nome": nome, "cpf": cpf, "saldo": saldo}), 201

# ---------------------------
# PUT - atualizar cliente - Passar no Body em json o valor do nome ou cpf: {"nome":"nome" ou "cpf": "cpf"}
# ---------------------------
@app.route("/clientes/<int:cliente_id>", methods=["PUT"])
def atualizar_cliente(cliente_id):
    data = request.get_json()
    nome = data.get("nome")
    cpf = data.get("cpf")

    if not nome and not cpf:
        return jsonify({"error": "Pelo menos nome ou CPF deve ser informado"}), 400
    if cpf and not validar_cpf(cpf):
        return jsonify({"error": "CPF inválido"}), 400
    if cpf and cpf_existe(cpf):
        return jsonify({"error": "CPF já cadastrado"}), 409

    conn = get_db_connection()
    cursor = conn.cursor()
    if cpf:
        cursor.execute(
            "UPDATE clientes SET nome = ?, cpf = ? WHERE id = ?",
            (nome, cpf, cliente_id)
        )
    else:
        cursor.execute(
            "UPDATE clientes SET nome = ? WHERE id = ?",
            (nome, cliente_id)
        )
    conn.commit()
    conn.close()

    return jsonify({"id": cliente_id, "nome": nome, "cpf": cpf if cpf else "mantido"})

# ---------------------------
# PUT - depósito - Passar no Body em json o valor do depósito: {"valor":0.0}
# ---------------------------
@app.route("/clientes/<int:cliente_id>/deposito", methods=["PUT"])
def deposito(cliente_id):
    valor = request.get_json().get("valor")
    if valor is None or valor <= 0:
        return jsonify({"error": "Valor inválido"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT saldo FROM clientes WHERE id = ?", (cliente_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "Cliente não encontrado"}), 404

    novo_saldo = row["saldo"] + valor
    cursor.execute("UPDATE clientes SET saldo = ? WHERE id = ?", (novo_saldo, cliente_id))
    conn.commit()
    conn.close()

    return jsonify({"saldo": novo_saldo})

# ---------------------------
# PUT - saque - Passar no Body em json o valor do saque: {"valor":0.0}
# ---------------------------
@app.route("/clientes/<int:cliente_id>/saque", methods=["PUT"])
def saque(cliente_id):
    valor = request.get_json().get("valor")
    if valor is None or valor <= 0:
        return jsonify({"error": "Valor inválido"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT saldo FROM clientes WHERE id = ?", (cliente_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "Cliente não encontrado"}), 404

    if valor > row["saldo"]:
        conn.close()
        return jsonify({"error": "Saldo insuficiente"}), 400

    novo_saldo = row["saldo"] - valor
    cursor.execute("UPDATE clientes SET saldo = ? WHERE id = ?", (novo_saldo, cliente_id))
    conn.commit()
    conn.close()

    return jsonify({"saldo": novo_saldo})

# ---------------------------
# Inicialização
# ---------------------------
if __name__ == "__main__":
    criar_tabela()
    app.run(debug=True)