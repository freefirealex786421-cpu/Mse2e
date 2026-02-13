"""
Enhanced Streamlit Application with Premium UI
Author: Darkstar Boii Sahiil
Version: 3.0 - Production Ready
Description: Premium Streamlit UI with animations, modern design, and full backend integration
"""

import streamlit as st
import streamlit.components.v1 as components
import time
import threading
import uuid
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Import backend systems
import config
import logger_system
import database_enhanced as db
import automation_engine
import monitoring_system
import error_recovery
import backup_system
import analytics_system
import alert_system
import browser_manager

# Configure page
st.set_page_config(
    page_title="Darkstar E2EE Premium",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium CSS with animations
PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

/* Global Styles */
* {
    font-family: 'Inter', sans-serif !important;
}

.stApp {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
    background-attachment: fixed;
    min-height: 100vh;
}

/* Main Container */
.main .block-container {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(20px);
    border-radius: 32px;
    padding: 48px;
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 
        0 32px 64px rgba(0, 0, 0, 0.1),
        0 0 0 1px rgba(255, 255, 255, 0.1) inset;
    animation: containerFade 0.6s ease-out;
}

@keyframes containerFade {
    from {
        opacity: 0;
        transform: translateY(20px) scale(0.98);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

/* Header */
.premium-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 24px;
    padding: 48px;
    text-align: center;
    color: white;
    box-shadow: 
        0 20px 40px rgba(102, 126, 234, 0.3),
        0 0 0 1px rgba(255, 255, 255, 0.2) inset;
    animation: headerSlide 0.8s ease-out;
    margin-bottom: 32px;
}

@keyframes headerSlide {
    from {
        opacity: 0;
        transform: translateY(-30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.premium-header h1 {
    font-size: 3.5rem;
    font-weight: 900;
    margin: 0;
    background: linear-gradient(135deg, #fff 0%, #f0f0f0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -1px;
}

.premium-header p {
    font-size: 1.3rem;
    margin: 16px 0 0 0;
    opacity: 0.95;
    font-weight: 400;
}

/* Metrics Cards */
.metric-card {
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
    border-radius: 20px;
    padding: 32px;
    text-align: center;
    box-shadow: 
        0 8px 16px rgba(0, 0, 0, 0.08),
        0 0 0 1px rgba(255, 255, 255, 0.5) inset;
    transition: all 0.3s ease;
    animation: cardFade 0.6s ease-out;
    animation-fill-mode: both;
}

.metric-card:hover {
    transform: translateY(-8px);
    box-shadow: 
        0 16px 32px rgba(0, 0, 0, 0.12),
        0 0 0 1px rgba(255, 255, 255, 0.8) inset;
}

.metric-card:nth-child(1) { animation-delay: 0.1s; }
.metric-card:nth-child(2) { animation-delay: 0.2s; }
.metric-card:nth-child(3) { animation-delay: 0.3s; }

@keyframes cardFade {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.metric-value {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 8px 0;
}

.metric-label {
    font-size: 0.95rem;
    color: #666;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
    border-radius: 16px;
    padding: 8px;
    gap: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 12px;
    padding: 16px 32px;
    font-weight: 600;
    color: #666;
    transition: all 0.3s ease;
    border: none;
}

.stTabs [data-baseweb="tab"]:hover {
    background: rgba(102, 126, 234, 0.1);
    color: #667eea;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white !important;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    font-weight: 700;
    font-size: 1rem;
    padding: 14px 32px;
    border-radius: 14px;
    border: none;
    transition: all 0.3s ease;
    box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
}

.stButton > button:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 24px rgba(102, 126, 234, 0.4);
}

.stButton > button:active {
    transform: translateY(-1px);
}

/* Input Fields */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input {
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
    border-radius: 12px;
    padding: 16px;
    border: 2px solid transparent;
    color: #333;
    font-size: 1rem;
    transition: all 0.3s ease;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stNumberInput > div > div > input:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
}

label {
    color: #333;
    font-weight: 700;
    font-size: 0.95rem;
}

/* Console Output */
.console-output {
    background: #1e1e1e;
    border-radius: 16px;
    padding: 24px;
    font-family: 'JetBrains Mono', monospace;
    max-height: 500px;
    color: #d4d4d4;
    overflow-y: auto;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.console-line {
    padding: 8px 12px;
    margin: 4px 0;
    border-left: 3px solid #667eea;
    background: rgba(102, 126, 234, 0.05);
    border-radius: 0 8px 8px 0;
    animation: lineFade 0.3s ease;
}

@keyframes lineFade {
    from {
        opacity: 0;
        transform: translateX(-10px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

.console-line.error {
    border-left-color: #ef4444;
    background: rgba(239, 68, 68, 0.1);
}

.console-line.success {
    border-left-color: #10b981;
    background: rgba(16, 185, 129, 0.1);
}

.console-line.warning {
    border-left-color: #f59e0b;
    background: rgba(245, 158, 11, 0.1);
}

/* Status Badge */
.status-badge {
    display: inline-block;
    padding: 8px 20px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% {
        transform: scale(1);
    }
    50% {
        transform: scale(1.02);
    }
}

.status-running {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.status-stopped {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    color: white;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

/* Sidebar */
.css-1d391kg {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
}

.css-1d391kg .css-17eq0hr {
    color: white !important;
}

/* Footer */
.footer {
    text-align: center;
    color: white;
    font-weight: 700;
    margin-top: 32px;
    padding: 24px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 16px;
}

/* Progress Bar */
.stProgress > div > div > div > div {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* Info Box */
.info-box {
    background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
    border-radius: 16px;
    padding: 24px;
    border-left: 4px solid #3b82f6;
    margin: 16px 0;
}

.success-box {
    background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
    border-radius: 16px;
    padding: 24px;
    border-left: 4px solid #10b981;
    margin: 16px 0;
}

.warning-box {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border-radius: 16px;
    padding: 24px;
    border-left: 4px solid #f59e0b;
    margin: 16px 0;
}

.error-box {
    background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
    border-radius: 16px;
    padding: 24px;
    border-left: 4px solid #ef4444;
    margin: 16px 0;
}

/* Charts */
.plotly-chart {
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

/* Spinner */
.stSpinner > div {
    border-color: #667eea !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}
</style>
"""

# Apply CSS
st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

# Session state initialization
def init_session_state():
    """Initialize session state variables"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'automation_running' not in st.session_state:
        st.session_state.automation_running = False
    if 'automation_engine' not in st.session_state:
        st.session_state.automation_engine = None
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = 0

init_session_state()

# Login Page
def login_page():
    """Render login page"""
    st.markdown("""
    <div class="premium-header">
        <h1>🚀 Darkstar Boii Sahiil</h1>
        <p>END TO END (E2EE) AUTOMATION SYSTEM v3.0</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    with tab1:
        st.markdown("### Welcome Back!")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            username = st.text_input("Username", key="login_username", 
                                   placeholder="Enter your username",
                                   help="Your registered username")
            password = st.text_input("Password", key="login_password", 
                                   type="password",
                                   placeholder="Enter your password",
                                   help="Your account password")
            
            if st.button("🚀 Login", key="login_btn", use_container_width=True):
                if username and password:
                    user_id = db.get_database().verify_user(username, password)
                    if user_id:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        
                        # Initialize automation engine
                        if st.session_state.automation_engine is None:
                            st.session_state.automation_engine = automation_engine.get_automation_engine(max_workers=5)
                            st.session_state.automation_engine.start()
                        
                        st.success(f"✅ Welcome back, {username.upper()}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password!")
                else:
                    st.warning("⚠️ Please enter both username and password")
    
    with tab2:
        st.markdown("### Create New Account")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            new_username = st.text_input("Choose Username", key="signup_username",
                                       placeholder="Choose a unique username")
            new_password = st.text_input("Choose Password", key="signup_password",
                                       type="password",
                                       placeholder="Create a strong password")
            confirm_password = st.text_input("Confirm Password", key="confirm_password",
                                           type="password",
                                           placeholder="Re-enter your password")
            
            if st.button("✨ Create Account", key="signup_btn", use_container_width=True):
                if new_username and new_password and confirm_password:
                    if new_password == confirm_password:
                        success, message = db.get_database().create_user(new_username, new_password)
                        if success:
                            st.success(f"✅ {message} Please login now!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.error("❌ Passwords do not match!")
                else:
                    st.warning("⚠️ Please fill all fields")

# Main Application
def main_app():
    """Render main application"""
    
    # Header
    st.markdown("""
    <div class="premium-header">
        <h1>🚀 Darkstar E2EE Automation</h1>
        <p>PREMIUM AUTOMATION CONTROL PANEL v3.0</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 16px; margin-bottom: 20px;">
            <h3 style="color: white; margin: 0 0 10px 0;">👤 User Profile</h3>
            <p style="color: white; margin: 0; font-weight: 600;">{username}</p>
            <p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0; font-size: 0.9em;">ID: {user_id}</p>
        </div>
        """.format(username=st.session_state.username, user_id=st.session_state.user_id),
        unsafe_allow_html=True)
        
        st.markdown('<div class="success-box" style="padding: 12px; margin: 10px 0;">✅ Premium Active</div>', unsafe_allow_html=True)
        
        # System Health
        monitor = monitoring_system.get_monitoring_system()
        health = monitor.get_health_status()
        
        health_color = "#10b981" if health['overall_status'] == 'healthy' else "#f59e0b"
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.1); padding: 16px; border-radius: 12px; margin: 16px 0;">
            <p style="color: white; margin: 0; font-size: 0.9em;">System Health</p>
            <p style="color: {health_color}; margin: 5px 0 0 0; font-weight: 700; font-size: 1.2em;">● {health['overall_status'].upper()}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Logout", use_container_width=True):
            if st.session_state.automation_engine:
                st.session_state.automation_engine.stop()
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()
    
    # Get user config
    database = db.get_database()
    user_config = database.get_user_config(st.session_state.user_id)
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⚙️ E2EE Setup", 
        "🤖 Automation", 
        "📊 Analytics", 
        "💾 Backups",
        "🔧 System"
    ])
    
    with tab1:
        render_setup_tab(user_config, database)
    
    with tab2:
        render_automation_tab(user_config, database)
    
    with tab3:
        render_analytics_tab()
    
    with tab4:
        render_backups_tab()
    
    with tab5:
        render_system_tab()
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>Made with ❤️ by Darkstar Boii Sahiil 🇮🇳 2026</p>
        <p style="font-size: 0.9em; opacity: 0.8;">Premium Automation System v3.0 | 24/7 Non-Stop Operation</p>
    </div>
    """, unsafe_allow_html=True)

def render_setup_tab(user_config, database):
    """Render E2EE setup tab"""
    st.markdown('<h2 style="margin-bottom: 24px;">⚙️ E2EE Configuration Setup</h2>', unsafe_allow_html=True)
    
    if user_config:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="info-box"><strong>📱 Chat Settings</strong></div>', unsafe_allow_html=True)
            chat_id = st.text_input("E2EE Chat ID", 
                                   value=user_config['chat_id'],
                                   placeholder="e.g., 10000634210631",
                                   help="Facebook conversation ID from URL")
            
            name_prefix = st.text_input("Name Prefix",
                                       value=user_config['name_prefix'],
                                       placeholder="Optional prefix",
                                       help="Prefix added before each message")
            
            delay = st.number_input("Message Delay (seconds)",
                                   min_value=1,
                                   max_value=300,
                                   value=user_config['delay'],
                                   help="Wait time between messages")
        
        with col2:
            st.markdown('<div class="info-box"><strong>🔐 Authentication</strong></div>', unsafe_allow_html=True)
            cookies = st.text_area("Facebook Cookies",
                                  placeholder="Paste your cookies here...",
                                  height=150,
                                  help="Your cookies are encrypted and secure")
            
            messages = st.text_area("Messages (one per line)",
                                   value=user_config['messages'],
                                   placeholder="Enter your messages...",
                                   height=200,
                                   help="Each message on a new line")
        
        if st.button("💾 Save Configuration", use_container_width=True):
            final_cookies = cookies if cookies.strip() else user_config['cookies']
            database.update_user_config(
                st.session_state.user_id,
                chat_id,
                name_prefix,
                delay,
                final_cookies,
                messages
            )
            st.success("✅ Configuration saved successfully!")
            time.sleep(1)
            st.rerun()
    else:
        st.warning("⚠️ No configuration found. Please refresh the page.")

def render_automation_tab(user_config, database):
    """Render automation control tab"""
    st.markdown('<h2 style="margin-bottom: 24px;">🤖 Automation Control Center</h2>', unsafe_allow_html=True)
    
    # Metrics
    engine = st.session_state.automation_engine
    stats = engine.get_stats() if engine else None
    
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Active Workers</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{stats.active_workers}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Tasks Done</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{stats.completed_tasks}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Messages Sent</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{stats.total_messages_sent}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Avg Time</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{stats.avg_task_time:.1f}s</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Worker Stats
    if engine:
        worker_stats = engine.get_worker_stats()
        
        st.markdown("### Worker Status")
        for worker in worker_stats:
            status_color = "🟢" if worker['status'] == 'idle' else "🟡" if worker['status'] == 'busy' else "🔴"
            st.markdown(f"""
            <div style="background: rgba(102, 126, 234, 0.1); padding: 16px; border-radius: 12px; margin: 8px 0;">
                <strong>{status_color} {worker['worker_id']}</strong><br>
                <small>Status: {worker['status']} | Tasks: {worker['total_tasks_completed']} | Messages: {worker['total_messages_sent']}</small>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start Automation", 
                    disabled=not user_config or not user_config['chat_id'] or stats and stats.active_workers > 0,
                    use_container_width=True):
            if user_config and user_config['chat_id']:
                engine = st.session_state.automation_engine
                engine.add_task_from_config(st.session_state.user_id, user_config)
                st.success("✅ Automation started!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Please configure chat ID first!")
    
    with col2:
        if st.button("⏹️ Stop Automation",
                    disabled=not stats or stats.active_workers == 0,
                    use_container_width=True):
            engine = st.session_state.automation_engine
            engine.stop()
            st.warning("⚠️ Automation stopped!")
            time.sleep(1)
            st.rerun()
    
    # Logs
    st.markdown("### 📋 Live Console Output")
    logs = database.get_automation_logs(st.session_state.user_id, limit=50)
    
    console_html = '<div class="console-output">'
    for log in logs:
        level_class = log['level'].lower()
        console_html += f'''
        <div class="console-line {level_class}">
            <small>[{log['timestamp']}]</small> 
            <strong>{log['process_id']}</strong>: {log['message']}
        </div>
        '''
    console_html += '</div>'
    
    st.markdown(console_html, unsafe_allow_html=True)
    
    if st.button("🔄 Refresh Logs", use_container_width=True):
        st.rerun()

def render_analytics_tab():
    """Render analytics and monitoring tab"""
    st.markdown('<h2 style="margin-bottom: 24px;">📊 Analytics & Monitoring</h2>', unsafe_allow_html=True)
    
    monitor = monitoring_system.get_monitoring_system()
    analytics = analytics_system.get_analytics_engine()
    
    # System Stats
    system_stats = monitor.get_system_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">CPU Usage</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{system_stats["cpu"]["percent"]:.1f}%</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Memory Usage</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{system_stats["memory"]["percent"]:.1f}%</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Disk Usage</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{system_stats["disk"]["percent"]:.1f}%</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Charts
    st.markdown("### Performance Trends")
    
    # CPU History Chart
    cpu_metrics = monitor.get_metrics("system.cpu_percent", hours=1)
    if cpu_metrics:
        df = pd.DataFrame(cpu_metrics)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        fig = px.line(df, x='timestamp', y='value', 
                     title='CPU Usage Over Time',
                     labels={'value': 'CPU %', 'timestamp': 'Time'},
                     color_discrete_sequence=['#667eea'])
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Message History Chart
    message_stats = database.get_database().get_message_stats(st.session_state.user_id, days=7)
    if message_stats['daily_stats']:
        df = pd.DataFrame(message_stats['daily_stats'])
        df['date'] = pd.to_datetime(df['date'])
        
        fig = go.Figure(data=[
            go.Bar(name='Sent', x=df['date'], y=df['total'], marker_color='#667eea'),
            go.Bar(name='Failed', x=df['date'], y=df['failed'], marker_color='#ef4444')
        ])
        fig.update_layout(barmode='stack', title='Messages Last 7 Days', height=300)
        st.plotly_chart(fig, use_container_width=True)

def render_backups_tab():
    """Render backup management tab"""
    st.markdown('<h2 style="margin-bottom: 24px;">💾 Backup Management</h2>', unsafe_allow_html=True)
    
    # Get backup manager
    database = db.get_database()
    backup_mgr = backup_system.get_backup_manager(database.db_path)
    
    # Stats
    stats = backup_mgr.get_backup_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Total Backups</div><div class="metric-value">{stats["total_backups"]}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Completed</div><div class="metric-value">{stats["completed_backups"]}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Total Size</div><div class="metric-value">{stats["total_size"] / (1024*1024):.1f} MB</div></div>', unsafe_allow_html=True)
    with col4:
        compression = stats["compression_ratio"] * 100
        st.markdown(f'<div class="metric-card"><div class="metric-label">Compression</div><div class="metric-value">{compression:.0f}%</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Create Backup Now", use_container_width=True):
            backup_id = backup_mgr.create_backup()
            if backup_id:
                st.success(f"✅ Backup created: {backup_id}")
            else:
                st.error("❌ Backup failed!")
            time.sleep(1)
            st.rerun()
    
    with col2:
        if st.button("🧹 Clean Old Backups", use_container_width=True):
            backup_mgr._cleanup_old_backups()
            st.success("✅ Old backups cleaned!")
            time.sleep(1)
            st.rerun()
    
    st.markdown("---")
    
    # Backup List
    st.markdown("### Recent Backups")
    backups = backup_mgr.list_backups(status=backup_system.BackupStatus.COMPLETED, limit=10)
    
    if backups:
        for backup in backups:
            size_mb = backup['file_size'] / (1024*1024)
            st.markdown(f"""
            <div style="background: rgba(102, 126, 234, 0.1); padding: 16px; border-radius: 12px; margin: 8px 0;">
                <strong>📦 {backup['backup_id']}</strong><br>
                <small>Size: {size_mb:.2f} MB | Compressed: {backup['compressed_size'] / (1024*1024):.2f} MB | {backup['created_at']}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ No backups found")

def render_system_tab():
    """Render system monitoring tab"""
    st.markdown('<h2 style="margin-bottom: 24px;">🔧 System Monitoring</h2>', unsafe_allow_html=True)
    
    monitor = monitoring_system.get_monitoring_system()
    recovery = error_recovery.get_error_recovery_system()
    alerts = alert_system.get_alert_manager()
    
    # Health Status
    health = monitor.get_health_status()
    health_color = "#10b981" if health['overall_status'] == 'healthy' else "#f59e0b"
    
    st.markdown(f"""
    <div class="{'success-box' if health['overall_status'] == 'healthy' else 'warning-box'}">
        <h3 style="margin: 0 0 16px 0;">Overall System Health</h3>
        <p style="margin: 0; font-size: 2em; font-weight: 800; color: {health_color};">● {health['overall_status'].upper()}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Health Checks
    st.markdown("### Health Check Status")
    for check_name, check_info in health['checks'].items():
        status_icon = "✅" if check_info['status'] == 'healthy' else "⚠️"
        status_color = "#10b981" if check_info['status'] == 'healthy' else "#f59e0b"
        
        st.markdown(f"""
        <div style="background: rgba(102, 126, 234, 0.1); padding: 16px; border-radius: 12px; margin: 8px 0;">
            {status_icon} <strong>{check_name.replace('_', ' ').title()}</strong>
            <span style="float: right; color: {status_color}; font-weight: 700;">{check_info['status'].upper()}</span>
            <br><small>Last check: {check_info['last_check'] or 'Never'}</small>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recent Errors
    st.markdown("### Recent Errors")
    errors = recovery.get_recent_errors(limit=10)
    
    if errors:
        for error in errors:
            severity_color = {
                'low': '#10b981',
                'medium': '#f59e0b',
                'high': '#ef4444',
                'critical': '#dc2626'
            }.get(error['severity'], '#666')
            
            st.markdown(f"""
            <div style="background: rgba(239, 68, 68, 0.1); padding: 16px; border-radius: 12px; margin: 8px 0; border-left: 4px solid {severity_color};">
                <strong style="color: {severity_color};">[{error['severity'].upper()}] {error['error_type']}</strong>
                <br><small>{error['message']}</small>
                <br><small>Occurrences: {error['occurrence_count']} | Resolved: {'✅' if error['resolved'] else '❌'}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ No recent errors")
    
    st.markdown("---")
    
    # Active Alerts
    st.markdown("### Active Alerts")
    active_alerts = alerts.get_active_alerts()
    
    if active_alerts:
        for alert in active_alerts:
            severity_color = {
                'info': '#3b82f6',
                'warning': '#f59e0b',
                'error': '#ef4444',
                'critical': '#dc2626'
            }.get(alert['severity'], '#666')
            
            st.markdown(f"""
            <div style="background: rgba(239, 68, 68, 0.1); padding: 16px; border-radius: 12px; margin: 8px 0; border-left: 4px solid {severity_color};">
                <strong style="color: {severity_color};">[{alert['severity'].upper()}] {alert['alert_name']}</strong>
                <br><small>{alert['message']}</small>
                <br><small>Value: {alert['value']} | Threshold: {alert['threshold']} | {alert['timestamp']}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ No active alerts")

# Main Application Logic
if not st.session_state.logged_in:
    login_page()
else:
    main_app()