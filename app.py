import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime

# Page configuration
st.set_page_config(
    page_title="FinTrack & Goal Engine",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom styling for clean UI
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# Database Connection (Local SQLite Fallback & Persistence)
def get_db():
    conn = sqlite3.connect("fintrack.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    type TEXT,
                    category TEXT,
                    amount REAL,
                    note TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    target_amount REAL,
                    current_amount REAL,
                    start_date TEXT,
                    target_date TEXT,
                    status TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

# Google Sheets Helper (Optional Sync if configured in secrets)
def get_gsheet_conn():
    try:
        import importlib
        GSheetsConnection = importlib.import_module("streamlit_gsheets").GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn
    except Exception:
        return None

# Navigation Tabs
st.title("💰 FinTrack & Goal Engine")
tab_goals, tab_add, tab_analytics, tab_history = st.tabs([
    "🎯 Goals & Targets",
    "➕ Add Entry",
    "📊 Monthly/Yearly Analytics",
    "📜 History & Manage Entries"
])

# ==================== TAB 1: GOALS & BREAKDOWN ====================
with tab_goals:
    st.subheader("🎯 Dream & Target Tracker")

    with st.expander("➕ Create New Goal", expanded=False):
        with st.form("new_goal_form", clear_on_submit=True):
            g_title = st.text_input("Goal Name", placeholder="e.g. 30k in 26 Days")
            g_target = st.number_input("Target Amount (₹)", min_value=1.0, value=30000.0, step=500.0)
            g_current = st.number_input("Already Saved/Earned (₹)", min_value=0.0, value=0.0, step=100.0)
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                g_start = st.date_input("Start Date", value=date.today())
            with col_d2:
                g_end = st.date_input("Target Date", value=date.today() + pd.Timedelta(days=26))
            
            submit_goal = st.form_submit_button("Save Goal")
            if submit_goal:
                if g_end <= g_start:
                    st.error("Target date, start date ke baad ki honi chahiye!")
                else:
                    conn = get_db()
                    c = conn.cursor()
                    c.execute('''INSERT INTO goals (title, target_amount, current_amount, start_date, target_date, status)
                                 VALUES (?, ?, ?, ?, ?, 'active')''',
                              (g_title, g_target, g_current, str(g_start), str(g_end)))
                    conn.commit()
                    conn.close()
                    st.success("Goal successfully save ho gaya!")
                    st.rerun()

    # Read Goals
    conn = get_db()
    goals_df = pd.read_sql_query("SELECT * FROM goals WHERE status='active'", conn)
    conn.close()

    if goals_df.empty:
        st.info("Abhi koi active goal nahi hai. Upar se add karein!")
    else:
        for _, row in goals_df.iterrows():
            today = date.today()
            target_date = datetime.strptime(row['target_date'], '%Y-%m-%d').date()
            days_left = max((target_date - today).days, 0)
            
            remaining_amount = max(row['target_amount'] - row['current_amount'], 0.0)
            progress = min(row['current_amount'] / row['target_amount'], 1.0) if row['target_amount'] > 0 else 0.0
            
            # Dynamic Run-rate calculation
            daily_run_rate = (remaining_amount / days_left) if days_left > 0 else remaining_amount

            st.markdown(f"### {row['title']}")
            st.progress(progress)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Target", f"₹{row['target_amount']:,.2f}")
            c2.metric("Achieved", f"₹{row['current_amount']:,.2f}", f"{progress*100:.1f}%")
            c3.metric("Remaining", f"₹{remaining_amount:,.2f}")

            c4, c5 = st.columns(2)
            c4.metric("Days Remaining", f"{days_left} Days")
            c5.metric("Required Run-Rate", f"₹{daily_run_rate:,.2f} / day")

            # Progress update & Reset/Delete options
            col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
            with col_act1:
                with st.form(f"progress_form_{row['id']}"):
                    add_amt = st.number_input("Add Progress Amount (₹)", min_value=1.0, step=100.0, key=f"amt_{row['id']}")
                    if st.form_submit_button("Update Progress"):
                        conn = get_db()
                        c = conn.cursor()
                        new_val = row['current_amount'] + add_amt
                        c.execute("UPDATE goals SET current_amount = ? WHERE id = ?", (new_val, row['id']))
                        conn.commit()
                        conn.close()
                        st.success("Progress update ho gaya!")
                        st.rerun()
            with col_act2:
                if st.button("🔄 Reset Progress", key=f"reset_g_{row['id']}"):
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("UPDATE goals SET current_amount = 0.0 WHERE id = ?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.warning("Goal progress 0 par reset ho gayi!")
                    st.rerun()
            with col_act3:
                if st.button("🗑️ Delete Goal", key=f"del_g_{row['id']}"):
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("DELETE FROM goals WHERE id = ?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.error("Goal delete kar diya gaya!")
                    st.rerun()
            st.markdown("---")

# ==================== TAB 2: ADD ENTRY ====================
with tab_add:
    st.subheader("➕ Add Income / Expense")
    with st.form("entry_form", clear_on_submit=True):
        t_type = st.radio("Type", ["Income", "Expense"], horizontal=True)
        t_amount = st.number_input("Amount (₹)", min_value=1.0, step=50.0)
        t_date = st.date_input("Date", value=date.today())
        
        categories = ["Salary", "Freelance/Gig", "Business", "Investment", "Other Income"] if t_type == "Income" else [
            "Food & Dining", "Rent & Utilities", "Shopping", "Travel", "Bills", "Health", "Miscellaneous"
        ]
        t_category = st.selectbox("Category", categories)
        t_note = st.text_input("Note (Optional)")
        
        save_entry = st.form_submit_button("Save Transaction")
        if save_entry:
            conn = get_db()
            c = conn.cursor()
            c.execute('''INSERT INTO transactions (date, type, category, amount, note)
                         VALUES (?, ?, ?, ?, ?)''',
                      (str(t_date), t_type, t_category, t_amount, t_note))
            conn.commit()
            conn.close()
            st.success(f"{t_type} ₹{t_amount} successfully save ho gaya!")

# ==================== TAB 3: ANALYTICS ====================
with tab_analytics:
    st.subheader("📊 Monthly & Yearly Breakdown")
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()

    if df.empty:
        st.info("Abhi koi transactions record nahi hain.")
    else:
        df['date'] = pd.to_datetime(df['date'])
        df['Year'] = df['date'].dt.year
        df['Month'] = df['date'].dt.strftime('%Y-%m')

        filter_type = st.radio("View By", ["Monthly", "Yearly"], horizontal=True)

        if filter_type == "Monthly":
            available_months = sorted(df['Month'].unique(), reverse=True)
            sel_month = st.selectbox("Select Month", available_months)
            filtered_df = df[df['Month'] == sel_month]
        else:
            available_years = sorted(df['Year'].unique(), reverse=True)
            sel_year = st.selectbox("Select Year", available_years)
            filtered_df = df[df['Year'] == sel_year]

        total_income = filtered_df[filtered_df['type'] == 'Income']['amount'].sum()
        total_expense = filtered_df[filtered_df['type'] == 'Expense']['amount'].sum()
        net_savings = total_income - total_expense

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"₹{total_income:,.2f}")
        col2.metric("Total Expense", f"₹{total_expense:,.2f}")
        col3.metric("Net Savings", f"₹{net_savings:,.2f}")

        st.markdown("#### Expense by Category")
        expense_df = filtered_df[filtered_df['type'] == 'Expense']
        if not expense_df.empty:
            cat_group = expense_df.groupby('category')['amount'].sum().reset_index()
            st.bar_chart(cat_group.set_index('category'))
        else:
            st.caption("Is time period me koi expense nahi hai.")

# ==================== TAB 4: HISTORY & RESET ====================
with tab_history:
    st.subheader("📜 Manage / Reset Wrong Entries")
    conn = get_db()
    all_df = pd.read_sql_query("SELECT id, date, type, category, amount, note FROM transactions ORDER BY id DESC", conn)
    conn.close()

    if all_df.empty:
        st.info("Koi transaction history nahi hai.")
    else:
        st.dataframe(all_df, use_container_width=True)

        st.markdown("### ❌ Wrong Entry Reset / Delete")
        entry_to_del = st.selectbox(
            "Galat entry select karein delete karne ke liye:",
            options=all_df['id'].tolist(),
            format_func=lambda x: f"ID #{x} | {all_df.loc[all_df['id']==x, 'date'].values[0]} | {all_df.loc[all_df['id']==x, 'type'].values[0]} | ₹{all_df.loc[all_df['id']==x, 'amount'].values[0]} ({all_df.loc[all_df['id']==x, 'category'].values[0]})"
        )

        col_del1, col_del2 = st.columns([1, 2])
        with col_del1:
            if st.button("🗑️ Delete This Transaction", type="primary"):
                conn = get_db()
                c = conn.cursor()
                c.execute("DELETE FROM transactions WHERE id = ?", (int(entry_to_del),))
                conn.commit()
                conn.close()
                st.success(f"Transaction ID #{entry_to_del} delete ho gaya!")
                st.rerun()

        with col_del2:
            with st.expander("⚠️ Danger Zone: Pura Data Reset Karein"):
                if st.button("🔥 Reset All Transactions"):
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("DELETE FROM transactions")
                    conn.commit()
                    conn.close()
                    st.warning("Saare transactions delete ho gaye!")
                    st.rerun()