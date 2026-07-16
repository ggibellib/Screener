"""
Screener personalizado — dashboard estático de una sola pantalla
(sin sidebar, sin gráficos, con auto-refresh)
Autor: generado con Claude
"""

import re
import streamlit as st
import yfinance as yf
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Screener de Activos Financieros",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------

REFRESH_SECONDS = 300
CACHE_TTL = 300

AR_TICKERS = ["GGAL", "BMA", "BBAR", "YPF", "VIST", "CRESY"]  # ADRs en NYSE/NASDAQ

US_TICKERS = ["SPY", "^DJI", "QQQ"]
US_LABELS = {"SPY": "S&P 500 (SPY)", "^DJI": "Dow Jones", "QQQ": "Nasdaq 100 (QQQ)"}

CRYPTO_TICKERS = ["BTC-USD"]

COMMODITY_TICKERS = {
    "BZ=F": "Brent (petróleo)",
    "GC=F": "Oro",
    "SI=F": "Plata",
    "ZS=F": "Soja",
    "ZW=F": "Trigo",
    "ZC=F": "Maíz",
}

NOAL_TICKER = "NOAL.V"  # NOA Lithium Brines, TSXV

MEP_API_URL = "https://dolarapi.com/v1/ambito/dolares/bolsa"
RIESGO_PAIS_API_URL = "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais"
SMM_LITHIUM_URL = "https://www.metal.com/en/prices/202212050001"  # SMM Battery-Grade Li2CO3 Index, USD/mt

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

@st.cache_data(ttl=CACHE_TTL)
def get_yf_data(tickers: list[str], labels: dict | None = None) -> pd.DataFrame:
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


@st.cache_data(ttl=CACHE_TTL)
def get_mep() -> dict:
    try:
        r = requests.get(MEP_API_URL, timeout=10)
        r.raise_for_status()
        d = r.json()
        return {
            "Ticker": "MEP", "Nombre": "Dólar MEP (AL30/AL30D)",
            "Precio": d.get("venta"), "Variación %": d.get("variacion"),
        }
    except Exception:
        return {"Ticker": "MEP", "Nombre": "Dólar MEP (no disponible)", "Precio": None, "Variación %": None}


@st.cache_data(ttl=CACHE_TTL)
def get_riesgo_pais() -> dict:
    try:
        r = requests.get(RIESGO_PAIS_API_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data or len(data) < 2:
            return {"Ticker": "RP", "Nombre": "Riesgo País (EMBI+)", "Precio": None, "Variación %": None}
        data_sorted = sorted(data, key=lambda x: x.get("fecha", ""))
        last, prev = data_sorted[-1], data_sorted[-2]
        valor = last.get("valor")
        change_pct = None
        if valor is not None and prev.get("valor"):
            change_pct = (valor / prev["valor"] - 1) * 100
        return {"Ticker": "RP", "Nombre": "Riesgo País (EMBI+)", "Precio": valor, "Variación %": change_pct}
    except Exception:
        return {"Ticker": "RP", "Nombre": "Riesgo País (no disponible)", "Precio": None, "Variación %": None}


@st.cache_data(ttl=CACHE_TTL)
def get_lithium_carbonate() -> dict:
    """Precio del carbonato de litio (SMM Battery-Grade Li2CO3 Index, USD/mt),
    scrapeado de Shanghai Metal Market. Frágil por naturaleza (depende de que
    SMM no cambie el HTML de la página ni bloquee el request)."""
    base = {"Ticker": "LI2CO3", "Nombre": "Litio Carbonato (SMM Battery-Grade, USD/mt)"}
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        }
        r = requests.get(SMM_LITHIUM_URL, headers=headers, timeout=15)
        r.raise_for_status()
        text = BeautifulSoup(r.text, "html.parser").get_text(separator=" ")
        text = re.sub(r"\s+", " ", text)

        patterns = [
            r"VAT excluded[^\d]{0,20}([\d,]+\.\d+)[^\d]{0,20}USD/mt[^\d\+\-]{0,20}([+-][\d,]+\.\d+)\(([+-]?[\d.]+)%\)",
            r"Li₂CO₃\s*[≥>=]*\s*99\.5%\s*([\d,]+\.\d+)\s*[+-][\d,\.]+\s*\(([+-]?[\d.]+)%\)",
            r"SMM Battery-Grade Lithium Carbonate Index[^\d]{0,60}([\d,]+\.\d+)[^\(]{0,20}\(([+-]?[\d.]+)%\)",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                groups = m.groups()
                price = float(groups[0].replace(",", ""))
                pct = float(groups[-1])
                return {**base, "Precio": price, "Variación %": pct}

        return {**base, "Nombre": "Litio Carbonato (no disponible, revisar scraper)", "Precio": None, "Variación %": None}
    except Exception:
        return {**base, "Nombre": "Litio Carbonato (no disponible, revisar scraper)", "Precio": None, "Variación %": None}


# ----------------------------------------------------------------------------
# ESTILOS
# ----------------------------------------------------------------------------

st.markdown("""
<style>
    .block-container {padding-top: 0.8rem; padding-bottom: 0.5rem; max-width: 1500px;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stSidebarCollapsedControl"] {display: none;}

    .stApp {background-color: #0b0f19;}

    .header-sub {color: #64748b; font-size: 0.75rem; margin-bottom: 0.6rem;}

    .card {
        background: #111827; border: 1px solid; border-radius: 8px;
        margin-bottom: 0.6rem; overflow: hidden;
    }
    .card-header {
        padding: 6px 12px; font-weight: 700; font-size: 0.8rem;
        letter-spacing: 0.5px; color: #f1f5f9;
    }
    table.card-table {width: 100%; border-collapse: collapse; font-size: 0.78rem;}
    table.card-table th {
        text-align: left; color: #64748b; font-size: 0.62rem; font-weight: 600;
        letter-spacing: 0.4px; padding: 3px 12px; border-bottom: 1px solid #1f2937;
    }
    table.card-table td {
        padding: 4px 12px; border-bottom: 1px solid #1a2130; color: #e2e8f0;
        line-height: 1.2;
    }
    table.card-table tr:last-child td {border-bottom: none;}
    td.ticker {font-weight: 700; color: #f1f5f9; white-space: nowrap;}
    td.desc {color: #94a3b8;}
    td.price {text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap;}
    td.change {text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap;}
    .pos {color: #22c55e; font-weight: 700;}
    .neg {color: #ef4444; font-weight: 700;}
    .neutral {color: #64748b;}
</style>
""", unsafe_allow_html=True)

st.markdown(f'<meta http-equiv="refresh" content="{REFRESH_SECONDS}">', unsafe_allow_html=True)

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
    html += '<table class="card-table"><thead><tr><th>TICKER</th><th>DESCRIPCIÓN</th><th style="text-align:right">PRECIO</th><th style="text-align:right">VAR.</th></tr></thead><tbody>'
    for r in rows:
        price = fmt_price(r["Precio"])
        change = change_span(r["Variación %"])
        html += (
            f'<tr><td class="ticker">{r["Ticker"]}</td><td class="desc">{r["Nombre"]}</td>'
            f'<td class="price">{price}</td><td class="change">{change}</td></tr>'
        )
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------

col_sub, col_btn = st.columns([6, 1])
with col_sub:
    st.markdown(
        f'<div class="header-sub">Actualizado: {datetime.now().strftime("%d %b %Y, %H:%M")} · '
        f'Auto-refresh cada {REFRESH_SECONDS // 60} min</div>',
        unsafe_allow_html=True,
    )
with col_btn:
    if st.button("🔄 Refrescar ahora"):
        st.cache_data.clear()

# ----------------------------------------------------------------------------
# CARGA DE DATOS
# ----------------------------------------------------------------------------

fx_rows = [get_mep(), get_riesgo_pais()]
df_ar = get_yf_data(AR_TICKERS)
df_us = get_yf_data(US_TICKERS, labels=US_LABELS)
df_crypto = get_yf_data(CRYPTO_TICKERS)
df_comm = get_yf_data(list(COMMODITY_TICKERS.keys()), labels=COMMODITY_TICKERS)

df_noal = get_yf_data([NOAL_TICKER])
lithium_rows = [get_lithium_carbonate()] + df_noal.to_dict("records")

# ----------------------------------------------------------------------------
# LAYOUT: 3 columnas
# ----------------------------------------------------------------------------

col1, col2, col3 = st.columns(3)

with col1:
    render_card("🛢️", "COMMODITIES", "#f59e0b", df_comm.to_dict("records"))
    render_card("⚡", "LITIO", "#a78bfa", lithium_rows)

with col2:
    render_card("📈", "ACCIONES ARGENTINAS (ADRs)", "#22c55e", df_ar.to_dict("records"))

with col3:
    render_card("💱", "TIPO DE CAMBIO Y RIESGO PAÍS", "#22d3ee", fx_rows)
    render_card("🇺🇸", "ACCIONES / ÍNDICES EE.UU.", "#818cf8", df_us.to_dict("records"))
    render_card("₿", "CRIPTOMONEDAS", "#f7931a", df_crypto.to_dict("records"))
