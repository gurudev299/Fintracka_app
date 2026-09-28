import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="FinTrack & Goal Engine",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Responsive & Clean CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        color: #ffffff;
        padding: 18px;
        border-radius: 12px;
        border-left: 6px solid #3b82f6;
        margin-bottom: 12px;
    }
    .metric-title {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .metric-val {
        font-size: 1.7rem;
        font-weight: 700;
        margin-top: 4px;
        color: #f8fafc;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- DATABASE HELPERS -----------------
DB_FILE = "fintrack.db"

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Transactions Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT
        )
    ''')
    # Goals Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0.0,
            start_date TEXT NOT NULL,
            target_date TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ----------------- UI TABS -----------------
st.title("💰 FinTrack & Dream Engine")

tab_goals, tab_add, tab_analytics, tab_history = st.tabs([
    "🎯 Goals & Run-Rate",
    "➕ Add Entry",
    "📊 Analytics",
    "📜 History"
])

# ================= TAB 1: DREAMS & GOAL TRACKER =================
with tab_goals:
    st.subheader("🎯 Dream / Goal Run-Rate Calculator")
    st.caption("Aapka daily required earning target calculate karta hai taaki deadline miss na ho.")

    conn = get_db()
    goals = conn.execute("SELECT * FROM goals WHERE status='active' ORDER BY id DESC").fetchall()
    conn.close()

    if not goals:
        st.info("💡 Koi active goal nahi mila! Niche diye gaye form se pehla goal banayein (Jaise: 26 din me ₹30,000).")
    else:
        for g in goals:
            t_date = datetime.strptime(g['target_date'], '%Y-%m-%d').date()
            today = date.today()
            days_left = (t_date - today).days
            
            remaining_amount = max(0.0, g['target_amount'] - g['current_amount'])
            progress = min(1.0, g['current_amount'] / g['target_amount']) if g['target_amount'] > 0 else 0.0

            # Dynamic daily calculation
            if days_left > 0 and remaining_amount > 0:
                per_day_needed = remaining_amount / days_left
            elif remaining_amount == 0:
                per_day_needed = 0.0
            else:
                per_day_needed = remaining_amount  # Deadline over

            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">{g['title']} (Deadline: {t_date.strftime('%d %b %Y')})</div>
                <div class="metric-val">₹{g['current_amount']:,.0f} / ₹{g['target_amount']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

            st.progress(progress)

            c1, c2, c3 = st.columns(3)
            c1.metric("Progress", f"{progress * 100:.1f}%")
            c2.metric("Bache Din", f"{days_left} din" if days_left >= 0 else "Expired")
            c3.metric("Required / Day", f"₹{per_day_needed:,.2f}" if days_left > 0 else "Goal Done" if remaining_amount == 0 else "Overdue")

            # Quick update goal progress
            with st.expander(f"Update Progress: {g['title']}"):
                with st.form(f"update_g_{g['id']}"):
                    add_val = st.number_input("Aur kitna add kiya/kamaya? (₹)", min_value=1.0, step=100.0, format="%.2f")
                    if st.form_submit_button("Update Karein"):
                        c = get_db()
                        c.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ?", (add_val, g['id']))
                        c.commit()
                        c.close()
                        st.success("Goal progress update ho gaya!")
                        st.rerun()

            st.divider()

    # Form to create new goal
    with st.expander("✨ Naya Target / Dream Set Karein"):
        with st.form("new_goal_form"):
            g_title = st.text_input("Goal Title", placeholder="e.g. 26 Din Me 30k Target")
            c_amt1, c_amt2 = st.columns(2)
            g_target = c_amt1.number_input("Target Amount (₹)", min_value=100.0, value=30000.0, step=500.0)
            g_curr = c_amt2.number_input("Already Earned/Saved (₹)", min_value=0.0, value=0.0, step=100.0)

            c_d1, c_d2 = st.columns(2)
            g_start = c_d1.date_input("Start Date", value=date.today())
            g_end = c_d2.date_input("Target Date", value=date.today() + pd.Timedelta(days=26))

            if st.form_submit_button("Goal Save Karein"):
                if g_end <= g_start:
                    st.error("Target date start date ke baad ki honi chahiye.")
                elif not g_title.strip():
                    st.error("Kripya goal ka naam likhein.")
                else:
                    c = get_db()
                    c.execute(
                        "INSERT INTO goals (title, target_amount, current_amount, start_date, target_date, status) VALUES (?, ?, ?, ?, ?, 'active')",
                        (g_title.strip(), g_target, g_curr, str(g_start), str(g_end))
                    )
                    c.commit()
                    c.close()
                    st.success("Goal successfully ban gaya!")
                    st.rerun()

# ================= TAB 2: ADD INCOME / EXPENSE =================
with tab_add:
    st.subheader("➕ Nayi Entry Dalein")
    
    t_type = st.radio("Entry Type", ["Expense (Kharcha)", "Income (Kamai)"], horizontal=True)
    is_expense = "Expense" in t_type

    with st.form("entry_form", clear_on_submit=True):
        col_amt, col_date = st.columns(2)
        amount = col_amt.number_input("Amount (₹)", min_value=1.0, step=10.0, format="%.2f")
        t_date = col_date.date_input("Date", value=date.today())

        if is_expense:
            categories = [
                "Food (Lunch/Dinner/Mess)",
                "Snacks & Tea/Coffee",
                "Fuel (Petrol/Diesel)",
                "Grocery & Vegetables",
                "Travel / Auto / Cab",
                "Mobile Recharge & Bills",
                "Shopping & Personal",
                "Room Rent",
                "Other Expense"
            ]
        else:
            categories = [
                "Daily Earning / Gig",
                "Freelance / Client Work",
                "Salary",
                "Business",
                "Other Income"
            ]

        category = st.selectbox("Category", categories)
        note = st.text_input("Details / Note (Optional)", placeholder="e.g. 2L Petrol, Chai & Biscuit, Client payment")

        # Smart option: Agar Income hai to sidhe goal me add karne ka option
        conn = get_db()
        active_goals = conn.execute("SELECT id, title FROM goals WHERE status='active'").fetchall()
        conn.close()

        goal_choice = None
        if not is_expense and active_goals:
            goal_options = ["None"] + [f"{g['id']} - {g['title']}" for g in active_goals]
            goal_choice = st.selectbox("Kya is kamai ko kisi Goal me jodna hai?", goal_options)

        if st.form_submit_button("Entry Save Karein"):
            c = get_db()
            tx_type_str = "Expense" if is_expense else "Income"
            c.execute(
                "INSERT INTO transactions (date, type, category, amount, note) VALUES (?, ?, ?, ?, ?)",
                (str(t_date), tx_type_str, category, amount, note.strip())
            )
            
            # Agar user ne goal me direct link kiya hai
            if not is_expense and goal_choice and goal_choice != "None":
                selected_goal_id = int(goal_choice.split(" - ")[0])
                c.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ?", (amount, selected_goal_id))

            c.commit()
            c.close()
            st.success(f"✅ ₹{amount:,.2f} ({category}) save ho gaya!")
            st.rerun()

# ================= TAB 3: ANALYTICS =================
with tab_analytics:
    st.subheader("📊 Monthly / Yearly Analysis")
    
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()

    if df.empty:
        st.info("Abhi tak koi transaction entry nahi hui hai.")
    else:
        df['date'] = pd.to_datetime(df['date'])
        df['Year'] = df['date'].dt.year
        df['Month'] = df['date'].dt.strftime('%Y-%m')

        f_type = st.radio("View By", ["Monthly", "Yearly", "Overall"], horizontal=True)
        filtered_df = df.copy()

        if f_type == "Monthly":
            m_list = sorted(df['Month'].unique(), reverse=True)
            sel_month = st.selectbox("Mahina Chunein", m_list)
            filtered_df = df[df['Month'] == sel_month]
        elif f_type == "Yearly":
            y_list = sorted(df['Year'].unique(), reverse=True)
            sel_year = st.selectbox("Saal Chunein", y_list)
            filtered_df = df[df['Year'] == sel_year]

        # Totals
        income_sum = filtered_df[filtered_df['type'] == 'Income']['amount'].sum()
        expense_sum = filtered_df[filtered_df['type'] == 'Expense']['amount'].sum()
        net_savings = income_sum - expense_sum

        c_inc, c_exp, c_bal = st.columns(3)
        c_inc.metric("Total Kamai (Income)", f"₹{income_sum:,.2f}")
        c_exp.metric("Total Kharcha (Expense)", f"₹{expense_sum:,.2f}")
        c_bal.metric("Bachat (Savings)", f"₹{net_savings:,.2f}", delta=f"{net_savings:,.2f}")

        st.divider()

        # Detailed Category Breakdown
        exp_df = filtered_df[filtered_df['type'] == 'Expense']
        if not exp_df.empty:
            st.write("#### 🛍️ Kharcho Ka Batwara (Where your money went):")
            cat_summary = exp_df.groupby('category')['amount'].sum().reset_index().sort_values(by='amount', ascending=False)
            st.dataframe(cat_summary.rename(columns={'category': 'Kharcha Category', 'amount': 'Kul Kharcha (₹)'}), use_container_width=True, hide_index=True)
            st.bar_chart(cat_summary.set_index('category'))
        else:
            st.caption("Is chune hue time me koi kharcha record nahi hua hai.")

# ================= TAB 4: HISTORY =================
with tab_history:
    st.subheader("📜 Sabhi Transactions")
    
    conn = get_db()
    hist_df = pd.read_sql_query("SELECT id, date, type, category, amount, note FROM transactions ORDER BY date DESC, id DESC", conn)
    conn.close()

    if hist_df.empty:
        st.info("Koi history nahi hai.")
    else:
        hist_df['amount'] = hist_df['amount'].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(hist_df, use_container_width=True, hide_index=True)