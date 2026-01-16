import streamlit as st
import requests
import time
import pandas as pd
import sqlite3
from datetime import datetime

# --- DATABASE LOGIC (SERVER STORAGE) ---
DB_NAME = "mail_tm_vault.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS accounts 
                 (email TEXT PRIMARY KEY, password TEXT, token TEXT, created_at TEXT)''')
    conn.commit()
    conn.close()

def save_account(email, password, token):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO accounts VALUES (?, ?, ?, ?)", 
              (email, password, token, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def load_accounts():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM accounts ORDER BY created_at DESC", conn)
    conn.close()
    return df

# --- MAIL.TM API LOGIC ---
BASE_URL = "https://api.mail.tm"

def api_request(method, endpoint, token=None, json=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"{BASE_URL}{endpoint}"
    if method == "GET":
        return requests.get(url, headers=headers)
    return requests.post(url, headers=headers, json=json)

# --- UI SETUP ---
st.set_page_config(page_title="Pro Mail.tm Manager", layout="wide")
init_db()

st.title("🛡️ Pro Mail.tm Terminal")
st.markdown("---")

# --- SIDEBAR: GENERATOR ---
with st.sidebar:
    st.header("⚡ Bulk Generator")
    try:
        domains = api_request("GET", "/domains").json()['hydra:member']
        domain = st.selectbox("Select Domain", [d['domain'] for d in domains])
    except:
        st.error("API Error: Could not fetch domains.")
        st.stop()

    prefix = st.text_input("Email Prefix", "bot")
    password = st.text_input("Password", "GlobalPass123!", type="password")
    count = st.number_input("Bulk Amount", 1, 100, 5)

    if st.button("🚀 Generate & Save to Server"):
        progress = st.progress(0)
        for i in range(count):
            acc_email = f"{prefix}{int(time.time())}{i}@{domain}"
            # 1. Create Account
            res = api_request("POST", "/accounts", json={"address": acc_email, "password": password})
            if res.status_code == 201:
                # 2. Get Token
                token_res = api_request("POST", "/token", json={"address": acc_email, "password": password})
                if token_res.status_code == 200:
                    token = token_res.json().get('token')
                    save_account(acc_email, password, token)
            progress.progress((i + 1) / count)
        st.success(f"Successfully added {count} accounts!")
        st.rerun()

# --- MAIN INTERFACE: TWO COLUMNS ---
tab1, tab2 = st.tabs(["📩 Inbox & Messages", "📋 Account Database"])

with tab2:
    st.subheader("Stored Accounts")
    all_accs = load_accounts()
    if not all_accs.empty:
        st.dataframe(all_accs, use_container_width=True)
        csv = all_accs.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export all to CSV", csv, "accounts.csv", "text/csv")
        
        if st.button("🗑️ Wipe All Data"):
            conn = sqlite3.connect(DB_NAME)
            conn.cursor().execute("DELETE FROM accounts")
            conn.commit()
            conn.close()
            st.rerun()
    else:
        st.info("No accounts in database.")

with tab1:
    if not all_accs.empty:
        col_acc, col_msg = st.columns([1, 2])
        
        with col_acc:
            st.subheader("1. Pick Account")
            target_email = st.selectbox("Select Account", all_accs['email'].tolist())
            account_row = all_accs[all_accs['email'] == target_email].iloc[0]
            token = account_row['token']
            
            if st.button("🔄 Refresh Inbox"):
                st.session_state.current_messages = api_request("GET", "/messages", token=token).json().get('hydra:member', [])
        
        with col_msg:
            st.subheader("2. Messages")
            messages = st.session_state.get('current_messages', [])
            
            if not messages:
                st.write("No messages found or click refresh.")
            
            for msg in messages:
                with st.expander(f"📧 {msg['subject']} (From: {msg['from']['address']})"):
                    st.write(f"**Date:** {msg['createdAt']}")
                    # Fetch full message body
                    msg_id = msg['id']
                    full_msg = api_request("GET", f"/messages/{msg_id}", token=token).json()
                    st.divider()
                    st.components.v1.html(full_msg.get('html', [full_msg.get('intro')])[0], scrolling=True, height=300)
    else:
        st.warning("Create accounts first to use the Inbox.")
