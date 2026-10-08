"""Itens compartilhados entre as páginas."""
from datetime import date

import streamlit as st

import db
import pcp

FMT_DATA = "DD/MM/YYYY"
FMT_DATAHORA = "DD/MM HH:mm"


def configurar():
    """Garante que o banco existe (a página pode ser aberta direto pela URL)."""
    db.iniciar()


def contexto():
    """Carrega os dados e roda o cálculo de PCP para hoje."""
    dados = db.carregar_tudo()
    return dados, pcp.calcular_tudo(dados, date.today())


def un() -> str:
    """Unidade do produto acabado da empresa de exemplo (pct, un...)."""
    return db.empresa()["un"]


def num(valor, casas=0):
    """Formata número no padrão brasileiro."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")
