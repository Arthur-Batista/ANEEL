import streamlit as st
import pandas as pd
import sqlite3
import os


st.set_page_config(layout="wide")

DB_PATH = "data/aneel.db"

# --------------------------
# Garantir índices no SQLite
# --------------------------
def ensure_indexes():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_uf ON reclamacoes(uf)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ano ON reclamacoes(ano)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mes ON reclamacoes(mes)")
    conn.commit()
    conn.close()

ensure_indexes()

# --------------------------
# Função para carregar dados
# --------------------------
@st.cache_data
@st.cache_data
def load_data(uf: str):
    conn = sqlite3.connect(DB_PATH)

    if uf != "Todos":
        query = f"""
        SELECT uf, municipio, canal_atendimento, qtd_reclamacoes_recebidas, 
               qtd_reclamacoes_procedentes, prazo_solucao, data_registro
        FROM reclamacoes
        WHERE uf = '{uf}'
        """
    else:
        query = """
        SELECT uf, municipio, canal_atendimento, qtd_reclamacoes_recebidas, 
               qtd_reclamacoes_procedentes, prazo_solucao, data_registro
        FROM reclamacoes
        """

    df = pd.read_sql(query, conn)
    conn.close()

    # Converter data_registro para datetime
    df["data_registro"] = pd.to_datetime(df["data_registro"], errors="coerce")

    # Criar colunas derivadas
    df["ano"] = df["data_registro"].dt.year
    df["mes"] = df["data_registro"].dt.month

    # Tratamento da coluna prazo_solucao
    mascara = df['prazo_solucao'].astype(str).str.startswith(',', na=False)
    df.loc[mascara, 'prazo_solucao'] = '0' + df.loc[mascara, 'prazo_solucao']
    df["prazo_solucao"] = df["prazo_solucao"].astype(str).str.replace(",", ".")
    df["prazo_solucao"] = pd.to_numeric(df["prazo_solucao"], errors='coerce')

    return df


# --------------------------
# Interface do Streamlit
# --------------------------
st.title("📊 Dashboard Reclamações ANEEL 2024")
st.markdown("Análise interativa das reclamações registradas por distribuidoras de energia no Brasil.")

# Filtro UF
ufs = ["Todos"] + sorted(pd.read_sql("SELECT DISTINCT uf FROM reclamacoes", sqlite3.connect(DB_PATH))["uf"].tolist())
uf_selected = st.sidebar.selectbox("Selecione o estado", ufs)

# Carregar dados filtrados (cacheado)
df = load_data(uf_selected)

if uf_selected == "Todos":
    with st.container(border=True):
        col_kpis, col_graficos = st.columns([2, 8])
        with col_kpis:
        # Cards KPI
            # col1, col2, col3 = st.columns([5, 2, 3])
            st.metric("Total Reclamações", f"{df['qtd_reclamacoes_recebidas'].sum():,}".replace(",", "."))
            st.metric("Procedentes (%)", f"{(df['qtd_reclamacoes_procedentes'].sum() / df['qtd_reclamacoes_recebidas'].sum())*100:.2f}%")
            st.metric("Prazo Médio Solução", f"{df['prazo_solucao'].mean():.1f} dias")

        with col_graficos:

            # Gráfico 1 — Reclamações por UF
            if uf_selected == "Todos":
                df_estado = df.groupby('uf')['qtd_reclamacoes_recebidas'].sum().reset_index()
                st.bar_chart(df_estado.set_index("uf"))
else:
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Reclamações", f"{df['qtd_reclamacoes_recebidas'].sum():,}".replace(",", "."))
        col2.metric("Procedentes (%)", f"{(df['qtd_reclamacoes_procedentes'].sum() / df['qtd_reclamacoes_recebidas'].sum())*100:.2f}%")
        col3.metric("Prazo Médio Solução", f"{df['prazo_solucao'].mean():.1f} dias")

st.write("")
st.write("")
# Gráfico 2 — Top 10 municípios
df_mun = df.groupby("municipio")["qtd_reclamacoes_recebidas"].sum().nlargest(10).reset_index()

col_mun, col_canal = st.columns(2)

with col_mun:
    with st.container(border=True):
        st.write("### 🏙 Top 10 Municípios com mais Reclamações")
        st.table(df_mun)
with col_canal:
    with st.container(border=True):
        # Gráfico 3 — Distribuição por canal
        df_canal = df["canal_atendimento"].value_counts().reset_index()
        df_canal.columns = ["Canal", "Qtd"]
        st.write("### 📞 Reclamações por Canal de Atendimento")
        st.bar_chart(df_canal.set_index("Canal"))

st.write("")
st.write("")

with st.container(border=True):
    st.write("### 📈 Evolução Mensal de Reclamações")
# ----------- Evolução Temporal  ---------------

    df_mes = df.groupby(['ano','mes'])['qtd_reclamacoes_recebidas'].sum().reset_index()
    df_mes['data'] = pd.to_datetime(df_mes['ano'].astype(str) + '-' + df_mes['mes'].astype(str) + '-01')
    st.line_chart(df_mes.set_index("data")["qtd_reclamacoes_recebidas"])
