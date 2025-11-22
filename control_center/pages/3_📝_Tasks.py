"""
Task Management Interface

Submit new scraping tasks and monitor their status.

Features:
- Submit individual URLs
- Batch upload via CSV
- View task queue
- Filter by status
- Pause/Resume controls
- Priority management
"""

import streamlit as st
import psycopg2
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime
import io
from urllib.parse import urlparse

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from config_manager import get_config

# Page config
st.set_page_config(
    page_title="📝 Tasks",
    page_icon="📝",
    layout="wide"
)

st.title("📝 Task Management")
st.markdown("**Submit new scraping tasks and monitor progress**")

# Load config for database connection
try:
    config_manager = get_config()
    
    # Build PostgreSQL connection string
    pg_config = config_manager.databases.postgres
    db_url = f"postgresql://{pg_config.username}:{pg_config.password}@{pg_config.host}:{pg_config.port}/{pg_config.database}"
    
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    
except Exception as e:
    st.error(f"❌ Failed to connect to database: {e}")
    st.info("Make sure PostgreSQL service is running: `docker-compose ps postgres`")
    st.stop()

st.markdown("---")

# ═══════════════════════════════════════════════════════════════
# SUBMIT NEW TASK
# ═══════════════════════════════════════════════════════════════
st.subheader("➕ Submit New Task")

col_submit1, col_submit2 = st.columns([3, 1])

with col_submit1:
    url_input = st.text_input(
        "Product URL to Scrape",
        placeholder="https://example.com/product/12345",
        help="Enter the full URL of the product page"
    )

with col_submit2:
    priority_input = st.slider(
        "Priority",
        min_value=1,
        max_value=10,
        value=5,
        help="Higher priority = processed sooner"
    )

def validate_url(url: str) -> bool:
    """
    Validate URL format and safety.
    
    Only allows http/https schemes to prevent:
    - SSRF attacks (javascript:, file:, data: schemes)
    - Local file disclosure
    - XSS via stored URLs
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        result = urlparse(url)
        
        # SECURITY: Only allow safe schemes
        if result.scheme not in ('http', 'https'):
            return False
        
        # Must have valid netloc (domain)
        if not result.netloc:
            return False
        
        # Reject suspicious patterns
        if any(char in url for char in ['<', '>', '"', "'"]):
            return False
            
        return True
    except Exception:
        return False

if st.button("➕ Add Single Task", type="primary", use_container_width=True):
    if url_input:
        if validate_url(url_input):
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO scraping_tasks (url, priority, status)
                    VALUES (%s, %s, 'pending')
                    ON CONFLICT (url) DO UPDATE SET priority = EXCLUDED.priority
                    RETURNING id
                    """,
                    (url_input, priority_input)
                )
                task_id = cursor.fetchone()[0]
                cursor.close()
                
                st.success(f"✅ Task added: {url_input} (ID: {task_id})")
            except Exception as e:
                st.error(f"❌ Failed to add task: {e}")
        else:
            st.error("❌ Invalid URL format. Must include scheme (http/https) and domain.")
    else:
        st.warning("⚠️ Please enter a URL")

# Batch upload
st.markdown("---")
st.subheader("📁 Batch Upload")

st.markdown("Upload a CSV file with columns: `url`, `priority` (optional)")

uploaded_file = st.file_uploader("Choose CSV file", type=['csv'])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        
        if 'url' not in df.columns:
            st.error("❌ CSV must have a 'url' column")
        else:
            # Add priority column if missing
            if 'priority' not in df.columns:
                df['priority'] = 5
            
            st.dataframe(df.head(10), use_container_width=True)
            
            if st.button(f"📥 Upload {len(df)} Tasks", type="primary"):
                cursor = conn.cursor()
                success_count = 0
                error_count = 0
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, row in df.iterrows():
                    url = row['url']
                    if validate_url(url):
                        try:
                            cursor.execute(
                                """
                                INSERT INTO scraping_tasks (url, priority, status)
                                VALUES (%s, %s, 'pending')
                                ON CONFLICT (url) DO NOTHING
                                """,
                                (url, int(row.get('priority', 5)))
                            )
                            success_count += 1
                        except:
                            error_count += 1
                    else:
                        error_count += 1
                    
                    # Update progress
                    progress = (idx + 1) / len(df)
                    progress_bar.progress(progress)
                    status_text.text(f"Uploading: {idx + 1}/{len(df)}")
                
                cursor.close()
                progress_bar.empty()
                status_text.empty()
                
                st.success(f"✅ Successfully uploaded {success_count} tasks")
                if error_count > 0:
                    st.warning(f"⚠️ Skipped {error_count} invalid/duplicate tasks")
                st.balloons()
                
    except Exception as e:
        st.error(f"❌ Failed to process CSV: {e}")

# ═══════════════════════════════════════════════════════════════
# TASK QUEUE VIEW
# ═══════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("📊 Task Queue")

# Filters
col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)

with col_filter1:
    status_filter = st.selectbox(
        "Filter by Status",
        options=['All', 'pending', 'running', 'completed', 'failed']
    )

with col_filter2:
    priority_filter = st.selectbox(
        "Filter by Priority",
        options=['All'] + list(range(1, 11))
    )

with col_filter3:
    limit = st.selectbox(
        "Show",
        options=[50, 100, 200, 500],
        index=0
    )

with col_filter4:
    sort_by = st.selectbox(
        "Sort by",
        options=['Priority (High→Low)', 'Created (New→Old)', 'Status']
    )

# Build query
query = "SELECT id, url, status, priority, attempts, max_attempts, created_at FROM scraping_tasks"
conditions = []
params = []

if status_filter != 'All':
    conditions.append("status = %s")
    params.append(status_filter)

if priority_filter != 'All':
    conditions.append("priority = %s")
    params.append(int(priority_filter))

if conditions:
    query += " WHERE " + " AND ".join(conditions)

# Add sorting
if sort_by == 'Priority (High→Low)':
    query += " ORDER BY priority DESC, created_at DESC"
elif sort_by == 'Created (New→Old)':
    query += " ORDER BY created_at DESC"
else:
    query += " ORDER BY status, priority DESC"

query += f" LIMIT {limit}"

# Execute query
try:
    cursor = conn.cursor()
    cursor.execute(query, params)
    tasks = cursor.fetchall()
    cursor.close()
    
    if tasks:
        # Convert to DataFrame
        df_tasks = pd.DataFrame(
            tasks,
            columns=['ID', 'URL', 'Status', 'Priority', 'Attempts', 'Max', 'Created']
        )
        
        # Display summary stats
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        # Get overall stats
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed
            FROM scraping_tasks
        """)
        stats = cursor.fetchone()
        cursor.close()
        
        with col_stat1:
            st.metric("Total Tasks", stats[0])
        with col_stat2:
            st.metric("Pending", stats[1])
        with col_stat3:
            st.metric("Completed", stats[2])
        with col_stat4:
            st.metric("Failed", stats[3])
        
        st.markdown("---")
        
        # Display tasks table
        st.dataframe(
            df_tasks,
            use_container_width=True,
            hide_index=True,
            column_config={
                "URL": st.column_config.LinkColumn("URL"),
                "Status": st.column_config.TextColumn("Status"),
                "Priority": st.column_config.NumberColumn("Priority", format="%d"),
                "Attempts": st.column_config.ProgressColumn(
                    "Attempts",
                    format="%d/%d",
                    min_value=0,
                    max_value=3
                )
            }
        )
        
        # Bulk actions
        st.markdown("---")
        st.subheader("🔧 Bulk Actions")
        
        col_action1, col_action2, col_action3 = st.columns(3)
        
        with col_action1:
            if st.button("🗑️ Delete Failed Tasks", use_container_width=True):
                try:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM scraping_tasks WHERE status = 'failed'")
                    deleted = cursor.rowcount
                    cursor.close()
                    st.success(f"✅ Deleted {deleted} failed tasks")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed: {e}")
        
        with col_action2:
            if st.button("🔄 Retry Failed Tasks", use_container_width=True):
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE scraping_tasks 
                        SET status = 'pending', attempts = 0 
                        WHERE status = 'failed'
                    """)
                    updated = cursor.rowcount
                    cursor.close()
                    st.success(f"✅ Reset {updated} tasks to pending")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed: {e}")
        
        with col_action3:
            if st.button("⚠️ Clear All Tasks", use_container_width=True):
                st.warning("This will delete ALL tasks. Use with caution!")
    
    else:
        st.info("📭 No tasks found matching your filters")
        
except Exception as e:
    st.error(f"❌ Failed to fetch tasks: {e}")

# Close connection when done
if 'conn' in locals():
    conn.close()

st.markdown("---")
st.info("💡 **Tip**: Tasks are processed by priority (10 = highest). Use batch upload for bulk operations.")
