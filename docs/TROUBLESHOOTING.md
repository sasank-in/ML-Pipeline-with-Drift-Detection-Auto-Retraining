# Troubleshooting Guide

## Common Issues and Solutions

### 1. Services Won't Start

#### Error: "Python is not installed"
**Solution**:
1. Install Python 3.9+ from [python.org](https://www.python.org/downloads/)
2. During installation, check "Add Python to PATH"
3. Restart your terminal
4. Run `python --version` to verify

#### Error: "Virtual environment not found"
**Solution**:
```bash
# Run setup first
setup.bat
```

#### Error: "Module not found" or "Import Error"
**Solution**:
```bash
# Reinstall dependencies
venv\Scripts\activate
pip install -r requirements.txt --force-reinstall
```

### 2. Port Already in Use

#### Error: "Address already in use" or "Port 8001/8002/8050 in use"
**Solution**:

**Find and kill the process**:
```bash
# Find process using port
netstat -ano | findstr :8001

# Kill process (replace <PID> with actual process ID)
taskkill /PID <PID> /F
```

**Or restart your computer** to clear all ports.

### 3. Services Start But Don't Work

#### Check if services are actually running:
```bash
# Test Ingestion API
curl http://localhost:8001/health

# Or in PowerShell
Invoke-WebRequest -Uri "http://localhost:8001/health"
```

#### Check logs for errors:
```bash
# View logs
type logs\ingestion_api.log
type logs\prediction_service.log
```

### 4. Demo Script Errors

#### Error: "Connection refused" or "Services not available"
**Solution**:
1. Make sure services are running first
2. Wait 10 seconds after starting services
3. Check if ports 8001 and 8002 respond

#### Error: "CSV file not found"
**Solution**:
The demo automatically creates sample data if CSV is missing. This is normal.

#### Error: "No module named 'requests'"
**Solution**:
```bash
venv\Scripts\activate
pip install requests
```

### 5. Dashboard Won't Open

#### Error: "Cannot connect to localhost:8050"
**Solution**:
1. Check if Dashboard service window is open
2. Look for errors in the Dashboard window
3. Check logs: `type logs\dashboard.log`
4. Try restarting just the dashboard:
   ```bash
   venv\Scripts\activate
   python dashboards/monitoring_app.py
   ```

### 6. Database Errors

#### Error: "Database is locked"
**Solution**:
1. Close all services
2. Delete `data/pipeline.db`
3. Restart services

#### Error: "No such table"
**Solution**:
Database will be created automatically. If issues persist:
```bash
# Delete and recreate
del data\pipeline.db
# Restart services
```

### 7. Import Path Errors

#### Error: "ModuleNotFoundError: No module named 'shared'"
**Solution**:
This should be fixed in all files. If you still see this:
1. Make sure you're running from project root directory
2. Check that all service files have the path setup at the top

### 8. Virtual Environment Issues

#### Error: "Cannot activate virtual environment"
**Solution**:
```bash
# Delete and recreate
rmdir /s /q venv
setup.bat
```

#### Error: "Scripts\activate.bat not found"
**Solution**:
```bash
# Recreate virtual environment
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 9. Performance Issues

#### Services are slow
**Solution**:
- Close unnecessary programs
- Ensure you have at least 2GB free RAM
- Check CPU usage in Task Manager

#### Demo takes too long
**Solution**:
- This is normal, demo takes ~30 seconds
- Wait for each phase to complete

### 10. Windows-Specific Issues

#### Error: "Execution of scripts is disabled"
**Solution**:
Run PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Error: "Access denied"
**Solution**:
- Run terminal as Administrator
- Check antivirus isn't blocking Python

## Diagnostic Tools

### Check Everything
```bash
check_errors.bat
```

This will check:
- Python installation
- Virtual environment
- Imports
- Port availability

### Test Single Service
```bash
test_single_service.bat
```

This will test one service at a time to identify issues.

### Run Test Suite
```bash
venv\Scripts\activate
python test_services.py
```

This runs comprehensive tests on all components.

## Step-by-Step Debugging

### If Nothing Works:

1. **Clean Start**:
   ```bash
   # Delete everything
   rmdir /s /q venv
   rmdir /s /q data
   rmdir /s /q logs
   rmdir /s /q models
   
   # Start fresh
   setup.bat
   run_all_services.bat
   ```

2. **Check Python**:
   ```bash
   python --version
   # Should show 3.9 or higher
   ```

3. **Check Dependencies**:
   ```bash
   venv\Scripts\activate
   pip list
   # Should show all packages from requirements.txt
   ```

4. **Test Imports**:
   ```bash
   venv\Scripts\activate
   python test_services.py
   # Should show all tests passing
   ```

5. **Start Services One by One**:
   ```bash
   # Terminal 1
   venv\Scripts\activate
   python services/ingestion_api/app.py
   
   # Terminal 2
   venv\Scripts\activate
   python services/prediction_service/app.py
   
   # etc.
   ```

## Getting Help

### Check Logs
All services log to `logs/` directory:
- `ingestion_api.log`
- `prediction_service.log`
- `drift_monitor.log`
- `retraining_worker.log`
- `dashboard.log`

### Check Database
```bash
sqlite3 data/pipeline.db
.tables
.quit
```

### System Information
```bash
# Check Python
python --version

# Check pip
pip --version

# Check installed packages
pip list

# Check ports
netstat -ano | findstr :8001
netstat -ano | findstr :8002
netstat -ano | findstr :8050
```

## Still Having Issues?

1. Read `GETTING_STARTED.md` for detailed setup
2. Read `README.md` for complete documentation
3. Check `TESTING_RESULTS.md` for known working configuration
4. Run `check_errors.bat` for automated diagnostics

## Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Port in use | `taskkill /PID <pid> /F` |
| Import error | `pip install -r requirements.txt --force-reinstall` |
| Database locked | Delete `data/pipeline.db` |
| Services won't start | Run `setup.bat` again |
| Demo fails | Ensure services running first |
| Virtual env issues | Delete `venv/` and run `setup.bat` |

## Prevention

To avoid issues:
1. Always run `setup.bat` first (one time)
2. Always activate virtual environment before running Python
3. Always start services before running demo
4. Always wait 10 seconds after starting services
5. Always close services properly (close windows or run stop script)
