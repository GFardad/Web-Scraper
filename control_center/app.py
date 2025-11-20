"""
Enterprise Scraper Control Center

A Streamlit-based web interface for monitoring and managing the scraper.

Features:
- Live monitoring dashboard (Prometheus metrics)
- Real-time configuration editing with hot-reload
- Task management (submit, view, control)
- GPU/VRAM monitoring
- Circuit breaker status
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config_manager import get_config

# Page configuration
st.set_page_config(
    page_title="🚀 Scraper Control Center",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Dark Mode & Glassmorphism
st.markdown("""
<style>
    /* Global Dark Theme Overrides */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Headers */
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 20px rgba(79, 172, 254, 0.3);
    }
    
    /* Cards */
    .metric-card {
        background: #1f2937;
        padding: 1.5rem;
        border-radius: 1rem;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    /* Status Indicators */
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 600;
    }
    .status-ok {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid #059669;
    }
    .status-warning {
        background-color: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        border: 1px solid #d97706;
    }
    .status-error {
        background-color: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid #b91c1c;
    }
    
    /* Buttons */
    .stButton button {
        border-radius: 0.5rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton button:hover {
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<h1 class="main-header">🚀 Enterprise Scraper Control Center</h1>', unsafe_allow_html=True)
st.markdown(
    "<div style='display: flex; gap: 1rem; align-items: center; margin-bottom: 2rem;'>"
    "<span class='status-badge status-ok'>V1.0 Production</span>"
    "<span class='status-badge status-ok'>God-Tier Compliance</span>"
    "<span class='status-badge status-ok'>Zero-Cost Sovereignty</span>"
    "</div>",
    unsafe_allow_html=True
)

# Load configuration
try:
    config = get_config()
    config_loaded = True
except Exception as e:
    st.error(f"❌ Failed to load configuration: {e}")
    config_loaded = False

# Sidebar information
with st.sidebar:
    st.markdown("## 🖥️ System Status")
    
    if config_loaded:
        # Hot-reload status
        hot_reload_enabled = config.get('hot_reload.enabled', default=False)
        st.markdown(
            f"**Hot-Reload:** {'<span class=\"status-ok\">✅ Active</span>' if hot_reload_enabled else '<span class=\"status-warning\">❌ Inactive</span>'}",
            unsafe_allow_html=True
        )
        
        # GPU status
        gpu_enabled = config.get('ai.gpu.enabled', default=False)
        st.markdown(
            f"**GPU:** {'<span class=\"status-ok\">✅ Online</span>' if gpu_enabled else '<span class=\"status-warning\">❌ Offline</span>'}",
            unsafe_allow_html=True
        )
        
        # Docker mode
        st.markdown(f"**Env:** `{config.get('environment', default='production')}`")
        
        st.markdown("---")
        
        # Quick stats
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("🔄 Reload Config", use_container_width=True):
            try:
                config.reload()
                st.toast("Configuration reloaded successfully!", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"Reload failed: {e}")
        
        if st.button("📊 View Logs", use_container_width=True):
            st.info("Check logs via terminal: `make logs`")
        
        if st.button("🚨 Emergency Stop", use_container_width=True, type="primary"):
            st.error("Run: `docker-compose down` in terminal")
    
    st.markdown("---")
    st.markdown("### 🧭 Navigation")
    st.page_link("pages/1_📊_Dashboard.py", label="📊 Dashboard", use_container_width=True)
    st.page_link("pages/2_⚙️_Configuration.py", label="⚙️ Configuration", use_container_width=True)
    st.page_link("pages/3_📝_Tasks.py", label="📝 Tasks", use_container_width=True)

# Welcome message
st.markdown("### 👋 Welcome, Chief QA Officer")

col1, col2, col3 = st.columns(3)

with col1:
    with st.container(border=True):
        st.markdown("### 📊 Live Monitoring")
        st.markdown("""
        Real-time telemetry of your scraping fleet.
        
        - **Throughput**: Pages/min
        - **Resources**: GPU/VRAM usage
        - **Health**: Error rates & Circuit breakers
        """)
        st.page_link("pages/1_📊_Dashboard.py", label="Open Dashboard", use_container_width=True)

with col2:
    with st.container(border=True):
        st.markdown("### ⚙️ Configuration")
        st.markdown("""
        Live tuning of scraper parameters.
        
        - **Rate Limiting**: Delays & Throttling
        - **Concurrency**: Workers & Semaphores
        - **Stealth**: Proxy & Fingerprint settings
        """)
        st.page_link("pages/2_⚙️_Configuration.py", label="Edit Config", use_container_width=True)

with col3:
    with st.container(border=True):
        st.markdown("### 📝 Task Management")
        st.markdown("""
        Control the scraping queue.
        
        - **Submit**: Add URLs (Single/Batch)
        - **Monitor**: View queue status
        - **Control**: Pause, Resume, Retry
        """)
        st.page_link("pages/3_📝_Tasks.py", label="Manage Tasks", use_container_width=True)

# System information
if config_loaded:
    st.markdown("---")
    st.markdown("### ℹ️ System Information")
    
    info_col1, info_col2, info_col3, info_col4 = st.columns(4)
    
    with info_col1:
        st.metric(
            "Config Sections",
            len(config.config.keys()) if hasattr(config, 'config') else 0,
            help="Number of top-level configuration sections"
        )
    
    with info_col2:
        ai_model = config.get('ai.ollama.model_name', default='N/A')
        st.metric("LLM Model", ai_model, help="Active Local LLM")
    
    with info_col3:
        max_workers = config.get('scraper.concurrency.max_workers', default=0)
        st.metric("Max Workers", max_workers, help="Concurrent scraping threads")
    
    with info_col4:
        vram_budget = config.get('ai.gpu.max_vram_gb', default=0)
        st.metric("VRAM Budget", f"{vram_budget} GB", help="Max GPU memory allocation")

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #6b7280; font-size: 0.875rem;">'
    '🚀 Enterprise Scraper Control Center v1.0 | '
    'Built with Streamlit & Python 3.11 | '
    '🔒 Secure & Local-First'
    '</div>',
    unsafe_allow_html=True
)
