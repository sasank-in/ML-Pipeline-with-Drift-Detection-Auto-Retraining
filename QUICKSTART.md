# Quick Start Guide

Get the ML Pipeline running in 3 steps!

## Step 1: Setup

```bash
# Windows
setup.bat

# Linux/Mac
./setup.sh
```

Wait for "Setup Complete!" message (2-3 minutes).

## Step 2: Start Services

```bash
# Windows
run_all_services.bat

# Linux/Mac
./run_all_services.sh
```

This opens 5 windows (one for each service). Wait 10-15 seconds.

## Step 3: Run Demo

Open a **new terminal**:

```bash
# Windows
venv\Scripts\activate
python demo.py

# Linux/Mac
source venv/bin/activate
python demo.py
```

## Verify It's Working

Open browser and check:
- http://localhost:8001/health (Ingestion API)
- http://localhost:8002/health (Prediction Service)
- http://localhost:8050 (Dashboard)

All should respond successfully!

## What You'll See

- **5 service windows** open (this is normal)
- **Demo runs** showing progress for each phase
- **Dashboard opens** in browser with metrics
- **~90% accuracy** on lung disease predictions

## Common Issues

**"Python not found"**
→ Install Python 3.9+ from python.org

**"Virtual environment not found"**
→ Run setup.bat/setup.sh first

**"Port already in use"**
→ Restart computer or kill the process

**"Services won't start"**
→ Run `scripts\verify_setup.bat` to diagnose

## Stop Services

```bash
# Windows
stop_all_services.bat

# Linux/Mac
./stop_all_services.sh
```

Or close all 5 service windows.

## Need More Help?

- Full documentation: `README.md`
- Architecture details: `docs/ARCHITECTURE.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`

---

**That's it!** Your ML pipeline is now running. 🚀
