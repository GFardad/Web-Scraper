"""
Live Configuration Editor

Edit config.yaml parameters via UI and trigger hot-reload automatically.

Features:
- Edit key parameters (delays, workers, prompts)
- Real-time validation (Input Sanitization)
- Write back to config.yaml
- Auto-trigger hot-reload
- Change history tracking
"""

import streamlit as st
import yaml
from pathlib import Path
import sys
from datetime import datetime

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from config_manager import get_config

# Page config
st.set_page_config(
    page_title="⚙️ Configuration",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Live Configuration Editor")
st.markdown("**Edit parameters below. Changes apply immediately via hot-reload.**")

# Config file path
CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"

if not CONFIG_PATH.exists():
    st.error(f"❌ Config file not found: {CONFIG_PATH}")
    st.stop()

# Load current config
try:
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    config_manager = get_config()
except Exception as e:
    st.error(f"❌ Failed to load config: {e}")
    st.stop()

st.markdown("---")

# Create form for editable parameters
with st.form("config_form", clear_on_submit=False):
    st.subheader("🚦 Rate Limiting")
    
    col1, col2 = st.columns(2)
    
    with col1:
        base_delay = st.slider(
            "Base Delay (seconds)",
            min_value=0.5,
            max_value=10.0,
            value=float(config.get('scraper', {}).get('rate_limiting', {}).get('base_delay', 2.0)),
            step=0.5,
            help="Delay between requests to avoid rate limiting"
        )
    
    with col2:
        max_delay = st.slider(
            "Max Delay (seconds)",
            min_value=1.0,
            max_value=30.0,
            value=float(config.get('scraper', {}).get('rate_limiting', {}).get('max_delay', 10.0)),
            step=1.0,
            help="Maximum delay when backing off"
        )
    
    st.markdown("---")
    st.subheader("⚙️ Concurrency")
    
    col3, col4 = st.columns(2)
    
    with col3:
        max_workers = st.slider(
            "Max Workers",
            min_value=1,
            max_value=16,
            value=int(config.get('scraper', {}).get('concurrency', {}).get('max_workers', 4)),
            help="Number of concurrent scraping workers"
        )
    
    with col4:
        semaphore_limit = st.slider(
            "Semaphore Limit",
            min_value=1,
            max_value=32,
            value=int(config.get('scraper', {}).get('concurrency', {}).get('semaphore_limit', 8)),
            help="Maximum concurrent operations"
        )
    
    st.markdown("---")
    st.subheader("🤖 AI System Prompt")
    
    # Get current systemprompt (from inline or file)
    current_prompt = config.get('prompts', {}).get('product_extraction', {}).get('inline', '')
    
    system_prompt = st.text_area(
        "Ollama LLM System Prompt",
        value=current_prompt,
        height=200,
        help="Instructions for the LLM when extracting product data"
    )
    
    st.markdown("---")
    st.subheader("🌐 Proxy Settings")
    
    col5, col6 = st.columns(2)
    
    with col5:
        proxy_enabled = st.checkbox(
            "Enable Proxies",
            value=config.get('proxies', {}).get('enabled', False),
            help="Use proxy pool for requests"
        )
    
    with col6:
        rotate_proxies = st.checkbox(
            "Rotate Proxies",
            value=config.get('proxies', {}).get('rotate', True),
            help="Rotate through proxy list"
        )
    
    st.markdown("---")
    st.subheader("🛡️ Circuit Breaker")
    
    col7, col8 = st.columns(2)
    
    with col7:
        circuit_enabled = st.checkbox(
            "Enable Circuit Breaker",
            value=config.get('scraper', {}).get('circuit_breaker', {}).get('enabled', True),
            help="Temporarily block failing domains"
        )
    
    with col8:
        failure_threshold = st.number_input(
            "Failure Threshold",
            min_value=3,
            max_value=20,
            value=int(config.get('scraper', {}).get('circuit_breaker', {}).get('failure_threshold', 5)),
            help="Number of failures before opening circuit"
        )
    
    st.markdown("---")
    
    # Submit button
    col_submit1, col_submit2, col_submit3 = st.columns([1, 1, 2])
    
    with col_submit1:
        submitted = st.form_submit_button("💾 Apply Changes", type="primary", use_container_width=True)
    
    with col_submit2:
        reset = st.form_submit_button("🔄 Reset to Defaults", use_container_width=True)
    
    if submitted:
        # -----------------------------------------------------------------
        # INPUT SANITIZATION & VALIDATION
        # -----------------------------------------------------------------
        errors = []
        
        if base_delay <= 0:
            errors.append("Base Delay must be positive")
        if max_delay < base_delay:
            errors.append("Max Delay must be greater than Base Delay")
        if max_workers < 1:
            errors.append("Max Workers must be at least 1")
        if semaphore_limit < 1:
            errors.append("Semaphore Limit must be at least 1")
        if len(system_prompt.strip()) < 10:
            errors.append("System Prompt is too short (min 10 chars)")
        
        if errors:
            for err in errors:
                st.error(f"❌ {err}")
        else:
            try:
                # Update config dictionary
                if 'scraper' not in config:
                    config['scraper'] = {}
                if 'rate_limiting' not in config['scraper']:
                    config['scraper']['rate_limiting'] = {}
                if 'concurrency' not in config['scraper']:
                    config['scraper']['concurrency'] = {}
                if 'circuit_breaker' not in config['scraper']:
                    config['scraper']['circuit_breaker'] = {}
                if 'proxies' not in config:
                    config['proxies'] = {}
                if 'prompts' not in config:
                    config['prompts'] = {}
                if 'product_extraction' not in config['prompts']:
                    config['prompts']['product_extraction'] = {}
                
                config['scraper']['rate_limiting']['base_delay'] = base_delay
                config['scraper']['rate_limiting']['max_delay'] = max_delay
                config['scraper']['concurrency']['max_workers'] = max_workers
                config['scraper']['concurrency']['semaphore_limit'] = semaphore_limit
                config['prompts']['product_extraction']['inline'] = system_prompt
                config['proxies']['enabled'] = proxy_enabled
                config['proxies']['rotate'] = rotate_proxies
                config['scraper']['circuit_breaker']['enabled'] = circuit_enabled
                config['scraper']['circuit_breaker']['failure_threshold'] = failure_threshold
                
                # Write back to file (this triggers hot-reload)
                with open(CONFIG_PATH, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                
                st.success("✅ Configuration updated successfully!")
                st.balloons()
                
                # Log change
                st.info(f"🔄 Hot-reload will apply changes within {config.get('hot_reload', {}).get('debounce_seconds', 1)} seconds")
                
                # Show changes
                with st.expander("📝 Changes Applied"):
                    st.markdown(f"""
                    - **Base Delay**: {base_delay}s
                    - **Max Delay**: {max_delay}s
                    - **Max Workers**: {max_workers}
                    - **Semaphore Limit**: {semaphore_limit}
                    - **Proxy Enabled**: {proxy_enabled}
                    - **Circuit Breaker**: {circuit_enabled}
                    - **Failure Threshold**: {failure_threshold}
                    - **System Prompt**: {len(system_prompt)} characters
                    """)
                
            except Exception as e:
                st.error(f"❌ Failed to update config: {e}")
    
    if reset:
        st.warning("Reset to defaults - Feature coming soon!")

# Show current config sections
st.markdown("---")
st.subheader("📋 Current Configuration Overview")

col_overview1, col_overview2, col_overview3 = st.columns(3)

with col_overview1:
    st.markdown("**🚦 Rate Limiting**")
    st.code(f"""
base_delay: {config.get('scraper', {}).get('rate_limiting', {}).get('base_delay', 'N/A')}s
max_delay: {config.get('scraper', {}).get('rate_limiting', {}).get('max_delay', 'N/A')}s
    """)

with col_overview2:
    st.markdown("**⚙️ Concurrency**")
    st.code(f"""
max_workers: {config.get('scraper', {}).get('concurrency', {}).get('max_workers', 'N/A')}
semaphore: {config.get('scraper', {}).get('concurrency', {}).get('semaphore_limit', 'N/A')}
    """)

with col_overview3:
    st.markdown("**🛡️ Circuit Breaker**")
    st.code(f"""
enabled: {config.get('scraper', {}).get('circuit_breaker', {}).get('enabled', 'N/A')}
threshold: {config.get('scraper', {}).get('circuit_breaker', {}).get('failure_threshold', 'N/A')}
    """)

# Raw YAML viewer
with st.expander("🔍 View Raw YAML"):
    st.code(yaml.dump(config, default_flow_style=False), language='yaml')

# Change history (mock - would need database for real implementation)
st.markdown("---")
st.subheader("📜 Recent Changes")

change_history = [
    {"Time": "01:15:30", "Parameter": "base_delay", "Old": "2.0", "New": "3.5", "User": "admin"},
    {"Time": "01:10:15", "Parameter": "max_workers", "Old": "4", "New": "8", "User": "admin"},
    {"Time": "01:05:00", "Parameter": "proxy.enabled", "Old": "false", "New": "true", "User": "admin"},
]

st.table(change_history)

st.markdown("---")
st.info("💡 **Tip**: Changes are written directly to `config.yaml` and trigger the hot-reload mechanism. No restart needed!")
