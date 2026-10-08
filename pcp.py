"""Regras de PCP: ordens de produção, MRP de materiais e programação por máquina.

Funções puras (recebem e devolvem DataFrames), fáceis de testar sem o Streamlit.
"""
import math
from datetime import date, datetime, time, timedelta

import pandas as pd

COLS_ORDENS = ["pedido_id", "cliente", "produto_id", "codigo", "produto",
               "quantidade", "data_entrega"]


# ---------------------------------------------------------------- 1. Ordens
def gerar_ordens(pedidos: pd.DataFrame, produtos: pd.DataFrame) -> pd.DataFrame:
    """Abate o estoque de produto acabado dos pedidos abertos, por data de entrega.
    O que sobrar vira ordem de produção."""
    abertos = pedidos[pedidos["status"] == "Aberto"].sort_values(["data_entrega", "id"])
    estoque = produtos.set_index("id")["estoque_atual"].to_dict()
    ordens = []
    for _, p in abertos.iterrows():
        saldo = estoque.get(p["produto_id"], 0)
        atendido = min(saldo, p["quantidade"])
        estoque[p["produto_id"]] = saldo - atendido
        falta = p["quantidade"] - atendido
        if falta > 0:
            ordens.append({"pedido_id": p["id"], "cliente": p["cliente"],
                           "produto_id": p["produto_id"], "codigo": p["codigo"],
                           "produto": p["produto"], "quantidade": falta,
                           "data_entrega": p["data_entrega"]})
    return pd.DataFrame(ordens, columns=COLS_ORDENS)


# ------------------------------------------------------------------ 2. MRP
def calcular_mrp(ordens: pd.DataFrame, bom: pd.DataFrame, produtos: pd.DataFrame,
                 hoje: date) -> pd.DataFrame:
    """Explode as ordens pela ficha técnica e compara com o estoque de cada material.

    - O material precisa estar disponível 1 dia antes da entrega do pedido.
    - Sugestão de compra = o que falta para cobrir a demanda e repor o estoque mínimo.
    - Data limite da compra = data da primeira falta − lead time do fornecedor.
    """
    materiais = produtos[produtos["tipo"] != "PA"]
    nec = ordens.merge(bom, on="produto_id") if not ordens.empty else pd.DataFrame()
    if not nec.empty:
        nec["qtd"] = nec["quantidade"] * nec["qtd_por_un"]
        nec["data_nec"] = nec["data_entrega"] - timedelta(days=1)

    linhas = []
    for _, m in materiais.iterrows():
        mov = (nec[nec["componente_id"] == m["id"]].groupby("data_nec")["qtd"].sum()
               .sort_index() if not nec.empty else pd.Series(dtype=float))
        demanda = float(mov.sum())
        acumulado = mov.cumsum()
        faltas = acumulado[acumulado > m["estoque_atual"]]
        primeira_falta = faltas.index[0] if not faltas.empty else None

        saldo_proj = m["estoque_atual"] - demanda
        sugestao = max(0.0, m["estoque_minimo"] - saldo_proj)
        sugestao = math.ceil(sugestao) if sugestao > 0 else 0

        if primeira_falta is not None:
            limite = primeira_falta - timedelta(days=int(m["lead_time_dias"]))
            status = "🔴 Falta - urgente" if limite <= hoje else "🟠 Falta - comprar"
        elif sugestao > 0:
            limite = hoje
            status = "🟡 Abaixo do mínimo"
        else:
            limite = None
            status = "🟢 OK"

        linhas.append({
            "codigo": m["codigo"], "material": m["nome"], "tipo": m["tipo"],
            "unidade": m["unidade"], "estoque": m["estoque_atual"],
            "minimo": m["estoque_minimo"], "demanda": round(demanda, 2),
            "saldo_projetado": round(saldo_proj, 2), "primeira_falta": primeira_falta,
            "sugestao_compra": sugestao, "comprar_ate": limite,
            "lead_time": int(m["lead_time_dias"]),
            "custo_compra": round(sugestao * m["custo_unit"], 2), "status": status,
        })
    ordem = {"🔴 Falta - urgente": 0, "🟠 Falta - comprar": 1,
             "🟡 Abaixo do mínimo": 2, "🟢 OK": 3}
    df = pd.DataFrame(linhas)
    return df.sort_values(by="status", key=lambda s: s.map(ordem), kind="stable")


# ------------------------------------------------------------ 3. Programação
def _janela(dt: datetime, hora_inicio: int, horas_dia: float):
    """Devolve (momento ajustado, fim da janela de trabalho) para um instante."""
    for d in (dt.date() - timedelta(days=1), dt.date()):
        ini = datetime.combine(d, time(hora_inicio))
        fim = ini + timedelta(hours=horas_dia)
        if ini <= dt < fim:
            return dt, fim
    ini = datetime.combine(dt.date(), time(hora_inicio))
    if dt >= ini:
        ini += timedelta(days=1)
    return ini, ini + timedelta(hours=horas_dia)


def _avancar(inicio: datetime, horas: float, hora_inicio: int, horas_dia: float):
    """Soma horas de trabalho respeitando o turno. Devolve (início real, fim)."""
    cursor, fim_janela = _janela(inicio, hora_inicio, horas_dia)
    comeco = cursor
    restante = horas
    while True:
        disponivel = (fim_janela - cursor).total_seconds() / 3600
        if restante <= disponivel + 1e-9:
            return comeco, cursor + timedelta(hours=restante)
        restante -= disponivel
        cursor, fim_janela = _janela(fim_janela, hora_inicio, horas_dia)


def programar(ordens: pd.DataFrame, roteiro: pd.DataFrame, maquinas: pd.DataFrame,
              inicio: datetime, hora_inicio: int = 6) -> pd.DataFrame:
    """Sequencia as ordens em cada máquina pela menor data de entrega (regra EDD).
    Ordens seguidas do mesmo produto em uma máquina não repetem o setup."""
    cols = ["maquina", "codigo", "produto", "cliente", "quantidade", "data_entrega",
            "setup_h", "producao_h", "inicio", "fim", "folga_h", "situacao"]
    if ordens.empty:
        return pd.DataFrame(columns=cols)
    o = (ordens.merge(roteiro, on="produto_id", how="left")
         .merge(maquinas.rename(columns={"id": "maquina_id", "nome": "maquina"}),
                on="maquina_id", how="left"))
    sem_roteiro = o[o["maquina_id"].isna()]
    o = o.dropna(subset=["maquina_id"])

    linhas = []
    for _, grupo in o.groupby("maquina", sort=True):
        grupo = grupo.sort_values(["data_entrega", "pedido_id"])
        cursor, anterior = inicio, None
        for _, r in grupo.iterrows():
            setup_h = 0.0 if r["produto_id"] == anterior else r["setup_min"] / 60
            prod_h = r["quantidade"] / r["un_por_hora"]
            ini, fim = _avancar(cursor, setup_h + prod_h, hora_inicio, r["horas_dia"])
            prazo = datetime.combine(r["data_entrega"], time(hora_inicio))
            folga = (prazo - fim).total_seconds() / 3600
            linhas.append({
                "maquina": r["maquina"], "codigo": r["codigo"], "produto": r["produto"],
                "cliente": r["cliente"], "quantidade": r["quantidade"],
                "data_entrega": r["data_entrega"], "setup_h": round(setup_h, 2),
                "producao_h": round(prod_h, 2), "inicio": ini, "fim": fim,
                "folga_h": round(folga, 1),
                "situacao": "🔴 Atrasa" if folga < 0 else ("🟡 Apertado" if folga < 8 else "🟢 No prazo"),
            })
            cursor, anterior = fim, r["produto_id"]

    for _, r in sem_roteiro.iterrows():
        linhas.append({"maquina": "— sem roteiro —", "codigo": r["codigo"],
                       "produto": r["produto"], "cliente": r["cliente"],
                       "quantidade": r["quantidade"], "data_entrega": r["data_entrega"],
                       "situacao": "⚪ Cadastre o roteiro"})
    return pd.DataFrame(linhas, columns=cols)


# ---------------------------------------------------------------- 4. Compras
def calcular_compras(produtos: pd.DataFrame, mrp: pd.DataFrame, dias_cobrir: int = 30) -> pd.DataFrame:
    """Controle de compras pelo consumo médio (o método da planilha, item a item).

    - Consumo diário = consumo dos últimos 90 dias ÷ 90.
    - Cobertura (dias) = estoque ÷ consumo diário.
    - Ponto de pedido = consumo diário × lead time + estoque mínimo (segurança).
    - Sugestão (só quando o estoque chega ao ponto de pedido) = o que leva o estoque a cobrir
      o lead time + `dias_cobrir` dias, mais o mínimo. Se os pedidos firmes (MRP) pedirem
      mais que isso, vale o maior.
    """
    mat = produtos[produtos["tipo"] != "PA"].copy()
    mat["consumo_dia"] = mat["consumo_90d"] / 90
    mat["cobertura_dias"] = (mat["estoque_atual"] / mat["consumo_dia"]).where(mat["consumo_dia"] > 0)
    mat["ponto_pedido"] = mat["consumo_dia"] * mat["lead_time_dias"] + mat["estoque_minimo"]
    alvo = mat["consumo_dia"] * (mat["lead_time_dias"] + dias_cobrir) + mat["estoque_minimo"]
    pelo_consumo = (alvo - mat["estoque_atual"]).clip(lower=0).where(
        mat["estoque_atual"] <= mat["ponto_pedido"], 0)
    pelo_mrp = mat["codigo"].map(mrp.set_index("codigo")["sugestao_compra"]).fillna(0)
    mat["sugestao"] = pd.concat([pelo_consumo, pelo_mrp], axis=1).max(axis=1).apply(math.ceil)
    mat["valor_compra"] = (mat["sugestao"] * mat["custo_unit"]).round(2)
    mat["status_mrp"] = mat["codigo"].map(mrp.set_index("codigo")["status"]).fillna("")

    def situacao(r):
        if r.status_mrp.startswith("🔴"):  # os pedidos firmes já furam o estoque
            return "🔴 Comprar já"
        if r.consumo_dia <= 0:
            return "⚪ Sem consumo"
        if r.cobertura_dias < r.lead_time_dias:
            return "🔴 Comprar já"
        if r.estoque_atual <= r.ponto_pedido or r.sugestao > 0:
            return "🟠 Pedir agora"
        if r.cobertura_dias < r.lead_time_dias + 15:
            return "🟡 Atenção"
        return "🟢 OK"

    mat["situacao"] = mat.apply(situacao, axis=1)
    ordem = {"🔴 Comprar já": 0, "🟠 Pedir agora": 1, "🟡 Atenção": 2, "🟢 OK": 3, "⚪ Sem consumo": 4}
    mat = mat.sort_values(["situacao", "cobertura_dias"],
                          key=lambda s: s.map(ordem) if s.name == "situacao" else s)
    return mat[["situacao", "fornecedor", "codigo", "nome", "unidade", "estoque_atual",
                "consumo_dia", "cobertura_dias", "lead_time_dias", "ponto_pedido",
                "sugestao", "custo_unit", "valor_compra"]].reset_index(drop=True)


def calcular_tudo(dados: dict, hoje: date, inicio: datetime | None = None,
                  hora_inicio: int = 6) -> dict:
    inicio = inicio or datetime.combine(hoje, time(hora_inicio))
    ordens = gerar_ordens(dados["pedidos"], dados["produtos"])
    return {
        "ordens": ordens,
        "mrp": calcular_mrp(ordens, dados["bom"], dados["produtos"], hoje),
        "programa": programar(ordens, dados["roteiro"], dados["maquinas"], inicio, hora_inicio),
    }
