from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from master_core import (
    carregar_valuation_master, carregar_garch_master, carregar_connors_master,
    construir_radar_mestre, executar_valuation, executar_garch, limpar_cache_connors,
)

st.set_page_config(page_title="Radar Mestre", page_icon="🎯", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2.2rem; max-width: 1750px;}
.small-note {color:#aeb6c2;font-size:.93rem;line-height:1.45;}
div[data-testid="stDataFrame"] {border:1px solid #2b313d;border-radius:9px;overflow:hidden;}
</style>
""", unsafe_allow_html=True)

def fmt_pct(v, decimals=1):
    try:
        x=float(v)
        if not np.isfinite(x): return "N/D"
        # Valuation usa razão decimal; GARCH/percentil já chegam em pontos percentuais.
        return f"{x:.{decimals}f}%".replace(".",",")
    except Exception:
        return "N/D"

def fmt_pct_ratio(v, decimals=1):
    try:
        x=float(v)
        if not np.isfinite(x): return "N/D"
        return f"{x*100:.{decimals}f}%".replace(".",",")
    except Exception:
        return "N/D"

def fmt_num(v, decimals=2):
    try:
        x=float(v)
        if not np.isfinite(x): return "N/D"
        return f"{x:.{decimals}f}".replace(".",",")
    except Exception:
        return "N/D"

def css_crsi(v):
    try:
        x=float(v)
    except Exception:
        return ""
    if x < 20: return "background-color:#184a35;color:#f6fff9;font-weight:700;"
    if x > 80: return "background-color:#573036;color:#fff8f8;font-weight:700;"
    return ""

def css_confluencia(v):
    try:
        x=float(v)
    except Exception:
        return ""
    if np.isfinite(x) and x < 1.0:
        return "background-color:#184a35;color:#f6fff9;font-weight:700;"
    return ""

def css_valuation(v):
    t=str(v).upper()
    if "ATRATIVO" in t: return "background-color:#184a35;color:#f6fff9;font-weight:700;"
    if "CARO" in t: return "background-color:#573036;color:#fff8f8;font-weight:700;"
    return ""

st.title("RADAR MESTRE")
st.caption("Valuation + GARCH × GEX + Connors RSI. Cada motor permanece independente; esta tela apenas consolida as saídas por ticker, sem criar score novo nem recalcular as metodologias.")

nav1,nav2,nav3 = st.columns(3)
with nav1: st.page_link("pages/01_Valuation.py", label="Abrir Valuation", icon="📊", use_container_width=True)
with nav2: st.page_link("pages/02_GARCH_GEX.py", label="Abrir GARCH × GEX", icon="📡", use_container_width=True)
with nav3: st.page_link("pages/03_Connors_RSI.py", label="Abrir Connors RSI", icon="📈", use_container_width=True)

st.divider()

# Atualizações independentes: não misturam os pipelines.
u1,u2,u3,u4 = st.columns([1.4,1.4,1.4,2.8])
with u1:
    if st.button("🔄 Valuation", use_container_width=True):
        with st.spinner("Executando Valuation completo..."):
            ok,msg=executar_valuation()
        (st.success if ok else st.error)(msg)
        if ok: st.rerun()
with u2:
    if st.button("🔄 GARCH × GEX", use_container_width=True):
        with st.spinner("Executando B3/GEX/GARCH/confluências..."):
            ok,msg=executar_garch()
        (st.success if ok else st.error)(msg)
        if ok: st.rerun()
with u3:
    if st.button("🔄 Connors", use_container_width=True):
        limpar_cache_connors(); st.rerun()
with u4:
    st.caption("Os botões executam os mesmos motores dos painéis originais. GARCH × GEX e Valuation preservam o último cache/snapshot válido em caso de falha.")

with st.spinner("Carregando as três bases..."):
    valuation, val_snapshot, val_erro = carregar_valuation_master()
    garch, garch_payload, garch_erro = carregar_garch_master()
    connors, connors_meta, connors_erro = carregar_connors_master()

status_cols=st.columns(3)
status_cols[0].metric("Valuation", "OK" if val_erro is None else "SEM BASE")
status_cols[1].metric("GARCH × GEX", "OK" if garch_erro is None else "SEM BASE")
status_cols[2].metric("Connors RSI", "OK" if connors_erro is None else "ERRO")
if val_erro: st.caption(f"Valuation: {val_erro}")
if garch_erro: st.caption(f"GARCH × GEX: {garch_erro}")
if connors_erro: st.caption(f"Connors: {connors_erro}")

master=construir_radar_mestre(valuation,garch,connors)
if master.empty:
    st.warning("Ainda não há dados suficientes para montar o Radar Mestre. Atualize os motores acima.")
    st.stop()

st.subheader("Visão integrada")
resumo_cols=[
    "Ativo","Valuation final","Qualidade para carteira","Upside/Downside",
    "30D · Confluência %","30D · Dist Preço→Zona %","30D · Dentro da zona",
    "90D · Confluência %","90D · Dist Preço→Zona %","90D · Dentro da zona",
    "180D · Confluência %","180D · Dist Preço→Zona %","180D · Dentro da zona",
    "CRSI confirmado","Percentil CRSI 1A","Evento confirmado",
]
resumo=master[[c for c in resumo_cols if c in master.columns]].copy()
formatters={}
if "Upside/Downside" in resumo.columns: formatters["Upside/Downside"]=lambda x: fmt_pct_ratio(x,1)
for c in ["30D · Confluência %","30D · Dist Preço→Zona %","90D · Confluência %","90D · Dist Preço→Zona %","180D · Confluência %","180D · Dist Preço→Zona %","Percentil CRSI 1A"]:
    if c in resumo.columns: formatters[c]=lambda x: fmt_pct(x,1)
if "CRSI confirmado" in resumo.columns: formatters["CRSI confirmado"]=lambda x: fmt_num(x,2)
sty=resumo.style.format(formatters,na_rep="N/D")
if "Valuation final" in resumo.columns: sty=sty.map(css_valuation,subset=["Valuation final"])
for c in ["30D · Confluência %","90D · Confluência %","180D · Confluência %"]:
    if c in resumo.columns: sty=sty.map(css_confluencia,subset=[c])
if "CRSI confirmado" in resumo.columns: sty=sty.map(css_crsi,subset=["CRSI confirmado"])
st.dataframe(sty,use_container_width=True,hide_index=True,height=min(1150,38*(len(resumo)+1)))

with st.expander("Valuation — saída consolidada do painel original"):
    if valuation.empty: st.info("Sem snapshot do Valuation.")
    else: st.dataframe(valuation,use_container_width=True,hide_index=True,height=min(900,38*(len(valuation)+1)))
with st.expander("GARCH × GEX — 30D / 90D / 180D"):
    if garch.empty: st.info("Sem cache GARCH × GEX.")
    else: st.dataframe(garch,use_container_width=True,hide_index=True,height=min(900,38*(len(garch)+1)))
with st.expander("Connors RSI — confirmado / 30D / 90D / 180D / percentil"):
    if connors.empty: st.info("Sem dados do Connors.")
    else:
        cols=["Ativo","Preço atual","CRSI confirmado","CRSI 30D","CRSI 90D","CRSI 180D","Percentil CRSI 1A","Evento confirmado","Auditoria CRSI"]
        st.dataframe(connors[[c for c in cols if c in connors.columns]],use_container_width=True,hide_index=True,height=min(900,38*(len(connors)+1)))

st.subheader("Detalhar ativo no Radar Mestre")
ativo=st.selectbox("Ativo", master["Ativo"].dropna().astype(str).tolist())
row=master.loc[master["Ativo"]==ativo].iloc[0]
ca,cb,cc=st.columns(3)
with ca:
    st.markdown("#### Valuation")
    for c in ["Preço Valuation","Qualidade para carteira","Alvo validado 12m","Upside/Downside","Alvo validado 24m","Potencial preço 24m","Valuation final","Confiança","Conclusão para carteira"]:
        if c in row.index: st.write(f"**{c}:** {row[c] if pd.notna(row[c]) else 'N/D'}")
with cb:
    st.markdown("#### GARCH × GEX")
    for p in ["30D","90D","180D"]:
        st.write(f"**{p}**")
        for suffix in ["Principal","Confluência %","Dist Preço→Zona %","Dentro da zona"]:
            c=f"{p} · {suffix}"
            if c in row.index: st.write(f"{suffix}: {row[c] if pd.notna(row[c]) else 'N/D'}")
with cc:
    st.markdown("#### Connors RSI")
    for c in ["CRSI confirmado","CRSI 30D","CRSI 90D","CRSI 180D","Percentil CRSI 1A","Evento confirmado","Zona confirmada","Distância confirmada 20/80","Pregões extremo confirmado","Auditoria CRSI"]:
        if c in row.index: st.write(f"**{c}:** {row[c] if pd.notna(row[c]) else 'N/D'}")

st.divider()
st.caption("Radar Mestre = consolidação. Valuation, GARCH × GEX e Connors RSI continuam sendo motores independentes e auditáveis. Nenhum score combinado ou sinal automático de compra/venda foi criado.")
