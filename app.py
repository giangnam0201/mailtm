import streamlit as st
import requests
import time
import pandas as pd

# API Base URL
BASE_URL = "https://api.mail.tm"

def get_domains():
    response = requests.get(f"{BASE_URL}/domains")
    if response.status_code == 200:
        return response.json().get('hydra:member', [])
    return []

def create_account(address, password):
    payload = {"address": address, "password": password}
    response = requests.post(f"{BASE_URL}/accounts", json=payload)
    return response

def get_token(address, password):
    payload = {"address": address, "password": password}
    response = requests.post(f"{BASE_URL}/token", json=payload)
    return response.json().get('token') if response.status_code == 200 else None

def fetch_messages(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/messages", headers=headers)
    if response.status_code == 200:
        return response.json().get('hydra:member', [])
    return []

# --- UI Setup ---
st.set_page_config(page_title="Mail.tm Manager", layout="wide")
st.title("📬 Mail.tm Bulk Account & Inbox Manager")

if 'accounts' not in st.session_state:
    st.session_state.accounts = []

# Sidebar: Create Accounts
with st.sidebar:
    st.header("Create New Accounts")
    domains = get_domains()
    domain_names = [d['domain'] for d in domains]
    
    selected_domain = st.selectbox("Select Domain", domain_names)
    prefix = st.text_input("Email Prefix (e.g., testuser)", "user")
    pwd = st.text_input("Password", "SecurePass123!", type="password")
    bulk_count = st.number_input("Number of accounts", min_value=1, max_value=10, value=1)
    
    if st.button("🚀 Generate Accounts"):
        for i in range(bulk_count):
            email = f"{prefix}{int(time.time()) + i}@{selected_domain}"
            res = create_account(email, pwd)
            if res.status_code == 201:
                token = get_token(email, pwd)
                st.session_state.accounts.append({"email": email, "password": pwd, "token": token})
                st.success(f"Created: {email}")
            else:
                st.error(f"Failed {email}: {res.text}")

# Main Area: Account Management
if st.session_state.accounts:
    st.subheader("Manage Generated Accounts")
    df = pd.DataFrame(st.session_state.accounts)[["email", "password"]]
    st.dataframe(df, use_container_width=True)

    selected_acc = st.selectbox("Select account to view Inbox", 
                                [a['email'] for a in st.session_state.accounts])
    
    if st.button("🔄 Refresh Inbox"):
        acc_data = next(item for item in st.session_state.accounts if item["email"] == selected_acc)
        messages = fetch_messages(acc_data['token'])
        
        if not messages:
            st.info("No messages found.")
        for msg in messages:
            with st.expander(f"From: {msg['from']['address']} - {msg['subject']}"):
                st.write(f"**Date:** {msg['createdAt']}")
                st.write(msg['intro'])
                # To get full body, you'd call /messages/{id}
else:
    st.info("No accounts generated yet. Use the sidebar to create some!")
