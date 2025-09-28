# Collaboration Guide

This guide will help you and your friend work together on the DNS Level Connection Interception, Analysis, and Maliciousness Scoring System capstone project.

## Setting Up for Collaboration

### 1. Prerequisites
Make sure both of you have:
- Python 3.8 or higher
- Git installed
- Visual Studio Code
- Administrative privileges (for packet capture)

### 2. Clone the Repository
```bash
git clone https://github.com/Zeviant/Capstone.git
cd Capstone
```

### 3. Set Up Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. VS Code Setup
1. Open the project in VS Code
2. Install recommended extensions (VS Code will prompt you)
3. Select the Python interpreter from your virtual environment
4. The workspace is already configured for collaborative development

## Working Together

### Git Workflow
1. **Always pull before starting work:**
   ```bash
   git pull origin main
   ```

2. **Create feature branches for new work:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Commit frequently with clear messages:**
   ```bash
   git add .
   git commit -m "Add DNS packet filtering functionality"
   ```

4. **Push your branch and create pull requests:**
   ```bash
   git push origin feature/your-feature-name
   ```

### VS Code Live Share (Recommended)
1. Install the "Live Share" extension in VS Code
2. One person starts a Live Share session
3. Share the link with your friend
4. Both can edit code simultaneously and see each other's changes in real-time

### Division of Work Suggestions

#### Person 1: Core DNS Analysis
- `src/dns_analyzer/core.py` - Main analysis engine
- `src/utils/scoring.py` - Maliciousness scoring algorithms
- Packet capture and processing logic

#### Person 2: Data Handling & UI
- `src/utils/data_handler.py` - Data storage and export
- Reporting and visualization features
- Configuration management improvements

#### Shared Responsibilities
- Testing (`tests/` directory)
- Documentation updates
- Configuration tuning
- Code reviews

## Running the Project

### Basic Usage
```bash
# Run with default settings
python main.py

# Run with custom configuration
python main.py --config src/config/default.yaml --log-level DEBUG

# Monitor specific network interface
python main.py --interface eth0 --output data/my_analysis.json
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_scoring.py

# Run with coverage
pytest --cov=src tests/
```

### Code Quality
```bash
# Format code
black src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/
```

## Project Structure
```
Capstone/
├── main.py                 # Main entry point
├── requirements.txt        # Python dependencies
├── src/
│   ├── dns_analyzer/      # Core analysis modules
│   ├── utils/             # Utility functions
│   └── config/            # Configuration management
├── tests/                 # Test files
├── docs/                  # Documentation
├── data/                  # Analysis results (created at runtime)
└── logs/                  # Log files (created at runtime)
```

## Communication

### Daily Standup (Suggested)
- What did you work on yesterday?
- What will you work on today?
- Any blockers or issues?

### Code Review Process
1. Create pull requests for all changes
2. Review each other's code before merging
3. Test changes locally before approving
4. Use GitHub's review features for feedback

### Issue Tracking
Use GitHub Issues to:
- Track bugs and feature requests
- Assign tasks to each other
- Document decisions and discussions

## Best Practices

### Code Style
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Write docstrings for all functions and classes
- Keep functions small and focused

### Git Commits
- Write clear, descriptive commit messages
- Make atomic commits (one logical change per commit)
- Reference issue numbers when applicable

### Testing
- Write tests for new functionality
- Run tests before pushing changes
- Maintain test coverage above 80%

### Documentation
- Update documentation when adding features
- Comment complex algorithms
- Keep README.md up to date

## Troubleshooting

### Common Issues

#### Permission Errors (Packet Capture)
- Run as administrator/sudo when capturing packets
- Consider using test data for development

#### Import Errors
- Ensure virtual environment is activated
- Verify all dependencies are installed
- Check PYTHONPATH in VS Code settings

#### Git Merge Conflicts
- Communicate before working on the same files
- Use VS Code's merge conflict resolution tools
- When in doubt, ask your partner before resolving

### Getting Help
- Check the project documentation
- Search GitHub issues for similar problems
- Ask your project partner
- Consult course materials or instructor

## Security Notes
- Never commit sensitive data or credentials
- Use environment variables for sensitive configuration
- Be careful when sharing packet capture data
- Follow your institution's network usage policies

Happy coding! 🚀