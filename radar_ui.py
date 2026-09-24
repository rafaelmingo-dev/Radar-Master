from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf


PERIODS = {
    "3M": "3mo",
    "6M": "6mo",
    "1A": "1y",
    "2A": "2y",
    "5A": "5y",
}


def fmt_money(value: Any) -> str:
    try:
        x = float(value)
        if np.isfinite(x):
            return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        pass
    return "n/d"


def fmt_pct(value: Any, decimals: int = 1) -> str:
    try:
        x = float(value)
        if np.isfinite(x):
            return f"{x * 100:.{decimals}f}%".replace(".", ",")
    except Exception:
        pass
    return "n/d"


def fmt_score(value: Any) -> str:
    try:
        x = float(value)
        if np.isfinite(x):
            return f"{x:.1f}/100".replace(".", ",")
    except Exception:
        pass
    return "n/d"


def app_css():
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2.0rem; padding-bottom: 3rem; max-width: 1500px;}
        h1, h2, h3 {letter-spacing: -0.02em;}
        .radar-subtitle {color:#aab0bb; font-size:1.02rem; margin-top:-0.65rem; margin-bottom:1.0rem;}
        .radar-meta {color:#8c94a3; font-size:.92rem;}
        .radar-card {border:1px solid #2f3542; border-radius:12px; padding:14px 16px; min-height:92px; background:#111722;}
        .radar-card .n {font-size:1.65rem; font-weight:800; line-height:1.1;}
        .radar-card .t {font-size:.83rem; color:#aeb5c1; margin-top:6px;}
        .badge {display:inline-block; padding:5px 9px; border-radius:999px; font-size:.82rem; font-weight:700; margin-right:5px; margin-bottom:4px;}
        .green {background:#113e2b; color:#72e5a7; border:1px solid #1f6b4c;}
        .yellow {background:#443610; color:#f3d36a; border:1px solid #705b19;}
        .purple {background:#31244f; color:#cbb5ff; border:1px solid #58418c;}
        .red {background:#4a2026; color:#ff9aa8; border:1px solid #76323b;}
        .gray {background:#262b35; color:#c8cdd6; border:1px solid #3a404d;}
        .blue {background:#142f4b; color:#8ecbff; border:1px solid #24527e;}
        .decision-box {border-left:4px solid #ff344d; border-radius:8px; padding:12px 14px; background:#111722; margin:8px 0 14px 0;}
        div[data-testid="stMetric"] {background:#111722; border:1px solid #2b313d; padding:10px 12px; border-radius:10px;}
        div[data-testid="stDataFrame"] {border:1px solid #2b313d; border-radius:9px; overflow:hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _frame(snapshot: dict, key: str) -> pd.DataFrame:
    value = snapshot.get("tables", {}).get(key)
    return value.copy() if isinstance(value, pd.DataFrame) else pd.DataFrame()


def _ensure_asset_column(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "Ativo" not in out.columns:
        idx_name = out.index.name or "Ativo"
        out = out.reset_index().rename(columns={idx_name: "Ativo", "index": "Ativo"})
    return out


def main_table(snapshot: dict) -> pd.DataFrame:
    radar = _frame(snapshot, "LONG_TERM_PORTFOLIO_RADAR")
    decisions = _frame(snapshot, "ASSET_DECISION_TABLE")
    radar = _ensure_asset_column(radar)
    decisions = _ensure_asset_column(decisions)
    if radar.empty:
        return pd.DataFrame()

    cols = [
        "Ativo", "Quality Score", "Classe de qualidade", "Preço atual",
        "Alvo validado 12m", "Upside/Downside", "Valuation Status",
        "Confiança", "Status de Carteira",
    ]
    out = radar[[c for c in cols if c in radar.columns]].copy()
    if not decisions.empty and "Conclusão direta" in decisions.columns:
        out = out.merge(decisions[["Ativo", "Conclusão direta"]], on="Ativo", how="left")
    return out


def _status_counts(df: pd.DataFrame) -> dict[str, int]:
    status = df.get("Status de Carteira", pd.Series(dtype=str)).astype(str)
    return {
        "priority": int(status.str.contains("CANDIDATO PRIORITÁRIO", regex=False).sum()),
        "wait": int(status.str.contains("AGUARDAR PREÇO", regex=False).sum()),
        "uncertain": int(status.str.contains("VALUATION INCONCLUSIVO", regex=False).sum()),
        "monitor": int(status.str.contains("MONITORAR", regex=False).sum()),
        "out": int(status.str.contains("FORA DA LISTA", regex=False).sum()),
    }


def render_summary_cards(df: pd.DataFrame):
    c = _status_counts(df)
    labels = [
        ("priority", "⭐ Candidatos prioritários"),
        ("wait", "🟡 Bons ativos — aguardar preço"),
        ("uncertain", "🟣 Bons ativos — valuation inconclusivo"),
        ("monitor", "🔎 Monitorar"),
        ("out", "🔴 Fora da prioridade"),
    ]
    cols = st.columns(5)
    for col, (key, title) in zip(cols, labels):
        with col:
            st.markdown(
                f'<div class="radar-card"><div class="n">{c[key]}</div><div class="t">{title}</div></div>',
                unsafe_allow_html=True,
            )


def _table_display(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "Quality Score" in out.columns:
        out["Quality Score"] = out["Quality Score"].map(fmt_score)
    if "Preço atual" in out.columns:
        out["Preço atual"] = out["Preço atual"].map(fmt_money)
    if "Alvo validado 12m" in out.columns:
        out["Alvo validado 12m"] = out["Alvo validado 12m"].map(fmt_money)
    if "Upside/Downside" in out.columns:
        out["Upside/Downside"] = out["Upside/Downside"].map(fmt_pct)
    return out


def render_selectable_table(df: pd.DataFrame, key: str = "main_radar") -> str | None:
    if df.empty:
        st.info("Nenhum dado disponível. Atualize o Radar.")
        return None
    shown = _table_display(df)
    event = st.dataframe(
        shown,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=key,
        height=min(760, 42 + 35 * max(len(shown), 1)),
    )
    rows = []
    try:
        rows = list(event.selection.rows)
    except Exception:
        pass
    if rows:
        pos = rows[0]
        if 0 <= pos < len(df):
            return str(df.iloc[pos]["Ativo"])
    return None


def asset_row(snapshot: dict, symbol: str) -> dict:
    radar = _ensure_asset_column(_frame(snapshot, "LONG_TERM_PORTFOLIO_RADAR"))
    if not radar.empty:
        hit = radar[radar["Ativo"].astype(str) == symbol]
        if not hit.empty:
            return hit.iloc[0].to_dict()
    return {}


def decision_row(snapshot: dict, symbol: str) -> dict:
    df = _ensure_asset_column(_frame(snapshot, "ASSET_DECISION_TABLE"))
    if not df.empty:
        hit = df[df["Ativo"].astype(str) == symbol]
        if not hit.empty:
            return hit.iloc[0].to_dict()
    return {}


def method_row(snapshot: dict, symbol: str) -> dict:
    df = _ensure_asset_column(_frame(snapshot, "METHOD_DISAGREEMENT_AUDIT"))
    if not df.empty:
        hit = df[df["Ativo"].astype(str) == symbol]
        if not hit.empty:
            return hit.iloc[0].to_dict()
    return {}


def quality_row(snapshot: dict, symbol: str) -> dict:
    df = _ensure_asset_column(_frame(snapshot, "QUALITY_SCORE_TABLE"))
    if not df.empty:
        hit = df[df["Ativo"].astype(str) == symbol]
        if not hit.empty:
            return hit.iloc[0].to_dict()
    return {}


def result_for(snapshot: dict, symbol: str) -> dict:
    if symbol in snapshot.get("results_fcff", {}):
        return snapshot["results_fcff"][symbol]
    if symbol in snapshot.get("results_equity", {}):
        return snapshot["results_equity"][symbol]
    return {}


def _badge_class(text: str) -> str:
    t = text.upper()
    if "ATRATIVO" in t or "CANDIDATO" in t:
        return "green"
    if "CARO" in t or "AGUARDAR" in t:
        return "yellow"
    if "INCONCLUS" in t or "MISTO" in t:
        return "purple"
    if "FORA" in t or "ABAIXO" in t:
        return "red"
    if "EXCELENTE" in t or "FORTE" in t:
        return "blue"
    return "gray"


def badge(text: str):
    if not text:
        return
    st.markdown(
        f'<span class="badge {_badge_class(text)}">{text}</span>',
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=900, show_spinner=False)
def load_market_history(ticker: str, period: str) -> pd.DataFrame:
    if not ticker:
        return pd.DataFrame()
    hist = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False, actions=False)
    if hist is None or hist.empty:
        return pd.DataFrame()
    hist = hist.copy()
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = [c[0] if isinstance(c, tuple) else c for c in hist.columns]
    needed = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in hist.columns for c in needed):
        return pd.DataFrame()
    hist = hist[needed].dropna(subset=["Open", "High", "Low", "Close"])
    return hist


def _method_targets(method: dict) -> list[tuple[str, float]]:
    targets = []
    names = [
        (method.get("Método principal"), method.get("Principal 12m")),
        ("P/L 12m", method.get("P/L 12m")),
        (method.get("Método secundário 2"), method.get("Secundário 2 12m")),
        ("Dividend Yield 12m", method.get("Dividend Yield 12m")),
    ]
    seen = set()
    for name, value in names:
        if not name or name in seen:
            continue
        try:
            x = float(value)
        except Exception:
            continue
        if np.isfinite(x):
            targets.append((str(name), x))
            seen.add(str(name))
    return targets


def render_candlestick(snapshot: dict, symbol: str):
    meta = snapshot.get("assets", {}).get(symbol, {})
    ticker = meta.get("ticker")
    radar = asset_row(snapshot, symbol)
    method = method_row(snapshot, symbol)

    controls = st.columns([1.1, 1.1, 3.8])
    with controls[0]:
        period_label = st.selectbox("Período", list(PERIODS.keys()), index=2, key=f"period_{symbol}")
    with controls[1]:
        show_methods = st.toggle("Mostrar métodos", value=False, key=f"methods_{symbol}")
    with controls[2]:
        st.caption("Candles e volume são apenas apoio visual; a conclusão do Radar continua vindo de qualidade + valuation + confiança.")

    with st.spinner(f"Carregando gráfico de {symbol}..."):
        hist = load_market_history(ticker, PERIODS[period_label])

    if hist.empty:
        st.warning("Não foi possível carregar o histórico de preço deste ativo agora.")
        return

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.76, 0.24], vertical_spacing=0.03,
    )
    fig.add_trace(
        go.Candlestick(
            x=hist.index,
            open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"],
            name=symbol,
            increasing_line_color="#19c77b",
            decreasing_line_color="#ff4d5e",
            increasing_fillcolor="#19c77b",
            decreasing_fillcolor="#ff4d5e",
        ),
        row=1, col=1,
    )

    volume_colors = np.where(hist["Close"] >= hist["Open"], "#3fbf8a", "#db5967")
    fig.add_trace(
        go.Bar(x=hist.index, y=hist["Volume"], marker_color=volume_colors, opacity=0.55, name="Volume"),
        row=2, col=1,
    )

    x0, x1 = hist.index.min(), hist.index.max()
    lines = []
    price = radar.get("Preço atual")
    target = radar.get("Alvo validado 12m")
    try:
        if np.isfinite(float(price)):
            lines.append(("Preço atual", float(price), "#d5dae3", "dot"))
    except Exception:
        pass
    try:
        if np.isfinite(float(target)):
            lines.append(("Alvo final 12m", float(target), "#ffb020", "dash"))
    except Exception:
        pass

    if show_methods:
        palette = ["#ab8cff", "#56b4ff", "#e78ac3", "#8bd17c"]
        for i, (name, value) in enumerate(_method_targets(method)):
            lines.append((name, value, palette[i % len(palette)], "dash"))

    for name, value, color, dash in lines:
        fig.add_trace(
            go.Scatter(
                x=[x0, x1], y=[value, value], mode="lines",
                line=dict(color=color, width=1.5, dash=dash), name=f"{name}: {fmt_money(value)}",
                hoverinfo="skip",
            ),
            row=1, col=1,
        )

    fig.update_layout(
        height=620,
        margin=dict(l=10, r=10, t=35, b=10),
        paper_bgcolor="#0b0f17",
        plot_bgcolor="#0b0f17",
        font=dict(color="#e6e9ef"),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(
        gridcolor="#202632", showgrid=True,
        rangebreaks=[dict(bounds=["sat", "mon"])],
    )
    fig.update_yaxes(gridcolor="#202632", showgrid=True, row=1, col=1, title_text="R$ por ação")
    fig.update_yaxes(gridcolor="#202632", showgrid=True, row=2, col=1, title_text="Volume")
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def render_asset_detail(snapshot: dict, symbol: str, compact: bool = False):
    if not symbol:
        return
    meta = snapshot.get("assets", {}).get(symbol, {})
    radar = asset_row(snapshot, symbol)
    decision = decision_row(snapshot, symbol)
    quality = quality_row(snapshot, symbol)
    result = result_for(snapshot, symbol)

    st.subheader(f"{symbol} — {meta.get('name', symbol)}")
    badge(str(radar.get("Classe de qualidade", "")))
    badge(str(radar.get("Valuation Status", "")))
    badge(str(radar.get("Status de Carteira", "")))

    metrics = st.columns(5)
    metrics[0].metric("Preço atual", fmt_money(radar.get("Preço atual")))
    metrics[1].metric("Alvo 12m", fmt_money(radar.get("Alvo validado 12m")))
    metrics[2].metric("Upside/Downside", fmt_pct(radar.get("Upside/Downside")))
    metrics[3].metric("Quality Score", fmt_score(radar.get("Quality Score")))
    metrics[4].metric("Confiança", str(radar.get("Confiança", "n/d")))

    conclusion = decision.get("Conclusão direta") or radar.get("Motivo resumido") or ""
    action = decision.get("O que fazer") or ""
    if conclusion:
        st.markdown(
            f'<div class="decision-box"><b>Leitura do Radar:</b> {conclusion}<br><b>Próxima ação:</b> {action}</div>',
            unsafe_allow_html=True,
        )

    render_candlestick(snapshot, symbol)

    if compact:
        return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Qualidade — evidências")
        st.write(decision.get("Motivo da qualidade — números", radar.get("Motivo resumido", "n/d")))
        st.caption("A classe forte/excelente é relativa ao grupo econômico do universo W1, exatamente como calculado pelo script.")
    with c2:
        st.markdown("#### Preço/valuation — evidências")
        st.write(decision.get("Motivo do preço — números", "n/d"))

    method = method_row(snapshot, symbol)
    if method:
        st.markdown("#### Métodos de valuation")
        method_df = pd.DataFrame([
            {"Método": method.get("Método principal", "Principal"), "Alvo 12m": method.get("Principal 12m")},
            {"Método": "P/L 12m", "Alvo 12m": method.get("P/L 12m")},
            {"Método": method.get("Método secundário 2", "Secundário 2"), "Alvo 12m": method.get("Secundário 2 12m")},
            {"Método": "Dividend Yield 12m", "Alvo 12m": method.get("Dividend Yield 12m")},
        ])
        method_df["Alvo 12m"] = method_df["Alvo 12m"].map(fmt_money)
        st.dataframe(method_df, use_container_width=True, hide_index=True)
        st.caption(str(method.get("Leitura diagnóstica", "")))

    hist = result.get("hist")
    if isinstance(hist, pd.DataFrame) and not hist.empty:
        with st.expander("Histórico fundamental 2021–2025"):
            st.dataframe(hist, use_container_width=True)

    if quality:
        with st.expander("Componentes do Quality Score"):
            qcols = [k for k in quality.keys() if str(k).startswith("Q — ")]
            qdf = pd.DataFrame(
                [{"Dimensão": k.replace("Q — ", ""), "Pontuação": quality.get(k)} for k in qcols]
            )
            if not qdf.empty:
                qdf["Pontuação"] = qdf["Pontuação"].map(fmt_score)
                st.dataframe(qdf, use_container_width=True, hide_index=True)


def render_method_audit(snapshot: dict):
    df = _ensure_asset_column(_frame(snapshot, "METHOD_DISAGREEMENT_AUDIT"))
    if df.empty:
        st.info("Auditoria de métodos indisponível.")
        return
    cols = [
        "Ativo", "Preço atual", "Método principal", "Principal 12m", "P/L 12m",
        "Método secundário 2", "Secundário 2 12m", "Dividend Yield 12m",
        "Alvo final atual 12m", "Leitura diagnóstica",
    ]
    show = df[[c for c in cols if c in df.columns]].copy()
    for c in ["Preço atual", "Principal 12m", "P/L 12m", "Secundário 2 12m", "Dividend Yield 12m", "Alvo final atual 12m"]:
        if c in show.columns:
            show[c] = show[c].map(fmt_money)
    st.dataframe(show, use_container_width=True, hide_index=True, height=720)
