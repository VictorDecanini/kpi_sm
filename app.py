# ---------------------------
# Upload + comportamento topo
# ---------------------------
import streamlit as st
import pandas as pd
import io
import time

from processar_solicitacoes import processar_solicitacoes
import kpi_calculos as kpi_mod
import dashboard_view as dv

st.set_page_config(page_title="Acompanhamento KPI ScannMarket", layout="wide")

# containers / placeholders
upload_slot = st.empty()            # placeholder que vamos esvaziar após upload
dashboard_container = st.container()

# Se quisermos permitir recarregar novo arquivo, guardamos flag em session_state
if "reload_requested" not in st.session_state:
    st.session_state["reload_requested"] = False

# Renderizar o título + uploader dentro do placeholder (upload_slot)
with upload_slot.container():
    st.markdown("<h1 style='text-align:center; color:#054FE1; margin-bottom:0.2rem;'>Acompanhamento KPI ScannMarket</h1>", unsafe_allow_html=True)
    st.markdown("Suba um arquivo Excel com a aba **SOLICITAÇÕES** (cabeçalho na 2ª linha).")
    uploaded_file = st.file_uploader("Upload do arquivo Excel (.xlsx)", type=["xlsx"], key="uploader")

# Se não houver arquivo, parar a execução aqui (uploader visível)
if uploaded_file is None:
    st.info("Envie o arquivo Excel para iniciar o processamento.")
    st.stop()

# Se chegou aqui, já há um arquivo: mostrar pequeno spinner e limpar upload
with st.spinner("Processando dados..."):
    time.sleep(0.5)  # só para dar tempo do spinner aparecer

upload_slot.empty()
st.markdown("<script>window.scrollTo(0, 0);</script>", unsafe_allow_html=True)

# ---------------------------
# Dashboard (vai aparecer no topo após upload_slot.empty())
# ---------------------------
with dashboard_container:

    # leitura e tratamento
    try:
        df_raw = pd.read_excel(uploaded_file, sheet_name="SOLICITAÇÕES", header=1)
    except Exception as e:
        st.error(f"Erro ao ler a aba SOLICITAÇÕES: {e}")
        st.stop()

    df_tratada = processar_solicitacoes(df_raw)

    # filtros (isso desenha o header + filtros e retorna a máscara)
    mask = dv.header_com_filtros(df_tratada)

    # aplicar máscara e gerar KPIs
    df_filtrado = df_tratada[mask]
    kpis = kpi_mod.gerar_resumo_kpis(df_tratada, mask)

    # mostrar cards (passando df_filtrado para que os cards respeitem filtros)
    dv.mostrar_kpi_cards(kpis, df_filtrado)
    st.markdown("<br><hr style='border:0.5px solid #ddd;margin:10px 0;'><br>", unsafe_allow_html=True)

    # gráficos (usando df_tratada e mask como você já tinha)
    # Gráficos: BU + TIPO (lado a lado) e pizza à direita
    col_main, col_pizza = st.columns([2.5, 1])

    with col_main:
        subcol_bu, subcol_tipo = st.columns([1, 1])
        with subcol_bu:
            dv.grafico_linhas_por_bu(df_tratada, mask)
        with subcol_tipo:
            dv.grafico_linhas_por_tipo(df_tratada, mask)

    with col_pizza:
        dv.grafico_pizza_status(df_tratada, mask)


    dv.grafico_sla_mensal(df_tratada, mask)

    st.markdown("---")
    st.markdown("### Tabela detalhada")
    dv.tabela_detalhada(df_tratada, mask)

    # botão para baixar
    def gerar_excel_em_bytes(df_tratada):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_tratada.to_excel(writer, sheet_name="Solicitações Tratada", index=False)
            pivot = df_tratada.pivot_table(index=["BU","STATUS"], values="JIRA", aggfunc="count", fill_value=0).reset_index().rename(columns={"JIRA":"QTDE"})
            pivot.to_excel(writer, sheet_name="Base KPI", index=False)
            pd.DataFrame({"Placeholder":["Este espaço será usado para análises e dashboards."]}).to_excel(writer, sheet_name="Análises para Dashboard", index=False)
            pd.DataFrame({"Placeholder":["Aba Acompanhamento SM - modelos e gráficos serão gerados no Streamlit."]}).to_excel(writer, sheet_name="Acompanhamento SM", index=False)
        output.seek(0)
        return output

    excel_bytes = gerar_excel_em_bytes(df_tratada)
    st.download_button("Baixar Excel tratado (com abas)", data=excel_bytes, file_name="Solicitacoes_Tratada_e_Bases.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
