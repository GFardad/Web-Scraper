"""
Live Monitoring Dashboard

Real-time monitoring of scraper performance, GPU usage, and system health.

Features:
- Pages/minute throughput
- Error rate breakdown
- GPU/VRAM utilization
- Redis queue depth
- Interactive charts (Plotly)
- Auto-refresh (1s interval)
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from monitoring.vram_monitor import get_vram_monitor
from resilience.circuit_breaker import get_circuit_breaker

# Page config
st.set_page_config(
    page_title="📊 Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Live Monitoring Dashboard")
st.markdown("**Real-time metrics** refreshing every 2 seconds")

# Initialize monitors
vram_monitor = get_vram_monitor()
circuit_breaker = get_circuit_breaker()

# Placeholder for auto-refresh
placeholder = st.empty()

# Refresh counter
if 'refresh_count' not in st.session_state:
    st.session_state.refresh_count = 0

# Auto-refresh toggle
auto_refresh = st.sidebar.checkbox("🔄 Auto-Refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 1, 10, 2)

# Main dashboard loop
while auto_refresh:
    with placeholder.container():
        st.session_state.refresh_count += 1
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Header with timestamp
        col_header1, col_header2 = st.columns([3, 1])
        with col_header1:
            st.markdown(f"### Live Data - {current_time}")
        with col_header2:
            st.markdown(f"*Refresh #{st.session_state.refresh_count}*")
        
        st.markdown("---")
        
        # ═══════════════════════════════════════════════════════════════
        # KEY METRICS ROW
        # ═══════════════════════════════════════════════════════════════
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            # Pages/minute (mock data for now - integrate Prometheus later)
            pages_per_min = 12.5  # TODO: Get from Prometheus
            st.metric(
                "📄 Pages/Minute",
                f"{pages_per_min:.1f}",
                delta="+2.3" if st.session_state.refresh_count % 3 == 0 else "-0.5"
            )
        
        with metric_col2:
            # Error rate
            error_rate = 2.1  # TODO: Get from Prometheus
            st.metric(
                "❌ Error Rate",
                f"{error_rate:.1f}%",
                delta="-0.3" if error_rate < 5 else "+1.2",
                delta_color="inverse"
            )
        
        with metric_col3:
            # Queue depth
            queue_depth = 47  # TODO: Get from Redis
            st.metric(
                "📦 Queue Depth",
                queue_depth,
                delta="-5" if queue_depth < 50 else "+10"
            )
        
        with metric_col4:
            # Active workers
            active_workers = 4  # TODO: Get from metrics
            st.metric(
                "⚙️ Active Workers",
                f"{active_workers}/8"
            )
        
        st.markdown("---")
        
        # ═══════════════════════════════════════════════════════════════
        # GPU/VRAM MONITORING
        # ═══════════════════════════════════════════════════════════════
        st.subheader("🎮 GPU & VRAM Statistics")
        
        gpu_stats = vram_monitor.get_full_stats()
        
        gpu_col1, gpu_col2, gpu_col3, gpu_col4 = st.columns(4)
        
        with gpu_col1:
            vram_used = gpu_stats.get('vram_used_gb', 0)
            vram_total = gpu_stats.get('vram_total_gb', 0)
            st.metric(
                "💾 VRAM Used",
                f"{vram_used:.2f} GB",
                f"of {vram_total:.2f} GB"
            )
        
        with gpu_col2:
            vram_percent =gpu_stats.get('vram_percent', 0)
            st.metric(
                "📊 VRAM %",
                f"{vram_percent:.1f}%",
                delta="Within Budget" if gpu_stats.get('within_budget') else "⚠️ Over Budget",
                delta_color="normal" if gpu_stats.get('within_budget') else "inverse"
            )
        
        with gpu_col3:
            gpu_util = gpu_stats.get('gpu_utilization_percent', 0)
            st.metric(
                "⚡ GPU Utilization",
                f"{gpu_util:.1f}%"
            )
        
        with gpu_col4:
            temp = gpu_stats.get('temperature_celsius', 0)
            st.metric(
                "🌡️ Temperature",
                f"{temp}°C",
                delta="Normal" if temp < 80 else "⚠️ High",
                delta_color="normal" if temp < 80 else "inverse"
            )
        
        # VRAM usage gauge
        fig_vram = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=vram_used,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "VRAM Usage (GB)"},
            delta={'reference': gpu_stats.get('vram_budget_gb', 3.0)},
            gauge={
                'axis': {'range': [None, vram_total]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, gpu_stats.get('vram_budget_gb', 3.0)], 'color': "lightgreen"},
                    {'range': [gpu_stats.get('vram_budget_gb', 3.0), vram_total], 'color': "lightcoral"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': gpu_stats.get('vram_budget_gb', 3.0)
                }
            }
        ))
        
        st.plotly_chart(fig_vram, use_container_width=True)
        
        st.markdown("---")
        
        # ═══════════════════════════════════════════════════════════════
        # THROUGHPUT CHART
        # ═══════════════════════════════════════════════════════════════
        st.subheader("📈 Throughput (Last 10 Minutes)")
        
        # Generate mock time series data
        # TODO: Replace with actual Prometheus queries
        time_points = pd.date_range(
            end=datetime.now(),
            periods=20,
            freq='30S'
        )
        
        success_data = [10 + i * 0.5 + (i % 3) * 2 for i in range(20)]
        error_data = [1 + (i % 5) * 0.3 for i in range(20)]
        
        fig_throughput = go.Figure()
        
        fig_throughput.add_trace(go.Scatter(
            x=time_points,
            y=success_data,
            mode='lines+markers',
            name='Successful',
            line=dict(color='green', width=2),
            fill='tozeroy'
        ))
        
        fig_throughput.add_trace(go.Scatter(
            x=time_points,
            y=error_data,
            mode='lines+markers',
            name='Errors',
            line=dict(color='red', width=2),
            fill='tozeroy'
        ))
        
        fig_throughput.update_layout(
            xaxis_title="Time",
            yaxis_title="Pages",
            hovermode='x unified',
            height=350
        )
        
        st.plotly_chart(fig_throughput, use_container_width=True)
        
        st.markdown("---")
        
        # ═══════════════════════════════════════════════════════════════
        # ERROR BREAKDOWN
        # ═══════════════════════════════════════════════════════════════
        st.subheader("🚨 Error Breakdown")
        
        error_col1, error_col2 = st.columns(2)
        
        with error_col1:
            # Error types pie chart
            error_types = {
                '403 Forbidden': 12,
                '404 Not Found': 5,
                'Timeout': 8,
                'Parser Error': 3,
                'CAPTCHA': 2
            }
            
            fig_errors = go.Figure(data=[go.Pie(
                labels=list(error_types.keys()),
                values=list(error_types.values()),
                hole=.3
            )])
            
            fig_errors.update_layout(title="Error Types (Last Hour)")
            st.plotly_chart(fig_errors, use_container_width=True)
        
        with error_col2:
            # Recent errors table
            st.markdown("**Recent Errors**")
            
            recent_errors = pd.DataFrame({
                'Time': ['01:12:45', '01:11:30', '01:10:15', '01:09:00', '01:07:45'],
                'Domain': ['example.com', 'test.com', 'shop.com', 'example.com', 'demo.com'],
                'Error': ['403', 'Timeout', '404', '403', 'Parser']
            })
            
            st.dataframe(recent_errors, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # ═══════════════════════════════════════════════════════════════
        # CIRCUIT BREAKER STATUS
        # ═══════════════════════════════════════════════════════════════
        st.subheader("🔌 Circuit Breaker Status")
        
        # Mock circuit breaker data
        circuit_data = pd.DataFrame({
            'Domain': ['example.com', 'test.com', 'shop.com'],
            'State': ['OPEN', 'CLOSED', 'HALF_OPEN'],
            'Failures': [5, 0, 2],
            'Cooldown': ['2:34', '-', '0:45']
        })
        
        st.dataframe(
            circuit_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "State": st.column_config.TextColumn(
                    "State",
                    help="Circuit state"
                )
            }
        )
    
    # Wait before next refresh
    time.sleep(refresh_interval)
    st.rerun()

# If auto-refresh disabled, show static view
if not auto_refresh:
    st.info("🔄 Auto-refresh disabled. Enable it in the sidebar to see live data.")
