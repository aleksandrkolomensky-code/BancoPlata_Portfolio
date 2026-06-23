import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

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
        "sec_kanban": "⏳ Эффективность потока и Kanban-аналитика",
        "sec_dora": "🚀 Метрики DORA (скользящие 90 дней)",
        "kpi_flow": "Эффективность потока (Flow Efficiency)",
        "kpi_active": "Активное время работы (Active Time)",
        "kpi_wait": "Время простоев в очередях (Wait Time)",
        "chart_pie_title": "🍩 Распределение времени: Работа vs. Ожидание",
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
        "dora_days": "дней с релизами (за последние 90 дн.)",
        "dora_rating": "Уровень команды:",
        "heatmap_title": "🗺️ Сравнительная матрица зрелости DORA по всем командам (за последние 90 дн.)",
        "error_load": "Не удалось загрузить данные. Ошибка:"
    },
    "ENG": {
        "title": "📊 Delivery Pipeline Engineering Operations Dashboard",
        "sidebar_filters": "🎯 Pipeline Filters",
        "filter_lang": "🌐 Выбор языка / Language:",
        "filter_squad": "Select Team (Squad):",
        "filter_type": "Select Issue Type:",
        "sec_kanban": "⏳ Flow Efficiency & Kanban Analytics",
        "sec_dora": "🚀 DORA Metrics (Rolling 90 Days)",
        "kpi_flow": "Flow Efficiency",
        "kpi_active": "Active Time (Value Add)",
        "kpi_wait": "Wait Time (Waste / Queues)",
        "chart_pie_title": "🍩 Time Allocation: Active Work vs. Queues",
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
        "dora_days": "days with deployments (last 90 days)",
        "dora_rating": "Team Rating:",
        "heatmap_title": "🗺️ Cross-Team DORA Maturity Comparison Matrix (Last 90 Days)",
        "error_load": "Failed to load data. Error:"
    }
}

# ==========================================
# 2. ЗАГРУЗКА ДАННЫХ / DATA LOADING
# ==========================================
@st.cache_data
def load_data():
    users = pd.read_csv("users.csv")
    issues = pd.read_csv("issues.csv")
    changelogs = pd.read_csv("changelogs.csv")
    
    changelogs["changed_at"] = pd.to_datetime(changelogs["changed_at"])
    return users, issues, changelogs

try:
    df_users, df_issues, df_changelogs = load_data()
    
    df_merged = df_changelogs.merge(df_issues, on="issue_id", how="left")
    df_merged = df_merged.merge(df_users, left_on="assignee_id", right_on="user_id", how="left")
    
    df_merged["squad"] = df_merged["squad"].fillna("Other")
    df_merged["issue_type"] = df_merged["issue_type"].fillna("Story")
    
    st.sidebar.header("⚙️ Settings & Filters")
    lang = st.sidebar.radio(LANG_PACK["RU"]["filter_lang"], options=["ENG", "RU"], index=0)
    T = LANG_PACK[lang]
    
    st.sidebar.markdown("---")
    st.sidebar.subheader(T["sidebar_filters"])
    
    squad_options = sorted(list(df_merged["squad"].unique()))
    selected_squad = st.sidebar.multiselect(T["filter_squad"], options=squad_options, default=squad_options)
    
    type_options = sorted(list(df_merged["issue_type"].unique()))
    selected_type = st.sidebar.multiselect(T["filter_type"], options=type_options, default=type_options)
    
    # Фильтруем данные для Kanban-аналитики (оставляем полный годовой диапазон)
    df_filtered = df_merged[(df_merged["squad"].isin(selected_squad)) & (df_merged["issue_type"].isin(selected_type))].copy()
    
    st.title(T["title"])
    st.markdown("---")
    
    # ==========================================
    # РАЗДЕЛ 1: KANBAN & FLOW EFFICIENCY
    # ==========================================
    st.header(T["sec_kanban"])
    
    active_statuses = ["Analysis", "In Progress", "Code Review", "QA In Progress"]
    total_active = df_filtered[df_filtered["from_status"].isin(active_statuses)]["hours_spent"].sum()
    total_wait = df_filtered[~df_filtered["from_status"].isin(active_statuses)]["hours_spent"].sum()
    flow_efficiency = (total_active / (total_active + total_wait)) * 100 if (total_active + total_wait) > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric(T["kpi_flow"], f"{flow_efficiency:.2f}%")
    col2.metric(T["kpi_active"], f"{total_active:,.1f} h" if lang == "ENG" else f"{total_active:,.1f} ч")
    col3.metric(T["kpi_wait"], f"{total_wait:,.1f} h" if lang == "ENG" else f"{total_wait:,.1f} ч")
    
    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader(T["chart_pie_title"])
        pie_labels = [
            "Active Work (Value Add)" if lang == "ENG" else "Активная работа (Value Add)",
            "Queue Waiting (Waste)" if lang == "ENG" else "Ожидание в очередях (Waste)"
        ]
        df_pie = pd.DataFrame({
            "Category": pie_labels,
            "Hours": [total_active, total_wait]
        })
        fig_pie = px.pie(
            df_pie, 
            values="Hours", 
            names="Category", 
            hole=0.6,
            color="Category",
            color_discrete_map={
                pie_labels[0]: "#2ca02c", # Зеленый для полезной работы
                pie_labels[1]: "#d62728"  # Красный для потерь
            }
        )
        fig_pie.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_chart2:
        st.subheader(T["chart_wait_title"])
        wait_stages = ["Ready for Dev", "Ready for Code Review", "Ready for QA", "Ready for Release"]
        df_wait = df_filtered[df_filtered["from_status"].isin(wait_stages)]
        df_wait_grouped = df_wait.groupby("from_status")["hours_spent"].sum().reset_index()
        fig_bar = px.bar(df_wait_grouped, x="from_status", y="hours_spent", labels={"from_status": T["chart_wait_x"], "hours_spent": T["chart_wait_y"]}, color="from_status", color_discrete_sequence=px.colors.sequential.Oranges_r)
        st.plotly_chart(fig_bar, use_container_width=True)
        
    st.markdown("---")
    st.subheader(T["chart_squad_title"])
    squad_data = []
    for squad in selected_squad:
        df_sq = df_filtered[df_filtered["squad"] == squad]
        act = df_sq[df_sq["from_status"].isin(active_statuses)]["hours_spent"].sum()
        wt = df_sq[~df_sq["from_status"].isin(active_statuses)]["hours_spent"].sum()
        eff = (act / (act + wt)) * 100 if (act + wt) > 0 else 0
        squad_data.append({T["chart_squad_x"]: squad, T["chart_squad_y"]: round(eff, 2)})
    fig_squad = px.bar(pd.DataFrame(squad_data), x=T["chart_squad_x"], y=T["chart_squad_y"], range_y=[0, 100], color=T["chart_squad_y"], color_continuous_scale=px.colors.sequential.Viridis)
    st.plotly_chart(fig_squad, use_container_width=True)

    # ==========================================
    # РАЗДЕЛ 2: DORA METRICS (90 ДНЕЙ)
    # ==========================================
    st.markdown("---")
    st.header(T["sec_dora"])
    
    max_date = df_merged["changed_at"].max()
    dora_start_date = max_date - pd.Timedelta(days=90)
    
    # Игнорируем фильтр сущностей, берем сквады и строго фильтруем по 90-дневному периоду
    df_dora_filtered = df_merged[
        (df_merged["squad"].isin(selected_squad)) & 
        (df_merged["changed_at"] >= dora_start_date)
    ].copy()
    
    df_deployments = df_dora_filtered[df_dora_filtered["to_status"] == "Done"].copy()
    
    if not df_deployments.empty:
        df_deployments["date"] = df_deployments["changed_at"].dt.date
        unique_deployment_days = df_deployments["date"].nunique()
        
        # Корректируем пороги для Deployment Frequency под 90-дневное окно
        if unique_deployment_days > 60: rating_df = "Elite 🌟"
        elif unique_deployment_days > 30: rating_df = "High 🟢"
        elif unique_deployment_days > 10: rating_df = "Medium 🟡"
        else: rating_df = "Low 🔴"
        
        # Lead Time for Changes (берем все типы задач за 90 дней)
        df_lead_time = df_dora_filtered.groupby("issue_id")["hours_spent"].sum().reset_index()
        lead_time_median = float(df_lead_time["hours_spent"].median())
        
        if lead_time_median < 120: rating_lt = "Elite 🌟"
        elif lead_time_median < 250: rating_lt = "High 🟢"
        else: rating_lt = "Medium 🟡"
        
        # Классический CFR: Отношение Багов к Сториз за последние 90 дней
        total_stories = df_dora_filtered[df_dora_filtered["issue_type"] == "Story"]["issue_id"].nunique()
        total_bugs = df_dora_filtered[df_dora_filtered["issue_type"] == "Bug"]["issue_id"].nunique()
        
        if total_stories > 0:
            cfr_value = (total_bugs / total_stories) * 100
            cfr_value = min(cfr_value, 100.0)
        else:
            cfr_value = 0.0
        
        if cfr_value < 15.0: rating_cfr = "Elite 🌟"
        elif cfr_value < 30.0: rating_cfr = "High 🟢"
        else: rating_cfr = "Medium/Low 🔴"
        
        # Time to Restore Service (MTTR по багам за последние 90 дней)
        df_bugs_time = df_dora_filtered[df_dora_filtered["issue_type"] == "Bug"].groupby("issue_id")["hours_spent"].sum().reset_index()
        if not df_bugs_time.empty:
            mttr_median = float(df_bugs_time["hours_spent"].median())
            rating_mttr = "Elite 🌟" if mttr_median < 24 else ("High 🟢" if mttr_median < 48 else "Medium 🟡")
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
        st.subheader("📈" + (" Deployment Activity Timeline (Last 90 Days)" if lang == "ENG" else " Динамика релизов по дням (за последние 90 дн.)"))
        df_timeline = df_deployments.groupby("date").size().reset_index(name="Deployments Count")
        df_timeline = df_timeline.sort_values(by="date")
        
        fig_line = px.line(df_timeline, x="date", y="Deployments Count", labels={"date": "Date", "Deployments Count": "Releases Count"}, color_discrete_sequence=["#228B22"])
        st.plotly_chart(fig_line, use_container_width=True)

    # ==========================================
    # РАЗДЕЛ 3: ТЕПЛОВАЯ КАРТА (HEATMAP ЗА 90 ДНЕЙ)
    # ==========================================
    st.markdown("---")
    st.header(T["heatmap_title"])
    
    all_squads = sorted(list(df_merged["squad"].unique()))
    if "Other" in all_squads:
        all_squads.remove("Other")
        
    metrics_list = [T["dora_df"], T["dora_lt"], T["dora_cfr"], T["dora_mttr"]]
    
    z_values = []
    text_values = []
    
    for squad in all_squads:
        df_sq = df_merged[
            (df_merged["squad"] == squad) & 
            (df_merged["changed_at"] >= dora_start_date)
        ]
        df_sq_deploys = df_sq[df_sq["to_status"] == "Done"].copy()
        
        # Расчет DF
        sq_df = df_sq_deploys["changed_at"].dt.date.nunique()
        lvl_df = 4 if sq_df > 60 else (3 if sq_df > 30 else (2 if sq_df > 10 else 1))
        txt_df = f"{sq_df} d" if lang == "ENG" else f"{sq_df} дн"
        
        # Расчет LT
        df_sq_lt = df_sq.groupby("issue_id")["hours_spent"].sum().reset_index()
        sq_lt = float(df_sq_lt["hours_spent"].median()) if not df_sq_lt.empty else 0
        lvl_lt = 4 if sq_lt < 120 else (3 if sq_lt < 250 else 2)
        txt_lt = f"{sq_lt:.1f} h" if lang == "ENG" else f"{sq_lt:.1f} ч"
        
        # Расчет CFR
        sq_stories = df_sq[df_sq["issue_type"] == "Story"]["issue_id"].nunique()
        sq_bugs = df_sq[df_sq["issue_type"] == "Bug"]["issue_id"].nunique()
        sq_cfr = (sq_bugs / sq_stories * 100) if sq_stories > 0 else 0
        lvl_cfr = 4 if sq_cfr < 15.0 else (3 if sq_cfr < 30.0 else 1)
        txt_cfr = f"{sq_cfr:.1f}%"
        
        # Расчет MTTR
        df_sq_bugs = df_sq[df_sq["issue_type"] == "Bug"].groupby("issue_id")["hours_spent"].sum().reset_index()
        sq_mttr = float(df_sq_bugs["hours_spent"].median()) if not df_sq_bugs.empty else 0
        lvl_mttr = 4 if sq_mttr < 24 else (3 if sq_mttr < 48 else 2)
        txt_mttr = f"{sq_mttr:.1f} h" if lang == "ENG" else f"{sq_mttr:.1f} ч"
        
        z_values.append([lvl_df, lvl_lt, lvl_cfr, lvl_mttr])
        text_values.append([txt_df, txt_lt, txt_cfr, txt_mttr])
        
    fig_heat = go.Figure(data=go.Heatmap(
        z=z_values,
        x=metrics_list,
        y=all_squads,
        text=text_values,
        texttemplate="%{text}",
        textfont={"size": 14, "weight": "bold"},
        colorscale=[[0.0, "#e34a33"], [0.33, "#fdbb84"], [0.66, "#addd8e"], [1.0, "#31a354"]],
        showscale=False,
        xgap=5,
        ygap=5
    ))
    
    fig_heat.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=10, b=10),
        yaxis=dict(autorange="reversed")
    )
    st.plotly_chart(fig_heat, use_container_width=True)

except Exception as e:
    st.error(f"{LANG_PACK['RU']['error_load']} {e}")
