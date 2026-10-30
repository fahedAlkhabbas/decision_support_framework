> **Note:** this document describes version 1 of the code. For version 2 (revision) see the top-level README.md, EXPERIMENTS.md and MODEL.md; some function signatures below have changed.

# Troubleshooting Guide

## Import Errors

### Error: `ModuleNotFoundError: No module named 'core'`

**Cause**: Python cannot find the framework modules because the framework directory is not in the Python path.

**Solutions** (in order of preference):

#### Solution 1: Run from the Framework Directory (Simplest)
```bash
cd /path/to/wildguard_framework
python run.py
```

or

```bash
cd /path/to/wildguard_framework
python main.py
```

#### Solution 2: Use Absolute Path to run.py
```bash
python /path/to/wildguard_framework/run.py
```

#### Solution 3: Install as a Package
```bash
cd /path/to/wildguard_framework
pip install -e .
python -m wildguard_framework
```

#### Solution 4: Set PYTHONPATH Environment Variable
```bash
# On macOS/Linux
export PYTHONPATH="/path/to/wildguard_framework:$PYTHONPATH"
python main.py

# On Windows
set PYTHONPATH=C:\path\to\wildguard_framework;%PYTHONPATH%
python main.py
```

## Dependency Errors

### Error: `ModuleNotFoundError: No module named 'ortools'`

**Solution**: Install the required package
```bash
pip install ortools
```

### Error: `ModuleNotFoundError: No module named 'psutil'`

**Solution**: Install the required package
```bash
pip install psutil
```

### Install All Dependencies at Once
```bash
pip install ortools psutil
```

## Runtime Errors

### Error: `No feasible deployment found`

**Causes**:
- System requirements are too strict
- Infrastructure is too small
- Constraints are conflicting

**Solutions**:

1. **Try with more nodes**:
   ```python
   ok, time, energy, nodes = ui.run_deployment_scenario(
       num_nodes=80,  # Increase from 40
       system_nfrs=system_nfrs,
       objective="feasible"
   )
   ```

2. **Relax system requirements**:
   ```python
   system_nfrs = {
       "availability": 95.0,        # Reduce from 99.5
       "performance": {
           "max_delay": 10000,      # Increase from 5000
           "min_throughput": 10     # Reduce from 30
       },
       "security": 80,              # Reduce from 96
   }
   ```

3. **Try feasible objective first**:
   ```python
   # Instead of "minimize" or "maximize"
   ok, time, energy, nodes = ui.run_deployment_scenario(
       num_nodes=40,
       system_nfrs=system_nfrs,
       objective="feasible"  # Fastest
   )
   ```

### Error: Script Takes Too Long to Run

**Causes**:
- Large number of nodes (> 100)
- Very strict constraints
- Optimization objective (minimize/maximize) takes longer than feasible

**Solutions**:

1. **Use fewer nodes**:
   ```python
   ok, time, energy, nodes = ui.run_deployment_scenario(
       num_nodes=40,  # Reduce from 80+
       system_nfrs=system_nfrs,
       objective="feasible"
   )
   ```

2. **Use feasible objective**:
   ```python
   # Feasible is faster than minimize/maximize
   objective="feasible"
   ```

3. **Relax constraints**:
   See "No feasible deployment found" section above

## File Organization Issues

### Error: `FileNotFoundError` or Path Issues

**Solution**: Make sure you're running from the correct directory or using absolute paths.

**Correct ways to run**:

```bash
# Method 1: From framework directory
cd /path/to/wildguard_framework
python run.py

# Method 2: Using absolute path
python /path/to/wildguard_framework/run.py

# Method 3: After installation
pip install -e /path/to/wildguard_framework
python -m wildguard_framework
```

## Python Version Issues

### Error: `SyntaxError` or Compatibility Issues

**Cause**: Using Python < 3.7

**Solution**: Use Python 3.7 or higher
```bash
python3 --version  # Check version
python3 run.py     # Use python3 explicitly
```

## macOS Specific Issues

### Error: `ModuleNotFoundError` on macOS

**Cause**: Using system Python instead of the correct Python installation

**Solution 1**: Use the full path to Python
```bash
/usr/local/bin/python3 /path/to/run.py
```

**Solution 2**: Use conda or virtualenv
```bash
conda activate base
python /path/to/run.py
```

**Solution 3**: Install with pip and use module execution
```bash
pip install -e /path/to/wildguard_framework
python -m wildguard_framework
```

## Windows Specific Issues

### Error: `ModuleNotFoundError` on Windows

**Solution 1**: Use backslashes in path
```bash
python C:\path\to\wildguard_framework\run.py
```

**Solution 2**: Use forward slashes (Python accepts both)
```bash
python C:/path/to/wildguard_framework/run.py
```

**Solution 3**: Set PYTHONPATH
```bash
set PYTHONPATH=C:\path\to\wildguard_framework;%PYTHONPATH%
python main.py
```

## Getting Help

If you encounter an issue not listed here:

1. **Check the error message carefully** - It usually indicates the root cause
2. **Try Solution 1** - Run from the framework directory
3. **Check dependencies** - Run `pip install ortools psutil`
4. **Review USAGE.md** - For detailed usage examples
5. **Review ARCHITECTURE.md** - For technical details

## Quick Checklist

- [ ] Python 3.7+ installed: `python --version`
- [ ] Dependencies installed: `pip install ortools psutil`
- [ ] Framework directory exists: `ls /path/to/wildguard_framework`
- [ ] run.py exists: `ls /path/to/wildguard_framework/run.py`
- [ ] Can run from framework dir: `cd /path/to/wildguard_framework && python run.py`
- [ ] Can run with absolute path: `python /path/to/wildguard_framework/run.py`

## Recommended Approach

For the most reliable experience:

```bash
# 1. Navigate to framework directory
cd /path/to/wildguard_framework

# 2. Run the script
python run.py
```

This avoids all path-related issues.
