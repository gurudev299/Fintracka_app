import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
import hashlib

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="FinTrack - Multi-User & Goal Engine",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Responsive styling
st.markdown("""
    <style>
    .metric-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- DATABASE HELPERS -----------------
def get_db():
    conn = sqlite3.connect("fintrack.db", check_same_thread=False)
    return conn

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT
                )''')
    # Transactions table with user_id
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    type TEXT,
                    category TEXT,
                    amount REAL,
                    note TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )''')
    # Goals table with user_id
    c.execute('''CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT,
                    target_amount REAL,
                    current_amount REAL,
                    start_date TEXT,
                    target_date TEXT,
                    status TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )''')
    conn.commit()
    conn.close()

init_db()

# ----------------- AUTHENTICATION SYSTEM -----------------
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None

def login_user(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hash_pass(password)))
    user = c.fetchone()
    conn.close()
    return user

def register_user(username, password):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_pass(password)))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

# Screen for Login / Signup if not logged in
if st.session_state["user_id"] is None:
    st.title("🔐 FinTrack Login / Sign Up")
    st.info("Har user ka data alag aur secure rahega. Apna user select karein ya naya banayein.")

    auth_choice = st.radio("Choose Option", ["Login", "Sign Up (Naya User)"], horizontal=True)

    with st.form("auth_form"):
        u_name = st.text_input("Username", placeholder="e.g. rahul, aman")
        u_pass = st.text_input("Password / 4-Digit PIN", type="password")
        submit_btn = st.form_submit_button("Submit")

        if submit_btn:
            if not u_name or not u_pass:
                st.warning("Kripya username aur password dono daalein.")
            elif auth_choice == "Login":
                user = login_user(u_name.strip().lower(), u_pass)
                if user:
                    st.session_state["user_id"] = user[0]
                    st.session_state["username"] = u_name.strip().lower()
                    st.success("Login safal raha!")
                    st.rerun()
                else:
                    st.error("Galat username ya password! Kripya dobara try karein.")
            else:
                ok = register_user(u_name.strip().lower(), u_pass)
                if ok:
                    st.success("Account ban gaya! Ab upar 'Login' chun kar login karein.")
                else:
                    st.error("Yeh username pehle se exist karta hai. Dusra naam chunein.")
    st.stop()

# ----------------- MAIN APP (LOGGED IN USER) -----------------
current_uid = st.session_state["user_id"]
current_uname = st.session_state["username"]

# Top Bar with Logout
top_c1, top_c2 = st.columns([4, 1])
with top_c1:
    st.title(f"💰 FinTrack ({current_uname.title()})")
with top_c2:
    if st.button("🚪 Logout"):
        st.session_state["user_id"] = None
        st.session_state["username"] = None
        st.rerun()

tab_goals, tab_add, tab_analytics, tab_history = st.tabs([
    "🎯 Goals & Targets",
    "➕ Add Entry",
    "📊 Monthly/Yearly Analytics",
    "📜 History & Delete/Reset"
])

# ----------------- TAB 1: GOALS & TARGETS -----------------
with tab_goals:
    st.subheader("🎯 Dream & Target Tracker")

    with st.expander("➕ Create New Goal / Target", expanded=False):
        with st.form("new_goal_form", clear_on_submit=True):
            g_title = st.text_input("Goal Name", placeholder="e.g. 26 Days me 30k")
            g_target = st.number_input("Target Amount (₹)", min_value=1.0, value=30000.0, step=500.0)
            g_current = st.number_input("Starting Saved Amount (₹)", min_value=0.0, value=0.0, step=100.0)
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                g_start = st.date_input("Start Date", value=date.today())
            with col_d2:
                g_end = st.date_input("Target Date", value=date.today() + pd.Timedelta(days=26))

            submit_goal = st.form_submit_button("Save Goal")
            if submit_goal:
                if g_end <= g_start:
                    st.error("Target date start date ke baad honi chahiye!")
                else:
                    conn = get_db()
                    c = conn.cursor()
                    c.execute('''INSERT INTO goals (user_id, title, target_amount, current_amount, start_date, target_date, status)
                                 VALUES (?, ?, ?, ?, ?, ?, 'active')''',
                              (current_uid, g_title, g_target, g_current, str(g_start), str(g_end)))
                    conn.commit()
                    conn.close()
                    st.success("Goal successfully save ho gaya!")
                    st.rerun()

    # Display only this user's active goals
    conn = get_db()
    goals_df = pd.read_sql_query("SELECT * FROM goals WHERE user_id = ? AND status='active'", conn, params=(current_uid,))
    conn.close()

    if goals_df.empty:
        st.info("Abhi aapka koi active goal nahi hai. Upar se add karein!")
    else:
        for _, row in goals_df.iterrows():
            today = date.today()
            target_date = datetime.strptime(row['target_date'], '%Y-%m-%d').date()
            days_left = max((target_date - today).days, 0)

            remaining_amount = max(row['target_amount'] - row['current_amount'], 0.0)
            progress = min(row['current_amount'] / row['target_amount'], 1.0) if row['target_amount'] > 0 else 0

            # Daily Run-rate formula
            daily_run_rate = (remaining_amount / days_left) if days_left > 0 else remaining_amount

            st.markdown(f"### 📌 {row['title']}")
            st.progress(progress)

            c1, c2, c3 = st.columns(3)
            c1.metric("Target Amount", f"₹{row['target_amount']:,.2f}")
            c2.metric("Achieved", f"₹{row['current_amount']:,.2f}", f"{progress*100:.1f}%")
            c3.metric("Remaining Amount", f"₹{remaining_amount:,.2f}")

            c4, c5 = st.columns(2)
            c4.metric("Days Remaining", f"{days_left} Days")
            c5.metric("Required Per Day Earning", f"₹{daily_run_rate:,.2f} / day")

            # Quick update or delete/reset goal
            with st.expander(f"⚙️ Manage '{row['title']}' (Progress ya Reset/Delete)"):
                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    with st.form(f"quick_add_{row['id']}"):
                        add_amt = st.number_input("Add Progress Amount (₹)", min_value=1.0, step=100.0)
                        if st.form_submit_button("Add Progress"):
                            conn = get_db()
                            c = conn.cursor()
                            c.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ? AND user_id = ?",
                                      (add_amt, row['id'], current_uid))
                            conn.commit()
                            conn.close()
                            st.success("Progress update ho gayi!")
                            st.rerun()

                with col_u2:
                    st.write("Galat goal ban gaya? Reset/Delete karein:")
                    if st.button(f"🗑️ Delete This Goal", key=f"del_goal_{row['id']}"):
                        conn = get_db()
                        c = conn.cursor()
                        c.execute("DELETE FROM goals WHERE id = ? AND user_id = ?", (row['id'], current_uid))
                        conn.commit()
                        conn.close()
                        st.warning("Goal delete/reset ho gaya!")
                        st.rerun()

            st.markdown("---")

# ----------------- TAB 2: ADD ENTRY -----------------
with tab_add:
    st.subheader("➕ Add Income / Expense Entry")
    
    with st.form("entry_form", clear_on_submit=True):
        t_type = st.radio("Transaction Type", ["Expense", "Income"], horizontal=True)
        t_amount = st.number_input("Amount (₹)", min_value=1.0, step=10.0, format="%.2f")
        t_date = st.date_input("Date", value=date.today())

        if t_type == "Expense":
            categories = [
                "Food (Lunch/Dinner)",
                "Snacks & Tea/Coffee",
                "Fuel (Petrol/Diesel)",
                "Shopping",
                "Rent & Utilities",
                "Travel / Auto / Cab",
                "Grocery & Household",
                "Other Expense"
            ]
        else:
            categories = [
                "Daily Earning / Gig",
                "Salary",
                "Freelance / Client Work",
                "Business Sale",
                "Other Income"
            ]

        t_category = st.selectbox("Category", categories)
        t_note = st.text_input("Details / Description (Optional)", placeholder="e.g. Petrol 2L, Samosa-Chai, etc.")

        # Goal linked progress option
        conn = get_db()
        user_goals = pd.read_sql_query("SELECT id, title FROM goals WHERE user_id = ? AND status='active'", conn, params=(current_uid,))
        conn.close()

        link_goal = False
        selected_goal_id = None
        if t_type == "Income" and not user_goals.empty:
            link_goal = st.checkbox("Kya ise kisi Active Goal ke progress me bhi jodna hai?", value=True)
            if link_goal:
                goal_options = dict(zip(user_goals['title'], user_goals['id']))
                chosen_title = st.selectbox("Choose Goal", list(goal_options.keys()))
                selected_goal_id = goal_options[chosen_title]

        save_entry = st.form_submit_button("💾 Save Entry")

        if save_entry:
            conn = get_db()
            c = conn.cursor()
            c.execute('''INSERT INTO transactions (user_id, date, type, category, amount, note)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (current_uid, str(t_date), t_type, t_category, t_amount, t_note))

            if link_goal and selected_goal_id:
                c.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ? AND user_id = ?",
                          (t_amount, selected_goal_id, current_uid))

            conn.commit()
            conn.close()
            st.success(f"✅ ₹{t_amount:,.2f} ({t_category}) save ho gaya!")

# ----------------- TAB 3: ANALYTICS -----------------
with tab_analytics:
    st.subheader("📊 Monthly & Yearly Analytics")
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM transactions WHERE user_id = ?", conn, params=(current_uid,))
    conn.close()

    if df.empty:
        st.info("Aapka abhi tak koi transaction record nahi hai.")
    else:
        df['date'] = pd.to_datetime(df['date'])
        df['Year'] = df['date'].dt.year
        df['Month'] = df['date'].dt.strftime('%Y-%m')

        filter_type = st.radio("Time View", ["Monthly", "Yearly"], horizontal=True)

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

        st.markdown("#### Kharcho ka Breakdown (Food, Fuel, Snacks, etc.)")
        expense_df = filtered_df[filtered_df['type'] == 'Expense']
        if not expense_df.empty:
            cat_group = expense_df.groupby('category')['amount'].sum().reset_index()
            st.bar_chart(cat_group.set_index('category'))
        else:
            st.caption("Is time period me koi kharcha nahi hai.")

# ----------------- TAB 4: HISTORY & RESET/DELETE -----------------
with tab_history:
    st.subheader("📜 Aapka History & Reset / Delete Section")
    st.caption("Agar koi galat entry ho gayi hai, to niche di gayi table se Entry ID dekh kar turant delete kar sakte hain.")

    conn = get_db()
    all_df = pd.read_sql_query("SELECT id AS 'Entry ID', date AS 'Date', type AS 'Type', category AS 'Category', amount AS 'Amount (₹)', note AS 'Notes' FROM transactions WHERE user_id = ? ORDER BY id DESC", conn, params=(current_uid,))
    conn.close()

    if all_df.empty:
        st.info("Koi transaction history nahi hai.")
    else:
        st.dataframe(all_df, use_container_width=True)

        st.markdown("---")
        st.subheader("🗑️ Galat Entry Reset / Delete Karein")

        col_del1, col_del2 = st.columns([2, 1])
        with col_del1:
            del_id = st.number_input("Galat entry ka 'Entry ID' daalein jise delete karna hai:", min_value=1, step=1)
        with col_del2:
            st.write("")
            st.write("")
            if st.button("🚨 Delete Selected Entry"):
                conn = get_db()
                c = conn.cursor()
                # Verify ki ye entry usi user ki ho
                c.execute("SELECT id FROM transactions WHERE id = ? AND user_id = ?", (del_id, current_uid))
                entry = c.fetchone()
                if entry:
                    c.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (del_id, current_uid))
                    conn.commit()
                    st.success(f"Entry ID #{del_id} successfully delete ho gayi!")
                    conn.close()
                    st.rerun()
                else:
                    st.error("Yeh ID nahi mili ya yeh aapki entry nahi hai.")
                    conn.close()