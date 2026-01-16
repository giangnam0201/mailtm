import streamlit as st
import requests
import time
import pandas as pd
import sqlite3

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('mail_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS accounts 
                 (email TEXT, password TEXT, token TEXT, created_at TEXT)''')
    conn.commit()
    conn.close()

def save_to_db(email, password, token):
    conn = sqlite3.connect('mail_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO accounts VALUES (?, ?, ?, ?)", 
              (email, password, token, time.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def load_from_db():
    conn = sqlite3.connect('mail_data.db')
    df = pd.read_sql_query("SELECT * FROM accounts", conn)
    conn.close()
    return df

# Initialize DB
init_db()

# --- API LOGIC ---
BASE_URL = "https://api.mail.tm"

def get_domains():
    try:
        res = requests.get(f"{BASE_URL}/domains")
        return res.json().get('hydra:member', [])
    except: return []

def create_mail_account(address, password):
    return requests.post(f"{BASE_URL}/accounts", json={"address": address, "password": password})

def get_token(address, password):
    res = requests.post(f"{BASE_URL}/token", json={"address": address, "password": password})
    return res.json().get('token') if res.status_code == 200 else None

# --- STREAMLIT UI ---
st.set_page_config(page_title="Server-Saved Mail.tm", layout="wide")
st.title("🛡️ Persistent Mail.tm Manager")
st.caption("Data is saved into a server-side SQLite database.")

# Sidebar for generation
with st.sidebar:
    st.header("Generate Accounts")
    domains = get_domains()
    dom_list = [d['domain'] for d in domains]
    
    sel_domain = st.selectbox("Select Domain", dom_list)
    prefix = st.text_input("Prefix", "user")
    pwd = st.text_input("Password", "Pass123!", type="password")
    num = st.number_input("How many?", 1, 20, 5)

    if st.button("Generate & Store on Server"):
        with st.spinner("Creating accounts..."):
            for i in range(num):
                unique_id = int(time.time() * 1000) + i # High precision for bulk
                email = f"{prefix}{unique_id}@{sel_domain}"
                
                if create_mail_account(email, pwd).status_code == 201:
                    token = get_token(email, pwd)
                    save_to_db(email, pwd, token)
            st.success("Done! Saved to Server DB.")
            st.rerun()

# Main Display
st.subheader("Stored Accounts")
data = load_from_db()

if not data.empty:
    # Display the table
    st.dataframe(data[["email", "password", "created_at"]], use_container_width=True)
    
    # Options
    col1, col2 = st.columns(2)
    with col1:
        csv = data.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Backup to CSV", csv, "backup_mails.csv", "text/csv")
    
    with col2:
        if st.button("🗑️ Wipe Server Database"):
            conn = sqlite3.connect('mail_data.db')
            conn.cursor().execute("DELETE FROM accounts")
            conn.commit()
            conn.close()
            st.rerun()
else:
    st.info("The server database is currently empty.")
