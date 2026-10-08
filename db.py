"""Persistência em SQLite e dados de exemplo (duas empresas fictícias)."""
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
    custo_unit REAL NOT NULL DEFAULT 0,
    fornecedor TEXT NOT NULL DEFAULT '',
    consumo_90d REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS config (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
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


EXEMPLOS = {
    "panificadora": {"nome": "Panificadora Trigo Bom", "un": "pct",
                     "descricao": "panificadora · 5 produtos, 3 linhas"},
    "vasos": {"nome": "Vasos Oeste Plásticos", "un": "un",
              "descricao": "vasos plásticos injetados · reciclado próprio, 3 injetoras"},
}


def iniciar():
    """Cria as tabelas e carrega os dados de exemplo se o banco estiver vazio."""
    with conectar() as con:
        con.executescript(SCHEMA)
        colunas = {c[1] for c in con.execute("PRAGMA table_info(produtos)")}
        for col, tipo in (("fornecedor", "TEXT NOT NULL DEFAULT ''"),
                          ("consumo_90d", "REAL NOT NULL DEFAULT 0")):
            if col not in colunas:  # banco criado por uma versão antiga
                con.execute(f"ALTER TABLE produtos ADD COLUMN {col} {tipo}")
        vazio = con.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 0
    if vazio:
        carregar_exemplo(exemplo_atual())


def exemplo_atual() -> str:
    try:
        with conectar() as con:
            linha = con.execute("SELECT valor FROM config WHERE chave = 'exemplo'").fetchone()
        return linha[0] if linha and linha[0] in EXEMPLOS else "panificadora"
    except sqlite3.OperationalError:
        return "panificadora"


def empresa() -> dict:
    """Nome e unidade do produto acabado da empresa de exemplo carregada."""
    return EXEMPLOS[exemplo_atual()]


def carregar_exemplo(exemplo: str = "panificadora"):
    """Apaga tudo e recarrega uma das empresas fictícias de demonstração."""
    dados = _dados_panificadora() if exemplo == "panificadora" else _dados_vasos()
    with conectar() as con:
        for tabela in ("pedidos", "roteiro", "bom", "maquinas", "produtos"):
            con.execute(f"DELETE FROM {tabela}")
        con.execute("DELETE FROM sqlite_sequence")
        con.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('exemplo', ?)", (exemplo,))

        con.executemany(
            "INSERT INTO produtos (codigo, nome, tipo, unidade, estoque_atual, estoque_minimo, "
            "lead_time_dias, custo_unit, fornecedor, consumo_90d) VALUES (?,?,?,?,?,?,?,?,?,?)",
            dados["produtos"],
        )
        ids = dict(con.execute("SELECT codigo, id FROM produtos").fetchall())
        con.executemany(
            "INSERT INTO bom (produto_id, componente_id, qtd_por_un) VALUES (?,?,?)",
            [(ids[pa], ids[c], q) for pa, comps in dados["bom"].items() for c, q in comps.items()],
        )
        con.executemany("INSERT INTO maquinas (nome, horas_dia) VALUES (?,?)", dados["maquinas"])
        maq = dict(con.execute("SELECT nome, id FROM maquinas").fetchall())
        con.executemany(
            "INSERT INTO roteiro (produto_id, maquina_id, un_por_hora, setup_min) VALUES (?,?,?,?)",
            [(ids[p], maq[m], t, st) for p, m, t, st in dados["roteiro"]],
        )
        # Datas relativas a hoje, para a demonstração funcionar em qualquer dia
        hoje = date.today()
        con.executemany(
            "INSERT INTO pedidos (cliente, produto_id, quantidade, data_entrega, status) "
            "VALUES (?,?,?,?,?)",
            [(c, ids[p], q, (hoje + timedelta(days=d)).isoformat(),
              "Entregue" if d < 0 else "Aberto") for c, p, q, d in dados["pedidos"]],
        )


def _dados_panificadora() -> dict:
    """Panificadora Trigo Bom (empresa fictícia)."""
    # codigo, nome, tipo, unidade, estoque, mínimo, lead time (dias), custo, fornecedor, consumo 90 dias
    produtos = [
        ("PF500", "Pão de forma tradicional 500 g", "PA", "pct", 800, 300, 0, 0, "", 0),
        ("PI500", "Pão de forma integral 500 g", "PA", "pct", 200, 150, 0, 0, "", 0),
        ("BIS300", "Bisnaguinha 300 g", "PA", "pct", 400, 200, 0, 0, "", 0),
        ("HB4", "Pão de hambúrguer c/ 4", "PA", "pct", 0, 100, 0, 0, "", 0),
        ("TOR160", "Torrada tradicional 160 g", "PA", "pct", 600, 200, 0, 0, "", 0),
        ("FAR", "Farinha de trigo tipo 1", "MP", "kg", 9000, 1000, 3, 3.40, "Moinho Iguaçu", 27000),
        ("FARI", "Farinha de trigo integral", "MP", "kg", 300, 200, 5, 5.10, "Moinho Iguaçu", 2700),
        ("ACU", "Açúcar refinado", "MP", "kg", 450, 100, 2, 4.20, "Atacado Oeste", 1800),
        ("FER", "Fermento biológico seco", "MP", "kg", 220, 20, 4, 28.00, "Distribuidora Sul Insumos", 420),
        ("SAL", "Sal refinado", "MP", "kg", 220, 30, 2, 1.90, "Atacado Oeste", 400),
        ("GOR", "Gordura vegetal", "MP", "kg", 300, 60, 3, 12.50, "Distribuidora Sul Insumos", 1300),
        ("LEI", "Leite em pó integral", "MP", "kg", 70, 10, 4, 32.00, "Distribuidora Sul Insumos", 110),
        ("GER", "Gergelim", "MP", "kg", 25, 5, 7, 22.00, "Atacado Oeste", 45),
        ("EMB-PF", "Embalagem pão de forma", "EMB", "un", 15000, 3000, 6, 0.18, "Gráfica Flexo PR", 60000),
        ("EMB-BIS", "Embalagem bisnaguinha", "EMB", "un", 7000, 1000, 6, 0.16, "Gráfica Flexo PR", 15000),
        ("EMB-HB", "Embalagem hambúrguer", "EMB", "un", 7000, 1000, 6, 0.17, "Gráfica Flexo PR", 14000),
        ("EMB-TOR", "Embalagem torrada", "EMB", "un", 5000, 800, 6, 0.21, "Gráfica Flexo PR", 9000),
        ("CLIP", "Fecho plástico (clip)", "EMB", "un", 40000, 4000, 5, 0.02, "Atacado Oeste", 90000),
    ]
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
    maquinas = [("Linha 1 - Pão de forma", 16), ("Linha 2 - Pães especiais", 16),
                ("Linha 3 - Torradas", 8)]
    roteiro = [
        ("PF500", "Linha 1 - Pão de forma", 400, 30),
        ("PI500", "Linha 1 - Pão de forma", 350, 45),
        ("BIS300", "Linha 2 - Pães especiais", 300, 40),
        ("HB4", "Linha 2 - Pães especiais", 280, 40),
        ("TOR160", "Linha 3 - Torradas", 200, 20),
    ]
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
    return {"produtos": produtos, "bom": bom, "maquinas": maquinas,
            "roteiro": roteiro, "pedidos": pedidos}


def _dados_vasos() -> dict:
    """Vasos Oeste Plásticos: indústria fictícia de vasos injetados com reciclagem própria.

    Os números são ilustrativos (pesos, ciclos e custos aproximados), só para demonstração.
    """
    produtos = [
        ("VR3-PT", "Vaso redondo nº 3 preto", "PA", "un", 4000, 3000, 0, 0, "", 0),
        ("VR5-PT", "Vaso redondo nº 5 preto", "PA", "un", 1500, 2000, 0, 0, "", 0),
        ("VR5-CE", "Vaso redondo nº 5 cerâmica", "PA", "un", 800, 1000, 0, 0, "", 0),
        ("VR8-CE", "Vaso redondo nº 8 cerâmica", "PA", "un", 300, 400, 0, 0, "", 0),
        ("CQ-VD", "Cachepô quadrado médio verde", "PA", "un", 600, 500, 0, 0, "", 0),
        ("JD60-CE", "Jardineira 60 cm cerâmica", "PA", "un", 150, 300, 0, 0, "", 0),
        ("PP-REC", "PP reciclado em pellet (reciclagem interna)", "MP", "kg", 6500, 4000, 2,
         3.10, "Reciclagem interna", 76000),
        ("PP-VIR", "PP virgem injeção", "MP", "kg", 1800, 1000, 12, 8.90, "Petroquímica Sul", 9500),
        ("MB-PT", "Masterbatch preto", "MP", "kg", 180, 80, 7, 14.50, "Cores Brasil Masterbatch", 1150),
        ("MB-CE", "Masterbatch cerâmica (terracota)", "MP", "kg", 60, 40, 15, 22.00,
         "Cores Brasil Masterbatch", 690),
        ("MB-VD", "Masterbatch verde", "MP", "kg", 70, 30, 15, 21.00, "Cores Brasil Masterbatch", 260),
        ("ADT-UV", "Aditivo anti-UV", "MP", "kg", 45, 30, 20, 48.00, "Química Aditiva", 410),
        ("ETQ", "Etiqueta com código de barras", "EMB", "un", 60000, 20000, 10, 0.03,
         "Gráfica Flexo PR", 330000),
        ("FARDO", "Saco plástico de fardo (50 vasos)", "EMB", "un", 3000, 1000, 8, 0.45,
         "Embalagens Cascavel", 5800),
        ("CX-JD", "Caixa de papelão jardineira", "EMB", "un", 200, 300, 10, 2.80,
         "Embalagens Cascavel", 2700),
    ]
    bom = {
        "VR3-PT": {"PP-REC": 0.058, "MB-PT": 0.0012, "ADT-UV": 0.0003, "ETQ": 1, "FARDO": 0.02},
        "VR5-PT": {"PP-REC": 0.145, "MB-PT": 0.003, "ADT-UV": 0.0007, "ETQ": 1, "FARDO": 0.02},
        "VR5-CE": {"PP-REC": 0.120, "PP-VIR": 0.027, "MB-CE": 0.0045, "ADT-UV": 0.0008,
                   "ETQ": 1, "FARDO": 0.02},
        "VR8-CE": {"PP-REC": 0.360, "PP-VIR": 0.080, "MB-CE": 0.013, "ADT-UV": 0.0022,
                   "ETQ": 1, "FARDO": 0.02},
        "CQ-VD": {"PP-REC": 0.200, "PP-VIR": 0.040, "MB-VD": 0.007, "ADT-UV": 0.0012,
                  "ETQ": 1, "FARDO": 0.02},
        "JD60-CE": {"PP-REC": 0.330, "PP-VIR": 0.070, "MB-CE": 0.012, "ADT-UV": 0.002,
                    "ETQ": 1, "CX-JD": 1},
    }
    maquinas = [("Injetora 1 - 250 t", 22), ("Injetora 2 - 450 t", 22), ("Injetora 3 - 800 t", 22)]
    roteiro = [  # produto, máquina, unidades por hora, setup (troca de molde ou de cor) em minutos
        ("VR3-PT", "Injetora 1 - 250 t", 600, 90),
        ("VR5-PT", "Injetora 2 - 450 t", 320, 120),
        ("VR5-CE", "Injetora 2 - 450 t", 300, 45),
        ("CQ-VD", "Injetora 2 - 450 t", 220, 150),
        ("VR8-CE", "Injetora 3 - 800 t", 140, 150),
        ("JD60-CE", "Injetora 3 - 800 t", 90, 180),
    ]
    pedidos = [
        ("Garden Center Flora", "VR3-PT", 12000, 2),
        ("Rede Casa & Jardim", "VR5-PT", 14000, 2),
        ("Rede Casa & Jardim", "VR5-CE", 5000, 4),
        ("Agropecuária Oeste", "VR3-PT", 15000, 5),
        ("Viveiro Bom Plantio", "VR5-PT", 10000, 6),
        ("Floricultura Primavera", "CQ-VD", 3000, 4),
        ("Garden Center Flora", "VR8-CE", 2500, 5),
        ("Rede Casa & Jardim", "JD60-CE", 1800, 7),
        ("Agropecuária Oeste", "CQ-VD", 2500, 8),
        ("Viveiro Bom Plantio", "VR8-CE", 1500, 9),
        ("Floricultura Primavera", "VR5-CE", 4000, 10),
        ("Garden Center Flora", "VR3-PT", 6000, -2),
    ]
    return {"produtos": produtos, "bom": bom, "maquinas": maquinas,
            "roteiro": roteiro, "pedidos": pedidos}


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
