"""
Screener personalizado — dashboard estilo tarjetas (sin sidebar, sin gráficos)
Autor: generado con Claude
"""

import streamlit as st
import yfinance as yf
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Screener de Activos Financieros",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------------------------------------------------------
# CONFIG: universo de activos (fijo, sin controles laterales)
# ----------------------------------------------------------------------------

# GGAL, BMA, BBAR, YPF, VIST y CRESY cotizan como ADRs en NYSE/NASDAQ.
AR_TICKERS = ["GGAL", "BMA", "BBAR", "YPF", "VIST", "CRESY"]

# ^DJI es el índice Dow Jones; SPY y QQQ son ETFs que replican S&P500 y Nasdaq100.
US_TICKERS = ["SPY", "^DJI", "QQQ"]
US_LABELS = {"SPY": "S&P 500 (SPY)", "^DJI": "Dow Jones", "QQQ": "Nasdaq 100 (QQQ)"}

CRYPTO_TICKERS = ["BTC-USD"]

COMMODITY_TICKERS = {
    "BZ=F": "Brent (petróleo)",
    "GC=F": "Oro",
    "SI=F": "Plata",
    "LIT": "Litio (ETF Global X Lithium)",
    "ZS=F": "Soja",
    "ZW=F": "Trigo",
    "ZC=F": "Maíz",
}

MEP_API_URL = "https://dolarapi.com/v1/dolares/bolsa"
RIESGO_PAIS_API_URL = "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo"

# ----------------------------------------------------------------------------
# FORMATO NUMÉRICO (es-AR: punto de miles, coma decimal)
# ----------------------------------------------------------------------------

def fmt_price(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    s = f"{val:+.2f}".replace(".", ",")
    return f"{s}%"


# ----------------------------------------------------------------------------
# FUNCIONES DE DATOS
# ----------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_yf_data(tickers: list[str], labels: dict | None = None) -> pd.DataFrame:
    """Trae ticker, nombre, precio y variación % vs cierre anterior.
    Usa siempre el histórico diario (Close): si el mercado está cerrado,
    'Precio' es el último cierre disponible y 'Variación %' es la variación
    de esa última rueda vs la rueda anterior."""
    rows = []
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            hist = tk.history(period="5d")
            if hist.empty or len(hist) < 2:
                rows.append({"Ticker": t, "Nombre": (labels or {}).get(t, t), "Precio": None, "Variación %": None})
                continue
            last_close = float(hist["Close"].iloc[-1])
            prev_close = float(hist["Close"].iloc[-2])
            if labels and t in labels:
                name = labels[t]
            else:
                try:
                    name = tk.info.get("shortName", t)
                except Exception:
                    name = t
            change_pct = (last_close / prev_close - 1) * 100
            rows.append({"Ticker": t, "Nombre": name, "Precio": last_close, "Variación %": change_pct})
        except Exception:
            rows.append({"Ticker": t, "Nombre": (labels or {}).get(t, t), "Precio": None, "Variación %": None})
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def get_mep() -> dict:
    try:
        r = requests.get(MEP_API_URL, timeout=10)
        r.raise_for_status()
        d = r.json()
        return {"Ticker": "MEP", "Nombre": "Dólar MEP (AL30/AL30D)", "Precio": d.get("venta"), "Variación %": None}
    except Exception:
        return {"Ticker": "MEP", "Nombre": "Dólar MEP (no disponible)", "Precio": None, "Variación %": None}


@st.cache_data(ttl=300)
def get_riesgo_pais() -> dict:
    try:
        r = requests.get(RIESGO_PAIS_API_URL, timeout=10)
        r.raise_for_status()
        d = r.json()
        return {"Ticker": "RP", "Nombre": "Riesgo País (EMBI+)", "Precio": d.get("valor"), "Variación %": None}
    except Exception:
        return {"Ticker": "RP", "Nombre": "Riesgo País (no disponible)", "Precio": None, "Variación %": None}


# ----------------------------------------------------------------------------
# ESTILOS
# ----------------------------------------------------------------------------

st.markdown("""
<style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stSidebarCollapsedControl"] {display: none;}

    .stApp {background-color: #0b0f19;}

    .header-title {
        font-size: 1.7rem; font-weight: 800; color: #f1f5f9;
        letter-spacing: 0.5px; margin-bottom: 0.1rem;
    }
    .header-sub {color: #64748b; font-size: 0.85rem; margin-bottom: 1.2rem;}

    .metric-tile {
        background: #111827; border: 1px solid #1f2937; border-radius: 10px;
        padding: 12px 16px; margin-bottom: 1.2rem;
    }
    .metric-label {color: #94a3b8; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.5px;}
    .metric-value {color: #f1f5f9; font-size: 1.4rem; font-weight: 700; margin-top: 2px;}
    .metric-change {font-size: 0.95rem; font-weight: 700; margin-top: 2px;}

    .card {
        background: #111827; border: 1px solid; border-radius: 10px;
        margin-bottom: 1.2rem; overflow: hidden;
    }
    .card-header {
        padding: 10px 16px; font-weight: 700; font-size: 0.95rem;
        letter-spacing: 0.5px; color: #f1f5f9;
    }
    table.card-table {width: 100%; border-collapse: collapse; font-size: 0.88rem;}
    table.card-table th {
        text-align: left; color: #64748b; font-size: 0.72rem; font-weight: 600;
        letter-spacing: 0.5px; padding: 6px 16px; border-bottom: 1px solid #1f2937;
    }
    table.card-table td {
        padding: 8px 16px; border-bottom: 1px solid #1a2130; color: #e2e8f0;
    }
    table.card-table tr:last-child td {border-bottom: none;}
    td.ticker {font-weight: 700; color: #f1f5f9;}
    td.desc {color: #94a3b8;}
    td.price {text-align: right; font-variant-numeric: tabular-nums;}
    td.change {text-align: right; font-variant-numeric: tabular-nums;}
    .pos {color: #22c55e; font-weight: 700;}
    .neg {color: #ef4444; font-weight: 700;}
    .neutral {color: #64748b;}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# RENDER HELPERS
# ----------------------------------------------------------------------------

def change_span(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return '<span class="neutral">—</span>'
    cls = "pos" if val >= 0 else "neg"
    arrow = "▲" if val >= 0 else "▼"
    return f'<span class="{cls}">{arrow} {fmt_pct(val)}</span>'


def render_card(icon: str, title: str, accent: str, rows: list[dict]):
    html = f'<div class="card" style="border-color:{accent}55">'
    html += f'<div class="card-header" style="background:{accent}1a; border-bottom:1px solid {accent}40;">{icon} {title}</div>'
    html += '<table class="card-table"><thead><tr><th>TICKER</th><th>DESCRIPCIÓN</th><th style="text-align:right">ÚLTIMO PRECIO</th><th style="text-align:right">VAR. DIARIA</th></tr></thead><tbody>'
    for r in rows:
        price = fmt_price(r["Precio"])
        change = change_span(r["Variación %"])
        html += (
            f'<tr><td class="ticker">{r["Ticker"]}</td><td class="desc">{r["Nombre"]}</td>'
            f'<td class="price">{price}</td><td class="change">{change}</td></tr>'
        )
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)


def render_metric_tile(label: str, row: dict):
    change = row["Variación %"]
    cls = "neutral" if change is None or pd.isna(change) else ("pos" if change >= 0 else "neg")
    arrow = "" if change is None or pd.isna(change) else ("▲ " if change >= 0 else "▼ ")
    html = f"""
    <div class="metric-tile">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{fmt_price(row["Precio"])}</div>
        <div class="metric-change {cls}">{arrow}{fmt_pct(change)}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------

col_title, col_btn = st.columns([6, 1])
with col_title:
    st.markdown('<div class="header-title">📊 SCREENER DE ACTIVOS FINANCIEROS</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-sub">Actualizado: {datetime.now().strftime("%d %b %Y, %H:%M")}</div>', unsafe_allow_html=True)
with col_btn:
    if st.button("🔄 Refrescar"):
        st.cache_data.clear()

# ----------------------------------------------------------------------------
# TOP STRIP: SPY / DOW / QQQ
# ----------------------------------------------------------------------------

df_us = get_yf_data(US_TICKERS, labels=US_LABELS)
tiles = st.columns(len(US_TICKERS))
for col, (_, row) in zip(tiles, df_us.iterrows()):
    with col:
        render_metric_tile(row["Nombre"], row)

# ----------------------------------------------------------------------------
# CARDS (2 columnas)
# ----------------------------------------------------------------------------

left, right = st.columns(2)

with left:
    fx_rows = [get_mep(), get_riesgo_pais()]
    render_card("💱", "TIPO DE CAMBIO Y RIESGO PAÍS", "#22d3ee", fx_rows)

    df_ar = get_yf_data(AR_TICKERS)
    render_card("📈", "ACCIONES ARGENTINAS (ADRs)", "#22c55e", df_ar.to_dict("records"))

    df_crypto = get_yf_data(CRYPTO_TICKERS)
    render_card("₿", "CRIPTOMONEDAS", "#f7931a", df_crypto.to_dict("records"))

with right:
    df_comm = get_yf_data(list(COMMODITY_TICKERS.keys()), labels=COMMODITY_TICKERS)
    render_card("🛢️", "COMMODITIES", "#f59e0b", df_comm.to_dict("records"))

st.caption(
    "Fuentes: Yahoo Finance (ADRs, índices, ETFs, cripto, commodities) vía yfinance · "
    "dolarapi.com (Dólar MEP) · ArgentinaDatos API (Riesgo País, EMBI+ JP Morgan). "
    "Precio y variación reflejan la última rueda con cierre disponible. "
    "GGAL, BMA, BBAR, YPF, VIST y CRESY se muestran como ADRs (USD), no como sus equivalentes en pesos de BYMA."
)
