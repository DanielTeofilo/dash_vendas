import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Painel de Vendas (2018–2023)", layout="wide")

# ----- 1) Leitura e preparação dos dados -----

@st.cache_data
def load_data():
    try:
        # Carregando o arquivo CSV
        # O arquivo está no mesmo diretório, conforme contexto do usuário
        df = pd.read_csv("vendas2018_2023.csv")
        
        # Convertendo data_venda para datetime
        df['data_venda'] = pd.to_datetime(df['data_venda'])
        
        # Criando colunas derivadas
        df['ano'] = df['data_venda'].dt.year
        df['mes'] = df['data_venda'].dt.month
        # Formatando mês_ano como AAAA-MM para ordenação correta em gráficos
        df['mes_ano'] = df['data_venda'].dt.to_period('M').astype(str)
        
        # Cálculos financeiros
        df['faturamento'] = df['quantidade'] * df['valor_venda']
        df['custo_total'] = df['quantidade'] * df['valor_custo']
        df['lucro'] = df['faturamento'] - df['custo_total']
        
        # Margem % (tratando divisão por zero)
        df['margem_pct'] = df.apply(
            lambda x: (x['lucro'] / x['faturamento']) if x['faturamento'] != 0 else 0.0, 
            axis=1
        )
        
        # Garantindo tipos numéricos
        cols_num = ['quantidade', 'valor_venda', 'valor_custo', 'faturamento', 'custo_total', 'lucro', 'margem_pct']
        for col in cols_num:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df.sort_values('data_venda')
    except FileNotFoundError:
        st.error("Arquivo 'vendas2018_2023.csv' não encontrado. Verifique se ele está na mesma pasta do app.py.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# Carregar dados iniciais
df_raw = load_data()

if df_raw.empty:
    st.stop()

# ----- 2) Filtros (Sidebar) -----
st.sidebar.header("Filtros")

# Filtro de Período
min_date = df_raw['data_venda'].min().date()
max_date = df_raw['data_venda'].max().date()

start_date = st.sidebar.date_input("Data Inicial", min_date, min_value=min_date, max_value=max_date, format="DD/MM/YYYY")
end_date = st.sidebar.date_input("Data Final", max_date, min_value=min_date, max_value=max_date, format="DD/MM/YYYY")

# Se o usuário selecionar apenas uma data, o date_input pode retornar apenas um objeto date, não uma tupla
# Mas aqui deixamos separado start e end para garantir robustez.

# Filtros Multiselect
# Pré-ordenar valores únicos para facilitar busca
all_years = sorted(df_raw['ano'].unique())
all_cats = sorted(df_raw['categoria'].unique())
all_sellers = sorted(df_raw['vendedor'].unique())
all_suppliers = sorted(df_raw['fornecedor'].unique())

selected_years = st.sidebar.multiselect("Ano", all_years, default=all_years)
selected_cats = st.sidebar.multiselect("Categoria", all_cats, default=all_cats)
selected_sellers = st.sidebar.multiselect("Vendedor", all_sellers, default=all_sellers)
selected_suppliers = st.sidebar.multiselect("Fornecedor", all_suppliers, default=all_suppliers)

# Filtro de Produto (Selectbox ou Multiselect)
# Como podem ser muitos, vamos usar multiselect vazio = todos
all_products = sorted(df_raw['produto'].unique())
selected_products = st.sidebar.multiselect("Produto (Deixe vazio para todos)", all_products)

# Filtro de Cliente (Texto)
client_search = st.sidebar.text_input("Buscar Cliente (contém)")

# --- Aplicar Filtros ---
# Filtro de data
mask_date = (df_raw['data_venda'].dt.date >= start_date) & (df_raw['data_venda'].dt.date <= end_date)
df_filtered = df_raw.loc[mask_date]

# Filtros categóricos
if selected_years:
    df_filtered = df_filtered[df_filtered['ano'].isin(selected_years)]

if selected_cats:
    df_filtered = df_filtered[df_filtered['categoria'].isin(selected_cats)]

if selected_sellers:
    df_filtered = df_filtered[df_filtered['vendedor'].isin(selected_sellers)]

if selected_suppliers:
    df_filtered = df_filtered[df_filtered['fornecedor'].isin(selected_suppliers)]

if selected_products:
    df_filtered = df_filtered[df_filtered['produto'].isin(selected_products)]

if client_search:
    df_filtered = df_filtered[df_filtered['cliente'].str.contains(client_search, case=False, na=False)]


# Título Principal
st.title("Painel de Vendas (2018–2023)")

# Verificar se sobrou dados
if df_filtered.empty:
    st.warning("Nenhum dado encontrado com os filtros selecionados.")
    st.stop()

# ----- 3) Cards de Métricas -----
st.markdown("### Métricas Gerais")

total_faturamento = df_filtered['faturamento'].sum()
total_lucro = df_filtered['lucro'].sum()
margem_global = (total_lucro / total_faturamento) if total_faturamento > 0 else 0
total_qtd = df_filtered['quantidade'].sum()
num_vendas = len(df_filtered)
ticket_medio = (total_faturamento / num_vendas) if num_vendas > 0 else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Faturamento Total", f"R$ {total_faturamento:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
c2.metric("Lucro Total", f"R$ {total_lucro:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
c3.metric("Margem Global", f"{margem_global:.1%}")
c4.metric("Qtd. Vendida", f"{total_qtd:,}".replace(",", "."))
c5.metric("Nº Vendas", f"{num_vendas:,}".replace(",", "."))
c6.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.markdown("---")

# ----- 4) Gráficos (Análises) -----
st.subheader("Análises Gráficas")

# Funções auxiliares para gráficos
def format_currency(val):
    return f"R$ {val:,.2f}"

# Layout de colunas para gráficos
g_col1, g_col2 = st.columns(2)

with g_col1:
    # (1) Linha: Faturamento por mês_ano
    st.markdown("#### Faturamento por Mês")
    fat_por_mes = df_filtered.groupby('mes_ano')['faturamento'].sum().reset_index().sort_values('mes_ano')
    fig1 = px.line(fat_por_mes, x='mes_ano', y='faturamento', markers=True, 
                   labels={'mes_ano': 'Mês/Ano', 'faturamento': 'Faturamento (R$)'})
    st.plotly_chart(fig1, use_container_width=True)
    
    # (3) Barras: Top 10 categorias por faturamento
    st.markdown("#### Top 10 Categorias (Faturamento)")
    fat_por_cat = df_filtered.groupby('categoria')['faturamento'].sum().reset_index().sort_values('faturamento', ascending=False).head(10)
    fig3 = px.bar(fat_por_cat, x='faturamento', y='categoria', orientation='h', text_auto='.2s',
                  labels={'faturamento': 'Faturamento', 'categoria': 'Categoria'})
    fig3.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig3, use_container_width=True)
    
    # (5) Treemap: Top 10 vendedores por faturamento
    st.markdown("#### Top 10 Vendedores (Faturamento)")
    fat_por_vend = df_filtered.groupby('vendedor')['faturamento'].sum().reset_index().sort_values('faturamento', ascending=False).head(10)
    fig5 = px.treemap(fat_por_vend, path=['vendedor'], values='faturamento',
                      labels={'faturamento': 'Faturamento', 'vendedor': 'Vendedor'})
    st.plotly_chart(fig5, use_container_width=True)

    # (7) Pizza: Participação do lucro por categoria (ou fornecedor)
    # Vamos usar Categoria como padrão
    st.markdown("#### Distribuição de Lucro por Categoria")
    lucro_por_cat = df_filtered.groupby('categoria')['lucro'].sum().reset_index()
    # Se houver lucro negativo em alguma categoria, pizza pode ficar estranha, mas plotly lida ou normaliza.
    # Vamos filtrar lucros positivos para evitar erro visual grave na pizza ou usar bar se tiver negativo
    if (lucro_por_cat['lucro'] < 0).any():
        st.warning("Existem categorias com lucro negativo, exibindo gráfico de barras.")
        fig7 = px.bar(lucro_por_cat, x='categoria', y='lucro')
    else:
        fig7 = px.pie(lucro_por_cat, names='categoria', values='lucro', hole=0.0)
    st.plotly_chart(fig7, use_container_width=True)

with g_col2:
    # (2) Linha: Lucro por mês_ano
    st.markdown("#### Lucro por Mês")
    lucro_por_mes = df_filtered.groupby('mes_ano')['lucro'].sum().reset_index().sort_values('mes_ano')
    fig2 = px.line(lucro_por_mes, x='mes_ano', y='lucro', markers=True, color_discrete_sequence=['green'],
                   labels={'mes_ano': 'Mês/Ano', 'lucro': 'Lucro (R$)'})
    st.plotly_chart(fig2, use_container_width=True)

    # (4) Rosca: Participação do faturamento por categoria
    st.markdown("#### Share Faturamento por Categoria")
    # Agrupamento já feito em fat_por_cat, mas aqui queremos de todas as categorias, não só top 10?
    # O pedido diz "Participação ... por categoria". Se forem muitas, fica ruim. Vamos mostrar as Top 10 + Outros se necessário.
    # Simplificando: usar as mesmas do dataframe completo filtrado
    fat_cat_share = df_filtered.groupby('categoria')['faturamento'].sum().reset_index()
    fig4 = px.pie(fat_cat_share, names='categoria', values='faturamento', hole=0.5)
    st.plotly_chart(fig4, use_container_width=True)

    # (6) Barras: Top 10 produtos por faturamento
    st.markdown("#### Top 10 Produtos (Faturamento)")
    fat_por_prod = df_filtered.groupby('produto')['faturamento'].sum().reset_index().sort_values('faturamento', ascending=False).head(10)
    fig6 = px.bar(fat_por_prod, x='faturamento', y='produto', orientation='h',
                  labels={'faturamento': 'Faturamento', 'produto': 'Produto'})
    fig6.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig6, use_container_width=True)

    # (8) Barras Empilhadas: Faturamento por ano e categoria
    st.markdown("#### Comparação Anual por Categoria")
    fat_ano_cat = df_filtered.groupby(['ano', 'categoria'])['faturamento'].sum().reset_index()
    fig8 = px.bar(fat_ano_cat, x='ano', y='faturamento', color='categoria', 
                  labels={'ano': 'Ano', 'faturamento': 'Faturamento'}, barmode='stack')
    # Forçar eixo X a mostrar apenas anos inteiros se forem poucos
    fig8.update_xaxes(dtick="M12") 
    st.plotly_chart(fig8, use_container_width=True)

st.markdown("---")

# ----- 5) Tabela Detalhada -----
st.subheader("Base de Dados Detalhada")
cols_view = ['data_venda', 'cliente', 'vendedor', 'produto', 'categoria', 'fornecedor', 'quantidade', 'valor_venda', 'valor_custo', 'faturamento', 'lucro', 'margem_pct']
df_display = df_filtered[cols_view].copy()

# Formatando para exibição (apenas visual, mas dataframe pandas st mostra bem numbers)
# Vamos deixar o dataframe interativo nativo do Streamlit
st.dataframe(df_display, use_container_width=True)

# Botão de Download
csv = df_display.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Baixar Dados Filtrados (CSV)",
    data=csv,
    file_name='vendas_filtradas.csv',
    mime='text/csv',
)
