# DNS Level Connection Interception, Analysis, and Maliciousness Scoring System

A Python-based capstone project for analyzing DNS traffic to detect potentially malicious network activity through packet capture, analysis, and intelligent scoring algorithms.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Administrative privileges (for packet capture)
- Git

### Setup
```bash
# Clone the repository
git clone https://github.com/Zeviant/Capstone.git
cd Capstone

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## 📋 Features

- **Real-time DNS Traffic Monitoring** - Capture and analyze DNS queries and responses
- **Maliciousness Scoring** - Intelligent scoring system to identify suspicious domains
- **Pattern Recognition** - Detect malicious patterns using entropy analysis and known indicators
- **Data Export** - Export results to JSON, CSV, and generate detailed reports
- **Configurable Analysis** - Customize analysis parameters through YAML configuration
- **Comprehensive Logging** - Detailed logging for monitoring and debugging

## 🏗️ Project Structure

```
Capstone/
├── main.py                    # Main application entry point
├── requirements.txt           # Python dependencies
├── src/
│   ├── dns_analyzer/         # Core DNS analysis engine
│   ├── utils/                # Scoring and data handling utilities
│   └── config/               # Configuration management
├── tests/                    # Test suite
├── docs/                     # Documentation
├── data/                     # Analysis results (auto-created)
└── logs/                     # Application logs (auto-created)
```

## 🛠️ Development

### For Collaboration
This project is set up for collaborative development in VS Code:

1. **Read the collaboration guide**: [docs/COLLABORATION.md](docs/COLLABORATION.md)
2. **Follow the setup guide**: [docs/SETUP.md](docs/SETUP.md)
3. **Use VS Code Live Share** for real-time collaboration
4. **Follow the Git workflow** described in the documentation

### Running Tests
```bash
pytest tests/                    # Run all tests
pytest --cov=src tests/         # Run with coverage
```

### Code Quality
```bash
black src/ tests/               # Format code
flake8 src/ tests/              # Lint code
mypy src/                       # Type checking
```

## 📊 Usage Examples

### Basic Analysis
```bash
# Capture DNS traffic for 5 minutes with default settings
python main.py

# Use custom configuration
python main.py --config src/config/default.yaml --log-level DEBUG

# Monitor specific interface (requires admin privileges)
python main.py --interface eth0 --output data/network_analysis.json
```

### Configuration
Customize analysis through `src/config/default.yaml`:
- Capture timeout and packet limits
- Scoring thresholds and algorithms
- Output formats and locations
- Logging levels and destinations

## 🔍 How It Works

1. **Packet Capture**: Uses Scapy to capture DNS traffic on specified interfaces
2. **Query Analysis**: Extracts DNS queries and responses for analysis
3. **Maliciousness Scoring**: Applies multiple scoring algorithms:
   - Pattern matching against known malicious indicators
   - Entropy analysis for detecting algorithmically generated domains
   - Domain characteristic analysis (length, subdomains, TLD)
4. **Results Export**: Saves analysis results in multiple formats with summary reports

## 🛡️ Security & Requirements

### Network Permissions
- Requires elevated privileges for packet capture
- Windows: Run as Administrator
- Linux/macOS: Run with sudo or configure capabilities

### Dependencies
Key dependencies include:
- `scapy` - Network packet analysis
- `dnspython` - DNS toolkit
- `pandas` - Data analysis
- `PyYAML` - Configuration management

See `requirements.txt` for complete list.

## 📖 Documentation

- [Setup Guide](docs/SETUP.md) - Detailed installation and configuration
- [Collaboration Guide](docs/COLLABORATION.md) - Working together effectively
- [Configuration Reference](src/config/default.yaml) - All configuration options

## 🤝 Contributing

This is a capstone project designed for collaborative development:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is for educational purposes as part of a capstone project.

## 👥 Authors

- [Add your names here]

## 🙏 Acknowledgments

- Course instructors and advisors
- Open source libraries used in this project
- Network security research community

---

**Note**: This tool is for educational and authorized network analysis only. Ensure you have permission to monitor network traffic and comply with all applicable laws and regulations.
