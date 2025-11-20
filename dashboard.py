import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config_db import DATABASE_URL

# Sync engine for Streamlit (simpler than async for UI)
SYNC_DB_URL = DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
engine = create_engine(SYNC_DB_URL)
Session = sessionmaker(bind=engine)

st.set_page_config(page_title="Scraper Admin", layout="wide")

st.title("🕷️ Scraper Admin Dashboard")

# --- Sidebar: Quick Add Task ---
with st.sidebar:
    st.header("🚀 Quick Add Task")
    new_url = st.text_input("Product URL", placeholder="https://...")
    if st.button("Inject Task"):
        if new_url:
            try:
                with Session() as session:
                    # Check duplicate
                    exists = session.execute(text("SELECT 1 FROM scrape_tasks WHERE url = :url"), {"url": new_url}).scalar()
                    if exists:
                        st.warning("URL already in queue!")
                    else:
                        session.execute(
                            text("INSERT INTO scrape_tasks (url, status, priority, attempts, created_at) VALUES (:url, 'pending', 1, 0, CURRENT_TIMESTAMP)"),
                            {"url": new_url}
                        )
                        session.commit()
                        st.success("Task injected successfully!")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please enter a URL")

    st.divider()
    st.info("Use this panel to manage the scraping queue and view results.")

# --- Main Content ---

col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Task Queue")
    try:
        df_tasks = pd.read_sql("SELECT * FROM scrape_tasks ORDER BY created_at DESC", engine)
        st.dataframe(df_tasks, use_container_width=True)
        
        if st.button("Refresh Queue"):
            st.rerun()
            
        if st.button("Clear Failed Tasks"):
            with Session() as session:
                session.execute(text("DELETE FROM scrape_tasks WHERE status = 'failed'"))
                session.commit()
            st.success("Failed tasks cleared!")
            st.rerun()
            
    except Exception as e:
        st.error(f"Database Error: {e}")

with col2:
    st.subheader("✅ Scrape Results")
    try:
        df_results = pd.read_sql("SELECT * FROM scrape_results ORDER BY extracted_at DESC", engine)
        st.dataframe(df_results, use_container_width=True)
        
        if st.button("Refresh Results"):
            st.rerun()
            
    except Exception as e:
        st.error(f"Database Error: {e}")

# --- Metrics ---
st.divider()
st.subheader("📊 System Health")
try:
    with Session() as session:
        total = session.execute(text("SELECT COUNT(*) FROM scrape_tasks")).scalar()
        pending = session.execute(text("SELECT COUNT(*) FROM scrape_tasks WHERE status = 'pending'")).scalar()
        done = session.execute(text("SELECT COUNT(*) FROM scrape_tasks WHERE status = 'done'")).scalar()
        failed = session.execute(text("SELECT COUNT(*) FROM scrape_tasks WHERE status = 'failed'")).scalar()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Tasks", total)
    m2.metric("Pending", pending)
    m3.metric("Completed", done)
    m4.metric("Failed", failed, delta_color="inverse")

except Exception:
    st.warning("Could not load metrics")
