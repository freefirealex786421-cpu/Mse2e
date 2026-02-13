# 🚀 Darkstar E2EE Automation System v3.0

## 📋 Overview

Darkstar E2EE Automation System is a production-ready, 24/7 non-stop automation platform for Facebook End-to-End Encrypted conversations. Built with advanced features including multi-worker architecture, connection pooling, automatic error recovery, comprehensive monitoring, and a premium modern UI.

**Author:** Darkstar Boii Sahiil  
**Version:** 3.0.0  
**Status:** Production Ready ✅

---

## ✨ Key Features

### 🎯 Core Automation
- **Multi-Worker Engine:** Parallel processing with configurable worker count
- **Smart Task Scheduling:** Priority-based task queue with automatic assignment
- **24/7 Operation:** Non-stop execution with auto-restart capabilities
- **Error Recovery:** Automatic detection and recovery from common errors

### 💾 Data Management
- **Connection Pooling:** Thread-safe database connection pool
- **Automated Backups:** Scheduled backups with compression
- **Message History:** Complete tracking of all sent messages
- **Data Encryption:** Secure cookie storage with Fernet encryption

### 🖥️ Browser Management
- **Browser Pool:** Multiple browser instances for parallel operations
- **Health Monitoring:** Automatic browser recreation on failure
- **Proxy Support:** Configurable proxy settings
- **Retry Logic:** Automatic retry with configurable attempts

### 📊 Monitoring & Analytics
- **Real-time Monitoring:** Live health checks and metrics collection
- **Performance Analytics:** Detailed analytics and reporting
- **System Statistics:** CPU, memory, disk, and network monitoring
- **Alert System:** Multi-channel notifications (email, webhook, etc.)

### 🎨 Premium UI
- **Modern Design:** Gradient-based UI with glassmorphism effects
- **Smooth Animations:** Fade-in, slide-up, and card animations
- **Real-time Updates:** Live dashboard with streaming updates
- **Responsive Layout:** Optimized for all screen sizes

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Orchestrator                 │
│                   (orchestrator.py)                         │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┴────────┬──────────────┬──────────────┬─────────┐
    │                 │              │              │         │
┌───▼────┐  ┌────────▼─────┐  ┌────▼────┐  ┌─────▼──────┐ │
│Config  │  │ Automation   │  │ Browser │  │  Monitoring │ │
│Manager │  │   Engine     │  │  Pool   │  │   System   │ │
└────────┘  └──────────────┘  └─────────┘  └────────────┘ │
                                            │               │
                                    ┌───────▼──────────────▼─────┐
                                    │     Error Recovery         │
                                    └──────────────┬────────────┘
                                                   │
                                    ┌──────────────▼────────────┐
                                    │   Backup & Analytics      │
                                    └───────────────────────────┘
```

---

## 📦 Installation

### Prerequisites

- **Operating System:** Linux (Debian/Ubuntu recommended)
- **Python:** 3.11 or higher
- **RAM:** Minimum 2GB (4GB+ recommended)
- **Storage:** Minimum 10GB free space

### Step-by-Step Installation

#### 1. Clone or Download the Project

```bash
cd /workspace
# Files should be in /workspace directory
```

#### 2. Run Deployment Script

```bash
chmod +x deploy.sh
./deploy.sh
```

This will:
- Install all system dependencies
- Set up Python virtual environment
- Install required Python packages
- Create necessary directories
- Initialize database
- Configure systemd service
- Set up Nginx (optional)

---

## 🚀 Usage

### Starting the Application

```bash
chmod +x start.sh
./start.sh
```

### Accessing the Application

Open your web browser and navigate to:
- **Local:** http://localhost:8501
- **Network:** http://YOUR_SERVER_IP:8501

### Stopping the Application

```bash
./stop.sh
```

### Checking Status

```bash
./status.sh
```

---

## 📱 User Guide

### 1. Login/Signup

- First time users: Click "Sign Up" tab and create an account
- Existing users: Enter username and password in "Login" tab

### 2. E2EE Setup

Configure your Facebook automation:

1. **Enter Chat ID:** The target Facebook chat ID
2. **Set Name Prefix:** Prefix for automated messages
3. **Configure Delay:** Time delay between messages (in seconds)
4. **Add Cookies:** Paste your Facebook cookies for authentication
5. **Enter Messages:** List of messages to send (one per line)

### 3. Automation Control

- **Start Automation:** Click to begin sending messages
- **Stop Automation:** Click to stop the current automation
- **View Status:** Monitor worker activity and progress
- **Live Console:** Real-time log output

### 4. Analytics Dashboard

View detailed analytics:
- System performance metrics
- Automation statistics
- Database performance
- Error summaries

---

## 🔧 Configuration

Key configuration settings in `config.py`:

```python
# Database Configuration
database.path = "users.db"
database.backup_enabled = true
database.connection_pool_size = 10

# Browser Configuration
browser.headless = true
browser.pool_size = 3

# Automation Configuration
automation.max_workers = 5
automation.auto_restart_enabled = true
```

---

## 🐛 Troubleshooting

### Common Issues

#### Application won't start

```bash
# Check logs
tail -f logs/orchestrator.log
tail -f logs/streamlit.log

# Restart
./restart.sh
```

#### Browser automation fails

```bash
# Check Chromium
chromium --version
chromedriver --version

# Reinstall
sudo apt-get install --reinstall chromium chromium-driver
```

---

## 📞 Support

For support, contact: **Darkstar Boii Sahiil**

---

**Built with ❤️ by Darkstar Boii Sahiil**