import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px

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
# --------------------------
# KPIs sempre visíveis
# --------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Total Reclamações", f"{df['qtd_reclamacoes_recebidas'].sum():,}".replace(",", "."))
col2.metric("Procedentes (%)", f"{(df['qtd_reclamacoes_procedentes'].sum() / df['qtd_reclamacoes_recebidas'].sum())*100:.2f}%")
col3.metric("Prazo Médio Solução", f"{df['prazo_solucao'].mean():.1f} dias")


# --------------------------
# Criando abas
# --------------------------
tab1, tab2, tab3 = st.tabs(["🌍 Estados / Mapa", "🏙 Municípios & Canais", "📈 Evolução Temporal"])

# -------- TAB 1: Estados e Mapa --------
with tab1:
    if uf_selected == "Todos":
        df_estado = df.groupby('uf')['qtd_reclamacoes_recebidas'].sum().reset_index()
        st.bar_chart(df_estado.set_index("uf"))

        # Mapa interativo
        df_estado = df.groupby("uf")["qtd_reclamacoes_recebidas"].sum().reset_index()
        fig = px.choropleth(
            df_estado,
            geojson="https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson",
            locations="uf",
            featureidkey="properties.sigla",
            color="qtd_reclamacoes_recebidas",
            color_continuous_scale="Reds",
            hover_name="uf",
            hover_data={'qtd_reclamacoes_recebidas': ':,2f'}
        )

        fig.update_layout(
            title_text='<b>Total de Reclamações por Estado</b>',
            title_x=0.5,
            height=600,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            geo=dict(
                bgcolor='rgba(0,0,0,0)',
                landcolor='rgb(40,40,40)',
                subunitcolor='white'
            ),
            margin=dict(l=0, r=0, t=40, b=0)
        )
        fig.update_geos(fitbounds="locations", visible=False)
        st.plotly_chart(fig, use_container_width=True)


# -------- TAB 2: Municípios e Canais --------
with tab2:
    col_mun, col_canal = st.columns(2)

    with col_mun:
        df_mun = df.groupby("municipio")["qtd_reclamacoes_recebidas"].sum().nlargest(10).reset_index()
        st.write("### 🏙 Top 10 Municípios com mais Reclamações")
        st.table(df_mun)

    with col_canal:
        df_canal = df["canal_atendimento"].value_counts().reset_index()
        df_canal.columns = ["Canal", "Qtd"]
        st.write("### 📞 Reclamações por Canal de Atendimento")
        st.bar_chart(df_canal.set_index("Canal"))


# -------- TAB 3: Evolução Temporal --------
with tab3:
        st.write("📅 Ver evolução mensal de reclamações")
        df_mes = df.groupby(['ano','mes'])['qtd_reclamacoes_recebidas'].sum().reset_index()
        df_mes['data'] = pd.to_datetime(df_mes['ano'].astype(str) + '-' + df_mes['mes'].astype(str) + '-01')
        st.line_chart(df_mes.set_index("data")["qtd_reclamacoes_recebidas"])