"""Persistência em SQLite e dados de exemplo (panificadora fictícia)."""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "pcp.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('PA', 'MP', 'EMB')),
    unidade TEXT NOT NULL,
    estoque_atual REAL NOT NULL DEFAULT 0,
    estoque_minimo REAL NOT NULL DEFAULT 0,
    lead_time_dias INTEGER NOT NULL DEFAULT 0,
    custo_unit REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS bom (
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    componente_id INTEGER NOT NULL REFERENCES produtos(id),
    qtd_por_un REAL NOT NULL,
    PRIMARY KEY (produto_id, componente_id)
);
CREATE TABLE IF NOT EXISTS maquinas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    horas_dia REAL NOT NULL DEFAULT 16
);
CREATE TABLE IF NOT EXISTS roteiro (
    produto_id INTEGER PRIMARY KEY REFERENCES produtos(id),
    maquina_id INTEGER NOT NULL REFERENCES maquinas(id),
    un_por_hora REAL NOT NULL,
    setup_min REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente TEXT NOT NULL,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    quantidade REAL NOT NULL,
    data_entrega TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Aberto'
        CHECK (status IN ('Aberto', 'Entregue', 'Cancelado'))
);
"""

TIPOS = {"PA": "Produto acabado", "MP": "Matéria-prima", "EMB": "Embalagem"}
STATUS_PEDIDO = ["Aberto", "Entregue", "Cancelado"]


def conectar():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def consultar(sql, params=()):
    with conectar() as con:
        return pd.read_sql_query(sql, con, params=params)


def executar(sql, params=()):
    with conectar() as con:
        con.execute(sql, params)


def executar_varios(sql, linhas):
    with conectar() as con:
        con.executemany(sql, linhas)


def iniciar():
    """Cria as tabelas e carrega os dados de exemplo se o banco estiver vazio."""
    with conectar() as con:
        con.executescript(SCHEMA)
        vazio = con.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 0
    if vazio:
        carregar_exemplo()


def carregar_exemplo():
    """Apaga tudo e recarrega a Panificadora Trigo Bom (empresa fictícia)."""
    with conectar() as con:
        for tabela in ("pedidos", "roteiro", "bom", "maquinas", "produtos"):
            con.execute(f"DELETE FROM {tabela}")
        con.execute("DELETE FROM sqlite_sequence")

        # codigo, nome, tipo, unidade, estoque, mínimo, lead time (dias), custo
        produtos = [
            ("PF500", "Pão de forma tradicional 500 g", "PA", "pct", 800, 300, 0, 0),
            ("PI500", "Pão de forma integral 500 g", "PA", "pct", 200, 150, 0, 0),
            ("BIS300", "Bisnaguinha 300 g", "PA", "pct", 400, 200, 0, 0),
            ("HB4", "Pão de hambúrguer c/ 4", "PA", "pct", 0, 100, 0, 0),
            ("TOR160", "Torrada tradicional 160 g", "PA", "pct", 600, 200, 0, 0),
            ("FAR", "Farinha de trigo tipo 1", "MP", "kg", 9000, 1000, 3, 3.40),
            ("FARI", "Farinha de trigo integral", "MP", "kg", 300, 200, 5, 5.10),
            ("ACU", "Açúcar refinado", "MP", "kg", 450, 100, 2, 4.20),
            ("FER", "Fermento biológico seco", "MP", "kg", 220, 20, 4, 28.00),
            ("SAL", "Sal refinado", "MP", "kg", 220, 30, 2, 1.90),
            ("GOR", "Gordura vegetal", "MP", "kg", 300, 60, 3, 12.50),
            ("LEI", "Leite em pó integral", "MP", "kg", 70, 10, 4, 32.00),
            ("GER", "Gergelim", "MP", "kg", 25, 5, 7, 22.00),
            ("EMB-PF", "Embalagem pão de forma", "EMB", "un", 15000, 3000, 6, 0.18),
            ("EMB-BIS", "Embalagem bisnaguinha", "EMB", "un", 7000, 1000, 6, 0.16),
            ("EMB-HB", "Embalagem hambúrguer", "EMB", "un", 7000, 1000, 6, 0.17),
            ("EMB-TOR", "Embalagem torrada", "EMB", "un", 5000, 800, 6, 0.21),
            ("CLIP", "Fecho plástico (clip)", "EMB", "un", 40000, 4000, 5, 0.02),
        ]
        con.executemany(
            "INSERT INTO produtos (codigo, nome, tipo, unidade, estoque_atual, "
            "estoque_minimo, lead_time_dias, custo_unit) VALUES (?,?,?,?,?,?,?,?)",
            produtos,
        )
        ids = dict(con.execute("SELECT codigo, id FROM produtos").fetchall())

        # Ficha técnica: quantidade de cada componente por pacote
        bom = {
            "PF500": {"FAR": 0.30, "ACU": 0.02, "FER": 0.006, "SAL": 0.005,
                      "GOR": 0.015, "EMB-PF": 1, "CLIP": 1},
            "PI500": {"FAR": 0.15, "FARI": 0.15, "ACU": 0.02, "FER": 0.006,
                      "SAL": 0.005, "GOR": 0.015, "EMB-PF": 1, "CLIP": 1},
            "BIS300": {"FAR": 0.17, "ACU": 0.03, "FER": 0.004, "SAL": 0.003,
                       "GOR": 0.02, "LEI": 0.01, "EMB-BIS": 1, "CLIP": 1},
            "HB4": {"FAR": 0.20, "ACU": 0.015, "FER": 0.005, "SAL": 0.004,
                    "GOR": 0.012, "GER": 0.003, "EMB-HB": 1, "CLIP": 1},
            "TOR160": {"FAR": 0.11, "ACU": 0.008, "FER": 0.002, "SAL": 0.002,
                       "GOR": 0.008, "EMB-TOR": 1},
        }
        con.executemany(
            "INSERT INTO bom (produto_id, componente_id, qtd_por_un) VALUES (?,?,?)",
            [(ids[pa], ids[c], q) for pa, comps in bom.items() for c, q in comps.items()],
        )

        maquinas = [("Linha 1 - Pão de forma", 16), ("Linha 2 - Pães especiais", 16),
                    ("Linha 3 - Torradas", 8)]
        con.executemany("INSERT INTO maquinas (nome, horas_dia) VALUES (?,?)", maquinas)
        maq = dict(con.execute("SELECT nome, id FROM maquinas").fetchall())

        roteiro = [
            ("PF500", "Linha 1 - Pão de forma", 400, 30),
            ("PI500", "Linha 1 - Pão de forma", 350, 45),
            ("BIS300", "Linha 2 - Pães especiais", 300, 40),
            ("HB4", "Linha 2 - Pães especiais", 280, 40),
            ("TOR160", "Linha 3 - Torradas", 200, 20),
        ]
        con.executemany(
            "INSERT INTO roteiro (produto_id, maquina_id, un_por_hora, setup_min) VALUES (?,?,?,?)",
            [(ids[p], maq[m], t, s) for p, m, t, s in roteiro],
        )

        # Datas relativas a hoje, para a demonstração funcionar em qualquer dia
        hoje = date.today()
        pedidos = [
            ("Supermercado Vila Nova", "PF500", 3000, 1),
            ("Rede Mercadão Oeste", "PF500", 6000, 1),
            ("Rede Mercadão Oeste", "PI500", 2500, 3),
            ("Mercearia São José", "BIS300", 1800, 2),
            ("Lanchonete Ponto Certo", "HB4", 2400, 2),
            ("Atacado Paraná Sul", "PF500", 8000, 5),
            ("Atacado Paraná Sul", "BIS300", 4000, 5),
            ("Hotel Lago Azul", "TOR160", 1500, 4),
            ("Supermercado Vila Nova", "TOR160", 2500, 6),
            ("Lanchonete Ponto Certo", "HB4", 3000, 6),
            ("Rede Mercadão Oeste", "PI500", 3000, 7),
            ("Mercearia São José", "PF500", 1200, -1),
        ]
        con.executemany(
            "INSERT INTO pedidos (cliente, produto_id, quantidade, data_entrega, status) "
            "VALUES (?,?,?,?,?)",
            [(c, ids[p], q, (hoje + timedelta(days=d)).isoformat(),
              "Entregue" if d < 0 else "Aberto") for c, p, q, d in pedidos],
        )


def carregar_tudo():
    """Lê todas as tabelas em DataFrames prontos para o cálculo."""
    produtos = consultar("SELECT * FROM produtos ORDER BY tipo DESC, codigo")
    pedidos = consultar(
        "SELECT pe.*, pr.codigo, pr.nome AS produto FROM pedidos pe "
        "JOIN produtos pr ON pr.id = pe.produto_id ORDER BY data_entrega, pe.id"
    )
    pedidos["data_entrega"] = pd.to_datetime(pedidos["data_entrega"]).dt.date
    return {
        "produtos": produtos,
        "pedidos": pedidos,
        "bom": consultar("SELECT * FROM bom"),
        "maquinas": consultar("SELECT * FROM maquinas ORDER BY nome"),
        "roteiro": consultar("SELECT * FROM roteiro"),
    }
