import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import numpy as np

# ===============================================================
# CONFIGURAÇÕES DE PÁGINA E ESTILO GERAL
# ===============================================================
st.set_page_config(
    page_title="Acompanhamento KPI ScannMarket",
    page_icon="📊",
    layout="wide",
)

# CSS customizado para estilo executivo e ocupar toda a tela
st.markdown("""
    <style>
        /* Remove margens e padding extras */
        .block-container {
            padding-top: 2rem !important;  /* adiciona respiro no topo */
            padding-bottom: 1rem !important;
        }


        /* Header fixo com sombra leve */
        .header-container {
            background-color: white;
            position: sticky;
            top: 0;
            z-index: 999;
            padding: 0.8rem 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        /* Logo */
        .header-logo {
            height: 45px;
        }

        /* Caixa dos KPIs */
        .metric-card {
            background-color: white;
            padding: 1.2rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            text-align: center;
        }

        /* Títulos e textos */
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #054FE1;
        }

        .metric-label {
            font-size: 0.9rem;
            color: #666;
        }
    </style>
""", unsafe_allow_html=True)

# ===============================================================
# HEADER COM LOGO E FILTROS
# ===============================================================

import base64

def header_com_filtros(df):
    """Cria o header com logo da Scanntech e filtros no topo."""

    # --- Garantir que a coluna RESP_SM exista ---
    df_cols_upper = {c.upper().replace(".", "").replace(" ", "_"): c for c in df.columns}
    for key in df_cols_upper.keys():
        if "RESP_SM" in key or "RESPONSAVEL_SM" in key or "RESP_SM" in key.replace("_", ""):
            df = df.rename(columns={df_cols_upper[key]: "RESP_SM"})
            break

    # --- CSS visual do header ---
    st.markdown("""
        <style>
        .header-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background-color: #f8f9fa;
            padding: 0.8rem 1.2rem;
            border-radius: 12px;
            box-shadow: 0px 2px 6px rgba(0,0,0,0.08);
            margin-bottom: 0.8rem;
        }
        .header-left {
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 160px;
        }
        .header-title {
            flex: 1;
            text-align: center;
            font-size: 1.7rem;
            font-weight: 700;
            color: #054FE1;
            white-space: nowrap;
        }
        .header-right {
            width: 160px; /* Apenas para equilibrar o flex e forçar centralização real */
        }
        .header-logo {
            height: 42px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- LOGO local ---
    logo_path = "scanntech_logo.png"
    try:
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode("utf-8")

        logo_html = f"""
            <div class="header-container">
                <!-- COLUNA ESQUERDA (LOGO) -->
                <div class="header-left">
                    <img src="data:image/png;base64,{logo_base64}" 
                        alt="Scanntech Logo" width="140" class="header-logo">
                </div>
                <!-- COLUNA CENTRAL (TÍTULO CENTRALIZADO) -->
                <div class="header-title">
                    Acompanhamento KPI ScannMarket
                </div>
                <!-- COLUNA DIREITA (VAZIA PARA EQUILIBRAR) -->
                <div class="header-right"></div>
            </div>
        """

    except FileNotFoundError:
        logo_html = """
            <div class="header-container">
                <div class="header-left">
                    <div style="width:140px; height:40px; background:#ccc; text-align:center; line-height:40px;">
                        (sem logo)
                    </div>
                </div>
                <div class="header-title">
                    Acompanhamento KPI ScannMarket
                </div>
                <div class="header-right"></div>
            </div>
        """

    st.markdown(logo_html, unsafe_allow_html=True)


    # --- Filtros (4 colunas alinhadas) ---
    cols = st.columns([1, 1, 1, 1])
    bu_vals = ["Todos"] + sorted(df["BU"].dropna().unique().tolist())
    resp_vals = ["Todos"] + sorted(df["RESP_SM"].dropna().unique().tolist()) if "RESP_SM" in df.columns else ["Todos"]
    status_vals = ["Todos"] + sorted(df["STATUS"].dropna().unique().tolist()) if "STATUS" in df.columns else ["Todos"]
    tipo_vals = ["Todos"] + sorted(df["TIPO"].dropna().unique().tolist()) if "TIPO" in df.columns else ["Todos"]

    selected_bu = cols[0].selectbox("BU", bu_vals)
    selected_resp = cols[1].selectbox("Responsável SM", resp_vals)
    selected_status = cols[2].selectbox("Status", status_vals)
    selected_tipo = cols[3].selectbox("Tipo", tipo_vals)

    # --- Construir máscara de filtro ---
    mask = pd.Series(True, index=df.index)
    if selected_bu != "Todos":
        mask &= (df["BU"] == selected_bu)
    if selected_resp != "Todos":
        mask &= (df["RESP_SM"] == selected_resp)
    if selected_status != "Todos":
        mask &= (df["STATUS"] == selected_status)
    if selected_tipo != "Todos":
        mask &= (df["TIPO"] == selected_tipo)

    return mask



# ===============================   ================================
# FUNÇÕES DE KPI
# ===============================================================

def calcular_kpis(df):
    total = len(df)
    concluidas = len(df[df["STATUS"].str.lower().eq("concluída")])
    pendentes = len(df[df["STATUS"].str.lower() != "concluída"])

    # cálculo de taxa de resolução (% resolvidas sobre total)
    taxa_resolucao = (concluidas / total * 100) if total > 0 else 0

    return {
        "total": total,
        "concluidas": concluidas,
        "pendentes": pendentes,
        "taxa_resolucao": round(taxa_resolucao, 1),
    }

# ------------------------------------------------------------
# 2️⃣ KPIs - Cards principais (compatível com dict ou DataFrame)
# ------------------------------------------------------------
def mostrar_kpi_cards(data, df_fonte=None):
    """
    Exibe os principais KPIs em cards executivos com sombra suave.

    Parâmetros:
      - data: pd.DataFrame OR dict
          Se for pd.DataFrame, a função calcula os KPIs e também mês/semana vigentes.
          Se for dict (resumo), a função usa os valores disponíveis.
      - df_fonte: pd.DataFrame (opcional)
          Se 'data' for dict e você passar df_fonte, será usado df_fonte para cálculos adicionais.

    Observações:
      - Para os novos requisitos, usamos `df_fonte` (DataFrame filtrado) para:
         * SLA separado em linhas sem JIRA (principal) e com JIRA (subvalor)
         * Card 5: categorias únicas no mês e clientes/fabricantes únicos no mês
    """
    import kpi_calculos as kc
    import math
    import pandas as pd
    import numpy as np
    from datetime import datetime
    import streamlit as st

    # Determinar se 'data' é DataFrame (então usamos ele como fonte) ou dict (resumo)
    df_for_calc = None
    if isinstance(data, pd.DataFrame):
        df_for_calc = data.copy()
        try:
            resumo = kc.gerar_resumo_kpis(data)
        except Exception:
            resumo = {}
    else:
        resumo = data if isinstance(data, dict) else {}
        # se foi passado df_fonte (2º argumento), usamos ele para cálculos temporais
        if isinstance(df_fonte, pd.DataFrame):
            df_for_calc = df_fonte.copy()

    # --- Mapear keys possíveis para os nomes que usaremos aqui ---
    def pick(*keys):
        for k in keys:
            if k in resumo and resumo[k] is not None:
                return resumo[k]
        return None

    sla_medio = pick("SLA_MÉDIO_DIAS_UTEIS", "SLA_MEDIO_DIAS_UTEIS", "SLA_MÉDIO", "SLA_MEDIO", "sla_medio")
    taxa_res = pick("TAXA_RESOLUCAO_1_DEV", "TAXA_RESOLUCAO", "taxa_resolucao", "TAXA_RESOLUÇÃO_1_DEV")
    pct_reproc = pick("PCT_REPROCESSO_QUESTIONAMENTO", "PCT_REPROCESSO", "perc_reprocesso", "PCT_REPROCESSO_QUESTIONAMENTO")
    total_sol = pick("TOTAL_SOLICITACOES", "TOTAL", "total_solicitacoes")

    # Normalizar valores básicos (evitar erros)
    try:
        sla_val = float(sla_medio) if sla_medio is not None and not (isinstance(sla_medio, float) and math.isnan(sla_medio)) else float("nan")
    except Exception:
        sla_val = float("nan")

    try:
        taxa_val = float(taxa_res) if taxa_res is not None else None
        if taxa_val is not None and taxa_val > 1:
            taxa_val = taxa_val / 100.0
    except Exception:
        taxa_val = None

    try:
        pct_reproc_val = float(pct_reproc) if pct_reproc is not None else None
        if pct_reproc_val is not None and pct_reproc_val > 1:
            pct_reproc_val = pct_reproc_val / 100.0
    except Exception:
        pct_reproc_val = None

    try:
        total_val = int(total_sol) if total_sol is not None else 0
    except Exception:
        total_val = 0

    # --- Cálculos adicionais requeridos ---

    # 1) SLA separado: sem JIRA (principal) e com JIRA (subvalor)
    sla_sem_jira = None
    sla_com_jira = None
    if df_for_calc is not None and "SLA_DIAS_UTEIS" in df_for_calc.columns and "JIRA" in df_for_calc.columns:
        # garantir tipos e padronizar JIRA vazio como string vazia
        df_for_calc["JIRA_STR"] = df_for_calc["JIRA"].astype(str).fillna("").str.strip()
        # filtrar apenas linhas com SLA calculado (não NaN)
        df_sla = df_for_calc[df_for_calc["SLA_DIAS_UTEIS"].notna()].copy()

        if not df_sla.empty:
            sla_sem_jira_vals = df_sla[df_sla["JIRA_STR"] == ""]["SLA_DIAS_UTEIS"]
            sla_com_jira_vals = df_sla[df_sla["JIRA_STR"] != ""]["SLA_DIAS_UTEIS"]

            sla_sem_jira = float(sla_sem_jira_vals.mean()) if not sla_sem_jira_vals.empty else float("nan")
            sla_com_jira = float(sla_com_jira_vals.mean()) if not sla_com_jira_vals.empty else float("nan")

    # 2) Card 5: categorias únicas no mês e clientes/fabricantes únicos no mês
    total_categorias_mes = "-"
    total_clientes_mes = "-"
    if df_for_calc is not None and "DATA_SOLICITACAO" in df_for_calc.columns:
        df_dates = df_for_calc.copy()
        df_dates["DATA_SOLICITACAO"] = pd.to_datetime(df_dates["DATA_SOLICITACAO"], errors="coerce")
        hoje = datetime.now()
        mes_vig = df_dates[
            (df_dates["DATA_SOLICITACAO"].dt.month == hoje.month) &
            (df_dates["DATA_SOLICITACAO"].dt.year == hoje.year)
        ]
        if not mes_vig.empty:
            # categorias únicas
            if "CATEGORIA" in mes_vig.columns:
                total_categorias_mes = int(mes_vig["CATEGORIA"].dropna().nunique())
            else:
                total_categorias_mes = 0
            # clientes/fabricantes únicos - usar coluna CLIENTE se existir, senão usar PRODUTO
            cliente_col = "CLIENTE" if "CLIENTE" in mes_vig.columns else ("PRODUTO" if "PRODUTO" in mes_vig.columns else None)
            if cliente_col is not None:
                total_clientes_mes = int(mes_vig[cliente_col].dropna().nunique())
            else:
                total_clientes_mes = 0

    # --- Layout visual dos 5 cards ---
    col1, col2, col3, col4, col5 = st.columns(5)

    azul = "#054FE1"
    laranja = "#FF6E3B"

    card_style = (
        "background-color: white; padding: 1.1rem; border-radius: 12px;"
        "box-shadow: 0px 2px 8px rgba(0,0,0,0.08); text-align: center; min-height:110px; display:flex; flex-direction:column; justify-content:center;"
    )

    # Helpers de formatação
    def fmt_pct(x):
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "-"
        return f"{x:.1%}"

    def fmt_num(x, dec=1):
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "-"
        if isinstance(x, int):
            return f"{x}"
        return f"{x:.{dec}f}"

    # --- CARD 1: SLA dividido (sem JIRA principal / com JIRA sub) ---
    with col1:
        sla_main_display = fmt_num(sla_sem_jira, dec=1) if sla_sem_jira is not None else "-"
        sla_sub_display = fmt_num(sla_com_jira, dec=1) if sla_com_jira is not None else "-"
        st.markdown(f"""
        <div style="{card_style}">
            <div style="color: #555; font-size:0.9rem;">SLA Médio (sem JIRA)</div>
            <div style="font-size: 1.4rem; font-weight: 800; color:{azul};">
                {sla_main_display}
            </div>
            <div style="font-size:0.85rem; color:#666; margin-top:6px;">Com JIRA: {sla_sub_display}</div>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # CARD 2 — TAXA RESOLUÇÃO + % REPROCESSO (subvalor)
    # ============================================================
    with col2:
        taxa_display = fmt_pct(taxa_val)
        reproc_display = fmt_pct(pct_reproc_val)
        st.markdown(f"""
        <div style="{card_style}">
            <div style="color: #555; font-size:0.9rem;">Taxa de Resolução (1ª Devolutiva)</div>
            <div style="font-size: 1.4rem; font-weight: 700; color:{azul};">
                {taxa_display}
            </div>
            <div style="font-size:0.85rem; color:#666;">Reprocesso: {reproc_display}</div>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # CARD 3 — FABRICANTES ÚNICOS (JULHO+) + NOVOS NO MÊS
    # ============================================================
    fabricantes_unicos = "-"
    fabricantes_novos = "-"

    if df_for_calc is not None and "DATA_SOLICITACAO" in df_for_calc.columns and "CLIENTE" in df_for_calc.columns:

        df_aux = df_for_calc.copy()
        df_aux["DATA_SOLICITACAO"] = pd.to_datetime(df_aux["DATA_SOLICITACAO"], errors="coerce")

        hoje = datetime.now()

        # recorte: apenas dados de JULHO pra frente
        df_julho = df_aux[df_aux["DATA_SOLICITACAO"] >= datetime(hoje.year, 7, 1)]

        # fabricantes únicos desde julho
        fabricantes_unicos = df_julho["CLIENTE"].nunique()

        # fabricantes cuja 1ª ocorrência é neste mês
        primeira_ocorrencia = df_aux.sort_values("DATA_SOLICITACAO").groupby("CLIENTE").first().reset_index()
        fabricantes_novos = primeira_ocorrencia[
            (primeira_ocorrencia["DATA_SOLICITACAO"].dt.month == hoje.month) &
            (primeira_ocorrencia["DATA_SOLICITACAO"].dt.year == hoje.year)
        ]["CLIENTE"].nunique()

    with col3:
        st.markdown(f"""
        <div style="{card_style}">
            <div style="color:#555; font-size:0.9rem;">Fabricantes</div>
            <div style="font-size:1.4rem; font-weight:700; color:{laranja};">
                {fabricantes_unicos}
            </div>
            <div style="font-size:0.85rem; color:#666;">Novos no mês: {fabricantes_novos}</div>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # CARD 4 — CATEGORIAS ÚNICAS (JULHO+) + NOVAS NO MÊS
    # ============================================================
    categorias_unicas = "-"
    categorias_novas = "-"

    if df_for_calc is not None and "DATA_SOLICITACAO" in df_for_calc.columns and "CATEGORIA" in df_for_calc.columns:

        df_aux = df_for_calc.copy()
        df_aux["DATA_SOLICITACAO"] = pd.to_datetime(df_aux["DATA_SOLICITACAO"], errors="coerce")

        hoje = datetime.now()

        df_julho = df_aux[df_aux["DATA_SOLICITACAO"] >= datetime(hoje.year, 7, 1)]

        categorias_unicas = df_julho["CATEGORIA"].nunique()

        primeira_categoria = df_aux.sort_values("DATA_SOLICITACAO").groupby("CATEGORIA").first().reset_index()
        categorias_novas = primeira_categoria[
            (primeira_categoria["DATA_SOLICITACAO"].dt.month == hoje.month) &
            (primeira_categoria["DATA_SOLICITACAO"].dt.year == hoje.year)
        ]["CATEGORIA"].nunique()

    with col4:
        st.markdown(f"""
        <div style="{card_style}">
            <div style="color:#555; font-size:0.9rem;">Categorias</div>
            <div style="font-size:1.4rem; font-weight:700; color:{azul};">
                {categorias_unicas}
            </div>
            <div style="font-size:0.85rem; color:#666;">Novas no mês: {categorias_novas}</div>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # CARD 5 — TOTAL DESDE JUL/25 + MÊS ATUAL + MÉDIA MENSAL
    # ============================================================
    total_desde_jul = "-"
    total_mes_atual = "-"
    media_mensal = "-"

    if df_for_calc is not None and "DATA_SOLICITACAO" in df_for_calc.columns:

        df_aux = df_for_calc.copy()
        df_aux["DATA_SOLICITACAO"] = pd.to_datetime(df_aux["DATA_SOLICITACAO"], errors="coerce")

        # --- 1) Filtrar desde JULHO/2025 ---
        inicio = pd.Timestamp(2025, 7, 1)
        df_desde_jul = df_aux[df_aux["DATA_SOLICITACAO"] >= inicio]

        if not df_desde_jul.empty:
            # Total desde julho
            # total_desde_jul = str(len(df_desde_jul))
            total_desde_jul = str(int(df_desde_jul['QTDE_QUEST'].sum()))

            # --- 2) Total do mês atual ---
            hoje = datetime.now()
            df_mes = df_desde_jul[
                (df_desde_jul["DATA_SOLICITACAO"].dt.month == hoje.month) &
                (df_desde_jul["DATA_SOLICITACAO"].dt.year == hoje.year)
            ]
            # total_mes_atual = str(len(df_mes))
            total_mes_atual = str(int(df_mes['QTDE_QUEST'].sum()))

            # --- 3) Média mensal ---
            df_desde_jul["ANO_MES"] = df_desde_jul["DATA_SOLICITACAO"].dt.to_period("M")
            media_calc = df_desde_jul.groupby("ANO_MES").size().mean()
            media_mensal = f"{media_calc:.1f}"

    with col5:
        st.markdown(f"""
        <div style="{card_style}">
            <div style="color:#555; font-size:0.9rem;">Solicitações Totais</div>
            <div style="font-size:1.4rem; font-weight:700; color:{azul};">
                {total_desde_jul}
            </div>
            <div style="font-size:0.85rem; color:#666; margin-top:6px;">
                Mês atual: {total_mes_atual}
            </div>
            <div style="font-size:0.85rem; color:#666;">
                Média mensal: {media_mensal}
            </div>
        </div>
        """, unsafe_allow_html=True)


# ------------------------------------------------------------
# 3️⃣ Gráfico de Solicitações por BU (com rótulos e estilo Scanntech)
# ------------------------------------------------------------
# ---------------------------
# Helpers: detectar coluna de quantidade
# ---------------------------
def __detect_qty_col(df):
    """
    Retorna o nome da coluna que representa a quantidade de questionamentos,
    tentando cobrir variantes comuns no Excel: QTDE_QUEST, QTIA_QUEST, 'QTIA QUEST', etc.
    Retorna None se não encontrar.
    """
    if df is None:
        return None
    cols = [c.upper().replace(".", "_").replace(" ", "_") for c in df.columns]
    mapping = dict(zip(cols, df.columns))  # map normalized -> original
    candidates = ["QTDE_QUEST", "QTIA_QUEST", "QTDE_QUEST_JIRA", "QTDEQUEST", "QTIAQUEST", "QTIA_QUEST_JIRA"]
    for cand in candidates:
        if cand in mapping:
            return mapping[cand]
    # also try exact names
    for try_name in ["QTDE_QUEST", "QTIA QUEST", "QTIA_QUEST", "QTDE QUEST"]:
        if try_name in df.columns:
            return try_name
    return None

# ---------------------------
# Helper: detectar e formatar coluna de data em MES_ANO
# ---------------------------
def __add_mes_ano_col(df):
    """
    Detecta a coluna de data (buscando nomes como 'DATA', 'DT_SOLIC', 'DATA_SOLICITACAO', etc.)
    e cria uma coluna 'MES_ANO' no formato YYYY-MM.
    Retorna o DataFrame atualizado.
    """
    import pandas as pd

    if df is None or df.empty:
        return df

    data_cols = [c for c in df.columns if "DATA" in c.upper() or "DT" in c.upper()]
    if not data_cols:
        return df

    # Pega a primeira coluna de data encontrada
    col = data_cols[0]
    df = df.copy()
    try:
        df[col] = pd.to_datetime(df[col], errors="coerce")
        df["MES_ANO"] = df[col].dt.to_period("M").astype(str)
    except Exception:
        pass
    return df


# ---------------------------
# Grafico: Solicitações por BU (agrega por soma de quantidade quando disponível)
# ---------------------------
def grafico_linhas_por_bu(df, mask):
    import plotly.express as px
    import pandas as pd

    df_filtrado = df[mask].copy() if mask is not None else df.copy()
    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return

    # garantir MES_ANO
    df_filtrado = __add_mes_ano_col(df_filtrado)

    # criar coluna MES_ANO_DT tentando vários formatos
    mes = df_filtrado.get("MES_ANO")
    mes_dt = pd.to_datetime(mes, format="%Y-%m", errors="coerce")
    if mes_dt.isna().all():
        mes_dt = pd.to_datetime(mes, format="%m/%y", errors="coerce")
    if mes_dt.isna().all():
        # tentativa geral
        mes_dt = pd.to_datetime(mes, errors="coerce")

    # se ainda tudo NA, tentar basear no primeiro campo de data real
    if mes_dt.isna().all():
        date_cols = [c for c in df_filtrado.columns if ("DATA" in c.upper()) or ("DT" in c.upper())]
        if date_cols:
            mes_dt = pd.to_datetime(df_filtrado[date_cols[0]], errors="coerce").dt.to_period("M").dt.to_timestamp()
        else:
            mes_dt = pd.Series([pd.NaT]*len(df_filtrado), index=df_filtrado.index)

    df_filtrado["MES_ANO_DT"] = mes_dt

    # filtrar a partir de 2025-07-01
    df_filtrado = df_filtrado[df_filtrado["MES_ANO_DT"].notna()]  # excluir nulos
    df_filtrado = df_filtrado[df_filtrado["MES_ANO_DT"] >= pd.Timestamp(2025, 7, 1)]
    if df_filtrado.empty:
        st.info("Não há dados a partir de jul/2025 para exibir.")
        return

    # preparar coluna MES_ANO formatada (YYYY-MM) para o eixo x
    df_filtrado["MES_ANO"] = df_filtrado["MES_ANO_DT"].dt.to_period("M").astype(str)

    qty_col = __detect_qty_col(df_filtrado)
    if qty_col:
        df_group = (
            df_filtrado.groupby(["MES_ANO_DT", "MES_ANO", "BU"], dropna=False)[qty_col]
            .sum()
            .reset_index()
            .rename(columns={qty_col: "Quantidade"})
        )
    else:
        df_group = (
            df_filtrado.groupby(["MES_ANO_DT", "MES_ANO", "BU"], dropna=False)
            .size()
            .reset_index(name="Quantidade")
        )

    df_group = df_group.sort_values("MES_ANO_DT")

    fig = px.line(
        df_group,
        x="MES_ANO",
        y="Quantidade",
        color="BU",
        markers=True,
        text="Quantidade",
        title="Evolução Mensal de Solicitações por BU",
        color_discrete_sequence=px.colors.qualitative.Safe,
    )

    fig.update_traces(
        line=dict(width=2),
        marker=dict(size=7),
        textposition="top center",
        texttemplate="%{text:,}",
    )

    fig.update_layout(
        title=dict(x=0.02, font=dict(size=16, color="#054FE1")),
        xaxis_title="Mês",
        yaxis_title="Quantidade de Questionamentos",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#333", size=12),
        margin=dict(t=50, b=80, l=30, r=30),
        height=380,
        legend=dict(title="BU", orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5),
    )

    st.markdown('<div class="graf-card">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# Grafico: Quantidade por TIPO (soma da coluna QTDE_QUEST quando existir)
# ---------------------------
def grafico_linhas_por_tipo(df, mask):
    import plotly.express as px
    import pandas as pd

    df_filtrado = df[mask].copy() if mask is not None else df.copy()
    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return

    df_filtrado = __add_mes_ano_col(df_filtrado)

    mes = df_filtrado.get("MES_ANO")
    mes_dt = pd.to_datetime(mes, format="%Y-%m", errors="coerce")
    if mes_dt.isna().all():
        mes_dt = pd.to_datetime(mes, format="%m/%y", errors="coerce")
    if mes_dt.isna().all():
        mes_dt = pd.to_datetime(mes, errors="coerce")

    if mes_dt.isna().all():
        date_cols = [c for c in df_filtrado.columns if ("DATA" in c.upper()) or ("DT" in c.upper())]
        if date_cols:
            mes_dt = pd.to_datetime(df_filtrado[date_cols[0]], errors="coerce").dt.to_period("M").dt.to_timestamp()
        else:
            mes_dt = pd.Series([pd.NaT]*len(df_filtrado), index=df_filtrado.index)

    df_filtrado["MES_ANO_DT"] = mes_dt
    df_filtrado = df_filtrado[df_filtrado["MES_ANO_DT"].notna()]
    df_filtrado = df_filtrado[df_filtrado["MES_ANO_DT"] >= pd.Timestamp(2025, 7, 1)]
    if df_filtrado.empty:
        st.info("Não há dados a partir de jul/2025 para exibir.")
        return

    df_filtrado["MES_ANO"] = df_filtrado["MES_ANO_DT"].dt.to_period("M").astype(str)

    qty_col = __detect_qty_col(df_filtrado)
    if qty_col:
        df_group = (
            df_filtrado.groupby(["MES_ANO_DT", "MES_ANO", "TIPO"], dropna=False)[qty_col]
            .sum()
            .reset_index()
            .rename(columns={qty_col: "Quantidade"})
        )
    else:
        df_group = (
            df_filtrado.groupby(["MES_ANO_DT", "MES_ANO", "TIPO"], dropna=False)
            .size()
            .reset_index(name="Quantidade")
        )

    df_group = df_group.sort_values("MES_ANO_DT")

    fig = px.line(
        df_group,
        x="MES_ANO",
        y="Quantidade",
        color="TIPO",
        markers=True,
        text="Quantidade",
        title="Evolução Mensal de Solicitações por Tipo",
        color_discrete_sequence=px.colors.qualitative.Vivid,
    )

    fig.update_traces(
        line=dict(width=2),
        marker=dict(size=7),
        textposition="top center",
        texttemplate="%{text:,}",
    )

    fig.update_layout(
        title=dict(x=0.02, font=dict(size=16, color="#054FE1")),
        xaxis_title="Mês",
        yaxis_title="Quantidade de Questionamentos",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#333", size=12),
        margin=dict(t=50, b=80, l=30, r=30),
        height=380,
        legend=dict(title="Tipo", orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5),
    )

    st.markdown('<div class="graf-card">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


def grafico_pizza_status(df, mask):
    """Gráfico de pizza mostrando proporção de status (Concluída x Pendente)."""
    df_filtrado = df[mask].copy()
    if df_filtrado.empty:
        st.info("Nenhum dado disponível para o gráfico de status.")
        return

    status_counts = df_filtrado["STATUS"].value_counts().reset_index()
    status_counts.columns = ["STATUS", "Quantidade"]

    fig = px.pie(
        status_counts,
        names="STATUS",
        values="Quantidade",
        title="<b>Distribuição por Status</b>",
        color_discrete_sequence=["#054FE1", "#FF6E3B"]
    )

    fig.update_layout(
        title=dict(x=0.02, font=dict(size=16, color="#054FE1")),
        margin=dict(t=45)
    )
    fig.update_traces(textposition="inside", textinfo="percent", textfont_size=14)
    st.plotly_chart(fig, use_container_width=True)

def tabela_detalhada(df, mask):
    """Exibe a tabela detalhada filtrada com estilo clean."""
    df_filtrado = df[mask].copy()
    if df_filtrado.empty:
        st.info("Nenhum registro encontrado para os filtros selecionados.")
        return

    st.markdown("### 📋 Tabela Detalhada")
    st.dataframe(
        df_filtrado.reset_index(drop=True),
        use_container_width=True,
        height=400,
    )



def grafico_sla_mensal(df, mask):

    df_filtrado = df[mask].copy()
    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return

    # --- Conversões de data ---
    df_filtrado["DATA_SOLICITACAO"] = pd.to_datetime(df_filtrado["DATA_SOLICITACAO"], errors="coerce")
    df_filtrado["DATA_CONCLUSAO"] = pd.to_datetime(df_filtrado["DATA_CONCLUSAO"], errors="coerce")

    # --- Calcular SLA em dias úteis ---
    df_filtrado["SLA_DIAS"] = df_filtrado.apply(
        lambda x: np.busday_count(x["DATA_SOLICITACAO"].date(), x["DATA_CONCLUSAO"].date())
        if pd.notna(x["DATA_SOLICITACAO"]) and pd.notna(x["DATA_CONCLUSAO"]) else np.nan,
        axis=1
    )

    # --- Criar coluna ANO_MES ---
    df_filtrado["ANO_MES"] = df_filtrado["DATA_SOLICITACAO"].dt.to_period("M").astype(str)

    # --- Filtrar a partir de julho/2025 ---
    df_filtrado = df_filtrado[df_filtrado["DATA_SOLICITACAO"] >= "2025-07-01"]
    if df_filtrado.empty:
        st.info("Não há dados a partir de jul/2025 para exibir.")
        return

    # --- Separar entre COM JIRA e SEM JIRA ---
    if "JIRA" in df_filtrado.columns:
    # forçar string, tirar espaços e normalizar lowercase
        jira_str = df_filtrado["JIRA"].astype(str).fillna("").str.strip().str.lower()

        # considerar como sem JIRA quando vazio ou representações textuais de NaN/None
        invalid_tokens = ["", "nan", "none", "na", "n/a", "null"]
        df_filtrado["Possui_JIRA"] = ~jira_str.isin(invalid_tokens)

        # opcional: remover casos em que o valor seja somente '-' ou '.' (ajuste se necessário)
        df_filtrado.loc[jira_str.isin(["-", "."]), "Possui_JIRA"] = False
    else:
        # se não houver coluna, marcar tudo como sem JIRA
        df_filtrado["Possui_JIRA"] = False

    # --- SLA médio por mês e tipo de solicitação ---
    df_sla = (
        df_filtrado.groupby(["ANO_MES", "Possui_JIRA"])
        .agg(SLA_MEDIO=("SLA_DIAS", "mean"))
        .reset_index()
    )

    # --- Quantidade de solicitações por mês ---
    df_qtde = (
        df_filtrado.groupby("ANO_MES")
        .agg(QTDE_SOLICITACOES=("JIRA", "count"))
        .reset_index()
    )

    # --- Gráfico combinado ---
    fig = go.Figure()

    # Linha 1 - SLA médio (Sem JIRA)
    df_sem_jira = df_sla[df_sla["Possui_JIRA"] == False]
    fig.add_trace(go.Scatter(
        x=df_sem_jira["ANO_MES"],
        y=df_sem_jira["SLA_MEDIO"],
        name="SLA Médio - Sem JIRA",
        mode="lines+markers+text",
        text=df_sem_jira["SLA_MEDIO"].round(1),
        textposition="top center",
        line=dict(color="#054FE1", width=3),
        yaxis="y1"
    ))

    # Linha 2 - SLA médio (Com JIRA)
    df_com_jira = df_sla[df_sla["Possui_JIRA"] == True]
    fig.add_trace(go.Scatter(
        x=df_com_jira["ANO_MES"],
        y=df_com_jira["SLA_MEDIO"],
        name="SLA Médio - Com JIRA",
        mode="lines+markers+text",
        text=df_com_jira["SLA_MEDIO"].round(1),
        textposition="top center",
        line=dict(color="#F39C12", width=3, dash="dot"),
        yaxis="y1"
    ))

    # Barra - Quantidade de Solicitações
    fig.add_trace(go.Bar(
        x=df_qtde["ANO_MES"],
        y=df_qtde["QTDE_SOLICITACOES"],
        name="Solicitações",
        marker_color="#FF6E3B",
        yaxis="y2",
        opacity=0.5,
        text=df_qtde["QTDE_SOLICITACOES"],
        textposition="outside",
        textfont=dict(size=14)
    ))

    # --- Layout duplo eixo ---
    fig.update_layout(
        title=dict(
            text="<b>Evolução Mensal: SLA Médio (Com e Sem JIRA) vs Quantidade de Solicitações</b>",
            x=0.02,
            font=dict(size=16, color="#054FE1")
        ),
        xaxis_title="Mês",
        yaxis=dict(
            title=dict(text="SLA (dias úteis)", font=dict(color="#054FE1")),
            tickfont=dict(color="#054FE1"),
        ),
        yaxis2=dict(
            title=dict(text="Qtd Solicitações", font=dict(color="#FF6E3B")),
            tickfont=dict(color="#FF6E3B"),
            overlaying="y",
            side="right"
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=70, b=80, l=40, r=40),
        height=460
    )



    # --- Exibir no Streamlit ---
    st.markdown('<div class="graf-card">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)



# ===============================================================
# FUNÇÃO PRINCIPAL DE DASHBOARD
# ===============================================================

def exibir_dashboard(df_tratada):
    st.markdown("<br>", unsafe_allow_html=True)

    mask = header_com_filtros(df_tratada)
    df_filtro = df_tratada[mask]

    # KPIs principais
    kpi = calcular_kpis(df_filtro)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📊 Visão Geral")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"<div class='metric-card'><div class='metric-value'>{kpi['total']}</div><div class='metric-label'>Solicitações Totais</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><div class='metric-value'>{kpi['concluidas']}</div><div class='metric-label'>Concluídas</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-card'><div class='metric-value'>{kpi['pendentes']}</div><div class='metric-label'>Pendentes</div></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='metric-card'><div class='metric-value'>{kpi['taxa_resolucao']}%</div><div class='metric-label'>Taxa de Resolução</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ===============================================================
    # GRÁFICO 1 - Solicitações por BU
    # ===============================================================
    st.markdown("### 🏢 Solicitações por BU")

    if not df_filtro.empty:
        solicitacoes_bu = df_filtro["BU"].value_counts().reset_index()
        solicitacoes_bu.columns = ["BU", "Quantidade"]

        fig_bu = px.bar(
            solicitacoes_bu,
            x="BU",
            y="Quantidade",
            text="Quantidade",
            color="BU",
            color_discrete_sequence=["#054FE1", "#FF6E3B", "#5C7AEA", "#FDBE8C"],
            title="<b>Distribuição de Solicitações por BU</b>"
        )
        fig_bu.update_traces(textposition="outside")
        fig_bu.update_layout(
            showlegend=False,
            title=dict(x=0.02, font=dict(size=16, color="#054FE1"))
        )

        st.plotly_chart(fig_bu, use_container_width=True)
    else:
        st.info("Nenhum dado encontrado para os filtros selecionados.")

    # ===============================================================
    # GRÁFICO 2 - SLA (média de dias de conclusão)
    # ===============================================================
    st.markdown("### ⏱️ Tempo Médio de SLA (em dias)")
    if "DATA_SOLICITAÇÃO" in df_filtro.columns and "DATA_CONCLUSÃO" in df_filtro.columns:
        df_filtro["DATA_SOLICITAÇÃO"] = pd.to_datetime(df_filtro["DATA_SOLICITAÇÃO"], errors="coerce")
        df_filtro["DATA_CONCLUSÃO"] = pd.to_datetime(df_filtro["DATA_CONCLUSÃO"], errors="coerce")
        df_filtro["SLA_DIAS"] = (df_filtro["DATA_CONCLUSÃO"] - df_filtro["DATA_SOLICITAÇÃO"]).dt.days

        sla_por_resp = df_filtro.groupby("RESP_SM")["SLA_DIAS"].mean().reset_index().dropna()
        fig_sla = px.bar(
            sla_por_resp,
            x="RESP_SM",
            y="SLA_DIAS",
            text="SLA_DIAS",
            color="RESP_SM",
            color_discrete_sequence=["#FF6E3B", "#054FE1"],
            title="Média de SLA por Responsável SM"
        )
        fig_sla.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_sla.update_layout(showlegend=False, title_x=0.3)
        st.plotly_chart(fig_sla, use_container_width=True)
    else:
        st.warning("Não há colunas de data suficientes para calcular SLA.")
