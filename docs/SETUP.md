# Project Setup Guide

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/Zeviant/Capstone.git
cd Capstone
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Create Required Directories
The following directories will be created automatically when you run the application:
- `data/` - For analysis results
- `logs/` - For log files

### 4. Test the Installation
```bash
# Run tests to verify setup
pytest tests/

# Run the application (basic test)
python main.py --help
```

## Development Environment

### VS Code Setup
1. Open the project folder in VS Code
2. VS Code will prompt to install recommended extensions:
   - Python
   - Python Linting (Flake8)
   - Python Formatting (Black)
   - Python Type Checking (MyPy)
   - Live Share (for collaboration)

3. Select Python interpreter:
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
   - Type "Python: Select Interpreter"
   - Choose the interpreter from your `venv` folder

### Configuration
The project includes:
- `.vscode/settings.json` - VS Code workspace settings
- `.vscode/extensions.json` - Recommended extensions
- `src/config/default.yaml` - Application configuration

## Running the Application

### Basic Usage
```bash
# Run with default settings (captures for 5 minutes)
python main.py

# Run with custom settings
python main.py --config src/config/default.yaml --log-level DEBUG

# Specify network interface (requires admin privileges)
python main.py --interface eth0

# Custom output file
python main.py --output data/my_analysis.json
```

### Command Line Options
- `--config PATH` - Configuration file path
- `--log-level LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--interface NAME` - Network interface to monitor
- `--output PATH` - Output file for results

## Network Requirements

### Packet Capture Privileges
To capture network packets, you'll need elevated privileges:

**Windows:**
- Run VS Code or command prompt as Administrator

**macOS/Linux:**
- Run with sudo: `sudo python main.py`
- Or configure capabilities: `sudo setcap cap_net_raw+ep $(which python)`

### Network Interfaces
To list available network interfaces:
```bash
# On Windows
ipconfig
netsh interface show interface

# On macOS/Linux
ifconfig
ip link show
```

## Project Structure

```
Capstone/
├── main.py                    # Main application entry point
├── requirements.txt           # Python dependencies
├── .gitignore                # Git ignore rules
│
├── .vscode/                   # VS Code configuration
│   ├── settings.json         # Workspace settings
│   └── extensions.json       # Recommended extensions
│
├── src/                       # Source code
│   ├── dns_analyzer/         # DNS analysis modules
│   │   ├── __init__.py
│   │   └── core.py           # Main analyzer class
│   │
│   ├── utils/                # Utility modules
│   │   ├── __init__.py
│   │   ├── scoring.py        # Maliciousness scoring
│   │   └── data_handler.py   # Data management
│   │
│   └── config/               # Configuration
│       ├── __init__.py
│       ├── settings.py       # Config loading
│       └── default.yaml      # Default configuration
│
├── tests/                     # Test files
│   ├── __init__.py
│   ├── test_scoring.py
│   └── test_config.py
│
├── docs/                      # Documentation
│   ├── SETUP.md              # This file
│   └── COLLABORATION.md      # Collaboration guide
│
├── data/                      # Analysis results (created at runtime)
└── logs/                      # Log files (created at runtime)
```

## Dependencies

### Core Dependencies
- `scapy` - Network packet capture and analysis
- `dnspython` - DNS toolkit
- `pandas` - Data analysis
- `numpy` - Numerical computing
- `PyYAML` - Configuration file parsing

### Development Dependencies
- `pytest` - Testing framework
- `black` - Code formatting
- `flake8` - Code linting
- `mypy` - Type checking

### Optional Dependencies
See `requirements.txt` for the complete list with version specifications.

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_scoring.py

# Run with coverage report
pytest --cov=src tests/

# Verbose output
pytest -v tests/
```

### Test Structure
- `tests/test_scoring.py` - Tests for maliciousness scoring
- `tests/test_config.py` - Tests for configuration management
- Add new test files as you develop new features

## Development Workflow

### Code Formatting
```bash
# Format all Python files
black src/ tests/

# Check formatting without changing files
black --check src/ tests/
```

### Linting
```bash
# Run linter
flake8 src/ tests/

# With specific configuration
flake8 --max-line-length=88 src/ tests/
```

### Type Checking
```bash
# Check types
mypy src/
```

## Troubleshooting

### Common Issues

#### ImportError: No module named 'scapy'
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt`

#### Permission denied for packet capture
- Run as administrator/sudo
- Or use test mode with sample data

#### VS Code not recognizing Python interpreter
- Press `Ctrl+Shift+P` → "Python: Select Interpreter"
- Choose the interpreter from your `venv` folder

#### Tests failing
- Ensure all dependencies are installed
- Check that you're in the project root directory
- Verify Python path is correctly set

### Getting Help
1. Check this documentation
2. Review error messages in logs (stored in `logs/` directory)
3. Run with `--log-level DEBUG` for more detailed output
4. Check GitHub issues for similar problems

## Next Steps

After setup:
1. Read the [Collaboration Guide](COLLABORATION.md)
2. Explore the codebase starting with `main.py`
3. Run the tests to understand the expected behavior
4. Try capturing some DNS traffic on your network
5. Begin implementing additional features for your capstone project

Good luck with your DNS analysis project! 🔍🌐