import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Banco Plata - Engineering Operations Dashboard", layout="wide")

# ==========================================
# 1. ЛОКАЛИЗАЦИЯ / LOCALIZATION DICTIONARY
# ==========================================
LANG_PACK = {
    "RU": {
        "title": "📊 Платформа анализа инженерной эффективности конвейера поставки",
        "sidebar_filters": "🎯 Фильтры конвейера",
        "filter_lang": "🌐 Выбор языка / Language:",
        "filter_squad": "Выбор Команды (Squad):",
        "filter_type": "Тип задачи (Issue Type):",
        "kpi_flow": "Эффективность потока (Flow Efficiency)",
        "kpi_active": "Активное время работы (Active Time)",
        "kpi_wait": "Время простоев в очередях (Wait Time)",
        "chart_wait_title": "⏳ Распределение времени ожидания по очередям",
        "chart_wait_x": "Статус очереди",
        "chart_wait_y": "Суммарный простой (часы)",
        "chart_squad_title": "👥 Сравнение эффективности команд",
        "chart_squad_x": "Команда",
        "chart_squad_y": "Эффективность (%)",
        "error_load": "Не удалось загрузить данные. Проверьте файлы в корневой папке. Ошибка:"
    },
    "ENG": {
        "title": "📊 Delivery Pipeline Engineering Operations & Flow Efficiency Dashboard",
        "sidebar_filters": "🎯 Pipeline Filters",
        "filter_lang": "🌐 Выбор языка / Language:",
        "filter_squad": "Select Team (Squad):",
        "filter_type": "Select Issue Type:",
        "kpi_flow": "Flow Efficiency",
        "kpi_active": "Active Time (Value Add)",
        "kpi_wait": "Wait Time (Waste / Queues)",
        "chart_wait_title": "⏳ Total Waste: Time Spent Waiting in Queues",
        "chart_wait_x": "Queue Status",
        "chart_wait_y": "Cumulative Delay (Hours)",
        "chart_squad_title": "👥 Team Performance & Flow Efficiency Comparison",
        "chart_squad_x": "Squad",
        "chart_squad_y": "Flow Efficiency (%)",
        "error_load": "Failed to load data. Please check root files. Error:"
    }
}

# ==========================================
# 2. ЗАГРУЗКА ДАННЫХ / DATA LOADING
# ==========================================
@st.cache_data
def load_data():
    users = pd.read_csv('users.csv')
    issues = pd.read_csv('issues.csv')
    changelogs = pd.read_csv('changelogs.csv')
    return users, issues, changelogs

try:
    df_users, df_issues, df_changelogs = load_data()
    
    # Объединение таблиц (left join)
    df_merged = df_changelogs.merge(df_issues, on='issue_id', how='left')
    df_merged = df_merged.merge(df_users, left_on='assignee_id', right_on='user_id', how='left')
    
    df_merged['squad'] = df_merged['squad'].fillna('Other')
    df_merged['issue_type'] = df_merged['issue_type'].fillna('Story')
    
    # ==========================================
    # 3. СЕКЦИЯ ФИЛЬТРОВ И ТУМБЛЕР ЯЗЫКА
    # ==========================================
    st.sidebar.header("⚙️ Settings & Filters")
    
    # Наш переключатель языка
    lang = st.sidebar.radio(LANG_PACK["RU"]["filter_lang"], options=["ENG", "RU"], index=0)
    T = LANG_PACK[lang] # Текущий языковой пакет
    
    st.sidebar.markdown("---")
    st.sidebar.subheader(T["sidebar_filters"])
    
    squad_options = sorted(list(df_merged['squad'].unique()))
    selected_squad = st.sidebar.multiselect(
        T["filter_squad"], 
        options=squad_options, 
        default=squad_options
    )
    
    type_options = sorted(list(df_merged['issue_type'].unique()))
    selected_type = st.sidebar.multiselect(
        T["filter_type"], 
        options=type_options, 
        default=type_options
    )
    
    # Фильтрация датасета
    df_filtered = df_merged[
        (df_merged['squad'].isin(selected_squad)) & 
        (df_merged['issue_type'].isin(selected_type))
    ]
    
    # Основной заголовок дашборда
    st.title(T["title"])
    st.markdown("---")
    
    # ==========================================
    # 4. РАСЧЕТЫ И KPI КАРТОЧКИ
    # ==========================================
    active_statuses = ['Analysis', 'In Progress', 'Code Review', 'QA In Progress']
    
    total_active = df_filtered[df_filtered['from_status'].isin(active_statuses)]['hours_spent'].sum()
    total_wait = df_filtered[~df_filtered['from_status'].isin(active_statuses)]['hours_spent'].sum()
    
    flow_efficiency = (total_active / (total_active + total_wait)) * 100 if (total_active + total_wait) > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric(T["kpi_flow"], f"{flow_efficiency:.2f}%")
    col2.metric(T["kpi_active"], f"{total_active:,.1f} h" if lang == "ENG" else f"{total_active:,.1f} ч")
    col3.metric(T["kpi_wait"], f"{total_wait:,.1f} h" if lang == "ENG" else f"{total_wait:,.1f} ч")
    
    st.markdown("---")
    
    # ==========================================
    # 5. СЕКЦИЯ ИНТЕРАКТИВНЫХ ГРАФИКОВ
    # ==========================================
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader(T["chart_wait_title"])
        wait_stages = ['Ready for Dev', 'Ready for Code Review', 'Ready for QA', 'Ready for Release']
        df_wait = df_filtered[df_filtered['from_status'].isin(wait_stages)]
        df_wait_grouped = df_wait.groupby('from_status')['hours_spent'].sum().reset_index()
        
        fig_bar = px.bar(
            df_wait_grouped, 
            x='from_status', 
            y='hours_spent',
            labels={'from_status': T["chart_wait_x"], 'hours_spent': T["chart_wait_y"]},
            color='from_status',
            color_discrete_sequence=px.colors.sequential.Oranges_r
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col_chart2:
        st.subheader(T["chart_squad_title"])
        squad_data = []
        for squad in selected_squad:
            df_sq = df_filtered[df_filtered['squad'] == squad]
            act = df_sq[df_sq['from_status'].isin(active_statuses)]['hours_spent'].sum()
            wt = df_sq[~df_sq['from_status'].isin(active_statuses)]['hours_spent'].sum()
            eff = (act / (act + wt)) * 100 if (act + wt) > 0 else 0
            squad_data.append({T["chart_squad_x"]: squad, T["chart_squad_y"]: round(eff, 2)})
            
        fig_squad = px.bar(
            pd.DataFrame(squad_data), 
            x=T["chart_squad_x"], 
            y=T["chart_squad_y"],
            range_y=[0, 100],
            color=T["chart_squad_y"],
            color_continuous_scale=px.colors.sequential.Viridis
        )
        st.plotly_chart(fig_squad, use_container_width=True)

except Exception as e:
    st.error(f"{LANG_PACK['RU']['error_load']} {e}")
