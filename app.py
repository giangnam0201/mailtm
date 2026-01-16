import streamlit as st
import requests
import uuid
import pandas as pd
import time
import os
import subprocess

# --- AUTO-INSTALL PLAYWRIGHT (As per your request) ---
def ensure_playwright_installed():
    try:
        import playwright
    except ImportError:
        subprocess.run(["pip", "install", "playwright"])
    
    # Check if chromium is installed, if not, install it
    # Note: On Streamlit Cloud, you may need a 'packages.txt' with playwright dependencies
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"Error installing Playwright Chromium: {e}")

ensure_playwright_installed()

# --- MAIL.TM API CONFIG ---
BASE_URL = "https://api.mail.tm"

def get_domains():
    response = requests.get(f"{BASE_URL}/domains")
    if response.status_code == 200:
        return [d['domain'] for d in response.json()['hydra:member']]
    return []

def create_account(address, password):
    payload = {"address": address, "password": password}
    response = requests.post(f"{BASE_URL}/accounts", json=payload)
    return response.status_code, response.json()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Mail.tm Bulk Creator", page_icon="📧")

st.title("📧 Mail.tm Bulk Account Generator")
st.markdown("Create temporary email accounts in bulk using the Mail.tm API.")

# Sidebar Settings
st.sidebar.header("Settings")
domains = get_domains()
selected_domain = st.sidebar.selectbox("Select Domain", domains if domains else ["Loading..."])
password_input = st.sidebar.text_input("Default Password", value="Pass1234!", type="password")

# Tabs for Single/Bulk
tab1, tab2 = st.tabs(["Single Account", "Bulk Creation"])

with tab1:
    user_part = st.text_input("Username (Leave blank for random)", "")
    if st.button("Create Single Account"):
        username = user_part if user_part else str(uuid.uuid4())[:8]
        full_email = f"{username}@{selected_domain}"
        
        status, resp = create_account(full_email, password_input)
        if status == 201:
            st.success(f"Created: {full_email}")
            st.code(f"Email: {full_email}\nPassword: {password_input}")
        else:
            st.error(f"Error: {resp.get('hydra:description', 'Unknown error')}")

with tab2:
    count = st.number_input("Number of accounts", min_value=1, max_value=50, value=5)
    if st.button(f"Generate {count} Accounts"):
        results = []
        progress_bar = st.progress(0)
        
        for i in range(count):
            username = str(uuid.uuid4())[:10]
            email = f"{username}@{selected_domain}"
            status, resp = create_account(email, password_input)
            
            if status == 201:
                results.append({"Email": email, "Password": password_input, "Status": "Success"})
            else:
                results.append({"Email": email, "Password": "N/A", "Status": "Failed"})
            
            progress_bar.progress((i + 1) / count)
            time.sleep(0.5) # Avoid rate limiting
        
        df = pd.DataFrame(results)
        st.table(df)
        
        # Download CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "mail_tm_accounts.csv", "text/csv")
