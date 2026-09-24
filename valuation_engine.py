# ================================================================
# VALUATION AUTOMÁTICO B3 — UNIVERSO RADAR W1
# Google Colab | CVM (DFP/ITR) + Yahoo Finance + BCB
# Versão multiactivos final auditada: FCFF + RI setorial + módulo equity para bancos/seguradoras/B3/holding/Unit + CAPEX multissetorial + Yahoo robusto + fallback CVM CON→IND
# ================================================================

import sys, subprocess, warnings, io, zipfile, re, math, html as html_lib, time, unicodedata
from datetime import datetime

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "yfinance>=0.2.54"])

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yfinance as yf
import matplotlib.pyplot as plt
from IPython.display import display

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 100)
pd.set_option("display.width", 180)
pd.set_option("display.float_format", lambda x: f"{x:,.2f}")

# ================================================================
# 1) CONFIGURAÇÃO — ALTERE SOMENTE AQUI SE QUISER
# ================================================================

ASSETS = {
    # ============================================================
    # Universo do Radar W1 — mesma ordem do painel
    # ============================================================

    "ABEV3": {
        "symbol": "ABEV3",
        "ticker": "ABEV3.SA", "cvm": 23264, "name": "Ambev",
        "ordinary_ticker": "ABEV3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "fcff",
        "capex_profile": "standard",
        "fcff_profile": "generic",
    },

    "EQTL3": {
        "symbol": "EQTL3",
        "ticker": "EQTL3.SA", "cvm": 20010, "name": "Equatorial",
        "ordinary_ticker": "EQTL3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "fcff",
        "capex_profile": "concession",
        "fcff_profile": "regulated",
    },

    "CMIG4": {
        "symbol": "CMIG4",
        "ticker": "CMIG4.SA", "cvm": 2453, "name": "Cemig",
        "ordinary_ticker": "CMIG3.SA",
        "preferred_ticker": "CMIG4.SA",
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "fcff",
        "capex_profile": "concession",
        "fcff_profile": "regulated",
    },

    "PSSA3": {
        "symbol": "PSSA3",
        "ticker": "PSSA3.SA", "cvm": 16659, "name": "Porto",
        "ordinary_ticker": "PSSA3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "financial",
        "financial_profile": "insurance",
        "model_reason": (
            "Seguradora/holding de seguros: dívida, caixa, NWC e FCFF corporativo não têm "
            "a mesma interpretação econômica de uma companhia não financeira. "
            "Não é forçada no DCF FCFF."
        ),
    },

    "ITUB4": {
        "symbol": "ITUB4",
        "ticker": "ITUB4.SA", "cvm": 19348, "name": "Itaú Unibanco",
        "ordinary_ticker": "ITUB3.SA",
        "preferred_ticker": "ITUB4.SA",
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "financial",
        "financial_profile": "bank",
        "model_reason": (
            "Banco: depósitos, carteira de crédito e passivos financeiros fazem parte da operação. "
            "O DCF FCFF corporativo deste arquivo não é apropriado."
        ),
    },

    "EGIE3": {
        "symbol": "EGIE3",
        "ticker": "EGIE3.SA", "cvm": 17329, "name": "Engie Brasil Energia",
        "ordinary_ticker": "EGIE3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "fcff",
        "capex_profile": "standard",
        "fcff_profile": "regulated",
    },

    "BBDC4": {
        "symbol": "BBDC4",
        "ticker": "BBDC4.SA", "cvm": 906, "name": "Banco Bradesco",
        "ordinary_ticker": "BBDC3.SA",
        "preferred_ticker": "BBDC4.SA",
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "financial",
        "financial_profile": "bank",
        "model_reason": (
            "Banco: depósitos, carteira de crédito e passivos financeiros fazem parte da operação. "
            "O DCF FCFF corporativo deste arquivo não é apropriado."
        ),
    },

    "BBAS3": {
        "symbol": "BBAS3",
        "ticker": "BBAS3.SA", "cvm": 1023, "name": "Banco do Brasil",
        "ordinary_ticker": "BBAS3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "financial",
        "financial_profile": "bank",
        "model_reason": (
            "Banco: depósitos, carteira de crédito e passivos financeiros fazem parte da operação. "
            "O DCF FCFF corporativo deste arquivo não é apropriado."
        ),
    },

    "BBSE3": {
        "symbol": "BBSE3",
        "ticker": "BBSE3.SA", "cvm": 23159, "name": "BB Seguridade",
        "ordinary_ticker": "BBSE3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "financial",
        "financial_profile": "insurance_holding",
        "model_reason": (
            "Holding de seguridade: a estrutura econômica é financeira e não deve ser forçada "
            "no DCF FCFF corporativo."
        ),
    },

    "SBSP3": {
        "symbol": "SBSP3",
        "ticker": "SBSP3.SA", "cvm": 14443, "name": "Sabesp",
        "ordinary_ticker": "SBSP3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "fcff",
        "capex_profile": "concession",
        "fcff_profile": "regulated",
    },

    "WEGE3": {
        "symbol": "WEGE3",
        "ticker": "WEGE3.SA", "cvm": 5410, "name": "WEG",
        "ordinary_ticker": "WEGE3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "fcff",
        "capex_profile": "standard",
        "fcff_profile": "high_roic_growth",
    },

    "B3SA3": {
        "symbol": "B3SA3",
        "ticker": "B3SA3.SA", "cvm": 21610, "name": "B3",
        "ordinary_ticker": "B3SA3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "financial_infrastructure",
        "financial_profile": "market_infrastructure",
        "model_reason": (
            "Infraestrutura de mercado financeiro: o balanço inclui contas ligadas a liquidação, "
            "garantias e ativos/passivos financeiros. O NWC/dívida líquida do DCF corporativo "
            "não deve ser aplicado automaticamente."
        ),
    },

    "VALE3": {
        "symbol": "VALE3",
        "ticker": "VALE3.SA", "cvm": 4170, "name": "Vale",
        "ordinary_ticker": "VALE3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 3_000_000_000,
        "shares_expected_max": 6_000_000_000,
        # Referência oficial de 30/06/2026 / divulgação de 30/07/2026.
        "official_shares_outstanding": {"2026-06-30": 4_255_762_795},
        # Referências oficiais recorrentes discutidas para evitar que itens não
        # recorrentes de 2025 contaminem a normalização econômica.
        "official_adjusted_ebitda": {2025: 85_900_000_000.0},
        "official_proforma_net_income": {2025: 43_500_000_000.0},
        "official_proforma_net_income_quarters": {
            "2025Q1": 8_600_000_000.0,
            "2025Q2": 12_100_000_000.0,
            "2026Q1": 10_000_000_000.0,
            "2026Q2": 7_800_000_000.0,
        },
        # Vale Annual Report 2025: US$ 5,5 bi de investimentos, dos quais
        # US$ 4,4 bi de maintenance/sustaining CAPEX. A diferença de US$ 1,1 bi
        # é tratada apenas como parcela de crescimento para decomposição do CAPEX.
        # O CAPEX TOTAL continua integralmente deduzido no FCFF.
        "official_capex_split": {
            "reference_year": 2025,
            "total_usd": 5_500_000_000.0,
            "sustaining_usd": 4_400_000_000.0,
            "basis": "Vale Annual Report 2025: US$ 5,5 bi total; US$ 4,4 bi maintenance CAPEX",
        },
        # Timing operacional oficial mantido SOMENTE para AUDITORIA.
        # Sem guidance anual quantitativo completo por janela forward, os marcos de
        # projeto NÃO alteram a trajetória de crescimento do DCF.
        "official_growth_timing": {
            "reference_base_year": 2026,
            "reference_base_date": "2026-06-30",
            "basis": (
                "Vale Annual Report 2025 + resultados 2T26: volumes realizados 2025, "
                "guidances 2026 e objetivos 2030; dados usados somente para auditoria temporal"
            ),
            "products": {
                "Minério de ferro": {
                    "actual_2025": 336.0,
                    "guidance_2026_min": 335.0,
                    "guidance_2026_max": 345.0,
                    "target_2030_min": 360.0,
                    "target_2030_max": 360.0,
                    "revenue_2025_usd_m": 30_130.0,
                    "unit": "Mt",
                },
                "Cobre": {
                    "actual_2025": 382.0,
                    "guidance_2026_min": 360.0,
                    "guidance_2026_max": 380.0,
                    "target_2030_min": 420.0,
                    "target_2030_max": 500.0,
                    "revenue_2025_usd_m": 4_509.0,
                    "unit": "kt",
                },
                "Níquel": {
                    "actual_2025": 177.0,
                    "guidance_2026_min": 185.0,
                    "guidance_2026_max": 200.0,
                    "target_2030_min": 210.0,
                    "target_2030_max": 250.0,
                    "revenue_2025_usd_m": 4_319.0,
                    "unit": "kt",
                },
            },
            "projects": [
                {
                    "name": "Capanema", "product": "Minério de ferro",
                    "capacity": 15.0, "unit": "Mtpa", "effect_from": "1S26",
                    "capex_usd": 930_000_000.0,
                    "status": "ramp-up previsto/concluído no 1S26; efeito já parcialmente incorporado no TTM",
                },
                {
                    "name": "Vargem Grande 1", "product": "Minério de ferro",
                    "capacity": 15.0, "unit": "Mtpa", "effect_from": "2S26",
                    "capex_usd": None,
                    "status": "ramp-up no 2S26; benefício operacional entra nos primeiros anos projetados",
                },
                {
                    "name": "Serra Sul +20 / Britador de Compactos", "product": "Minério de ferro",
                    "capacity": 20.0, "unit": "Mtpa", "effect_from": "2027",
                    "capex_usd": 2_800_000_000.0,
                    "status": "start-up em 2S26/4T26; Vale indica suporte à produção a partir de 2027",
                },
                {
                    "name": "Bacaba", "product": "Cobre",
                    "capacity": 50.0, "unit": "ktpa", "effect_from": "3T27",
                    "capex_usd": 290_000_000.0,
                    "status": "start-up antecipado para 3T27; efeito pleno ocorre após entrada em operação/ramp-up",
                },
            ],
        },
        "valuation_model": "fcff",
        "capex_profile": "standard",
        "fcff_profile": "custom_validated",
    },

    "GGBR4": {
        "symbol": "GGBR4",
        "ticker": "GGBR4.SA", "cvm": 3980, "name": "Gerdau",
        "ordinary_ticker": "GGBR3.SA",
        "preferred_ticker": "GGBR4.SA",
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "fcff",
        "capex_profile": "standard",
        "fcff_profile": "cyclical",
    },

    "ITSA4": {
        "symbol": "ITSA4",
        "ticker": "ITSA4.SA", "cvm": 7617, "name": "Itaúsa",
        "ordinary_ticker": "ITSA3.SA",
        "preferred_ticker": "ITSA4.SA",
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "holding",
        "financial_profile": "holding",
        "model_reason": (
            "Holding diversificada com participação relevante em instituição financeira. "
            "O valuation adequado é por NAV/soma das partes, não pelo FCFF consolidado deste arquivo."
        ),
    },

    "CXSE3": {
        "symbol": "CXSE3",
        "ticker": "CXSE3.SA", "cvm": 23795, "name": "Caixa Seguridade",
        "ordinary_ticker": "CXSE3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "financial",
        "financial_profile": "insurance_holding",
        "model_reason": (
            "Holding de seguridade: a estrutura econômica é financeira e não deve ser forçada "
            "no DCF FCFF corporativo."
        ),
    },

    "BPAC11": {
        "symbol": "BPAC11",
        "ticker": "BPAC11.SA", "cvm": 22616, "name": "BTG Pactual",
        "ordinary_ticker": None,
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "financial_unit",
        "financial_profile": "bank_unit",
        # Estrutura oficial BPAC11: 1 ação ON + 2 ações PNA por Unit.
        # O fator converte a quantidade total de ações subjacentes em Units equivalentes.
        "unit_share_factor": 3.0,
        "unit_structure_basis": "BTG Pactual/B3: BPAC11 = 1 ON + 2 PNA",
        "model_reason": (
            "Banco e ativo negociado como Unit. Depósitos/carteira de crédito são operacionais "
            "e uma Unit representa combinação de classes; exige módulo próprio para instituições financeiras."
        ),
    },

    "CPFE3": {
        "symbol": "CPFE3",
        "ticker": "CPFE3.SA", "cvm": 18660, "name": "CPFL Energia",
        "ordinary_ticker": "CPFE3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        # B3/CVM: capital integralizado em 30/06/2026 = 1.152.254.440 ON;
        # sem ações em tesouraria na referência oficial consultada.
        "official_shares_outstanding": {"2026-06-30": 1_152_254_440},
        "official_capex_split": None,
        "valuation_model": "fcff",
        "capex_profile": "concession",
        "fcff_profile": "regulated",
    },

    "CPLE3": {
        "symbol": "CPLE3",
        "ticker": "CPLE3.SA", "cvm": 14311, "name": "Copel",
        "ordinary_ticker": "CPLE3.SA",
        "preferred_ticker": None,
        "shares_expected_min": 50_000_000,
        "shares_expected_max": 30_000_000_000,
        "official_shares_outstanding": {},
        "official_capex_split": None,
        "valuation_model": "fcff",
        "capex_profile": "concession",
        "fcff_profile": "regulated",
    },

    "PETR4": {
        "symbol": "PETR4",
        "ticker": "PETR4.SA", "cvm": 9512, "name": "Petrobras",
        "ordinary_ticker": "PETR3.SA",
        "preferred_ticker": "PETR4.SA",
        "shares_expected_min": 10_000_000_000,
        "shares_expected_max": 15_000_000_000,
        "official_shares_outstanding": {"2026-06-30": 12_888_732_761},
        "official_capex_split": None,
        "valuation_model": "fcff",
        "capex_profile": "standard",
        "fcff_profile": "custom_validated",
    },
}
HIST_YEARS = [2021, 2022, 2023, 2024, 2025]
AUX_NWC_YEAR = 2020  # usado somente para calcular Delta NWC e FCFF de 2021
CURRENT_ITR_YEAR = 2026
PROJECTION_YEARS = 5

# Premissas macro/modelo (não são dados contábeis)
#
# Ke/WACC — metodologia revisada e coerente com um DCF nominal em BRL:
#   1) A Selic Meta corrente continua sendo consultada e exibida apenas como
#      diagnóstico; ela NÃO é tratada como taxa livre de risco permanente.
#   2) A taxa-base do valuation usa a ETTJ prefixada soberana de longo prazo
#      da ANBIMA (vértice-alvo de 2.520 dias úteis, ~10 anos) e retira o
#      default spread soberano do Brasil para obter uma proxy de Rf nominal BRL.
#   3) O CAPM preserva a estrutura já usada no modelo:
#          Ke = Rf + beta × ERP Brasil
#      usando o ERP TOTAL Brasil de 7,30% (referência 01/07/2026), sem somar
#      um segundo prêmio-país, pois ele já está embutido no ERP total.
#   4) O custo bruto da dívida preserva o spread corporativo de 2,5 p.p. já
#      acordado e recompõe o risco soberano que foi retirado da Rf:
#          Kd = Rf default-free + default spread Brasil + spread corporativo
#      Isso equivale, quando a Rf vem da ANBIMA, a ETTJ soberana + spread corporativo.
#   5) O escudo fiscal do WACC usa a alíquota marginal de 34%. A taxa efetiva
#      normalizada permanece no NOPAT/FCFF, sem alteração.
EQUITY_RISK_PREMIUM = 0.0730      # ERP total Brasil — referência 01/07/2026
EQUITY_RISK_PREMIUM_ASOF = "2026-07-01"
BRAZIL_DEFAULT_SPREAD = 0.0199    # default spread soberano Brasil — referência 01/07/2026
BRAZIL_DEFAULT_SPREAD_ASOF = "2026-07-01"
DEBT_SPREAD = 0.025               # spread corporativo preservado, adicional ao soberano
WACC_MARGINAL_TAX_RATE = 0.34     # IRPJ marginal 25% + CSLL 9%
TERMINAL_GROWTH = 0.040           # 4,0% nominal a.a.
RF_OVERRIDE = None                # Ex.: 0.125 para forçar Rf; None = ANBIMA - default spread
ANBIMA_CURVE_URL = "https://www.anbima.com.br/informacoes/curvas-intradiarias/CIntra.asp"
ANBIMA_TARGET_VERTEX = 2520       # ~10 anos em base 252 dias úteis


# Composição econômica do CAPEX:
# - O DCF sempre deduz 100% do CAPEX extraído/projetado.
# - Sustaining x growth só é separado quando a própria companhia divulga uma
#   abertura oficial comparável.
# - Para a Vale, o Relatório Anual 2025 informa US$ 5,5 bi de investimentos,
#   incluindo US$ 4,4 bi de maintenance CAPEX => 80% sustaining / 20% growth.
# - Para a Petrobras, não é imposto split consolidado sem base oficial comparável.
#
# Timing do growth CAPEX / crescimento — GOVERNANÇA FINAL:
# - O modelo NÃO faz CAPEX growth do mesmo ano gerar receita do mesmo ano.
# - Também NÃO inventa IRR/ROIC de projeto, EBITDA incremental ou ramp-up.
# - Janelas forward e marcos oficiais de projetos são exibidos para AUDITORIA.
# - Sem guidance anual quantitativo completo por janela, esses marcos NÃO alteram
#   numericamente a trajetória de crescimento.
# - Não há soma entre CAGR físico e capacidade de projeto, nem score de timing.
# - A trajetória quantitativa preserva o crescimento legado já aprovado em cada cenário.
# - Para Petrobras e Vale, qualquer futuro ajuste de timing só deve ocorrer quando
#   houver base oficial quantitativa suficiente para os períodos projetados.

# Limites para evitar extrapolações absurdas de empresas cíclicas
AUTO_GROWTH_FLOOR = -0.03
AUTO_GROWTH_CEILING = 0.08
TAX_FLOOR = 0.15
TAX_CEILING = 0.34

# Padrões de extração contábil.
# D&A deve vir da reconciliação operacional da DFC (bloco 6.01),
# nunca de amortizações de principal/juros/financiamentos.
DA_INCLUDE_PATTERN = r"deprecia|deple[cç]|exaust|amortiza"
DA_EXCLUDE_PATTERN = (
    r"principal|juros|financi|empr[eé]st|capta[cç]|d[ií]vida|deb[eê]nt|"
    r"amortiza.*arrendamento|arrendamento.*amortiza"
)
CAPEX_PATTERN = (
    r"aquisi.*(?:imobil|intang)|adi[cç].*(?:imobil|intang)|"
    r"aplica.*(?:imobil|intang)|invest.*(?:imobil|intang)|compra.*(?:imobil|intang)"
)

# CAPEX concessionário/regulado:
# certas companhias reconhecem expansão de rede/concessão como ativo contratual,
# ativo financeiro de concessão ou infraestrutura, e não apenas como imobilizado.
# Esses itens são incluídos somente quando aparecem explicitamente como aplicação/
# aquisição/adição de ativo nas DFCs; não são estimados.
CAPEX_CONCESSION_PATTERN = (
    r"ativo.?contrat|ativo de contrato|"
    r"concess[aã]o.*servi[cç]o.*p[uú]blico.*ativo|"
    r"infraestrutura.*(?:distribui|concess|transmiss)|"
    r"adi[cç].*ativo.*transmiss"
)

CAPEX_EXCLUDE_PATTERN = (
    r"venda|aliena[cç]|recebimento|baixa|resgate|"
    r"aplica[cç][oõ]es? financeiras|t[ií]tulos e valores mobili[aá]rios|"
    r"participa[cç][aã]o societ[aá]ria|aumento de capital|redu[cç][aã]o de capital|"
    r"combina[cç][aã]o de neg[oó]cios|aquisi[cç][aã]o de empresa|"
    r"aquisi[cç][oõ]es? de investimento|aquisi[cç][aã]o de investimento"
)

# Cenários do DCF: ajustes sobre as premissas-base
SCENARIOS = {
    "Pessimista": {
        "weight": 0.25,
        "growth_shift": -0.03,
        "ebit_margin_shift": -0.03,
        "capex_ratio_shift": +0.01,
        "wacc_shift": +0.02,
        "terminal_g_shift": -0.015,
    },
    "Base": {
        "weight": 0.50,
        "growth_shift": 0.00,
        "ebit_margin_shift": 0.00,
        "capex_ratio_shift": 0.00,
        "wacc_shift": 0.00,
        "terminal_g_shift": 0.00,
    },
    "Otimista": {
        "weight": 0.25,
        "growth_shift": +0.03,
        "ebit_margin_shift": +0.03,
        "capex_ratio_shift": -0.005,
        "wacc_shift": -0.015,
        "terminal_g_shift": +0.010,
    },
}

# Pesos do preço-alvo final em 12 meses
METHOD_WEIGHTS = {
    "DCF 12m": 0.50,
    "P/L 12m": 0.20,
    "EV/EBITDA 12m": 0.20,
    "Dividend Yield 12m": 0.10,
}

# Pesos do módulo de equity para bancos/seguradoras/infraestrutura financeira/holding.
# A distribuição 50/20/20/10 é a MESMA já adotada no Radar; apenas EV/EBITDA,
# inadequado para instituições financeiras, é substituído por P/VP histórico.
EQUITY_METHOD_WEIGHTS = {
    "Residual Income 12m": 0.50,
    "P/L 12m": 0.20,
    "P/VP 12m": 0.20,
    "Dividend Yield 12m": 0.10,
}

# Governança do preço-alvo multissetorial:
# - O motor FCFF continua calculando todos os ativos não financeiros compatíveis.
# - Para empresas reguladas/concessionárias e WEGE3, o FCFF genérico permanece como
#   diagnóstico paralelo; o alvo final setorial usa o módulo Residual Income quando
#   patrimônio líquido/payout/Ke necessários estiverem disponíveis.
# - O RI não cria RAB, WACC regulatório, ROE perpétuo, ramp-up ou prêmio setorial.
# - O horizonte-base permanece em 5 anos. Se o ROE ainda estiver acima do Ke no ano 5,
#   o lucro residual positivo é prolongado apenas com o mesmo g terminal, margem, payout
#   e Ke já existentes até a convergência endógena; depois RI terminal = 0.
# - O composto de 50/20/20/10 só é calculado quando os QUATRO métodos estão disponíveis;
#   método ausente não tem seu peso redistribuído silenciosamente.
#
# MÓDULO RESIDUAL INCOME (RI) — REGULADAS / HIGH-ROIC:
# - O FCFF genérico continua integralmente calculado e exibido como diagnóstico.
# - Para perfis "regulated" e "high_roic_growth", o slot principal de 50% do composto
#   passa a usar um modelo de Lucro Residual (Residual Income) sobre patrimônio líquido.
# - O RI usa apenas dados já observados/projetados pelo próprio modelo: patrimônio líquido
#   CVM, lucro líquido, Ke, crescimento, margem líquida e payout histórico normalizado.
# - Não usa RAB inventada, WACC regulatório inventado, ROE futuro arbitrário, prêmio
#   setorial nem prazo de fade escolhido manualmente. O RI projeta no mínimo 5 anos e,
#   quando ainda existe excesso de retorno positivo no ano 5, continua a dinâmica já
#   existente com g terminal/margem/payout/Ke até o ROE atingir o Ke.
# - Isso evita tanto o corte abrupto de um excesso de retorno ainda positivo quanto a
#   perpetuação artificial desse excesso.
# - Os pesos finais permanecem 50/20/20/10; apenas o método principal de 50% é substituído
#   por RI nesses dois perfis. Para os demais perfis, o método principal continua sendo DCF.

CVM_BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"

# Robustez de rede — não altera nenhuma premissa de valuation.
# O problema observado no Colab foi de conectividade com dados.cvm.gov.br: o código
# esperava até 90 s por ativo e repetia a mesma falha. Mantemos 90 s para LEITURA do
# ZIP, mas limitamos a fase de CONEXÃO e fazemos apenas uma repetição automática.
CVM_CONNECT_TIMEOUT = 10
CVM_READ_TIMEOUT = 90
CVM_PREFLIGHT_CONNECT_TIMEOUT = 8
CVM_PREFLIGHT_READ_TIMEOUT = 15

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 valuation-colab/2.0"})

_CVM_RETRY = Retry(
    total=1,
    connect=1,
    read=1,
    status=1,
    backoff_factor=1.0,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET"]),
    raise_on_status=False,
)
_CVM_ADAPTER = HTTPAdapter(max_retries=_CVM_RETRY)
SESSION.mount(CVM_BASE + "/", _CVM_ADAPTER)

# Cache para não baixar o mesmo ZIP várias vezes
_ZIP_CACHE = {}
_PRICE_CACHE = {}
_YAHOO_JSON_CACHE = {}
_SPLIT_CACHE = {}


class CVMConnectivityError(ConnectionError):
    """Falha de rede/HTTP que impede o acesso aos arquivos oficiais da CVM."""


def check_cvm_connectivity():
    """
    Testa uma única vez a mesma rota da CVM usada pelo valuation antes de iniciar
    os 20 ativos. Usa stream=True, portanto não baixa o ZIP inteiro no teste.

    Se o runtime do Colab estiver sem rota para dados.cvm.gov.br, a execução para
    aqui em vez de repetir a mesma espera em cada ativo.
    """
    probe_url = (
        f"{CVM_BASE}/DFP/DADOS/"
        f"dfp_cia_aberta_{AUX_NWC_YEAR}.zip"
    )
    response = None
    try:
        response = SESSION.get(
            probe_url,
            timeout=(CVM_PREFLIGHT_CONNECT_TIMEOUT, CVM_PREFLIGHT_READ_TIMEOUT),
            stream=True,
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as exc:
        raise CVMConnectivityError(
            "Não foi possível acessar dados.cvm.gov.br a partir deste runtime do Colab. "
            "A execução foi interrompida antes de processar os ativos para evitar repetir "
            "a mesma falha por muitos minutos. Reinicie o ambiente de execução do Colab e "
            "rode novamente. Erro original: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    finally:
        if response is not None:
            response.close()


# ================================================================
# 2) UTILITÁRIOS CVM
# ================================================================

def _download_zip(doc_type: str, year: int):
    key = (doc_type.upper(), int(year))
    if key in _ZIP_CACHE:
        return _ZIP_CACHE[key]

    doc = doc_type.upper()
    filename = f"{doc.lower()}_cia_aberta_{year}.zip"
    url = f"{CVM_BASE}/{doc}/DADOS/{filename}"

    try:
        r = SESSION.get(
            url,
            timeout=(CVM_CONNECT_TIMEOUT, CVM_READ_TIMEOUT),
        )
        r.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise CVMConnectivityError(
            f"Falha ao acessar arquivo oficial da CVM ({doc} {year}): {url}. "
            f"Erro original: {type(exc).__name__}: {exc}"
        ) from exc

    try:
        z = zipfile.ZipFile(io.BytesIO(r.content))
    except zipfile.BadZipFile as exc:
        raise ValueError(
            f"A CVM respondeu, mas o conteúdo recebido não é um ZIP válido: {url}."
        ) from exc

    _ZIP_CACHE[key] = z
    return z


def _find_member(z: zipfile.ZipFile, tokens):
    tokens = [t.lower() for t in tokens]
    matches = []
    for name in z.namelist():
        low = name.lower()
        if low.endswith(".csv") and all(t in low for t in tokens):
            matches.append(name)
    if not matches:
        return None
    # Prefere consolidado quando aplicável
    con = [m for m in matches if "_con_" in m.lower()]
    return con[0] if con else matches[0]


def _read_member(z, member):
    if member is None:
        return pd.DataFrame()
    with z.open(member) as f:
        raw = f.read()
    # CVM normalmente usa latin1/ISO-8859-1, ; e vírgula decimal
    return pd.read_csv(
        io.BytesIO(raw),
        sep=";",
        decimal=",",
        encoding="latin1",
        low_memory=False,
    )


def _find_submission_member(z: zipfile.ZipFile, doc_type: str, year: int):
    """Localiza a tabela-base de submissão do DFP/ITR dentro do ZIP da CVM."""
    target = f"{doc_type.lower()}_cia_aberta_{int(year)}.csv"
    for name in z.namelist():
        if name.split("/")[-1].lower() == target.lower():
            return name
    return None


def _normalize_cnpj_series(s):
    """Normaliza CNPJ para somente dígitos, preservando zeros à esquerda."""
    return s.astype(str).str.replace(r"\D", "", regex=True).str.zfill(14)


def _normalize_capital_submission_keys(df):
    """Normaliza chaves usadas para ligar composicao_capital à submissao."""
    x = df.copy()
    if "CNPJ_CIA" in x.columns:
        x["CNPJ_CIA"] = _normalize_cnpj_series(x["CNPJ_CIA"])
    if "DT_REFER" in x.columns:
        x["DT_REFER"] = pd.to_datetime(x["DT_REFER"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "VERSAO" in x.columns:
        v = pd.to_numeric(x["VERSAO"], errors="coerce")
        x["VERSAO"] = v.astype("Int64").astype(str)
    return x


def _attach_cd_cvm_to_capital(capital_df, submission_df):
    """
    A tabela composicao_capital da CVM não possui CD_CVM.
    Faz o relacionamento via submissao (CNPJ/data/versão) e devolve
    a composição de capital com CD_CVM anexado.
    """
    if capital_df is None or capital_df.empty:
        return pd.DataFrame()
    cap = _normalize_capital_submission_keys(capital_df)
    if submission_df is None or submission_df.empty:
        return cap
    sub = _normalize_capital_submission_keys(submission_df)
    if "CD_CVM" not in sub.columns or "CNPJ_CIA" not in cap.columns or "CNPJ_CIA" not in sub.columns:
        return cap

    sub["CD_CVM"] = pd.to_numeric(sub["CD_CVM"], errors="coerce")
    sub = sub.dropna(subset=["CD_CVM"]).copy()

    # Primeiro tenta a chave mais específica disponível.
    candidate_keys = [
        ["CNPJ_CIA", "DT_REFER", "VERSAO"],
        ["CNPJ_CIA", "DT_REFER"],
        ["CNPJ_CIA"],
    ]

    if "CD_CVM" in cap.columns:
        cap = cap.drop(columns=["CD_CVM"])

    for keys in candidate_keys:
        if not all(k in cap.columns and k in sub.columns for k in keys):
            continue
        lookup = sub[keys + ["CD_CVM"]].drop_duplicates(keys, keep="last")
        merged = cap.merge(lookup, on=keys, how="left")
        if merged["CD_CVM"].notna().any():
            return merged

    return cap


def load_cvm_package(doc_type: str, year: int):
    """
    Carrega o pacote CVM preservando separadamente demonstrações consolidadas (CON)
    e individuais (IND).

    Motivo: alguns emissores/anos não possuem linhas utilizáveis na versão consolidada
    de uma demonstração, embora o ZIP da CVM contenha normalmente o arquivo *_con_ por
    causa de outras companhias. A escolha CON -> IND precisa, portanto, ser feita por
    companhia/ano/demonstração, e não apenas pela existência global do CSV no ZIP.

    As chaves históricas DRE/BPA/BPP/DFC são mantidas para compatibilidade interna,
    mas os carregadores de histórico e TTM usam _select_statement_rows(), que faz a
    seleção por companhia sem misturar CON e IND.
    """
    z = _download_zip(doc_type, year)
    out = {}

    # DRE/BPA/BPP: mantém as duas bases disponíveis para seleção posterior por companhia.
    for statement in ("DRE", "BPA", "BPP"):
        con_member = _find_member(z, [statement, "con"])
        ind_member = _find_member(z, [statement, "ind"])
        out[f"{statement}_CON"] = _read_member(z, con_member)
        out[f"{statement}_IND"] = _read_member(z, ind_member)

        # Compatibilidade com funções antigas/diagnósticos: não decide a base econômica
        # final aqui. A seleção correta é feita por _select_statement_rows().
        if not out[f"{statement}_CON"].empty:
            out[statement] = out[f"{statement}_CON"]
        else:
            out[statement] = out[f"{statement}_IND"]

    # DFC: além de CON/IND, a CVM pode publicar método indireto (MI) ou direto (MD).
    # Todos os quatro candidatos são preservados; a seleção é feita depois por companhia.
    for method in ("MI", "MD"):
        for scope in ("CON", "IND"):
            member = _find_member(z, [f"DFC_{method}", scope.lower()])
            out[f"DFC_{method}_{scope}"] = _read_member(z, member)

    # Compatibilidade com a chave DFC anterior, sem afetar a seleção por companhia.
    out["DFC"] = pd.DataFrame()
    for key in ("DFC_MI_CON", "DFC_MD_CON", "DFC_MI_IND", "DFC_MD_IND"):
        if key in out and not out[key].empty:
            out["DFC"] = out[key]
            break

    capital_member = _find_member(z, ["composicao_capital"])
    out["CAPITAL"] = _read_member(z, capital_member)

    # A composição de capital não traz CD_CVM. A tabela de submissão
    # contém CD_CVM + CNPJ e é usada para fazer o relacionamento correto.
    submission_member = _find_submission_member(z, doc_type, year)
    submission = _read_member(z, submission_member)
    out["SUBMISSAO"] = submission
    out["CAPITAL"] = _attach_cd_cvm_to_capital(out["CAPITAL"], submission)
    return out


def _select_statement_rows(
    pkg,
    statement,
    cvm,
    year=None,
    ref_date=None,
    cumulative=False,
):
    """
    Seleciona uma demonstração por companhia/período com fallback CON -> IND.

    Regras:
    - DRE/BPA/BPP: tenta CON; somente se não houver linhas utilizáveis da companhia
      no período solicitado tenta IND.
    - DFC: tenta MI_CON, MD_CON, MI_IND, MD_IND nessa ordem. MI/MD são apenas formas
      de apresentação da DFC; não são combinadas entre si.
    - Nunca concatena CON e IND e nunca soma bases diferentes.
    - Retorna (linhas, origem), permitindo auditoria explícita da base escolhida.
    """
    statement = str(statement).upper().strip()

    if statement in {"DRE", "BPA", "BPP"}:
        candidates = [
            (f"{statement}_CON", "CON"),
            (f"{statement}_IND", "IND"),
        ]
    elif statement == "DFC":
        candidates = [
            ("DFC_MI_CON", "CON / DFC-MI"),
            ("DFC_MD_CON", "CON / DFC-MD"),
            ("DFC_MI_IND", "IND / DFC-MI"),
            ("DFC_MD_IND", "IND / DFC-MD"),
        ]
    else:
        raise ValueError(f"Demonstração CVM não suportada: {statement}")

    for key, origin in candidates:
        raw = pkg.get(key, pd.DataFrame())
        if raw is None or raw.empty:
            continue
        rows = _latest_filing_rows(
            raw,
            cvm,
            year=year,
            ref_date=ref_date,
            cumulative=cumulative,
        )
        if rows is not None and not rows.empty:
            return rows, origin

    return pd.DataFrame(), "n/d"


def _to_num(s):
    return pd.to_numeric(s, errors="coerce")


def _scale_values(df):
    df = df.copy()
    if "VL_CONTA" not in df.columns:
        return df
    df["VL_CONTA"] = _to_num(df["VL_CONTA"])
    if "ESCALA_MOEDA" in df.columns:
        scale = df["ESCALA_MOEDA"].astype(str).str.upper()
        mult = np.where(scale.str.contains("MILH"), 1_000_000,
               np.where(scale.str.contains("MIL"), 1_000, 1))
        df["VL_CONTA"] = df["VL_CONTA"] * mult
    return df


def _filter_company(df, cvm):
    if df is None or df.empty or "CD_CVM" not in df.columns:
        return pd.DataFrame()
    x = df.copy()
    x["CD_CVM"] = _to_num(x["CD_CVM"])
    x = x[x["CD_CVM"] == int(cvm)].copy()
    return _scale_values(x)


def _latest_filing_rows(df, cvm, year=None, ref_date=None, cumulative=False):
    x = _filter_company(df, cvm)
    if x.empty:
        return x

    if "DT_REFER" in x.columns:
        x["DT_REFER"] = pd.to_datetime(x["DT_REFER"], errors="coerce")
        if year is not None:
            x = x[x["DT_REFER"].dt.year == int(year)]
        if ref_date is not None:
            ref_date = pd.Timestamp(ref_date)
            exact = x[x["DT_REFER"] == ref_date]
            if not exact.empty:
                x = exact
            else:
                # mesmo mês/dia se possível; senão a data mais próxima anterior
                same_md = x[(x["DT_REFER"].dt.month == ref_date.month) &
                            (x["DT_REFER"].dt.day == ref_date.day)]
                if not same_md.empty:
                    x = same_md
                else:
                    before = x[x["DT_REFER"] <= ref_date]
                    x = before if not before.empty else x
        if x.empty:
            return x
        latest_ref = x["DT_REFER"].max()
        x = x[x["DT_REFER"] == latest_ref]

    if "VERSAO" in x.columns and not x.empty:
        x["VERSAO_NUM"] = _to_num(x["VERSAO"])
        vmax = x["VERSAO_NUM"].max()
        if pd.notna(vmax):
            x = x[x["VERSAO_NUM"] == vmax]

    if "ORDEM_EXERC" in x.columns:
        # IMPORTANTE: não usar contains("LTIMO"), porque isso também casa
        # com "PENÚLTIMO" e pode misturar o exercício comparativo ao atual.
        ordem = x["ORDEM_EXERC"].astype(str).str.upper().str.strip()
        ult = x[ordem.isin(["ÚLTIMO", "ULTIMO"])]
        if not ult.empty:
            x = ult

    # Para DRE/DFC de ITR, manter acumulado desde 01/01 quando disponível
    if cumulative and "DT_INI_EXERC" in x.columns and not x.empty:
        x["DT_INI_EXERC"] = pd.to_datetime(x["DT_INI_EXERC"], errors="coerce")
        if "DT_REFER" in x.columns and x["DT_REFER"].notna().any():
            ref = x["DT_REFER"].dropna().iloc[0]
            jan1 = pd.Timestamp(year=ref.year, month=1, day=1)
            ytd = x[x["DT_INI_EXERC"] == jan1]
            if not ytd.empty:
                x = ytd
            else:
                min_start = x["DT_INI_EXERC"].min()
                ytd = x[x["DT_INI_EXERC"] == min_start]
                if not ytd.empty:
                    x = ytd

    # Remove duplicatas remanescentes por conta, preservando a linha de maior valor absoluto
    if "CD_CONTA" in x.columns and "VL_CONTA" in x.columns:
        x["ABS_VL"] = x["VL_CONTA"].abs()
        x = x.sort_values("ABS_VL", ascending=False).drop_duplicates("CD_CONTA")
    return x


def value_by_code(df, code, default=np.nan):
    if df is None or df.empty or "CD_CONTA" not in df.columns:
        return default
    s = df[df["CD_CONTA"].astype(str).str.strip() == str(code)]
    if s.empty:
        return default
    vals = _to_num(s["VL_CONTA"]).dropna()
    return float(vals.iloc[0]) if len(vals) else default


def value_first_code(df, codes, default=np.nan):
    for c in codes:
        v = value_by_code(df, c, np.nan)
        if pd.notna(v):
            return v
    return default


def sum_leaf_matches(df, pattern, prefix=None, absolute=True):
    """Soma somente contas-folha entre as descrições que casam com regex."""
    if df is None or df.empty or "DS_CONTA" not in df.columns:
        return 0.0, []
    x = df.copy()
    desc = x["DS_CONTA"].astype(str)
    m = desc.str.contains(pattern, case=False, regex=True, na=False)
    if prefix is not None and "CD_CONTA" in x.columns:
        m &= x["CD_CONTA"].astype(str).str.startswith(str(prefix))
    y = x[m].copy()
    if y.empty:
        return 0.0, []

    y["CODE"] = y["CD_CONTA"].astype(str).str.strip()
    codes = y["CODE"].tolist()
    is_parent = []
    for c in codes:
        parent = any((other != c) and other.startswith(c + ".") for other in codes)
        is_parent.append(parent)
    leaves = y[~pd.Series(is_parent, index=y.index)].copy()
    if leaves.empty:
        leaves = y
    vals = _to_num(leaves["VL_CONTA"]).fillna(0.0)
    total = vals.abs().sum() if absolute else vals.sum()
    labels = [f"{r.CD_CONTA} - {r.DS_CONTA}" for r in leaves.itertuples()]
    return float(total), labels



def sum_top_matches(df, pattern, prefix=None, absolute=True, exclude_pattern=None):
    """
    Soma contas que casam com um padrão sem duplicar conta-pai e conta-filha.

    Se uma conta-pai e uma de suas filhas casarem com o mesmo padrão, usa a
    conta-pai (valor agregado) e descarta as filhas para evitar dupla contagem.
    Se somente a filha casar, usa a filha normalmente.
    """
    if df is None or df.empty or "DS_CONTA" not in df.columns or "CD_CONTA" not in df.columns:
        return 0.0, []

    x = df.copy()
    desc = x["DS_CONTA"].astype(str)
    codes = x["CD_CONTA"].astype(str).str.strip()

    m = desc.str.contains(pattern, case=False, regex=True, na=False)
    if exclude_pattern:
        m &= ~desc.str.contains(exclude_pattern, case=False, regex=True, na=False)
    if prefix is not None:
        m &= codes.str.startswith(str(prefix))

    y = x[m].copy()
    if y.empty:
        return 0.0, []

    y["CODE"] = y["CD_CONTA"].astype(str).str.strip()
    y["NUM"] = _to_num(y["VL_CONTA"]).fillna(0.0)
    y["ABS_VL"] = y["NUM"].abs()
    y["DEPTH"] = y["CODE"].str.count(r"\.")

    # Uma linha por código, priorizando o maior valor absoluto se ainda restou
    # alguma duplicidade após a seleção da versão/exercício.
    y = (
        y.sort_values(["DEPTH", "ABS_VL"], ascending=[True, False])
         .drop_duplicates("CODE", keep="first")
    )

    matched_codes = y["CODE"].tolist()
    keep = []
    for c in matched_codes:
        has_matched_parent = any(
            other != c and c.startswith(other + ".")
            for other in matched_codes
        )
        keep.append(not has_matched_parent)

    selected = y.loc[pd.Series(keep, index=y.index)].copy()
    vals = selected["NUM"]
    total = vals.abs().sum() if absolute else vals.sum()
    labels = [f"{r.CD_CONTA} - {r.DS_CONTA}" for r in selected.itertuples()]
    return float(total), labels


def extract_da_from_dfc(dfc):
    """
    Extrai depreciação/depleção/exaustão/amortização operacional da DFC-MI.

    A restrição ao bloco 6.01 evita confundir D&A com amortização de principal,
    juros, financiamentos ou outros fluxos de financiamento do bloco 6.03.
    """
    total, labels = sum_top_matches(
        dfc,
        DA_INCLUDE_PATTERN,
        prefix="6.01",
        absolute=True,
        exclude_pattern=DA_EXCLUDE_PATTERN,
    )
    return (float(total), labels) if labels else (np.nan, [])


def _normalize_text(value):
    """Normaliza texto apenas para comparação de descrições, sem alterar os dados originais."""
    s = "" if value is None else str(value)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip().lower()


def _dedupe_hierarchical_rows(rows):
    """
    Evita dupla contagem quando a DFC traz simultaneamente conta-pai e conta-filha
    para o mesmo investimento. Mantém a conta-pai agregada entre as linhas candidatas.
    """
    if rows is None or rows.empty:
        return pd.DataFrame() if rows is None else rows.copy()

    y = rows.copy()
    y["CODE"] = y["CD_CONTA"].astype(str).str.strip()
    y["NUM"] = pd.to_numeric(y["VL_CONTA"], errors="coerce")
    y = y.dropna(subset=["NUM"]).copy()
    y["DEPTH"] = y["CODE"].str.count(r"\.")
    y["ABS_VL"] = y["NUM"].abs()
    y = (
        y.sort_values(["DEPTH", "ABS_VL"], ascending=[True, False])
         .drop_duplicates("CODE", keep="first")
    )

    codes = y["CODE"].tolist()
    keep = []
    for c in codes:
        has_parent = any(other != c and c.startswith(other + ".") for other in codes)
        keep.append(not has_parent)
    return y.loc[pd.Series(keep, index=y.index)].copy()


def extract_capex_from_dfc(dfc, profile="standard"):
    """
    Extrai CAPEX diretamente das linhas da DFC sem criar estimativas.

    Regras:
    1) bloco 6.02: aquisições/adições/aplicações em imobilizado e intangível;
    2) aceita layouts em que a própria linha é apenas "Imobilizado"/"Intangível";
    3) para perfil concessionário, inclui ativos contratuais/infraestrutura/concessão
       explicitamente apresentados como investimento;
    4) para perfil concessionário, também captura em 6.01 somente linhas que digam
       explicitamente "aquisição/adição" de ativo contratual/transmissão, pois algumas
       concessionárias classificam esse desembolso na atividade operacional;
    5) vendas, alienações, resgates, aplicações financeiras, aquisições societárias e
       combinações de negócios são excluídas;
    6) CAPEX é o valor absoluto dos desembolsos negativos selecionados.

    Nenhum valor é inferido por diferença de balanço ou por guidance.
    """
    if dfc is None or dfc.empty or "DS_CONTA" not in dfc.columns or "CD_CONTA" not in dfc.columns or "VL_CONTA" not in dfc.columns:
        return np.nan, []

    x = dfc.copy()
    x["CODE"] = x["CD_CONTA"].astype(str).str.strip()
    x["NUM"] = pd.to_numeric(x["VL_CONTA"], errors="coerce")
    x["DESC"] = x["DS_CONTA"].astype(str)
    x["DESC_NORM"] = x["DESC"].map(_normalize_text)

    is_investing = x["CODE"].str.startswith("6.02") & (x["CODE"] != "6.02")
    is_operating = x["CODE"].str.startswith("6.01") & (x["CODE"] != "6.01")

    explicit_core = x["DESC"].str.contains(CAPEX_PATTERN, case=False, regex=True, na=False)

    # Layouts como WEG/Cemig: "Imobilizado", "Intangível", "No Imobilizado".
    direct_asset = x["DESC_NORM"].str.match(
        r"^(em |no |na |aplicacao no |aplicacao em )?(ativo )?(imobilizado|intangivel)"
        r"(\b| e\b| /|$)",
        na=False,
    )

    concession = x["DESC"].str.contains(
        CAPEX_CONCESSION_PATTERN, case=False, regex=True, na=False
    )
    excluded = x["DESC"].str.contains(
        CAPEX_EXCLUDE_PATTERN, case=False, regex=True, na=False
    )

    profile = str(profile or "standard").lower().strip()
    invest_candidate = is_investing & (explicit_core | direct_asset)
    if profile == "concession":
        invest_candidate |= is_investing & concession

    # Fora do bloco 6.02, só aceita uma adição/aquisição explicitamente descrita.
    if profile == "concession":
        explicit_addition = x["DESC"].str.contains(
            r"aquisi[cç]|adi[cç]", case=False, regex=True, na=False
        )
        operating_candidate = is_operating & concession & explicit_addition
    else:
        operating_candidate = pd.Series(False, index=x.index)

    candidate = (invest_candidate | operating_candidate) & (~excluded) & x["NUM"].notna()

    y = x[candidate & (x["NUM"] < 0)].copy()

    # Fallback conservador para eventual emissor que apresente aquisição/aplicação
    # com sinal positivo: somente o padrão explícito de aquisição/adição/aplicação,
    # nunca as linhas genéricas de concessão ou "Imobilizado" isolado.
    if y.empty:
        fallback = x[
            is_investing
            & explicit_core
            & (~excluded)
            & x["NUM"].notna()
            & (x["NUM"] != 0)
        ].copy()
        y = fallback

    if y.empty:
        return np.nan, []

    selected = _dedupe_hierarchical_rows(y)
    if selected.empty:
        return np.nan, []

    total = selected["NUM"].abs().sum()
    labels = [
        f"{r.CODE} - {r.DESC}"
        for r in selected[["CODE", "DESC"]].itertuples(index=False)
    ]
    return float(total), labels


def _label_for_code(df, code):
    if df is None or df.empty or "CD_CONTA" not in df.columns:
        return []
    s = df[df["CD_CONTA"].astype(str).str.strip() == str(code)]
    if s.empty:
        return []
    r = s.iloc[0]
    desc = r.get("DS_CONTA", "")
    return [f"{code} - {desc}"]


def extract_debt_from_bpp(bpp):
    """
    Extrai dívida financeira usando primeiro as contas padronizadas agregadas:
      2.01.04 = Empréstimos e Financiamentos (circulante)
      2.02.01 = Empréstimos e Financiamentos (não circulante)

    O fallback por descrição só é usado quando a conta agregada não existe.
    Isso evita dupla contagem ou perda de subclasses (ex.: debêntures) quando
    conta-pai e contas-filhas coexistem.

    Se a demonstração BPP inteira estiver indisponível, retorna NaN em vez de
    transformar ausência de dado em dívida zero.
    """
    if bpp is None or bpp.empty:
        return np.nan, np.nan, []

    current_debt = value_first_code(bpp, ["2.01.04"], np.nan)
    if pd.notna(current_debt):
        current_debt = abs(float(current_debt))
        cur_labels = _label_for_code(bpp, "2.01.04")
    else:
        current_debt, cur_labels = sum_top_matches(
            bpp,
            r"empr[eé]stimos|financiamentos|arrendamento|deb[eê]ntures",
            prefix="2.01",
            absolute=True,
        )

    noncurrent_debt = value_first_code(bpp, ["2.02.01"], np.nan)
    if pd.notna(noncurrent_debt):
        noncurrent_debt = abs(float(noncurrent_debt))
        noncur_labels = _label_for_code(bpp, "2.02.01")
    else:
        noncurrent_debt, noncur_labels = sum_top_matches(
            bpp,
            r"empr[eé]stimos|financiamentos|arrendamento|deb[eê]ntures",
            prefix="2.02",
            absolute=True,
        )

    current_debt = float(current_debt) if np.isfinite(current_debt) else 0.0
    noncurrent_debt = float(noncurrent_debt) if np.isfinite(noncurrent_debt) else 0.0
    return current_debt, noncurrent_debt, cur_labels + noncur_labels



def extract_equity_from_bpp(bpp):
    """
    Extrai patrimônio líquido total e patrimônio atribuível aos controladores.

    Regras:
    - 2.03 = Patrimônio Líquido consolidado.
    - 2.03.09, quando existente, é participação de não controladores.
    - Para manter coerência com o lucro líquido preferencialmente atribuído aos
      controladores (3.11.01), o módulo Residual Income usa:
          PL controladores = PL total - não controladores.
    - Se a parcela de não controladores não existir, PL controladores = PL total.
    - Demonstração BPP ausente retorna NaN; nenhuma base patrimonial é inventada.
    """
    if bpp is None or bpp.empty:
        return np.nan, np.nan, []

    total_equity = value_first_code(bpp, ["2.03"], np.nan)
    if pd.isna(total_equity) or not np.isfinite(total_equity):
        return np.nan, np.nan, []

    nci = value_first_code(bpp, ["2.03.09"], np.nan)
    labels = _label_for_code(bpp, "2.03")
    if pd.notna(nci) and np.isfinite(nci):
        parent_equity = float(total_equity) - float(nci)
        labels += _label_for_code(bpp, "2.03.09")
    else:
        parent_equity = float(total_equity)

    return float(total_equity), float(parent_equity), labels




def extract_financial_equity_from_bpp(bpp):
    """
    Extrai patrimônio líquido para o módulo equity de instituições financeiras,
    seguradoras, infraestrutura financeira, holdings e Units usando semântica da
    descrição da conta, e não um CD_CONTA fixo.

    Motivo:
    - em layouts CVM não financeiros, 2.03 costuma representar Patrimônio Líquido;
    - em algumas instituições financeiras, o mesmo código 2.03 pode representar
      Provisões ou Passivos Financeiros ao Custo Amortizado.

    Regras de governança:
    1. CD_CONTA sozinho nunca qualifica uma linha como patrimônio líquido;
    2. a descrição precisa ser semanticamente compatível com Patrimônio Líquido;
    3. linhas de não controladores são identificadas separadamente;
    4. se houver PL atribuível aos controladores explícito, ele é preferido;
    5. caso contrário, PL controladores = PL total - não controladores, quando
       ambos estiverem disponíveis;
    6. pais/filhos semanticamente equivalentes não são somados;
    7. se nenhuma linha patrimonial semanticamente válida existir, falha de forma
       explícita em vez de usar provisões/passivos por coincidência de código.

    Retorna:
        (equity_total, equity_parent, labels)
    """
    if bpp is None or bpp.empty:
        raise ValueError(
            "BPP financeiro indisponível; patrimônio líquido não pode ser extraído."
        )

    required = {"CD_CONTA", "DS_CONTA", "VL_CONTA"}
    missing_cols = sorted(required.difference(bpp.columns))
    if missing_cols:
        raise ValueError(
            "BPP financeiro sem colunas obrigatórias para extração patrimonial: "
            + ", ".join(missing_cols)
        )

    x = bpp.copy()
    x["CODE"] = x["CD_CONTA"].astype(str).str.strip()
    x["DESC_NORM"] = x["DS_CONTA"].map(_normalize_text)
    x["NUM"] = pd.to_numeric(x["VL_CONTA"], errors="coerce")
    x = x.dropna(subset=["NUM"]).copy()
    if x.empty:
        raise ValueError(
            "BPP financeiro sem valores numéricos; patrimônio líquido indisponível."
        )

    # Termos que comprovam natureza patrimonial. A busca é deliberadamente
    # semântica: não depende da posição/código usado por um emissor específico.
    has_equity = x["DESC_NORM"].str.contains(
        r"\bpatrimonio\s+liquido\b", regex=True, na=False
    )

    # Rejeições defensivas. Em especial, impedem que 2.03 seja aceito quando
    # significa Provisões ou Passivos Financeiros.
    forbidden = x["DESC_NORM"].str.contains(
        r"provis|passiv|custo amortizado|emprestim|financiament|deposit|obrigac",
        regex=True,
        na=False,
    )
    eq = x[has_equity & ~forbidden].copy()

    if eq.empty:
        # Diagnóstico curto com linhas possivelmente relacionadas, sem escolher
        # nenhuma delas como PL. Isso torna a falha auditável no Colab.
        related = x[
            x["DESC_NORM"].str.contains(
                r"patrimonio|provis|passiv.*financeir|capital.*social",
                regex=True,
                na=False,
            )
        ].copy()
        preview = [
            f"{r.CD_CONTA} - {r.DS_CONTA}"
            for r in related.head(12).itertuples()
        ]
        detail = "; ".join(preview) if preview else "nenhuma linha relacionada encontrada"
        raise ValueError(
            "Patrimônio líquido financeiro semanticamente válido não encontrado no BPP. "
            f"Linhas relacionadas: {detail}"
        )

    desc = eq["DESC_NORM"]
    is_nci_eq = desc.str.contains(
        r"nao\s+control|acionistas\s+nao\s+control|participacao.*nao\s+control",
        regex=True,
        na=False,
    )
    is_parent = (
        desc.str.contains(r"atribu[ií]vel|atribuido", regex=True, na=False)
        & desc.str.contains(r"controlador|controladora", regex=True, na=False)
        & ~is_nci_eq
    ) | desc.str.contains(
        r"socios.*controlador|acionistas.*controlador", regex=True, na=False
    )

    # A linha de não controladores pode se chamar apenas "Participação dos
    # Acionistas Não Controladores", sem conter literalmente "Patrimônio Líquido".
    # Por isso ela é procurada no BPP inteiro, ainda com filtro semântico próprio.
    nci_desc_all = x["DESC_NORM"]
    is_nci_all = (
        nci_desc_all.str.contains(r"nao\s+control", regex=True, na=False)
        & nci_desc_all.str.contains(
            r"participacao|acionistas|socios|patrimonio", regex=True, na=False
        )
        & ~nci_desc_all.str.contains(
            r"passiv|provis|emprestim|financiament|deposit", regex=True, na=False
        )
    )

    # Candidato a PL total: descrição agregada, sem indicar controladores/NCI e
    # sem ser uma subconta típica do patrimônio (capital, reservas, ajustes etc.).
    detail_terms = desc.str.contains(
        r"capital social|reserva|ajuste|lucros? acumul|prejuizos? acumul|"
        r"acoes em tesouraria|outros resultados abrangentes|dividendo",
        regex=True,
        na=False,
    )
    is_total = ~is_nci_eq & ~is_parent & ~detail_terms

    def choose_one(mask, role, frame=None):
        base = eq if frame is None else frame
        y = base[mask].copy()
        if y.empty:
            return None
        y["DEPTH"] = y["CODE"].str.count(r"\.")
        y["ABS_VL"] = y["NUM"].abs()
        # Uma linha por código e preferência pela conta mais agregada. Em empate,
        # usa o maior valor absoluto, evitando somar pai e filho.
        y = (
            y.sort_values(["DEPTH", "ABS_VL"], ascending=[True, False])
             .drop_duplicates("CODE", keep="first")
        )
        min_depth = y["DEPTH"].min()
        shallow = y[y["DEPTH"] == min_depth].copy()
        if len(shallow) > 1:
            # Se múltiplas contas agregadas diferentes permanecerem, só é seguro
            # escolher quando uma delas domina claramente em valor; caso contrário,
            # falha para não inventar qual agregado é o correto.
            shallow = shallow.sort_values("ABS_VL", ascending=False)
            if len(shallow) > 1:
                top = float(shallow.iloc[0]["ABS_VL"])
                second = float(shallow.iloc[1]["ABS_VL"])
                if second > 0 and top / second < 1.25:
                    labels = [
                        f"{r.CD_CONTA} - {r.DS_CONTA}"
                        for r in shallow.head(6).itertuples()
                    ]
                    raise ValueError(
                        f"BPP financeiro ambíguo para {role}: " + "; ".join(labels)
                    )
        return shallow.iloc[0]

    total_row = choose_one(is_total, "Patrimônio Líquido total")
    parent_row = choose_one(is_parent, "Patrimônio Líquido dos controladores")
    nci_row = choose_one(
        is_nci_all, "participação de não controladores", frame=x
    )

    if total_row is None and parent_row is None:
        labels = [f"{r.CD_CONTA} - {r.DS_CONTA}" for r in eq.head(12).itertuples()]
        raise ValueError(
            "Foram encontradas linhas patrimoniais, mas nenhuma conta agregada de "
            "Patrimônio Líquido total/controladores pôde ser identificada com segurança. "
            "Candidatos: " + "; ".join(labels)
        )

    if parent_row is not None:
        parent_equity = float(parent_row["NUM"])
    elif total_row is not None and nci_row is not None:
        parent_equity = float(total_row["NUM"]) - float(nci_row["NUM"])
    else:
        parent_equity = float(total_row["NUM"])

    if total_row is not None:
        total_equity = float(total_row["NUM"])
    elif nci_row is not None:
        total_equity = parent_equity + float(nci_row["NUM"])
    else:
        total_equity = parent_equity

    if not np.isfinite(total_equity) or not np.isfinite(parent_equity):
        raise ValueError("Patrimônio líquido financeiro extraído não é numérico/finito.")
    if total_equity <= 0 or parent_equity <= 0:
        raise ValueError(
            "Patrimônio líquido financeiro semanticamente identificado, porém não positivo."
        )
    labels = []
    seen = set()
    for row, role in [
        (total_row, "PL total"),
        (parent_row, "PL controladores"),
        (nci_row, "não controladores"),
    ]:
        if row is None:
            continue
        key = (str(row["CODE"]), str(row["DS_CONTA"]))
        if key in seen:
            continue
        seen.add(key)
        labels.append(
            f"{row['CD_CONTA']} - {row['DS_CONTA']} [{role}]"
        )

    return float(total_equity), float(parent_equity), labels

def _last_numeric_value(df, candidates, default=np.nan):
    """Retorna o último valor numérico encontrado entre nomes de coluna candidatos."""
    for col in candidates:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(vals):
                return float(vals.iloc[-1])
    return default


def get_share_structure(capital_df, cvm, year=None, ref_date=None):
    """Lê a composição de capital CVM sem decidir ainda a semântica final das ações."""
    x = _filter_company(capital_df, cvm)
    if x.empty:
        return {}

    if "DT_REFER" in x.columns:
        x["DT_REFER"] = pd.to_datetime(x["DT_REFER"], errors="coerce")
        if year is not None:
            x = x[x["DT_REFER"].dt.year == int(year)]
        if ref_date is not None and not x.empty:
            ref_date = pd.Timestamp(ref_date)
            exact = x[x["DT_REFER"] == ref_date]
            if not exact.empty:
                x = exact
            else:
                prior = x[x["DT_REFER"] <= ref_date]
                if not prior.empty:
                    x = prior
        if x.empty:
            return {}
        x = x[x["DT_REFER"] == x["DT_REFER"].max()]

    if "VERSAO" in x.columns and not x.empty:
        v = pd.to_numeric(x["VERSAO"], errors="coerce")
        if v.notna().any():
            x = x[v == v.max()]

    return {
        "issued_total_raw": _last_numeric_value(x, [
            "QT_ACAO_TOTAL_CAP_INTEGR", "QT_TOTAL_ACAO_CAP_INTEGR", "QT_TOTAL_ACAO_CAP_INTEGRALIZADO"
        ], np.nan),
        "treasury_total_raw": _last_numeric_value(x, [
            "QT_ACAO_TOTAL_TESOURO", "QT_TOTAL_ACAO_TESOURO"
        ], 0.0),
        "ordinary_issued_raw": _last_numeric_value(x, [
            "QT_ACAO_ORDIN_CAP_INTEGR", "QT_ACAO_ORDIN_CAP_INTEGRALIZADO"
        ], 0.0),
        "preferred_issued_raw": _last_numeric_value(x, [
            "QT_ACAO_PREF_CAP_INTEGR", "QT_ACAO_PREFER_CAP_INTEGR", "QT_ACAO_PREF_CAP_INTEGRALIZADO"
        ], 0.0),
        "ordinary_treasury_raw": _last_numeric_value(x, ["QT_ACAO_ORDIN_TESOURO"], 0.0),
        "preferred_treasury_raw": _last_numeric_value(x, ["QT_ACAO_PREF_TESOURO", "QT_ACAO_PREFER_TESOURO"], 0.0),
    }


def _official_share_reference(asset, ref_date):
    if ref_date is None:
        return np.nan
    key = pd.Timestamp(ref_date).date().isoformat()
    value = asset.get("official_shares_outstanding", {}).get(key, np.nan)
    return float(value) if pd.notna(value) else np.nan


def normalize_share_structure_for_asset(raw_struct, asset, ref_date=None):
    """
    Normaliza escala e valida ações em circulação.

    Regra-base CVM preservada:
        ações em circulação = QT_ACAO_TOTAL_CAP_INTEGR - QT_ACAO_TOTAL_TESOURO

    Exceção somente quando existe uma referência oficial da própria companhia na
    MESMA data e a composição CVM publicada é incompatível com ela. Nesse caso,
    entre os dois candidatos transparentes (capital-tesouraria e próprio campo
    capital), usa-se o candidato compatível com a referência oficial. Isso evita
    a dupla subtração observada na Vale em 30/06/2026 sem transformar a exceção
    em uma regra genérica para outras datas/empresas.
    """
    if not raw_struct:
        raise ValueError(f"Composição de capital indisponível para {asset['name']}.")

    issued_raw = raw_struct.get("issued_total_raw", np.nan)
    treasury_raw = raw_struct.get("treasury_total_raw", 0.0)
    if pd.isna(issued_raw) or not np.isfinite(issued_raw) or issued_raw <= 0:
        raise ValueError(f"Quantidade total de ações inválida na CVM para {asset['name']}.")

    issued_raw = float(issued_raw)
    treasury_raw = float(treasury_raw) if pd.notna(treasury_raw) and np.isfinite(treasury_raw) else 0.0
    lo = float(asset.get("shares_expected_min", 0.0))
    hi = float(asset.get("shares_expected_max", np.inf))

    chosen_factor = None
    for factor in (1.0, 1_000.0):
        reported = issued_raw * factor
        standard = (issued_raw - treasury_raw) * factor
        if (lo <= reported <= hi) or (lo <= standard <= hi):
            chosen_factor = factor
            break
    if chosen_factor is None:
        raise ValueError(
            f"Quantidade de ações fora da faixa de sanidade para {asset['name']}: "
            f"capital bruto={issued_raw:,.0f}; tesouraria bruta={treasury_raw:,.0f}; "
            f"faixa esperada={lo:,.0f} a {hi:,.0f}. Valuation interrompido."
        )

    factor = chosen_factor
    reported_total = issued_raw * factor
    treasury_total = max(treasury_raw * factor, 0.0)
    standard_outstanding = reported_total - treasury_total
    official_ref = _official_share_reference(asset, ref_date)

    # Regra padrão da CVM.
    chosen = standard_outstanding
    basis = "Regra CVM padrão: capital integralizado - ações em tesouraria"
    use_reported_as_outstanding = False

    if pd.notna(official_ref):
        err_standard = abs(standard_outstanding - official_ref) / official_ref if official_ref > 0 else np.inf
        err_reported = abs(reported_total - official_ref) / official_ref if official_ref > 0 else np.inf
        if err_reported + 1e-9 < err_standard:
            chosen = official_ref
            use_reported_as_outstanding = True
            basis = (
                "Referência oficial da companhia na mesma data: campo de capital CVM é compatível com ações em circulação; "
                "tesouraria não é subtraída uma segunda vez"
            )
        else:
            chosen = official_ref
            basis = "Referência oficial da companhia confirma a regra CVM capital - tesouraria"

    if not (lo <= chosen <= hi):
        raise ValueError(
            f"Ações finais fora da faixa de sanidade para {asset['name']}: {chosen:,.0f}; "
            f"faixa={lo:,.0f} a {hi:,.0f}."
        )

    on_issued = max(float(raw_struct.get("ordinary_issued_raw", 0.0) or 0.0) * factor, 0.0)
    pn_issued = max(float(raw_struct.get("preferred_issued_raw", 0.0) or 0.0) * factor, 0.0)
    on_treasury = max(float(raw_struct.get("ordinary_treasury_raw", 0.0) or 0.0) * factor, 0.0)
    pn_treasury = max(float(raw_struct.get("preferred_treasury_raw", 0.0) or 0.0) * factor, 0.0)

    if use_reported_as_outstanding:
        on_out = on_issued
        pn_out = pn_issued
    else:
        on_out = max(on_issued - on_treasury, 0.0)
        pn_out = max(pn_issued - pn_treasury, 0.0)

    # Ajusta apenas arredondamento das classes para a referência oficial, sem
    # alterar a proporção ON/PN reportada.
    class_sum = on_out + pn_out
    if pd.notna(official_ref) and class_sum > 0 and abs(class_sum - chosen) / chosen < 0.01:
        ratio = chosen / class_sum
        on_out *= ratio
        pn_out *= ratio

    return {
        "shares": float(chosen),
        "scale_factor": float(factor),
        "basis": basis,
        "official_reference": official_ref,
        "reported_total_scaled": float(reported_total),
        "treasury_total_scaled": float(treasury_total),
        "standard_outstanding": float(standard_outstanding),
        "ordinary_outstanding": float(on_out) if on_out > 0 else np.nan,
        "preferred_outstanding": float(pn_out) if pn_out > 0 else np.nan,
        "ordinary_issued_scaled": float(on_issued),
        "preferred_issued_scaled": float(pn_issued),
        "ordinary_treasury_scaled": float(on_treasury),
        "preferred_treasury_scaled": float(pn_treasury),
        "issued_total_raw": issued_raw,
        "treasury_total_raw": treasury_raw,
        "chosen_raw_equivalent": float(chosen / factor),
    }


def get_shares(capital_df, cvm, year=None, ref_date=None):
    """Compatibilidade: devolve a regra CVM padrão sem aplicar referência específica do ativo."""
    raw = get_share_structure(capital_df, cvm, year=year, ref_date=ref_date)
    if not raw:
        return np.nan
    issued = raw.get("issued_total_raw", np.nan)
    treasury = raw.get("treasury_total_raw", 0.0)
    if pd.isna(issued):
        return np.nan
    result = float(issued) - (float(treasury) if pd.notna(treasury) else 0.0)
    return result if result > 0 else np.nan


def normalize_shares_for_asset(raw_shares, asset):
    """Compatibilidade com chamadas antigas: normaliza um total simples por escala e sanidade."""
    if raw_shares is None or pd.isna(raw_shares) or not np.isfinite(raw_shares) or raw_shares <= 0:
        return np.nan, np.nan
    raw = float(raw_shares)
    lo = float(asset.get("shares_expected_min", 0.0))
    hi = float(asset.get("shares_expected_max", np.inf))
    if lo <= raw <= hi:
        return raw, 1.0
    scaled = raw * 1_000.0
    if lo <= scaled <= hi:
        return scaled, 1_000.0
    raise ValueError(
        f"Quantidade de ações fora da faixa de sanidade para {asset['name']}: "
        f"valor bruto={raw:,.0f}; após x1.000={scaled:,.0f}; faixa esperada={lo:,.0f} a {hi:,.0f}."
    )


# ================================================================
# 3) EXTRAÇÃO DE MÉTRICAS CONTÁBEIS
# ================================================================

def _first_dre_description_value(dre, patterns, prefix="3.", exclude_pattern=None):
    """
    Fallback conservador por descrição para métricas da DRE.

    Só é usado quando a conta padronizada esperada está ausente/inutilizável.
    Entre as linhas candidatas, prioriza a conta mais agregada (menor profundidade)
    e, em empate, o maior valor absoluto. Não soma linhas diferentes e não cria
    estimativas por diferença.
    """
    if dre is None or dre.empty or "DS_CONTA" not in dre.columns or "CD_CONTA" not in dre.columns:
        return np.nan, None

    x = dre.copy()
    x["CODE"] = x["CD_CONTA"].astype(str).str.strip()
    x["DESC"] = x["DS_CONTA"].astype(str)
    x["NUM"] = pd.to_numeric(x.get("VL_CONTA"), errors="coerce")
    x = x[x["NUM"].notna()].copy()
    if prefix:
        x = x[x["CODE"].str.startswith(str(prefix))].copy()
    if x.empty:
        return np.nan, None

    mask = pd.Series(False, index=x.index)
    for pattern in patterns:
        mask |= x["DESC"].str.contains(pattern, case=False, regex=True, na=False)
    if exclude_pattern:
        mask &= ~x["DESC"].str.contains(exclude_pattern, case=False, regex=True, na=False)

    y = x[mask].copy()
    if y.empty:
        return np.nan, None

    y["DEPTH"] = y["CODE"].str.count(r"\.")
    y["ABS_VL"] = y["NUM"].abs()
    y = y.sort_values(["DEPTH", "ABS_VL"], ascending=[True, False])
    r = y.iloc[0]
    return float(r["NUM"]), f"{r['CODE']} - {r['DESC']}"


def extract_revenue_from_dre(dre):
    """Receita: conta 3.01; fallback apenas por descrição explícita da própria DRE."""
    v = value_by_code(dre, "3.01", np.nan)
    if pd.notna(v):
        return float(v), (_label_for_code(dre, "3.01") or ["3.01"])[0]
    return _first_dre_description_value(
        dre,
        [r"receita.*(?:venda|servi[cç]|operacional|l[ií]quida)", r"^receita l[ií]quida"],
        prefix="3.",
        exclude_pattern=r"financeir|tribut|imposto|equival[eê]ncia",
    )


def extract_ebit_from_dre(dre):
    """EBIT contábil: conta 3.05; fallback por descrição de resultado antes do financeiro."""
    v = value_by_code(dre, "3.05", np.nan)
    if pd.notna(v):
        return float(v), (_label_for_code(dre, "3.05") or ["3.05"])[0]
    return _first_dre_description_value(
        dre,
        [r"resultado.*antes.*resultado financeiro", r"resultado operacional.*antes.*financeir"],
        prefix="3.",
    )


def extract_ebt_from_dre(dre):
    """EBT: conta 3.07; fallback por descrição de resultado antes dos tributos sobre o lucro."""
    v = value_by_code(dre, "3.07", np.nan)
    if pd.notna(v):
        return float(v), (_label_for_code(dre, "3.07") or ["3.07"])[0]
    return _first_dre_description_value(
        dre,
        [r"resultado.*antes.*tribut.*lucro", r"lucro.*antes.*tribut.*lucro"],
        prefix="3.",
    )


def extract_net_income_from_dre(dre):
    """
    Lucro líquido atribuível aos acionistas, com tratamento conservador do layout CVM.

    Regra:
    1) prefere 3.11.01 quando é material;
    2) se 3.11.01 estiver ausente OU for zero enquanto 3.11 é material, usa 3.11;
    3) se ambas faltarem, usa somente uma linha explicitamente descrita como lucro/
       prejuízo consolidado ou líquido do período.

    Isso corrige emissores em que 3.11.01 aparece zerada/inadequada no layout sem
    trocar silenciosamente o critério das companhias em que 3.11.01 é válido.
    """
    child = value_by_code(dre, "3.11.01", np.nan)
    parent = value_by_code(dre, "3.11", np.nan)

    child_ok = pd.notna(child) and np.isfinite(child)
    parent_ok = pd.notna(parent) and np.isfinite(parent)

    if child_ok and (abs(float(child)) > 1e-9 or not parent_ok or abs(float(parent)) <= 1e-9):
        return float(child), (_label_for_code(dre, "3.11.01") or ["3.11.01"])[0]
    if parent_ok:
        return float(parent), (_label_for_code(dre, "3.11") or ["3.11"])[0]
    if child_ok:
        return float(child), (_label_for_code(dre, "3.11.01") or ["3.11.01"])[0]

    return _first_dre_description_value(
        dre,
        [
            r"lucro.*preju[ií]zo.*consolidado.*per[ií]odo",
            r"lucro.*l[ií]quido.*(?:exerc[ií]cio|per[ií]odo)",
            r"resultado l[ií]quido.*(?:exerc[ií]cio|per[ií]odo)",
        ],
        prefix="3.",
        exclude_pattern=r"por a[cç][aã]o|b[aá]sico|dilu[ií]do|abrangente",
    )


def extract_metrics(dre, bpa, bpp, dfc, asset=None):
    revenue, revenue_label = extract_revenue_from_dre(dre)
    ebit, ebit_label = extract_ebit_from_dre(dre)
    ebt, ebt_label = extract_ebt_from_dre(dre)
    tax_raw = value_first_code(dre, ["3.08"], np.nan)
    tax_expense = abs(float(tax_raw)) if pd.notna(tax_raw) and np.isfinite(tax_raw) else np.nan
    net_income, net_income_label = extract_net_income_from_dre(dre)

    # D&A: somente reconciliação operacional da DFC-MI.
    da, da_labels = extract_da_from_dfc(dfc)

    # CAPEX: aquisições de imobilizado/intangível, evitando dupla contagem
    # entre contas-pai e contas-filhas.
    capex_profile = asset.get("capex_profile", "standard") if isinstance(asset, dict) else "standard"
    capex, capex_labels = extract_capex_from_dfc(dfc, profile=capex_profile)

    # Balanço: ausência da demonstração inteira NÃO é tratada como caixa/dívida zero.
    # Quando a BPA existe, preserva-se a regra anterior de tratar contas específicas
    # de caixa/aplicações não apresentadas como zero dentro daquela demonstração.
    if bpa is None or bpa.empty:
        current_assets = np.nan
        cash = np.nan
        fin_inv = np.nan
        liquid_assets = np.nan
    else:
        current_assets = value_first_code(bpa, ["1.01"], np.nan)
        cash = value_first_code(bpa, ["1.01.01"], 0.0)
        fin_inv = value_first_code(bpa, ["1.01.02"], 0.0)
        liquid_assets = max(cash, 0.0) + max(fin_inv, 0.0)

    current_liab = value_first_code(bpp, ["2.01"], np.nan)

    # Patrimônio líquido: preserva PL total e PL atribuível aos controladores.
    # O segundo é usado pelo módulo Residual Income para manter coerência com
    # lucro líquido atribuído aos controladores (3.11.01) quando disponível.
    equity_total, equity_parent, equity_labels = extract_equity_from_bpp(bpp)

    # Dívida: usa primeiro as contas agregadas padronizadas da CVM;
    # fallback textual apenas se elas não existirem. BPP ausente retorna NaN,
    # evitando que lacuna de fonte vire dívida zero silenciosamente.
    current_debt, noncurrent_debt, debt_labels = extract_debt_from_bpp(bpp)
    debt = (
        current_debt + noncurrent_debt
        if pd.notna(current_debt) and pd.notna(noncurrent_debt)
        else np.nan
    )

    # NWC operacional aproximado = AC - caixa/aplicações - PC + dívida financeira CP
    if all(pd.notna(v) for v in [current_assets, liquid_assets, current_liab, current_debt]):
        nwc = current_assets - liquid_assets - current_liab + current_debt
    else:
        nwc = np.nan

    # taxa efetiva normalizada depois, aqui apenas observada
    tax_rate = np.nan
    if pd.notna(ebt) and abs(ebt) > 1e-9:
        tax_rate = tax_expense / abs(ebt)

    ebitda = ebit + da if pd.notna(ebit) and pd.notna(da) else np.nan

    return {
        "revenue": revenue,
        "ebit": ebit,
        "ebt": ebt,
        "tax_expense": tax_expense,
        "tax_rate": tax_rate,
        "net_income": net_income,
        "da": da,
        "capex": capex,
        "current_assets": current_assets,
        "cash": liquid_assets,
        "current_liab": current_liab,
        "current_debt": current_debt,
        "debt": debt,
        "net_debt": debt - liquid_assets if pd.notna(debt) and pd.notna(liquid_assets) else np.nan,
        "nwc": nwc,
        "equity_total": equity_total,
        "equity_parent": equity_parent,
        "ebitda": ebitda,
        "da_labels": da_labels,
        "capex_labels": capex_labels,
        "debt_labels": debt_labels,
        "equity_labels": equity_labels,
        "revenue_label": revenue_label,
        "ebit_label": ebit_label,
        "ebt_label": ebt_label,
        "net_income_label": net_income_label,
    }


def load_annual_history(asset):
    """
    Carrega 2020 apenas como ano auxiliar para obter o Delta NWC de 2021.
    O histórico exibido continua sendo 2021–2025.

    Quando há referência oficial recorrente/proforma cadastrada para um período,
    ela é colocada em colunas separadas *_for_normalization. Os valores CVM
    originais permanecem intocados e continuam visíveis no histórico.
    """
    rows = []
    diagnostics = {}
    years_to_load = [AUX_NWC_YEAR] + list(HIST_YEARS)

    for year in years_to_load:
        pkg = load_cvm_package("DFP", year)

        # Seleção por companhia/ano/demonstração: prefere consolidado e só cai para
        # individual quando a base consolidada não possui linhas utilizáveis do emissor.
        # Cada demonstração é resolvida separadamente; CON e IND nunca são somados.
        dre, dre_source = _select_statement_rows(
            pkg, "DRE", asset["cvm"], year=year, cumulative=True
        )
        bpa, bpa_source = _select_statement_rows(
            pkg, "BPA", asset["cvm"], year=year
        )
        bpp, bpp_source = _select_statement_rows(
            pkg, "BPP", asset["cvm"], year=year
        )
        dfc, dfc_source = _select_statement_rows(
            pkg, "DFC", asset["cvm"], year=year, cumulative=True
        )

        m = extract_metrics(dre, bpa, bpp, dfc, asset=asset)
        m["year"] = year

        raw_struct = get_share_structure(pkg["CAPITAL"], asset["cvm"], year=year)
        if year in HIST_YEARS:
            # A quantidade histórica de ações é necessária para P/L, payout e market cap
            # históricos, mas NÃO é necessária para extrair Receita/EBIT/D&A/CAPEX/NWC nem
            # para o DCF atual. Portanto, uma lacuna isolada na tabela de composição de
            # capital de um ano antigo não deve derrubar o valuation inteiro.
            #
            # Importante: não há forward-fill/backfill de ações. Se a CVM não trouxer um
            # histórico utilizável, o ano fica NaN e é naturalmente excluído das medianas
            # de múltiplos. As ações do TTM continuam sendo críticas e validadas em load_ttm().
            try:
                share_info = normalize_share_structure_for_asset(
                    raw_struct,
                    asset,
                    ref_date=pd.Timestamp(year=year, month=12, day=31),
                )
                share_error = None
                m["shares"] = share_info["shares"]
                m["shares_raw"] = share_info.get("chosen_raw_equivalent", np.nan)
                m["shares_scale_factor"] = share_info.get("scale_factor", np.nan)
                m["shares_ordinary"] = share_info.get("ordinary_outstanding", np.nan)
                m["shares_preferred"] = share_info.get("preferred_outstanding", np.nan)
            except Exception as e:
                share_info = {}
                share_error = f"{type(e).__name__}: {e}"
                m["shares"] = np.nan
                m["shares_raw"] = np.nan
                m["shares_scale_factor"] = np.nan
                m["shares_ordinary"] = np.nan
                m["shares_preferred"] = np.nan
        else:
            share_info = {}
            share_error = None
            m["shares"] = np.nan
            m["shares_raw"] = np.nan
            m["shares_scale_factor"] = np.nan
            m["shares_ordinary"] = np.nan
            m["shares_preferred"] = np.nan

        # Por padrão, normalização = contábil.
        m["ebit_for_normalization"] = m["ebit"]
        m["ebitda_for_normalization"] = m["ebitda"]
        m["net_income_for_normalization"] = m["net_income"]

        # Vale 2025: referências oficiais discutidas. EBITDA Ajustado e lucro
        # líquido proforma são usados somente na normalização; DRE/DFC CVM não
        # são sobrescritas. EBIT recorrente é EBITDA ajustado - D&A CVM.
        adj_ebitda = asset.get("official_adjusted_ebitda", {}).get(year)
        if adj_ebitda is not None and pd.notna(m["da"]):
            m["ebitda_for_normalization"] = float(adj_ebitda)
            m["ebit_for_normalization"] = float(adj_ebitda) - float(m["da"])

        proforma_ni = asset.get("official_proforma_net_income", {}).get(year)
        if proforma_ni is not None:
            m["net_income_for_normalization"] = float(proforma_ni)

        diagnostics[year] = {
            "D&A": m.pop("da_labels"),
            "CAPEX": m.pop("capex_labels"),
            "Dívida": m.pop("debt_labels"),
            "Patrimônio líquido": m.pop("equity_labels"),
            "Receita DRE": m.pop("revenue_label", None),
            "EBIT DRE": m.pop("ebit_label", None),
            "EBT DRE": m.pop("ebt_label", None),
            "Lucro líquido DRE": m.pop("net_income_label", None),
            "Base demonstrações CVM": {
                "DRE": dre_source,
                "BPA": bpa_source,
                "BPP": bpp_source,
                "DFC": dfc_source,
            },
            "Ações": share_info,
            "Erro ações históricas": share_error,
        }
        rows.append(m)

    hist_all = pd.DataFrame(rows).set_index("year").sort_index()
    hist_all["delta_nwc"] = hist_all["nwc"].diff()
    # Base média de patrimônio para ROE histórico. O ano auxiliar 2020 permite
    # calcular o ROE de 2021 sem inventar patrimônio inicial.
    hist_all["avg_equity_parent"] = (
        hist_all["equity_parent"] + hist_all["equity_parent"].shift(1)
    ) / 2.0
    hist_all["roe_parent"] = hist_all["net_income"] / hist_all["avg_equity_parent"]
    hist_all["nopat"] = hist_all["ebit"] * (1 - hist_all["tax_rate"].clip(TAX_FLOOR, TAX_CEILING))
    hist_all["fcff"] = hist_all["nopat"] + hist_all["da"] - hist_all["capex"] - hist_all["delta_nwc"]

    # 2020 não aparece na saída; serviu somente como base do Delta NWC de 2021.
    hist = hist_all.loc[HIST_YEARS].copy()
    return hist, diagnostics


def load_ttm(asset):
    """TTM = DFP 2025 + ITR 2026 YTD - ITR 2025 YTD."""
    pkg25_dfp = load_cvm_package("DFP", 2025)
    pkg26 = load_cvm_package("ITR", CURRENT_ITR_YEAR)
    pkg25_itr = load_cvm_package("ITR", 2025)

    # Descobre a data do último ITR pela própria DRE da companhia, com fallback
    # CON -> IND por emissor. A existência global de *_con_ no ZIP não basta.
    dre_26_probe, dre_26_probe_source = _select_statement_rows(
        pkg26,
        "DRE",
        asset["cvm"],
        year=CURRENT_ITR_YEAR,
        cumulative=True,
    )
    if dre_26_probe.empty or "DT_REFER" not in dre_26_probe.columns:
        return None
    x26 = dre_26_probe.copy()
    x26["DT_REFER"] = pd.to_datetime(x26["DT_REFER"], errors="coerce")
    latest_ref = x26["DT_REFER"].max()
    if pd.isna(latest_ref):
        return None

    # 2025 anual
    dre_a, dre_a_source = _select_statement_rows(
        pkg25_dfp, "DRE", asset["cvm"], year=2025, cumulative=True
    )
    dfc_a, dfc_a_source = _select_statement_rows(
        pkg25_dfp, "DFC", asset["cvm"], year=2025, cumulative=True
    )

    # 2026 YTD
    dre_26, dre_26_source = _select_statement_rows(
        pkg26, "DRE", asset["cvm"], ref_date=latest_ref, cumulative=True
    )
    dfc_26, dfc_26_source = _select_statement_rows(
        pkg26, "DFC", asset["cvm"], ref_date=latest_ref, cumulative=True
    )
    bpa_26, bpa_26_source = _select_statement_rows(
        pkg26, "BPA", asset["cvm"], ref_date=latest_ref
    )
    bpp_26, bpp_26_source = _select_statement_rows(
        pkg26, "BPP", asset["cvm"], ref_date=latest_ref
    )

    # mesmo trimestre do ano anterior
    prior_ref = latest_ref - pd.DateOffset(years=1)
    dre_25q, dre_25q_source = _select_statement_rows(
        pkg25_itr, "DRE", asset["cvm"], ref_date=prior_ref, cumulative=True
    )
    dfc_25q, dfc_25q_source = _select_statement_rows(
        pkg25_itr, "DFC", asset["cvm"], ref_date=prior_ref, cumulative=True
    )
    bpa_25q, bpa_25q_source = _select_statement_rows(
        pkg25_itr, "BPA", asset["cvm"], ref_date=prior_ref
    )
    bpp_25q, bpp_25q_source = _select_statement_rows(
        pkg25_itr, "BPP", asset["cvm"], ref_date=prior_ref
    )

    def ttm_metric(extractor):
        a, la = extractor(dre_a)
        c, lc = extractor(dre_26)
        p, lp = extractor(dre_25q)
        if all(pd.notna(v) and np.isfinite(v) for v in [a, c, p]):
            return float(a + c - p), {
                "DFP 2025": la,
                f"ITR {latest_ref.year} YTD": lc,
                f"ITR {prior_ref.year} YTD": lp,
            }
        return np.nan, {
            "DFP 2025": la,
            f"ITR {latest_ref.year} YTD": lc,
            f"ITR {prior_ref.year} YTD": lp,
        }

    # DRE TTM — cada componente usa a mesma extração robusta do histórico anual.
    revenue, revenue_components = ttm_metric(extract_revenue_from_dre)
    ebit, ebit_components = ttm_metric(extract_ebit_from_dre)
    ebt, ebt_components = ttm_metric(extract_ebt_from_dre)
    net_income, net_income_components = ttm_metric(extract_net_income_from_dre)

    tax_a = abs(value_first_code(dre_a, ["3.08"], np.nan))
    tax_c = abs(value_first_code(dre_26, ["3.08"], np.nan))
    tax_p = abs(value_first_code(dre_25q, ["3.08"], np.nan))
    tax_expense = tax_a + tax_c - tax_p if all(pd.notna(v) for v in [tax_a, tax_c, tax_p]) else np.nan

    # D&A / CAPEX TTM: DFP 2025 + ITR 2026 YTD - ITR 2025 YTD.
    da_a, da_labels_a = extract_da_from_dfc(dfc_a)
    da_c, da_labels_c = extract_da_from_dfc(dfc_26)
    da_p, da_labels_p = extract_da_from_dfc(dfc_25q)
    da = da_a + da_c - da_p if all(np.isfinite(v) for v in [da_a, da_c, da_p]) else np.nan

    capex_profile = asset.get("capex_profile", "standard")
    cap_a, cap_labels_a = extract_capex_from_dfc(dfc_a, profile=capex_profile)
    cap_c, cap_labels_c = extract_capex_from_dfc(dfc_26, profile=capex_profile)
    cap_p, cap_labels_p = extract_capex_from_dfc(dfc_25q, profile=capex_profile)
    capex = cap_a + cap_c - cap_p if all(np.isfinite(v) for v in [cap_a, cap_c, cap_p]) else np.nan

    # Balanço atual e balanço comparável para Delta NWC TTM
    bal_cur = extract_metrics(pd.DataFrame(), bpa_26, bpp_26, pd.DataFrame(), asset=asset)
    bal_prev = extract_metrics(pd.DataFrame(), bpa_25q, bpp_25q, pd.DataFrame(), asset=asset)
    delta_nwc = bal_cur["nwc"] - bal_prev["nwc"] if pd.notna(bal_cur["nwc"]) and pd.notna(bal_prev["nwc"]) else np.nan

    tax_rate = tax_expense / abs(ebt) if pd.notna(ebt) and abs(ebt) > 1e-9 and pd.notna(tax_expense) else np.nan
    tax_norm = np.clip(tax_rate, TAX_FLOOR, TAX_CEILING) if pd.notna(tax_rate) else np.nan
    nopat = ebit * (1 - tax_norm) if pd.notna(ebit) and pd.notna(tax_norm) else np.nan
    fcff = nopat + da - capex - delta_nwc if all(pd.notna(v) for v in [nopat, da, capex, delta_nwc]) else np.nan

    # Quantidade de ações: preserva a regra CVM padrão, mas valida a data atual
    # contra referência oficial explícita quando ela existe. Isso corrige o caso
    # Vale 30/06/2026 em que subtrair tesouraria do campo reportado produz dupla
    # subtração em relação à quantidade oficial divulgada pela própria companhia.
    raw_struct = get_share_structure(pkg26["CAPITAL"], asset["cvm"], ref_date=latest_ref)
    if not raw_struct:
        raw_struct = get_share_structure(pkg25_dfp["CAPITAL"], asset["cvm"], year=2025)
    share_info = normalize_share_structure_for_asset(raw_struct, asset, ref_date=latest_ref)
    shares = share_info["shares"]

    ebitda = ebit + da if pd.notna(ebit) and pd.notna(da) else np.nan
    normalization_notes = []
    ebit_for_normalization = ebit
    ebitda_for_normalization = ebitda
    net_income_for_normalization = net_income

    # Ajuste recorrente da Vale: apenas dados oficiais explicitamente cadastrados.
    # Não converte EBITDA trimestral em USD para BRL e não estima itens que a fonte
    # oficial não forneceu em reais; isso evita criar uma premissa silenciosa.
    if asset.get("symbol") == "VALE3":
        qref = asset.get("official_proforma_net_income_quarters", {})
        annual_ref = asset.get("official_proforma_net_income", {}).get(2025)
        if pd.Timestamp(latest_ref).date().isoformat() == "2026-06-30" and annual_ref is not None:
            needed = ["2025Q1", "2025Q2", "2026Q1", "2026Q2"]
            if all(k in qref for k in needed):
                net_income_for_normalization = (
                    float(annual_ref)
                    + float(qref["2026Q1"]) + float(qref["2026Q2"])
                    - float(qref["2025Q1"]) - float(qref["2025Q2"])
                )
                normalization_notes.append(
                    "Vale TTM — lucro usado na normalização = lucro líquido proforma 2025 + 1S26 proforma - 1S25 proforma; "
                    f"resultado R$ {net_income_for_normalization/1e9:,.2f} bi."
                )
                normalization_notes.append(
                    "Vale TTM — EBITDA permanece contábil no TTM porque os releases 1T26/2T26 divulgam EBITDA Proforma em US$; "
                    "o código não inventa conversão cambial para criar um EBITDA TTM em reais."
                )

    return {
        "ref_date": latest_ref,
        "revenue": revenue,
        "ebit": ebit,
        "ebt": ebt,
        "tax_expense": tax_expense,
        "tax_rate": tax_rate,
        "net_income": net_income,
        "da": da,
        "capex": capex,
        "delta_nwc": delta_nwc,
        "nopat": nopat,
        "fcff": fcff,
        "ebitda": ebitda,
        "ebit_for_normalization": ebit_for_normalization,
        "ebitda_for_normalization": ebitda_for_normalization,
        "net_income_for_normalization": net_income_for_normalization,
        "cash": bal_cur["cash"],
        "debt": bal_cur["debt"],
        "net_debt": bal_cur["net_debt"],
        "nwc": bal_cur["nwc"],
        "equity_total": bal_cur["equity_total"],
        "equity_parent": bal_cur["equity_parent"],
        "shares": shares,
        "shares_raw": share_info.get("chosen_raw_equivalent", np.nan),
        "shares_scale_factor": share_info.get("scale_factor", np.nan),
        "share_info": share_info,
        "statement_sources": {
            "DFP 2025": {
                "DRE": dre_a_source,
                "DFC": dfc_a_source,
            },
            f"ITR {latest_ref.year} YTD": {
                "DRE": dre_26_source,
                "BPA": bpa_26_source,
                "BPP": bpp_26_source,
                "DFC": dfc_26_source,
            },
            f"ITR {prior_ref.year} YTD": {
                "DRE": dre_25q_source,
                "BPA": bpa_25q_source,
                "BPP": bpp_25q_source,
                "DFC": dfc_25q_source,
            },
        },
        "dre_components": {
            "Receita": revenue_components,
            "EBIT": ebit_components,
            "EBT": ebt_components,
            "Lucro líquido": net_income_components,
        },
        "normalization_notes": normalization_notes,
        "da_labels": da_labels_c,
        "capex_labels": cap_labels_c,
        "debt_labels": bal_cur["debt_labels"],
        "equity_labels": bal_cur["equity_labels"],
        "da_components": {
            "DFP 2025": da_a,
            f"ITR {latest_ref.year} YTD": da_c,
            f"ITR {prior_ref.year} YTD": da_p,
        },
        "capex_components": {
            "DFP 2025": cap_a,
            f"ITR {latest_ref.year} YTD": cap_c,
            f"ITR {prior_ref.year} YTD": cap_p,
        },
        "da_component_labels": {
            "DFP 2025": da_labels_a,
            f"ITR {latest_ref.year} YTD": da_labels_c,
            f"ITR {prior_ref.year} YTD": da_labels_p,
        },
        "capex_component_labels": {
            "DFP 2025": cap_labels_a,
            f"ITR {latest_ref.year} YTD": cap_labels_c,
            f"ITR {prior_ref.year} YTD": cap_labels_p,
        },
    }


# ================================================================
# 4) MERCADO, SELIC E BETA
# ================================================================

def _yahoo_chart_history(ticker, period="10y", interval="1d", auto_adjust=False, include_events=False):
    """
    Fallback direto para o endpoint público de chart do próprio Yahoo Finance.

    É a MESMA fonte de mercado já usada pelo yfinance; serve apenas para contornar
    falhas transitórias da biblioteca/wrapper. Tenta os hosts query1 e query2 do
    Yahoo. Não cria preço, dividendo ou ajuste sintético.
    """
    if not ticker:
        raise ValueError("Ticker de mercado ausente.")

    key = (ticker, str(period), str(interval), bool(auto_adjust), bool(include_events))
    if key in _YAHOO_JSON_CACHE:
        cached = _YAHOO_JSON_CACHE[key]
        return cached.copy() if isinstance(cached, pd.DataFrame) else cached

    params = {
        "range": str(period),
        "interval": str(interval),
        "events": "div,splits" if include_events else "history",
        "includeAdjustedClose": "true",
    }

    errors = []
    item = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            url = f"https://{host}/v8/finance/chart/{ticker}"
            r = SESSION.get(url, params=params, timeout=30)
            r.raise_for_status()
            payload = r.json()

            chart = payload.get("chart", {})
            error = chart.get("error")
            result = chart.get("result")
            if error:
                raise RuntimeError(str(error))
            if not result:
                raise RuntimeError("resultado vazio")

            item = result[0]
            break
        except Exception as e:
            errors.append(f"{host}: {type(e).__name__}: {e}")

    if item is None:
        raise RuntimeError(
            f"Yahoo chart não retornou resultado para {ticker}. "
            + " | ".join(errors[-2:])
        )

    timestamps = item.get("timestamp") or []
    indicators = item.get("indicators") or {}
    quote = (indicators.get("quote") or [{}])[0]
    closes = quote.get("close") or []

    if not timestamps or not closes:
        raise RuntimeError(f"Yahoo chart sem fechamentos para {ticker}.")

    n = min(len(timestamps), len(closes))
    idx = pd.to_datetime(timestamps[:n], unit="s", utc=True).tz_convert(None)
    close = pd.to_numeric(pd.Series(closes[:n], index=idx), errors="coerce")

    if auto_adjust:
        adj_groups = indicators.get("adjclose") or []
        if adj_groups:
            adj = adj_groups[0].get("adjclose") or []
            if adj:
                m = min(n, len(adj))
                adj_s = pd.to_numeric(pd.Series(adj[:m], index=idx[:m]), errors="coerce")
                close.loc[idx[:m]] = adj_s

    h = pd.DataFrame({"Close": close}).dropna(subset=["Close"])
    h = h[~h.index.duplicated(keep="last")].sort_index()

    if h.empty:
        raise RuntimeError(f"Yahoo chart sem fechamentos numéricos para {ticker}.")

    _YAHOO_JSON_CACHE[key] = h.copy()
    return h


def get_price_history(ticker, period="10y", interval="1d", auto_adjust=False):
    """
    Obtém histórico do Yahoo Finance com cache e três rotas, todas na mesma fonte:

      1) yfinance.Ticker.history;
      2) yfinance.download;
      3) endpoint chart público do próprio Yahoo Finance.

    Não cria preço sintético e não troca de provedor silenciosamente. Se as três
    rotas falharem, o erro é explícito e o ativo permanece em FAILED_ASSETS.
    """
    if not ticker:
        raise ValueError("Ticker de mercado ausente.")

    key = (ticker, period, interval, bool(auto_adjust))
    if key in _PRICE_CACHE:
        return _PRICE_CACHE[key].copy()

    errors = []
    h = pd.DataFrame()

    for attempt in range(3):
        try:
            t = yf.Ticker(ticker)
            h = t.history(
                period=period,
                interval=interval,
                auto_adjust=auto_adjust,
                actions=False,
            )
            if h is not None and not h.empty and "Close" in h.columns and h["Close"].dropna().size:
                break
        except Exception as e:
            errors.append(f"Ticker.history tentativa {attempt+1}: {type(e).__name__}: {e}")
        if attempt < 2:
            time.sleep(0.8 * (attempt + 1))

    if h is None or h.empty or "Close" not in h.columns or h["Close"].dropna().empty:
        try:
            h = yf.download(
                ticker,
                period=period,
                interval=interval,
                auto_adjust=auto_adjust,
                progress=False,
                threads=False,
            )
            if isinstance(h.columns, pd.MultiIndex):
                # Para um único ticker, remove o nível do ticker e preserva OHLCV.
                if ticker in h.columns.get_level_values(-1):
                    h = h.xs(ticker, axis=1, level=-1, drop_level=True)
                elif len(set(h.columns.get_level_values(-1))) == 1:
                    h.columns = h.columns.get_level_values(0)
        except Exception as e:
            errors.append(f"yf.download: {type(e).__name__}: {e}")
            h = pd.DataFrame()

    if h is None or h.empty or "Close" not in h.columns or h["Close"].dropna().empty:
        try:
            h = _yahoo_chart_history(
                ticker,
                period=period,
                interval=interval,
                auto_adjust=auto_adjust,
                include_events=False,
            )
        except Exception as e:
            errors.append(f"Yahoo chart direto: {type(e).__name__}: {e}")
            h = pd.DataFrame()

    if h is None or h.empty or "Close" not in h.columns or h["Close"].dropna().empty:
        detail = " | ".join(errors[-6:]) if errors else "sem detalhe adicional"
        raise RuntimeError(f"Sem cotações válidas para {ticker}. {detail}")

    h = h.copy()
    if getattr(h.index, "tz", None) is not None:
        h.index = h.index.tz_localize(None)
    h["Close"] = pd.to_numeric(h["Close"], errors="coerce")
    h = h.dropna(subset=["Close"])
    h = h[~h.index.duplicated(keep="last")].sort_index()

    if h.empty:
        raise RuntimeError(f"Sem fechamentos numéricos válidos para {ticker}.")

    _PRICE_CACHE[key] = h
    return h.copy()


def get_dividend_history(ticker, period="10y"):
    """
    Obtém dividendos do Yahoo sem inventar proventos e sem transformar falha de
    fonte em "dividendo zero".

    1) tenta yfinance.Ticker.dividends;
    2) valida os eventos no endpoint chart query1/query2 do próprio Yahoo.

    Série vazia é aceita somente quando o endpoint chart respondeu validamente e
    informou ausência de eventos. Se todas as rotas falharem, levanta erro explícito.
    """
    if not ticker:
        raise ValueError("Ticker de mercado ausente para dividendos.")

    yf_error = None
    try:
        div = yf.Ticker(ticker).dividends
        if div is not None and not div.empty:
            div = pd.to_numeric(div, errors="coerce").dropna()
            if getattr(div.index, "tz", None) is not None:
                div.index = div.index.tz_localize(None)
            if not div.empty:
                return div.sort_index()
    except Exception as e:
        yf_error = f"{type(e).__name__}: {e}"

    params = {
        "range": str(period),
        "interval": "1d",
        "events": "div",
        "includeAdjustedClose": "false",
    }
    errors = []

    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            url = f"https://{host}/v8/finance/chart/{ticker}"
            r = SESSION.get(url, params=params, timeout=30)
            r.raise_for_status()
            payload = r.json()

            chart = payload.get("chart", {})
            if chart.get("error"):
                raise RuntimeError(str(chart.get("error")))
            result = chart.get("result") or []
            if not result:
                raise RuntimeError("resultado vazio")

            events = (result[0].get("events") or {}).get("dividends") or {}
            rows = []
            for event in events.values():
                ts = event.get("date")
                amount = event.get("amount")
                if ts is None or amount is None:
                    continue
                try:
                    dt = pd.to_datetime(int(ts), unit="s", utc=True).tz_convert(None)
                    val = float(amount)
                except Exception:
                    continue
                if np.isfinite(val):
                    rows.append((dt, val))

            if not rows:
                # Resposta válida do Yahoo, sem dividendos no intervalo.
                return pd.Series(dtype=float)

            return pd.Series(
                [v for _, v in rows],
                index=pd.DatetimeIndex([d for d, _ in rows]),
                dtype=float,
            ).sort_index()

        except Exception as e:
            errors.append(f"{host}: {type(e).__name__}: {e}")

    details = []
    if yf_error:
        details.append(f"yfinance: {yf_error}")
    details.extend(errors)
    raise RuntimeError(
        f"Não foi possível validar histórico de dividendos para {ticker}. "
        + " | ".join(details[-3:])
    )


def current_price(ticker):
    """
    Último fechamento válido do Yahoo.

    A tentativa primária usa 1 mês. Se uma janela curta vier vazia por problema
    transitório de metadados, tenta 3 meses e 1 ano na mesma fonte antes de falhar.
    """
    errors = []
    for period in ("1mo", "3mo", "1y"):
        try:
            h = get_price_history(ticker, period, interval="1d", auto_adjust=False)
            close = pd.to_numeric(h["Close"], errors="coerce").dropna()
            if not close.empty:
                return float(close.iloc[-1])
        except Exception as e:
            errors.append(f"{period}: {type(e).__name__}: {e}")

    raise RuntimeError(
        f"Sem fechamento recente válido para {ticker}. " + " | ".join(errors[-3:])
    )


def get_selic_meta():
    """
    Selic Meta corrente do BCB (SGS 432).

    É mantida como diagnóstico macro, mas não é usada diretamente como Rf
    permanente no DCF/WACC.
    """
    url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
    r = SESSION.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise RuntimeError("BCB SGS 432 não retornou a Selic Meta atual.")
    return float(str(data[-1]["valor"]).replace(",", ".")) / 100.0


def _html_to_plain_text(raw_html):
    """Converte HTML da página pública da ANBIMA em texto simples para leitura da ETTJ."""
    if raw_html is None:
        return ""
    text = re.sub(r"(?is)<script.*?</script>", " ", str(raw_html))
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_anbima_long_term_risk_free():
    """
    Estima uma Rf nominal de longo prazo em BRL.

    Metodologia:
      Rf nominal BRL = ETTJ soberana prefixada ANBIMA - default spread Brasil

    A ETTJ soberana traz a taxa de mercado em reais, mas ainda contém risco
    soberano. A retirada do default spread evita tratar o prêmio de default do
    Brasil como se fosse remuneração livre de risco.

    Usa o vértice de 2.520 dias úteis (~10 anos) quando disponível. Se esse
    vértice não existir no dia, escolhe o vértice publicado mais próximo.

    Não existe fallback silencioso para a Selic Meta. Se a ANBIMA estiver
    indisponível, o valuation é interrompido, salvo se RF_OVERRIDE for definido.
    """
    if RF_OVERRIDE is not None:
        rate = float(RF_OVERRIDE)
        if not np.isfinite(rate) or rate <= 0:
            raise ValueError("RF_OVERRIDE inválido; use uma taxa decimal positiva, ex.: 0.125.")
        return {
            "rate": rate,
            "source": "RF_OVERRIDE",
            "curve_date": None,
            "vertex": None,
            "sovereign_curve_rate": np.nan,
            "default_spread": float(BRAZIL_DEFAULT_SPREAD),
        }

    r = SESSION.get(ANBIMA_CURVE_URL, timeout=45)
    r.raise_for_status()

    plain = _html_to_plain_text(r.text)
    block_match = re.search(
        r"ETTJ\s+PREFIXADOS.*?(?=ETTJ\s+IPCA|$)",
        plain,
        flags=re.I | re.S,
    )
    if not block_match:
        raise RuntimeError(
            "Não foi possível localizar o bloco 'ETTJ PREFIXADOS' na página pública da ANBIMA. "
            "Defina RF_OVERRIDE apenas se quiser forçar manualmente a Rf."
        )

    block = block_match.group(0)
    date_match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", block)
    curve_date = pd.to_datetime(
        date_match.group(1), format="%d/%m/%Y", errors="coerce"
    ) if date_match else pd.NaT

    # Formato publicado: vértice | fechamento D-1 | D0
    rows = re.findall(
        r"(?<![\d,])(\d{1,5})\s+(\d{1,3},\d{4})\s+(\d{1,3},\d{4})(?![\d,])",
        block,
    )
    if not rows:
        raise RuntimeError(
            "ANBIMA encontrada, mas nenhuma linha numérica da ETTJ prefixada pôde ser lida."
        )

    curve = pd.DataFrame(rows, columns=["vertex", "d_minus_1", "d0"])
    curve["vertex"] = pd.to_numeric(curve["vertex"], errors="coerce")
    for col in ["d_minus_1", "d0"]:
        curve[col] = pd.to_numeric(
            curve[col].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        )
    curve = curve.dropna(subset=["vertex", "d0"]).copy()
    if curve.empty:
        raise RuntimeError("ETTJ prefixada ANBIMA sem vértices/taxas válidos.")

    curve["distance"] = (curve["vertex"] - int(ANBIMA_TARGET_VERTEX)).abs()
    chosen = curve.sort_values(["distance", "vertex"]).iloc[0]
    vertex = int(chosen["vertex"])
    sovereign_curve_rate = float(chosen["d0"]) / 100.0
    default_spread = float(BRAZIL_DEFAULT_SPREAD)
    rf = sovereign_curve_rate - default_spread

    if not np.isfinite(sovereign_curve_rate) or sovereign_curve_rate <= 0:
        raise RuntimeError("Taxa soberana ANBIMA inválida.")
    if not np.isfinite(default_spread) or default_spread < 0:
        raise RuntimeError("Default spread Brasil inválido.")
    if not np.isfinite(rf) or rf <= 0:
        raise RuntimeError(
            f"Rf nominal calculada inválida: ANBIMA {sovereign_curve_rate:.2%} "
            f"- default spread {default_spread:.2%}."
        )

    return {
        "rate": float(rf),
        "source": "ANBIMA ETTJ prefixada soberana - default spread Brasil",
        "curve_date": curve_date,
        "vertex": vertex,
        "sovereign_curve_rate": sovereign_curve_rate,
        "default_spread": default_spread,
    }


def build_rate_context():
    """Monta o contexto macro usado por Ke/WACC, mantendo Selic spot apenas como diagnóstico."""
    selic_spot = get_selic_meta()
    long_rf = get_anbima_long_term_risk_free()

    return {
        "selic_spot": float(selic_spot),
        "valuation_rf": float(long_rf["rate"]),
        "rf_source": long_rf["source"],
        "curve_date": long_rf.get("curve_date"),
        "curve_vertex": long_rf.get("vertex"),
        "sovereign_curve_rate": long_rf.get("sovereign_curve_rate", np.nan),
        "default_spread": float(long_rf.get("default_spread", BRAZIL_DEFAULT_SPREAD)),
        "default_spread_asof": BRAZIL_DEFAULT_SPREAD_ASOF,
        "erp": float(EQUITY_RISK_PREMIUM),
        "erp_asof": EQUITY_RISK_PREMIUM_ASOF,
        "wacc_tax_rate": float(WACC_MARGINAL_TAX_RATE),
    }


def estimate_beta(stock_ticker, market_ticker="BOVA11.SA"):
    """
    Beta de 3 anos contra BOVA11. Usa preços ajustados diários e reamostragem semanal,
    evitando uma segunda chamada frágil específica de intervalo semanal.

    Preserva o fallback histórico beta=1,0 somente quando existem dados, mas a amostra
    é insuficiente para uma estimativa estável. Falha de download não é mascarada.
    """
    s_hist = get_price_history(stock_ticker, "3y", interval="1d", auto_adjust=True)
    m_hist = get_price_history(market_ticker, "3y", interval="1d", auto_adjust=True)

    s = pd.to_numeric(s_hist["Close"], errors="coerce").dropna().resample("W-FRI").last().dropna()
    m = pd.to_numeric(m_hist["Close"], errors="coerce").dropna().resample("W-FRI").last().dropna()

    r = pd.concat([s.rename("stock"), m.rename("market")], axis=1).dropna().pct_change().dropna()
    if len(r) < 30 or not np.isfinite(r["market"].var()) or r["market"].var() <= 0:
        return 1.0

    beta = r["stock"].cov(r["market"]) / r["market"].var()
    return float(beta) if np.isfinite(beta) else 1.0


def _year_end_price(prices, year):
    py = prices[prices.index.year == int(year)]["Close"].dropna()
    return float(py.iloc[-1]) if len(py) else np.nan


def current_company_market_cap(symbol, asset, ttm, target_price):
    """
    Valor de mercado atual da companhia inteira.

    Para companhias com ON e PN cadastradas, o modelo exige quantidade válida de
    cada classe e usa o preço de cada ticker. Não existe fallback silencioso para
    "preço da classe-alvo × todas as ações", pois isso distorceria WACC e EV quando
    as classes negociam a preços diferentes.
    """
    shares = float(ttm.get("shares", np.nan))
    share_info = ttm.get("share_info", {})

    ordinary_ticker = asset.get("ordinary_ticker")
    preferred_ticker = asset.get("preferred_ticker")
    ordinary_shares = share_info.get("ordinary_outstanding", np.nan)
    preferred_shares = share_info.get("preferred_outstanding", np.nan)

    if ordinary_ticker and preferred_ticker:
        if not (
            pd.notna(ordinary_shares) and pd.notna(preferred_shares)
            and np.isfinite(ordinary_shares) and np.isfinite(preferred_shares)
            and ordinary_shares > 0 and preferred_shares > 0
        ):
            raise ValueError(
                f"{symbol}: companhia possui ON/PN cadastradas, mas a composição "
                "de ações por classe no TTM está indisponível/inválida. "
                "Market Cap não será aproximado com uma única cotação."
            )

        ordinary_price = current_price(ordinary_ticker)
        preferred_price = current_price(preferred_ticker)
        market_cap = ordinary_price * ordinary_shares + preferred_price * preferred_shares
        return float(market_cap), {
            "method": "classes",
            "ordinary_ticker": ordinary_ticker,
            "preferred_ticker": preferred_ticker,
            "ordinary_price": ordinary_price,
            "preferred_price": preferred_price,
            "ordinary_shares": ordinary_shares,
            "preferred_shares": preferred_shares,
        }

    if not np.isfinite(shares) or shares <= 0:
        raise ValueError(f"{symbol}: quantidade total de ações inválida para Market Cap.")
    return float(target_price * shares), {
        "method": "single_ticker",
        "ticker": asset["ticker"],
        "price": target_price,
        "shares": shares,
    }


def get_split_history(ticker, period="max"):
    """
    Obtém eventos de desdobramento/grupamento do Yahoo, sem cadastrar fator manual.

    O histórico de preços do Yahoo é apresentado em base ajustada por splits. Para
    múltiplos históricos consistentes, a quantidade de ações contábil de cada ano
    precisa ser convertida para a mesma base acionária do preço histórico.
    """
    if not ticker:
        return pd.Series(dtype=float)

    key = (str(ticker), str(period))
    if key in _SPLIT_CACHE:
        return _SPLIT_CACHE[key].copy()

    errors = []
    try:
        s = yf.Ticker(ticker).splits
        if s is not None and not s.empty:
            s = pd.to_numeric(s, errors="coerce").dropna()
            if getattr(s.index, "tz", None) is not None:
                s.index = s.index.tz_localize(None)
            s = s[(s > 0) & np.isfinite(s)]
            if not s.empty:
                _SPLIT_CACHE[key] = s.sort_index()
                return _SPLIT_CACHE[key].copy()
    except Exception as e:
        errors.append(f"Ticker.splits: {type(e).__name__}: {e}")

    params = {
        "range": str(period),
        "interval": "1d",
        "events": "splits",
        "includeAdjustedClose": "false",
    }
    valid_response = False
    rows = []
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            url = f"https://{host}/v8/finance/chart/{ticker}"
            r = SESSION.get(url, params=params, timeout=30)
            r.raise_for_status()
            payload = r.json()
            chart = payload.get("chart", {})
            if chart.get("error"):
                raise RuntimeError(str(chart.get("error")))
            result = chart.get("result") or []
            if not result:
                raise RuntimeError("resultado vazio")
            valid_response = True
            events = (result[0].get("events") or {}).get("splits") or {}
            for ev in events.values():
                ts = ev.get("date")
                ratio = ev.get("splitRatio")
                num = ev.get("numerator")
                den = ev.get("denominator")
                factor = np.nan
                if pd.notna(num) and pd.notna(den):
                    try:
                        num = float(num); den = float(den)
                        if den != 0:
                            factor = num / den
                    except Exception:
                        factor = np.nan
                if not np.isfinite(factor) and ratio:
                    try:
                        a, b = str(ratio).replace("/", ":").split(":", 1)
                        factor = float(a) / float(b)
                    except Exception:
                        factor = np.nan
                if ts is not None and np.isfinite(factor) and factor > 0:
                    rows.append((pd.to_datetime(int(ts), unit="s"), float(factor)))
            break
        except Exception as e:
            errors.append(f"{host}: {type(e).__name__}: {e}")

    if rows:
        s = pd.Series({dt: factor for dt, factor in rows}, dtype=float).sort_index()
        _SPLIT_CACHE[key] = s
        return s.copy()
    if valid_response:
        s = pd.Series(dtype=float)
        _SPLIT_CACHE[key] = s
        return s.copy()

    raise RuntimeError(
        f"Não foi possível validar histórico de splits para {ticker}. "
        + " | ".join(errors[-4:])
    )


def _split_factor_after_date(splits, ref_date):
    """Produto dos fatores de split posteriores à data de referência."""
    if splits is None or len(splits) == 0:
        return 1.0
    ref = pd.Timestamp(ref_date)
    s = pd.to_numeric(pd.Series(splits), errors="coerce").dropna()
    if getattr(s.index, "tz", None) is not None:
        s.index = s.index.tz_localize(None)
    future = s[s.index > ref]
    if future.empty:
        return 1.0
    factor = float(np.prod(future.values))
    return factor if np.isfinite(factor) and factor > 0 else 1.0


def annual_market_data(symbol, asset, hist):
    target_ticker = asset["ticker"]
    prices = get_price_history(target_ticker, "10y")
    div = get_dividend_history(target_ticker, period="10y")
    target_splits = get_split_history(target_ticker, period="max")
    if not div.empty and getattr(div.index, "tz", None) is not None:
        div.index = div.index.tz_localize(None)

    ordinary_ticker = asset.get("ordinary_ticker")
    preferred_ticker = asset.get("preferred_ticker")
    ordinary_prices = get_price_history(ordinary_ticker, "10y") if ordinary_ticker else None
    preferred_prices = get_price_history(preferred_ticker, "10y") if preferred_ticker else None
    ordinary_splits = get_split_history(ordinary_ticker, period="max") if ordinary_ticker else pd.Series(dtype=float)
    preferred_splits = get_split_history(preferred_ticker, period="max") if preferred_ticker else pd.Series(dtype=float)

    out = hist.copy()
    # Preserva as quantidades exatamente como vieram da CVM antes de convertê-las
    # para a base acionária ajustada dos preços históricos do Yahoo.
    out["shares_reported"] = out.get("shares", np.nan)
    out["shares_ordinary_reported"] = out.get("shares_ordinary", np.nan)
    out["shares_preferred_reported"] = out.get("shares_preferred", np.nan)

    year_end_prices = []
    divs = []
    company_mcaps = []
    adjusted_total_shares = []
    adjusted_on_shares = []
    adjusted_pn_shares = []
    split_factors = []

    for y, row in out.iterrows():
        ref_date = pd.Timestamp(year=int(y), month=12, day=31)
        target_py = _year_end_price(prices, y)
        year_end_prices.append(target_py)
        dy = div[div.index.year == int(y)] if not div.empty else pd.Series(dtype=float)
        divs.append(float(dy.sum()) if len(dy) else 0.0)

        reported_total = row.get("shares_reported", np.nan)
        reported_on = row.get("shares_ordinary_reported", np.nan)
        reported_pn = row.get("shares_preferred_reported", np.nan)

        factor_target = _split_factor_after_date(target_splits, ref_date)
        adj_total = reported_total * factor_target if pd.notna(reported_total) else np.nan

        if ordinary_ticker and preferred_ticker:
            factor_on = _split_factor_after_date(ordinary_splits, ref_date)
            factor_pn = _split_factor_after_date(preferred_splits, ref_date)
            adj_on = reported_on * factor_on if pd.notna(reported_on) else np.nan
            adj_pn = reported_pn * factor_pn if pd.notna(reported_pn) else np.nan
            # Para a classe-alvo, registra o fator correspondente ao ticker usado no preço.
            factor_display = factor_pn if target_ticker == preferred_ticker else factor_on
        else:
            adj_on = reported_on * factor_target if pd.notna(reported_on) else np.nan
            adj_pn = reported_pn * factor_target if pd.notna(reported_pn) else np.nan
            factor_display = factor_target

        adjusted_total_shares.append(adj_total)
        adjusted_on_shares.append(adj_on)
        adjusted_pn_shares.append(adj_pn)
        split_factors.append(factor_display)

        if ordinary_ticker and preferred_ticker:
            if (
                ordinary_prices is not None and preferred_prices is not None
                and pd.notna(adj_on) and pd.notna(adj_pn)
                and adj_on > 0 and adj_pn > 0
            ):
                on_price = _year_end_price(ordinary_prices, y)
                pn_price = _year_end_price(preferred_prices, y)
                if pd.notna(on_price) and pd.notna(pn_price):
                    company_mcaps.append(on_price * adj_on + pn_price * adj_pn)
                else:
                    company_mcaps.append(np.nan)
            else:
                company_mcaps.append(np.nan)
        else:
            company_mcaps.append(
                target_py * adj_total
                if pd.notna(target_py) and pd.notna(adj_total)
                else np.nan
            )

    # A partir daqui shares/share classes ficam na MESMA base dos preços Yahoo,
    # permitindo EPS, P/L, payout e Market Cap históricos coerentes após splits.
    out["shares"] = adjusted_total_shares
    out["shares_ordinary"] = adjusted_on_shares
    out["shares_preferred"] = adjusted_pn_shares
    out["historical_split_factor"] = split_factors
    out["price_yend"] = year_end_prices
    out["dividend_ps"] = divs
    out["company_market_cap_yend"] = company_mcaps
    return out


# ================================================================
# 5) NORMALIZAÇÃO E PREMISSAS AUTOMÁTICAS
# ================================================================

def safe_median(series, default=np.nan):
    s = pd.Series(series).replace([np.inf, -np.inf], np.nan).dropna()
    return float(s.median()) if len(s) else default


def get_fcff_model_governance(asset, ri_module_ready=False, ri_module_reason=None):
    """
    Define como o preço-alvo deve ser apresentado por perfil econômico.

    O motor FCFF genérico continua existindo para todos os ativos não financeiros
    compatíveis. Para regulated, o RI economicamente coerente pode ocupar o slot
    principal de 50% sem alterar os três métodos secundários. Para high_roic_growth,
    a auditoria final mostrou que o RI patrimonial permanece excessivamente dependente
    do patrimônio contábil; por isso o DCF/FCFF volta a ser o método principal e o RI
    coerente permanece apenas como diagnóstico.

    Perfis:
      - custom_validated: regras específicas já auditadas (PETR4/VALE3).
      - generic: companhia operacional sem limitação setorial identificada.
      - cyclical: FCFF aplicável, com ressalva de ciclo.
      - regulated: FCFF genérico permanece diagnóstico; quando o RI coerente estiver
        completo e auditável, o alvo final usa RI coerente no slot principal de 50%.
      - high_roic_growth: DCF/FCFF volta ao slot principal de 50%; RI coerente é
        preservado como diagnóstico paralelo, sem calibração ao preço de mercado.
    """
    profile = str((asset or {}).get("fcff_profile", "generic")).strip().lower()

    if profile == "regulated":
        if ri_module_ready:
            return {
                "profile": profile,
                "validated_final_target": True,
                "status": "MÓDULO REGULADO CONTÁBIL ATIVO — RI COERENTE",
                "reason": (
                    "O FCFF genérico continua exibido como diagnóstico. O alvo final usa "
                    "Residual Income economicamente coerente no slot principal de 50%. O payout "
                    "somente pode subir quando o crescimento usado exige menos retenção do que "
                    "o payout histórico implica; nunca cai para fabricar crescimento. Se o ROE "
                    "do primeiro ano terminal produzido pelo próprio modelo ainda superar o Ke, "
                    "o RI positivo é capitalizado com o mesmo g terminal. Não foi inventada RAB, "
                    "WACC regulatório, ROE-alvo, prazo de fade ou calibração ao preço de mercado."
                    + (f" Observação: {ri_module_reason}" if ri_module_reason else "")
                ),
            }
        return {
            "profile": profile,
            "validated_final_target": False,
            "status": "DIAGNÓSTICO — MÓDULO REGULADO RI COERENTE INDISPONÍVEL",
            "reason": (
                "O FCFF genérico deduz o CAPEX integralmente. O módulo Residual Income "
                "coerente não pôde ser calculado com todos os dados necessários; nenhum "
                "fallback de RAB, ROE, patrimônio ou payout foi inventado."
                + (f" Motivo: {ri_module_reason}" if ri_module_reason else "")
            ),
        }

    if profile == "high_roic_growth":
        return {
            "profile": profile,
            "validated_final_target": True,
            "status": "MÓDULO HIGH-ROIC — DCF/FCFF PRINCIPAL; RI COERENTE DIAGNÓSTICO",
            "reason": (
                "A auditoria econômica mostrou que, mesmo após corrigir retenção/payout e "
                "o fechamento terminal, o RI continua excessivamente condicionado ao pequeno "
                "patrimônio contábil em empresas high-ROIC. Por isso o DCF/FCFF retorna ao slot "
                "principal de 50% e o RI coerente permanece visível apenas como diagnóstico. "
                "P/L, EV/EBITDA, Dividend Yield, Ke, WACC, crescimento e pesos 50/20/20/10 "
                "permanecem inalterados; nenhum valor é calibrado à cotação."
                + (f" Observação RI: {ri_module_reason}" if ri_module_reason else "")
            ),
        }

    if profile == "cyclical":
        return {
            "profile": profile,
            "validated_final_target": True,
            "status": "FCFF APLICÁVEL — SENSÍVEL AO CICLO",
            "reason": (
                "O motor FCFF é aplicável, mas margens, crescimento e CAPEX normalizados "
                "devem ser interpretados à luz do ciclo. Nenhum ajuste de ciclo adicional "
                "é imposto sem base quantitativa específica."
            ),
        }

    if profile == "custom_validated":
        return {
            "profile": profile,
            "validated_final_target": True,
            "status": "VALIDADO NO MOTOR ATUAL",
            "reason": "Regras específicas já auditadas e preservadas para o ativo.",
        }

    return {
        "profile": "generic",
        "validated_final_target": True,
        "status": "FCFF GENÉRICO APLICÁVEL",
        "reason": (
            "Nenhuma limitação setorial específica foi identificada que exija bloquear "
            "a publicação do composto do motor atual."
        ),
    }


def get_official_capex_split(asset):
    """
    Retorna a abertura oficial sustaining/growth do CAPEX quando ela foi
    explicitamente cadastrada a partir de divulgação da própria companhia.

    Não estima split ausente. Se não houver uma abertura oficial comparável,
    devolve None e o DCF continua usando somente CAPEX total.
    """
    raw = asset.get("official_capex_split") if asset else None
    if not raw:
        return None

    total = float(raw.get("total_usd", np.nan))
    sustaining = float(raw.get("sustaining_usd", np.nan))
    if not (np.isfinite(total) and np.isfinite(sustaining) and total > 0 and 0 <= sustaining <= total):
        raise ValueError(f"Split oficial de CAPEX inválido para {asset.get('name', 'ativo')}.")

    sustaining_share = sustaining / total
    growth_share = 1.0 - sustaining_share
    return {
        "reference_year": raw.get("reference_year"),
        "total_usd": total,
        "sustaining_usd": sustaining,
        "growth_usd": total - sustaining,
        "sustaining_share": float(sustaining_share),
        "growth_share": float(growth_share),
        "basis": raw.get("basis", "Referência oficial da companhia"),
    }



def _build_forward_windows(ref_date, n_years=PROJECTION_YEARS):
    """
    Constrói janelas forward de 12 meses a partir da data-base do TTM.

    Exemplo com TTM em 30/06/2026:
      Ano 1 = 01/07/2026 a 30/06/2027
      Ano 2 = 01/07/2027 a 30/06/2028

    A data-base não é contada novamente; o primeiro dia forward é o dia seguinte.
    """
    if ref_date is None or pd.isna(ref_date):
        return []

    base = pd.Timestamp(ref_date).normalize()
    windows = []
    for y in range(1, int(n_years) + 1):
        start = (base + pd.DateOffset(years=y - 1) + pd.Timedelta(days=1)).normalize()
        end = (base + pd.DateOffset(years=y)).normalize()
        windows.append({
            "year": y,
            "period_start": start,
            "period_end": end,
            "period_label": f"{start:%d/%m/%Y}–{end:%d/%m/%Y}",
            # Mantido por compatibilidade com saídas anteriores: é o ano em que
            # termina a janela forward, não um "ano calendário puro".
            "calendar_year": int(end.year),
        })
    return windows


def _parse_official_effect_period(effect_from):
    """
    Converte a granularidade temporal PUBLICADA do projeto em um intervalo.

    Formatos aceitos no cadastro atual:
      1S26 / 2S26  -> semestre inteiro
      1T27..4T27   -> trimestre inteiro
      2027         -> ano inteiro

    Não escolhe uma data pontual dentro de semestre/trimestre/ano e, portanto,
    não inventa mês de start-up. O intervalo publicado é preservado integralmente.
    """
    if effect_from is None:
        return None, None

    s = str(effect_from).upper().strip().replace(" ", "")

    def _year4(two_or_four):
        y = int(two_or_four)
        return y + 2000 if y < 100 else y

    m = re.fullmatch(r"([12])S(\d{2}|\d{4})", s)
    if m:
        sem = int(m.group(1))
        year = _year4(m.group(2))
        if sem == 1:
            return pd.Timestamp(year=year, month=1, day=1), pd.Timestamp(year=year, month=6, day=30)
        return pd.Timestamp(year=year, month=7, day=1), pd.Timestamp(year=year, month=12, day=31)

    m = re.fullmatch(r"([1-4])T(\d{2}|\d{4})", s)
    if m:
        quarter = int(m.group(1))
        year = _year4(m.group(2))
        start_month = 1 + (quarter - 1) * 3
        start = pd.Timestamp(year=year, month=start_month, day=1)
        end = (start + pd.DateOffset(months=3) - pd.Timedelta(days=1)).normalize()
        return start, end

    if re.fullmatch(r"\d{4}", s):
        year = int(s)
        return pd.Timestamp(year=year, month=1, day=1), pd.Timestamp(year=year, month=12, day=31)

    return None, None


def get_official_growth_timing(asset, projection_ref_date):
    """
    Monta uma AUDITORIA temporal dos marcos oficiais de produção/projetos.

    REGRA FINAL DE GOVERNANÇA DO MODELO:
    - Sem guidance anual quantitativo completo para cada janela forward, os marcos
      de projetos NÃO alteram numericamente a trajetória de crescimento do DCF.
    - Não se soma CAGR físico com capacidade de projeto e não se converte capacidade
      nominal em peso de crescimento, receita, EBITDA, IRR, ROIC ou ramp-up.
    - Semestre/trimestre/ano informado pela companhia é preservado como INTERVALO.
      O overlap calendário serve somente para mostrar em qual janela forward o marco
      divulgado se encontra.
    - Os guidances 2026 e objetivos 2030 continuam visíveis como contexto/auditoria,
      mas não são transformados em uma curva anual de receita sem guidance anual oficial.
    - A trajetória quantitativa de crescimento permanece a trajetória legada já
      aprovada pelo modelo. Isso elimina uma hipótese de escala não suportada por fonte.
    """
    raw = asset.get("official_growth_timing") if asset else None
    if not raw:
        return None

    base_return = {
        "enabled": False,
        "audit_only": True,
        "basis": raw.get("basis", ""),
        "products": [],
        "projects": raw.get("projects", []),
        "signals": [],
        "window_rows": [],
        "project_allocations": [],
    }

    if projection_ref_date is None or pd.isna(projection_ref_date):
        return {
            **base_return,
            "reason": "Data-base do TTM indisponível; trajetória legada preservada.",
        }

    ref_date = pd.Timestamp(projection_ref_date).normalize()
    reference_date_raw = raw.get("reference_base_date")
    if reference_date_raw is not None:
        reference_date = pd.Timestamp(reference_date_raw).normalize()
        if ref_date != reference_date:
            return {
                **base_return,
                "reason": (
                    f"Auditoria temporal cadastrada para base {reference_date.date().isoformat()}; "
                    f"base atual do valuation={ref_date.date().isoformat()}. "
                    "Trajetória legada preservada."
                ),
                "projection_ref_date": ref_date,
            }
    else:
        reference_base_year = int(raw.get("reference_base_year", -1))
        if int(ref_date.year) != reference_base_year:
            return {
                **base_return,
                "reason": (
                    f"Auditoria temporal cadastrada para base {reference_base_year}; "
                    f"base atual do valuation={ref_date.year}. Trajetória legada preservada."
                ),
                "projection_ref_date": ref_date,
            }

    products = raw.get("products", {})
    validated = []
    total_weight_raw = 0.0

    for name, p in products.items():
        actual25 = float(p.get("actual_2025", np.nan))
        v26_min = float(p.get("guidance_2026_min", np.nan))
        v26_max = float(p.get("guidance_2026_max", np.nan))
        v30_min = float(p.get("target_2030_min", np.nan))
        v30_max = float(p.get("target_2030_max", np.nan))
        rev = float(p.get("revenue_2025_usd_m", np.nan))

        vals = [actual25, v26_min, v26_max, v30_min, v30_max, rev]
        if not all(np.isfinite(v) for v in vals):
            raise ValueError(
                f"Auditoria operacional oficial incompleta para {asset.get('name', 'ativo')} / {name}."
            )
        if min(v26_min, v26_max, v30_min, v30_max, rev) <= 0:
            raise ValueError(
                f"Auditoria operacional oficial inválida para {asset.get('name', 'ativo')} / {name}."
            )

        v26 = 0.5 * (v26_min + v26_max)
        v30 = 0.5 * (v30_min + v30_max)
        cagr_26_30 = (v30 / v26) ** (1 / 4) - 1

        row = {
            "product": name,
            "actual_2025": actual25,
            "guidance_2026_mid": float(v26),
            "target_2030_mid": float(v30),
            # Somente diagnóstico entre duas âncoras oficiais; NÃO entra no DCF.
            "cagr_2026_2030": float(cagr_26_30),
            "revenue_weight_raw": float(rev),
            "unit": p.get("unit", ""),
        }
        validated.append(row)
        total_weight_raw += rev

    if total_weight_raw > 0:
        for row in validated:
            # Somente contexto econômico da tabela; NÃO entra no crescimento projetado.
            row["revenue_weight"] = row["revenue_weight_raw"] / total_weight_raw
    else:
        for row in validated:
            row["revenue_weight"] = np.nan

    windows = _build_forward_windows(ref_date, PROJECTION_YEARS)
    needed = max(PROJECTION_YEARS - 1, 0)
    preterminal_windows = windows[:needed]

    project_names_by_year = {w["year"]: [] for w in preterminal_windows}
    project_allocations = []
    enriched_projects = []

    for project in raw.get("projects", []):
        p = dict(project)
        effect_start, effect_end = _parse_official_effect_period(p.get("effect_from"))
        p["effect_period_start"] = effect_start
        p["effect_period_end"] = effect_end
        p["forward_allocation"] = []

        if (
            effect_start is not None
            and effect_end is not None
            and effect_end >= effect_start
        ):
            event_days = (effect_end - effect_start).days + 1
            for w in preterminal_windows:
                overlap_start = max(effect_start, w["period_start"])
                overlap_end = min(effect_end, w["period_end"])

                if overlap_end >= overlap_start:
                    overlap_days = (overlap_end - overlap_start).days + 1
                    allocation = overlap_days / event_days

                    alloc_row = {
                        "project": p.get("name", "n/d"),
                        "product": p.get("product", "n/d"),
                        "effect_from": p.get("effect_from", "n/d"),
                        "effect_period_start": effect_start,
                        "effect_period_end": effect_end,
                        "forward_year": w["year"],
                        "period_label": w["period_label"],
                        # Percentual do INTERVALO PUBLICADO que cai na janela.
                        # Não é ramp-up nem peso econômico.
                        "calendar_overlap": float(allocation),
                    }
                    project_allocations.append(alloc_row)
                    p["forward_allocation"].append(alloc_row)
                    project_names_by_year[w["year"]].append(p.get("name", "Projeto"))

        enriched_projects.append(p)

    window_rows = []
    for w in preterminal_windows:
        window_rows.append({
            **w,
            "projects_activating": ", ".join(project_names_by_year[w["year"]]) or "—",
        })

    return {
        "enabled": False,
        "audit_only": True,
        "reason": (
            "Marcos oficiais mantidos SOMENTE como auditoria temporal. "
            "Sem guidance anual quantitativo completo por janela forward, o modelo "
            "não usa capacidade de projeto, CAGR físico ou overlap de datas como peso "
            "numérico do crescimento. Trajetória de crescimento legada preservada."
        ),
        "basis": raw.get("basis", ""),
        "projection_ref_date": ref_date,
        "products": validated,
        "projects": enriched_projects,
        "signals": [],
        "window_rows": window_rows,
        "project_allocations": project_allocations,
    }


def build_growth_path(assump, scenario):
    """
    Produz a trajetória anual de crescimento da receita nas janelas forward.

    REGRA FINAL:
    - O crescimento quantitativo continua sendo a trajetória legada já aprovada:
      crescimento inicial normalizado -> g terminal do cenário.
    - Marcos de projetos, capacidade nominal, guidance 2026 e objetivo 2030 ficam
      disponíveis na auditoria, mas NÃO redistribuem crescimento sem guidance anual
      quantitativo oficial suficiente para cada janela.
    - Portanto, não existe mais soma de CAGR físico + score de capacidade, nem qualquer
      outra escala arbitrária de timing.
    """
    g0 = assump["base_growth"] + scenario["growth_shift"]
    terminal_g = max(-0.01, TERMINAL_GROWTH + scenario["terminal_g_shift"])

    legacy = []
    for y in range(1, PROJECTION_YEARS + 1):
        if PROJECTION_YEARS == 1:
            g = g0
        else:
            frac = (y - 1) / (PROJECTION_YEARS - 1)
            g = g0 * (1 - frac) + terminal_g * frac
        if g <= -0.999:
            raise ValueError("Crescimento projetado inválido (<= -99,9%).")
        legacy.append(float(g))

    ref_date = assump.get("projection_ref_date")
    windows = _build_forward_windows(ref_date, PROJECTION_YEARS)
    if len(windows) != PROJECTION_YEARS:
        base_year = int(assump.get("projection_base_year", 0) or 0)
        windows = [{
            "year": y,
            "period_start": pd.NaT,
            "period_end": pd.NaT,
            "period_label": f"Ano {y}",
            "calendar_year": base_year + y if base_year else y,
        } for y in range(1, PROJECTION_YEARS + 1)]

    timing = assump.get("growth_timing")
    window_rows = timing.get("window_rows", []) if isinstance(timing, dict) else []
    window_by_year = {int(r["year"]): r for r in window_rows if "year" in r}

    # Auditoria matemática: nesta versão growth DEVE ser idêntico ao legado.
    applied = list(legacy)
    legacy_factor = float(np.prod(1 + np.asarray(legacy, dtype=float)))
    applied_factor = float(np.prod(1 + np.asarray(applied, dtype=float)))
    if abs(applied_factor - legacy_factor) > 1e-12 * max(1.0, abs(legacy_factor)):
        raise RuntimeError("Governança de crescimento violada: trajetória aplicada divergiu do legado.")

    return pd.DataFrame({
        "year": [w["year"] for w in windows],
        "calendar_year": [w["calendar_year"] for w in windows],
        "period_start": [w["period_start"] for w in windows],
        "period_end": [w["period_end"] for w in windows],
        "period_label": [w["period_label"] for w in windows],
        "legacy_growth": legacy,
        "growth": applied,
        # Campos preservados por compatibilidade com as tabelas/retornos existentes.
        "timing_signal": [np.nan] * PROJECTION_YEARS,
        "timing_baseline_signal": [np.nan] * PROJECTION_YEARS,
        "timing_project_signal": [np.nan] * PROJECTION_YEARS,
        "timing_projects": [
            window_by_year.get(y, {}).get("projects_activating", "—")
            for y in range(1, PROJECTION_YEARS + 1)
        ],
        "timing_applied": [False] * PROJECTION_YEARS,
    })


def normalize_assumptions(hist, ttm, rf, beta, price, market_cap_override=None, asset=None):
    h = hist.copy()

    # Crescimento anual histórico (não usa TTM para não misturar janelas)
    growth = h["revenue"].pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    growth_recent = growth.tail(3)
    base_growth = safe_median(growth_recent, np.nan)
    if pd.isna(base_growth) or not np.isfinite(base_growth):
        raise ValueError(
            "Crescimento histórico recente indisponível; o modelo não aplica "
            "crescimento padrão arbitrário."
        )
    base_growth = float(np.clip(base_growth, AUTO_GROWTH_FLOOR, AUTO_GROWTH_CEILING))

    # Conjunto recente: 2023-2025 + TTM quando válido.
    # As colunas *_for_normalization preservam a informação contábil original e
    # só alteram o insumo de normalização quando há referência oficial explícita.
    recent = h.tail(3).copy()
    metric_rows = [r.to_dict() for _, r in recent.iterrows()]
    if ttm is not None:
        metric_rows.append(ttm)
    rr = pd.DataFrame(metric_rows)

    ebit_series = rr["ebit_for_normalization"] if "ebit_for_normalization" in rr.columns else rr["ebit"]
    ni_series = rr["net_income_for_normalization"] if "net_income_for_normalization" in rr.columns else rr["net_income"]

    ebit_margin = safe_median(ebit_series / rr["revenue"], np.nan)
    da_ratio = safe_median(rr["da"] / rr["revenue"], np.nan)
    capex_ratio = safe_median(rr["capex"] / rr["revenue"], np.nan)

    # Composição econômica do CAPEX. O split sustaining/growth é usado SOMENTE
    # quando existe uma abertura oficial explícita da própria companhia.
    # Importante: isso NÃO reduz o CAPEX do DCF. Todo o CAPEX continua sendo
    # saída de caixa; a decomposição serve para (i) política de dividendos da Vale
    # e (ii) medir separadamente o capital de crescimento nos diagnósticos.
    capex_split = get_official_capex_split(asset)

    # Auditoria temporal oficial: usa a DATA EXATA do TTM e janelas forward de
    # 12 meses. Sem guidance anual quantitativo suficiente, essa auditoria NÃO altera
    # a trajetória de crescimento; serve apenas para localizar os marcos divulgados.
    projection_ref_date = (
        pd.Timestamp(ttm["ref_date"]).normalize()
        if ttm is not None and ttm.get("ref_date") is not None and pd.notna(ttm.get("ref_date"))
        else None
    )
    projection_base_year = int(projection_ref_date.year) if projection_ref_date is not None else None
    growth_timing = get_official_growth_timing(asset, projection_ref_date)

    # Capital de giro — CORREÇÃO METODOLÓGICA:
    # O modelo anterior normalizava Delta NWC / Receita e depois aplicava essa
    # porcentagem sobre TODA a receita projetada em cada ano. Como Delta NWC já é
    # uma variação, isso fazia a empresa consumir/liberar uma fração da receita
    # inteira repetidamente, mesmo quando a direção do crescimento mudava.
    #
    # Agora normalizamos o NÍVEL de capital de giro operacional:
    #     NWC normalizado = mediana(NWC operacional / Receita)
    # e o Delta NWC projetado será obtido pela diferença entre dois níveis
    # consecutivos de NWC. Assim, o capital de giro reage à VARIAÇÃO da receita.
    nwc_ratio = safe_median(rr["nwc"] / rr["revenue"], np.nan)

    # Métrica antiga preservada somente como diagnóstico/auditoria. Ela NÃO é mais
    # usada para projetar o FCFF.
    d_nwc_ratio_observed = safe_median(rr["delta_nwc"] / rr["revenue"], np.nan)

    net_margin = safe_median(ni_series / rr["revenue"], np.nan)
    tax_rate = safe_median(rr["tax_rate"], np.nan)

    critical = {
        "margem EBIT": ebit_margin,
        "D&A/Receita": da_ratio,
        "CAPEX/Receita": capex_ratio,
        "NWC operacional/Receita": nwc_ratio,
        "margem líquida": net_margin,
        "taxa efetiva": tax_rate,
    }
    missing = [k for k, v in critical.items() if pd.isna(v) or not np.isfinite(v)]
    if missing:
        raise ValueError(
            "Premissas críticas indisponíveis: " + ", ".join(missing) + ". "
            "O valuation foi interrompido; não será aplicado fallback contábil silencioso."
        )

    tax_rate = float(np.clip(tax_rate, TAX_FLOOR, TAX_CEILING))

    # Contas atuais
    latest = ttm if ttm is not None else h.iloc[-1].to_dict()
    shares = latest.get("shares", np.nan)
    debt = latest.get("debt", np.nan)
    cash = latest.get("cash", np.nan)
    net_debt = latest.get("net_debt", np.nan)
    current_nwc = latest.get("nwc", np.nan)
    equity_parent = latest.get("equity_parent", np.nan)

    # Se algum campo do ITR não estiver disponível, usa o último DFP anual.
    # O NWC atual é mantido como diagnóstico; a base projetiva é normalizada
    # por NWC/Receita para evitar uma correção instantânea arbitrária no ano 1.
    last_annual = h.iloc[-1]
    if pd.isna(shares): shares = last_annual.get("shares", np.nan)
    if pd.isna(debt): debt = last_annual.get("debt", np.nan)
    if pd.isna(cash): cash = last_annual.get("cash", np.nan)
    if pd.isna(net_debt): net_debt = last_annual.get("net_debt", np.nan)
    if pd.isna(current_nwc): current_nwc = last_annual.get("nwc", np.nan)
    if pd.isna(equity_parent): equity_parent = last_annual.get("equity_parent", np.nan)

    if pd.isna(shares) or not np.isfinite(shares) or shares <= 0:
        raise ValueError("Quantidade de ações inválida; valuation interrompido.")
    if pd.isna(net_debt) or not np.isfinite(net_debt):
        raise ValueError("Dívida líquida inválida; valuation interrompido.")
    if pd.isna(current_nwc) or not np.isfinite(current_nwc):
        raise ValueError("NWC operacional atual inválido; valuation interrompido.")
    if pd.isna(price) or not np.isfinite(price) or price <= 0:
        raise ValueError("Preço de mercado inválido; valuation interrompido.")

    market_cap = float(market_cap_override) if pd.notna(market_cap_override) and np.isfinite(market_cap_override) and market_cap_override > 0 else price * shares

    # CAPM local em BRL:
    # Ke = Rf nominal BRL de longo prazo + beta × ERP total Brasil.
    # O ERP total Brasil já incorpora o componente de risco-país; portanto,
    # nenhum CRP adicional é somado novamente.
    cost_equity = rf + beta * EQUITY_RISK_PREMIUM

    # Kd bruto: a Rf foi depurada do risco soberano para o CAPM. Para a dívida
    # corporativa, esse risco soberano precisa voltar, além do spread corporativo
    # de 2,5 p.p. já acordado:
    #     Kd = Rf default-free + default spread Brasil + spread corporativo
    # Quando a Rf vem da ETTJ ANBIMA - default spread, isso é algebricamente
    # equivalente a: Kd = ETTJ soberana + spread corporativo.
    country_default_spread = float(BRAZIL_DEFAULT_SPREAD)
    corporate_debt_spread = float(DEBT_SPREAD)
    cost_debt = rf + country_default_spread + corporate_debt_spread

    # Escudo fiscal do WACC: usa alíquota marginal. A taxa efetiva histórica
    # acima permanece sendo usada no NOPAT/FCFF e não é sobrescrita.
    wacc_tax_rate = float(WACC_MARGINAL_TAX_RATE)

    if all(pd.notna(v) and np.isfinite(v) and v >= 0 for v in [market_cap, debt]) and (market_cap + debt) > 0:
        ew = market_cap / (market_cap + debt)
        dw = debt / (market_cap + debt)
        wacc = ew * cost_equity + dw * cost_debt * (1 - wacc_tax_rate)
    else:
        ew, dw = 1.0, 0.0
        wacc = cost_equity

    return {
        "base_growth": base_growth,
        "ebit_margin": float(ebit_margin),
        "da_ratio": float(max(da_ratio, 0.0)),
        "capex_ratio": float(max(capex_ratio, 0.0)),
        "capex_profile": asset.get("capex_profile", "standard") if isinstance(asset, dict) else "standard",
        "capex_split": capex_split,
        "sustaining_capex_share": (
            float(capex_split["sustaining_share"]) if capex_split is not None else np.nan
        ),
        "growth_capex_share": (
            float(capex_split["growth_share"]) if capex_split is not None else np.nan
        ),
        "projection_base_year": projection_base_year,
        "projection_ref_date": projection_ref_date,
        "growth_timing": growth_timing,
        # NWC/Receita é a premissa efetivamente usada na projeção.
        "nwc_ratio": float(nwc_ratio),
        # Preservado apenas como diagnóstico de comparação com a versão anterior.
        "d_nwc_ratio": float(d_nwc_ratio_observed) if pd.notna(d_nwc_ratio_observed) and np.isfinite(d_nwc_ratio_observed) else np.nan,
        "current_nwc": float(current_nwc),
        "net_margin": float(net_margin),
        "tax_rate": tax_rate,
        "rf": rf,
        "erp": float(EQUITY_RISK_PREMIUM),
        "erp_asof": EQUITY_RISK_PREMIUM_ASOF,
        "beta": beta,
        "cost_equity": cost_equity,
        "country_default_spread": country_default_spread,
        "corporate_debt_spread": corporate_debt_spread,
        "cost_debt": cost_debt,
        "wacc_tax_rate": wacc_tax_rate,
        "wacc": float(wacc),
        "equity_weight": ew,
        "debt_weight": dw,
        "shares": shares,
        "debt": debt,
        "cash": cash,
        "net_debt": net_debt,
        "market_cap": market_cap,
        "equity_parent": (
            float(equity_parent)
            if pd.notna(equity_parent) and np.isfinite(equity_parent)
            else np.nan
        ),
    }


# ================================================================
# 6) DCF FCFF
# ================================================================

def project_fcff(start_revenue, assump, scenario):
    """
    Projeta os cinco anos explícitos preservando as premissas já aprovadas de
    margem EBIT, D&A/Receita, CAPEX/Receita, imposto e crescimento.

    As projeções são janelas forward de 12 meses a partir da data-base do TTM.
    Ex.: TTM 30/06/2026 -> Ano 1 = 01/07/2026–30/06/2027.

    CAPITAL DE GIRO:
        NWC_t = Receita_t × (NWC/Receita normalizado)
        Delta NWC_t = NWC_t - NWC_(t-1)

    Reinvestimento líquido TOTAL:
        CAPEX total - D&A + Delta NWC

    FCFF:
        NOPAT - Reinvestimento líquido total
      = NOPAT + D&A - CAPEX total - Delta NWC

    Quando existe split oficial sustaining/growth:
        CAPEX sustaining = CAPEX total × participação oficial sustaining
        CAPEX growth = CAPEX total - CAPEX sustaining

    TIMING DO GROWTH CAPEX / BENEFÍCIO OPERACIONAL:
    - O CAPEX growth do próprio ano NÃO recebe automaticamente o crescimento do
      próprio ano.
    - Janelas forward e marcos oficiais são preservados como AUDITORIA.
    - Sem guidance anual quantitativo completo, build_growth_path() NÃO redistribui
      crescimento por capacidade, CAGR físico, overlap ou score de projeto.
    - A trajetória aplicada é idêntica à trajetória legada do cenário.
    - O antigo retorno growth contemporâneo é preservado apenas como diagnóstico.

    CAPEX sustaining e growth continuam ambos 100% como saídas de caixa no FCFF.
    """
    ebit_margin = assump["ebit_margin"] + scenario["ebit_margin_shift"]
    capex_ratio = max(0.0, assump["capex_ratio"] + scenario["capex_ratio_shift"])
    da_ratio = assump["da_ratio"]
    nwc_ratio = assump["nwc_ratio"]
    sustaining_share = assump.get("sustaining_capex_share", np.nan)
    tax = assump["tax_rate"]

    growth_path = build_growth_path(assump, scenario)

    rows = []
    revenue = float(start_revenue)

    previous_nwc = revenue * nwc_ratio

    for gp in growth_path.itertuples(index=False):
        y = int(gp.year)
        g = float(gp.growth)
        legacy_g = float(gp.legacy_growth)
        calendar_year = int(gp.calendar_year) if gp.calendar_year else y

        period_start = pd.Timestamp(gp.period_start) if pd.notna(gp.period_start) else pd.NaT
        period_end = pd.Timestamp(gp.period_end) if pd.notna(gp.period_end) else pd.NaT
        period_label = str(gp.period_label)

        timing_signal = float(gp.timing_signal) if pd.notna(gp.timing_signal) else np.nan
        timing_baseline_signal = (
            float(gp.timing_baseline_signal)
            if pd.notna(gp.timing_baseline_signal)
            else np.nan
        )
        timing_project_signal = (
            float(gp.timing_project_signal)
            if pd.notna(gp.timing_project_signal)
            else np.nan
        )
        timing_projects = str(gp.timing_projects)
        timing_applied = bool(gp.timing_applied)

        revenue = revenue * (1 + g)
        ebit = revenue * ebit_margin
        nopat = ebit * (1 - tax)
        da = revenue * da_ratio
        capex = revenue * capex_ratio

        if pd.notna(sustaining_share) and np.isfinite(sustaining_share):
            sustaining_capex = capex * float(np.clip(sustaining_share, 0.0, 1.0))
            growth_capex = max(capex - sustaining_capex, 0.0)
        else:
            sustaining_capex = np.nan
            growth_capex = np.nan

        nwc = revenue * nwc_ratio
        delta_nwc = nwc - previous_nwc
        previous_nwc = nwc

        net_reinvestment = capex - da + delta_nwc
        fcff = nopat - net_reinvestment

        reinvestment_rate = (
            net_reinvestment / nopat
            if np.isfinite(nopat) and abs(nopat) > 1e-12
            else np.nan
        )

        implied_roic = (
            g / reinvestment_rate
            if np.isfinite(reinvestment_rate) and reinvestment_rate > 1e-9 and g > 0
            else np.nan
        )

        # Diagnóstico LEGADO de associação contemporânea. Continua disponível,
        # mas não é interpretado como retorno econômico de projeto.
        growth_reinvestment = (
            growth_capex + delta_nwc
            if pd.notna(growth_capex) and np.isfinite(growth_capex)
            else np.nan
        )
        growth_reinvestment_rate = (
            growth_reinvestment / nopat
            if pd.notna(growth_reinvestment) and np.isfinite(growth_reinvestment)
            and growth_reinvestment > 1e-9 and np.isfinite(nopat) and nopat > 1e-12
            else np.nan
        )
        implied_growth_return = (
            g / growth_reinvestment_rate
            if pd.notna(growth_reinvestment_rate) and np.isfinite(growth_reinvestment_rate)
            and growth_reinvestment_rate > 1e-9 and g > 0
            else np.nan
        )

        rows.append({
            "year": y,
            "calendar_year": calendar_year,
            "period_start": period_start,
            "period_end": period_end,
            "period_label": period_label,
            "legacy_growth": legacy_g,
            "growth": g,
            "timing_signal": timing_signal,
            "timing_baseline_signal": timing_baseline_signal,
            "timing_project_signal": timing_project_signal,
            "timing_projects": timing_projects,
            "timing_applied": timing_applied,
            "revenue": revenue,
            "ebit": ebit,
            "nopat": nopat,
            "da": da,
            "capex": capex,
            "sustaining_capex": sustaining_capex,
            "growth_capex": growth_capex,
            "nwc": nwc,
            "delta_nwc": delta_nwc,
            "net_reinvestment": net_reinvestment,
            "reinvestment_rate": reinvestment_rate,
            "implied_roic": implied_roic,
            "growth_reinvestment": growth_reinvestment,
            "growth_reinvestment_rate": growth_reinvestment_rate,
            "implied_growth_return": implied_growth_return,
            "fcff": fcff,
        })

    return pd.DataFrame(rows)


def stable_terminal_value(proj, wacc, terminal_g):
    """
    Fecha o DCF com reinvestimento coerente com o crescimento perpétuo.

    No modelo anterior, o FCFF do ano 5 era simplesmente multiplicado por (1+g).
    Isso perpetuava, sem tornar explícito, qualquer relação CAPEX/D&A/NWC observada
    no quinto ano. Para uma empresa em crescimento estável, crescimento precisa ser
    financiado por reinvestimento:

        crescimento = taxa de reinvestimento × ROIC
        taxa de reinvestimento estável = g / ROIC estável

    Para não inventar um prêmio de retorno sobre o capital em perpetuidade, o
    fechamento adota ROIC terminal = WACC, isto é, zero excesso de retorno econômico
    permanente. Os cinco anos explícitos NÃO são alterados por essa hipótese.

    Assim:
        NOPAT_(n+1) = NOPAT_n × (1+g)
        Reinvestimento_(n+1) = NOPAT_(n+1) × g / ROIC_terminal
        FCFF_(n+1) = NOPAT_(n+1) - Reinvestimento_(n+1)
        TV_n = FCFF_(n+1) / (WACC-g)
    """
    if proj is None or len(proj) == 0:
        raise ValueError("Projeção vazia; não é possível calcular o valor terminal.")

    if not np.isfinite(wacc) or not np.isfinite(terminal_g):
        raise ValueError("WACC/g terminal inválidos.")

    # Guarda matemática: WACC precisa exceder g com folga mínima.
    # Não ajusta o WACC silenciosamente, pois isso criaria uma premissa nova dentro
    # de um cenário. Se a condição for violada, o cenário é interrompido e precisa
    # ser revisto explicitamente.
    if wacc <= terminal_g + 0.005:
        raise ValueError(
            f"WACC terminal ({wacc:.2%}) precisa exceder g ({terminal_g:.2%}) "
            "em pelo menos 0,50 p.p.; nenhum ajuste automático foi aplicado."
        )

    last_nopat = float(proj["nopat"].iloc[-1])
    if not np.isfinite(last_nopat):
        raise ValueError("NOPAT do último ano explícito inválido.")

    # Fechamento conservador de estado estável: sem excesso de retorno perpétuo.
    terminal_roic = float(wacc)
    terminal_reinvestment_rate = float(terminal_g / terminal_roic)

    nopat_next = last_nopat * (1 + terminal_g)
    terminal_reinvestment = nopat_next * terminal_reinvestment_rate
    terminal_fcff = nopat_next - terminal_reinvestment
    terminal_value = terminal_fcff / (wacc - terminal_g)

    # Diagnóstico da hipótese que o método antigo perpetuaria implicitamente.
    last_net_reinvestment = (
        float(proj["net_reinvestment"].iloc[-1])
        if "net_reinvestment" in proj.columns
        else np.nan
    )
    legacy_reinvestment_rate = (
        last_net_reinvestment / last_nopat
        if np.isfinite(last_net_reinvestment) and abs(last_nopat) > 1e-12
        else np.nan
    )
    legacy_implied_roic = (
        terminal_g / legacy_reinvestment_rate
        if np.isfinite(legacy_reinvestment_rate) and legacy_reinvestment_rate > 1e-9 and terminal_g > 0
        else np.nan
    )

    return {
        "wacc": float(wacc),
        "terminal_g": float(terminal_g),
        "terminal_roic": terminal_roic,
        "terminal_reinvestment_rate": terminal_reinvestment_rate,
        "nopat_next": float(nopat_next),
        "terminal_reinvestment": float(terminal_reinvestment),
        "terminal_fcff": float(terminal_fcff),
        "terminal_value": float(terminal_value),
        "legacy_reinvestment_rate": float(legacy_reinvestment_rate) if np.isfinite(legacy_reinvestment_rate) else np.nan,
        "legacy_implied_roic": float(legacy_implied_roic) if np.isfinite(legacy_implied_roic) else np.nan,
    }


def dcf_value(start_revenue, assump, scenario):
    proj = project_fcff(start_revenue, assump, scenario)
    wacc = assump["wacc"] + scenario["wacc_shift"]
    terminal_g = max(-0.01, TERMINAL_GROWTH + scenario["terminal_g_shift"])

    terminal = stable_terminal_value(proj, wacc, terminal_g)
    wacc = terminal["wacc"]

    proj["discount_factor"] = [(1 + wacc) ** y for y in proj["year"]]
    proj["pv_fcff"] = proj["fcff"] / proj["discount_factor"]

    terminal_value = terminal["terminal_value"]
    pv_terminal = terminal_value / ((1 + wacc) ** PROJECTION_YEARS)
    pv_explicit = float(proj["pv_fcff"].sum())
    enterprise_value = pv_explicit + pv_terminal
    equity_value = enterprise_value - assump["net_debt"]
    fair_price = equity_value / assump["shares"] if assump["shares"] > 0 else np.nan
    terminal_share_ev = pv_terminal / enterprise_value if enterprise_value > 0 else np.nan

    return {
        "projection": proj,
        "wacc": wacc,
        "terminal_g": terminal_g,
        "terminal_roic": terminal["terminal_roic"],
        "terminal_reinvestment_rate": terminal["terminal_reinvestment_rate"],
        "terminal_nopat_next": terminal["nopat_next"],
        "terminal_reinvestment": terminal["terminal_reinvestment"],
        "terminal_fcff": terminal["terminal_fcff"],
        "legacy_reinvestment_rate": terminal["legacy_reinvestment_rate"],
        "legacy_implied_roic": terminal["legacy_implied_roic"],
        "terminal_value": terminal_value,
        "pv_explicit": pv_explicit,
        "pv_terminal": pv_terminal,
        "terminal_share_ev": terminal_share_ev,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "fair_price_today": fair_price,
    }



def residual_income_value(
    hist_mkt,
    ttm,
    assump,
    start_revenue,
    payout_norm,
    expected_dividend,
    profile_label="regulated",
):
    """
    Valuation por Lucro Residual (Residual Income) para perfis em que o FCFF
    explícito pode distorcer a leitura econômica do reinvestimento.

    Usado atualmente em:
      - regulated: utilities/concessionárias;
      - high_roic_growth: companhias de alto retorno/reinvestimento.

    Fórmula:
        Valor do equity hoje = PL atribuível aos controladores hoje
                              + PV dos lucros residuais explícitos

        Lucro residual_t = Lucro líquido_t - Ke × PL_inicial_t

    Evolução do PL:
        PL_final_t = PL_inicial_t + Lucro_t - Dividendos_t

    O lucro líquido projetado preserva EXATAMENTE as premissas já existentes:
      Receita projetada × margem líquida normalizada.

    Dividendos projetados:
      lucro líquido positivo × payout histórico normalizado já usado pelo modelo.

    Fechamento sem prazo de fade inventado:
      1) os 5 anos do horizonte-base são sempre projetados;
      2) se ao fim do ano 5 o ROE ainda estiver acima do Ke e o lucro residual
         continuar positivo, o período explícito é prolongado usando SOMENTE:
            - o mesmo g terminal já aprovado no modelo;
            - a mesma margem líquida normalizada;
            - o mesmo payout histórico normalizado;
            - o mesmo Ke;
      3) a extensão termina no primeiro ano em que essa dinâmica mecânica faria
         o lucro residual deixar de ser positivo. Esse primeiro ano não recebe
         lucro residual negativo: dali em diante vale a regra terminal ROE = Ke,
         logo lucro residual = 0;
      4) se, pelas próprias premissas existentes, a dinâmica não puder convergir
         ao Ke, o RI é considerado indisponível em vez de inventar um prazo de fade.

    Assim, não há RAB, WACC regulatório, ROE perpétuo, múltiplo terminal, prazo de
    fade arbitrário ou crescimento adicional. O FCFF genérico permanece calculado
    e exibido separadamente.
    """
    if ttm is None:
        raise ValueError("Residual Income indisponível: TTM ausente.")

    book0 = ttm.get("equity_parent", np.nan)
    if pd.isna(book0) or not np.isfinite(book0) or book0 <= 0:
        raise ValueError(
            "Residual Income indisponível: patrimônio líquido atribuível aos "
            "controladores ausente ou não positivo."
        )

    ke = float(assump.get("cost_equity", np.nan))
    shares = float(assump.get("shares", np.nan))
    net_margin = float(assump.get("net_margin", np.nan))
    if not (np.isfinite(ke) and ke > 0):
        raise ValueError("Residual Income indisponível: Ke inválido.")
    if not (np.isfinite(shares) and shares > 0):
        raise ValueError("Residual Income indisponível: ações inválidas.")
    if not np.isfinite(net_margin):
        raise ValueError("Residual Income indisponível: margem líquida inválida.")
    if pd.isna(payout_norm) or not np.isfinite(payout_norm) or payout_norm < 0:
        raise ValueError(
            "Residual Income indisponível: payout histórico normalizado inválido."
        )

    growth_audit = build_growth_path(assump, SCENARIOS["Base"])
    growth_path = growth_audit["growth"].astype(float).tolist()
    terminal_growth = float(TERMINAL_GROWTH + SCENARIOS["Base"].get("terminal_g_shift", 0.0))

    revenue = float(start_revenue)
    book_begin = float(book0)
    rows = []
    pv_residual_income = 0.0

    def _project_one_year(year, growth, revenue_in, book_in):
        revenue_out = float(revenue_in) * (1.0 + float(growth))
        net_income = revenue_out * net_margin
        dividends = max(net_income, 0.0) * float(payout_norm)
        retained = net_income - dividends
        residual_income = net_income - ke * float(book_in)
        pv_ri = residual_income / ((1.0 + ke) ** int(year))
        roe = net_income / float(book_in) if abs(float(book_in)) > 1e-12 else np.nan
        book_end = float(book_in) + retained
        if not np.isfinite(book_end) or book_end <= 0:
            raise ValueError(
                f"Residual Income indisponível: patrimônio projetado não positivo no ano {year}. "
                "O modelo não aplica piso ou recapitalização artificial."
            )
        return {
            "year": int(year),
            "growth": float(growth),
            "revenue": revenue_out,
            "book_begin": float(book_in),
            "net_income": net_income,
            "roe": roe,
            "ke": ke,
            "residual_income": residual_income,
            "dividends": dividends,
            "retained_earnings": retained,
            "book_end": book_end,
            "pv_residual_income": pv_ri,
        }

    # Horizonte-base obrigatório de 5 anos: preservado exatamente.
    for y in range(1, PROJECTION_YEARS + 1):
        row = _project_one_year(y, growth_path[y - 1], revenue, book_begin)
        rows.append(row)
        pv_residual_income += row["pv_residual_income"]
        revenue = row["revenue"]
        book_begin = row["book_end"]

    extended_years = 0
    convergence_year = PROJECTION_YEARS + 1
    terminal_mechanical_roe = np.nan

    # Se ainda existe excesso de retorno positivo no fim do horizonte-base,
    # não o zeramos abruptamente no ano 6. Prolongamos somente a dinâmica já
    # existente até que ela própria encontre o Ke.
    if rows[-1]["residual_income"] > 0:
        retention = 1.0 - float(payout_norm)
        if retention <= 0:
            raise ValueError(
                "Residual Income indisponível: ROE no ano 5 ainda supera o Ke, mas o payout "
                "normalizado é >= 100%; não há convergência endógena segura para ROE=Ke sem "
                "introduzir uma hipótese nova de fade."
            )

        terminal_mechanical_roe = terminal_growth / retention
        if not np.isfinite(terminal_mechanical_roe) or terminal_mechanical_roe >= ke:
            raise ValueError(
                "Residual Income indisponível: pelas premissas já existentes, o ROE mecânico "
                f"de longo prazo ({terminal_mechanical_roe:.2%}) não converge abaixo do Ke "
                f"({ke:.2%}). O modelo não inventa um prazo de fade para forçar a convergência."
            )

        y = PROJECTION_YEARS + 1
        while True:
            candidate = _project_one_year(y, terminal_growth, revenue, book_begin)

            # O primeiro ano que ficaria em RI <= 0 marca a convergência. A partir
            # dele adotamos ROE=Ke e RI=0, em vez de perpetuar lucro residual negativo.
            if candidate["residual_income"] <= 0:
                convergence_year = y
                break

            rows.append(candidate)
            pv_residual_income += candidate["pv_residual_income"]
            revenue = candidate["revenue"]
            book_begin = candidate["book_end"]
            extended_years += 1
            y += 1

    equity_value_today = float(book0 + pv_residual_income)
    fair_price_today = equity_value_today / shares

    # Pela identidade do clean-surplus RI, o preço ex-dividendo esperado em 12m
    # é o valor de hoje capitalizado a Ke menos o dividendo esperado do período.
    target_12m = (
        fair_price_today * (1 + ke) - float(expected_dividend)
        if pd.notna(expected_dividend) and np.isfinite(expected_dividend)
        else np.nan
    )

    projection = pd.DataFrame(rows)

    roe_hist = pd.Series(dtype=float)
    if hist_mkt is not None and not hist_mkt.empty and "roe_parent" in hist_mkt.columns:
        roe_hist = (
            pd.to_numeric(hist_mkt["roe_parent"], errors="coerce")
            .replace([np.inf, -np.inf], np.nan)
            .dropna()
        )

    return {
        "profile_label": profile_label,
        "book_equity_today": float(book0),
        "cost_equity": ke,
        "payout_norm": float(payout_norm),
        "projection": projection,
        "pv_residual_income": float(pv_residual_income),
        "equity_value_today": equity_value_today,
        "fair_price_today": float(fair_price_today),
        "target_12m": float(target_12m) if pd.notna(target_12m) and np.isfinite(target_12m) else np.nan,
        "terminal_residual_income": 0.0,
        "terminal_rule": "ROE terminal = Ke; lucro residual terminal = 0 após convergência endógena",
        "historical_roe_median": safe_median(roe_hist.tail(4), np.nan),
        "growth_audit": growth_audit,
        "minimum_explicit_years": int(PROJECTION_YEARS),
        "extended_positive_ri_years": int(extended_years),
        "explicit_ri_years": int(len(rows)),
        "convergence_year": int(convergence_year),
        "terminal_growth_used_for_extension": float(terminal_growth),
        "terminal_mechanical_roe": (
            float(terminal_mechanical_roe)
            if pd.notna(terminal_mechanical_roe) and np.isfinite(terminal_mechanical_roe)
            else np.nan
        ),
    }


# ================================================================
# 7) MÚLTIPLOS E DIVIDENDOS
# ================================================================

def compute_historical_multiples(hist_mkt):
    h = hist_mkt.copy()

    # 1) Múltiplos contábeis históricos: permanecem visíveis e comparáveis ao
    # histórico original do modelo.
    h["eps"] = h["net_income"] / h["shares"]
    h["pe"] = h["price_yend"] / h["eps"]
    h.loc[(h["eps"] <= 0) | (h["pe"] <= 0) | (h["pe"] > 50), "pe"] = np.nan

    if "company_market_cap_yend" in h.columns:
        h["market_cap_yend"] = h["company_market_cap_yend"]
    else:
        h["market_cap_yend"] = h["price_yend"] * h["shares"]
    h["ev_yend"] = h["market_cap_yend"] + h["net_debt"]
    h["ev_ebitda"] = h["ev_yend"] / h["ebitda"]
    h.loc[(h["ebitda"] <= 0) | (h["ev_ebitda"] <= 0) | (h["ev_ebitda"] > 30), "ev_ebitda"] = np.nan

    h["dividend_yield"] = h["dividend_ps"] / h["price_yend"]
    h.loc[(h["dividend_yield"] <= 0) | (h["dividend_yield"] > 0.40), "dividend_yield"] = np.nan

    h["payout"] = (h["dividend_ps"] * h["shares"]) / h["net_income"]
    # Payout acima de 100% pode ocorrer legitimamente por uso de reservas/caixa.
    # Não impomos teto positivo arbitrário. Apenas lucro não positivo ou payout
    # negativo tornam a observação economicamente inadequada para normalização.
    h.loc[(h["net_income"] <= 0) | (h["payout"] < 0), "payout"] = np.nan

    # 2) Séries usadas APENAS para normalizar P/L e EV/EBITDA. Quando não há
    # referência oficial recorrente, são idênticas às séries contábeis acima.
    ni_for_mult = h["net_income_for_normalization"] if "net_income_for_normalization" in h.columns else h["net_income"]
    ebitda_for_mult = h["ebitda_for_normalization"] if "ebitda_for_normalization" in h.columns else h["ebitda"]

    h["eps_for_normalization"] = ni_for_mult / h["shares"]
    h["pe_for_normalization"] = h["price_yend"] / h["eps_for_normalization"]
    h.loc[
        (h["eps_for_normalization"] <= 0)
        | (h["pe_for_normalization"] <= 0)
        | (h["pe_for_normalization"] > 50),
        "pe_for_normalization"
    ] = np.nan

    h["ev_ebitda_for_normalization"] = h["ev_yend"] / ebitda_for_mult
    h.loc[
        (ebitda_for_mult <= 0)
        | (h["ev_ebitda_for_normalization"] <= 0)
        | (h["ev_ebitda_for_normalization"] > 30),
        "ev_ebitda_for_normalization"
    ] = np.nan
    return h


def forward_multiple_targets(symbol, hist_mkt, assump, start_revenue):
    h = compute_historical_multiples(hist_mkt)
    pe_series = h["pe_for_normalization"] if "pe_for_normalization" in h.columns else h["pe"]
    ev_series = h["ev_ebitda_for_normalization"] if "ev_ebitda_for_normalization" in h.columns else h["ev_ebitda"]
    pe_norm = safe_median(pe_series.tail(4), np.nan)
    ev_ebitda_norm = safe_median(ev_series.tail(4), np.nan)
    dy_norm = safe_median(h["dividend_yield"].tail(4), np.nan)
    payout_norm = safe_median(h["payout"].tail(4), np.nan)
    if pd.notna(payout_norm):
        # Não impõe teto arbitrário ao payout histórico. Empresas podem distribuir
        # acima de 100% do lucro em determinados ciclos usando reservas/caixa.
        # Valores negativos são inválidos; valores positivos permanecem como observados.
        payout_norm = float(max(payout_norm, 0.0))

    # Ano 1 base usando as mesmas premissas econômicas do DCF.
    base_proj = project_fcff(start_revenue, assump, SCENARIOS["Base"])
    rev1 = float(base_proj["revenue"].iloc[0])
    ebit1 = float(base_proj["ebit"].iloc[0])
    da1 = float(base_proj["da"].iloc[0])
    capex1 = float(base_proj["capex"].iloc[0])
    sustaining_capex1 = (
        float(base_proj["sustaining_capex"].iloc[0])
        if "sustaining_capex" in base_proj.columns and pd.notna(base_proj["sustaining_capex"].iloc[0])
        else np.nan
    )
    growth_capex1 = (
        float(base_proj["growth_capex"].iloc[0])
        if "growth_capex" in base_proj.columns and pd.notna(base_proj["growth_capex"].iloc[0])
        else np.nan
    )
    fcff1 = float(base_proj["fcff"].iloc[0])
    ebitda1 = ebit1 + da1
    net_income1 = rev1 * assump["net_margin"]
    eps1 = net_income1 / assump["shares"]

    # Ano 2 usa a MESMA projeção-base já produzida pelo DCF.
    # Nenhuma nova premissa de crescimento é introduzida.
    if len(base_proj) < 2:
        raise ValueError(
            "Projeção base possui menos de 2 anos; alvo de 24 meses indisponível."
        )
    rev2 = float(base_proj["revenue"].iloc[1])
    ebit2 = float(base_proj["ebit"].iloc[1])
    da2 = float(base_proj["da"].iloc[1])
    capex2 = float(base_proj["capex"].iloc[1])
    sustaining_capex2 = (
        float(base_proj["sustaining_capex"].iloc[1])
        if "sustaining_capex" in base_proj.columns
        and pd.notna(base_proj["sustaining_capex"].iloc[1])
        else np.nan
    )
    growth_capex2 = (
        float(base_proj["growth_capex"].iloc[1])
        if "growth_capex" in base_proj.columns
        and pd.notna(base_proj["growth_capex"].iloc[1])
        else np.nan
    )
    fcff2 = float(base_proj["fcff"].iloc[1])
    ebitda2 = ebit2 + da2
    net_income2 = rev2 * assump["net_margin"]
    eps2 = net_income2 / assump["shares"]

    # Política de remuneração discutida para cada companhia.
    # Petrobras: 45% do FCL. Neste modelo, FCFF é mantido como proxy explícita
    # (não é afirmado como reprodução exata do FCL societário da política).
    # Vale: mínimo de 30% de (EBITDA Ajustado - Sustaining Investments).
    # A partir desta versão, quando há split oficial sustaining/growth cadastrado,
    # a política usa a parcela sustaining projetada. O CAPEX TOTAL continua sendo
    # deduzido no FCFF; a mudança aqui corrige somente a métrica específica da
    # política de remuneração da Vale.
    if symbol == "PETR4":
        dividend_policy_value = 0.45 * max(fcff1, 0.0)
        dividend_method = "Política Petrobras: 45% do FCL; FCFF projetado mantido como proxy explícita"
    elif symbol == "VALE3":
        if pd.notna(sustaining_capex1) and np.isfinite(sustaining_capex1):
            dividend_policy_value = 0.30 * max(ebitda1 - sustaining_capex1, 0.0)
            split = assump.get("capex_split") or {}
            dividend_method = (
                "Política Vale: 30% de (EBITDA Ajustado - Sustaining Investments); "
                f"Sustaining projetado usa split oficial {split.get('reference_year', 'n/d')}: "
                f"{split.get('sustaining_share', np.nan):.1%} do CAPEX total"
            )
        else:
            dividend_policy_value = 0.30 * max(ebitda1 - capex1, 0.0)
            dividend_method = (
                "Política Vale: 30% de (EBITDA Ajustado - Sustaining Investments); "
                "split oficial indisponível, portanto CAPEX total permanece proxy conservadora"
            )
    else:
        # Regra genérica para companhias FCFF novas:
        # usa o payout histórico normalizado da própria empresa, já calculado pelo modelo.
        # Não impõe um payout fixo externo nem inventa uma política societária.
        dividend_policy_value = (
            max(net_income1, 0.0) * payout_norm
            if pd.notna(payout_norm) and np.isfinite(payout_norm)
            else np.nan
        )
        dividend_method = (
            "Regra genérica: lucro líquido projetado × payout histórico normalizado "
            "da própria companhia; nenhuma política fixa externa foi inventada"
        )

    expected_dividend = (
        dividend_policy_value / assump["shares"]
        if pd.notna(dividend_policy_value) and assump["shares"] > 0
        else np.nan
    )

    # Se payout histórico não for utilizável, preserva uma referência estritamente
    # histórica por ação para permitir a conversão ex-dividendo do DCF 12m sem assumir zero.
    if pd.isna(expected_dividend) or not np.isfinite(expected_dividend):
        div_hist = pd.to_numeric(h.get("dividend_ps", pd.Series(dtype=float)), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        div_hist = div_hist[div_hist >= 0]
        expected_dividend = safe_median(div_hist.tail(4), 0.0)
        dividend_method = (
            "Fallback genérico: mediana do dividendo/ação histórico dos últimos 4 anos; "
            "usado apenas porque o payout normalizado ficou indisponível"
        )

    # Dividendo do ano 2: aplica exatamente a mesma política já usada no ano 1,
    # porém sobre os números do segundo ano da projeção-base.
    if symbol == "PETR4":
        dividend_policy_value_2 = 0.45 * max(fcff2, 0.0)
    elif symbol == "VALE3":
        if pd.notna(sustaining_capex2) and np.isfinite(sustaining_capex2):
            dividend_policy_value_2 = 0.30 * max(ebitda2 - sustaining_capex2, 0.0)
        else:
            dividend_policy_value_2 = 0.30 * max(ebitda2 - capex2, 0.0)
    else:
        dividend_policy_value_2 = (
            max(net_income2, 0.0) * payout_norm
            if pd.notna(payout_norm) and np.isfinite(payout_norm)
            else np.nan
        )

    expected_dividend_24m = (
        dividend_policy_value_2 / assump["shares"]
        if pd.notna(dividend_policy_value_2)
        and np.isfinite(dividend_policy_value_2)
        and assump["shares"] > 0
        else np.nan
    )

    if pd.isna(expected_dividend_24m) or not np.isfinite(expected_dividend_24m):
        div_hist = pd.to_numeric(
            h.get("dividend_ps", pd.Series(dtype=float)),
            errors="coerce",
        ).replace([np.inf, -np.inf], np.nan).dropna()
        div_hist = div_hist[div_hist >= 0]
        expected_dividend_24m = safe_median(div_hist.tail(4), 0.0)

    pe_target = eps1 * pe_norm if pd.notna(pe_norm) and np.isfinite(pe_norm) and eps1 > 0 else np.nan
    if pd.notna(ev_ebitda_norm):
        target_ev = ebitda1 * ev_ebitda_norm
        target_equity = target_ev - assump["net_debt"]
        ev_ebitda_target = target_equity / assump["shares"]
    else:
        ev_ebitda_target = np.nan

    # Mantém o método de DY previamente acordado. Não é aplicado teto arbitrário:
    # quando o DY histórico normalizado estiver muito elevado, o programa apenas
    # sinaliza o risco de o histórico conter distribuições extraordinárias.
    dy_target = expected_dividend / dy_norm if pd.notna(expected_dividend) and np.isfinite(expected_dividend) and expected_dividend > 0 and pd.notna(dy_norm) and np.isfinite(dy_norm) and dy_norm > 0 else np.nan

    # Métodos de 24 meses usam o segundo ano da MESMA projeção e os MESMOS
    # múltiplos normalizados. Não há nova curva de crescimento nem novo múltiplo.
    pe_target_24m = (
        eps2 * pe_norm
        if pd.notna(pe_norm) and np.isfinite(pe_norm) and eps2 > 0
        else np.nan
    )
    if pd.notna(ev_ebitda_norm):
        target_ev_24m = ebitda2 * ev_ebitda_norm
        # O motor não projeta uma trajetória explícita de dívida líquida.
        # Portanto, preserva-se a mesma convenção do método de 12 meses:
        # dívida líquida atual, sem inventar desalavancagem futura.
        target_equity_24m = target_ev_24m - assump["net_debt"]
        ev_ebitda_target_24m = target_equity_24m / assump["shares"]
    else:
        ev_ebitda_target_24m = np.nan

    dy_target_24m = (
        expected_dividend_24m / dy_norm
        if pd.notna(expected_dividend_24m)
        and np.isfinite(expected_dividend_24m)
        and expected_dividend_24m > 0
        and pd.notna(dy_norm)
        and np.isfinite(dy_norm)
        and dy_norm > 0
        else np.nan
    )

    dy_warning = None
    if pd.notna(dy_norm) and pd.notna(assump.get("cost_equity", np.nan)) and dy_norm > assump["cost_equity"]:
        dy_warning = (
            f"DY histórico normalizado ({dy_norm:.2%}) supera o Ke ({assump['cost_equity']:.2%}). "
            "O método foi preservado, mas pode refletir distribuições extraordinárias; nenhum teto foi inventado."
        )

    return {
        "history": h,
        "pe_norm": pe_norm,
        "ev_ebitda_norm": ev_ebitda_norm,
        "dy_norm": dy_norm,
        "payout_norm": payout_norm,
        "rev1": rev1,
        "ebitda1": ebitda1,
        "capex1": capex1,
        "sustaining_capex1": sustaining_capex1,
        "growth_capex1": growth_capex1,
        "fcff1": fcff1,
        "net_income1": net_income1,
        "eps1": eps1,
        "rev2": rev2,
        "ebitda2": ebitda2,
        "capex2": capex2,
        "sustaining_capex2": sustaining_capex2,
        "growth_capex2": growth_capex2,
        "fcff2": fcff2,
        "net_income2": net_income2,
        "eps2": eps2,
        "expected_dividend": expected_dividend,
        "expected_dividend_24m": expected_dividend_24m,
        "dividend_method": dividend_method,
        "pe_target": pe_target,
        "ev_ebitda_target": ev_ebitda_target,
        "dy_target": dy_target,
        "pe_target_24m": pe_target_24m,
        "ev_ebitda_target_24m": ev_ebitda_target_24m,
        "dy_target_24m": dy_target_24m,
        "dy_warning": dy_warning,
    }



# ================================================================
# 7B) MÓDULO DE EQUITY — BANCOS / SEGURADORAS / B3 / HOLDING / UNIT
# ================================================================

def get_equity_model_profile(asset):
    """
    Classifica os ativos não FCFF sem mudar a configuração econômica já existente.

    Perfis:
      - bank
      - bank_unit
      - insurance
      - insurance_holding
      - market_infrastructure
      - holding

    Todos usam um motor patrimonial (equity-side), pois dívida/caixa/NWC do FCFF
    corporativo não têm a mesma interpretação para esses negócios.
    """
    explicit = asset.get("financial_profile")
    if explicit:
        return str(explicit)

    model_type = str(asset.get("valuation_model", "")).lower()
    if model_type == "financial_unit":
        return "bank_unit"
    if model_type == "financial_infrastructure":
        return "market_infrastructure"
    if model_type == "holding":
        return "holding"
    if model_type == "financial":
        return "financial"
    return "unsupported"


def _target_security_factor(asset):
    """
    Número de ações subjacentes por ativo negociado.

    Para ações simples, fator = 1.
    Para BPAC11, a configuração traz fator = 3 porque cada Unit contém
    1 ON + 2 PNA. Isso é uma característica societária, não uma premissa
    de valuation.
    """
    factor = float(asset.get("unit_share_factor", 1.0) or 1.0)
    if not np.isfinite(factor) or factor <= 0:
        raise ValueError("Fator de conversão de ativo negociado inválido.")
    return factor


def _equity_security_count(total_shares, asset):
    """Converte ações totais subjacentes em quantidade do ativo-alvo negociado."""
    if pd.isna(total_shares) or not np.isfinite(total_shares) or total_shares <= 0:
        return np.nan
    return float(total_shares) / _target_security_factor(asset)


def load_equity_annual_history(asset):
    """
    Histórico anual patrimonial 2020-2025 para instituições financeiras,
    seguradoras, infraestrutura financeira, holdings e Units.

    O módulo usa apenas:
      - lucro líquido atribuível aos controladores;
      - patrimônio líquido atribuível aos controladores;
      - quantidade de ações / ativos negociados.

    Não usa dívida líquida, NWC, CAPEX ou EBITDA do FCFF.
    2020 é carregado apenas para calcular o PL médio e o ROE de 2021.
    """
    rows = []
    diagnostics = {}
    years_to_load = [AUX_NWC_YEAR] + list(HIST_YEARS)

    for year in years_to_load:
        pkg = load_cvm_package("DFP", year)

        dre, dre_source = _select_statement_rows(
            pkg, "DRE", asset["cvm"], year=year, cumulative=True
        )
        bpp, bpp_source = _select_statement_rows(
            pkg, "BPP", asset["cvm"], year=year
        )

        net_income, net_income_label = extract_net_income_from_dre(dre)
        equity_total, equity_parent, equity_labels = extract_financial_equity_from_bpp(bpp)

        raw_struct = get_share_structure(pkg["CAPITAL"], asset["cvm"], year=year)
        share_info = {}
        share_error = None

        if year in HIST_YEARS:
            try:
                share_info = normalize_share_structure_for_asset(
                    raw_struct,
                    asset,
                    ref_date=pd.Timestamp(year=year, month=12, day=31),
                )
                total_shares = share_info["shares"]
                security_count = _equity_security_count(total_shares, asset)
                shares_ordinary = share_info.get("ordinary_outstanding", np.nan)
                shares_preferred = share_info.get("preferred_outstanding", np.nan)
            except Exception as e:
                share_error = f"{type(e).__name__}: {e}"
                total_shares = np.nan
                security_count = np.nan
                shares_ordinary = np.nan
                shares_preferred = np.nan
        else:
            total_shares = np.nan
            security_count = np.nan
            shares_ordinary = np.nan
            shares_preferred = np.nan

        rows.append({
            "year": int(year),
            "net_income": net_income,
            "equity_total": equity_total,
            "equity_parent": equity_parent,
            "shares": total_shares,
            "security_count": security_count,
            "shares_ordinary": shares_ordinary,
            "shares_preferred": shares_preferred,
        })

        diagnostics[int(year)] = {
            "Lucro líquido DRE": net_income_label,
            "Patrimônio líquido": equity_labels,
            "Base demonstrações CVM": {
                "DRE": dre_source,
                "BPP": bpp_source,
            },
            "Ações": share_info,
            "Erro ações históricas": share_error,
        }

    hist_all = pd.DataFrame(rows).set_index("year").sort_index()
    hist_all["avg_equity_parent"] = (
        hist_all["equity_parent"] + hist_all["equity_parent"].shift(1)
    ) / 2.0
    hist_all["roe_parent"] = hist_all["net_income"] / hist_all["avg_equity_parent"]

    hist = hist_all.loc[HIST_YEARS].copy()
    return hist, diagnostics


def load_equity_ttm(asset):
    """
    TTM patrimonial:
        lucro TTM = DFP 2025 + ITR 2026 YTD - ITR 2025 YTD
        PL atual   = último BPP do ITR 2026

    Não calcula FCFF, CAPEX, NWC ou dívida líquida.
    """
    pkg25_dfp = load_cvm_package("DFP", 2025)
    pkg26 = load_cvm_package("ITR", CURRENT_ITR_YEAR)
    pkg25_itr = load_cvm_package("ITR", 2025)

    dre_probe, _ = _select_statement_rows(
        pkg26, "DRE", asset["cvm"], year=CURRENT_ITR_YEAR, cumulative=True
    )
    if dre_probe.empty or "DT_REFER" not in dre_probe.columns:
        return None

    probe = dre_probe.copy()
    probe["DT_REFER"] = pd.to_datetime(probe["DT_REFER"], errors="coerce")
    latest_ref = probe["DT_REFER"].max()
    if pd.isna(latest_ref):
        return None

    prior_ref = latest_ref - pd.DateOffset(years=1)

    dre_a, dre_a_source = _select_statement_rows(
        pkg25_dfp, "DRE", asset["cvm"], year=2025, cumulative=True
    )
    dre_c, dre_c_source = _select_statement_rows(
        pkg26, "DRE", asset["cvm"], ref_date=latest_ref, cumulative=True
    )
    dre_p, dre_p_source = _select_statement_rows(
        pkg25_itr, "DRE", asset["cvm"], ref_date=prior_ref, cumulative=True
    )
    bpp_c, bpp_c_source = _select_statement_rows(
        pkg26, "BPP", asset["cvm"], ref_date=latest_ref
    )

    ni_a, ni_a_label = extract_net_income_from_dre(dre_a)
    ni_c, ni_c_label = extract_net_income_from_dre(dre_c)
    ni_p, ni_p_label = extract_net_income_from_dre(dre_p)

    if not all(pd.notna(v) and np.isfinite(v) for v in [ni_a, ni_c, ni_p]):
        net_income = np.nan
    else:
        net_income = float(ni_a + ni_c - ni_p)

    equity_total, equity_parent, equity_labels = extract_financial_equity_from_bpp(bpp_c)

    raw_struct = get_share_structure(
        pkg26["CAPITAL"], asset["cvm"], ref_date=latest_ref
    )
    if not raw_struct:
        raw_struct = get_share_structure(
            pkg25_dfp["CAPITAL"], asset["cvm"], year=2025
        )
    share_info = normalize_share_structure_for_asset(
        raw_struct, asset, ref_date=latest_ref
    )
    total_shares = share_info["shares"]
    security_count = _equity_security_count(total_shares, asset)

    return {
        "ref_date": latest_ref,
        "net_income": net_income,
        "equity_total": equity_total,
        "equity_parent": equity_parent,
        "shares": total_shares,
        "security_count": security_count,
        "share_info": share_info,
        "equity_labels": equity_labels,
        "statement_sources": {
            "DFP 2025": {"DRE": dre_a_source},
            f"ITR {latest_ref.year} YTD": {
                "DRE": dre_c_source,
                "BPP": bpp_c_source,
            },
            f"ITR {prior_ref.year} YTD": {"DRE": dre_p_source},
        },
        "net_income_components": {
            "DFP 2025": ni_a_label,
            f"ITR {latest_ref.year} YTD": ni_c_label,
            f"ITR {prior_ref.year} YTD": ni_p_label,
        },
    }


def annual_equity_market_data(symbol, asset, hist):
    """
    Adiciona preço, dividendos e base ajustada por splits ao histórico patrimonial.

    Para BPAC11, security_count representa Units equivalentes; para ações simples,
    representa o total de ações econômicas usado em EPS/BVPS. O preço histórico
    é sempre o do ticker-alvo, de forma que eventual prêmio/desconto da classe
    negociada é capturado pelos seus próprios múltiplos históricos.
    """
    ticker = asset["ticker"]
    prices = get_price_history(ticker, "10y")
    dividends = get_dividend_history(ticker, period="10y")
    splits = get_split_history(ticker, period="max")

    if not dividends.empty and getattr(dividends.index, "tz", None) is not None:
        dividends.index = dividends.index.tz_localize(None)

    out = hist.copy()
    out["shares_reported"] = out.get("shares", np.nan)
    out["security_count_reported"] = out.get("security_count", np.nan)

    adjusted_shares = []
    adjusted_security_count = []
    factors = []
    prices_yend = []
    div_ps = []

    for year, row in out.iterrows():
        ref_date = pd.Timestamp(year=int(year), month=12, day=31)
        factor = _split_factor_after_date(splits, ref_date)

        reported_shares = row.get("shares_reported", np.nan)
        reported_sec = row.get("security_count_reported", np.nan)

        adj_shares = (
            float(reported_shares) * factor
            if pd.notna(reported_shares) and np.isfinite(reported_shares)
            else np.nan
        )
        adj_sec = (
            float(reported_sec) * factor
            if pd.notna(reported_sec) and np.isfinite(reported_sec)
            else np.nan
        )

        adjusted_shares.append(adj_shares)
        adjusted_security_count.append(adj_sec)
        factors.append(float(factor))
        prices_yend.append(_year_end_price(prices, year))

        dy = (
            dividends[dividends.index.year == int(year)]
            if not dividends.empty
            else pd.Series(dtype=float)
        )
        div_ps.append(float(dy.sum()) if len(dy) else 0.0)

    out["shares"] = adjusted_shares
    out["security_count"] = adjusted_security_count
    out["historical_split_factor"] = factors
    out["price_yend"] = prices_yend
    out["dividend_ps"] = div_ps
    return out


def compute_equity_historical_multiples(hist_mkt):
    """
    Múltiplos adequados ao equity de instituições financeiras/seguradoras/holdings.

    Não usa EV/EBITDA.
      P/L  = preço / EPS
      P/VP = preço / valor patrimonial por ativo-alvo
      DY   = dividendos por ativo-alvo / preço
      payout = dividendos totais / lucro

    Não são introduzidos tetos arbitrários de P/L, P/VP, DY ou payout; observações
    não positivas/inválidas são descartadas e a normalização usa mediana recente.
    """
    h = hist_mkt.copy()

    h["eps"] = h["net_income"] / h["security_count"]
    h["bvps"] = h["equity_parent"] / h["security_count"]

    h["pe"] = h["price_yend"] / h["eps"]
    h.loc[
        (h["eps"] <= 0) | (h["price_yend"] <= 0) | (h["pe"] <= 0),
        "pe"
    ] = np.nan

    h["pb"] = h["price_yend"] / h["bvps"]
    h.loc[
        (h["bvps"] <= 0) | (h["price_yend"] <= 0) | (h["pb"] <= 0),
        "pb"
    ] = np.nan

    h["dividend_yield"] = h["dividend_ps"] / h["price_yend"]
    h.loc[
        (h["price_yend"] <= 0) | (h["dividend_yield"] < 0),
        "dividend_yield"
    ] = np.nan

    h["payout"] = (
        h["dividend_ps"] * h["security_count"]
    ) / h["net_income"]
    h.loc[
        (h["net_income"] <= 0) | (h["payout"] < 0),
        "payout"
    ] = np.nan

    return h


def normalize_equity_assumptions(hist_mkt, ttm, rf, beta, price, asset):
    """
    Normaliza somente variáveis patrimoniais/equity.

    Crescimento:
      mediana dos 3 crescimentos anuais recentes do lucro líquido;
      usa os mesmos limites globais já existentes no projeto (-3% / +8%).
      Se não houver histórico válido, falha explicitamente.

    Custo de equity:
      Ke = Rf + beta × ERP Brasil, idêntico ao motor FCFF.
    """
    if ttm is None:
        raise ValueError("TTM patrimonial indisponível.")

    h = compute_equity_historical_multiples(hist_mkt)

    ni = pd.to_numeric(h["net_income"], errors="coerce")
    prev = ni.shift(1)
    valid_growth = (ni > 0) & (prev > 0)
    growth = ni.pct_change().where(valid_growth).replace([np.inf, -np.inf], np.nan).dropna()
    base_growth = safe_median(growth.tail(3), np.nan)
    if pd.isna(base_growth) or not np.isfinite(base_growth):
        raise ValueError(
            "Crescimento recente do lucro líquido indisponível; "
            "o módulo financeiro não cria crescimento padrão."
        )
    base_growth = float(np.clip(
        base_growth, AUTO_GROWTH_FLOOR, AUTO_GROWTH_CEILING
    ))

    pe_norm = safe_median(h["pe"].tail(4), np.nan)
    pb_norm = safe_median(h["pb"].tail(4), np.nan)
    dy_norm = safe_median(h["dividend_yield"].tail(4), np.nan)
    payout_norm = safe_median(h["payout"].tail(4), np.nan)

    critical = {
        "lucro líquido TTM": ttm.get("net_income", np.nan),
        "patrimônio líquido atual": ttm.get("equity_parent", np.nan),
        "quantidade do ativo-alvo": ttm.get("security_count", np.nan),
        "P/L histórico normalizado": pe_norm,
        "P/VP histórico normalizado": pb_norm,
        "DY histórico normalizado": dy_norm,
        "payout histórico normalizado": payout_norm,
    }
    missing = [
        k for k, v in critical.items()
        if pd.isna(v) or not np.isfinite(v)
    ]
    if missing:
        raise ValueError(
            "Premissas patrimoniais críticas indisponíveis: "
            + ", ".join(missing)
        )

    if ttm["equity_parent"] <= 0:
        raise ValueError("Patrimônio líquido atribuível aos controladores não positivo.")
    if ttm["security_count"] <= 0:
        raise ValueError("Quantidade do ativo-alvo inválida.")
    if price <= 0 or not np.isfinite(price):
        raise ValueError("Preço atual inválido.")
    if payout_norm < 0:
        raise ValueError("Payout normalizado negativo.")
    if dy_norm < 0:
        raise ValueError("Dividend Yield normalizado negativo.")

    cost_equity = float(rf + beta * EQUITY_RISK_PREMIUM)

    return {
        "base_growth": base_growth,
        "rf": float(rf),
        "erp": float(EQUITY_RISK_PREMIUM),
        "erp_asof": EQUITY_RISK_PREMIUM_ASOF,
        "beta": float(beta),
        "cost_equity": cost_equity,
        "shares": float(ttm["shares"]),
        "security_count": float(ttm["security_count"]),
        "equity_parent": float(ttm["equity_parent"]),
        "net_income_ttm": float(ttm["net_income"]),
        "pe_norm": float(pe_norm),
        "pb_norm": float(pb_norm),
        "dy_norm": float(dy_norm),
        "payout_norm": float(payout_norm),
        "projection_ref_date": pd.Timestamp(ttm["ref_date"]).normalize(),
        "projection_base_year": int(pd.Timestamp(ttm["ref_date"]).year),
        "growth_timing": None,
        "financial_profile": get_equity_model_profile(asset),
        "unit_share_factor": _target_security_factor(asset),
    }


def financial_residual_income_value(
    hist_mkt,
    ttm,
    assump,
    payout_norm,
    expected_dividend,
    profile_label,
):
    """
    Residual Income patrimonial para negócios financeiros/equity-side.

    Diferença para o RI de utilities/high-ROIC:
      - não projeta receita/margem;
      - projeta diretamente o lucro líquido a partir do TTM usando a trajetória
        de crescimento histórica -> g terminal já adotada no Radar.

    Fórmulas explícitas:
      RI_t = Lucro_t - Ke × PL_inicial_t
      PL_final_t = PL_inicial_t + Lucro_t - Dividendos_t

    Horizonte e fechamento:
      - mínimo de 5 anos com o payout histórico normalizado;
      - se, após o ano 5, a própria dinâmica g/payout já implica ROE mecânico
        de longo prazo abaixo do Ke, prolonga exatamente a regra existente até
        o primeiro ano em que RI deixa de ser positivo;
      - se essa dinâmica não converge, não inventa prazo de fade. Em vez disso,
        aplica somente no fechamento terminal a condição econômica de estado
        estacionário sem excesso de retorno:

            ROE_terminal = Ke
            retention_terminal = g_terminal / Ke
            payout_terminal = 1 - g_terminal / Ke
            RI_terminal = 0

        Para que as quatro condições sejam simultaneamente verdadeiras, o lucro
        do primeiro ano terminal é normalizado para Ke × PL_inicial_terminal.
        Isso evita o erro de apenas trocar o payout mantendo lucro_{t+1}=lucro_t
        × (1+g), combinação que não zera o RI quando o ROE de entrada ainda está
        acima do Ke.
    """
    book0 = float(assump["equity_parent"])
    ni0 = float(assump["net_income_ttm"])
    ke = float(assump["cost_equity"])
    security_count = float(assump["security_count"])

    if not (np.isfinite(book0) and book0 > 0):
        raise ValueError("RI financeiro indisponível: PL atual inválido.")
    if not (np.isfinite(ni0) and ni0 > 0):
        raise ValueError("RI financeiro indisponível: lucro TTM não positivo.")
    if not (np.isfinite(ke) and ke > 0):
        raise ValueError("RI financeiro indisponível: Ke inválido.")
    if not (np.isfinite(security_count) and security_count > 0):
        raise ValueError("RI financeiro indisponível: quantidade do ativo inválida.")
    if pd.isna(payout_norm) or not np.isfinite(payout_norm) or payout_norm < 0:
        raise ValueError("RI financeiro indisponível: payout normalizado inválido.")

    growth_audit = build_growth_path(assump, SCENARIOS["Base"])
    growth_path = growth_audit["growth"].astype(float).tolist()
    terminal_growth = float(
        TERMINAL_GROWTH + SCENARIOS["Base"].get("terminal_g_shift", 0.0)
    )

    rows = []
    pv_ri = 0.0
    ni_begin = ni0
    book_begin = book0

    def _project_one_year(year, growth, ni_in, book_in, payout):
        net_income = float(ni_in) * (1.0 + float(growth))
        dividends = max(net_income, 0.0) * float(payout)
        retained = net_income - dividends
        residual_income = net_income - ke * float(book_in)
        book_end = float(book_in) + retained

        if not np.isfinite(book_end) or book_end <= 0:
            raise ValueError(
                f"RI financeiro indisponível: PL projetado não positivo no ano {year}; "
                "nenhuma recapitalização ou piso artificial é aplicado."
            )

        roe = (
            net_income / float(book_in)
            if abs(float(book_in)) > 1e-12
            else np.nan
        )
        pv = residual_income / ((1.0 + ke) ** int(year))

        return {
            "year": int(year),
            "growth_net_income": float(growth),
            "net_income": net_income,
            "book_begin": float(book_in),
            "roe": roe,
            "ke": ke,
            "residual_income": residual_income,
            "dividends": dividends,
            "retained_earnings": retained,
            "book_end": book_end,
            "pv_residual_income": pv,
            "payout_used": float(payout),
        }

    for y in range(1, PROJECTION_YEARS + 1):
        row = _project_one_year(
            y, growth_path[y - 1], ni_begin, book_begin, payout_norm
        )
        rows.append(row)
        pv_ri += row["pv_residual_income"]
        ni_begin = row["net_income"]
        book_begin = row["book_end"]

    extended_years = 0
    convergence_year = PROJECTION_YEARS + 1
    terminal_mechanical_roe = np.nan
    terminal_closure_applied = False
    terminal_retention = np.nan
    terminal_payout = np.nan
    terminal_normalized_net_income = np.nan
    terminal_normalized_roe = np.nan
    terminal_residual_income = np.nan
    terminal_implied_growth_from_last_explicit = np.nan
    terminal_book_begin = np.nan
    terminal_book_end = np.nan
    terminal_rule = (
        "ROE terminal = Ke; lucro residual terminal = 0 após convergência endógena"
    )

    if rows[-1]["residual_income"] > 0:
        retention_explicit = 1.0 - float(payout_norm)
        if retention_explicit > 0:
            terminal_mechanical_roe = terminal_growth / retention_explicit
        else:
            terminal_mechanical_roe = np.inf

        converges_with_existing_payout = (
            np.isfinite(terminal_mechanical_roe)
            and terminal_mechanical_roe < ke
        )

        if converges_with_existing_payout:
            y = PROJECTION_YEARS + 1
            while True:
                candidate = _project_one_year(
                    y, terminal_growth, ni_begin, book_begin, payout_norm
                )
                if candidate["residual_income"] <= 0:
                    convergence_year = y
                    break
                rows.append(candidate)
                pv_ri += candidate["pv_residual_income"]
                ni_begin = candidate["net_income"]
                book_begin = candidate["book_end"]
                extended_years += 1
                y += 1

                # Guarda exclusivamente operacional contra loop patológico. Não define
                # um prazo econômico de fade: se a convergência não ocorreu em 100 anos,
                # o modelo falha em vez de publicar um número.
                if y > 100:
                    raise ValueError(
                        "RI financeiro não convergiu em horizonte operacional de segurança; "
                        "valuation interrompido."
                    )
        else:
            # Fechamento terminal endógeno. A condição g < Ke é necessária para
            # retention_terminal = g/Ke ficar economicamente entre 0 e 1.
            if not np.isfinite(terminal_growth) or terminal_growth < 0 or terminal_growth >= ke:
                raise ValueError(
                    "RI financeiro indisponível: fechamento terminal exige 0 <= g terminal < Ke. "
                    f"g={terminal_growth:.2%}; Ke={ke:.2%}."
                )

            terminal_closure_applied = True
            terminal_retention = terminal_growth / ke
            terminal_payout = 1.0 - terminal_retention
            terminal_book_begin = float(book_begin)

            # Esta normalização é o passo que torna ROE_terminal = Ke e RI_terminal = 0
            # de forma simultânea, sem prazo arbitrário de fade.
            terminal_normalized_net_income = ke * terminal_book_begin
            terminal_normalized_roe = (
                terminal_normalized_net_income / terminal_book_begin
            )
            terminal_residual_income = (
                terminal_normalized_net_income - ke * terminal_book_begin
            )
            terminal_retained_earnings = (
                terminal_normalized_net_income * terminal_retention
            )
            terminal_book_end = terminal_book_begin + terminal_retained_earnings
            terminal_implied_growth_from_last_explicit = (
                terminal_normalized_net_income / float(ni_begin) - 1.0
                if np.isfinite(ni_begin) and abs(float(ni_begin)) > 1e-12
                else np.nan
            )

            # Valida identidades do estado estacionário. Nenhum valor é acrescentado
            # ao PV de RI porque, por construção, o RI terminal e posterior é zero.
            if not np.isclose(terminal_normalized_roe, ke, rtol=1e-10, atol=1e-12):
                raise ValueError("Falha interna: ROE terminal não igualou Ke.")
            if not np.isclose(terminal_residual_income, 0.0, rtol=0.0, atol=1e-8):
                raise ValueError("Falha interna: RI terminal não zerou.")
            if not np.isclose(
                terminal_book_end,
                terminal_book_begin * (1.0 + terminal_growth),
                rtol=1e-10,
                atol=max(1e-6, abs(terminal_book_begin) * 1e-10),
            ):
                raise ValueError(
                    "Falha interna: retenção terminal não reproduziu o crescimento g."
                )

            convergence_year = PROJECTION_YEARS + 1
            terminal_rule = (
                "Fechamento terminal endógeno: ROE=Ke; retention=g/Ke; "
                "payout=1-g/Ke; RI terminal=0"
            )

    equity_value_today = book0 + pv_ri
    fair_price_today = equity_value_today / security_count
    target_12m = (
        fair_price_today * (1.0 + ke) - float(expected_dividend)
        if pd.notna(expected_dividend) and np.isfinite(expected_dividend)
        else np.nan
    )

    projection = pd.DataFrame(rows)

    roe_hist = pd.to_numeric(
        hist_mkt.get("roe_parent", pd.Series(dtype=float)),
        errors="coerce"
    ).replace([np.inf, -np.inf], np.nan).dropna()

    return {
        "profile_label": profile_label,
        "book_equity_today": book0,
        "cost_equity": ke,
        "payout_norm": float(payout_norm),
        "projection": projection,
        "pv_residual_income": float(pv_ri),
        "equity_value_today": float(equity_value_today),
        "fair_price_today": float(fair_price_today),
        "target_12m": (
            float(target_12m)
            if pd.notna(target_12m) and np.isfinite(target_12m)
            else np.nan
        ),
        "historical_roe_median": safe_median(roe_hist.tail(4), np.nan),
        "minimum_explicit_years": int(PROJECTION_YEARS),
        "extended_positive_ri_years": int(extended_years),
        "explicit_ri_years": int(len(rows)),
        "convergence_year": int(convergence_year),
        "terminal_growth_used_for_extension": terminal_growth,
        "terminal_mechanical_roe": (
            float(terminal_mechanical_roe)
            if pd.notna(terminal_mechanical_roe)
            and np.isfinite(terminal_mechanical_roe)
            else np.nan
        ),
        "terminal_closure_applied": bool(terminal_closure_applied),
        "terminal_retention": (
            float(terminal_retention) if np.isfinite(terminal_retention) else np.nan
        ),
        "terminal_payout": (
            float(terminal_payout) if np.isfinite(terminal_payout) else np.nan
        ),
        "terminal_normalized_net_income": (
            float(terminal_normalized_net_income)
            if np.isfinite(terminal_normalized_net_income) else np.nan
        ),
        "terminal_normalized_roe": (
            float(terminal_normalized_roe)
            if np.isfinite(terminal_normalized_roe) else np.nan
        ),
        "terminal_residual_income": (
            float(terminal_residual_income)
            if np.isfinite(terminal_residual_income) else np.nan
        ),
        "terminal_implied_growth_from_last_explicit": (
            float(terminal_implied_growth_from_last_explicit)
            if np.isfinite(terminal_implied_growth_from_last_explicit) else np.nan
        ),
        "terminal_book_begin": (
            float(terminal_book_begin) if np.isfinite(terminal_book_begin) else np.nan
        ),
        "terminal_book_end": (
            float(terminal_book_end) if np.isfinite(terminal_book_end) else np.nan
        ),
        "terminal_rule": terminal_rule,
        "growth_audit": growth_audit,
    }


def forward_equity_targets(symbol, asset, hist_mkt, ttm, assump):
    """
    Preço-alvo financeiro em quatro métodos, preservando 50/20/20/10:
      50% Residual Income
      20% P/L
      20% P/VP
      10% Dividend Yield

    EV/EBITDA é deliberadamente substituído por P/VP porque dívida e ativos
    financeiros fazem parte da operação dos bancos/seguradoras.
    """
    h = compute_equity_historical_multiples(hist_mkt)

    pe_norm = assump["pe_norm"]
    pb_norm = assump["pb_norm"]
    dy_norm = assump["dy_norm"]
    payout_norm = assump["payout_norm"]
    security_count = assump["security_count"]

    growth_audit = build_growth_path(assump, SCENARIOS["Base"])
    g1 = float(growth_audit["growth"].iloc[0])
    ni1 = float(ttm["net_income"]) * (1.0 + g1)

    expected_dividend = (
        max(ni1, 0.0) * payout_norm / security_count
        if np.isfinite(payout_norm) and security_count > 0
        else np.nan
    )
    dividend_method = (
        "Lucro líquido projetado × payout histórico normalizado da própria companhia"
    )

    if pd.isna(expected_dividend) or not np.isfinite(expected_dividend):
        div_hist = pd.to_numeric(
            h.get("dividend_ps", pd.Series(dtype=float)),
            errors="coerce"
        ).replace([np.inf, -np.inf], np.nan).dropna()
        div_hist = div_hist[div_hist >= 0]
        expected_dividend = safe_median(div_hist.tail(4), np.nan)
        dividend_method = (
            "Fallback: mediana do dividendo/ativo histórico; nenhum payout é inventado"
        )

    # RI legado preservado para auditoria. Os métodos secundários continuam
    # exatamente na mesma base anterior, isolando a correção no slot principal.
    ri_legacy = financial_residual_income_value(
        hist_mkt=h,
        ttm=ttm,
        assump=assump,
        payout_norm=payout_norm,
        expected_dividend=expected_dividend,
        profile_label=get_equity_model_profile(asset),
    )

    # RI coerente ativado no slot principal de 50%.
    ri = financial_residual_income_value_coherent_candidate(
        hist_mkt=h,
        ttm=ttm,
        assump=assump,
        payout_norm=payout_norm,
        profile_label=get_equity_model_profile(asset),
    )

    first = ri_legacy["projection"].iloc[0]
    if len(ri_legacy["projection"]) < 2 or len(ri["projection"]) < 2:
        raise ValueError(
            "Projeção patrimonial possui menos de 2 anos; alvo de 24 meses indisponível."
        )
    second = ri_legacy["projection"].iloc[1]
    coherent_first = ri["projection"].iloc[0]
    coherent_second = ri["projection"].iloc[1]

    eps1 = float(first["net_income"]) / security_count
    bvps1 = float(first["book_end"]) / security_count
    eps2 = float(second["net_income"]) / security_count
    bvps2 = float(second["book_end"]) / security_count

    expected_dividend_24m = (
        float(second["dividends"]) / security_count
        if pd.notna(second["dividends"])
        and np.isfinite(second["dividends"])
        and security_count > 0
        else np.nan
    )

    coherent_dividend_1 = (
        float(coherent_first["dividends"]) / security_count
        if pd.notna(coherent_first["dividends"])
        and np.isfinite(coherent_first["dividends"])
        and security_count > 0
        else np.nan
    )
    coherent_dividend_2 = (
        float(coherent_second["dividends"]) / security_count
        if pd.notna(coherent_second["dividends"])
        and np.isfinite(coherent_second["dividends"])
        and security_count > 0
        else np.nan
    )
    ri_target_24m = (
        float(ri["fair_price_today"]) * ((1.0 + float(assump["cost_equity"])) ** 2)
        - coherent_dividend_1 * (1.0 + float(assump["cost_equity"]))
        - coherent_dividend_2
        if np.isfinite(coherent_dividend_1)
        and np.isfinite(coherent_dividend_2)
        else np.nan
    )

    pe_target = (
        eps1 * pe_norm
        if eps1 > 0 and np.isfinite(pe_norm)
        else np.nan
    )
    pb_target = (
        bvps1 * pb_norm
        if bvps1 > 0 and np.isfinite(pb_norm)
        else np.nan
    )
    dy_target = (
        expected_dividend / dy_norm
        if pd.notna(expected_dividend)
        and np.isfinite(expected_dividend)
        and expected_dividend >= 0
        and np.isfinite(dy_norm)
        and dy_norm > 0
        else np.nan
    )

    pe_target_24m = (
        eps2 * pe_norm
        if eps2 > 0 and np.isfinite(pe_norm)
        else np.nan
    )
    pb_target_24m = (
        bvps2 * pb_norm
        if bvps2 > 0 and np.isfinite(pb_norm)
        else np.nan
    )
    dy_target_24m = (
        expected_dividend_24m / dy_norm
        if pd.notna(expected_dividend_24m)
        and np.isfinite(expected_dividend_24m)
        and expected_dividend_24m >= 0
        and np.isfinite(dy_norm)
        and dy_norm > 0
        else np.nan
    )

    methods = {
        "Residual Income 12m": ri["target_12m"],
        "P/L 12m": pe_target,
        "P/VP 12m": pb_target,
        "Dividend Yield 12m": dy_target,
    }
    legacy_methods = {
        "Residual Income 12m": ri_legacy["target_12m"],
        "P/L 12m": pe_target,
        "P/VP 12m": pb_target,
        "Dividend Yield 12m": dy_target,
    }
    missing = [
        name for name in EQUITY_METHOD_WEIGHTS
        if pd.isna(methods.get(name, np.nan))
        or not np.isfinite(methods.get(name, np.nan))
    ]

    methods_24m = {
        "Residual Income 12m": ri_target_24m,
        "P/L 12m": pe_target_24m,
        "P/VP 12m": pb_target_24m,
        "Dividend Yield 12m": dy_target_24m,
    }
    missing_24m = [
        name for name in EQUITY_METHOD_WEIGHTS
        if pd.isna(methods_24m.get(name, np.nan))
        or not np.isfinite(methods_24m.get(name, np.nan))
    ]
    final_target_24m = (
        float(sum(
            max(float(methods_24m[name]), 0.0) * weight
            for name, weight in EQUITY_METHOD_WEIGHTS.items()
        ))
        if not missing_24m else np.nan
    )

    method_rows = []
    floored = []
    for name, weight in EQUITY_METHOD_WEIGHTS.items():
        raw = methods.get(name, np.nan)
        if pd.notna(raw) and np.isfinite(raw):
            used = max(float(raw), 0.0)
            if raw < 0:
                floored.append(name)
            used_weight = weight
        else:
            used = np.nan
            used_weight = np.nan
        method_rows.append({
            "Método": name,
            "Preço-alvo bruto 12m": raw,
            "Preço-alvo bruto 24m": methods_24m.get(name, np.nan),
            "Peso original": weight,
            "Valor usado no composto": used,
            "Peso usado": used_weight,
        })

    method_df = pd.DataFrame(method_rows).set_index("Método")

    if missing:
        final_target = np.nan
        upside = np.nan
    else:
        final_target = float(sum(
            max(float(methods[name]), 0.0) * weight
            for name, weight in EQUITY_METHOD_WEIGHTS.items()
        ))
        upside = np.nan

    legacy_missing = [
        name for name in EQUITY_METHOD_WEIGHTS
        if pd.isna(legacy_methods.get(name, np.nan))
        or not np.isfinite(legacy_methods.get(name, np.nan))
    ]
    legacy_final_target = (
        float(sum(
            max(float(legacy_methods[name]), 0.0) * weight
            for name, weight in EQUITY_METHOD_WEIGHTS.items()
        ))
        if not legacy_missing else np.nan
    )

    return {
        "history": h,
        "ri": ri,
        "ri_legacy": ri_legacy,
        "pe_norm": pe_norm,
        "pb_norm": pb_norm,
        "dy_norm": dy_norm,
        "payout_norm": payout_norm,
        "expected_dividend": expected_dividend,
        "expected_dividend_24m": expected_dividend_24m,
        "dividend_method": dividend_method,
        "eps1": eps1,
        "bvps1": bvps1,
        "eps2": eps2,
        "bvps2": bvps2,
        "ri_target_24m": ri_target_24m,
        "pe_target": pe_target,
        "pb_target": pb_target,
        "dy_target": dy_target,
        "pe_target_24m": pe_target_24m,
        "pb_target_24m": pb_target_24m,
        "dy_target_24m": dy_target_24m,
        "method_table": method_df,
        "missing_methods": missing,
        "missing_methods_24m": missing_24m,
        "floored_methods": floored,
        "target_12m": final_target,
        "target_24m": final_target_24m,
        "upside": upside,
        "legacy_target_12m": legacy_final_target,
        "legacy_missing_methods": legacy_missing,
    }


def run_equity_asset(symbol, asset, rate_context):
    """
    Executa o módulo patrimonial para todos os ativos não FCFF do Radar W1.

    O objetivo é completar o universo sem forçar bancos/seguradoras/holdings
    no FCFF corporativo.
    """
    print("\n" + "=" * 90)
    print(f"{symbol} — {asset.get('name', symbol)} | MÓDULO EQUITY/PATRIMONIAL")
    print("=" * 90)

    print("1/5 — Carregando histórico patrimonial CVM 2021–2025...")
    hist, diagnostics = load_equity_annual_history(asset)

    print("2/5 — Montando lucro TTM e patrimônio líquido atual...")
    ttm = load_equity_ttm(asset)
    if ttm is None:
        raise ValueError("TTM patrimonial não encontrado.")

    print("3/5 — Obtendo preço, dividendos e beta...")
    price = current_price(asset["ticker"])
    beta = estimate_beta(asset["ticker"])

    print("4/5 — Normalizando P/L, P/VP, DY, payout e Ke...")
    hist_mkt = annual_equity_market_data(symbol, asset, hist)
    assump = normalize_equity_assumptions(
        hist_mkt=hist_mkt,
        ttm=ttm,
        rf=rate_context["valuation_rf"],
        beta=beta,
        price=price,
        asset=asset,
    )

    print("5/5 — Residual Income + múltiplos patrimoniais + alvo composto...")
    targets = forward_equity_targets(
        symbol=symbol,
        asset=asset,
        hist_mkt=hist_mkt,
        ttm=ttm,
        assump=assump,
    )

    targets["upside"] = (
        targets["target_12m"] / price - 1.0
        if pd.notna(targets["target_12m"])
        and np.isfinite(targets["target_12m"])
        and price > 0
        else np.nan
    )

    profile = get_equity_model_profile(asset)
    if profile in {"bank", "bank_unit", "financial"}:
        status = "MÓDULO BANCÁRIO ATIVO — RI COERENTE + P/L + P/VP + DY"
        validation = "Modelo equity-side apropriado; RI coerente ativo no slot de 50%; FCFF não utilizado"
    elif profile in {"insurance", "insurance_holding"}:
        status = "MÓDULO SEGURIDADE ATIVO — RI COERENTE + P/L + P/VP + DY"
        validation = "Modelo equity-side apropriado; RI coerente ativo no slot de 50%; FCFF não utilizado"
    elif profile == "market_infrastructure":
        status = "MÓDULO INFRA FINANCEIRA ATIVO — RI COERENTE + P/L + P/VP + DY"
        validation = "Modelo patrimonial com RI coerente; EV/NWC corporativo não utilizado"
    elif profile == "holding":
        status = "MÓDULO HOLDING CONTÁBIL — PROXY, NÃO VALIDADO COMO NAV/SOTP"
        validation = (
            "O composto RI coerente + P/L + P/VP + DY permanece disponível apenas como "
            "proxy contábil automatizada. NAV/SOTP continua sendo a referência econômica "
            "preferencial para a holding; nenhum NAV é inventado e o proxy não é publicado "
            "como alvo final validado."
        )
    else:
        status = "MÓDULO EQUITY ATIVO — RI COERENTE"
        validation = "Modelo patrimonial com RI coerente"

    validated_target_12m = np.nan if profile == "holding" else targets["target_12m"]
    validated_upside = (
        validated_target_12m / price - 1.0
        if pd.notna(validated_target_12m)
        and np.isfinite(validated_target_12m)
        and price > 0
        else np.nan
    )

    validated_target_24m = np.nan if profile == "holding" else targets["target_24m"]
    validated_upside_24m = (
        validated_target_24m / price - 1.0
        if pd.notna(validated_target_24m)
        and np.isfinite(validated_target_24m)
        and price > 0
        else np.nan
    )

    print(f"\nPreço atual: R$ {price:,.2f}")
    print(
        f"Rf nominal BRL: {assump['rf']:.2%} | "
        f"ERP Brasil: {assump['erp']:.2%} | "
        f"Beta: {assump['beta']:.2f} | Ke: {assump['cost_equity']:.2%}"
    )
    print(
        f"Lucro líquido TTM: R$ {ttm['net_income']/1e9:,.2f} bi | "
        f"PL controladores: R$ {ttm['equity_parent']/1e9:,.2f} bi"
    )
    print(
        f"Ações subjacentes CVM: {ttm['shares']/1e9:,.3f} bi | "
        f"Quantidade do ativo-alvo: {ttm['security_count']/1e9:,.3f} bi"
    )
    if _target_security_factor(asset) != 1.0:
        print(
            f"Conversão Unit: {_target_security_factor(asset):.0f} ações por ativo | "
            f"{asset.get('unit_structure_basis', 'base societária cadastrada')}"
        )

    print("\nPREMISSAS / MÚLTIPLOS PATRIMONIAIS NORMALIZADOS")
    print(f"Crescimento inicial do lucro líquido: {assump['base_growth']:.2%}")
    print(f"P/L normalizado: {assump['pe_norm']:.2f}x")
    print(f"P/VP normalizado: {assump['pb_norm']:.2f}x")
    print(f"Dividend Yield normalizado: {assump['dy_norm']:.2%}")
    print(f"Payout normalizado: {assump['payout_norm']:.2%}")
    print(
        f"Dividendo projetado 12m: R$ {targets['expected_dividend']:,.2f} | "
        f"{targets['dividend_method']}"
    )

    print("\nHISTÓRICO PATRIMONIAL")
    hist_display = targets["history"][[
        "net_income", "equity_parent", "roe_parent", "security_count",
        "price_yend", "dividend_ps", "pe", "pb",
        "dividend_yield", "payout"
    ]].copy()
    hist_display.columns = [
        "Lucro R$", "PL controladores R$", "ROE", "Qtd. ativo-alvo",
        "Preço fim ano", "Dividendo/ativo", "P/L", "P/VP", "DY", "Payout"
    ]
    display(hist_display.style.format({
        "Lucro R$": lambda x: f"R$ {x/1e9:,.2f} bi" if pd.notna(x) else "n/d",
        "PL controladores R$": lambda x: f"R$ {x/1e9:,.2f} bi" if pd.notna(x) else "n/d",
        "ROE": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
        "Qtd. ativo-alvo": lambda x: f"{x:,.0f}" if pd.notna(x) else "n/d",
        "Preço fim ano": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "Dividendo/ativo": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "P/L": lambda x: f"{x:.2f}x" if pd.notna(x) else "n/d",
        "P/VP": lambda x: f"{x:.2f}x" if pd.notna(x) else "n/d",
        "DY": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
        "Payout": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
    }))

    ri = targets["ri"]
    ri_legacy = targets["ri_legacy"]
    print("\nMÓDULO RESIDUAL INCOME — EQUITY | RI COERENTE ATIVADO")
    print(f"RI legado — justo hoje: R$ {ri_legacy['fair_price_today']:,.2f}")
    print(f"RI legado — alvo 12m: R$ {ri_legacy['target_12m']:,.2f}")
    print(f"RI coerente — justo hoje: R$ {ri['fair_price_today']:,.2f}")
    print(f"RI coerente — alvo 12m: R$ {ri['target_12m']:,.2f}")
    print(
        "Regra ativa: payout só pode subir quando o crescimento usado exige menos "
        "retenção do que o payout histórico implica; nunca cai para fabricar crescimento."
    )
    if ri.get("terminal_positive_excess_capitalized", False):
        print(
            "Terminal RI positivo capitalizado: "
            f"ROE terminal={ri['terminal_roe']:.2%} | "
            f"Ke={ri['cost_equity']:.2%} | "
            f"payout terminal={ri['terminal_payout']:.2%} | "
            f"PV RI terminal=R$ {ri['pv_terminal_residual_income']/1e9:,.2f} bi"
        )
    else:
        print(
            "Terminal RI positivo não capitalizado: o ROE terminal produzido pelo "
            "próprio modelo não supera o Ke."
        )

    ri_display = ri["projection"].copy()
    display(ri_display.style.format({
        "growth_net_income": "{:.2%}",
        "net_income": lambda x: f"R$ {x/1e9:,.2f} bi",
        "book_begin": lambda x: f"R$ {x/1e9:,.2f} bi",
        "roe": "{:.2%}",
        "ke": "{:.2%}",
        "historical_payout": "{:.2%}",
        "payout_used": "{:.2%}",
        "retention_used": "{:.2%}",
        "sustainable_growth_historical_payout": "{:.2%}",
        "sustainable_growth_used": "{:.2%}",
        "residual_income": lambda x: f"R$ {x/1e9:,.2f} bi",
        "dividends": lambda x: f"R$ {x/1e9:,.2f} bi",
        "retained_earnings": lambda x: f"R$ {x/1e9:,.2f} bi",
        "book_end": lambda x: f"R$ {x/1e9:,.2f} bi",
        "pv_residual_income": lambda x: f"R$ {x/1e9:,.2f} bi",
    }))

    print("\nPREÇO-ALVO — MÓDULO PATRIMONIAL")
    method_df = targets["method_table"].copy()
    method_df["Upside bruto vs atual"] = (
        method_df["Preço-alvo bruto 12m"] / price - 1.0
    )
    display(method_df.style.format({
        "Preço-alvo bruto 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "Peso original": "{:.0%}",
        "Valor usado no composto": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "Peso usado": lambda x: f"{x:.0%}" if pd.notna(x) else "n/d",
        "Upside bruto vs atual": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
    }))

    if targets["missing_methods"]:
        print(
            "ALVO FINAL INDISPONÍVEL: método(s) ausente(s): "
            + ", ".join(targets["missing_methods"])
            + ". Os pesos não são redistribuídos."
        )
    if targets["floored_methods"]:
        print(
            "Piso zero preservando peso: "
            + ", ".join(targets["floored_methods"])
        )

    print("\nGOVERNANÇA DO MODELO")
    print("Perfil:", profile)
    print("Status:", status)
    print("Validação:", validation)
    print("-" * 90)
    print(f"PREÇO ATUAL            : R$ {price:,.2f}")
    print(
        "ALVO COMPOSTO RI COERENTE 12M : "
        + (
            f"R$ {targets['target_12m']:,.2f}"
            if pd.notna(targets["target_12m"])
            else "n/d"
        )
    )
    if profile == "holding":
        print("ALVO FINAL VALIDADO 12M      : n/d — holding exige NAV/SOTP")
        print("ALVO FINAL VALIDADO 24M      : n/d — holding exige NAV/SOTP")
        print("UPSIDE/DOWNSIDE VALIDADO     : n/d")
    else:
        print(
            "ALVO FINAL VALIDADO 12M      : "
            + (f"R$ {validated_target_12m:,.2f}" if pd.notna(validated_target_12m) else "n/d")
        )
        print(
            "ALVO FINAL VALIDADO 24M      : "
            + (f"R$ {validated_target_24m:,.2f}" if pd.notna(validated_target_24m) else "n/d")
        )
        print(
            "UPSIDE/DOWNSIDE VALIDADO 12M : "
            + (f"{validated_upside:.1%}" if pd.notna(validated_upside) else "n/d")
        )
        print(
            "POTENCIAL PREÇO 24M          : "
            + (f"{validated_upside_24m:.1%}" if pd.notna(validated_upside_24m) else "n/d")
        )
    print("-" * 90)

    print("\nDIAGNÓSTICO DE EXTRAÇÃO CVM — MÓDULO PATRIMONIAL")
    source_rows = []
    for year in HIST_YEARS:
        src = diagnostics.get(year, {}).get("Base demonstrações CVM", {})
        source_rows.append({
            "Ano": year,
            "DRE": src.get("DRE", "n/d"),
            "BPP": src.get("BPP", "n/d"),
        })
    display(pd.DataFrame(source_rows).set_index("Ano"))

    print("Lucro líquido TTM — contas efetivamente usadas:")
    for period, label in ttm.get("net_income_components", {}).items():
        print(f"  • {period}: {label if label else 'n/d'}")

    print("Patrimônio líquido atual — contas usadas:")
    for label in ttm.get("equity_labels", []):
        print("  •", label)

    if "historical_split_factor" in hist_mkt.columns:
        sf = pd.to_numeric(
            hist_mkt["historical_split_factor"], errors="coerce"
        )
        events = sf[
            sf.notna() & (abs(sf - 1.0) > 1e-12)
        ]
        if len(events):
            print("Base histórica ajustada por splits/grupamentos do ticker-alvo:")
            for year, factor in events.items():
                print(f"  • {int(year)}: fator acumulado posterior {factor:.6g}x")

    plt.figure(figsize=(8, 5))
    plot_vals = {
        "Preço atual": price,
        "RI legado 12m": ri_legacy["target_12m"],
        "RI coerente 12m": ri["target_12m"],
        "P/L 12m": targets["pe_target"],
        "P/VP 12m": targets["pb_target"],
        "DY 12m": targets["dy_target"],
    }
    if pd.notna(targets["target_12m"]):
        plot_vals["Alvo final"] = targets["target_12m"]
    plt.bar(plot_vals.keys(), plot_vals.values())
    plt.axhline(price, linestyle="--", linewidth=1)
    plt.title(f"{symbol} — Módulo patrimonial / equity")
    plt.ylabel("R$ por ativo-alvo")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.show()

    return {
        "symbol": symbol,
        "price": price,
        "hist": hist_mkt,
        "ttm": ttm,
        "assumptions": assump,
        "residual_income": ri,
        "residual_income_legacy": ri_legacy,
        "method_table": targets["method_table"],
        "target_12m": targets["target_12m"],
        "upside": targets["upside"],
        "legacy_target_12m": targets.get("legacy_target_12m", np.nan),
        "validated_target_12m": validated_target_12m,
        "validated_upside": validated_upside,
        "target_24m": targets["target_24m"],
        "validated_target_24m": validated_target_24m,
        "validated_upside_24m": validated_upside_24m,
        "expected_dividend": targets["expected_dividend"],
        "expected_dividend_24m": targets["expected_dividend_24m"],
        "pe_target": targets["pe_target"],
        "pb_target": targets["pb_target"],
        "dy_target": targets["dy_target"],
        "pe_target_24m": targets["pe_target_24m"],
        "pb_target_24m": targets["pb_target_24m"],
        "dy_target_24m": targets["dy_target_24m"],
        "missing_methods": targets["missing_methods"],
        "floored_methods": targets["floored_methods"],
        "model_profile": profile,
        "model_status": status,
        "validation_note": validation,
        "diagnostics": diagnostics,
    }


# ================================================================
# 8) SENSIBILIDADE DCF
# ================================================================

def dcf_sensitivity(start_revenue, assump, wacc_steps=(-0.02, -0.01, 0, 0.01, 0.02), g_steps=(-0.01, -0.005, 0, 0.005, 0.01)):
    """
    Sensibilidade do DCF usando o MESMO fechamento econômico do cálculo principal.

    Os cinco anos explícitos permanecem iguais ao cenário-base. Para cada par
    WACC/g, o valor terminal recalcula o reinvestimento estável por g/ROIC,
    adotando ROIC terminal = WACC (sem excesso de retorno perpétuo).
    """
    base_proj = project_fcff(start_revenue, assump, SCENARIOS["Base"])
    rows = []

    for dw in wacc_steps:
        w_input = assump["wacc"] + dw
        row = {}

        for dg in g_steps:
            g = TERMINAL_GROWTH + dg
            if w_input <= g + 0.005:
                row[g] = np.nan
                continue

            terminal = stable_terminal_value(base_proj, w_input, g)
            w = terminal["wacc"]

            finite = sum(
                float(r.fcff) / ((1 + w) ** int(r.year))
                for r in base_proj.itertuples()
            )
            pv_tv = terminal["terminal_value"] / ((1 + w) ** PROJECTION_YEARS)
            ev = finite + pv_tv
            eq = ev - assump["net_debt"]
            row[g] = eq / assump["shares"]

        rows.append(pd.Series(row, name=w_input))

    sens = pd.DataFrame(rows)
    sens.index = [f"WACC {x:.1%}" for x in sens.index]
    sens.columns = [f"g {x:.1%}" for x in sens.columns]
    return sens


# ================================================================
# 9) MODELO COMPLETO POR ATIVO
# ================================================================

def run_asset(symbol, asset, rate_context):
    rf = float(rate_context["valuation_rf"])
    print("\n" + "=" * 90)
    print(f"{symbol} — {asset['name']} | CVM {asset['cvm']}")
    print("=" * 90)

    print("1/6 — Baixando e estruturando DFPs 2021–2025...")
    hist, diagnostics = load_annual_history(asset)

    print("2/6 — Montando TTM com o último ITR de 2026...")
    ttm = load_ttm(asset)

    print("3/6 — Obtendo preço, dividendos, beta e valor de mercado...")
    price = current_price(asset["ticker"])
    beta = estimate_beta(asset["ticker"])
    hist_mkt = annual_market_data(symbol, asset, hist)

    print("4/6 — Validando extrações críticas, normalizando premissas e calculando WACC...")
    if ttm is None:
        raise ValueError("TTM indisponível; valuation interrompido.")
    for field, label in [("revenue", "Receita TTM"), ("da", "D&A TTM"), ("capex", "CAPEX TTM"), ("shares", "Ações")]:
        v = ttm.get(field, np.nan)
        if pd.isna(v) or not np.isfinite(v) or (field in {"revenue", "da", "capex", "shares"} and v <= 0):
            raise ValueError(f"{label} inválido/ausente; valuation interrompido para evitar fallback silencioso.")

    market_cap, market_cap_detail = current_company_market_cap(symbol, asset, ttm, price)
    assump = normalize_assumptions(
        hist_mkt, ttm, rf, beta, price,
        market_cap_override=market_cap,
        asset=asset,
    )

    # Receita-base = TTM quando disponível; senão último DFP
    start_revenue = ttm["revenue"] if ttm is not None and pd.notna(ttm["revenue"]) else hist_mkt["revenue"].dropna().iloc[-1]

    print("5/6 — DCF, cenários, múltiplos e dividendos...")
    dcf_results = {}
    scenario_rows = []
    weighted_dcf_today = 0.0
    for name, sc in SCENARIOS.items():
        res = dcf_value(start_revenue, assump, sc)
        dcf_results[name] = res
        fp = res["fair_price_today"]
        weighted_dcf_today += sc["weight"] * fp
        scenario_rows.append({
            "Cenário": name,
            "Peso": sc["weight"],
            "WACC": res["wacc"],
            "g terminal": res["terminal_g"],
            "ROIC terminal": res["terminal_roic"],
            "Reinvest. terminal": res["terminal_reinvestment_rate"],
            "PV terminal / EV": res["terminal_share_ev"],
            "Valor justo hoje": fp,
        })
    scenario_df = pd.DataFrame(scenario_rows).set_index("Cenário")

    mult = forward_multiple_targets(symbol, hist_mkt, assump, start_revenue)
    expected_dividend = mult["expected_dividend"]
    expected_dividend_24m = mult["expected_dividend_24m"]

    # Converte DCF de hoje para alvos ex-dividendo em 12 e 24 meses.
    # A regra de 24m é a extensão temporal exata da convenção já usada em 12m:
    # capitaliza o valor justo a Ke e retira os dividendos esperados nos dois anos.
    dcf_12m = weighted_dcf_today * (1 + assump["cost_equity"]) - expected_dividend
    dcf_24m = (
        weighted_dcf_today * ((1 + assump["cost_equity"]) ** 2)
        - expected_dividend * (1 + assump["cost_equity"])
        - expected_dividend_24m
    )

    method_values = {
        "DCF 12m": dcf_12m,
        "P/L 12m": mult["pe_target"],
        "EV/EBITDA 12m": mult["ev_ebitda_target"],
        "Dividend Yield 12m": mult["dy_target"],
    }
    method_values_24m = {
        "DCF 12m": dcf_24m,
        "P/L 12m": mult["pe_target_24m"],
        "EV/EBITDA 12m": mult["ev_ebitda_target_24m"],
        "Dividend Yield 12m": mult["dy_target_24m"],
    }

    # Composto FCFF genérico — preservado integralmente para comparação/auditoria.
    available = {
        k: float(v)
        for k, v in method_values.items()
        if pd.notna(v) and np.isfinite(v)
    }
    missing_methods = [k for k in METHOD_WEIGHTS if k not in available]
    composite_values = {k: max(v, 0.0) for k, v in available.items()}
    floored_methods = [k for k, v in available.items() if v < 0]

    all_methods_available = len(missing_methods) == 0
    generic_final_target = (
        sum(composite_values[k] * METHOD_WEIGHTS[k] for k in METHOD_WEIGHTS)
        if all_methods_available else np.nan
    )
    generic_upside = (
        generic_final_target / price - 1
        if pd.notna(generic_final_target) and np.isfinite(generic_final_target)
        else np.nan
    )

    available_24m = {
        k: float(v)
        for k, v in method_values_24m.items()
        if pd.notna(v) and np.isfinite(v)
    }
    missing_methods_24m = [k for k in METHOD_WEIGHTS if k not in available_24m]
    composite_values_24m = {k: max(v, 0.0) for k, v in available_24m.items()}
    all_methods_available_24m = len(missing_methods_24m) == 0
    generic_final_target_24m = (
        sum(
            composite_values_24m[k] * METHOD_WEIGHTS[k]
            for k in METHOD_WEIGHTS
        )
        if all_methods_available_24m else np.nan
    )
    generic_upside_24m = (
        generic_final_target_24m / price - 1
        if pd.notna(generic_final_target_24m)
        and np.isfinite(generic_final_target_24m)
        else np.nan
    )

    # ----------------------------------------------------------------
    # Residual Income — legado preservado + RI coerente ativado.
    # regulated: RI coerente ocupa o slot principal de 50%.
    # high_roic_growth: DCF/FCFF permanece principal; RI é diagnóstico.
    # ----------------------------------------------------------------
    profile = str(asset.get("fcff_profile", "generic")).strip().lower()
    ri_legacy_result = None
    ri_result = None
    ri_error = None
    ri_method_values = None
    ri_method_df = None
    ri_missing_methods = []
    ri_floored_methods = []
    ri_final_target = np.nan
    ri_upside = np.nan
    ri_final_target_24m = np.nan
    ri_upside_24m = np.nan
    ri_missing_methods_24m = []
    ri_legacy_final_target = np.nan

    if profile in {"regulated", "high_roic_growth"}:
        try:
            ri_legacy_result = residual_income_value(
                hist_mkt=hist_mkt,
                ttm=ttm,
                assump=assump,
                start_revenue=start_revenue,
                payout_norm=mult["payout_norm"],
                expected_dividend=expected_dividend,
                profile_label=profile,
            )
            ri_result = residual_income_value_coherent_candidate(
                hist_mkt=hist_mkt,
                ttm=ttm,
                assump=assump,
                start_revenue=start_revenue,
                payout_norm=mult["payout_norm"],
                profile_label=profile,
            )
            ri_projection = ri_result.get("projection", pd.DataFrame())
            if len(ri_projection) < 2:
                raise ValueError(
                    "RI coerente possui menos de 2 anos; alvo de 24 meses indisponível."
                )
            ri_dividend_1 = (
                float(ri_projection.iloc[0]["dividends"]) / assump["shares"]
            )
            ri_dividend_2 = (
                float(ri_projection.iloc[1]["dividends"]) / assump["shares"]
            )
            ri_target_24m_primary = (
                float(ri_result["fair_price_today"])
                * ((1.0 + float(assump["cost_equity"])) ** 2)
                - ri_dividend_1 * (1.0 + float(assump["cost_equity"]))
                - ri_dividend_2
            )

            ri_method_values = {
                "DCF 12m": ri_result["target_12m"],
                "P/L 12m": mult["pe_target"],
                "EV/EBITDA 12m": mult["ev_ebitda_target"],
                "Dividend Yield 12m": mult["dy_target"],
            }
            ri_method_values_24m = {
                "DCF 12m": ri_target_24m_primary,
                "P/L 12m": mult["pe_target_24m"],
                "EV/EBITDA 12m": mult["ev_ebitda_target_24m"],
                "Dividend Yield 12m": mult["dy_target_24m"],
            }
            ri_available = {
                k: float(v) for k, v in ri_method_values.items()
                if pd.notna(v) and np.isfinite(v)
            }
            ri_missing_methods = [k for k in METHOD_WEIGHTS if k not in ri_available]
            ri_composite_values = {k: max(v, 0.0) for k, v in ri_available.items()}
            ri_floored_methods = [k for k, v in ri_available.items() if v < 0]
            ri_final_target = (
                sum(ri_composite_values[k] * METHOD_WEIGHTS[k] for k in METHOD_WEIGHTS)
                if len(ri_missing_methods) == 0 else np.nan
            )
            ri_upside = (
                ri_final_target / price - 1
                if pd.notna(ri_final_target) and np.isfinite(ri_final_target) else np.nan
            )

            ri_available_24m = {
                k: float(v) for k, v in ri_method_values_24m.items()
                if pd.notna(v) and np.isfinite(v)
            }
            ri_missing_methods_24m = [
                k for k in METHOD_WEIGHTS if k not in ri_available_24m
            ]
            ri_composite_values_24m = {
                k: max(v, 0.0) for k, v in ri_available_24m.items()
            }
            ri_final_target_24m = (
                sum(
                    ri_composite_values_24m[k] * METHOD_WEIGHTS[k]
                    for k in METHOD_WEIGHTS
                )
                if len(ri_missing_methods_24m) == 0 else np.nan
            )
            ri_upside_24m = (
                ri_final_target_24m / price - 1
                if pd.notna(ri_final_target_24m)
                and np.isfinite(ri_final_target_24m)
                else np.nan
            )

            legacy_values = {
                "DCF 12m": ri_legacy_result["target_12m"],
                "P/L 12m": mult["pe_target"],
                "EV/EBITDA 12m": mult["ev_ebitda_target"],
                "Dividend Yield 12m": mult["dy_target"],
            }
            if all(pd.notna(legacy_values[k]) and np.isfinite(legacy_values[k]) for k in METHOD_WEIGHTS):
                ri_legacy_final_target = sum(
                    max(float(legacy_values[k]), 0.0) * METHOD_WEIGHTS[k]
                    for k in METHOD_WEIGHTS
                )

            ri_display_values = {
                "Residual Income coerente 12m": ri_method_values["DCF 12m"],
                "P/L 12m": ri_method_values["P/L 12m"],
                "EV/EBITDA 12m": ri_method_values["EV/EBITDA 12m"],
                "Dividend Yield 12m": ri_method_values["Dividend Yield 12m"],
            }
            ri_display_weights = {
                "Residual Income coerente 12m": METHOD_WEIGHTS["DCF 12m"],
                "P/L 12m": METHOD_WEIGHTS["P/L 12m"],
                "EV/EBITDA 12m": METHOD_WEIGHTS["EV/EBITDA 12m"],
                "Dividend Yield 12m": METHOD_WEIGHTS["Dividend Yield 12m"],
            }
            ri_method_df = pd.DataFrame({
                "Preço-alvo bruto 12m": pd.Series(ri_display_values),
                "Peso original": pd.Series(ri_display_weights),
            })
            ri_method_df["Valor usado no composto"] = [
                max(float(v), 0.0) if pd.notna(v) and np.isfinite(v) else np.nan
                for v in ri_method_df["Preço-alvo bruto 12m"]
            ]
            ri_method_df["Peso usado"] = [
                ri_display_weights[i] if len(ri_missing_methods) == 0 else np.nan
                for i in ri_method_df.index
            ]
            ri_method_df["Upside bruto vs atual"] = (
                ri_method_df["Preço-alvo bruto 12m"] / price - 1
            )
        except Exception as e:
            ri_error = f"{type(e).__name__}: {e}"

    ri_ready = (
        profile in {"regulated", "high_roic_growth"}
        and ri_result is not None
        and pd.notna(ri_final_target)
        and np.isfinite(ri_final_target)
        and len(ri_missing_methods) == 0
    )

    governance = get_fcff_model_governance(
        asset,
        ri_module_ready=ri_ready,
        ri_module_reason=ri_error,
    )

    if profile == "regulated":
        validated_final_target = (
            ri_final_target if governance["validated_final_target"] and ri_ready else np.nan
        )
        validated_upside = (
            ri_upside if pd.notna(validated_final_target) and np.isfinite(validated_final_target) else np.nan
        )
        validated_final_target_24m = (
            ri_final_target_24m
            if governance["validated_final_target"]
            and ri_ready
            and len(ri_missing_methods_24m) == 0
            else np.nan
        )
    else:
        validated_final_target = (
            generic_final_target
            if governance["validated_final_target"] and all_methods_available
            else np.nan
        )
        validated_upside = (
            validated_final_target / price - 1
            if pd.notna(validated_final_target) and np.isfinite(validated_final_target)
            else np.nan
        )
        validated_final_target_24m = (
            generic_final_target_24m
            if governance["validated_final_target"] and all_methods_available_24m
            else np.nan
        )

    validated_upside_24m = (
        validated_final_target_24m / price - 1
        if pd.notna(validated_final_target_24m)
        and np.isfinite(validated_final_target_24m)
        and price > 0
        else np.nan
    )

    # Compatibilidade: target_12m/upside continuam representando o composto genérico
    # calculado pelo motor. Os novos campos validated_* distinguem o que pode ser
    # publicado como alvo final segundo a governança setorial.
    final_target = generic_final_target
    upside = generic_upside

    method_df = pd.DataFrame({
        "Preço-alvo bruto 12m": pd.Series(method_values),
        "Preço-alvo bruto 24m": pd.Series(method_values_24m),
        "Peso original": pd.Series(METHOD_WEIGHTS),
    })
    method_df["Valor usado no composto"] = [
        composite_values.get(i, np.nan) for i in method_df.index
    ]
    method_df["Peso usado"] = [
        METHOD_WEIGHTS[i] if all_methods_available else np.nan
        for i in method_df.index
    ]
    method_df["Upside bruto vs atual"] = method_df["Preço-alvo bruto 12m"] / price - 1

    print("6/6 — Gerando diagnóstico, sensibilidade e resumo...")
    sens = dcf_sensitivity(start_revenue, assump)

    # ---------------- RESULTADOS ----------------
    print(f"\nPreço atual: R$ {price:,.2f}")
    print(f"Selic Meta atual (diagnóstico; não usada diretamente no WACC): {rate_context['selic_spot']:.2%}")
    curve_rate = rate_context.get("sovereign_curve_rate", np.nan)
    curve_vertex = rate_context.get("curve_vertex")
    curve_date = rate_context.get("curve_date")
    if pd.notna(curve_rate):
        curve_date_txt = (
            pd.Timestamp(curve_date).date().isoformat()
            if curve_date is not None and pd.notna(curve_date)
            else "n/d"
        )
        print(
            f"ETTJ soberana prefixada ANBIMA: {curve_rate:.2%} "
            f"(vértice {curve_vertex} dias úteis; data {curve_date_txt})"
        )
        print(
            f"Default spread Brasil retirado da taxa soberana: {rate_context['default_spread']:.2%} "
            f"(referência {rate_context['default_spread_asof']})"
        )
    else:
        print(f"Fonte da Rf: {rate_context.get('rf_source', 'RF_OVERRIDE')}")
    print(f"Rf nominal BRL de longo prazo usada no valuation: {rf:.2%}")
    print(
        f"ERP total Brasil usado no CAPM: {assump['erp']:.2%} "
        f"(referência {assump['erp_asof']})"
    )
    print(f"Beta 3 anos semanal vs BOVA11: {beta:.2f}")
    print(
        f"Custo de capital próprio (Ke): {assump['cost_equity']:.2%} "
        f"= Rf {rf:.2%} + beta {beta:.2f} × ERP {assump['erp']:.2%}"
    )
    print(
        f"Custo bruto da dívida (Kd): {assump['cost_debt']:.2%} "
        f"= Rf {rf:.2%} + default soberano {assump['country_default_spread']:.2%} "
        f"+ spread corporativo {assump['corporate_debt_spread']:.2%}"
    )
    print(f"Taxa marginal usada no escudo fiscal do WACC: {assump['wacc_tax_rate']:.2%}")
    print(f"WACC base: {assump['wacc']:.2%}")
    print(f"Pesos no WACC — Equity: {assump['equity_weight']:.2%} | Dívida: {assump['debt_weight']:.2%}")
    print(f"Market Cap usado no WACC: R$ {assump['market_cap']/1e9:,.2f} bi")
    if market_cap_detail.get("method") == "classes":
        on_ticker_txt = market_cap_detail.get("ordinary_ticker", "").replace(".SA", "")
        pn_ticker_txt = market_cap_detail.get("preferred_ticker", "").replace(".SA", "")
        print(
            "Market Cap por classe: "
            f"{on_ticker_txt} R$ {market_cap_detail['ordinary_price']:,.2f} × "
            f"{market_cap_detail['ordinary_shares']/1e9:,.3f} bi + "
            f"{pn_ticker_txt} R$ {market_cap_detail['preferred_price']:,.2f} × "
            f"{market_cap_detail['preferred_shares']/1e9:,.3f} bi"
        )
    print(f"Dívida líquida: R$ {assump['net_debt']/1e9:,.2f} bi")
    print(f"Ações usadas: {assump['shares']/1e9:,.3f} bi")

    share_info = ttm.get("share_info", {})
    if share_info:
        raw_issued = share_info.get("issued_total_raw", np.nan)
        raw_treasury = share_info.get("treasury_total_raw", np.nan)
        sf = share_info.get("scale_factor", np.nan)
        if pd.notna(raw_issued) and pd.notna(sf):
            print(f"Ações CVM — capital integralizado (bruto): {raw_issued:,.0f} | fator de escala: x{sf:,.0f}")
        if pd.notna(raw_treasury) and pd.notna(sf):
            print(f"Ações CVM — tesouraria (bruto): {raw_treasury:,.0f} | fator de escala: x{sf:,.0f}")
        std = share_info.get("standard_outstanding", np.nan)
        reported = share_info.get("reported_total_scaled", np.nan)
        if pd.notna(std) and pd.notna(reported):
            print(f"Candidatos após escala — CVM padrão (capital - tesouraria): {std/1e9:,.6f} bi | campo capital: {reported/1e9:,.6f} bi")
        official_ref = share_info.get("official_reference", np.nan)
        if pd.notna(official_ref):
            print(f"Referência oficial da companhia na data: {official_ref/1e9:,.6f} bi ações em circulação")
        print(f"Critério final de ações: {share_info.get('basis', 'n/d')}")

    if ttm is not None:
        print(f"TTM baseado no ITR de: {pd.Timestamp(ttm['ref_date']).date()}")

    prem = pd.DataFrame({
        "Premissa": [
            "Crescimento receita inicial (antes do timing)", "Margem EBIT normalizada", "D&A / Receita",
            "CAPEX / Receita", "NWC operacional / Receita (usado)",
            "Delta NWC / Receita histórico (diagnóstico)", "Margem líquida normalizada",
            "Taxa efetiva normalizada", "Selic Meta atual (diagnóstico)",
            "ETTJ soberana ANBIMA", "Default spread Brasil",
            "Rf nominal BRL longo prazo", "ERP total Brasil", "Ke",
            "Spread corporativo da dívida", "Kd bruto",
            "Taxa marginal escudo WACC", "WACC", "g terminal"
        ],
        "Valor": [
            assump["base_growth"], assump["ebit_margin"], assump["da_ratio"],
            assump["capex_ratio"], assump["nwc_ratio"], assump["d_nwc_ratio"], assump["net_margin"],
            assump["tax_rate"], rate_context["selic_spot"],
            rate_context.get("sovereign_curve_rate", np.nan), rate_context["default_spread"],
            assump["rf"], assump["erp"], assump["cost_equity"],
            assump["corporate_debt_spread"], assump["cost_debt"],
            assump["wacc_tax_rate"], assump["wacc"], TERMINAL_GROWTH
        ]
    })
    prem["Valor"] = prem["Valor"].map(lambda x: f"{x:.2%}")
    print("\nPREMISSAS NORMALIZADAS")
    display(prem)

    hist_show = mult["history"][[
        "revenue", "ebitda", "net_income", "fcff", "debt", "cash", "net_debt",
        "equity_parent", "roe_parent", "shares", "price_yend", "dividend_ps",
        "pe", "ev_ebitda", "dividend_yield", "payout"
    ]].copy()
    for c in [
        "revenue", "ebitda", "net_income", "fcff", "debt", "cash", "net_debt",
        "equity_parent"
    ]:
        hist_show[c] = hist_show[c] / 1e9
    hist_show = hist_show.rename(columns={
        "revenue": "Receita R$ bi", "ebitda": "EBITDA R$ bi", "net_income": "Lucro R$ bi",
        "fcff": "FCFF R$ bi", "debt": "Dívida R$ bi", "cash": "Caixa R$ bi",
        "net_debt": "Dív. líquida R$ bi", "equity_parent": "PL controladores R$ bi",
        "roe_parent": "ROE", "shares": "Ações", "price_yend": "Preço fim ano",
        "dividend_ps": "Dividendo/ação", "pe": "P/L", "ev_ebitda": "EV/EBITDA",
        "dividend_yield": "DY", "payout": "Payout"
    })
    print("\nHISTÓRICO")
    display(hist_show)

    # Mostra qualquer ajuste de normalização sem apagar os números contábeis originais.
    norm_rows = []
    for year, r in hist_mkt.iterrows():
        ebitda_norm = r.get("ebitda_for_normalization", r.get("ebitda", np.nan))
        ni_norm = r.get("net_income_for_normalization", r.get("net_income", np.nan))
        changed_ebitda = pd.notna(ebitda_norm) and pd.notna(r.get("ebitda", np.nan)) and abs(ebitda_norm - r["ebitda"]) > 1e6
        changed_ni = pd.notna(ni_norm) and pd.notna(r.get("net_income", np.nan)) and abs(ni_norm - r["net_income"]) > 1e6
        if changed_ebitda or changed_ni:
            norm_rows.append({
                "Período": str(year),
                "EBITDA contábil R$ bi": r.get("ebitda", np.nan) / 1e9,
                "EBITDA usado na normalização R$ bi": ebitda_norm / 1e9 if pd.notna(ebitda_norm) else np.nan,
                "Lucro contábil R$ bi": r.get("net_income", np.nan) / 1e9,
                "Lucro usado na normalização R$ bi": ni_norm / 1e9 if pd.notna(ni_norm) else np.nan,
            })
    ttm_ni_norm = ttm.get("net_income_for_normalization", ttm.get("net_income", np.nan))
    if pd.notna(ttm_ni_norm) and pd.notna(ttm.get("net_income", np.nan)) and abs(ttm_ni_norm - ttm["net_income"]) > 1e6:
        norm_rows.append({
            "Período": "TTM",
            "EBITDA contábil R$ bi": ttm.get("ebitda", np.nan) / 1e9,
            "EBITDA usado na normalização R$ bi": ttm.get("ebitda_for_normalization", ttm.get("ebitda", np.nan)) / 1e9,
            "Lucro contábil R$ bi": ttm.get("net_income", np.nan) / 1e9,
            "Lucro usado na normalização R$ bi": ttm_ni_norm / 1e9,
        })
    if norm_rows:
        print("\nAJUSTES EXPLÍCITOS USADOS SOMENTE NA NORMALIZAÇÃO")
        display(pd.DataFrame(norm_rows).set_index("Período"))
        for note in ttm.get("normalization_notes", []):
            print("  •", note)

    # Auditoria específica da nova metodologia de capital de giro.
    nwc_audit = pd.DataFrame({
        "Métrica": [
            "NWC atual CVM",
            "Receita-base TTM",
            "NWC operacional / Receita normalizado",
            "NWC base projetiva normalizada",
            "Delta NWC / Receita histórico (somente diagnóstico)",
        ],
        "Valor": [
            f"R$ {assump['current_nwc']/1e9:,.2f} bi",
            f"R$ {start_revenue/1e9:,.2f} bi",
            f"{assump['nwc_ratio']:.2%}",
            f"R$ {(start_revenue * assump['nwc_ratio'])/1e9:,.2f} bi",
            f"{assump['d_nwc_ratio']:.2%}" if pd.notna(assump['d_nwc_ratio']) else "n/d",
        ],
    }).set_index("Métrica")
    print("\nAUDITORIA DO CAPITAL DE GIRO — METODOLOGIA NWC/RECEITA")
    print("Regra projetiva: NWC_t = Receita_t × NWC/Receita normalizado; Delta NWC_t = NWC_t - NWC_(t-1).")
    display(nwc_audit)

    # Auditoria da composição do CAPEX. Não altera o CAPEX total do FCFF.
    split = assump.get("capex_split")
    print("\nAUDITORIA DA COMPOSIÇÃO DO CAPEX — SUSTAINING x GROWTH")
    if split is not None:
        capex_audit = pd.DataFrame({
            "Métrica": [
                "Ano da referência oficial",
                "CAPEX total oficial",
                "CAPEX sustaining/maintenance oficial",
                "CAPEX growth implícito pela diferença",
                "Participação sustaining",
                "Participação growth",
                "Uso no DCF",
                "Uso na política de dividendos Vale",
            ],
            "Valor": [
                str(split.get("reference_year", "n/d")),
                f"US$ {split['total_usd']/1e9:,.2f} bi",
                f"US$ {split['sustaining_usd']/1e9:,.2f} bi",
                f"US$ {split['growth_usd']/1e9:,.2f} bi",
                f"{split['sustaining_share']:.2%}",
                f"{split['growth_share']:.2%}",
                "CAPEX total continua 100% deduzido do FCFF",
                "Usa a parcela sustaining projetada",
            ],
        }).set_index("Métrica")
        display(capex_audit)
        print("Base:", split.get("basis", "referência oficial da companhia"))
    else:
        print(
            "Split consolidado sustaining/growth não utilizado: não há referência oficial "
            "comparável cadastrada para este ativo. O modelo não inventa um percentual. "
            "CAPEX total continua integralmente no FCFF."
        )

    # Auditoria temporal dos projetos em janelas forward. Nesta versão final,
    # os marcos NÃO alteram quantitativamente o crescimento do valuation.
    timing = assump.get("growth_timing")
    print("\nAUDITORIA DO TIMING DO GROWTH CAPEX — SOMENTE INFORMATIVA / JANELAS FORWARD")
    if isinstance(timing, dict):
        print(timing.get("reason", ""))
        print("Base:", timing.get("basis", "referência oficial da companhia"))
        if assump.get("projection_ref_date") is not None:
            print(f"Data-base TTM: {pd.Timestamp(assump['projection_ref_date']):%d/%m/%Y}")

        prod_rows = []
        for r in timing.get("products", []):
            prod_rows.append({
                "Produto": r["product"],
                "2025 realizado": f"{r['actual_2025']:,.1f} {r['unit']}" if pd.notna(r.get("actual_2025")) else "n/d",
                "2026 guidance (ponto médio)": f"{r['guidance_2026_mid']:,.1f} {r['unit']}",
                "2030 objetivo (ponto médio)": f"{r['target_2030_mid']:,.1f} {r['unit']}",
                "CAGR físico 2026-2030 (diagnóstico)": r["cagr_2026_2030"],
                "Peso receita 2025 (contexto)": r["revenue_weight"],
            })
        if prod_rows:
            prod_df = pd.DataFrame(prod_rows).set_index("Produto")
            display(prod_df.style.format({
                "CAGR físico 2026-2030 (diagnóstico)": "{:.2%}",
                "Peso receita 2025 (contexto)": "{:.2%}",
            }))

        projects = timing.get("projects", [])
        if projects:
            project_rows = []
            for p in projects:
                capex_txt = (
                    f"US$ {float(p['capex_usd'])/1e9:,.2f} bi"
                    if p.get("capex_usd") is not None and np.isfinite(float(p.get("capex_usd")))
                    else "n/d"
                )
                allocs = p.get("forward_allocation", [])
                if allocs:
                    alloc_txt = "; ".join(
                        f"Ano {int(a['forward_year'])} ({a['calendar_overlap']:.0%} do intervalo publicado)"
                        for a in allocs
                    )
                else:
                    alloc_txt = "sem marco forward nas janelas pré-terminais"

                effect_start = p.get("effect_period_start")
                effect_end = p.get("effect_period_end")
                effect_interval = (
                    f"{pd.Timestamp(effect_start):%d/%m/%Y}–{pd.Timestamp(effect_end):%d/%m/%Y}"
                    if effect_start is not None and effect_end is not None
                    and pd.notna(effect_start) and pd.notna(effect_end)
                    else "n/d"
                )

                project_rows.append({
                    "Projeto": p.get("name", "n/d"),
                    "Produto": p.get("product", "n/d"),
                    "Capacidade divulgada": f"{p.get('capacity', 'n/d')} {p.get('unit', '')}".strip(),
                    "Efeito divulgado": p.get("effect_from", "n/d"),
                    "Intervalo preservado": effect_interval,
                    "Localização nas janelas (auditoria)": alloc_txt,
                    "CAPEX projeto": capex_txt,
                    "Leitura": p.get("status", ""),
                })

            project_df = pd.DataFrame(project_rows).set_index("Projeto")
            display(project_df)

        window_rows = timing.get("window_rows", [])
        if window_rows:
            window_df = pd.DataFrame([{
                "Ano proj.": int(r["year"]),
                "Janela forward": r["period_label"],
                "Marcos de projetos na janela (auditoria)": r.get("projects_activating", "—"),
            } for r in window_rows]).set_index("Ano proj.")
            print("\nJANELAS FORWARD — MARCOS OFICIAIS (SEM PESO NUMÉRICO NO DCF)")
            display(window_df)

        base_growth_audit = build_growth_path(assump, SCENARIOS["Base"]).copy()
        base_growth_audit["Fator acumulado legado"] = (1 + base_growth_audit["legacy_growth"]).cumprod()
        base_growth_audit["Fator acumulado aplicado"] = (1 + base_growth_audit["growth"]).cumprod()

        growth_show = base_growth_audit[[
            "year", "period_label", "legacy_growth", "growth",
            "timing_projects", "Fator acumulado legado", "Fator acumulado aplicado"
        ]].rename(columns={
            "year": "Ano proj.",
            "period_label": "Janela forward",
            "legacy_growth": "Crescimento legado",
            "growth": "Crescimento aplicado",
            "timing_projects": "Projetos na janela (auditoria)",
        }).set_index("Ano proj.")

        display(growth_show.style.format({
            "Crescimento legado": "{:.2%}",
            "Crescimento aplicado": "{:.2%}",
            "Fator acumulado legado": "{:.6f}",
            "Fator acumulado aplicado": "{:.6f}",
        }))

        diff = np.max(np.abs(base_growth_audit["growth"].to_numpy() - base_growth_audit["legacy_growth"].to_numpy()))
        if diff > 1e-12:
            raise RuntimeError("Governança do timing violada: auditoria temporal alterou crescimento.")
        print(
            "VALIDAÇÃO FINAL: marcos de projetos NÃO alteram o crescimento do valuation. "
            "Crescimento aplicado = crescimento legado em todas as janelas."
        )
    else:
        print("Não há auditoria temporal oficial cadastrada para este ativo; trajetória legada preservada.")

    print("\nDCF POR CENÁRIO")
    show_scen = scenario_df.copy()
    show_scen["Peso"] = show_scen["Peso"].map(lambda x: f"{x:.0%}")
    show_scen["WACC"] = show_scen["WACC"].map(lambda x: f"{x:.2%}")
    show_scen["g terminal"] = show_scen["g terminal"].map(lambda x: f"{x:.2%}")
    show_scen["ROIC terminal"] = show_scen["ROIC terminal"].map(lambda x: f"{x:.2%}")
    show_scen["Reinvest. terminal"] = show_scen["Reinvest. terminal"].map(lambda x: f"{x:.2%}")
    show_scen["PV terminal / EV"] = show_scen["PV terminal / EV"].map(lambda x: f"{x:.1%}" if pd.notna(x) else "n/d")
    show_scen["Valor justo hoje"] = show_scen["Valor justo hoje"].map(lambda x: f"R$ {x:,.2f}")
    display(show_scen)

    # Auditoria explícita da relação crescimento x reinvestimento no cenário-base.
    base_proj_audit = dcf_results["Base"]["projection"].copy()
    reinvest_cols = [
        "year", "period_label", "legacy_growth", "growth", "timing_projects",
        "revenue", "nopat", "da", "capex",
        "sustaining_capex", "growth_capex", "nwc", "delta_nwc",
        "net_reinvestment", "reinvestment_rate", "implied_roic",
        "growth_reinvestment", "growth_reinvestment_rate", "implied_growth_return", "fcff"
    ]
    reinvest_show = base_proj_audit[reinvest_cols].copy()

    for c in [
        "revenue", "nopat", "da", "capex", "sustaining_capex", "growth_capex",
        "nwc", "delta_nwc", "net_reinvestment", "growth_reinvestment", "fcff"
    ]:
        reinvest_show[c] = reinvest_show[c] / 1e9

    reinvest_show = reinvest_show.rename(columns={
        "year": "Ano",
        "period_label": "Janela forward",
        "legacy_growth": "Crescimento legado",
        "growth": "Crescimento aplicado",
        "timing_projects": "Projetos na janela (auditoria)",
        "revenue": "Receita R$ bi",
        "nopat": "NOPAT R$ bi",
        "da": "D&A R$ bi",
        "capex": "CAPEX total R$ bi",
        "sustaining_capex": "CAPEX sustaining R$ bi",
        "growth_capex": "CAPEX growth R$ bi",
        "nwc": "NWC projetado R$ bi",
        "delta_nwc": "Delta NWC R$ bi",
        "net_reinvestment": "Reinvest. líquido total R$ bi",
        "reinvestment_rate": "Taxa reinvest. total",
        "implied_roic": "Retorno implícito total",
        "growth_reinvestment": "Reinvest. crescimento R$ bi",
        "growth_reinvestment_rate": "Taxa reinvest. crescimento",
        "implied_growth_return": "Retorno growth contemporâneo (legado)",
        "fcff": "FCFF R$ bi",
    }).set_index("Ano")

    print("\nREINVESTIMENTO E COERÊNCIA DO FCFF — CENÁRIO BASE")
    display(reinvest_show.style.format({
        "Crescimento legado": "{:.2%}",
        "Crescimento aplicado": "{:.2%}",
        "Receita R$ bi": "{:,.2f}",
        "NOPAT R$ bi": "{:,.2f}",
        "D&A R$ bi": "{:,.2f}",
        "CAPEX total R$ bi": "{:,.2f}",
        "CAPEX sustaining R$ bi": lambda x: f"{x:,.2f}" if pd.notna(x) else "n/d",
        "CAPEX growth R$ bi": lambda x: f"{x:,.2f}" if pd.notna(x) else "n/d",
        "NWC projetado R$ bi": "{:,.2f}",
        "Delta NWC R$ bi": "{:,.2f}",
        "Reinvest. líquido total R$ bi": "{:,.2f}",
        "Taxa reinvest. total": "{:.2%}",
        "Retorno implícito total": lambda x: f"{x:.2%}" if pd.notna(x) else "n/m",
        "Reinvest. crescimento R$ bi": lambda x: f"{x:,.2f}" if pd.notna(x) else "n/d",
        "Taxa reinvest. crescimento": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
        "Retorno growth contemporâneo (legado)": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
        "FCFF R$ bi": "{:,.2f}",
    }))
    base_terminal = dcf_results["Base"]
    last_base = base_proj_audit.iloc[-1]
    terminal_audit = pd.DataFrame({
        "Métrica": [
            "WACC terminal",
            "g terminal",
            "ROIC terminal adotado",
            "Taxa de reinvestimento terminal = g / ROIC",
            "NOPAT ano 6",
            "Reinvestimento terminal ano 6",
            "FCFF terminal ano 6",
            "Valor terminal no ano 5",
            "PV do valor terminal",
            "PV terminal / Enterprise Value",
            "Retorno implícito total no ano 5",
            "Retorno growth contemporâneo legado no ano 5",
            "ROIC implícito que o método antigo perpetuaria",
        ],
        "Valor": [
            f"{base_terminal['wacc']:.2%}",
            f"{base_terminal['terminal_g']:.2%}",
            f"{base_terminal['terminal_roic']:.2%}",
            f"{base_terminal['terminal_reinvestment_rate']:.2%}",
            f"R$ {base_terminal['terminal_nopat_next']/1e9:,.2f} bi",
            f"R$ {base_terminal['terminal_reinvestment']/1e9:,.2f} bi",
            f"R$ {base_terminal['terminal_fcff']/1e9:,.2f} bi",
            f"R$ {base_terminal['terminal_value']/1e9:,.2f} bi",
            f"R$ {base_terminal['pv_terminal']/1e9:,.2f} bi",
            f"{base_terminal['terminal_share_ev']:.1%}" if pd.notna(base_terminal['terminal_share_ev']) else "n/d",
            f"{last_base['implied_roic']:.2%}" if pd.notna(last_base.get('implied_roic', np.nan)) else "n/m",
            f"{last_base['implied_growth_return']:.2%}" if pd.notna(last_base.get('implied_growth_return', np.nan)) else "n/d",
            f"{base_terminal['legacy_implied_roic']:.2%}" if pd.notna(base_terminal['legacy_implied_roic']) else "n/m",
        ],
    }).set_index("Métrica")
    print("\nFECHAMENTO DO VALOR TERMINAL — CENÁRIO BASE")
    print("Regra: crescimento perpétuo exige reinvestimento; ROIC terminal = WACC, sem excesso de retorno econômico permanente.")
    display(terminal_audit)

    print("\nMÚLTIPLOS NORMALIZADOS")
    print(f"P/L normalizado: {mult['pe_norm']:.2f}x" if pd.notna(mult['pe_norm']) else "P/L normalizado: indisponível")
    print(f"EV/EBITDA normalizado: {mult['ev_ebitda_norm']:.2f}x" if pd.notna(mult['ev_ebitda_norm']) else "EV/EBITDA normalizado: indisponível")
    print(f"Dividend Yield histórico normalizado: {mult['dy_norm']:.2%}" if pd.notna(mult['dy_norm']) else "Dividend Yield histórico normalizado: indisponível")
    print(f"Payout histórico normalizado: {mult['payout_norm']:.2%}" if pd.notna(mult['payout_norm']) else "Payout histórico normalizado: indisponível")
    print(f"EPS projetado 12m: R$ {mult['eps1']:.2f}")
    print(f"Dividendo projetado 12m: R$ {expected_dividend:.2f}/ação" if pd.notna(expected_dividend) else "Dividendo projetado 12m: indisponível")
    print(f"Método do dividendo: {mult['dividend_method']}")
    if mult.get("dy_warning"):
        print("ATENÇÃO DY:", mult["dy_warning"])

    print("\nPREÇO-ALVO POR MÉTODO")
    show_method = method_df.copy()
    show_method["Preço-alvo bruto 12m"] = show_method["Preço-alvo bruto 12m"].map(
        lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d"
    )
    show_method["Valor usado no composto"] = show_method["Valor usado no composto"].map(
        lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d"
    )
    show_method["Peso original"] = show_method["Peso original"].map(
        lambda x: f"{x:.0%}" if pd.notna(x) else "n/d"
    )
    show_method["Peso usado"] = show_method["Peso usado"].map(
        lambda x: f"{x:.0%}" if pd.notna(x) else "n/d"
    )
    show_method["Upside bruto vs atual"] = show_method["Upside bruto vs atual"].map(
        lambda x: f"{x:.1%}" if pd.notna(x) else "n/d"
    )
    display(show_method)

    if floored_methods:
        print(
            "\nATENÇÃO COMPOSTO: os métodos a seguir produziram equity negativo e "
            "mantiveram seu peso com valor econômico mínimo de R$ 0,00 no composto: "
            + ", ".join(floored_methods)
        )

    if missing_methods:
        print(
            "\nATENÇÃO COMPOSTO: método(s) indisponível(is): "
            + ", ".join(missing_methods)
            + ". O composto 50/20/20/10 NÃO foi renormalizado e fica indisponível."
        )

    if profile in {"regulated", "high_roic_growth"}:
        print("\nMÓDULO RESIDUAL INCOME — AUDITORIA LEGADO x COERENTE")
        if ri_result is not None:
            if ri_legacy_result is not None:
                print(
                    f"RI legado — justo hoje: R$ {ri_legacy_result['fair_price_today']:,.2f} | "
                    f"alvo 12m: R$ {ri_legacy_result['target_12m']:,.2f}"
                )
            print(
                f"RI coerente — justo hoje: R$ {ri_result['fair_price_today']:,.2f} | "
                f"alvo 12m: R$ {ri_result['target_12m']:,.2f}"
            )
            print(f"Patrimônio líquido atual usado: R$ {ri_result['book_equity_today']/1e9:,.2f} bi")
            print(f"Ke usado no RI: {ri_result['cost_equity']:.2%}")
            print(f"Payout histórico de referência: {ri_result['historical_payout']:.2%}")
            if ri_result.get("terminal_positive_excess_capitalized", False):
                print(
                    "Terminal positivo capitalizado: "
                    f"ROE terminal={ri_result['terminal_roe']:.2%} | "
                    f"Ke={ri_result['cost_equity']:.2%} | "
                    f"payout terminal={ri_result['terminal_payout']:.2%} | "
                    f"PV RI terminal=R$ {ri_result['pv_terminal_residual_income']/1e9:,.2f} bi"
                )
            else:
                print("Terminal positivo não capitalizado: ROE terminal <= Ke.")

            ri_proj_show = ri_result["projection"].copy().set_index("year")
            display(ri_proj_show.style.format({
                "growth": "{:.2%}",
                "revenue": lambda x: f"R$ {x/1e9:,.2f} bi",
                "book_begin": lambda x: f"R$ {x/1e9:,.2f} bi",
                "net_income": lambda x: f"R$ {x/1e9:,.2f} bi",
                "roe": "{:.2%}",
                "ke": "{:.2%}",
                "historical_payout": "{:.2%}",
                "payout_used": "{:.2%}",
                "retention_used": "{:.2%}",
                "sustainable_growth_historical_payout": "{:.2%}",
                "sustainable_growth_used": "{:.2%}",
                "residual_income": lambda x: f"R$ {x/1e9:,.2f} bi",
                "dividends": lambda x: f"R$ {x/1e9:,.2f} bi",
                "retained_earnings": lambda x: f"R$ {x/1e9:,.2f} bi",
                "book_end": lambda x: f"R$ {x/1e9:,.2f} bi",
                "pv_residual_income": lambda x: f"R$ {x/1e9:,.2f} bi",
            }))

            if ri_method_df is not None:
                print(
                    "\nCOMPOSTO COM RI COERENTE — "
                    + ("ATIVO NO ALVO FINAL" if profile == "regulated" else "SOMENTE DIAGNÓSTICO")
                )
                display(ri_method_df.style.format({
                    "Preço-alvo bruto 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
                    "Peso original": "{:.0%}",
                    "Valor usado no composto": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
                    "Peso usado": lambda x: f"{x:.0%}" if pd.notna(x) else "n/d",
                    "Upside bruto vs atual": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
                }))
        else:
            print("Módulo RI coerente indisponível:", ri_error or "motivo não identificado")

    print("\nGOVERNANÇA DO MODELO")
    print(f"Perfil FCFF: {governance['profile']}")
    print(f"Status: {governance['status']}")
    print(governance["reason"])

    print("\n" + "-" * 90)
    print(f"PREÇO ATUAL                : R$ {price:,.2f}")
    print(f"DCF PONDERADO HOJE         : R$ {weighted_dcf_today:,.2f}")
    if pd.notna(generic_final_target):
        print(f"ALVO COMPOSTO GENÉRICO 12M : R$ {generic_final_target:,.2f}")
        print(f"UPSIDE/DOWNSIDE GENÉRICO   : {generic_upside:.1%}")
    else:
        print("ALVO COMPOSTO GENÉRICO 12M : indisponível — conjunto 50/20/20/10 incompleto")
        print("UPSIDE/DOWNSIDE GENÉRICO   : n/d")

    if pd.notna(validated_final_target):
        print(f"ALVO FINAL VALIDADO 12M    : R$ {validated_final_target:,.2f}")
        print(f"UPSIDE/DOWNSIDE VALIDADO   : {validated_upside:.1%}")
    else:
        print(f"ALVO FINAL VALIDADO 12M    : n/d — {governance['status']}")
        print("UPSIDE/DOWNSIDE VALIDADO   : n/d")

    if pd.notna(validated_final_target_24m):
        print(f"ALVO FINAL VALIDADO 24M    : R$ {validated_final_target_24m:,.2f}")
        print(f"POTENCIAL PREÇO 24M        : {validated_upside_24m:.1%}")
    else:
        print(f"ALVO FINAL VALIDADO 24M    : n/d — {governance['status']}")
        print("POTENCIAL PREÇO 24M        : n/d")

    print(f"DIVIDENDO PROJ. ANO 1      : R$ {expected_dividend:,.2f}/ação")
    print(f"DIVIDENDO PROJ. ANO 2      : R$ {expected_dividend_24m:,.2f}/ação")
    print("-" * 90)

    print("\nSENSIBILIDADE DCF BASE — preço justo hoje | reinvestimento terminal coerente")
    display(sens.applymap(lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "—"))

    # Diagnóstico das contas identificadas no TTM / último histórico
    print("\nDIAGNÓSTICO DE EXTRAÇÃO CVM")

    # Auditoria explícita da base escolhida. CON é sempre preferida; IND somente
    # aparece quando não há linhas utilizáveis da companhia naquela demonstração/período.
    historical_sources = []
    for yr in [AUX_NWC_YEAR] + list(HIST_YEARS):
        src = diagnostics.get(yr, {}).get("Base demonstrações CVM", {})
        if src:
            historical_sources.append({
                "Ano": int(yr),
                "DRE": src.get("DRE", "n/d"),
                "BPA": src.get("BPA", "n/d"),
                "BPP": src.get("BPP", "n/d"),
                "DFC": src.get("DFC", "n/d"),
            })
    if historical_sources:
        print("Base CVM histórica por demonstração — CON preferido; IND somente como fallback:")
        display(pd.DataFrame(historical_sources).set_index("Ano"))

    statement_sources = ttm.get("statement_sources", {})
    if statement_sources:
        print("Base CVM usada nos componentes do TTM:")
        ttm_source_rows = []
        for period_name, src in statement_sources.items():
            row = {"Período": period_name}
            row.update(src)
            ttm_source_rows.append(row)
        display(pd.DataFrame(ttm_source_rows).set_index("Período"))

    dre_components = ttm.get("dre_components", {})
    if dre_components:
        print("DRE TTM — contas/descrições efetivamente usadas por componente:")
        for metric_name, parts in dre_components.items():
            print(f"  {metric_name}:")
            for period_name, label in parts.items():
                print(f"    • {period_name}: {label if label else 'n/d'}")

    if "historical_split_factor" in hist_mkt.columns:
        sf = pd.to_numeric(hist_mkt["historical_split_factor"], errors="coerce")
        events = sf[(sf.notna()) & (abs(sf - 1.0) > 1e-12)]
        if len(events):
            print("Ações históricas — ajuste de base por desdobramento/grupamento do Yahoo:")
            for year, factor in events.items():
                reported = hist_mkt.loc[year].get("shares_reported", np.nan)
                adjusted = hist_mkt.loc[year].get("shares", np.nan)
                print(
                    f"  • {int(year)}: fator acumulado posterior {factor:.6g}x | "
                    f"ações CVM reportadas={reported:,.0f} | ações na base ajustada do preço={adjusted:,.0f}"
                )


    historical_share_gaps = {
        int(year): info.get("Erro ações históricas")
        for year, info in diagnostics.items()
        if info.get("Erro ações históricas")
    }
    if historical_share_gaps:
        print(
            "Ações históricas: há ano(s) sem composição de capital utilizável. "
            "Esses anos ficam NaN apenas nos múltiplos/payout históricos; não há "
            "forward-fill/backfill e o DCF atual continua usando ações TTM validadas."
        )
        for year, err in historical_share_gaps.items():
            print(f"  • {year}: {err}")
    print(f"Delta NWC histórico de 2021 usa {AUX_NWC_YEAR} como ano auxiliar; {AUX_NWC_YEAR} não entra no histórico exibido.")
    print("Projeção futura de Delta NWC usa níveis de NWC/Receita normalizados; a métrica histórica Delta NWC/Receita fica somente como diagnóstico.")
    if assump.get("capex_split") is not None:
        print("CAPEX: split oficial sustaining/growth é usado para diagnóstico econômico e política de dividendos da Vale; CAPEX total continua 100% deduzido no FCFF.")
    else:
        print("CAPEX: sem split oficial consolidado sustaining/growth; nenhum percentual foi inventado e CAPEX total permanece 100% no FCFF.")
    capex_profile = asset.get("capex_profile", "standard")
    if capex_profile == "concession":
        print(
            "Perfil CAPEX: concessionário/regulado — além de imobilizado/intangível, "
            "o modelo inclui somente desembolsos explicitamente identificados na DFC "
            "como ativo contratual, infraestrutura ou ativo de concessão."
        )
    else:
        print("Perfil CAPEX: padrão — imobilizado/intangível conforme linhas explícitas da DFC.")
    timing = assump.get("growth_timing")
    if isinstance(timing, dict) and timing.get("audit_only", False):
        print(
            "Growth CAPEX/timing: marcos oficiais são exibidos somente como auditoria em janelas forward; "
            "não alteram numericamente o crescimento. Sem guidance anual quantitativo completo, a trajetória legada é preservada."
        )
    else:
        print("Growth CAPEX/timing: nenhuma trajetória quantitativa oficial de timing foi aplicada; crescimento legado preservado.")
    if ttm is not None:
        da_comp = ttm.get("da_components", {})
        cap_comp = ttm.get("capex_components", {})

        if da_comp:
            vals = list(da_comp.values())
            keys = list(da_comp.keys())
            if len(vals) == 3 and all(np.isfinite(v) for v in vals):
                print(
                    f"D&A TTM: {keys[0]} R$ {vals[0]/1e9:,.2f} bi + "
                    f"{keys[1]} R$ {vals[1]/1e9:,.2f} bi - "
                    f"{keys[2]} R$ {vals[2]/1e9:,.2f} bi = "
                    f"R$ {ttm['da']/1e9:,.2f} bi"
                )
        print("D&A — linhas usadas no ITR atual:")
        for item in ttm.get("da_labels", [])[:12]:
            print("  •", item)

        if cap_comp:
            vals = list(cap_comp.values())
            keys = list(cap_comp.keys())
            if len(vals) == 3 and all(np.isfinite(v) for v in vals):
                print(
                    f"CAPEX TTM: {keys[0]} R$ {vals[0]/1e9:,.2f} bi + "
                    f"{keys[1]} R$ {vals[1]/1e9:,.2f} bi - "
                    f"{keys[2]} R$ {vals[2]/1e9:,.2f} bi = "
                    f"R$ {ttm['capex']/1e9:,.2f} bi"
                )

        print("CAPEX — linhas usadas por componente do TTM:")
        cap_label_components = ttm.get("capex_component_labels", {})
        if cap_label_components:
            for component, items in cap_label_components.items():
                print(f"  {component}:")
                if items:
                    for item in items[:16]:
                        print("    •", item)
                else:
                    print("    • nenhuma linha elegível encontrada")
        else:
            for item in ttm.get("capex_labels", [])[:16]:
                print("  •", item)

        print("Dívida atual — contas agregadas usadas:")
        for item in ttm.get("debt_labels", [])[:12]:
            print("  •", item)

        print("Patrimônio líquido atual — contas usadas:")
        for item in ttm.get("equity_labels", [])[:8]:
            print("  •", item)
        if pd.notna(ttm.get("equity_parent", np.nan)):
            print(
                f"PL atribuível aos controladores usado no RI: "
                f"R$ {ttm['equity_parent']/1e9:,.2f} bi"
            )

    # Gráfico 1: preços-alvo. Para perfis ainda não validados setorialmente,
    # o composto continua visível, mas é rotulado explicitamente como genérico.
    plot_vals = {"Preço atual": price, **available}
    if ri_legacy_result is not None and pd.notna(ri_legacy_result.get("target_12m", np.nan)):
        plot_vals["RI legado 12m"] = ri_legacy_result["target_12m"]
    if ri_result is not None and pd.notna(ri_result.get("target_12m", np.nan)):
        plot_vals["RI coerente 12m"] = ri_result["target_12m"]
    if pd.notna(generic_final_target):
        plot_vals["Alvo composto FCFF"] = generic_final_target
    if pd.notna(validated_final_target):
        plot_vals["Alvo final validado"] = validated_final_target
    plt.figure(figsize=(10, 5))
    plt.bar(plot_vals.keys(), plot_vals.values())
    plt.axhline(price, linestyle="--", linewidth=1)
    plt.title(f"{symbol} — Preço atual x Valuation 12 meses")
    plt.ylabel("R$ por ação")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.show()

    # Gráfico 2: projeção FCFF base
    bp = dcf_results["Base"]["projection"]
    plt.figure(figsize=(9, 5))
    plt.plot(bp["year"], bp["fcff"] / 1e9, marker="o")
    plt.title(f"{symbol} — FCFF projetado (cenário base)")
    plt.xlabel("Ano projetado")
    plt.ylabel("R$ bilhões")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.show()

    return {
        "symbol": symbol,
        "price": price,
        "hist": hist_mkt,
        "ttm": ttm,
        "assumptions": assump,
        "dcf": dcf_results,
        "scenario_table": scenario_df,
        "multiples": mult,
        "method_table": method_df,
        "ri_method_table": ri_method_df,
        "residual_income": ri_result,
        "residual_income_legacy": ri_legacy_result,
        "ri_error": ri_error,
        "ri_target_12m": ri_final_target,
        "ri_target_24m": ri_final_target_24m,
        "ri_legacy_target_12m": ri_legacy_final_target,
        "ri_upside": ri_upside,
        "ri_upside_24m": ri_upside_24m,
        "ri_missing_methods": ri_missing_methods,
        "ri_missing_methods_24m": ri_missing_methods_24m,
        "ri_floored_methods": ri_floored_methods,
        "floored_methods": floored_methods,
        "missing_methods": missing_methods,
        "missing_methods_24m": missing_methods_24m,
        "weighted_dcf_today": weighted_dcf_today,
        "target_12m": generic_final_target,
        "target_24m": generic_final_target_24m,
        "upside": generic_upside,
        "upside_24m": generic_upside_24m,
        "generic_target_12m": generic_final_target,
        "generic_target_24m": generic_final_target_24m,
        "generic_upside": generic_upside,
        "generic_upside_24m": generic_upside_24m,
        "validated_target_12m": validated_final_target,
        "validated_target_24m": validated_final_target_24m,
        "validated_upside": validated_upside,
        "validated_upside_24m": validated_upside_24m,
        "model_governance": governance,
        "expected_dividend": expected_dividend,
        "expected_dividend_24m": expected_dividend_24m,
        "sensitivity": sens,
        "diagnostics": diagnostics,
        "market_cap_detail": market_cap_detail,
    }


# ================================================================
# 9A) AUDITORIA DE DIVERGÊNCIA ENTRE MÉTODOS — SOMENTE DIAGNÓSTICA
# ================================================================
#
# Esta camada NÃO altera:
# - nenhuma premissa de valuation;
# - nenhum peso 50/20/20/10;
# - nenhum DCF, Residual Income, múltiplo ou Dividend Yield;
# - nenhum alvo final já calculado.
#
# Objetivo:
# medir se o método principal de 50% está ou não alinhado com os três
# métodos secundários do MESMO motor. Isso permite distinguir:
#   (a) consenso de downside/upside entre metodologias;
#   (b) divergência interna, quando o método principal puxa o composto
#       em direção diferente da maioria dos métodos secundários.
#
# O "Impacto do gap no composto" é puramente aritmético:
#     peso_principal × (valor_usado_principal - mediana_valores_usados_secundários)
# Portanto, não cria um novo preço-alvo e não redistribui pesos.


def _method_value_from_table(method_table, method_name, column="Preço-alvo bruto 12m"):
    """Lê um valor numérico de uma tabela de métodos sem alterar o dado original."""
    if method_table is None or not isinstance(method_table, pd.DataFrame) or method_table.empty:
        return np.nan
    if method_name not in method_table.index or column not in method_table.columns:
        return np.nan
    value = pd.to_numeric(
        pd.Series([method_table.loc[method_name, column]]),
        errors="coerce"
    ).iloc[0]
    return float(value) if pd.notna(value) and np.isfinite(value) else np.nan


def build_method_disagreement_audit(results, equity_results, assets):
    """
    Consolida a divergência entre o método principal de 50% e os três secundários.

    Regras:
    - FCFF genérico/custom/cyclical:
        principal = DCF 12m
        secundários = P/L, EV/EBITDA, Dividend Yield
    - FCFF regulated:
        principal = Residual Income coerente 12m do composto setorial validado
        secundários = P/L, EV/EBITDA, Dividend Yield
    - FCFF high_roic_growth:
        principal = DCF 12m; RI coerente permanece diagnóstico
        secundários = P/L, EV/EBITDA, Dividend Yield
    - Equity/patrimonial:
        principal = Residual Income 12m
        secundários = P/L, P/VP, Dividend Yield

    Nenhum método é recalculado aqui. A função apenas lê as tabelas que já foram
    produzidas pelos motores e calcula estatísticas descritivas de divergência.
    """
    rows = []

    for symbol, asset in assets.items():
        engine = None
        result = None
        method_table = None
        primary_name = None
        secondary_names = None
        family = None
        final_target = np.nan
        final_upside = np.nan

        if symbol in results:
            engine = "FCFF"
            result = results[symbol]
            gov = result.get("model_governance", {}) or {}
            profile = gov.get("profile", asset.get("fcff_profile", "generic"))
            family = "RI coerente setorial + múltiplos" if profile == "regulated" else "FCFF + múltiplos"

            if profile == "regulated":
                method_table = result.get("ri_method_table")
                primary_name = "Residual Income coerente 12m"
                secondary_names = ["P/L 12m", "EV/EBITDA 12m", "Dividend Yield 12m"]
            else:
                method_table = result.get("method_table")
                primary_name = "DCF 12m"
                secondary_names = ["P/L 12m", "EV/EBITDA 12m", "Dividend Yield 12m"]

            final_target = result.get("validated_target_12m", np.nan)
            final_upside = result.get("validated_upside", np.nan)

        elif symbol in equity_results:
            engine = "Equity / patrimonial"
            result = equity_results[symbol]
            family = result.get("model_profile", asset.get("financial_profile", "equity"))
            method_table = result.get("method_table")
            primary_name = "Residual Income 12m"
            secondary_names = [
                "P/L 12m",
                "P/VP 12m",
                "Dividend Yield 12m",
            ]
            final_target = result.get("validated_target_12m", result.get("target_12m", np.nan))
            final_upside = result.get("validated_upside", result.get("upside", np.nan))

        else:
            continue

        price = float(result.get("price", np.nan))
        primary_raw = _method_value_from_table(
            method_table, primary_name, "Preço-alvo bruto 12m"
        )
        primary_used = _method_value_from_table(
            method_table, primary_name, "Valor usado no composto"
        )
        primary_weight = _method_value_from_table(
            method_table, primary_name, "Peso original"
        )

        secondary_raw = {
            name: _method_value_from_table(
                method_table, name, "Preço-alvo bruto 12m"
            )
            for name in secondary_names
        }
        secondary_used = {
            name: _method_value_from_table(
                method_table, name, "Valor usado no composto"
            )
            for name in secondary_names
        }

        valid_secondary_raw = [
            float(v)
            for v in secondary_raw.values()
            if pd.notna(v) and np.isfinite(v)
        ]
        valid_secondary_used = [
            float(v)
            for v in secondary_used.values()
            if pd.notna(v) and np.isfinite(v)
        ]

        secondary_median = (
            float(np.median(valid_secondary_raw))
            if valid_secondary_raw else np.nan
        )
        secondary_used_median = (
            float(np.median(valid_secondary_used))
            if valid_secondary_used else np.nan
        )

        primary_vs_secondary_gap = (
            primary_raw - secondary_median
            if np.isfinite(primary_raw) and np.isfinite(secondary_median)
            else np.nan
        )
        primary_vs_secondary_gap_pct = (
            primary_raw / secondary_median - 1.0
            if np.isfinite(primary_raw)
            and np.isfinite(secondary_median)
            and secondary_median > 0
            else np.nan
        )

        secondary_dispersion = (
            (max(valid_secondary_raw) - min(valid_secondary_raw)) / abs(secondary_median)
            if len(valid_secondary_raw) >= 2
            and np.isfinite(secondary_median)
            and abs(secondary_median) > 1e-12
            else np.nan
        )

        impact_gap_on_composite = (
            primary_weight * (primary_used - secondary_used_median)
            if np.isfinite(primary_weight)
            and np.isfinite(primary_used)
            and np.isfinite(secondary_used_median)
            else np.nan
        )

        primary_upside = (
            primary_raw / price - 1.0
            if np.isfinite(primary_raw) and np.isfinite(price) and price > 0
            else np.nan
        )
        secondary_median_upside = (
            secondary_median / price - 1.0
            if np.isfinite(secondary_median) and np.isfinite(price) and price > 0
            else np.nan
        )

        secondary_at_or_above_price = (
            sum(v >= price for v in valid_secondary_raw)
            if np.isfinite(price) else 0
        )
        secondary_below_price = (
            sum(v < price for v in valid_secondary_raw)
            if np.isfinite(price) else 0
        )

        # Leitura somente direcional. Não existe limiar arbitrário de 10%, 20% etc.
        if (
            not np.isfinite(primary_raw)
            or not np.isfinite(price)
            or len(valid_secondary_raw) != 3
        ):
            diagnostic_read = "INCOMPLETO — faltam métodos para a leitura 4/4"
        elif primary_raw < price and secondary_at_or_above_price >= 2:
            diagnostic_read = (
                "DIVERGÊNCIA — principal abaixo do preço; "
                "maioria dos secundários >= preço"
            )
        elif primary_raw >= price and secondary_below_price >= 2:
            diagnostic_read = (
                "DIVERGÊNCIA INVERSA — principal >= preço; "
                "maioria dos secundários abaixo"
            )
        elif primary_raw < price and secondary_below_price == 3:
            diagnostic_read = "CONSENSO DE DOWNSIDE — 4/4 métodos abaixo do preço"
        elif primary_raw >= price and secondary_at_or_above_price == 3:
            diagnostic_read = "CONSENSO DE UPSIDE — 4/4 métodos >= preço"
        else:
            diagnostic_read = "MISTO — sem consenso direcional entre os 4 métodos"

        middle_method = secondary_names[1]

        rows.append({
            "Ativo": symbol,
            "Motor": engine,
            "Família": family,
            "Preço atual": price,
            "Método principal": primary_name,
            "Principal 12m": primary_raw,
            "Upside principal": primary_upside,
            "P/L 12m": secondary_raw.get("P/L 12m", np.nan),
            "Método secundário 2": middle_method,
            "Secundário 2 12m": secondary_raw.get(middle_method, np.nan),
            "Dividend Yield 12m": secondary_raw.get("Dividend Yield 12m", np.nan),
            "Mediana secundários 12m": secondary_median,
            "Upside mediana secundários": secondary_median_upside,
            "Gap principal - mediana R$": primary_vs_secondary_gap,
            "Gap principal vs mediana %": primary_vs_secondary_gap_pct,
            "Dispersão dos secundários %": secondary_dispersion,
            "Peso do principal": primary_weight,
            "Impacto do gap no composto R$": impact_gap_on_composite,
            "Secundários >= preço": int(secondary_at_or_above_price),
            "Secundários < preço": int(secondary_below_price),
            "Alvo final atual 12m": (
                float(final_target)
                if pd.notna(final_target) and np.isfinite(final_target)
                else np.nan
            ),
            "Upside final atual": (
                float(final_upside)
                if pd.notna(final_upside) and np.isfinite(final_upside)
                else np.nan
            ),
            "Leitura diagnóstica": diagnostic_read,
        })

    if not rows:
        return pd.DataFrame()

    audit = pd.DataFrame(rows).set_index("Ativo")
    order = [s for s in assets.keys() if s in audit.index]
    return audit.loc[order]


# ================================================================
# 9B) AUDITORIA ECONÔMICA PROFUNDA DO RESIDUAL INCOME — DIAGNÓSTICA
# ================================================================
#
# Esta camada NÃO altera:
# - o Residual Income já calculado;
# - Ke, WACC, crescimento, payout, margem ou patrimônio líquido;
# - os pesos 50/20/20/10;
# - qualquer preço-alvo, composto, piso ou regra terminal.
#
# Objetivo:
# decompor economicamente o RI existente para responder, com os próprios
# números do modelo, por que o método principal fica muito abaixo (ou acima)
# dos métodos secundários.
#
# Testes exclusivamente diagnósticos:
#   1) ROE x Ke: excesso de retorno contábil atual e projetado;
#   2) crescimento usado x g sustentável implícito = ROE x retenção;
#   3) identidade do RI: valor hoje = PL atual + PV dos lucros residuais.
#
# Nenhum limiar percentual de aprovação/reprovação é criado aqui.


def build_residual_income_economic_audit(
    results,
    equity_results,
    assets,
    method_disagreement_audit=None,
):
    """
    Consolida a anatomia econômica do Residual Income já calculado.

    Retorna:
      summary: uma linha por ativo com RI disponível;
      trajectory: anos 1-5 do RI por ativo.

    A função não recalcula o RI e não cria preço-alvo alternativo. Ela apenas
    decompõe os objetos `residual_income` devolvidos pelos motores existentes.
    """
    summary_rows = []
    trajectory_rows = []

    for symbol, asset in assets.items():
        if symbol in results:
            result = results[symbol]
            ri = result.get("residual_income")
            if not isinstance(ri, dict):
                continue
            motor = "RI setorial"
            profile = result.get("model_governance", {}).get(
                "profile", asset.get("fcff_profile", "n/d")
            )
            count = pd.to_numeric(
                pd.Series([result.get("assumptions", {}).get("shares", np.nan)]),
                errors="coerce",
            ).iloc[0]
        elif symbol in equity_results:
            result = equity_results[symbol]
            ri = result.get("residual_income")
            if not isinstance(ri, dict):
                continue
            motor = "RI equity/patrimonial"
            profile = result.get("model_profile", asset.get("financial_profile", "n/d"))
            count = pd.to_numeric(
                pd.Series([
                    result.get("assumptions", {}).get("security_count", np.nan)
                ]),
                errors="coerce",
            ).iloc[0]
        else:
            continue

        projection = ri.get("projection")
        if projection is None or not isinstance(projection, pd.DataFrame) or projection.empty:
            continue

        price = pd.to_numeric(pd.Series([result.get("price", np.nan)]), errors="coerce").iloc[0]
        ttm = result.get("ttm", {}) or {}
        book0 = pd.to_numeric(
            pd.Series([ri.get("book_equity_today", np.nan)]), errors="coerce"
        ).iloc[0]
        ni0 = pd.to_numeric(
            pd.Series([ttm.get("net_income", np.nan)]), errors="coerce"
        ).iloc[0]
        ke = pd.to_numeric(
            pd.Series([ri.get("cost_equity", np.nan)]), errors="coerce"
        ).iloc[0]
        payout = pd.to_numeric(
            pd.Series([ri.get("historical_payout", ri.get("payout_norm", np.nan))]),
            errors="coerce"
        ).iloc[0]
        retention = 1.0 - payout if pd.notna(payout) and np.isfinite(payout) else np.nan

        current_roe = (
            float(ni0 / book0)
            if pd.notna(ni0) and pd.notna(book0)
            and np.isfinite(ni0) and np.isfinite(book0) and book0 != 0
            else np.nan
        )
        current_spread = (
            float(current_roe - ke)
            if np.isfinite(current_roe) and pd.notna(ke) and np.isfinite(ke)
            else np.nan
        )
        sustainable_growth_current = (
            float(current_roe * retention)
            if np.isfinite(current_roe) and np.isfinite(retention)
            else np.nan
        )

        p = projection.copy()
        p["year"] = pd.to_numeric(p.get("year"), errors="coerce")
        p = p[p["year"].notna()].copy()
        p["year"] = p["year"].astype(int)
        p5 = p[p["year"] <= PROJECTION_YEARS].copy()

        if "growth_net_income" in p5.columns:
            growth_col = "growth_net_income"
        elif "growth" in p5.columns:
            growth_col = "growth"
        else:
            growth_col = None

        first = p5.iloc[0] if not p5.empty else pd.Series(dtype=float)
        fifth_rows = p5[p5["year"] == PROJECTION_YEARS]
        fifth = (
            fifth_rows.iloc[0]
            if not fifth_rows.empty
            else (p5.iloc[-1] if not p5.empty else pd.Series(dtype=float))
        )

        g1 = (
            float(pd.to_numeric(pd.Series([first.get(growth_col, np.nan)]), errors="coerce").iloc[0])
            if growth_col is not None and not first.empty
            else np.nan
        )
        roe1 = pd.to_numeric(pd.Series([first.get("roe", np.nan)]), errors="coerce").iloc[0]
        roe5 = pd.to_numeric(pd.Series([fifth.get("roe", np.nan)]), errors="coerce").iloc[0]
        g5 = (
            float(pd.to_numeric(pd.Series([fifth.get(growth_col, np.nan)]), errors="coerce").iloc[0])
            if growth_col is not None and not fifth.empty
            else np.nan
        )

        payout1 = pd.to_numeric(
            pd.Series([first.get("payout_used", payout)]), errors="coerce"
        ).iloc[0]
        payout5 = pd.to_numeric(
            pd.Series([fifth.get("payout_used", payout)]), errors="coerce"
        ).iloc[0]
        retention1 = 1.0 - payout1 if pd.notna(payout1) and np.isfinite(payout1) else np.nan
        retention5 = 1.0 - payout5 if pd.notna(payout5) and np.isfinite(payout5) else np.nan
        sustainable_growth1 = (
            float(roe1 * retention1)
            if pd.notna(roe1) and np.isfinite(roe1) and np.isfinite(retention1)
            else np.nan
        )
        sustainable_growth5 = (
            float(roe5 * retention5)
            if pd.notna(roe5) and np.isfinite(roe5) and np.isfinite(retention5)
            else np.nan
        )

        book_ps = (
            float(book0 / count)
            if pd.notna(book0) and np.isfinite(book0)
            and pd.notna(count) and np.isfinite(count) and count > 0
            else np.nan
        )
        pv_ri = pd.to_numeric(
            pd.Series([ri.get("pv_residual_income", np.nan)]), errors="coerce"
        ).iloc[0]
        pv_ri_ps = (
            float(pv_ri / count)
            if pd.notna(pv_ri) and np.isfinite(pv_ri)
            and pd.notna(count) and np.isfinite(count) and count > 0
            else np.nan
        )
        ri_fair_today = pd.to_numeric(
            pd.Series([ri.get("fair_price_today", np.nan)]), errors="coerce"
        ).iloc[0]
        ri_target_12m = pd.to_numeric(
            pd.Series([ri.get("target_12m", np.nan)]), errors="coerce"
        ).iloc[0]
        identity_sum = (
            float(book_ps + pv_ri_ps)
            if np.isfinite(book_ps) and np.isfinite(pv_ri_ps)
            else np.nan
        )
        identity_error = (
            float(identity_sum - ri_fair_today)
            if np.isfinite(identity_sum) and pd.notna(ri_fair_today) and np.isfinite(ri_fair_today)
            else np.nan
        )
        pv_ri_share = (
            float(pv_ri_ps / ri_fair_today)
            if np.isfinite(pv_ri_ps) and pd.notna(ri_fair_today)
            and np.isfinite(ri_fair_today) and abs(ri_fair_today) > 1e-12
            else np.nan
        )

        first5_ri = pd.to_numeric(
            p5.get("residual_income", pd.Series(dtype=float)), errors="coerce"
        ).replace([np.inf, -np.inf], np.nan)
        positive_ri_years = int((first5_ri > 0).sum()) if not first5_ri.empty else 0
        negative_ri_years = int((first5_ri < 0).sum()) if not first5_ri.empty else 0

        if np.isfinite(current_roe) and pd.notna(ke) and np.isfinite(ke):
            if current_roe < ke and negative_ri_years == len(first5_ri.dropna()) and len(first5_ri.dropna()) > 0:
                economic_read = "ROE atual < Ke; RI negativo em todos os anos 1-5"
            elif current_roe >= ke and pd.notna(roe5) and np.isfinite(roe5) and roe5 < ke:
                economic_read = "ROE atual >= Ke, mas cai abaixo do Ke até o ano 5"
            elif current_roe >= ke and pd.notna(roe5) and np.isfinite(roe5) and roe5 >= ke:
                economic_read = "ROE atual e do ano 5 >= Ke; excesso de retorno permanece"
            elif current_roe < ke:
                economic_read = "ROE atual < Ke; trajetória do RI é mista"
            else:
                economic_read = "ROE x Ke disponível; trajetória incompleta para leitura"
        else:
            economic_read = "ROE atual ou Ke indisponível para leitura"

        disagreement_read = "n/d"
        if (
            method_disagreement_audit is not None
            and isinstance(method_disagreement_audit, pd.DataFrame)
            and symbol in method_disagreement_audit.index
        ):
            disagreement_read = str(
                method_disagreement_audit.loc[symbol, "Leitura diagnóstica"]
            )

        summary_rows.append({
            "Ativo": symbol,
            "Motor RI": motor,
            "Perfil": profile,
            "Preço atual": float(price) if pd.notna(price) and np.isfinite(price) else np.nan,
            "PL atual R$ bi": float(book0 / 1e9) if pd.notna(book0) and np.isfinite(book0) else np.nan,
            "Lucro TTM R$ bi": float(ni0 / 1e9) if pd.notna(ni0) and np.isfinite(ni0) else np.nan,
            "ROE atual": current_roe,
            "ROE histórico mediano": ri.get("historical_roe_median", np.nan),
            "Ke": float(ke) if pd.notna(ke) and np.isfinite(ke) else np.nan,
            "Spread ROE atual - Ke": current_spread,
            "Payout": float(payout) if pd.notna(payout) and np.isfinite(payout) else np.nan,
            "Retenção": retention,
            "g sustentável atual = ROE×retenção": sustainable_growth_current,
            "g usado ano 1": g1,
            "g1 - g sustentável atual": (
                float(g1 - sustainable_growth_current)
                if np.isfinite(g1) and np.isfinite(sustainable_growth_current)
                else np.nan
            ),
            "ROE ano 1": float(roe1) if pd.notna(roe1) and np.isfinite(roe1) else np.nan,
            "Spread ROE1 - Ke": (
                float(roe1 - ke)
                if pd.notna(roe1) and np.isfinite(roe1) and pd.notna(ke) and np.isfinite(ke)
                else np.nan
            ),
            "g sustentável ano 1": sustainable_growth1,
            "ROE ano 5": float(roe5) if pd.notna(roe5) and np.isfinite(roe5) else np.nan,
            "Spread ROE5 - Ke": (
                float(roe5 - ke)
                if pd.notna(roe5) and np.isfinite(roe5) and pd.notna(ke) and np.isfinite(ke)
                else np.nan
            ),
            "g usado ano 5": g5,
            "g sustentável ano 5": sustainable_growth5,
            "g5 - g sustentável ano 5": (
                float(g5 - sustainable_growth5)
                if np.isfinite(g5) and np.isfinite(sustainable_growth5)
                else np.nan
            ),
            "PL por ativo": book_ps,
            "PV RI por ativo": pv_ri_ps,
            "PL + PV RI por ativo": identity_sum,
            "RI justo hoje": float(ri_fair_today) if pd.notna(ri_fair_today) and np.isfinite(ri_fair_today) else np.nan,
            "Erro identidade RI R$": identity_error,
            "PV RI / valor RI hoje": pv_ri_share,
            "RI alvo 12m": float(ri_target_12m) if pd.notna(ri_target_12m) and np.isfinite(ri_target_12m) else np.nan,
            "RI positivos anos 1-5": positive_ri_years,
            "RI negativos anos 1-5": negative_ri_years,
            "Anos RI explícitos": ri.get("explicit_ri_years", np.nan),
            "Extensão além do ano 5": ri.get("extended_positive_ri_years", np.nan),
            "Ano de convergência RI=0": ri.get("convergence_year", np.nan),
            "Fechamento terminal especial": bool(ri.get("terminal_closure_applied", False)),
            "ROE terminal mecânico": ri.get("terminal_mechanical_roe", np.nan),
            "Leitura ROE x Ke": economic_read,
            "Leitura divergência métodos": disagreement_read,
        })

        for _, row in p5.iterrows():
            year = int(row["year"])
            roe = pd.to_numeric(pd.Series([row.get("roe", np.nan)]), errors="coerce").iloc[0]
            row_ke = pd.to_numeric(pd.Series([row.get("ke", ke)]), errors="coerce").iloc[0]
            row_payout = pd.to_numeric(
                pd.Series([row.get("payout_used", payout)]), errors="coerce"
            ).iloc[0]
            row_retention = (
                1.0 - row_payout
                if pd.notna(row_payout) and np.isfinite(row_payout)
                else np.nan
            )
            row_growth = (
                pd.to_numeric(pd.Series([row.get(growth_col, np.nan)]), errors="coerce").iloc[0]
                if growth_col is not None else np.nan
            )
            row_sustainable = (
                float(roe * row_retention)
                if pd.notna(roe) and np.isfinite(roe) and np.isfinite(row_retention)
                else np.nan
            )

            trajectory_rows.append({
                "Ativo": symbol,
                "Ano": year,
                "Motor RI": motor,
                "Perfil": profile,
                "g usado": float(row_growth) if pd.notna(row_growth) and np.isfinite(row_growth) else np.nan,
                "ROE": float(roe) if pd.notna(roe) and np.isfinite(roe) else np.nan,
                "Ke": float(row_ke) if pd.notna(row_ke) and np.isfinite(row_ke) else np.nan,
                "Spread ROE - Ke": (
                    float(roe - row_ke)
                    if pd.notna(roe) and np.isfinite(roe)
                    and pd.notna(row_ke) and np.isfinite(row_ke)
                    else np.nan
                ),
                "Payout usado": float(row_payout) if pd.notna(row_payout) and np.isfinite(row_payout) else np.nan,
                "Retenção": row_retention,
                "g sustentável = ROE×retenção": row_sustainable,
                "g usado - g sustentável": (
                    float(row_growth - row_sustainable)
                    if pd.notna(row_growth) and np.isfinite(row_growth)
                    and np.isfinite(row_sustainable)
                    else np.nan
                ),
                "PL inicial R$ bi": (
                    float(row.get("book_begin", np.nan) / 1e9)
                    if pd.notna(row.get("book_begin", np.nan))
                    and np.isfinite(row.get("book_begin", np.nan)) else np.nan
                ),
                "Lucro R$ bi": (
                    float(row.get("net_income", np.nan) / 1e9)
                    if pd.notna(row.get("net_income", np.nan))
                    and np.isfinite(row.get("net_income", np.nan)) else np.nan
                ),
                "RI R$ bi": (
                    float(row.get("residual_income", np.nan) / 1e9)
                    if pd.notna(row.get("residual_income", np.nan))
                    and np.isfinite(row.get("residual_income", np.nan)) else np.nan
                ),
                "PV RI R$ bi": (
                    float(row.get("pv_residual_income", np.nan) / 1e9)
                    if pd.notna(row.get("pv_residual_income", np.nan))
                    and np.isfinite(row.get("pv_residual_income", np.nan)) else np.nan
                ),
                "PL final R$ bi": (
                    float(row.get("book_end", np.nan) / 1e9)
                    if pd.notna(row.get("book_end", np.nan))
                    and np.isfinite(row.get("book_end", np.nan)) else np.nan
                ),
            })

    if summary_rows:
        summary = pd.DataFrame(summary_rows).set_index("Ativo")
        order = [s for s in assets.keys() if s in summary.index]
        summary = summary.loc[order]
    else:
        summary = pd.DataFrame()

    if trajectory_rows:
        trajectory = pd.DataFrame(trajectory_rows)
        trajectory["_asset_order"] = trajectory["Ativo"].map(
            {s: i for i, s in enumerate(assets.keys())}
        )
        trajectory = (
            trajectory.sort_values(["_asset_order", "Ano"])
            .drop(columns="_asset_order")
            .set_index(["Ativo", "Ano"])
        )
    else:
        trajectory = pd.DataFrame()

    return summary, trajectory



# ================================================================
# 11C) RI ECONOMICAMENTE COERENTE — MOTOR ATIVADO + AUDITORIA LEGADA
# ================================================================
#
# Esta camada NÃO apaga nem modifica o RI legado. Ela calcula, em paralelo,
# um candidato economicamente coerente para resolver exatamente os dois pontos
# diagnosticados pela auditoria anterior:
#
#   1) quando o crescimento projetado cai abaixo do crescimento sustentável
#      ROE × retenção histórica, o payout pode SUBIR para devolver o capital que
#      já não precisa ser retido. O payout nunca é reduzido abaixo do histórico
#      para "fabricar" crescimento;
#
#   2) se, ao fim do horizonte explícito, o ROE produzido pelo próprio modelo
#      ainda superar o Ke, não há salto artificial para ROE=Ke no ano seguinte.
#      O excesso de retorno do primeiro ano terminal é capitalizado com o mesmo
#      g terminal e o ROE que resulta mecanicamente das projeções já existentes.
#
# Nenhum horizonte de fade, ROE-alvo, RAB, prêmio setorial ou calibração ao
# preço de mercado é introduzido. O RI legado continua sendo o alvo oficial
# nesta versão; o candidato abaixo é mostrado lado a lado para decisão final.
# ================================================================

def _coherent_payout_for_growth(roe, growth, historical_payout):
    """
    Ajuste estritamente unilateral do payout.

    Se 0 <= g < ROE × retenção histórica, a companhia está retendo mais capital
    do que o crescimento usado no próprio valuation requer. Nesse caso:
        retenção requerida = g / ROE
        payout coerente    = 1 - retenção requerida

    O payout coerente nunca fica ABAIXO do payout histórico. Portanto esta regra
    não injeta retenção adicional nem cria crescimento que o modelo não possuía.
    Para crescimento negativo, ROE não positivo ou dados inválidos, preserva o
    payout histórico.
    """
    payout_hist = float(historical_payout)
    if not np.isfinite(payout_hist) or payout_hist < 0:
        raise ValueError("RI coerente indisponível: payout histórico inválido.")

    if not (np.isfinite(roe) and np.isfinite(growth)):
        return payout_hist, 1.0 - payout_hist, False

    if growth < 0 or roe <= 0:
        return payout_hist, 1.0 - payout_hist, False

    historical_retention = 1.0 - payout_hist
    if historical_retention <= 0:
        return payout_hist, historical_retention, False

    required_retention = float(growth) / float(roe)

    # A correção é somente de excesso de retenção. Se o crescimento exigiria
    # mais retenção do que a histórica, a regra legada é preservada.
    if required_retention < historical_retention:
        coherent_retention = max(float(required_retention), 0.0)
        coherent_payout = 1.0 - coherent_retention
        return coherent_payout, coherent_retention, True

    return payout_hist, historical_retention, False


def residual_income_value_coherent_candidate(
    hist_mkt,
    ttm,
    assump,
    start_revenue,
    payout_norm,
    profile_label="regulated",
):
    """
    RI coerente para regulated/high_roic_growth.

    Preserva:
      - patrimônio líquido CVM;
      - Ke;
      - trajetória de crescimento já existente;
      - margem líquida normalizada;
      - horizonte explícito de 5 anos;
      - nenhuma calibração ao preço de mercado.

    Corrige somente:
      - excesso de retenção incompatível com o crescimento usado;
      - fechamento terminal abrupto quando ainda existe ROE > Ke.

    O terminal positivo usa o primeiro ano terminal produzido pela própria
    trajetória do modelo. Se ROE_terminal > Ke:
        RI_6 = Lucro_6 - Ke × PL_inicial_6
        TV_RI_5 = RI_6 / (Ke - g)
    com retenção terminal = g / ROE_terminal, que mantém crescimento, ROE,
    retenção e payout internamente coerentes. Se ROE_terminal <= Ke, RI
    terminal permanece zero, preservando a postura conservadora anterior.
    """
    if ttm is None:
        raise ValueError("RI coerente indisponível: TTM ausente.")

    book0 = float(ttm.get("equity_parent", np.nan))
    ke = float(assump.get("cost_equity", np.nan))
    shares = float(assump.get("shares", np.nan))
    net_margin = float(assump.get("net_margin", np.nan))

    if not (np.isfinite(book0) and book0 > 0):
        raise ValueError("RI coerente indisponível: PL controladores inválido.")
    if not (np.isfinite(ke) and ke > 0):
        raise ValueError("RI coerente indisponível: Ke inválido.")
    if not (np.isfinite(shares) and shares > 0):
        raise ValueError("RI coerente indisponível: ações inválidas.")
    if not np.isfinite(net_margin):
        raise ValueError("RI coerente indisponível: margem líquida inválida.")
    if pd.isna(payout_norm) or not np.isfinite(payout_norm) or payout_norm < 0:
        raise ValueError("RI coerente indisponível: payout histórico inválido.")

    growth_audit = build_growth_path(assump, SCENARIOS["Base"])
    growth_path = growth_audit["growth"].astype(float).tolist()
    terminal_growth = float(
        TERMINAL_GROWTH + SCENARIOS["Base"].get("terminal_g_shift", 0.0)
    )

    if not np.isfinite(terminal_growth) or terminal_growth < 0 or terminal_growth >= ke:
        raise ValueError(
            "RI coerente indisponível: terminal exige 0 <= g < Ke. "
            f"g={terminal_growth:.2%}; Ke={ke:.2%}."
        )

    revenue = float(start_revenue)
    book_begin = book0
    rows = []
    pv_ri_explicit = 0.0

    for year in range(1, PROJECTION_YEARS + 1):
        growth = float(growth_path[year - 1])
        revenue_out = revenue * (1.0 + growth)
        net_income = revenue_out * net_margin
        roe = net_income / book_begin if abs(book_begin) > 1e-12 else np.nan

        payout_used, retention_used, payout_adjusted = _coherent_payout_for_growth(
            roe=roe,
            growth=growth,
            historical_payout=payout_norm,
        )

        dividends = max(net_income, 0.0) * payout_used
        retained = net_income - dividends
        residual_income = net_income - ke * book_begin
        pv_ri = residual_income / ((1.0 + ke) ** year)
        book_end = book_begin + retained

        if not np.isfinite(book_end) or book_end <= 0:
            raise ValueError(
                f"RI coerente indisponível: PL projetado não positivo no ano {year}."
            )

        sustainable_growth_hist = (
            roe * (1.0 - float(payout_norm))
            if np.isfinite(roe) else np.nan
        )
        sustainable_growth_used = (
            roe * retention_used if np.isfinite(roe) else np.nan
        )

        rows.append({
            "year": year,
            "growth": growth,
            "revenue": revenue_out,
            "book_begin": book_begin,
            "net_income": net_income,
            "roe": roe,
            "ke": ke,
            "historical_payout": float(payout_norm),
            "payout_used": payout_used,
            "retention_used": retention_used,
            "payout_adjusted_up": bool(payout_adjusted),
            "sustainable_growth_historical_payout": sustainable_growth_hist,
            "sustainable_growth_used": sustainable_growth_used,
            "residual_income": residual_income,
            "dividends": dividends,
            "retained_earnings": retained,
            "book_end": book_end,
            "pv_residual_income": pv_ri,
        })

        pv_ri_explicit += pv_ri
        revenue = revenue_out
        book_begin = book_end

    # Primeiro ano terminal produzido pela MESMA trajetória de lucro.
    revenue6 = revenue * (1.0 + terminal_growth)
    net_income6 = revenue6 * net_margin
    terminal_book_begin = book_begin
    terminal_roe = (
        net_income6 / terminal_book_begin
        if abs(terminal_book_begin) > 1e-12 else np.nan
    )
    terminal_residual_income = (
        net_income6 - ke * terminal_book_begin
        if np.isfinite(terminal_roe) else np.nan
    )

    terminal_value_ri_year5 = 0.0
    pv_terminal_ri = 0.0
    terminal_retention = np.nan
    terminal_payout = np.nan
    terminal_positive_excess_capitalized = False

    if (
        np.isfinite(terminal_roe)
        and terminal_roe > ke
        and np.isfinite(terminal_residual_income)
        and terminal_residual_income > 0
    ):
        terminal_retention = terminal_growth / terminal_roe
        if not (0 <= terminal_retention < 1):
            raise ValueError(
                "RI coerente indisponível: retenção terminal fora de [0,1)."
            )
        terminal_payout = 1.0 - terminal_retention
        terminal_value_ri_year5 = terminal_residual_income / (ke - terminal_growth)
        pv_terminal_ri = terminal_value_ri_year5 / ((1.0 + ke) ** PROJECTION_YEARS)
        terminal_positive_excess_capitalized = True
    else:
        # Se o próprio horizonte explícito já levou ROE <= Ke, não perpetuamos
        # lucro residual negativo. O fechamento conservador RI_terminal=0 é mantido.
        terminal_value_ri_year5 = 0.0
        pv_terminal_ri = 0.0

    pv_ri_total = pv_ri_explicit + pv_terminal_ri
    equity_value_today = book0 + pv_ri_total
    fair_price_today = equity_value_today / shares

    projection = pd.DataFrame(rows)
    first_dividend_ps = (
        float(projection.iloc[0]["dividends"]) / shares
        if not projection.empty else np.nan
    )
    target_12m = (
        fair_price_today * (1.0 + ke) - first_dividend_ps
        if np.isfinite(first_dividend_ps)
        else np.nan
    )

    roe_hist = pd.Series(dtype=float)
    if hist_mkt is not None and not hist_mkt.empty and "roe_parent" in hist_mkt.columns:
        roe_hist = (
            pd.to_numeric(hist_mkt["roe_parent"], errors="coerce")
            .replace([np.inf, -np.inf], np.nan)
            .dropna()
        )

    return {
        "profile_label": profile_label,
        "book_equity_today": book0,
        "cost_equity": ke,
        "historical_payout": float(payout_norm),
        "projection": projection,
        "pv_residual_income_explicit": float(pv_ri_explicit),
        "pv_terminal_residual_income": float(pv_terminal_ri),
        "pv_residual_income": float(pv_ri_total),
        "equity_value_today": float(equity_value_today),
        "fair_price_today": float(fair_price_today),
        "target_12m": (
            float(target_12m)
            if pd.notna(target_12m) and np.isfinite(target_12m)
            else np.nan
        ),
        "first_year_dividend_ps": float(first_dividend_ps),
        "historical_roe_median": safe_median(roe_hist.tail(4), np.nan),
        "terminal_growth": terminal_growth,
        "terminal_book_begin": float(terminal_book_begin),
        "terminal_net_income": float(net_income6),
        "terminal_roe": float(terminal_roe) if np.isfinite(terminal_roe) else np.nan,
        "terminal_residual_income": (
            float(terminal_residual_income)
            if np.isfinite(terminal_residual_income) else np.nan
        ),
        "terminal_retention": (
            float(terminal_retention) if np.isfinite(terminal_retention) else np.nan
        ),
        "terminal_payout": (
            float(terminal_payout) if np.isfinite(terminal_payout) else np.nan
        ),
        "terminal_value_ri_year5": float(terminal_value_ri_year5),
        "terminal_positive_excess_capitalized": bool(
            terminal_positive_excess_capitalized
        ),
        "rule": (
            "Regra ativa: payout só sobe quando g < ROE×retenção histórica; "
            "se ROE terminal > Ke, capitaliza RI positivo com g terminal e "
            "ROE produzido mecanicamente pelo próprio modelo."
        ),
    }


def financial_residual_income_value_coherent_candidate(
    hist_mkt,
    ttm,
    assump,
    payout_norm,
    profile_label,
):
    """
    RI coerente para bancos/seguradoras/B3/holding/Unit.

    O lucro líquido continua usando exatamente a trajetória histórica -> g terminal
    já existente. A única correção explícita é a coerência de retenção/payout:
    payout pode subir quando o crescimento usado não exige toda a retenção histórica,
    mas nunca é reduzido abaixo do histórico para sustentar crescimento.

    No terminal, quando o ROE produzido pelo próprio modelo ainda é > Ke, o RI
    positivo é capitalizado sem salto de ROE para Ke e sem prazo arbitrário de fade.
    """
    book0 = float(assump["equity_parent"])
    ni0 = float(assump["net_income_ttm"])
    ke = float(assump["cost_equity"])
    security_count = float(assump["security_count"])

    if not (np.isfinite(book0) and book0 > 0):
        raise ValueError("RI financeiro coerente indisponível: PL atual inválido.")
    if not (np.isfinite(ni0) and ni0 > 0):
        raise ValueError("RI financeiro coerente indisponível: lucro TTM não positivo.")
    if not (np.isfinite(ke) and ke > 0):
        raise ValueError("RI financeiro coerente indisponível: Ke inválido.")
    if not (np.isfinite(security_count) and security_count > 0):
        raise ValueError("RI financeiro coerente indisponível: quantidade inválida.")
    if pd.isna(payout_norm) or not np.isfinite(payout_norm) or payout_norm < 0:
        raise ValueError("RI financeiro coerente indisponível: payout inválido.")

    growth_audit = build_growth_path(assump, SCENARIOS["Base"])
    growth_path = growth_audit["growth"].astype(float).tolist()
    terminal_growth = float(
        TERMINAL_GROWTH + SCENARIOS["Base"].get("terminal_g_shift", 0.0)
    )

    if not np.isfinite(terminal_growth) or terminal_growth < 0 or terminal_growth >= ke:
        raise ValueError(
            "RI financeiro coerente indisponível: terminal exige 0 <= g < Ke. "
            f"g={terminal_growth:.2%}; Ke={ke:.2%}."
        )

    ni_begin = ni0
    book_begin = book0
    rows = []
    pv_ri_explicit = 0.0

    for year in range(1, PROJECTION_YEARS + 1):
        growth = float(growth_path[year - 1])
        net_income = ni_begin * (1.0 + growth)
        roe = net_income / book_begin if abs(book_begin) > 1e-12 else np.nan

        payout_used, retention_used, payout_adjusted = _coherent_payout_for_growth(
            roe=roe,
            growth=growth,
            historical_payout=payout_norm,
        )

        dividends = max(net_income, 0.0) * payout_used
        retained = net_income - dividends
        residual_income = net_income - ke * book_begin
        pv_ri = residual_income / ((1.0 + ke) ** year)
        book_end = book_begin + retained

        if not np.isfinite(book_end) or book_end <= 0:
            raise ValueError(
                f"RI financeiro coerente indisponível: PL não positivo no ano {year}."
            )

        sustainable_growth_hist = (
            roe * (1.0 - float(payout_norm))
            if np.isfinite(roe) else np.nan
        )
        sustainable_growth_used = (
            roe * retention_used if np.isfinite(roe) else np.nan
        )

        rows.append({
            "year": year,
            "growth_net_income": growth,
            "net_income": net_income,
            "book_begin": book_begin,
            "roe": roe,
            "ke": ke,
            "historical_payout": float(payout_norm),
            "payout_used": payout_used,
            "retention_used": retention_used,
            "payout_adjusted_up": bool(payout_adjusted),
            "sustainable_growth_historical_payout": sustainable_growth_hist,
            "sustainable_growth_used": sustainable_growth_used,
            "residual_income": residual_income,
            "dividends": dividends,
            "retained_earnings": retained,
            "book_end": book_end,
            "pv_residual_income": pv_ri,
        })

        pv_ri_explicit += pv_ri
        ni_begin = net_income
        book_begin = book_end

    # Primeiro ano terminal usa o mesmo g terminal aplicado ao lucro já projetado.
    terminal_book_begin = book_begin
    terminal_net_income = ni_begin * (1.0 + terminal_growth)
    terminal_roe = (
        terminal_net_income / terminal_book_begin
        if abs(terminal_book_begin) > 1e-12 else np.nan
    )
    terminal_residual_income = (
        terminal_net_income - ke * terminal_book_begin
        if np.isfinite(terminal_roe) else np.nan
    )

    terminal_value_ri_year5 = 0.0
    pv_terminal_ri = 0.0
    terminal_retention = np.nan
    terminal_payout = np.nan
    terminal_positive_excess_capitalized = False

    if (
        np.isfinite(terminal_roe)
        and terminal_roe > ke
        and np.isfinite(terminal_residual_income)
        and terminal_residual_income > 0
    ):
        terminal_retention = terminal_growth / terminal_roe
        if not (0 <= terminal_retention < 1):
            raise ValueError(
                "RI financeiro coerente indisponível: retenção terminal fora de [0,1)."
            )
        terminal_payout = 1.0 - terminal_retention
        terminal_value_ri_year5 = terminal_residual_income / (ke - terminal_growth)
        pv_terminal_ri = terminal_value_ri_year5 / ((1.0 + ke) ** PROJECTION_YEARS)
        terminal_positive_excess_capitalized = True

    pv_ri_total = pv_ri_explicit + pv_terminal_ri
    equity_value_today = book0 + pv_ri_total
    fair_price_today = equity_value_today / security_count

    projection = pd.DataFrame(rows)
    first_dividend_ps = (
        float(projection.iloc[0]["dividends"]) / security_count
        if not projection.empty else np.nan
    )
    target_12m = (
        fair_price_today * (1.0 + ke) - first_dividend_ps
        if np.isfinite(first_dividend_ps)
        else np.nan
    )

    roe_hist = pd.to_numeric(
        hist_mkt.get("roe_parent", pd.Series(dtype=float)),
        errors="coerce",
    ).replace([np.inf, -np.inf], np.nan).dropna()

    return {
        "profile_label": profile_label,
        "book_equity_today": book0,
        "cost_equity": ke,
        "historical_payout": float(payout_norm),
        "projection": projection,
        "pv_residual_income_explicit": float(pv_ri_explicit),
        "pv_terminal_residual_income": float(pv_terminal_ri),
        "pv_residual_income": float(pv_ri_total),
        "equity_value_today": float(equity_value_today),
        "fair_price_today": float(fair_price_today),
        "target_12m": (
            float(target_12m)
            if pd.notna(target_12m) and np.isfinite(target_12m)
            else np.nan
        ),
        "first_year_dividend_ps": float(first_dividend_ps),
        "historical_roe_median": safe_median(roe_hist.tail(4), np.nan),
        "terminal_growth": terminal_growth,
        "terminal_book_begin": float(terminal_book_begin),
        "terminal_net_income": float(terminal_net_income),
        "terminal_roe": float(terminal_roe) if np.isfinite(terminal_roe) else np.nan,
        "terminal_residual_income": (
            float(terminal_residual_income)
            if np.isfinite(terminal_residual_income) else np.nan
        ),
        "terminal_retention": (
            float(terminal_retention) if np.isfinite(terminal_retention) else np.nan
        ),
        "terminal_payout": (
            float(terminal_payout) if np.isfinite(terminal_payout) else np.nan
        ),
        "terminal_value_ri_year5": float(terminal_value_ri_year5),
        "terminal_positive_excess_capitalized": bool(
            terminal_positive_excess_capitalized
        ),
        "rule": (
            "Regra ativa: payout só sobe quando g < ROE×retenção histórica; "
            "se ROE terminal > Ke, capitaliza RI positivo com g terminal e "
            "ROE produzido mecanicamente pelo próprio modelo."
        ),
    }


def build_ri_coherent_candidate_comparison(
    results,
    equity_results,
    assets,
    method_disagreement_audit=None,
):
    """
    Compara o RI coerente ativado com o RI legado preservado para auditoria.

    IMPORTANTE:
      - os três métodos secundários permanecem exatamente os já calculados;
      - regulated e módulos equity usam RI coerente no slot principal de 50%;
      - high_roic_growth usa DCF/FCFF como principal e mantém RI como diagnóstico;
      - holding permanece proxy não validado como NAV/SOTP.
    """
    rows = []
    candidate_objects = {}

    for symbol, asset in assets.items():
        if symbol in results:
            r = results[symbol]
            legacy_ri = r.get("residual_income_legacy", r.get("residual_income"))
            profile = str(
                r.get("model_governance", {}).get(
                    "profile", asset.get("fcff_profile", "")
                )
            ).strip().lower()

            if not isinstance(legacy_ri, dict) or profile not in {
                "regulated", "high_roic_growth"
            }:
                continue

            try:
                candidate = residual_income_value_coherent_candidate(
                    hist_mkt=r["hist"],
                    ttm=r["ttm"],
                    assump=r["assumptions"],
                    start_revenue=float(r["ttm"]["revenue"]),
                    payout_norm=float(r["multiples"]["payout_norm"]),
                    profile_label=profile,
                )
                candidate_error = ""
            except Exception as exc:
                candidate = None
                candidate_error = f"{type(exc).__name__}: {exc}"

            secondary_values = {
                "P/L 12m": r["multiples"].get("pe_target", np.nan),
                "EV/EBITDA 12m": r["multiples"].get("ev_ebitda_target", np.nan),
                "Dividend Yield 12m": r["multiples"].get("dy_target", np.nan),
            }
            legacy_final = r.get("ri_legacy_target_12m", np.nan)
            price = r.get("price", np.nan)
            motor = "RI setorial"

        elif symbol in equity_results:
            r = equity_results[symbol]
            legacy_ri = r.get("residual_income_legacy", r.get("residual_income"))
            profile = str(
                r.get("model_profile", asset.get("financial_profile", ""))
            ).strip().lower()

            if not isinstance(legacy_ri, dict):
                continue

            try:
                # O payout é o mesmo já usado pelo motor legado.
                payout_norm = float(legacy_ri.get("payout_norm", np.nan))
                if not np.isfinite(payout_norm):
                    payout_norm = float(
                        normalize_equity_assumptions(
                            hist_mkt=r["hist"],
                            ttm=r["ttm"],
                            rf=r["assumptions"]["rf"],
                            beta=r["assumptions"]["beta"],
                            price=r["price"],
                            asset=asset,
                        )["payout_norm"]
                    )

                candidate = financial_residual_income_value_coherent_candidate(
                    hist_mkt=r["hist"],
                    ttm=r["ttm"],
                    assump=r["assumptions"],
                    payout_norm=payout_norm,
                    profile_label=profile,
                )
                candidate_error = ""
            except Exception as exc:
                candidate = None
                candidate_error = f"{type(exc).__name__}: {exc}"

            secondary_values = {
                "P/L 12m": r.get("pe_target", np.nan),
                "P/VP 12m": r.get("pb_target", np.nan),
                "Dividend Yield 12m": r.get("dy_target", np.nan),
            }
            legacy_final = r.get("legacy_target_12m", np.nan)
            price = r.get("price", np.nan)
            motor = "RI equity/patrimonial"

        else:
            continue

        legacy_target = pd.to_numeric(
            pd.Series([legacy_ri.get("target_12m", np.nan)]),
            errors="coerce",
        ).iloc[0]
        legacy_fair_today = pd.to_numeric(
            pd.Series([legacy_ri.get("fair_price_today", np.nan)]),
            errors="coerce",
        ).iloc[0]

        valid_secondary = [
            float(v)
            for v in secondary_values.values()
            if pd.notna(v) and np.isfinite(v)
        ]
        secondary_median = (
            float(np.median(valid_secondary))
            if len(valid_secondary) == 3 else np.nan
        )

        candidate_target = (
            float(candidate["target_12m"])
            if isinstance(candidate, dict)
            and pd.notna(candidate.get("target_12m", np.nan))
            and np.isfinite(candidate.get("target_12m", np.nan))
            else np.nan
        )
        candidate_fair_today = (
            float(candidate["fair_price_today"])
            if isinstance(candidate, dict)
            and pd.notna(candidate.get("fair_price_today", np.nan))
            and np.isfinite(candidate.get("fair_price_today", np.nan))
            else np.nan
        )

        # Mesmo composto 50/20/20/10; só o principal é substituído no candidato.
        candidate_composite = np.nan
        if np.isfinite(candidate_target) and len(valid_secondary) == 3:
            if motor == "RI setorial":
                candidate_composite = (
                    max(candidate_target, 0.0) * METHOD_WEIGHTS["DCF 12m"]
                    + max(float(secondary_values["P/L 12m"]), 0.0)
                    * METHOD_WEIGHTS["P/L 12m"]
                    + max(float(secondary_values["EV/EBITDA 12m"]), 0.0)
                    * METHOD_WEIGHTS["EV/EBITDA 12m"]
                    + max(float(secondary_values["Dividend Yield 12m"]), 0.0)
                    * METHOD_WEIGHTS["Dividend Yield 12m"]
                )
            else:
                candidate_composite = (
                    max(candidate_target, 0.0)
                    * EQUITY_METHOD_WEIGHTS["Residual Income 12m"]
                    + max(float(secondary_values["P/L 12m"]), 0.0)
                    * EQUITY_METHOD_WEIGHTS["P/L 12m"]
                    + max(float(secondary_values["P/VP 12m"]), 0.0)
                    * EQUITY_METHOD_WEIGHTS["P/VP 12m"]
                    + max(float(secondary_values["Dividend Yield 12m"]), 0.0)
                    * EQUITY_METHOD_WEIGHTS["Dividend Yield 12m"]
                )

        legacy_projection = legacy_ri.get("projection", pd.DataFrame())
        legacy_payout1 = np.nan
        legacy_payout5 = np.nan
        if isinstance(legacy_projection, pd.DataFrame) and not legacy_projection.empty:
            legacy_payout1 = pd.to_numeric(
                pd.Series([
                    legacy_projection.iloc[0].get(
                        "payout_used", legacy_ri.get("payout_norm", np.nan)
                    )
                ]),
                errors="coerce",
            ).iloc[0]
            row5 = legacy_projection[
                pd.to_numeric(legacy_projection.get("year"), errors="coerce")
                == PROJECTION_YEARS
            ]
            if not row5.empty:
                legacy_payout5 = pd.to_numeric(
                    pd.Series([
                        row5.iloc[0].get(
                            "payout_used", legacy_ri.get("payout_norm", np.nan)
                        )
                    ]),
                    errors="coerce",
                ).iloc[0]

        candidate_payout1 = np.nan
        candidate_payout5 = np.nan
        payout_adjusted_years = 0
        if isinstance(candidate, dict):
            cp = candidate.get("projection", pd.DataFrame())
            if isinstance(cp, pd.DataFrame) and not cp.empty:
                candidate_payout1 = float(cp.iloc[0]["payout_used"])
                row5 = cp[pd.to_numeric(cp["year"], errors="coerce") == PROJECTION_YEARS]
                if not row5.empty:
                    candidate_payout5 = float(row5.iloc[0]["payout_used"])
                payout_adjusted_years = int(
                    pd.Series(cp["payout_adjusted_up"]).fillna(False).astype(bool).sum()
                )

        disagreement_read = "n/d"
        if (
            method_disagreement_audit is not None
            and isinstance(method_disagreement_audit, pd.DataFrame)
            and symbol in method_disagreement_audit.index
        ):
            disagreement_read = str(
                method_disagreement_audit.loc[symbol, "Leitura diagnóstica"]
            )

        candidate_objects[symbol] = candidate

        candidate_count = (
            r["assumptions"].get("shares", np.nan)
            if motor == "RI setorial"
            else r["assumptions"].get("security_count", np.nan)
        )
        candidate_identity_error = np.nan
        if (
            isinstance(candidate, dict)
            and pd.notna(candidate_count)
            and np.isfinite(candidate_count)
            and candidate_count > 0
            and np.isfinite(candidate_fair_today)
        ):
            candidate_identity_value = (
                candidate.get("book_equity_today", np.nan)
                + candidate.get("pv_residual_income", np.nan)
            ) / candidate_count
            if np.isfinite(candidate_identity_value):
                candidate_identity_error = (
                    candidate_identity_value - candidate_fair_today
                )

        rows.append({
            "Ativo": symbol,
            "Motor": motor,
            "Perfil": profile,
            "Preço atual": float(price) if pd.notna(price) and np.isfinite(price) else np.nan,
            "RI legado justo hoje": (
                float(legacy_fair_today)
                if pd.notna(legacy_fair_today) and np.isfinite(legacy_fair_today)
                else np.nan
            ),
            "RI coerente justo hoje": candidate_fair_today,
            "RI legado 12m": (
                float(legacy_target)
                if pd.notna(legacy_target) and np.isfinite(legacy_target)
                else np.nan
            ),
            "RI coerente 12m": candidate_target,
            "Variação RI coerente vs legado": (
                candidate_target / legacy_target - 1.0
                if np.isfinite(candidate_target)
                and pd.notna(legacy_target)
                and np.isfinite(legacy_target)
                and abs(float(legacy_target)) > 1e-12
                else np.nan
            ),
            "Mediana secundários 12m": secondary_median,
            "Gap legado vs mediana": (
                legacy_target / secondary_median - 1.0
                if pd.notna(legacy_target) and np.isfinite(legacy_target)
                and np.isfinite(secondary_median) and secondary_median != 0
                else np.nan
            ),
            "Gap coerente vs mediana": (
                candidate_target / secondary_median - 1.0
                if np.isfinite(candidate_target)
                and np.isfinite(secondary_median) and secondary_median != 0
                else np.nan
            ),
            "Alvo final oficial atual 12m": (
                float(legacy_final)
                if pd.notna(legacy_final) and np.isfinite(legacy_final)
                else np.nan
            ),
            "Composto candidato coerente 12m": (
                float(candidate_composite)
                if pd.notna(candidate_composite) and np.isfinite(candidate_composite)
                else np.nan
            ),
            "Alvo final oficial ativado 12m": (
                float(r.get("validated_target_12m", r.get("target_12m", np.nan)))
                if pd.notna(r.get("validated_target_12m", r.get("target_12m", np.nan)))
                and np.isfinite(r.get("validated_target_12m", r.get("target_12m", np.nan)))
                else np.nan
            ),
            "Upside oficial ativado": (
                r.get("validated_target_12m", r.get("target_12m", np.nan)) / price - 1.0
                if pd.notna(r.get("validated_target_12m", r.get("target_12m", np.nan)))
                and np.isfinite(r.get("validated_target_12m", r.get("target_12m", np.nan)))
                and pd.notna(price) and np.isfinite(price) and price > 0
                else np.nan
            ),
            "Upside composto candidato": (
                candidate_composite / price - 1.0
                if pd.notna(candidate_composite) and np.isfinite(candidate_composite)
                and pd.notna(price) and np.isfinite(price) and price > 0
                else np.nan
            ),
            "Payout legado ano 1": (
                float(legacy_payout1)
                if pd.notna(legacy_payout1) and np.isfinite(legacy_payout1)
                else np.nan
            ),
            "Payout coerente ano 1": candidate_payout1,
            "Payout legado ano 5": (
                float(legacy_payout5)
                if pd.notna(legacy_payout5) and np.isfinite(legacy_payout5)
                else np.nan
            ),
            "Payout coerente ano 5": candidate_payout5,
            "Anos com payout elevado": payout_adjusted_years,
            "ROE terminal coerente": (
                candidate.get("terminal_roe", np.nan)
                if isinstance(candidate, dict) else np.nan
            ),
            "Ke": (
                candidate.get("cost_equity", np.nan)
                if isinstance(candidate, dict) else legacy_ri.get("cost_equity", np.nan)
            ),
            "PV RI terminal por ativo": (
                candidate.get("pv_terminal_residual_income", np.nan)
                / candidate_count
                if isinstance(candidate, dict)
                and pd.notna(candidate.get("pv_terminal_residual_income", np.nan))
                and np.isfinite(candidate.get("pv_terminal_residual_income", np.nan))
                and pd.notna(candidate_count)
                and np.isfinite(candidate_count)
                and candidate_count > 0
                else np.nan
            ),
            "Erro identidade candidato R$": candidate_identity_error,
            "Excesso terminal capitalizado": (
                bool(candidate.get("terminal_positive_excess_capitalized", False))
                if isinstance(candidate, dict) else False
            ),
            "Erro candidato": candidate_error,
            "Leitura divergência anterior": disagreement_read,
        })

    if rows:
        comparison = pd.DataFrame(rows).set_index("Ativo")
        order = [s for s in assets.keys() if s in comparison.index]
        comparison = comparison.loc[order]
    else:
        comparison = pd.DataFrame()

    return comparison, candidate_objects


# ================================================================
# 10) EXECUÇÃO — UNIVERSO DO RADAR W1
# ================================================================

print("Verificando acesso aos arquivos oficiais da CVM...")
check_cvm_connectivity()
print("CVM acessível. Iniciando o valuation.\n")

print("Consultando Selic Meta e a curva soberana de longo prazo...")
RATE_CONTEXT = build_rate_context()
print(f"Selic Meta atual: {RATE_CONTEXT['selic_spot']:.2%}")
if pd.notna(RATE_CONTEXT.get("sovereign_curve_rate", np.nan)):
    print(
        f"ETTJ soberana ANBIMA ({RATE_CONTEXT['curve_vertex']} d.u.): "
        f"{RATE_CONTEXT['sovereign_curve_rate']:.2%}"
    )
    print(f"Default spread Brasil retirado: {RATE_CONTEXT['default_spread']:.2%}")
print(f"Rf nominal BRL usada no valuation: {RATE_CONTEXT['valuation_rf']:.2%}")
print(
    f"ERP total Brasil no CAPM: {RATE_CONTEXT['erp']:.2%} "
    f"(referência {RATE_CONTEXT['erp_asof']})"
)
print(f"Spread corporativo assumido no Kd: {DEBT_SPREAD:.2%}")
print(
    "Fórmula do Kd: Rf default-free + default spread Brasil + spread corporativo"
    "\n"
)

RESULTS = {}
EQUITY_RESULTS = {}
SKIPPED_ASSETS = {}
FAILED_ASSETS = {}
EQUITY_FAILED_ASSETS = {}

SUPPORTED_EQUITY_MODELS = {
    "financial", "financial_infrastructure", "holding", "financial_unit"
}

for SYMBOL, ASSET in ASSETS.items():
    model_type = ASSET.get("valuation_model", "fcff")

    if model_type == "fcff":
        try:
            RESULTS[SYMBOL] = run_asset(SYMBOL, ASSET, RATE_CONTEXT)
        except CVMConnectivityError:
            # A CVM é fonte contábil obrigatória. Se a conexão cair no meio da rodada,
            # interrompe imediatamente em vez de repetir a mesma falha nos ativos seguintes.
            raise
        except Exception as e:
            FAILED_ASSETS[SYMBOL] = {
                "Ativo": ASSET.get("name", SYMBOL),
                "Tipo do erro": type(e).__name__,
                "Mensagem": str(e),
            }
            print(f"\nERRO FCFF EM {SYMBOL}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc(limit=5)
        continue

    if model_type in SUPPORTED_EQUITY_MODELS:
        try:
            EQUITY_RESULTS[SYMBOL] = run_equity_asset(
                SYMBOL, ASSET, RATE_CONTEXT
            )
        except CVMConnectivityError:
            # Mesma regra do FCFF: indisponibilidade da fonte oficial interrompe a rodada.
            raise
        except Exception as e:
            EQUITY_FAILED_ASSETS[SYMBOL] = {
                "Ativo": ASSET.get("name", SYMBOL),
                "Modelo": model_type,
                "Tipo do erro": type(e).__name__,
                "Mensagem": str(e),
            }
            print(f"\nERRO EQUITY EM {SYMBOL}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc(limit=5)
        continue

    reason = ASSET.get(
        "model_reason", "Nenhum motor compatível cadastrado para este ativo."
    )
    SKIPPED_ASSETS[SYMBOL] = {
        "Ativo": ASSET.get("name", SYMBOL),
        "Modelo necessário": model_type,
        "Motivo": reason,
    }
    print("\n" + "=" * 90)
    print(f"{SYMBOL} — {ASSET.get('name', SYMBOL)} | SEM MOTOR COMPATÍVEL")
    print("=" * 90)
    print(reason)

# ================================================================
# 11) COMPARATIVO FINAL
# ================================================================

summary_rows = []
for symbol, r in RESULTS.items():
    summary_rows.append({
        "Ativo": symbol,
        "Preço atual": r["price"],
        "DCF justo hoje": r["weighted_dcf_today"],
        "RI justo hoje": (
            r.get("residual_income", {}).get("fair_price_today", np.nan)
            if isinstance(r.get("residual_income"), dict) else np.nan
        ),
        "Alvo genérico 12m": r.get("generic_target_12m", r["target_12m"]),
        "Upside genérico": r.get("generic_upside", r["upside"]),
        "Alvo RI setorial 12m": r.get("ri_target_12m", np.nan),
        "Alvo final validado 12m": r.get("validated_target_12m", np.nan),
        "Upside validado": r.get("validated_upside", np.nan),
        "Status do modelo": r.get("model_governance", {}).get("status", "n/d"),
        "Métodos ausentes": ", ".join(r.get("missing_methods", [])) or "—",
        "Dividendo proj. 12m": r["expected_dividend"],
        "Rf longo prazo": r["assumptions"]["rf"],
        "ERP Brasil": r["assumptions"]["erp"],
        "Ke": r["assumptions"]["cost_equity"],
        "Kd": r["assumptions"]["cost_debt"],
        "WACC": r["assumptions"]["wacc"],
        "Beta": r["assumptions"]["beta"],
        "Piso zero no composto": ", ".join(r.get("floored_methods", [])) or "—",
        "Piso zero no RI": ", ".join(r.get("ri_floored_methods", [])) or "—",
    })

if summary_rows:
    SUMMARY = pd.DataFrame(summary_rows).set_index("Ativo")
    print("\n" + "=" * 90)
    print("COMPARATIVO FINAL — ATIVOS PROCESSADOS PELO MODELO FCFF")
    print("=" * 90)
    display(SUMMARY.style.format({
        "Preço atual": "R$ {:,.2f}",
        "DCF justo hoje": "R$ {:,.2f}",
        "RI justo hoje": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "Alvo genérico 12m": "R$ {:,.2f}",
        "Upside genérico": "{:.1%}",
        "Alvo RI setorial 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "Alvo final validado 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "Upside validado": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
        "Dividendo proj. 12m": "R$ {:,.2f}",
        "Rf longo prazo": "{:.2%}",
        "ERP Brasil": "{:.2%}",
        "Ke": "{:.2%}",
        "Kd": "{:.2%}",
        "WACC": "{:.2%}",
        "Beta": "{:.2f}",
    }))

    plt.figure(figsize=(8, 5))
    x = np.arange(len(SUMMARY.index))
    width = 0.25
    plt.bar(x - width, SUMMARY["Preço atual"], width, label="Preço atual")
    plt.bar(x, SUMMARY["DCF justo hoje"], width, label="DCF justo hoje")
    plt.bar(x + width, SUMMARY["Alvo genérico 12m"], width, label="Alvo composto genérico 12m")
    plt.xticks(x, SUMMARY.index)
    plt.ylabel("R$ por ação")
    plt.title("Radar W1 — Comparação FCFF / composto genérico (governança setorial)")
    plt.legend()
    plt.tight_layout()
    plt.show()

    validated_plot = SUMMARY.dropna(subset=["Alvo final validado 12m"]).copy()
    if not validated_plot.empty:
        plt.figure(figsize=(8, 5))
        xv = np.arange(len(validated_plot.index))
        widthv = 0.30
        plt.bar(xv - widthv/2, validated_plot["Preço atual"], widthv, label="Preço atual")
        plt.bar(xv + widthv/2, validated_plot["Alvo final validado 12m"], widthv, label="Alvo final validado 12m")
        plt.xticks(xv, validated_plot.index)
        plt.ylabel("R$ por ação")
        plt.title("Radar W1 — Apenas alvos validados pela governança do modelo")
        plt.legend()
        plt.tight_layout()
        plt.show()

EXPECTED_FCFF = [
    symbol for symbol, asset in ASSETS.items()
    if asset.get("valuation_model", "fcff") == "fcff"
]
print("\n" + "=" * 90)
print("COBERTURA DO MOTOR FCFF")
print("=" * 90)
print(f"Ativos FCFF esperados : {len(EXPECTED_FCFF)}")
print(f"Ativos FCFF processados: {len(RESULTS)}")
print(f"Ativos FCFF com falha  : {len(FAILED_ASSETS)}")

# ================================================================
# 12) COMPARATIVO — MÓDULOS PATRIMONIAIS / EQUITY
# ================================================================

if EQUITY_RESULTS:
    equity_summary_rows = []
    for symbol, r in EQUITY_RESULTS.items():
        equity_summary_rows.append({
            "Ativo": symbol,
            "Preço atual": r["price"],
            "RI coerente justo hoje": r["residual_income"]["fair_price_today"],
            "RI legado justo hoje": r["residual_income_legacy"]["fair_price_today"],
            "Alvo composto proxy 12m": r["target_12m"],
            "Alvo final validado 12m": r.get("validated_target_12m", np.nan),
            "Upside/Downside validado": r.get("validated_upside", np.nan),
            "P/L normalizado": r["assumptions"]["pe_norm"],
            "P/VP normalizado": r["assumptions"]["pb_norm"],
            "DY normalizado": r["assumptions"]["dy_norm"],
            "Payout normalizado": r["assumptions"]["payout_norm"],
            "Ke": r["assumptions"]["cost_equity"],
            "Beta": r["assumptions"]["beta"],
            "Perfil": r["model_profile"],
            "Status": r["model_status"],
            "Métodos ausentes": ", ".join(r.get("missing_methods", [])) or "—",
        })

    EQUITY_SUMMARY = pd.DataFrame(equity_summary_rows).set_index("Ativo")
    print("\n" + "=" * 90)
    print("COMPARATIVO — ATIVOS PROCESSADOS PELO MÓDULO EQUITY/PATRIMONIAL")
    print("=" * 90)
    display(EQUITY_SUMMARY.style.format({
        "Preço atual": "R$ {:,.2f}",
        "RI coerente justo hoje": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "RI legado justo hoje": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "Alvo composto proxy 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "Alvo final validado 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "Upside/Downside validado": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
        "P/L normalizado": lambda x: f"{x:.2f}x" if pd.notna(x) else "n/d",
        "P/VP normalizado": lambda x: f"{x:.2f}x" if pd.notna(x) else "n/d",
        "DY normalizado": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
        "Payout normalizado": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
        "Ke": "{:.2%}",
        "Beta": "{:.2f}",
    }))


# ================================================================
# 13) COMPARATIVO FINAL — UNIVERSO COMPLETO RADAR W1
# ================================================================

universe_rows = []
for symbol, asset in ASSETS.items():
    if symbol in RESULTS:
        r = RESULTS[symbol]
        gov = r.get("model_governance", {})
        profile = gov.get("profile", "fcff")
        target = r.get("validated_target_12m", np.nan)
        upside = r.get("validated_upside", np.nan)
        primary = (
            "Residual Income coerente setorial (50%)"
            if profile == "regulated"
            else "DCF / FCFF (50%)"
        )
        universe_rows.append({
            "Ativo": symbol,
            "Preço atual": r["price"],
            "Alvo final do modelo 12m": target,
            "Upside/Downside": upside,
            "Família do modelo": "FCFF + múltiplos" if primary.startswith("DCF") else "RI coerente setorial + múltiplos",
            "Método principal": primary,
            "Status": gov.get("status", "n/d"),
            "Observação": gov.get("reason", ""),
        })
    elif symbol in EQUITY_RESULTS:
        r = EQUITY_RESULTS[symbol]
        universe_rows.append({
            "Ativo": symbol,
            "Preço atual": r["price"],
            "Alvo final do modelo 12m": r.get("validated_target_12m", np.nan),
            "Upside/Downside": r.get("validated_upside", np.nan),
            "Família do modelo": "Equity / patrimonial",
            "Método principal": (
                "NAV/SOTP requerido — proxy RI coerente não validado"
                if r.get("model_profile") == "holding"
                else "Residual Income coerente (50%)"
            ),
            "Status": r["model_status"],
            "Observação": r["validation_note"],
        })
    elif symbol in FAILED_ASSETS:
        e = FAILED_ASSETS[symbol]
        universe_rows.append({
            "Ativo": symbol,
            "Preço atual": np.nan,
            "Alvo final do modelo 12m": np.nan,
            "Upside/Downside": np.nan,
            "Família do modelo": "FCFF",
            "Método principal": "n/d",
            "Status": "FALHA DE EXECUÇÃO",
            "Observação": e.get("Mensagem", ""),
        })
    elif symbol in EQUITY_FAILED_ASSETS:
        e = EQUITY_FAILED_ASSETS[symbol]
        universe_rows.append({
            "Ativo": symbol,
            "Preço atual": np.nan,
            "Alvo final do modelo 12m": np.nan,
            "Upside/Downside": np.nan,
            "Família do modelo": "Equity / patrimonial",
            "Método principal": "n/d",
            "Status": "FALHA DE EXECUÇÃO",
            "Observação": e.get("Mensagem", ""),
        })
    else:
        s = SKIPPED_ASSETS.get(symbol, {})
        universe_rows.append({
            "Ativo": symbol,
            "Preço atual": np.nan,
            "Alvo final do modelo 12m": np.nan,
            "Upside/Downside": np.nan,
            "Família do modelo": asset.get("valuation_model", "n/d"),
            "Método principal": "n/d",
            "Status": "SEM MOTOR COMPATÍVEL",
            "Observação": s.get("Motivo", asset.get("model_reason", "")),
        })

UNIVERSE_SUMMARY = pd.DataFrame(universe_rows).set_index("Ativo")

print("\n" + "=" * 90)
print("COMPARATIVO FINAL — UNIVERSO COMPLETO RADAR W1")
print("=" * 90)
display(UNIVERSE_SUMMARY.style.format({
    "Preço atual": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
    "Alvo final do modelo 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
    "Upside/Downside": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
}))

valid_universe_plot = UNIVERSE_SUMMARY.dropna(
    subset=["Preço atual", "Alvo final do modelo 12m"]
).copy()
if not valid_universe_plot.empty:
    plt.figure(figsize=(13, 6))
    xu = np.arange(len(valid_universe_plot.index))
    widthu = 0.34
    plt.bar(
        xu - widthu/2,
        valid_universe_plot["Preço atual"],
        widthu,
        label="Preço atual"
    )
    plt.bar(
        xu + widthu/2,
        valid_universe_plot["Alvo final do modelo 12m"],
        widthu,
        label="Alvo final do modelo 12m"
    )
    plt.xticks(xu, valid_universe_plot.index, rotation=45)
    plt.ylabel("R$ por ativo")
    plt.title("Radar W1 — Universo completo: preço atual x alvo do modelo")
    plt.legend()
    plt.tight_layout()
    plt.show()

TOTAL_EXPECTED = len(ASSETS)
TOTAL_PROCESSED = len(RESULTS) + len(EQUITY_RESULTS)
TOTAL_FAILED = len(FAILED_ASSETS) + len(EQUITY_FAILED_ASSETS)
TOTAL_SKIPPED = len(SKIPPED_ASSETS)

print("\n" + "=" * 90)
print("COBERTURA TOTAL DO RADAR W1 — TODOS OS MOTORES")
print("=" * 90)
print(f"Ativos esperados            : {TOTAL_EXPECTED}")
print(f"Processados pelo FCFF       : {len(RESULTS)}")
print(f"Processados por Equity/RI   : {len(EQUITY_RESULTS)}")
print(f"Total processado            : {TOTAL_PROCESSED}")
print(f"Falhas de execução          : {TOTAL_FAILED}")
print(f"Sem motor compatível        : {TOTAL_SKIPPED}")
if (
    TOTAL_PROCESSED == TOTAL_EXPECTED
    and TOTAL_FAILED == 0
    and TOTAL_SKIPPED == 0
):
    print("Cobertura Radar W1: 100% — 20/20 ativos processados.")
else:
    print(
        "Cobertura Radar W1 incompleta; falhas/ausências permanecem explícitas "
        "e nenhum valuation é inventado."
    )


# ================================================================
# 13A) AUDITORIA ECONÔMICA — PRINCIPAL 50% x MÉTODOS SECUNDÁRIOS
# ================================================================

METHOD_DISAGREEMENT_AUDIT = build_method_disagreement_audit(
    RESULTS,
    EQUITY_RESULTS,
    ASSETS,
)

if not METHOD_DISAGREEMENT_AUDIT.empty:
    print("\n" + "=" * 90)
    print("AUDITORIA DE DIVERGÊNCIA — MÉTODO PRINCIPAL 50% x TRÊS SECUNDÁRIOS")
    print("=" * 90)
    print(
        "Esta tabela é SOMENTE DIAGNÓSTICA e não altera adicionalmente o valuation. "
        "Ela lê os métodos já ativados nesta versão; pesos e fórmulas permanecem os definidos no motor."
    )
    print(
        "Impacto do gap no composto = peso do principal × "
        "(valor usado do principal - mediana dos valores usados dos secundários)."
    )

    audit_columns = [
        "Motor",
        "Preço atual",
        "Método principal",
        "Principal 12m",
        "P/L 12m",
        "Método secundário 2",
        "Secundário 2 12m",
        "Dividend Yield 12m",
        "Mediana secundários 12m",
        "Gap principal vs mediana %",
        "Impacto do gap no composto R$",
        "Alvo final atual 12m",
        "Upside final atual",
        "Leitura diagnóstica",
    ]

    display(
        METHOD_DISAGREEMENT_AUDIT[audit_columns].style.format({
            "Preço atual": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Principal 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "P/L 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Secundário 2 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Dividend Yield 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Mediana secundários 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Gap principal vs mediana %": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
            "Impacto do gap no composto R$": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Alvo final atual 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Upside final atual": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
        })
    )

    print("\n" + "=" * 90)
    print("RESUMO AGREGADO DA DIVERGÊNCIA ENTRE MÉTODOS")
    print("=" * 90)

    audit_valid = METHOD_DISAGREEMENT_AUDIT.dropna(
        subset=["Preço atual", "Principal 12m", "Mediana secundários 12m"]
    ).copy()

    if not audit_valid.empty:
        final_valid = audit_valid.dropna(subset=["Alvo final atual 12m"])
        final_below = int(
            (final_valid["Alvo final atual 12m"] < final_valid["Preço atual"]).sum()
        )
        final_above_or_equal = int(
            (final_valid["Alvo final atual 12m"] >= final_valid["Preço atual"]).sum()
        )
        principal_below_median = int(
            (audit_valid["Principal 12m"] < audit_valid["Mediana secundários 12m"]).sum()
        )
        principal_above_or_equal_median = int(
            (audit_valid["Principal 12m"] >= audit_valid["Mediana secundários 12m"]).sum()
        )

        diagnostic_series = audit_valid["Leitura diagnóstica"].astype(str)
        divergent_primary_low = int(
            diagnostic_series.str.startswith(
                "DIVERGÊNCIA — principal abaixo", na=False
            ).sum()
        )
        divergent_primary_high = int(
            diagnostic_series.str.startswith(
                "DIVERGÊNCIA INVERSA", na=False
            ).sum()
        )
        consensus_downside = int(
            diagnostic_series.str.startswith(
                "CONSENSO DE DOWNSIDE", na=False
            ).sum()
        )
        consensus_upside = int(
            diagnostic_series.str.startswith(
                "CONSENSO DE UPSIDE", na=False
            ).sum()
        )

        gap_pct = pd.to_numeric(
            audit_valid["Gap principal vs mediana %"],
            errors="coerce"
        ).replace([np.inf, -np.inf], np.nan).dropna()

        impact = pd.to_numeric(
            audit_valid["Impacto do gap no composto R$"],
            errors="coerce"
        ).replace([np.inf, -np.inf], np.nan).dropna()

        print(f"Ativos com auditoria completa                     : {len(audit_valid)}")
        print(f"Alvo final abaixo do preço atual                  : {final_below}")
        print(f"Alvo final >= preço atual                         : {final_above_or_equal}")
        print(f"Principal abaixo da mediana dos secundários       : {principal_below_median}")
        print(f"Principal >= mediana dos secundários              : {principal_above_or_equal_median}")
        print(f"Divergência: principal baixo / maioria secundária >= preço: {divergent_primary_low}")
        print(f"Divergência inversa                               : {divergent_primary_high}")
        print(f"Consenso 4/4 de downside                          : {consensus_downside}")
        print(f"Consenso 4/4 de upside                            : {consensus_upside}")
        if not gap_pct.empty:
            print(
                "Gap mediano principal vs mediana secundários       : "
                f"{gap_pct.median():.1%}"
            )
        if not impact.empty:
            print(
                "Impacto mediano do gap do principal no composto    : "
                f"R$ {impact.median():,.2f}"
            )

        disagreement_only = audit_valid[
            audit_valid["Leitura diagnóstica"].astype(str).str.startswith(
                "DIVERGÊNCIA", na=False
            )
        ].copy()

        if not disagreement_only.empty:
            print("\nATIVOS EM QUE O MÉTODO PRINCIPAL E A MAIORIA DOS SECUNDÁRIOS DISCORDAM:")
            disagreement_view = disagreement_only[[
                "Preço atual",
                "Principal 12m",
                "Mediana secundários 12m",
                "Gap principal vs mediana %",
                "Impacto do gap no composto R$",
                "Alvo final atual 12m",
                "Leitura diagnóstica",
            ]].sort_values("Gap principal vs mediana %")

            display(disagreement_view.style.format({
                "Preço atual": "R$ {:,.2f}",
                "Principal 12m": "R$ {:,.2f}",
                "Mediana secundários 12m": "R$ {:,.2f}",
                "Gap principal vs mediana %": "{:.1%}",
                "Impacto do gap no composto R$": "R$ {:,.2f}",
                "Alvo final atual 12m": "R$ {:,.2f}",
            }))

        gap_plot = audit_valid.dropna(
            subset=["Gap principal vs mediana %"]
        ).sort_values("Gap principal vs mediana %")

        if not gap_plot.empty:
            plt.figure(figsize=(13, 6))
            plt.bar(
                gap_plot.index,
                gap_plot["Gap principal vs mediana %"] * 100.0,
            )
            plt.axhline(0.0, linewidth=1)
            plt.ylabel("Gap do principal vs mediana dos secundários (%)")
            plt.title(
                "Radar W1 — divergência do método principal de 50% "
                "vs mediana dos três secundários"
            )
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()

    print(
        "\nLeitura: esta auditoria não substitui o valuation. "
        "Ela identifica onde existe consenso entre métodos e onde o método principal "
        "de 50% está economicamente desalinhado dos três métodos secundários."
    )


# ================================================================
# 13B) AUDITORIA ECONÔMICA PROFUNDA DO RESIDUAL INCOME
# ================================================================

RI_ECONOMIC_AUDIT, RI_TRAJECTORY_AUDIT = build_residual_income_economic_audit(
    RESULTS,
    EQUITY_RESULTS,
    ASSETS,
    METHOD_DISAGREEMENT_AUDIT,
)

if not RI_ECONOMIC_AUDIT.empty:
    print("\n" + "=" * 90)
    print("AUDITORIA ECONÔMICA PROFUNDA DO RESIDUAL INCOME — SEM ALTERAR O VALUATION")
    print("=" * 90)
    print(
        "Teste 1: ROE x Ke. Teste 2: crescimento usado x ROE×retenção. "
        "Teste 3: RI justo hoje = PL por ativo + PV dos lucros residuais por ativo."
    )
    print(
        "Esta seção é exclusivamente diagnóstica: nenhum RI, peso, preço-alvo ou "
        "premissa foi recalibrado."
    )

    ri_summary_columns = [
        "Motor RI",
        "Perfil",
        "Preço atual",
        "ROE atual",
        "Ke",
        "Spread ROE atual - Ke",
        "Payout",
        "Retenção",
        "g sustentável atual = ROE×retenção",
        "g usado ano 1",
        "g1 - g sustentável atual",
        "ROE ano 1",
        "ROE ano 5",
        "Spread ROE5 - Ke",
        "g usado ano 5",
        "g sustentável ano 5",
        "g5 - g sustentável ano 5",
        "PL por ativo",
        "PV RI por ativo",
        "RI justo hoje",
        "Erro identidade RI R$",
        "RI alvo 12m",
        "RI positivos anos 1-5",
        "RI negativos anos 1-5",
        "Extensão além do ano 5",
        "Fechamento terminal especial",
        "Leitura ROE x Ke",
        "Leitura divergência métodos",
    ]

    display(
        RI_ECONOMIC_AUDIT[ri_summary_columns].style.format({
            "Preço atual": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "ROE atual": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "Ke": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "Spread ROE atual - Ke": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "Payout": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "Retenção": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "g sustentável atual = ROE×retenção": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "g usado ano 1": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "g1 - g sustentável atual": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "ROE ano 1": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "ROE ano 5": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "Spread ROE5 - Ke": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "g usado ano 5": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "g sustentável ano 5": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "g5 - g sustentável ano 5": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "PL por ativo": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "PV RI por ativo": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "RI justo hoje": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Erro identidade RI R$": lambda x: f"R$ {x:,.8f}" if pd.notna(x) else "n/d",
            "RI alvo 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        })
    )

    print("\nDECOMPOSIÇÃO DO VALOR RI — PL POR ATIVO + PV DOS LUCROS RESIDUAIS")
    decomposition_columns = [
        "Preço atual",
        "PL por ativo",
        "PV RI por ativo",
        "PL + PV RI por ativo",
        "RI justo hoje",
        "Erro identidade RI R$",
        "PV RI / valor RI hoje",
        "RI alvo 12m",
        "Leitura divergência métodos",
    ]
    display(
        RI_ECONOMIC_AUDIT[decomposition_columns].style.format({
            "Preço atual": "R$ {:,.2f}",
            "PL por ativo": "R$ {:,.2f}",
            "PV RI por ativo": "R$ {:,.2f}",
            "PL + PV RI por ativo": "R$ {:,.2f}",
            "RI justo hoje": "R$ {:,.2f}",
            "Erro identidade RI R$": "R$ {:,.8f}",
            "PV RI / valor RI hoje": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
            "RI alvo 12m": "R$ {:,.2f}",
        })
    )

    if not RI_TRAJECTORY_AUDIT.empty:
        print("\nTRAJETÓRIA ECONÔMICA DO RI — ANOS 1 A 5")
        print(
            "g sustentável é exibido somente como identidade diagnóstica ROE×retenção; "
            "não substitui o crescimento usado no valuation."
        )
        trajectory_columns = [
            "Motor RI",
            "g usado",
            "ROE",
            "Ke",
            "Spread ROE - Ke",
            "Payout usado",
            "Retenção",
            "g sustentável = ROE×retenção",
            "g usado - g sustentável",
            "PL inicial R$ bi",
            "Lucro R$ bi",
            "RI R$ bi",
            "PV RI R$ bi",
            "PL final R$ bi",
        ]
        display(
            RI_TRAJECTORY_AUDIT[trajectory_columns].style.format({
                "g usado": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
                "ROE": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
                "Ke": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
                "Spread ROE - Ke": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
                "Payout usado": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
                "Retenção": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
                "g sustentável = ROE×retenção": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
                "g usado - g sustentável": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
                "PL inicial R$ bi": "{:.2f}",
                "Lucro R$ bi": "{:.2f}",
                "RI R$ bi": "{:.2f}",
                "PV RI R$ bi": "{:.2f}",
                "PL final R$ bi": "{:.2f}",
            })
        )

    divergent_ri = RI_ECONOMIC_AUDIT[
        RI_ECONOMIC_AUDIT["Leitura divergência métodos"].astype(str).str.startswith(
            "DIVERGÊNCIA — principal abaixo", na=False
        )
    ].copy()
    if not divergent_ri.empty:
        print("\nFOCO — ATIVOS EM QUE O RI É O PRINCIPAL E DIVERGE DA MAIORIA DOS SECUNDÁRIOS")
        focus_columns = [
            "Preço atual",
            "ROE atual",
            "Ke",
            "Spread ROE atual - Ke",
            "g sustentável atual = ROE×retenção",
            "g usado ano 1",
            "ROE ano 5",
            "Spread ROE5 - Ke",
            "PL por ativo",
            "PV RI por ativo",
            "RI justo hoje",
            "RI alvo 12m",
            "Leitura ROE x Ke",
        ]
        display(
            divergent_ri[focus_columns].style.format({
                "Preço atual": "R$ {:,.2f}",
                "ROE atual": "{:.2%}",
                "Ke": "{:.2%}",
                "Spread ROE atual - Ke": "{:.2%}",
                "g sustentável atual = ROE×retenção": "{:.2%}",
                "g usado ano 1": "{:.2%}",
                "ROE ano 5": "{:.2%}",
                "Spread ROE5 - Ke": "{:.2%}",
                "PL por ativo": "R$ {:,.2f}",
                "PV RI por ativo": "R$ {:,.2f}",
                "RI justo hoje": "R$ {:,.2f}",
                "RI alvo 12m": "R$ {:,.2f}",
            })
        )

        focus_symbols = list(divergent_ri.index)
        focus_traj = RI_TRAJECTORY_AUDIT[
            RI_TRAJECTORY_AUDIT.index.get_level_values("Ativo").isin(focus_symbols)
        ].copy()
        if not focus_traj.empty:
            print("\nTRAJETÓRIA ANOS 1-5 — APENAS OS CASOS DE DIVERGÊNCIA DO RI")
            display(
                focus_traj[[
                    "g usado",
                    "ROE",
                    "Ke",
                    "Spread ROE - Ke",
                    "g sustentável = ROE×retenção",
                    "g usado - g sustentável",
                    "RI R$ bi",
                    "PV RI R$ bi",
                ]].style.format({
                    "g usado": "{:.2%}",
                    "ROE": "{:.2%}",
                    "Ke": "{:.2%}",
                    "Spread ROE - Ke": "{:.2%}",
                    "g sustentável = ROE×retenção": "{:.2%}",
                    "g usado - g sustentável": "{:.2%}",
                    "RI R$ bi": "{:.2f}",
                    "PV RI R$ bi": "{:.2f}",
                })
            )

    identity_errors = pd.to_numeric(
        RI_ECONOMIC_AUDIT["Erro identidade RI R$"], errors="coerce"
    ).abs().replace([np.inf, -np.inf], np.nan).dropna()
    print("\nVALIDAÇÃO DA IDENTIDADE DO RESIDUAL INCOME")
    if not identity_errors.empty:
        print(
            "Maior erro absoluto de reconciliação PL/ativo + PV RI/ativo - RI justo hoje: "
            f"R$ {identity_errors.max():.10f}"
        )
    print(
        "A auditoria acima não decide ainda se o RI deve ser alterado. "
        "Ela isola a origem econômica do valor para a próxima decisão metodológica."
    )



# ================================================================
# 13C) COMPARAÇÃO RI LEGADO x RI ECONOMICAMENTE COERENTE
# ================================================================
#
# O RI coerente já está ATIVADO nesta versão onde ele permanece método principal.
# Esta seção conserva o legado somente como trilha de auditoria e compara:
#   - RI legado x RI coerente ativado;
#   - mediana dos três secundários;
#   - composto legado/candidato x alvo oficial ativado;
#   - payout histórico x payout coerente;
#   - ROE terminal, Ke e parcela de RI terminal capitalizada.
# ================================================================

RI_CORRECTION_COMPARISON, RI_COHERENT_CANDIDATES = (
    build_ri_coherent_candidate_comparison(
        RESULTS,
        EQUITY_RESULTS,
        ASSETS,
        METHOD_DISAGREEMENT_AUDIT,
    )
)

if not RI_CORRECTION_COMPARISON.empty:
    print("\n" + "=" * 90)
    print("RI LEGADO x RI ECONOMICAMENTE COERENTE — ATIVAÇÃO FINAL")
    print("=" * 90)
    print(
        "ATIVAÇÃO FINAL: RI coerente substitui o RI legado onde RI continua sendo o "
        "método principal. WEG/high-ROIC usa DCF/FCFF como principal; ITSA4 permanece "
        "proxy contábil não validado como NAV/SOTP. Ke, crescimento, dados CVM, métodos "
        "secundários e pesos permanecem inalterados."
    )
    print(
        "Regra de payout: ele só pode SUBIR em relação ao histórico quando "
        "g < ROE×retenção histórica. Nunca cai para fabricar crescimento."
    )
    print(
        "Regra terminal: se o ROE do primeiro ano terminal produzido pelo próprio modelo "
        "ainda for > Ke, o RI positivo é capitalizado com o mesmo g terminal. "
        "Nenhum prazo de fade ou ROE arbitrário é criado."
    )

    comparison_cols = [
        "Motor",
        "Perfil",
        "Preço atual",
        "RI legado 12m",
        "RI coerente 12m",
        "Variação RI coerente vs legado",
        "Mediana secundários 12m",
        "Gap legado vs mediana",
        "Gap coerente vs mediana",
        "Alvo final oficial atual 12m",
        "Composto candidato coerente 12m",
        "Alvo final oficial ativado 12m",
        "Upside oficial ativado",
        "Upside composto candidato",
        "Anos com payout elevado",
        "ROE terminal coerente",
        "Ke",
        "PV RI terminal por ativo",
        "Erro identidade candidato R$",
        "Excesso terminal capitalizado",
        "Erro candidato",
        "Leitura divergência anterior",
    ]

    display(
        RI_CORRECTION_COMPARISON[comparison_cols].style.format({
            "Preço atual": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "RI legado 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "RI coerente 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Variação RI coerente vs legado": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
            "Mediana secundários 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Gap legado vs mediana": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
            "Gap coerente vs mediana": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
            "Alvo final oficial atual 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Composto candidato coerente 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Alvo final oficial ativado 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Upside oficial ativado": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
            "Upside composto candidato": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
            "ROE terminal coerente": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "Ke": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "PV RI terminal por ativo": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Erro identidade candidato R$": lambda x: f"R$ {x:,.10f}" if pd.notna(x) else "n/d",
        })
    )

    print("\nCOERÊNCIA DE PAYOUT — ANO 1 E ANO 5")
    payout_cols = [
        "Perfil",
        "Payout legado ano 1",
        "Payout coerente ano 1",
        "Payout legado ano 5",
        "Payout coerente ano 5",
        "Anos com payout elevado",
        "ROE terminal coerente",
        "Ke",
        "Excesso terminal capitalizado",
    ]
    display(
        RI_CORRECTION_COMPARISON[payout_cols].style.format({
            "Payout legado ano 1": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "Payout coerente ano 1": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "Payout legado ano 5": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "Payout coerente ano 5": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "ROE terminal coerente": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
            "Ke": lambda x: f"{x:.2%}" if pd.notna(x) else "n/d",
        })
    )

    divergent_mask = (
        RI_CORRECTION_COMPARISON["Leitura divergência anterior"]
        .astype(str)
        .str.startswith("DIVERGÊNCIA — principal abaixo", na=False)
    )
    corrected_focus = RI_CORRECTION_COMPARISON[divergent_mask].copy()

    if not corrected_focus.empty:
        print("\nFOCO FINAL — OS CASOS QUE MOTIVARAM A CORREÇÃO")
        focus_cols = [
            "Preço atual",
            "RI legado 12m",
            "RI coerente 12m",
            "Mediana secundários 12m",
            "Gap legado vs mediana",
            "Gap coerente vs mediana",
            "Alvo final oficial atual 12m",
            "Composto candidato coerente 12m",
            "Alvo final oficial ativado 12m",
            "Upside oficial ativado",
            "Upside composto candidato",
            "Anos com payout elevado",
            "ROE terminal coerente",
            "Ke",
            "PV RI terminal por ativo",
        ]
        display(
            corrected_focus[focus_cols].style.format({
                "Preço atual": "R$ {:,.2f}",
                "RI legado 12m": "R$ {:,.2f}",
                "RI coerente 12m": "R$ {:,.2f}",
                "Mediana secundários 12m": "R$ {:,.2f}",
                "Gap legado vs mediana": "{:.1%}",
                "Gap coerente vs mediana": "{:.1%}",
                "Alvo final oficial atual 12m": "R$ {:,.2f}",
                "Composto candidato coerente 12m": "R$ {:,.2f}",
                "Alvo final oficial ativado 12m": "R$ {:,.2f}",
                "Upside oficial ativado": "{:.1%}",
                "Upside composto candidato": "{:.1%}",
                "ROE terminal coerente": "{:.2%}",
                "Ke": "{:.2%}",
                "PV RI terminal por ativo": "R$ {:,.2f}",
            })
        )

        # Trajetória candidata apenas dos casos de divergência, para não alongar
        # desnecessariamente a saída dos demais ativos.
        candidate_traj_rows = []
        for symbol in corrected_focus.index:
            candidate = RI_COHERENT_CANDIDATES.get(symbol)
            if not isinstance(candidate, dict):
                continue
            proj = candidate.get("projection", pd.DataFrame())
            if not isinstance(proj, pd.DataFrame) or proj.empty:
                continue
            for _, row in proj.iterrows():
                candidate_traj_rows.append({
                    "Ativo": symbol,
                    "Ano": int(row["year"]),
                    "g usado": row.get(
                        "growth_net_income",
                        row.get("growth", np.nan),
                    ),
                    "ROE": row.get("roe", np.nan),
                    "Ke": row.get("ke", np.nan),
                    "Payout histórico": row.get("historical_payout", np.nan),
                    "Payout coerente": row.get("payout_used", np.nan),
                    "Retenção coerente": row.get("retention_used", np.nan),
                    "g sustentável com payout histórico": row.get(
                        "sustainable_growth_historical_payout", np.nan
                    ),
                    "g sustentável com payout coerente": row.get(
                        "sustainable_growth_used", np.nan
                    ),
                    "Payout foi elevado": bool(
                        row.get("payout_adjusted_up", False)
                    ),
                    "RI R$ bi": (
                        row.get("residual_income", np.nan) / 1e9
                        if pd.notna(row.get("residual_income", np.nan))
                        else np.nan
                    ),
                    "PV RI R$ bi": (
                        row.get("pv_residual_income", np.nan) / 1e9
                        if pd.notna(row.get("pv_residual_income", np.nan))
                        else np.nan
                    ),
                })

        if candidate_traj_rows:
            candidate_traj_df = (
                pd.DataFrame(candidate_traj_rows)
                .set_index(["Ativo", "Ano"])
            )
            print("\nTRAJETÓRIA DO RI COERENTE — CASOS DE DIVERGÊNCIA")
            display(
                candidate_traj_df.style.format({
                    "g usado": "{:.2%}",
                    "ROE": "{:.2%}",
                    "Ke": "{:.2%}",
                    "Payout histórico": "{:.2%}",
                    "Payout coerente": "{:.2%}",
                    "Retenção coerente": "{:.2%}",
                    "g sustentável com payout histórico": "{:.2%}",
                    "g sustentável com payout coerente": "{:.2%}",
                    "RI R$ bi": "{:.2f}",
                    "PV RI R$ bi": "{:.2f}",
                })
            )

    candidate_errors = RI_CORRECTION_COMPARISON[
        RI_CORRECTION_COMPARISON["Erro candidato"].astype(str).str.len() > 0
    ]
    print("\nVALIDAÇÃO DA CORREÇÃO CANDIDATA")
    print(f"Ativos com RI legado analisados       : {len(RI_CORRECTION_COMPARISON)}")
    print(
        "Candidatos coerentes calculados       : "
        f"{len(RI_CORRECTION_COMPARISON) - len(candidate_errors)}"
    )
    print(f"Falhas do candidato                   : {len(candidate_errors)}")
    candidate_identity_errors = pd.to_numeric(
        RI_CORRECTION_COMPARISON["Erro identidade candidato R$"],
        errors="coerce",
    ).abs().replace([np.inf, -np.inf], np.nan).dropna()
    if not candidate_identity_errors.empty:
        print(
            "Maior erro identidade do RI candidato : "
            f"R$ {candidate_identity_errors.max():.10f}"
        )
    activated_count = int(
        pd.to_numeric(
            RI_CORRECTION_COMPARISON["Alvo final oficial ativado 12m"],
            errors="coerce",
        ).notna().sum()
    )
    print(
        "Alvos oficiais disponíveis após ativação: "
        f"{activated_count} dentro dos {len(RI_CORRECTION_COMPARISON)} ativos com RI auditado"
    )
    print(
        "Regra final: regulated/equity usam RI coerente; high_roic_growth usa DCF/FCFF; "
        "holding permanece sem alvo final validado até NAV/SOTP."
    )
    if len(candidate_errors):
        display(candidate_errors[["Perfil", "Erro candidato"]])


if EQUITY_FAILED_ASSETS:
    print("\n" + "=" * 90)
    print("ATIVOS EQUITY/PATRIMONIAIS COM FALHA — ERRO EXATO")
    print("=" * 90)
    eq_failed_df = pd.DataFrame(
        EQUITY_FAILED_ASSETS.values(),
        index=EQUITY_FAILED_ASSETS.keys()
    )
    eq_failed_df.index.name = "Ticker"
    display(eq_failed_df)


if FAILED_ASSETS:
    print("Falhas:", ", ".join(FAILED_ASSETS.keys()))
else:
    print("Cobertura FCFF: 100% dos ativos compatíveis processados.")

# Governança econômica dos resultados FCFF já processados.
if RESULTS:
    model_status_rows = []
    for symbol, r in RESULTS.items():
        gov = r.get("model_governance", {})
        model_status_rows.append({
            "Ativo": symbol,
            "Perfil": gov.get("profile", "n/d"),
            "Status": gov.get("status", "n/d"),
            "Alvo genérico 12m": r.get("generic_target_12m", np.nan),
            "Alvo RI setorial 12m": r.get("ri_target_12m", np.nan),
            "Alvo final validado 12m": r.get("validated_target_12m", np.nan),
            "Motivo": gov.get("reason", ""),
        })
    print("\n" + "=" * 90)
    print("GOVERNANÇA ECONÔMICA DOS ALVOS — NÃO CONFUNDIR DIAGNÓSTICO COM ALVO VALIDADO")
    print("=" * 90)
    model_status_df = pd.DataFrame(model_status_rows).set_index("Ativo")
    display(model_status_df.style.format({
        "Alvo genérico 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "Alvo RI setorial 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
        "Alvo final validado 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
    }))

if FAILED_ASSETS:
    print("\n" + "=" * 90)
    print("ATIVOS FCFF COM FALHA DE EXECUÇÃO — NÃO SOMEM MAIS DO RELATÓRIO")
    print("=" * 90)
    failed_df = pd.DataFrame(FAILED_ASSETS.values(), index=FAILED_ASSETS.keys())
    failed_df.index.name = "Ticker"
    display(failed_df)
    print(
        "\nUma falha de fonte/dado não é convertida em valuation silencioso. "
        "O ativo permanece listado com o erro exato para auditoria."
    )

if SKIPPED_ASSETS:
    print("\n" + "=" * 90)
    print("ATIVOS DO RADAR W1 QUE EXIGEM MODELO ESPECÍFICO")
    print("=" * 90)
    skipped_df = pd.DataFrame(SKIPPED_ASSETS.values(), index=SKIPPED_ASSETS.keys())
    skipped_df.index.name = "Ticker"
    display(skipped_df)
    print(
        "\nEsses ativos foram incluídos no universo, mas não são forçados no FCFF. "
        "Bancos, seguradoras, holdings financeiras, Units bancárias e infraestrutura "
        "de mercado financeiro exigem metodologia própria para evitar números enganadores. "
        "Entre os FCFF processados, regulated usa RI coerente quando todos os dados necessários "
        "existem; high-ROIC usa DCF/FCFF como principal e mantém RI coerente como diagnóstico."
    )



# ================================================================
# 14) RADAR DE QUALIDADE E CARTEIRA DE LONGO PRAZO
# ================================================================
#
# CAMADA DE DECISÃO — NÃO ALTERA O VALUATION
# ------------------------------------------------
# Esta seção usa SOMENTE dados e resultados já produzidos pelo próprio Radar W1.
# Ela NÃO altera:
# - DCF / FCFF;
# - Residual Income legado ou coerente;
# - Ke, WACC, g terminal, crescimento, margens ou payout do valuation;
# - P/L, EV/EBITDA, P/VP ou Dividend Yield;
# - pesos 50/20/20/10;
# - nenhum preço-alvo já calculado.
#
# Objetivo:
# separar quatro perguntas que não devem ser confundidas:
#   1) QUALIDADE DO NEGÓCIO — histórico de 5 anos;
#   2) VALUATION — leitura já existente dos quatro métodos;
#   3) CONFIANÇA DO VALUATION — concordância direcional entre os métodos;
#   4) STATUS DE CARTEIRA — síntese para acompanhamento de longo prazo.
#
# QUALITY SCORE:
# - é RELATIVO AO GRUPO ECONÔMICO DO RADAR W1, não um rating absoluto do mercado;
# - usa pesos iguais entre as dimensões discutidas, evitando criar preferência
#   discricionária por uma única métrica;
# - métricas de nível são comparadas por percentil dentro do grupo econômico;
# - métricas de consistência são calculadas diretamente pela própria série de 5 anos;
# - quando um subgrupo tem poucos pares, usa um benchmark econômico mais amplo e
#   deixa isso explícito na coluna "Grupo de comparação".
#
# Grupos utilizados:
# - Reguladas: somente regulated;
# - Bancos: bank + bank_unit;
# - Seguridade: insurance + insurance_holding;
# - Não financeiras diversas: demais companhias operacionais FCFF;
# - B3: benchmark financeiro amplo, pois não há outro market_infrastructure no universo;
# - Itaúsa: benchmark financeiro amplo, mas o status permanece PROXY/NAV-SOTP pendente.
#
# CONFIDENCE SCORE:
# - não usa limiar subjetivo;
# - é simplesmente a porcentagem dos quatro métodos que aponta para o MESMO LADO
#   do preço atual que o alvo final publicado pelo modelo;
# - portanto, com quatro métodos, os valores naturais são 25%, 50%, 75% ou 100%.
#
# STATUS DE CARTEIRA:
# - qualidade alta + consenso de upside => candidato prioritário;
# - qualidade alta + consenso de downside => excelente/forte, aguardar preço;
# - qualidade alta + divergência/misto => excelente/forte, valuation inconclusivo;
# - qualidade não prioritária + consenso de upside => preço atrativo, mas não entra
#   automaticamente na lista principal;
# - holding continua sem alvo validado até NAV/SOTP.
#


def _quality_numeric(history, column):
    """Retorna série numérica limpa sem alterar o histórico original."""
    if history is None or not isinstance(history, pd.DataFrame) or history.empty:
        return pd.Series(dtype=float)
    if column not in history.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(history[column], errors="coerce").replace([np.inf, -np.inf], np.nan)


def _quality_available_mean(values):
    """Média somente dos componentes disponíveis; não imputa dado ausente."""
    vals = [float(v) for v in values if pd.notna(v) and np.isfinite(v)]
    return float(np.mean(vals)) if vals else np.nan


def _quality_positive_share(series):
    """Percentual de observações válidas estritamente positivas, em escala 0-100."""
    s = pd.to_numeric(pd.Series(series), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return np.nan
    return float((s > 0).mean() * 100.0)


def _quality_cagr(series):
    """CAGR entre primeira e última observação válida positiva; sem extrapolar sinais."""
    s = pd.to_numeric(pd.Series(series), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 2:
        return np.nan
    first = float(s.iloc[0])
    last = float(s.iloc[-1])
    periods = len(s) - 1
    if first <= 0 or last <= 0 or periods <= 0:
        return np.nan
    return float((last / first) ** (1.0 / periods) - 1.0)


def _quality_stability_score(series):
    """
    Estabilidade interna 0-100 baseada no coeficiente de variação absoluto.

    Fórmula mecânica:
        estabilidade = 100 / (1 + CV)
    onde CV = desvio-padrão / |média|.

    Não compara a empresa com preço de mercado e não cria teto econômico externo.
    """
    s = pd.to_numeric(pd.Series(series), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 2:
        return np.nan
    mean = float(s.mean())
    if abs(mean) <= 1e-12:
        return 0.0
    cv = float(s.std(ddof=0) / abs(mean))
    if not np.isfinite(cv) or cv < 0:
        return np.nan
    return float(100.0 / (1.0 + cv))


def _quality_peer_group(symbol, asset, result_kind):
    """Define o grupo econômico de comparação sem misturar bancos com empresas operacionais."""
    if result_kind == "fcff":
        profile = str(asset.get("fcff_profile", "generic"))
        if profile == "regulated":
            return "Reguladas"
        return "Não financeiras diversas"

    profile = str(asset.get("financial_profile", "equity"))
    if profile in {"bank", "bank_unit"}:
        return "Bancos"
    if profile in {"insurance", "insurance_holding"}:
        return "Seguridade"
    if profile == "market_infrastructure":
        return "Financeiro amplo — benchmark B3"
    if profile == "holding":
        return "Financeiro amplo — proxy holding"
    return "Financeiro amplo"


def _build_quality_raw_metrics(results, equity_results, assets):
    """
    Constrói métricas históricas de qualidade usando somente os 5 anos já carregados.

    Não cria dado fundamentalista novo e não consulta fonte adicional.
    """
    rows = []

    for symbol, asset in assets.items():
        if symbol in results:
            r = results[symbol]
            h = r.get("hist", pd.DataFrame()).copy()
            if h is None or h.empty:
                continue

            revenue = _quality_numeric(h, "revenue")
            net_income = _quality_numeric(
                h,
                "net_income_for_normalization" if "net_income_for_normalization" in h.columns else "net_income"
            )
            roe = _quality_numeric(h, "roe_parent")
            fcff = _quality_numeric(h, "fcff")
            ebit = _quality_numeric(
                h,
                "ebit_for_normalization" if "ebit_for_normalization" in h.columns else "ebit"
            )
            ebitda = _quality_numeric(
                h,
                "ebitda_for_normalization" if "ebitda_for_normalization" in h.columns else "ebitda"
            )
            net_debt = _quality_numeric(h, "net_debt")
            dividends = _quality_numeric(h, "dividend_ps")

            ebit_margin = (ebit / revenue).replace([np.inf, -np.inf], np.nan)
            nd_ebitda = (net_debt / ebitda).replace([np.inf, -np.inf], np.nan)
            nd_ebitda = nd_ebitda.where(ebitda > 0)

            rows.append({
                "Ativo": symbol,
                "Tipo de motor": "FCFF",
                "Perfil": str(asset.get("fcff_profile", "generic")),
                "Grupo de comparação": _quality_peer_group(symbol, asset, "fcff"),
                "ROE mediano 5a": safe_median(roe),
                "Lucro positivo 5a %": _quality_positive_share(net_income),
                "FCFF positivo 5a %": _quality_positive_share(fcff),
                "Margem EBIT mediana 5a": safe_median(ebit_margin),
                "Estabilidade margem %": _quality_stability_score(ebit_margin),
                "Dívida líquida/EBITDA mediana": safe_median(nd_ebitda),
                "CAGR receita 5a": _quality_cagr(revenue),
                "CAGR lucro 5a": _quality_cagr(net_income),
                "Dividendos positivos 5a %": _quality_positive_share(dividends),
                "Estabilidade ROE %": _quality_stability_score(roe),
                "CAGR PL 5a": np.nan,
                "ROE > Ke anos %": np.nan,
            })

        elif symbol in equity_results:
            r = equity_results[symbol]
            h = r.get("hist", pd.DataFrame()).copy()
            if h is None or h.empty:
                continue

            net_income = _quality_numeric(h, "net_income")
            equity = _quality_numeric(h, "equity_parent")
            roe = _quality_numeric(h, "roe_parent")
            dividends = _quality_numeric(h, "dividend_ps")
            ke = pd.to_numeric(
                pd.Series([r.get("assumptions", {}).get("cost_equity", np.nan)]),
                errors="coerce"
            ).iloc[0]
            roe_excess = roe - float(ke) if pd.notna(ke) and np.isfinite(ke) else pd.Series(dtype=float)

            rows.append({
                "Ativo": symbol,
                "Tipo de motor": "Equity / patrimonial",
                "Perfil": str(asset.get("financial_profile", r.get("model_profile", "equity"))),
                "Grupo de comparação": _quality_peer_group(symbol, asset, "equity"),
                "ROE mediano 5a": safe_median(roe),
                "Lucro positivo 5a %": _quality_positive_share(net_income),
                "FCFF positivo 5a %": np.nan,
                "Margem EBIT mediana 5a": np.nan,
                "Estabilidade margem %": np.nan,
                "Dívida líquida/EBITDA mediana": np.nan,
                "CAGR receita 5a": np.nan,
                "CAGR lucro 5a": _quality_cagr(net_income),
                "Dividendos positivos 5a %": _quality_positive_share(dividends),
                "Estabilidade ROE %": _quality_stability_score(roe),
                "CAGR PL 5a": _quality_cagr(equity),
                "ROE > Ke anos %": _quality_positive_share(roe_excess),
            })

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).set_index("Ativo")
    order = [s for s in assets.keys() if s in df.index]
    return df.loc[order]


def _quality_benchmark_group(raw_quality, symbol):
    """
    Retorna a série de pares usada para percentis.

    B3 e holding não possuem três pares do mesmo subtipo no universo. Nesses casos,
    usa todos os ativos patrimoniais como benchmark, preservando a indicação explícita
    de que se trata de benchmark amplo.
    """
    if symbol not in raw_quality.index:
        return raw_quality.iloc[0:0]

    group = str(raw_quality.loc[symbol, "Grupo de comparação"])
    if group in {"Financeiro amplo — benchmark B3", "Financeiro amplo — proxy holding", "Financeiro amplo"}:
        peers = raw_quality[raw_quality["Tipo de motor"] == "Equity / patrimonial"]
    else:
        peers = raw_quality[raw_quality["Grupo de comparação"] == group]

    if len(peers) < 3:
        if raw_quality.loc[symbol, "Tipo de motor"] == "FCFF":
            peers = raw_quality[raw_quality["Tipo de motor"] == "FCFF"]
        else:
            peers = raw_quality[raw_quality["Tipo de motor"] == "Equity / patrimonial"]
    return peers


def _quality_percentile(raw_quality, symbol, column, higher_is_better=True):
    """Percentil 0-100 dentro do benchmark econômico do ativo."""
    if symbol not in raw_quality.index or column not in raw_quality.columns:
        return np.nan
    value = pd.to_numeric(pd.Series([raw_quality.loc[symbol, column]]), errors="coerce").iloc[0]
    if pd.isna(value) or not np.isfinite(value):
        return np.nan

    peers = _quality_benchmark_group(raw_quality, symbol)
    s = pd.to_numeric(peers[column], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return np.nan

    if higher_is_better:
        percentile = float((s <= float(value)).mean() * 100.0)
    else:
        percentile = float((s >= float(value)).mean() * 100.0)
    return percentile


def _quality_class_from_peer_rank(score_table, symbol):
    """
    Classificação RELATIVA ao benchmark econômico.

    Os quartis são usados apenas para comunicar posição relativa:
      quartil superior -> EXCELENTE NO GRUPO
      segundo quartil -> FORTE NO GRUPO
      terceiro quartil -> INTERMEDIÁRIA NO GRUPO
      quartil inferior -> ABAIXO DO GRUPO
    """
    if symbol not in score_table.index:
        return "N/D"
    score = pd.to_numeric(pd.Series([score_table.loc[symbol, "Quality Score"]]), errors="coerce").iloc[0]
    if pd.isna(score) or not np.isfinite(score):
        return "N/D"

    group = score_table.loc[symbol, "Grupo de comparação"]
    if group in {"Financeiro amplo — benchmark B3", "Financeiro amplo — proxy holding", "Financeiro amplo"}:
        peers = score_table[score_table["Tipo de motor"] == "Equity / patrimonial"]
    else:
        peers = score_table[score_table["Grupo de comparação"] == group]
    if len(peers) < 3:
        peers = score_table[score_table["Tipo de motor"] == score_table.loc[symbol, "Tipo de motor"]]

    valid = pd.to_numeric(peers["Quality Score"], errors="coerce").dropna()
    if valid.empty:
        return "N/D"
    rank_pct = float((valid <= float(score)).mean())

    if rank_pct >= 0.75:
        return "EXCELENTE NO GRUPO"
    if rank_pct >= 0.50:
        return "FORTE NO GRUPO"
    if rank_pct >= 0.25:
        return "INTERMEDIÁRIA NO GRUPO"
    return "ABAIXO DO GRUPO"


def build_quality_score(results, equity_results, assets):
    """
    Calcula Quality Score relativo 0-100 por família econômica.

    Empresas operacionais — dimensões discutidas:
      rentabilidade, consistência de lucros, geração de caixa, endividamento,
      estabilidade de margens, dividendos e crescimento.

    Instituições financeiras/seguradoras/B3/holding — dimensões discutidas:
      ROE, estabilidade do ROE, consistência de lucros, crescimento do PL,
      crescimento do lucro, dividendos e persistência do excesso ROE > Ke.

    Todas as dimensões disponíveis recebem PESO IGUAL. Dado ausente não recebe zero:
    ele fica fora da média e a cobertura do score é informada separadamente.
    """
    raw = _build_quality_raw_metrics(results, equity_results, assets)
    if raw.empty:
        return raw

    rows = []
    for symbol, r in raw.iterrows():
        if r["Tipo de motor"] == "FCFF":
            profitability = _quality_available_mean([
                _quality_percentile(raw, symbol, "ROE mediano 5a", True),
                _quality_percentile(raw, symbol, "Margem EBIT mediana 5a", True),
            ])
            earnings_consistency = r["Lucro positivo 5a %"]
            cash_generation = r["FCFF positivo 5a %"]
            leverage = _quality_percentile(raw, symbol, "Dívida líquida/EBITDA mediana", False)
            margin_stability = r["Estabilidade margem %"]
            dividends = r["Dividendos positivos 5a %"]
            growth = _quality_available_mean([
                _quality_percentile(raw, symbol, "CAGR receita 5a", True),
                _quality_percentile(raw, symbol, "CAGR lucro 5a", True),
            ])

            components = {
                "Rentabilidade": profitability,
                "Consistência de lucros": earnings_consistency,
                "Geração de caixa": cash_generation,
                "Endividamento": leverage,
                "Estabilidade de margens": margin_stability,
                "Dividendos": dividends,
                "Crescimento": growth,
            }
        else:
            components = {
                "Rentabilidade": _quality_percentile(raw, symbol, "ROE mediano 5a", True),
                "Estabilidade do ROE": r["Estabilidade ROE %"],
                "Consistência de lucros": r["Lucro positivo 5a %"],
                "Crescimento patrimonial": _quality_percentile(raw, symbol, "CAGR PL 5a", True),
                "Crescimento do lucro": _quality_percentile(raw, symbol, "CAGR lucro 5a", True),
                "Dividendos": r["Dividendos positivos 5a %"],
                "Excesso ROE > Ke": r["ROE > Ke anos %"],
            }

        valid_components = {
            k: float(v)
            for k, v in components.items()
            if pd.notna(v) and np.isfinite(v)
        }
        score = float(np.mean(list(valid_components.values()))) if valid_components else np.nan
        coverage = len(valid_components) / len(components) if components else np.nan

        rows.append({
            "Ativo": symbol,
            "Tipo de motor": r["Tipo de motor"],
            "Perfil": r["Perfil"],
            "Grupo de comparação": r["Grupo de comparação"],
            "Quality Score": score,
            "Cobertura Quality Score": coverage,
            **{f"Q — {k}": components.get(k, np.nan) for k in components},
            "ROE mediano 5a": r["ROE mediano 5a"],
            "Lucro positivo 5a %": r["Lucro positivo 5a %"],
            "FCFF positivo 5a %": r["FCFF positivo 5a %"],
            "Dívida líquida/EBITDA mediana": r["Dívida líquida/EBITDA mediana"],
            "CAGR receita 5a": r["CAGR receita 5a"],
            "CAGR lucro 5a": r["CAGR lucro 5a"],
            "CAGR PL 5a": r["CAGR PL 5a"],
            "Dividendos positivos 5a %": r["Dividendos positivos 5a %"],
            "ROE > Ke anos %": r["ROE > Ke anos %"],
        })

    score_table = pd.DataFrame(rows).set_index("Ativo")
    order = [s for s in assets.keys() if s in score_table.index]
    score_table = score_table.loc[order]
    score_table["Classe de qualidade"] = [
        _quality_class_from_peer_rank(score_table, symbol)
        for symbol in score_table.index
    ]
    return score_table


def _confidence_from_audit(symbol, audit):
    """
    Confidence Score = % dos quatro métodos no mesmo lado do preço que o alvo final.

    Não usa nota subjetiva. Com quatro métodos completos, o resultado é naturalmente
    25%, 50%, 75% ou 100%.
    """
    if audit is None or audit.empty or symbol not in audit.index:
        return np.nan, "N/D"

    row = audit.loc[symbol]
    price = pd.to_numeric(pd.Series([row.get("Preço atual", np.nan)]), errors="coerce").iloc[0]
    target = pd.to_numeric(pd.Series([row.get("Alvo final atual 12m", np.nan)]), errors="coerce").iloc[0]
    primary = pd.to_numeric(pd.Series([row.get("Principal 12m", np.nan)]), errors="coerce").iloc[0]
    secondary_above = int(row.get("Secundários >= preço", 0))
    secondary_below = int(row.get("Secundários < preço", 0))

    if not all(pd.notna(v) and np.isfinite(v) for v in [price, target, primary]) or price <= 0:
        return np.nan, "N/D"

    primary_above = int(primary >= price)
    primary_below = int(primary < price)
    if target >= price:
        agreeing = primary_above + secondary_above
    else:
        agreeing = primary_below + secondary_below

    score = float(agreeing / 4.0 * 100.0)
    if score >= 100.0 - 1e-9:
        label = "ALTA — 4/4"
    elif score >= 75.0 - 1e-9:
        label = "MÉDIA-ALTA — 3/4"
    elif score >= 50.0 - 1e-9:
        label = "MÉDIA — 2/4"
    else:
        label = "BAIXA — 1/4"
    return score, label


def _valuation_status_from_diagnostic(symbol, audit, is_holding=False):
    if is_holding:
        return "SEM ALVO — NAV/SOTP REQUERIDO"
    if audit is None or audit.empty or symbol not in audit.index:
        return "N/D"
    diagnostic = str(audit.loc[symbol, "Leitura diagnóstica"])
    if diagnostic.startswith("CONSENSO DE UPSIDE"):
        return "ATRATIVO — CONSENSO 4/4"
    if diagnostic.startswith("CONSENSO DE DOWNSIDE"):
        return "CARO — CONSENSO 4/4"
    if diagnostic.startswith("DIVERGÊNCIA"):
        return "INCONCLUSIVO — DIVERGÊNCIA ENTRE MÉTODOS"
    if diagnostic.startswith("MISTO"):
        return "MISTO — SEM CONSENSO"
    return diagnostic


def _quality_reason(symbol, qrow, audit):
    """Gera motivo curto com as melhores e piores dimensões efetivamente calculadas."""
    qcols = [c for c in qrow.index if str(c).startswith("Q — ")]
    pairs = []
    for c in qcols:
        v = pd.to_numeric(pd.Series([qrow[c]]), errors="coerce").iloc[0]
        if pd.notna(v) and np.isfinite(v):
            pairs.append((c.replace("Q — ", ""), float(v)))
    pairs.sort(key=lambda x: x[1], reverse=True)

    strengths = ", ".join(name for name, _ in pairs[:2]) if pairs else "dados insuficientes"
    weaknesses = ", ".join(name for name, _ in pairs[-2:]) if len(pairs) >= 2 else "dados insuficientes"

    diagnostic = (
        str(audit.loc[symbol, "Leitura diagnóstica"])
        if audit is not None and not audit.empty and symbol in audit.index
        else "valuation sem auditoria completa"
    )
    return f"Forças: {strengths}. Pontos mais fracos: {weaknesses}. Valuation: {diagnostic}."


def build_long_term_portfolio_radar(
    results,
    equity_results,
    assets,
    method_audit,
):
    """
    Consolida Quality Score + Valuation Status + Confidence Score + Status de Carteira.

    O resultado é suporte à decisão: não altera preço-alvo e não transforma score em
    recomendação automática de compra/venda.
    """
    quality = build_quality_score(results, equity_results, assets)
    if quality.empty:
        return quality

    rows = []
    for symbol, asset in assets.items():
        if symbol not in quality.index:
            continue
        q = quality.loc[symbol]
        is_holding = str(asset.get("financial_profile", "")) == "holding"

        if symbol in results:
            r = results[symbol]
            price = r.get("price", np.nan)
            target = r.get("validated_target_12m", np.nan)
            upside = r.get("validated_upside", np.nan)
        elif symbol in equity_results:
            r = equity_results[symbol]
            price = r.get("price", np.nan)
            target = r.get("validated_target_12m", np.nan)
            upside = r.get("validated_upside", np.nan)
        else:
            continue

        confidence_score, confidence_label = _confidence_from_audit(symbol, method_audit)
        valuation_status = _valuation_status_from_diagnostic(symbol, method_audit, is_holding=is_holding)
        quality_class = str(q["Classe de qualidade"])
        high_quality = quality_class in {"EXCELENTE NO GRUPO", "FORTE NO GRUPO"}

        if is_holding:
            portfolio_status = "⚪ QUALIDADE CONTÁBIL — NAV/SOTP PENDENTE"
        elif high_quality and valuation_status.startswith("ATRATIVO"):
            portfolio_status = "⭐ CANDIDATO PRIORITÁRIO"
        elif high_quality and valuation_status.startswith("CARO"):
            portfolio_status = "🟡 EMPRESA FORTE/EXCELENTE — AGUARDAR PREÇO"
        elif high_quality:
            portfolio_status = "⚪ EMPRESA FORTE/EXCELENTE — VALUATION INCONCLUSIVO"
        elif valuation_status.startswith("ATRATIVO"):
            portfolio_status = "🟢 PREÇO ATRATIVO — QUALIDADE NÃO PRIORITÁRIA"
        elif valuation_status.startswith("CARO"):
            portfolio_status = "🔴 FORA DA LISTA PRIORITÁRIA NO PREÇO ATUAL"
        else:
            portfolio_status = "⚪ MONITORAR — SEM CONCLUSÃO"

        rows.append({
            "Ativo": symbol,
            "Quality Score": q["Quality Score"],
            "Classe de qualidade": quality_class,
            "Grupo de comparação": q["Grupo de comparação"],
            "Cobertura Quality Score": q["Cobertura Quality Score"],
            "Preço atual": price,
            "Alvo validado 12m": target,
            "Upside/Downside": upside,
            "Valuation Status": valuation_status,
            "Confidence Score": confidence_score,
            "Confiança": confidence_label,
            "Status de Carteira": portfolio_status,
            "Motivo resumido": _quality_reason(symbol, q, method_audit),
        })

    if not rows:
        return pd.DataFrame()

    radar = pd.DataFrame(rows).set_index("Ativo")
    order = [s for s in assets.keys() if s in radar.index]
    return radar.loc[order]


QUALITY_SCORE_TABLE = build_quality_score(
    RESULTS,
    EQUITY_RESULTS,
    ASSETS,
)

LONG_TERM_PORTFOLIO_RADAR = build_long_term_portfolio_radar(
    RESULTS,
    EQUITY_RESULTS,
    ASSETS,
    METHOD_DISAGREEMENT_AUDIT,
)

print("\n" + "=" * 90)
print("RADAR DE QUALIDADE E CARTEIRA DE LONGO PRAZO")
print("=" * 90)
print(
    "Quality Score = qualidade histórica RELATIVA ao grupo econômico do universo W1. "
    "Ele não entra no valuation e não usa a cotação para medir qualidade."
)
print(
    "Confidence Score = porcentagem dos 4 métodos que aponta para o mesmo lado do preço "
    "que o alvo final do modelo. O score não é uma opinião subjetiva."
)

if not LONG_TERM_PORTFOLIO_RADAR.empty:
    portfolio_columns = [
        "Quality Score",
        "Classe de qualidade",
        "Grupo de comparação",
        "Preço atual",
        "Alvo validado 12m",
        "Upside/Downside",
        "Valuation Status",
        "Confidence Score",
        "Confiança",
        "Status de Carteira",
        "Motivo resumido",
    ]
    display(
        LONG_TERM_PORTFOLIO_RADAR[portfolio_columns].style.format({
            "Quality Score": lambda x: f"{x:.1f}/100" if pd.notna(x) else "n/d",
            "Preço atual": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Alvo validado 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Upside/Downside": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
            "Confidence Score": lambda x: f"{x:.0f}/100" if pd.notna(x) else "n/d",
        })
    )

    print("\n" + "=" * 90)
    print("EMPRESAS FORTES / EXCELENTES PARA ACOMPANHAMENTO DE CARTEIRA")
    print("=" * 90)
    strong_mask = LONG_TERM_PORTFOLIO_RADAR["Classe de qualidade"].isin([
        "EXCELENTE NO GRUPO",
        "FORTE NO GRUPO",
    ])
    LONG_TERM_STRONG_COMPANIES = LONG_TERM_PORTFOLIO_RADAR[strong_mask].copy()
    if not LONG_TERM_STRONG_COMPANIES.empty:
        priority_order = {
            "⭐ CANDIDATO PRIORITÁRIO": 0,
            "⚪ EMPRESA FORTE/EXCELENTE — VALUATION INCONCLUSIVO": 1,
            "🟡 EMPRESA FORTE/EXCELENTE — AGUARDAR PREÇO": 2,
            "⚪ QUALIDADE CONTÁBIL — NAV/SOTP PENDENTE": 3,
        }
        LONG_TERM_STRONG_COMPANIES["_ordem_status"] = (
            LONG_TERM_STRONG_COMPANIES["Status de Carteira"]
            .map(priority_order)
            .fillna(9)
        )
        LONG_TERM_STRONG_COMPANIES = LONG_TERM_STRONG_COMPANIES.sort_values(
            ["_ordem_status", "Quality Score"],
            ascending=[True, False],
        ).drop(columns=["_ordem_status"])

        display(
            LONG_TERM_STRONG_COMPANIES[[
                "Quality Score",
                "Classe de qualidade",
                "Valuation Status",
                "Confidence Score",
                "Status de Carteira",
                "Motivo resumido",
            ]].style.format({
                "Quality Score": lambda x: f"{x:.1f}/100" if pd.notna(x) else "n/d",
                "Confidence Score": lambda x: f"{x:.0f}/100" if pd.notna(x) else "n/d",
            })
        )
    else:
        LONG_TERM_STRONG_COMPANIES = pd.DataFrame()
        print("Nenhum ativo atingiu as classes relativas FORTE/EXCELENTE com os dados disponíveis.")

    print("\n" + "=" * 90)
    print("DETALHE DO QUALITY SCORE — AUDITORIA DAS DIMENSÕES")
    print("=" * 90)
    quality_detail_columns = [
        c for c in QUALITY_SCORE_TABLE.columns
        if c.startswith("Q — ")
    ]
    display(
        QUALITY_SCORE_TABLE[[
            "Quality Score",
            "Classe de qualidade",
            "Grupo de comparação",
            "Cobertura Quality Score",
            *quality_detail_columns,
        ]].style.format({
            "Quality Score": lambda x: f"{x:.1f}" if pd.notna(x) else "n/d",
            "Cobertura Quality Score": lambda x: f"{x:.0%}" if pd.notna(x) else "n/d",
            **{
                c: (lambda x: f"{x:.1f}" if pd.notna(x) else "n/d")
                for c in quality_detail_columns
            },
        })
    )

    print("\n" + "=" * 90)
    print("LEITURA DE GOVERNANÇA DO RADAR DE CARTEIRA")
    print("=" * 90)
    print("1) Quality Score não muda preço-alvo e não usa preço de mercado.")
    print("2) EXCELENTE/FORTE é posição relativa ao grupo econômico do universo W1, não rating absoluto do mercado.")
    print("3) Confidence Score mede somente concordância direcional entre os quatro métodos.")
    print("4) Divergência entre métodos permanece INCONCLUSIVA; o sistema não força compra/venda.")
    print("5) ITSA4 permanece sem alvo validado enquanto NAV/SOTP não for calculado com base própria.")
    print("6) O Status de Carteira é uma síntese de qualidade + valuation + confiança; nenhuma fórmula de valuation foi recalibrada.")

else:
    LONG_TERM_STRONG_COMPANIES = pd.DataFrame()
    print("Radar de qualidade indisponível: não houve dados históricos suficientes para construir a camada.")




print("\n" + "=" * 90)
print("VALIDAÇÃO DA CAMADA DE QUALIDADE / CARTEIRA")
print("=" * 90)
if not QUALITY_SCORE_TABLE.empty:
    _qs = pd.to_numeric(QUALITY_SCORE_TABLE["Quality Score"], errors="coerce").dropna()
    _qc = pd.to_numeric(QUALITY_SCORE_TABLE["Cobertura Quality Score"], errors="coerce").dropna()
    _quality_bounds_ok = bool(_qs.between(0.0, 100.0).all()) if len(_qs) else True
    _coverage_bounds_ok = bool(_qc.between(0.0, 1.0).all()) if len(_qc) else True
else:
    _quality_bounds_ok = True
    _coverage_bounds_ok = True

if not LONG_TERM_PORTFOLIO_RADAR.empty:
    _cs = pd.to_numeric(LONG_TERM_PORTFOLIO_RADAR["Confidence Score"], errors="coerce").dropna()
    _confidence_grid_ok = bool(
        _cs.round(10).isin([25.0, 50.0, 75.0, 100.0]).all()
    ) if len(_cs) else True
else:
    _confidence_grid_ok = True

print(f"Quality Score dentro de 0–100            : {'OK' if _quality_bounds_ok else 'ERRO'}")
print(f"Cobertura do Quality Score dentro de 0–1 : {'OK' if _coverage_bounds_ok else 'ERRO'}")
print(f"Confidence Score na grade 25/50/75/100   : {'OK' if _confidence_grid_ok else 'ERRO'}")
print("Valuation recalculado pela camada         : NÃO")
print("Pesos 50/20/20/10 alterados              : NÃO")

print("\nConcluído.")

# ================================================================
# PAINEL EXECUTIVO FINAL — DECISÃO DE CARTEIRA
# ================================================================
#
# Esta camada é SOMENTE DE APRESENTAÇÃO.
# Ela não recalcula valuation, Quality Score, Confidence Score, pesos ou premissas.
# Apenas organiza os resultados já produzidos em categorias executivas para facilitar
# a leitura da carteira de longo prazo.
#
# Categorias executivas já discutidas:
#   1) Candidatos prioritários
#   2) Empresas fortes/excelentes — aguardar preço
#   3) Empresas fortes/excelentes — valuation inconclusivo
#   4) Preço atrativo — qualidade não prioritária
#   5) Monitorar — sem conclusão
#   6) Fora da prioridade no preço atual
#   7) NAV/SOTP pendente
#
# Nenhum ativo é promovido ou rebaixado por regra nova: a categoria executiva
# deriva exclusivamente do campo "Status de Carteira" já calculado acima.


def _executive_bucket_from_portfolio_status(status):
    status = str(status or "").strip()

    mapping = {
        "⭐ CANDIDATO PRIORITÁRIO":
            ("1 — ⭐ CANDIDATOS PRIORITÁRIOS", 1),

        "🟡 EMPRESA FORTE/EXCELENTE — AGUARDAR PREÇO":
            ("2 — 🟡 EMPRESAS FORTES/EXCELENTES — AGUARDAR PREÇO", 2),

        "⚪ EMPRESA FORTE/EXCELENTE — VALUATION INCONCLUSIVO":
            ("3 — ⚪ EMPRESAS FORTES/EXCELENTES — VALUATION INCONCLUSIVO", 3),

        "🟢 PREÇO ATRATIVO — QUALIDADE NÃO PRIORITÁRIA":
            ("4 — 🟢 PREÇO ATRATIVO — QUALIDADE NÃO PRIORITÁRIA", 4),

        "⚪ MONITORAR — SEM CONCLUSÃO":
            ("5 — ⚪ MONITORAR — SEM CONCLUSÃO", 5),

        "🔴 FORA DA LISTA PRIORITÁRIA NO PREÇO ATUAL":
            ("6 — 🔴 FORA DA PRIORIDADE NO PREÇO ATUAL", 6),

        "⚪ QUALIDADE CONTÁBIL — NAV/SOTP PENDENTE":
            ("7 — ⚪ NAV/SOTP PENDENTE", 7),
    }

    return mapping.get(
        status,
        ("8 — ⚪ OUTROS / REVISÃO MANUAL", 8),
    )


def build_executive_decision_panel(long_term_portfolio_radar, assets):
    """
    Reorganiza o LONG_TERM_PORTFOLIO_RADAR em uma visão executiva.

    IMPORTANTE:
    - não recalcula Quality Score;
    - não recalcula valuation;
    - não cria novo score combinado;
    - não altera Confidence Score;
    - não altera Status de Carteira;
    - não cria preço de entrada;
    - não escolhe ativo por proximidade com a cotação.

    A ordenação dentro de cada categoria usa somente:
      1) categoria executiva já derivada do Status de Carteira;
      2) Quality Score decrescente;
      3) Confidence Score decrescente;
      4) ordem original do universo como desempate estável.
    """
    if long_term_portfolio_radar is None or long_term_portfolio_radar.empty:
        return pd.DataFrame()

    panel = long_term_portfolio_radar.copy()

    original_order = {symbol: i for i, symbol in enumerate(assets.keys())}
    buckets = [
        _executive_bucket_from_portfolio_status(status)
        for status in panel["Status de Carteira"]
    ]
    panel["Categoria executiva"] = [x[0] for x in buckets]
    panel["_ordem_categoria"] = [x[1] for x in buckets]
    panel["_ordem_universo"] = [
        original_order.get(symbol, 999)
        for symbol in panel.index
    ]

    panel["_quality_sort"] = pd.to_numeric(
        panel["Quality Score"], errors="coerce"
    ).fillna(-np.inf)
    panel["_confidence_sort"] = pd.to_numeric(
        panel["Confidence Score"], errors="coerce"
    ).fillna(-np.inf)

    panel = panel.sort_values(
        [
            "_ordem_categoria",
            "_quality_sort",
            "_confidence_sort",
            "_ordem_universo",
        ],
        ascending=[True, False, False, True],
        kind="stable",
    )

    return panel


def _executive_display_table(df):
    """
    Exibe a tabela executiva sem alterar dados.
    """
    if df is None or df.empty:
        print("Nenhum ativo nesta categoria.")
        return

    columns = [
        "Quality Score",
        "Classe de qualidade",
        "Preço atual",
        "Alvo validado 12m",
        "Upside/Downside",
        "Valuation Status",
        "Confidence Score",
        "Confiança",
        "Status de Carteira",
    ]

    available = [c for c in columns if c in df.columns]

    display(
        df[available].style.format({
            "Quality Score": lambda x: f"{x:.1f}/100" if pd.notna(x) else "n/d",
            "Preço atual": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Alvo validado 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Upside/Downside": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
            "Confidence Score": lambda x: f"{x:.0f}/100" if pd.notna(x) else "n/d",
        })
    )


def build_executive_watchlist(executive_panel):
    """
    Watchlist de empresas classificadas como FORTE/EXCELENTE no grupo.

    Não existe filtro adicional de valuation ou de preço aqui.
    O objetivo é separar QUALIDADE do momento de entrada.
    """
    if executive_panel is None or executive_panel.empty:
        return pd.DataFrame()

    mask = executive_panel["Classe de qualidade"].isin([
        "EXCELENTE NO GRUPO",
        "FORTE NO GRUPO",
    ])
    return executive_panel.loc[mask].copy()


def executive_panel_validation(
    executive_panel,
    long_term_portfolio_radar,
):
    """
    Valida que o painel é apenas uma reorganização do Radar de Carteira.
    """
    checks = {}

    if long_term_portfolio_radar is None:
        long_term_portfolio_radar = pd.DataFrame()
    if executive_panel is None:
        executive_panel = pd.DataFrame()

    original_index = list(long_term_portfolio_radar.index)
    executive_index = list(executive_panel.index)

    checks["mesmos_ativos"] = (
        set(original_index) == set(executive_index)
    )
    checks["sem_duplicacoes"] = (
        len(executive_index) == len(set(executive_index))
    )
    checks["mesma_quantidade"] = (
        len(original_index) == len(executive_index)
    )

    protected_columns = [
        "Quality Score",
        "Classe de qualidade",
        "Grupo de comparação",
        "Cobertura Quality Score",
        "Preço atual",
        "Alvo validado 12m",
        "Upside/Downside",
        "Valuation Status",
        "Confidence Score",
        "Confiança",
        "Status de Carteira",
        "Motivo resumido",
    ]

    protected_ok = True
    common_symbols = [
        s for s in original_index if s in executive_panel.index
    ]

    for symbol in common_symbols:
        for col in protected_columns:
            if col not in long_term_portfolio_radar.columns or col not in executive_panel.columns:
                continue

            a = long_term_portfolio_radar.at[symbol, col]
            b = executive_panel.at[symbol, col]

            if pd.isna(a) and pd.isna(b):
                continue

            if isinstance(a, (int, float, np.number)) or isinstance(b, (int, float, np.number)):
                try:
                    if not np.isclose(float(a), float(b), rtol=0.0, atol=0.0, equal_nan=True):
                        protected_ok = False
                        break
                except Exception:
                    if str(a) != str(b):
                        protected_ok = False
                        break
            elif str(a) != str(b):
                protected_ok = False
                break

        if not protected_ok:
            break

    checks["campos_protegidos_inalterados"] = protected_ok
    checks["ok"] = all(checks.values())
    return checks


EXECUTIVE_DECISION_PANEL = build_executive_decision_panel(
    LONG_TERM_PORTFOLIO_RADAR,
    ASSETS,
)

EXECUTIVE_STRONG_WATCHLIST = build_executive_watchlist(
    EXECUTIVE_DECISION_PANEL,
)


print("\n" + "=" * 100)
print("PAINEL EXECUTIVO FINAL — DECISÃO DE CARTEIRA DE LONGO PRAZO")
print("=" * 100)
print(
    "Esta é a visão resumida do Radar W1. "
    "Ela organiza Quality Score + valuation + confiança + Status de Carteira já calculados."
)
print(
    "Nenhuma fórmula de valuation, Quality Score, Confidence Score ou peso foi alterada nesta etapa."
)

if not EXECUTIVE_DECISION_PANEL.empty:
    executive_main_columns = [
        "Quality Score",
        "Classe de qualidade",
        "Grupo de comparação",
        "Preço atual",
        "Alvo validado 12m",
        "Upside/Downside",
        "Valuation Status",
        "Confidence Score",
        "Confiança",
        "Status de Carteira",
    ]

    print("\nVISÃO EXECUTIVA — UNIVERSO COMPLETO")
    display(
        EXECUTIVE_DECISION_PANEL[executive_main_columns].style.format({
            "Quality Score": lambda x: f"{x:.1f}/100" if pd.notna(x) else "n/d",
            "Preço atual": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Alvo validado 12m": lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "n/d",
            "Upside/Downside": lambda x: f"{x:.1%}" if pd.notna(x) else "n/d",
            "Confidence Score": lambda x: f"{x:.0f}/100" if pd.notna(x) else "n/d",
        })
    )

    print("\n" + "-" * 100)
    print("RESUMO POR CATEGORIA EXECUTIVA")
    print("-" * 100)

    _category_summary = (
        EXECUTIVE_DECISION_PANEL
        .groupby(
            ["_ordem_categoria", "Categoria executiva"],
            sort=True,
            dropna=False,
        )
        .size()
        .reset_index(name="Quantidade")
        .sort_values("_ordem_categoria")
        .drop(columns="_ordem_categoria")
        .set_index("Categoria executiva")
    )
    display(_category_summary)

    # Seções individuais, para leitura rápida sem misturar sinais.
    for category in (
        EXECUTIVE_DECISION_PANEL[
            ["_ordem_categoria", "Categoria executiva"]
        ]
        .drop_duplicates()
        .sort_values("_ordem_categoria")["Categoria executiva"]
        .tolist()
    ):
        subset = EXECUTIVE_DECISION_PANEL[
            EXECUTIVE_DECISION_PANEL["Categoria executiva"] == category
        ]
        print("\n" + "=" * 100)
        print(category)
        print("=" * 100)
        _executive_display_table(subset)

    print("\n" + "=" * 100)
    print("WATCHLIST DE QUALIDADE — EMPRESAS FORTES / EXCELENTES")
    print("=" * 100)
    print(
        "Esta lista ignora o momento de entrada e responde apenas: "
        "'quais empresas do universo W1 merecem permanecer acompanhadas pela qualidade relativa?'."
    )
    if not EXECUTIVE_STRONG_WATCHLIST.empty:
        watchlist_columns = [
            "Quality Score",
            "Classe de qualidade",
            "Grupo de comparação",
            "Valuation Status",
            "Confidence Score",
            "Status de Carteira",
            "Motivo resumido",
        ]
        display(
            EXECUTIVE_STRONG_WATCHLIST[watchlist_columns].style.format({
                "Quality Score": lambda x: f"{x:.1f}/100" if pd.notna(x) else "n/d",
                "Confidence Score": lambda x: f"{x:.0f}/100" if pd.notna(x) else "n/d",
            })
        )
    else:
        print("Nenhum ativo classificado como FORTE/EXCELENTE no grupo.")

else:
    print("Painel executivo indisponível porque o Radar de Carteira está vazio.")


_EXECUTIVE_VALIDATION = executive_panel_validation(
    EXECUTIVE_DECISION_PANEL,
    LONG_TERM_PORTFOLIO_RADAR,
)

print("\n" + "=" * 100)
print("VALIDAÇÃO DO PAINEL EXECUTIVO")
print("=" * 100)
print(
    f"Mesmos ativos do Radar de Carteira          : "
    f"{'OK' if _EXECUTIVE_VALIDATION.get('mesmos_ativos') else 'ERRO'}"
)
print(
    f"Sem ativos duplicados                       : "
    f"{'OK' if _EXECUTIVE_VALIDATION.get('sem_duplicacoes') else 'ERRO'}"
)
print(
    f"Mesma quantidade de ativos                  : "
    f"{'OK' if _EXECUTIVE_VALIDATION.get('mesma_quantidade') else 'ERRO'}"
)
print(
    f"Scores, alvos, status e confiança inalterados: "
    f"{'OK' if _EXECUTIVE_VALIDATION.get('campos_protegidos_inalterados') else 'ERRO'}"
)
print("Valuation recalculado pelo painel executivo : NÃO")
print("Quality Score recalculado pelo painel       : NÃO")
print("Confidence Score recalculado pelo painel    : NÃO")
print("Pesos 50/20/20/10 alterados                : NÃO")

if not _EXECUTIVE_VALIDATION.get("ok", False):
    raise AssertionError(
        "Falha na validação do Painel Executivo: a camada de apresentação "
        "não preservou integralmente o Radar de Carteira."
    )

print("\nPAINEL EXECUTIVO FINAL CONCLUÍDO.")
# ================================================================
# TABELA OBJETIVA FINAL — SITUAÇÃO ATUAL E O QUE FAZER
# ================================================================
#
# Esta camada é SOMENTE de apresentação.
# Ela não recalcula valuation, Quality Score, Confidence Score,
# Status de Carteira, preços-alvo ou pesos.
#
# A tabela consolida os ativos por "Categoria executiva" já definida
# pelo Painel Executivo e traduz cada categoria em uma ação curta
# coerente com a própria leitura do Radar W1.
#
# Colunas finais:
#   Situação atual | Ativo(s) | O que fazer
#
# Nenhum novo ranking, nota composta, gatilho de compra ou preço de
# entrada é criado aqui.


def _objective_action_from_executive_category(category):
    """
    Traduz a Categoria executiva já existente em uma orientação operacional curta.

    IMPORTANTE:
    - não promove/rebaixa ativos;
    - não altera valuation;
    - não cria recomendação a partir de informação nova;
    - apenas explica, em linguagem direta, como ler a categoria já calculada.
    """
    category = str(category or "").strip()

    actions = {
        "1 — ⭐ CANDIDATOS PRIORITÁRIOS": (
            "Aprofundar a análise do ativo para eventual inclusão em carteira; "
            "o Radar encontrou combinação favorável de qualidade, valuation e confiança."
        ),
        "2 — 🟡 EMPRESAS FORTES/EXCELENTES — AGUARDAR PREÇO": (
            "Manter na watchlist e reavaliar nas próximas atualizações; "
            "a empresa é forte/excelente, mas o preço atual ainda não está atrativo pelo modelo."
        ),
        "3 — ⚪ EMPRESAS FORTES/EXCELENTES — VALUATION INCONCLUSIVO": (
            "Continuar acompanhando a empresa, mas não usar o alvo atual isoladamente para decidir entrada; "
            "aguardar maior convergência entre os métodos ou mudança relevante nos dados/preço."
        ),
        "4 — 🟢 PREÇO ATRATIVO — QUALIDADE NÃO PRIORITÁRIA": (
            "Não priorizar somente porque o preço parece atrativo; "
            "exigir análise adicional da qualidade do negócio antes de considerar inclusão em carteira."
        ),
        "5 — ⚪ MONITORAR — SEM CONCLUSÃO": (
            "Acompanhar sem priorizar; qualidade e/ou valuation ainda não fornecem evidência suficiente "
            "para elevar o ativo às categorias principais."
        ),
        "6 — 🔴 FORA DA PRIORIDADE NO PREÇO ATUAL": (
            "Não priorizar no preço atual; reavaliar se houver mudança relevante de preço, "
            "fundamentos ou resultados nas próximas execuções."
        ),
        "7 — ⚪ NAV/SOTP PENDENTE": (
            "Não usar o valuation atual para decisão de entrada; "
            "concluir NAV/SOTP antes de classificar o ativo para carteira."
        ),
        "8 — ⚪ OUTROS / REVISÃO MANUAL": (
            "Revisar manualmente o caso antes de qualquer conclusão; "
            "o ativo não se encaixou em uma das categorias executivas padronizadas."
        ),
    }

    return actions.get(
        category,
        "Revisar manualmente a situação antes de qualquer conclusão.",
    )


def build_objective_situation_table(executive_panel):
    """
    Consolida o Painel Executivo em uma tabela final curta:

        Situação atual | Ativo(s) | O que fazer

    Regras:
    - usa somente categorias e ativos já existentes no EXECUTIVE_DECISION_PANEL;
    - cada ativo aparece uma única vez;
    - preserva a ordem das categorias executivas;
    - dentro de cada categoria, preserva a ordem já definida pelo Painel Executivo;
    - não usa preço, alvo, score ou confiança para criar nova classificação.
    """
    columns = ["Situação atual", "Ativo(s)", "O que fazer"]

    if executive_panel is None or executive_panel.empty:
        return pd.DataFrame(columns=columns)

    required = {"Categoria executiva", "_ordem_categoria"}
    missing = required.difference(executive_panel.columns)
    if missing:
        raise KeyError(
            "Painel executivo sem colunas necessárias para a tabela objetiva final: "
            + ", ".join(sorted(missing))
        )

    rows = []

    categories = (
        executive_panel[["_ordem_categoria", "Categoria executiva"]]
        .drop_duplicates()
        .sort_values("_ordem_categoria", kind="stable")
    )

    for row in categories.itertuples(index=False):
        order = int(row[0])
        category = str(row[1])

        subset = executive_panel[
            executive_panel["Categoria executiva"] == category
        ]

        symbols = [str(symbol) for symbol in subset.index]

        rows.append({
            "_ordem_categoria": order,
            "Situação atual": category,
            "Ativo(s)": ", ".join(symbols),
            "O que fazer": _objective_action_from_executive_category(category),
        })

    out = pd.DataFrame(rows)
    out = out.sort_values("_ordem_categoria", kind="stable")
    out = out.drop(columns="_ordem_categoria")
    return out[columns]


def validate_objective_situation_table(
    objective_table,
    executive_panel,
):
    """
    Confirma que a tabela objetiva é apenas uma consolidação do Painel Executivo.
    """
    checks = {}

    if executive_panel is None:
        executive_panel = pd.DataFrame()
    if objective_table is None:
        objective_table = pd.DataFrame()

    original_assets = [str(x) for x in executive_panel.index]

    summarized_assets = []
    if not objective_table.empty and "Ativo(s)" in objective_table.columns:
        for value in objective_table["Ativo(s)"].fillna(""):
            summarized_assets.extend([
                item.strip()
                for item in str(value).split(",")
                if item.strip()
            ])

    checks["mesmos_ativos"] = set(original_assets) == set(summarized_assets)
    checks["mesma_quantidade"] = len(original_assets) == len(summarized_assets)
    checks["sem_ativos_duplicados"] = (
        len(summarized_assets) == len(set(summarized_assets))
    )

    expected_categories = []
    if not executive_panel.empty and "Categoria executiva" in executive_panel.columns:
        expected_categories = (
            executive_panel[["_ordem_categoria", "Categoria executiva"]]
            .drop_duplicates()
            .sort_values("_ordem_categoria", kind="stable")["Categoria executiva"]
            .astype(str)
            .tolist()
        )

    actual_categories = (
        objective_table["Situação atual"].astype(str).tolist()
        if not objective_table.empty and "Situação atual" in objective_table.columns
        else []
    )

    checks["mesmas_categorias"] = expected_categories == actual_categories

    checks["acoes_preenchidas"] = (
        True
        if objective_table.empty
        else objective_table["O que fazer"].astype(str).str.strip().ne("").all()
    )

    checks["ok"] = all(checks.values())
    return checks


OBJECTIVE_SITUATION_TABLE = build_objective_situation_table(
    EXECUTIVE_DECISION_PANEL,
)

_OBJECTIVE_TABLE_VALIDATION = validate_objective_situation_table(
    OBJECTIVE_SITUATION_TABLE,
    EXECUTIVE_DECISION_PANEL,
)


print("\n" + "=" * 120)
print("RESUMO AGRUPADO — PRESERVADO INTERNAMENTE, MAS NÃO EXIBIDO NESTA VERSÃO")
print("=" * 120)
print(
    "A antiga tabela por categorias continua calculada em OBJECTIVE_SITUATION_TABLE e validada, "
    "mas sua exibição foi substituída para evitar a leitura genérica que confundia a decisão. "
    "A leitura recomendada está no PAINEL FINAL POR ATIVO, no fim absoluto da execução."
)
print(
    f"Validação interna do resumo agrupado: "
    f"{'OK' if _OBJECTIVE_TABLE_VALIDATION.get('ok', False) else 'ERRO'}"
)
if not _OBJECTIVE_TABLE_VALIDATION.get("ok", False):
    raise AssertionError(
        "Falha na validação da Tabela Objetiva agrupada: a consolidação "
        "não preservou integralmente os ativos/categorias do Painel Executivo."
    )
print("Resumo agrupado preservado como auditoria; siga para a tabela final individual por ativo.")
# ================================================================
# 21) TABELA FINAL EXPLICATIVA POR ATIVO — QUALIDADE + PREÇO
# ================================================================
#
# OBJETIVO:
# - responder de forma objetiva, ativo por ativo:
#       1) a empresa é forte dentro do grupo comparável do Radar W1?
#       2) o preço atual está atrativo segundo os quatro métodos do valuation?
#       3) quais números sustentam essas duas leituras?
#       4) qual é a leitura operacional para carteira?
#
# GOVERNANÇA:
# - NÃO recalcula valuation;
# - NÃO recalcula Quality Score;
# - NÃO recalcula Confidence Score;
# - NÃO altera Status de Carteira;
# - NÃO cria margem de segurança arbitrária;
# - NÃO cria novo ranking, peso ou recomendação oculta;
# - usa somente métricas e classificações já calculadas pelo Radar.
# ================================================================


def _final_explanation_fmt_pct(value, decimals=1):
    """Formata razão em escala 0-1 como percentual; retorna n/d quando indisponível."""
    v = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(v) or not np.isfinite(v):
        return "n/d"
    return f"{float(v) * 100.0:.{int(decimals)}f}%"


def _final_explanation_fmt_score_pct(value, decimals=0):
    """Formata métrica já expressa em escala 0-100."""
    v = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(v) or not np.isfinite(v):
        return "n/d"
    return f"{float(v):.{int(decimals)}f}%"


def _final_explanation_fmt_money(value):
    """Formata preço/alvo em reais."""
    v = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(v) or not np.isfinite(v):
        return "n/d"
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _final_explanation_fmt_multiple(value):
    """Formata múltiplo em x."""
    v = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(v) or not np.isfinite(v):
        return "n/d"
    return f"{float(v):.2f}x".replace(".", ",")


def _final_company_strength_label(qrow):
    """
    Traduz a classe relativa já calculada pelo Quality Score para uma resposta direta
    à pergunta 'a empresa é forte?' sem criar novo limiar.
    """
    quality_class = str(qrow.get("Classe de qualidade", "N/D"))
    score = pd.to_numeric(
        pd.Series([qrow.get("Quality Score", np.nan)]),
        errors="coerce",
    ).iloc[0]
    score_text = f"{float(score):.1f}/100" if pd.notna(score) and np.isfinite(score) else "n/d"

    if quality_class == "EXCELENTE NO GRUPO":
        return f"SIM — EXCELENTE NO GRUPO ({score_text})"
    if quality_class == "FORTE NO GRUPO":
        return f"SIM — FORTE NO GRUPO ({score_text})"
    if quality_class == "INTERMEDIÁRIA NO GRUPO":
        return f"NÃO PRIORITÁRIA — INTERMEDIÁRIA NO GRUPO ({score_text})"
    if quality_class == "ABAIXO DO GRUPO":
        return f"NÃO — ABAIXO DO GRUPO ({score_text})"
    return f"N/D ({score_text})"


def _final_quality_evidence(qrow):
    """
    Explica a qualidade com NÚMEROS observados no histórico usado pelo Radar.

    FCFF:
      ROE mediano, lucro positivo, FCFF positivo, dívida líquida/EBITDA,
      CAGR de receita/lucro e presença de dividendos.

    Equity/patrimonial:
      ROE mediano, lucro positivo, ROE > Ke, CAGR do PL/lucro
      e presença de dividendos.
    """
    engine = str(qrow.get("Tipo de motor", ""))
    group = str(qrow.get("Grupo de comparação", "n/d"))
    coverage = pd.to_numeric(
        pd.Series([qrow.get("Cobertura Quality Score", np.nan)]),
        errors="coerce",
    ).iloc[0]

    roe = _final_explanation_fmt_pct(qrow.get("ROE mediano 5a", np.nan))
    profit_positive = _final_explanation_fmt_score_pct(
        qrow.get("Lucro positivo 5a %", np.nan)
    )
    dividends_positive = _final_explanation_fmt_score_pct(
        qrow.get("Dividendos positivos 5a %", np.nan)
    )

    if engine == "FCFF":
        fcff_positive = _final_explanation_fmt_score_pct(
            qrow.get("FCFF positivo 5a %", np.nan)
        )
        leverage = _final_explanation_fmt_multiple(
            qrow.get("Dívida líquida/EBITDA mediana", np.nan)
        )
        revenue_cagr = _final_explanation_fmt_pct(
            qrow.get("CAGR receita 5a", np.nan)
        )
        profit_cagr = _final_explanation_fmt_pct(
            qrow.get("CAGR lucro 5a", np.nan)
        )
        evidence = (
            f"Grupo: {group}. ROE mediano 5a {roe}; lucro positivo em "
            f"{profit_positive} dos anos válidos; FCFF positivo em {fcff_positive}; "
            f"dívida líquida/EBITDA mediana {leverage}; CAGR receita {revenue_cagr}; "
            f"CAGR lucro {profit_cagr}; dividendos positivos em {dividends_positive}."
        )
    else:
        roe_above_ke = _final_explanation_fmt_score_pct(
            qrow.get("ROE > Ke anos %", np.nan)
        )
        equity_cagr = _final_explanation_fmt_pct(
            qrow.get("CAGR PL 5a", np.nan)
        )
        profit_cagr = _final_explanation_fmt_pct(
            qrow.get("CAGR lucro 5a", np.nan)
        )
        evidence = (
            f"Grupo: {group}. ROE mediano 5a {roe}; lucro positivo em "
            f"{profit_positive} dos anos válidos; ROE acima do Ke em {roe_above_ke}; "
            f"CAGR do patrimônio líquido {equity_cagr}; CAGR do lucro {profit_cagr}; "
            f"dividendos positivos em {dividends_positive}."
        )

    if pd.notna(coverage) and np.isfinite(coverage) and float(coverage) < 0.999999:
        evidence += (
            f" Cobertura do Quality Score: {float(coverage) * 100.0:.0f}% "
            "das dimensões previstas."
        )

    return evidence


def _final_price_attractiveness_label(portfolio_row):
    """
    Responde 'o preço está atrativo?' usando SOMENTE o Valuation Status existente.
    Não cria margem de segurança nova.
    """
    status = str(portfolio_row.get("Valuation Status", "N/D"))

    if status.startswith("ATRATIVO"):
        return "SIM — PREÇO ATRATIVO PELO MODELO"
    if status.startswith("CARO"):
        return "NÃO — PREÇO CARO PELO MODELO"
    if status.startswith("INCONCLUSIVO") or status.startswith("MISTO"):
        return "INCONCLUSIVO — MÉTODOS DIVERGEM"
    if status.startswith("SEM ALVO"):
        return "N/D — NAV/SOTP PENDENTE"
    return "N/D"


def _final_valuation_evidence(symbol, portfolio_row, method_audit):
    """
    Mostra os números que sustentam a leitura de preço:
    preço atual, alvo final, upside/downside e os quatro métodos.

    Para holding sem alvo validado, explicita a necessidade de NAV/SOTP.
    """
    valuation_status = str(portfolio_row.get("Valuation Status", "N/D"))

    if valuation_status.startswith("SEM ALVO"):
        price = _final_explanation_fmt_money(portfolio_row.get("Preço atual", np.nan))
        return (
            f"Preço atual {price}. O Radar não publica alvo validado para este caso; "
            "o método adequado permanece NAV/SOTP antes de concluir se a ação está barata ou cara."
        )

    price = _final_explanation_fmt_money(portfolio_row.get("Preço atual", np.nan))
    target = _final_explanation_fmt_money(portfolio_row.get("Alvo validado 12m", np.nan))
    upside = pd.to_numeric(
        pd.Series([portfolio_row.get("Upside/Downside", np.nan)]),
        errors="coerce",
    ).iloc[0]
    upside_text = (
        f"{float(upside) * 100.0:+.1f}%"
        if pd.notna(upside) and np.isfinite(upside)
        else "n/d"
    )

    if method_audit is None or method_audit.empty or symbol not in method_audit.index:
        return (
            f"Preço atual {price}; alvo validado 12m {target} ({upside_text}). "
            "Auditoria dos quatro métodos indisponível."
        )

    a = method_audit.loc[symbol]
    primary_name = str(a.get("Método principal", "Principal"))
    primary = _final_explanation_fmt_money(a.get("Principal 12m", np.nan))
    pl = _final_explanation_fmt_money(a.get("P/L 12m", np.nan))
    secondary2_name = str(a.get("Método secundário 2", "Secundário 2"))
    secondary2 = _final_explanation_fmt_money(a.get("Secundário 2 12m", np.nan))
    dy = _final_explanation_fmt_money(a.get("Dividend Yield 12m", np.nan))
    diagnostic = str(a.get("Leitura diagnóstica", "n/d"))

    return (
        f"Preço {price}; alvo final 12m {target} ({upside_text}). "
        f"{primary_name}: {primary}; P/L: {pl}; {secondary2_name}: {secondary2}; "
        f"Dividend Yield: {dy}. Resultado: {diagnostic}."
    )


def _final_portfolio_reading(portfolio_row):
    """
    Explica o que a combinação QUALIDADE + PREÇO significa para a carteira,
    sem alterar o Status de Carteira já calculado.
    """
    status = str(portfolio_row.get("Status de Carteira", "")).strip()

    mapping = {
        "⭐ CANDIDATO PRIORITÁRIO": (
            "Qualidade forte/excelente e preço atrativo com consenso dos métodos. "
            "É o primeiro grupo a ser aprofundado para eventual inclusão em carteira."
        ),
        "🟡 EMPRESA FORTE/EXCELENTE — AGUARDAR PREÇO": (
            "A empresa passa no filtro de qualidade, mas o preço atual não passa no valuation. "
            "Manter na watchlist e reavaliar quando a cotação cair ou os fundamentos elevarem o alvo."
        ),
        "⚪ EMPRESA FORTE/EXCELENTE — VALUATION INCONCLUSIVO": (
            "A empresa passa no filtro de qualidade, mas os métodos não confirmam um preço de entrada. "
            "Manter na watchlist e não usar o alvo composto isoladamente como sinal de entrada."
        ),
        "🟢 PREÇO ATRATIVO — QUALIDADE NÃO PRIORITÁRIA": (
            "O valuation indica preço atrativo, mas a qualidade relativa não está entre Forte/Excelente. "
            "Exigir análise adicional da qualidade antes de considerar inclusão em carteira."
        ),
        "⚪ MONITORAR — SEM CONCLUSÃO": (
            "A combinação entre qualidade e valuation ainda não é suficiente para prioridade. "
            "Acompanhar novas demonstrações e nova leitura de preço antes de decidir."
        ),
        "🔴 FORA DA LISTA PRIORITÁRIA NO PREÇO ATUAL": (
            "No estado atual, o ativo não combina qualidade prioritária com preço atrativo. "
            "Não priorizar agora; reavaliar se preço ou fundamentos mudarem."
        ),
        "⚪ QUALIDADE CONTÁBIL — NAV/SOTP PENDENTE": (
            "Há leitura contábil de qualidade, mas ainda não existe valuation apropriado para o preço. "
            "Concluir NAV/SOTP antes de qualquer decisão baseada em preço justo."
        ),
    }

    return mapping.get(
        status,
        "Revisar manualmente antes de concluir; o caso não se encaixou nas situações padronizadas.",
    )


def build_final_explanatory_asset_table(
    quality_score_table,
    long_term_portfolio_radar,
    method_audit,
    executive_panel,
):
    """
    Tabela final, UMA LINHA POR ATIVO:

        Ativo
        Empresa forte?
        Evidências da qualidade
        Preço está atrativo?
        Evidências do valuation
        Leitura para carteira

    Nenhum campo desta tabela participa dos cálculos anteriores.
    """
    columns = [
        "Ativo",
        "Empresa forte?",
        "Evidências da qualidade",
        "Preço está atrativo?",
        "Evidências do valuation",
        "Leitura para carteira",
    ]

    if (
        quality_score_table is None
        or quality_score_table.empty
        or long_term_portfolio_radar is None
        or long_term_portfolio_radar.empty
    ):
        return pd.DataFrame(columns=columns)

    if executive_panel is not None and not executive_panel.empty:
        order = [str(symbol) for symbol in executive_panel.index]
    else:
        order = [str(symbol) for symbol in long_term_portfolio_radar.index]

    rows = []
    for symbol in order:
        if symbol not in quality_score_table.index:
            continue
        if symbol not in long_term_portfolio_radar.index:
            continue

        q = quality_score_table.loc[symbol]
        p = long_term_portfolio_radar.loc[symbol]

        rows.append({
            "Ativo": symbol,
            "Empresa forte?": _final_company_strength_label(q),
            "Evidências da qualidade": _final_quality_evidence(q),
            "Preço está atrativo?": _final_price_attractiveness_label(p),
            "Evidências do valuation": _final_valuation_evidence(
                symbol,
                p,
                method_audit,
            ),
            "Leitura para carteira": _final_portfolio_reading(p),
        })

    return pd.DataFrame(rows, columns=columns)


def validate_final_explanatory_asset_table(
    final_table,
    quality_score_table,
    long_term_portfolio_radar,
    executive_panel,
):
    """
    Valida que a nova tabela é SOMENTE explicativa e cobre os mesmos ativos.
    """
    checks = {}

    expected = (
        [str(x) for x in executive_panel.index]
        if executive_panel is not None and not executive_panel.empty
        else [str(x) for x in long_term_portfolio_radar.index]
    )

    actual = (
        final_table["Ativo"].astype(str).tolist()
        if final_table is not None and not final_table.empty
        else []
    )

    checks["mesmos_ativos"] = set(expected) == set(actual)
    checks["mesma_quantidade"] = len(expected) == len(actual)
    checks["sem_duplicados"] = len(actual) == len(set(actual))
    checks["mesma_ordem"] = expected == actual

    required_text = [
        "Empresa forte?",
        "Evidências da qualidade",
        "Preço está atrativo?",
        "Evidências do valuation",
        "Leitura para carteira",
    ]
    checks["explicacoes_preenchidas"] = (
        True
        if final_table is None or final_table.empty
        else all(
            final_table[col].astype(str).str.strip().ne("").all()
            for col in required_text
        )
    )

    checks["ok"] = all(checks.values())
    return checks


FINAL_EXPLANATORY_ASSET_TABLE = build_final_explanatory_asset_table(
    QUALITY_SCORE_TABLE,
    LONG_TERM_PORTFOLIO_RADAR,
    METHOD_DISAGREEMENT_AUDIT,
    EXECUTIVE_DECISION_PANEL,
)

_FINAL_EXPLANATORY_VALIDATION = validate_final_explanatory_asset_table(
    FINAL_EXPLANATORY_ASSET_TABLE,
    QUALITY_SCORE_TABLE,
    LONG_TERM_PORTFOLIO_RADAR,
    EXECUTIVE_DECISION_PANEL,
)


print("\n" + "=" * 140)
print("TABELA FINAL EXPLICATIVA — EMPRESA FORTE? PREÇO ATRATIVO? POR QUÊ?")
print("=" * 140)
print(
    "Esta é a leitura final do Radar W1 por ativo. "
    "A coluna de qualidade usa o Quality Score já calculado; "
    "a coluna de preço usa o valuation e a auditoria dos quatro métodos já calculados."
)
print(
    "IMPORTANTE: 'forte/excelente' é relativo ao grupo econômico do universo W1; "
    "'preço atrativo/caro' é a leitura do modelo, não uma garantia de retorno."
)

if not FINAL_EXPLANATORY_ASSET_TABLE.empty:
    display(
        FINAL_EXPLANATORY_ASSET_TABLE.style.set_properties(
            subset=[
                "Empresa forte?",
                "Evidências da qualidade",
                "Preço está atrativo?",
                "Evidências do valuation",
                "Leitura para carteira",
            ],
            **{"white-space": "normal", "text-align": "left"}
        )
    )
else:
    print("Tabela final explicativa indisponível.")


print("\nCOMO LER EM 10 SEGUNDOS")
print(
    "• SIM — EXCELENTE/FORTE + SIM — PREÇO ATRATIVO: "
    "combinação que leva ao grupo de candidatos prioritários."
)
print(
    "• SIM — EXCELENTE/FORTE + NÃO — PREÇO CARO: "
    "boa empresa, mas o Radar indica esperar preço."
)
print(
    "• SIM — EXCELENTE/FORTE + INCONCLUSIVO: "
    "boa empresa, porém o Radar ainda não confirma preço de entrada."
)
print(
    "• NÃO PRIORITÁRIA/ABAIXO + PREÇO ATRATIVO: "
    "o preço pode chamar atenção, mas a qualidade precisa ser investigada antes."
)
print(
    "• N/D — NAV/SOTP: "
    "não concluir barato/caro até terminar o valuation adequado da holding."
)


print("\nVALIDAÇÃO DA TABELA FINAL EXPLICATIVA")
print(
    f"Mesmos ativos do Painel Executivo      : "
    f"{'OK' if _FINAL_EXPLANATORY_VALIDATION.get('mesmos_ativos') else 'ERRO'}"
)
print(
    f"Mesma quantidade de ativos             : "
    f"{'OK' if _FINAL_EXPLANATORY_VALIDATION.get('mesma_quantidade') else 'ERRO'}"
)
print(
    f"Sem ativos duplicados                  : "
    f"{'OK' if _FINAL_EXPLANATORY_VALIDATION.get('sem_duplicados') else 'ERRO'}"
)
print(
    f"Mesma ordem do Painel Executivo        : "
    f"{'OK' if _FINAL_EXPLANATORY_VALIDATION.get('mesma_ordem') else 'ERRO'}"
)
print(
    f"Explicações objetivas preenchidas      : "
    f"{'OK' if _FINAL_EXPLANATORY_VALIDATION.get('explicacoes_preenchidas') else 'ERRO'}"
)
print("Valuation alterado por esta tabela      : NÃO")
print("Quality Score alterado por esta tabela  : NÃO")
print("Confidence Score alterado               : NÃO")
print("Status de Carteira alterado              : NÃO")
print("Pesos 50/20/20/10 alterados             : NÃO")

if not _FINAL_EXPLANATORY_VALIDATION.get("ok", False):
    raise AssertionError(
        "Falha na validação da Tabela Final Explicativa: "
        "a camada de apresentação não preservou integralmente os ativos do painel."
    )

print("\nRADAR W1 — TABELA FINAL EXPLICATIVA CONCLUÍDA.")

# ================================================================
# 17D) PAINEL FINAL DE DECISÃO POR ATIVO — QUALIDADE + PREÇO + MOTIVO
# ================================================================
#
# OBJETIVO DESTA CAMADA:
# responder diretamente, PARA CADA ATIVO:
#   1) É um bom ativo para carteira segundo a qualidade histórica do Radar?
#   2) O preço atual está atrativo, caro ou inconclusivo segundo o valuation?
#   3) Quais números sustentam essas duas respostas?
#   4) Qual é a conclusão operacional coerente com o próprio Radar?
#
# GOVERNANÇA — ESTA CAMADA NÃO ALTERA NENHUM CÁLCULO:
# - não recalcula valuation;
# - não recalcula Quality Score;
# - não recalcula Confidence Score;
# - não altera Status de Carteira;
# - não cria margem de segurança nova;
# - não cria nota composta, ranking ou peso novo;
# - não cria preço de entrada;
# - apenas traduz, com números, as classificações JÁ PRODUZIDAS acima.
#
# A tabela anterior agrupada é preservada por auditoria/compatibilidade.
# ESTA tabela abaixo é a leitura final recomendada para uso diário.


def _decision_fmt_num(value, decimals=1):
    """Número simples; n/d quando indisponível."""
    v = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(v) or not np.isfinite(v):
        return "n/d"
    return f"{float(v):.{int(decimals)}f}".replace(".", ",")


def _decision_fmt_ratio_pct(value, decimals=1):
    """Razão 0-1 -> percentual."""
    v = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(v) or not np.isfinite(v):
        return "n/d"
    return f"{float(v) * 100.0:.{int(decimals)}f}%".replace(".", ",")


def _decision_fmt_score_pct(value, decimals=0):
    """Valor já expresso em 0-100 -> percentual."""
    v = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(v) or not np.isfinite(v):
        return "n/d"
    return f"{float(v):.{int(decimals)}f}%".replace(".", ",")


def _decision_fmt_money(value):
    """Preço em reais."""
    v = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(v) or not np.isfinite(v):
        return "n/d"
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _decision_fmt_multiple(value):
    """Múltiplo em x."""
    v = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(v) or not np.isfinite(v):
        return "n/d"
    return f"{float(v):.2f}x".replace(".", ",")


def _decision_quality_verdict(qrow):
    """
    Resposta direta à pergunta 'é bom ativo para carteira?' usando SOMENTE
    a Classe de qualidade já calculada pelo Radar.

    Não cria limiar novo: EXCELENTE/FORTE já são classes do motor existente.
    """
    quality_class = str(qrow.get("Classe de qualidade", "N/D")).strip()
    score = pd.to_numeric(
        pd.Series([qrow.get("Quality Score", np.nan)]),
        errors="coerce",
    ).iloc[0]
    score_text = (
        f"{float(score):.1f}/100".replace(".", ",")
        if pd.notna(score) and np.isfinite(score)
        else "n/d"
    )

    if quality_class == "EXCELENTE NO GRUPO":
        return f"SIM — BOM ATIVO / EXCELENTE NO GRUPO ({score_text})"
    if quality_class == "FORTE NO GRUPO":
        return f"SIM — BOM ATIVO / FORTE NO GRUPO ({score_text})"
    if quality_class == "INTERMEDIÁRIA NO GRUPO":
        return f"NÃO PRIORITÁRIO — QUALIDADE INTERMEDIÁRIA ({score_text})"
    if quality_class == "ABAIXO DO GRUPO":
        return f"NÃO PRIORITÁRIO — QUALIDADE ABAIXO DOS PARES ({score_text})"
    return f"INCONCLUSIVO — QUALIDADE N/D ({score_text})"


def _decision_quality_components(qrow):
    """
    Retorna os dois componentes mais fortes e os dois mais fracos do Quality Score.
    Usa SOMENTE as dimensões Q — ... já calculadas.
    """
    components = []
    for col in qrow.index:
        if not str(col).startswith("Q — "):
            continue
        v = pd.to_numeric(pd.Series([qrow.get(col, np.nan)]), errors="coerce").iloc[0]
        if pd.notna(v) and np.isfinite(v):
            components.append((str(col).replace("Q — ", ""), float(v)))

    if not components:
        return "Componentes do Quality Score indisponíveis."

    ordered = sorted(components, key=lambda x: x[1], reverse=True)
    top = ordered[:2]
    bottom = sorted(components, key=lambda x: x[1])[:2]

    top_text = "; ".join(
        f"{name} {value:.0f}/100" for name, value in top
    )
    bottom_text = "; ".join(
        f"{name} {value:.0f}/100" for name, value in bottom
    )

    return f"Melhores dimensões: {top_text}. Mais fracas: {bottom_text}."


def _decision_quality_evidence(qrow):
    """
    Motivo NUMÉRICO da qualidade, em linguagem curta.

    Não financeiro/FCFF:
      Quality Score, ROE mediano, lucro positivo, FCFF positivo,
      dívida líquida/EBITDA, CAGR de receita/lucro, dividendos.

    Financeiro/patrimonial:
      Quality Score, ROE mediano, lucro positivo, ROE>Ke,
      CAGR do PL/lucro, dividendos.
    """
    score = _decision_fmt_num(qrow.get("Quality Score", np.nan), 1)
    group = str(qrow.get("Grupo de comparação", "n/d"))
    engine = str(qrow.get("Tipo de motor", ""))

    roe = _decision_fmt_ratio_pct(qrow.get("ROE mediano 5a", np.nan), 1)
    profit_positive = _decision_fmt_score_pct(qrow.get("Lucro positivo 5a %", np.nan), 0)
    dividends_positive = _decision_fmt_score_pct(qrow.get("Dividendos positivos 5a %", np.nan), 0)

    if engine == "FCFF":
        fcff_positive = _decision_fmt_score_pct(qrow.get("FCFF positivo 5a %", np.nan), 0)
        leverage = _decision_fmt_multiple(qrow.get("Dívida líquida/EBITDA mediana", np.nan))
        revenue_cagr = _decision_fmt_ratio_pct(qrow.get("CAGR receita 5a", np.nan), 1)
        profit_cagr = _decision_fmt_ratio_pct(qrow.get("CAGR lucro 5a", np.nan), 1)
        raw = (
            f"Score {score}/100 no grupo {group}. ROE mediano 5a {roe}; "
            f"lucro positivo em {profit_positive} das observações válidas; "
            f"FCFF positivo em {fcff_positive}; dívida líquida/EBITDA mediana {leverage}; "
            f"CAGR receita {revenue_cagr}; CAGR lucro {profit_cagr}; "
            f"dividendos positivos em {dividends_positive}."
        )
    else:
        roe_above_ke = _decision_fmt_score_pct(qrow.get("ROE > Ke anos %", np.nan), 0)
        equity_cagr = _decision_fmt_ratio_pct(qrow.get("CAGR PL 5a", np.nan), 1)
        profit_cagr = _decision_fmt_ratio_pct(qrow.get("CAGR lucro 5a", np.nan), 1)
        raw = (
            f"Score {score}/100 no grupo {group}. ROE mediano 5a {roe}; "
            f"lucro positivo em {profit_positive} das observações válidas; "
            f"ROE acima do Ke em {roe_above_ke}; CAGR do PL {equity_cagr}; "
            f"CAGR do lucro {profit_cagr}; dividendos positivos em {dividends_positive}."
        )

    return raw + " " + _decision_quality_components(qrow)


def _decision_price_verdict(prow):
    """
    Resposta direta à pergunta 'está barato?' usando SOMENTE o Valuation Status já existente.
    """
    status = str(prow.get("Valuation Status", "N/D")).strip()
    confidence = str(prow.get("Confiança", "N/D")).strip()

    if status.startswith("ATRATIVO"):
        return f"SIM — BARATO/ATRATIVO PELO MODELO ({confidence})"
    if status.startswith("CARO"):
        return f"NÃO — CARO PELO MODELO ({confidence})"
    if status.startswith("INCONCLUSIVO"):
        return f"INCONCLUSIVO — MÉTODOS DIVERGEM ({confidence})"
    if status.startswith("MISTO"):
        return f"INCONCLUSIVO — SEM CONSENSO ({confidence})"
    if status.startswith("SEM ALVO"):
        return "N/D — NAV/SOTP PENDENTE"
    return f"INCONCLUSIVO — {status}"


def _decision_method_values(symbol, method_audit):
    """Resumo legível dos quatro métodos já existentes na auditoria."""
    if method_audit is None or method_audit.empty or symbol not in method_audit.index:
        return "Quatro métodos: n/d."

    a = method_audit.loc[symbol]
    primary_name = str(a.get("Método principal", "Principal"))
    primary = _decision_fmt_money(a.get("Principal 12m", np.nan))
    pl = _decision_fmt_money(a.get("P/L 12m", np.nan))
    secondary2_name = str(a.get("Método secundário 2", "Secundário 2"))
    secondary2 = _decision_fmt_money(a.get("Secundário 2 12m", np.nan))
    dy = _decision_fmt_money(a.get("Dividend Yield 12m", np.nan))

    return (
        f"{primary_name} {primary}; P/L {pl}; "
        f"{secondary2_name} {secondary2}; Dividend Yield {dy}."
    )


def _decision_price_evidence(symbol, prow, method_audit):
    """Motivo NUMÉRICO do barato/caro/inconclusivo."""
    price = _decision_fmt_money(prow.get("Preço atual", np.nan))
    target = _decision_fmt_money(prow.get("Alvo validado 12m", np.nan))
    upside = pd.to_numeric(
        pd.Series([prow.get("Upside/Downside", np.nan)]),
        errors="coerce",
    ).iloc[0]
    upside_text = (
        f"{float(upside) * 100.0:+.1f}%".replace(".", ",")
        if pd.notna(upside) and np.isfinite(upside)
        else "n/d"
    )
    status = str(prow.get("Valuation Status", "N/D"))

    if status.startswith("SEM ALVO"):
        return (
            f"Preço atual {price}. Não há alvo validado: holding exige NAV/SOTP. "
            "Não é possível concluir barato/caro com o valuation atual."
        )

    method_text = _decision_method_values(symbol, method_audit)
    diagnostic = "n/d"
    if method_audit is not None and not method_audit.empty and symbol in method_audit.index:
        diagnostic = str(method_audit.loc[symbol].get("Leitura diagnóstica", "n/d"))

    return (
        f"Preço {price}; alvo final 12m {target}; diferença {upside_text}. "
        f"{method_text} Leitura dos métodos: {diagnostic}."
    )


def _decision_combined_conclusion(qrow, prow):
    """
    Conclusão direta derivada APENAS da combinação entre:
      - Classe de qualidade já existente; e
      - Valuation Status já existente.

    Não há novo limiar numérico.
    """
    quality_class = str(qrow.get("Classe de qualidade", "N/D")).strip()
    valuation_status = str(prow.get("Valuation Status", "N/D")).strip()

    high_quality = quality_class in {"EXCELENTE NO GRUPO", "FORTE NO GRUPO"}
    intermediate = quality_class == "INTERMEDIÁRIA NO GRUPO"
    below = quality_class == "ABAIXO DO GRUPO"

    if valuation_status.startswith("SEM ALVO"):
        return (
            "PREÇO NÃO CLASSIFICÁVEL — concluir NAV/SOTP antes de decidir entrada."
        )

    if high_quality and valuation_status.startswith("ATRATIVO"):
        return (
            "BOM ATIVO + PREÇO ATRATIVO — melhor combinação do Radar; "
            "candidato para aprofundar antes de eventual inclusão em carteira."
        )

    if high_quality and valuation_status.startswith("CARO"):
        return (
            "BOM ATIVO, MAS CARO AGORA — qualidade aprovada; preço não aprovado. "
            "Manter na watchlist e não priorizar entrada no preço atual."
        )

    if high_quality and (
        valuation_status.startswith("INCONCLUSIVO")
        or valuation_status.startswith("MISTO")
    ):
        return (
            "BOM ATIVO, MAS PREÇO NÃO CONFIRMADO — qualidade aprovada, valuation sem consenso. "
            "Manter na watchlist e não decidir entrada pelo alvo composto isolado."
        )

    if intermediate and valuation_status.startswith("ATRATIVO"):
        return (
            "PREÇO ATRATIVO, MAS QUALIDADE APENAS INTERMEDIÁRIA — não entrar só porque parece barato; "
            "qualidade não é prioritária no universo W1."
        )

    if intermediate and valuation_status.startswith("CARO"):
        return (
            "NÃO PRIORITÁRIO — qualidade intermediária e preço caro pelo modelo."
        )

    if intermediate:
        return (
            "NÃO PRIORITÁRIO AGORA — qualidade intermediária e preço sem confirmação suficiente."
        )

    if below:
        return (
            "NÃO PRIORITÁRIO PARA CARTEIRA — qualidade abaixo dos pares do grupo; "
            "o preço, isoladamente, não compensa essa leitura de qualidade no Radar."
        )

    return "INCONCLUSIVO — revisar manualmente o caso."


def _decision_action(qrow, prow):
    """Ação curta e coerente com a conclusão acima; sem criar ordem automática de compra/venda."""
    quality_class = str(qrow.get("Classe de qualidade", "N/D")).strip()
    valuation_status = str(prow.get("Valuation Status", "N/D")).strip()
    high_quality = quality_class in {"EXCELENTE NO GRUPO", "FORTE NO GRUPO"}

    if valuation_status.startswith("SEM ALVO"):
        return "Concluir NAV/SOTP; até lá, não usar preço-alvo para decisão."
    if high_quality and valuation_status.startswith("ATRATIVO"):
        return "Aprofundar riscos/tese do ativo; é o grupo com melhor combinação qualidade + preço."
    if high_quality and valuation_status.startswith("CARO"):
        return "Manter na watchlist; reavaliar quando a cotação cair e/ou os fundamentos elevarem o alvo."
    if high_quality:
        return "Manter na watchlist; esperar maior convergência entre os métodos antes de avaliar entrada."
    if quality_class == "INTERMEDIÁRIA NO GRUPO":
        return "Monitorar, mas não priorizar para carteira enquanto a qualidade relativa continuar intermediária."
    if quality_class == "ABAIXO DO GRUPO":
        return "Não priorizar para carteira; reavaliar somente se a qualidade fundamental melhorar nas próximas execuções."
    return "Revisar manualmente antes de decidir."


def build_asset_decision_table(
    quality_score_table,
    long_term_portfolio_radar,
    method_audit,
    assets,
):
    """
    Tabela FINAL recomendada para leitura diária — UMA LINHA POR ATIVO.

    Colunas:
      Ativo
      Bom ativo para carteira?
      Motivo da qualidade — números
      Está barato hoje?
      Motivo do preço — números
      Conclusão direta
      O que fazer
    """
    columns = [
        "Ativo",
        "Bom ativo para carteira?",
        "Motivo da qualidade — números",
        "Está barato hoje?",
        "Motivo do preço — números",
        "Conclusão direta",
        "O que fazer",
    ]

    if (
        quality_score_table is None
        or quality_score_table.empty
        or long_term_portfolio_radar is None
        or long_term_portfolio_radar.empty
    ):
        return pd.DataFrame(columns=columns)

    rows = []
    for symbol in assets.keys():
        if symbol not in quality_score_table.index:
            continue
        if symbol not in long_term_portfolio_radar.index:
            continue

        q = quality_score_table.loc[symbol]
        p = long_term_portfolio_radar.loc[symbol]

        rows.append({
            "Ativo": symbol,
            "Bom ativo para carteira?": _decision_quality_verdict(q),
            "Motivo da qualidade — números": _decision_quality_evidence(q),
            "Está barato hoje?": _decision_price_verdict(p),
            "Motivo do preço — números": _decision_price_evidence(symbol, p, method_audit),
            "Conclusão direta": _decision_combined_conclusion(q, p),
            "O que fazer": _decision_action(q, p),
        })

    return pd.DataFrame(rows, columns=columns)


def validate_asset_decision_table(
    decision_table,
    quality_score_table,
    long_term_portfolio_radar,
    assets,
):
    """Confirma cobertura integral e ausência de duplicação/alteração da base."""
    expected = [
        str(symbol)
        for symbol in assets.keys()
        if symbol in quality_score_table.index
        and symbol in long_term_portfolio_radar.index
    ]
    actual = (
        decision_table["Ativo"].astype(str).tolist()
        if decision_table is not None and not decision_table.empty
        else []
    )

    required_text = [
        "Bom ativo para carteira?",
        "Motivo da qualidade — números",
        "Está barato hoje?",
        "Motivo do preço — números",
        "Conclusão direta",
        "O que fazer",
    ]

    checks = {
        "mesmos_ativos": expected == actual,
        "mesma_quantidade": len(expected) == len(actual),
        "sem_duplicados": len(actual) == len(set(actual)),
        "textos_preenchidos": (
            True
            if decision_table is None or decision_table.empty
            else all(
                decision_table[col].astype(str).str.strip().ne("").all()
                for col in required_text
            )
        ),
    }
    checks["ok"] = all(checks.values())
    return checks


ASSET_DECISION_TABLE = build_asset_decision_table(
    QUALITY_SCORE_TABLE,
    LONG_TERM_PORTFOLIO_RADAR,
    METHOD_DISAGREEMENT_AUDIT,
    ASSETS,
)

_ASSET_DECISION_VALIDATION = validate_asset_decision_table(
    ASSET_DECISION_TABLE,
    QUALITY_SCORE_TABLE,
    LONG_TERM_PORTFOLIO_RADAR,
    ASSETS,
)


print("\n" + "=" * 160)
print("PAINEL FINAL POR ATIVO — É BOM PARA CARTEIRA? ESTÁ BARATO? POR QUÊ?")
print("=" * 160)
print(
    "USE ESTA TABELA COMO A LEITURA FINAL DO RADAR. Cada linha separa duas perguntas: "
    "(1) qualidade da empresa e (2) preço/valuation. As conclusões são sustentadas pelos números exibidos."
)
print(
    "'BOM ATIVO' = classe EXCELENTE/FORTE já calculada pelo Quality Score do grupo. "
    "'BARATO/CARO' = Valuation Status já calculado pelos quatro métodos. "
    "Nenhum limiar novo foi criado nesta seção."
)

if not ASSET_DECISION_TABLE.empty:
    display(
        ASSET_DECISION_TABLE.style.set_properties(
            subset=[
                "Bom ativo para carteira?",
                "Motivo da qualidade — números",
                "Está barato hoje?",
                "Motivo do preço — números",
                "Conclusão direta",
                "O que fazer",
            ],
            **{
                "white-space": "normal",
                "text-align": "left",
                "vertical-align": "top",
            }
        )
    )
else:
    print("Tabela final por ativo indisponível.")


print("\nLEITURA DIRETA DAS COMBINAÇÕES")
print("• BOM ATIVO + BARATO/ATRATIVO: melhor combinação do Radar; aprofundar a tese antes de eventual inclusão.")
print("• BOM ATIVO + CARO: empresa passa em qualidade, mas o preço atual não passa; manter na watchlist.")
print("• BOM ATIVO + PREÇO INCONCLUSIVO: qualidade passa, valuation não confirma entrada; esperar convergência.")
print("• QUALIDADE INTERMEDIÁRIA: não é prioridade estrutural, mesmo que o preço eventualmente pareça atrativo.")
print("• QUALIDADE ABAIXO DOS PARES: não priorizar para carteira até haver melhora fundamental nas próximas leituras.")
print("• NAV/SOTP PENDENTE: não concluir barato/caro antes do valuation adequado da holding.")


print("\nVALIDAÇÃO DO PAINEL FINAL POR ATIVO")
print(
    f"Mesmos ativos e mesma ordem do universo W1 : "
    f"{'OK' if _ASSET_DECISION_VALIDATION.get('mesmos_ativos') else 'ERRO'}"
)
print(
    f"Mesma quantidade de ativos                : "
    f"{'OK' if _ASSET_DECISION_VALIDATION.get('mesma_quantidade') else 'ERRO'}"
)
print(
    f"Sem ativos duplicados                     : "
    f"{'OK' if _ASSET_DECISION_VALIDATION.get('sem_duplicados') else 'ERRO'}"
)
print(
    f"Motivos e conclusões preenchidos           : "
    f"{'OK' if _ASSET_DECISION_VALIDATION.get('textos_preenchidos') else 'ERRO'}"
)
print("Valuation recalculado por esta tabela      : NÃO")
print("Quality Score recalculado                  : NÃO")
print("Confidence Score recalculado               : NÃO")
print("Status de Carteira alterado                : NÃO")
print("Pesos 50/20/20/10 alterados               : NÃO")

if not _ASSET_DECISION_VALIDATION.get("ok", False):
    raise AssertionError(
        "Falha na validação do Painel Final por Ativo: a camada de apresentação "
        "não preservou integralmente o universo W1."
    )

print("\nRADAR W1 — PAINEL FINAL POR ATIVO CONCLUÍDO.")
