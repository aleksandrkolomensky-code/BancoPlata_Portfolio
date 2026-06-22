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
        "title": "📊 Платформа анализа инженерной эффективности конвейера",
        "sidebar_filters": "🎯 Фильтры конвейера",
        "filter_lang": "🌐 Выбор языка / Language:",
        "filter_squad": "Выбор Команды (Squad):",
        "filter_type": "Тип задачи (Issue Type):",
        "tab_kanban": "⏳ Kanban & Flow Efficiency",
        "tab_dora": "🚀 DORA Metrics",
        "kpi_flow": "Эффективность потока (Flow Efficiency)",
        "kpi_active": "Активное время работы (Active Time)",
        "kpi_wait": "Время простоев в очередях (Wait Time)",
        "chart_wait_title": "⏳ Распределение времени ожидания по очередям",
        "chart_wait_x": "Статус очереди",
        "chart_wait_y": "Суммарный простой (часы)",
        "chart_squad_title": "👥 Сравнение эффективности команд",
        "chart_squad_x": "Команда",
        "chart_squad_y": "Эффективность (%)",
        "dora_df": "Частота деплоев (Deployment Frequency)",
        "dora_lt": "Время изменений (Lead Time for Changes)",
        "dora_cfr": "Доля брака (Change Failure Rate)",
        "dora_mttr": "Время восстановления (Time to Restore)",
        "dora_days": "дней с релизами",
        "dora_rating": "Уровень команды:",
        "error_load": "Не удалось загрузить данные. Ошибка:"
    },
    "ENG": {
        "title": "📊 Delivery Pipeline Engineering Operations Dashboard",
        "sidebar_filters": "🎯 Pipeline Filters",
        "filter_lang": "🌐 Выбор языка / Language:",
        "filter_squad": "Select Team (Squad):",
        "filter_type": "Select Issue Type:",
        "tab_kanban": "⏳ Kanban & Flow Efficiency",
        "tab_dora": "🚀 DORA Metrics",
        "kpi_flow": "Flow Efficiency",
        "kpi_active": "Active Time (Value Add)",
        "kpi_wait": "Wait Time (Waste / Queues)",
        "chart_wait_title": "⏳ Total Waste: Time Spent Waiting in Queues",
        "chart_wait_x": "Queue Status",
        "chart_wait_y": "Cumulative Delay (Hours)",
        "chart_squad_title": "👥 Team Performance & Flow Efficiency Comparison",
        "chart_squad_x": "Squad",
        "chart_squad_y": "Flow Efficiency (%)",
        "dora_df": "Deployment Frequency",
        "dora_lt": "Lead Time for Changes",
        "dora_cfr": "Change Failure Rate",
        "dora_mttr": "Time to Restore Service",
        "dora_days": "days with deployments",
        "dora_rating": "Team Rating:",
        "error_load": "Failed to load data. Error:"
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
    
    # Жесткое приведение типов дат при чтении
    changelogs['changed_at'] = pd.to_datetime(changelogs['changed_at'])
    return users, issues, changelogs

try:
    df_users, df_issues, df_changelogs = load_data()
    
    # Объединяем витрину данных
    df_merged = df_changelogs.merge(df_issues, on='issue_id', how='left')
    df_merged = df_merged.merge(df_users, left_on='assignee_id', right_on='user_id', how='left')
    
    df_merged['squad'] = df_merged['squad'].fillna('Other')
    df_merged['issue_type'] = df_merged['issue_type'].fillna('Story')
    
    # Настройки боковой панели
    st.sidebar.header("⚙️ Settings & Filters")
    lang = st.sidebar.radio(LANG_PACK["RU"]["filter_lang"], options=["ENG", "RU"], index=0)
    T = LANG_PACK[lang]
    
    st.sidebar.markdown("---")
    st.sidebar.subheader(T["sidebar_filters"])
    
    squad_options = sorted(list(df_merged['squad'].unique()))
    selected_squad = st.sidebar.multiselect(T["filter_squad"], options=squad_options, default=squad_options)
    
    type_options = sorted(list(df_merged['issue_type'].unique()))
    selected_type = st.sidebar.multiselect(T["filter_type"], options=type_options, default=type_options)
    
    # Фильтруем данные на основе выбора пользователя
    df_filtered = df_merged[(df_merged['squad'].isin(selected_squad)) & (df_merged['issue_type'].isin(selected_type))].copy()
    
    st.title(T["title"])
    st.markdown("---")
    
    tab1, tab2 = st.tabs([T["tab_kanban"], T["tab_dora"]])
    
    # ==========================================
    # ВКЛАДКА 1: KANBAN & FLOW EFFICIENCY
    # ==========================================
    with tab1:
        active_statuses = ['Analysis', 'In Progress', 'Code Review', 'QA In Progress']
        total_active = df_filtered[df_filtered['from_status'].isin(active_statuses)]['hours_spent'].sum()
        total_wait = df_filtered[~df_filtered['from_status'].isin(active_statuses)]['hours_spent'].sum()
        flow_efficiency = (total_active / (total_active + total_wait)) * 100 if (total_active + total_wait) > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric(T["kpi_flow"], f"{flow_efficiency:.2f}%")
        col2.metric(T["kpi_active"], f"{total_active:,.1f} h" if lang == "ENG" else f"{total_active:,.1f} ч")
        col3.metric(T["kpi_wait"], f"{total_wait:,.1f} h" if lang == "ENG" else f"{total_wait:,.1f} ч")
        
        st.markdown("---")
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader(T["chart_wait_title"])
            wait_stages = ['Ready for Dev', 'Ready for Code Review', 'Ready for QA', 'Ready for Release']
            df_wait = df_filtered[df_filtered['from_status'].isin(wait_stages)]
            df_wait_grouped = df_wait.groupby('from_status')['hours_spent'].sum().reset_index()
            fig_bar = px.bar(df_wait_grouped, x='from_status', y='hours_spent', labels={'from_status': T["chart_wait_x"], 'hours_spent': T["chart_wait_y"]}, color='from_status', color_discrete_sequence=px.colors.sequential.Oranges_r)
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
            fig_squad = px.bar(pd.DataFrame(squad_data), x=T["chart_squad_x"], y=T["chart_squad_y"], range_y=[0, 100], color=T["chart_squad_y"], color_continuous_scale=px.colors.sequential.Viridis)
            st.plotly_chart(fig_squad, use_container_width=True)

    # ==========================================
    # ВКЛАДКА 2: DORA METRICS (СТАБИЛЬНЫЙ РАСЧЕТ)
    # ==========================================
    with tab2:
        df_deployments = df_filtered[df_filtered['to_status'] == 'Done'].copy()
        
        if not df_deployments.empty:
            # Извлекаем чистую дату для группировки
            df_deployments['date'] = df_deployments['changed_at'].dt.date
            unique_deployment_days = df_deployments['date'].nunique()
            
            # 1. Бенчмарк Частоты деплоев
            if unique_deployment_days > 24: rating_df = "Elite 🌟"
            elif unique_deployment_days > 15: rating_df = "High 🟢"
            elif unique_deployment_days > 8: rating_df = "Medium 🟡"
            else: rating_df = "Low 🔴"
            
            # 2. Lead Time for Changes (Медиана полного цикла жизни задач)
            df_lead_time = df_filtered.groupby('issue_id')['hours_spent'].sum().reset_index()
            lead_time_median = float(df_lead_time['hours_spent'].median())
            
            if lead_time_median < 120: rating_lt = "Elite 🌟"
            elif lead_time_median < 250: rating_lt = "High 🟢"
            else: rating_lt = "Medium 🟡"
            
            # 3. Change Failure Rate (Процент сбойных релизов, где застряли на QA / релизе)
            total_deploys = len(df_deployments)
            failed_issues = df_filtered[(df_filtered['from_status'].isin(['QA In Progress', 'Ready for Release'])) & (df_filtered['hours_spent'] > 35.0)]['issue_id'].nunique()
            failed_deploys = min(failed_issues, total_deploys)
            cfr_value = (failed_deploys / total_deploys * 100) if total_deploys > 0 else 0.0
            
            if cfr_value < 15.0: rating_cfr = "Elite 🌟"
            elif cfr_value < 25.0: rating_cfr = "High 🟢"
            else: rating_cfr = "Medium/Low 🔴"
            
            # 4. Time to Restore Service (MTTR по багам)
            df_bugs = df_filtered[df_filtered['issue_type'] == 'Bug'].groupby('issue_id')['hours_spent'].sum().reset_index()
            if not df_bugs.empty:
                mttr_median = float(df_bugs['hours_spent'].median())
                rating_mttr = "Elite 🌟" if mttr_median < 48 else "High 🟢"
            else:
                mttr_median = 0.0
                rating_mttr = "N/A"
        else:
            unique_deployment_days = 0
            lead_time_median = 0.0
            cfr_value = 0.0
            mttr_median = 0.0
            rating_df = rating_lt = rating_cfr = rating_mttr = "N/A"
            
        row1_col1, row1_col2 = st.columns(2)
        row2_col1, row2_col2 = st.columns(2)
        
        with row1_col1:
            st.metric(T["dora_df"], f"{unique_deployment_days} {T['dora_days']}")
            st.markdown(f"**{T['dora_rating']}** `{rating_df}`")
            
        with row1_col2:
            st.metric(T["dora_lt"], f"{lead_time_median:.1f} h" if lang == "ENG" else f"{lead_time_median:.1f} ч")
            st.markdown(f"**{T['dora_rating']}** `{rating_lt}`")
            
        st.markdown("---")
        
        with row2_col1:
            st.metric(T["dora_cfr"], f"{cfr_value:.2f}%")
            st.markdown(f"**{T['dora_rating']}** `{rating_cfr}`")
            
        with row2_col2:
            st.metric(T["dora_mttr"], f"{mttr_median:.1f} h" if lang == "ENG" else f"{mttr_median:.1f} ч")
            st.markdown(f"**{T['dora_rating']}** `{rating_mttr}`")
            
        st.markdown("---")
        
        if not df_deployments.empty:
            st.subheader("📈" + (" Deployment Activity Timeline" if lang == "ENG" else " Динамика релизов по дням"))
            df_timeline = df_deployments.groupby('date').size().reset_index(name='Deployments Count')
            df_timeline = df_timeline.sort_values(by='date')
            
            fig_line = px.line(df_timeline, x='date', y='Deployments Count', labels={'date': 'Date', 'Deployments Count': 'Releases Count'}, color_discrete_sequence=['#228B22'])
            st.plotly_chart(fig_line, use_container_width=True)

except Exception as e:
    st.error(f"{LANG_PACK['RU']['error_load']} {e}")
