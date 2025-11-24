# Documentation Index

Complete documentation for PoE Price Checker, organized by category.

---

## 🚀 Quick Start

**New to the project?** Start here:
1. [README](../README.md) - Project overview
2. [Development Guide](development/DEVELOPMENT_GUIDE.md) - Architecture & setup
3. [Test Suite Guide](testing/TEST_SUITE_GUIDE.md) - Running tests

---

## 📁 Documentation Structure

```
docs/
├── development/        # Architecture, setup, plugins
├── testing/           # Test suite, coverage, history
├── mcp/              # AI assistant integration
├── troubleshooting/  # Bug fixes, diagnostics
└── roadmap.md        # Future features
```

---

## 💻 Development

### Getting Started
- **[Development Guide](development/DEVELOPMENT_GUIDE.md)** - Complete development setup
  - Architecture overview
  - Code organization
  - Development workflow
  - Best practices

- **[PyCharm Setup](development/PYCHARM_SETUP.md)** - AI-assisted development
  - Continue AI assistant setup
  - Keyboard shortcuts
  - Productivity tips

### Extending the App
- **[Plugin Spec](development/PLUGIN_SPEC.md)** - Build your own plugins
  - Plugin API documentation
  - Example plugins
  - Best practices

### Project Context
- **[Context](development/Context.md)** - Design decisions and history
- **[Code Review](development/code_review.md)** - Code quality notes

---

## 🧪 Testing

### Test Guides
- **[Test Suite Guide](testing/TEST_SUITE_GUIDE.md)** - Complete testing guide
  - Running tests
  - Writing new tests
  - Coverage reports
  - Best practices

- **[Testing Guide](testing/TESTING_GUIDE.md)** - Original testing documentation
  - Test organization
  - Common patterns
  - CI/CD setup

### Test History
- **[Testing History](testing/TESTING_HISTORY.md)** - Journey from 109 → 163 tests
  - All fixes documented
  - Lessons learned
  - Metrics progression

- **[Test Summary](testing/SUMMARY.md)** - Final test results
- **[Test Fixes](testing/FIXES.md)** - Detailed fix explanations
- **[Additional Tests](testing/ADDITIONAL_TESTS.md)** - Edge cases added

### Coverage
- **[Coverage Gaps](testing/COVERAGE_GAPS.md)** - Areas needing more tests
  - High priority gaps
  - Recommended tests
  - Coverage analysis

---

## 🤖 MCP Integration (AI Assistant)

### Quick Start
- **[Quick Start](mcp/QUICK_START.md)** - 5-minute setup guide
  - Installation (3 commands)
  - Testing in 2 minutes
  - Claude Desktop setup

### Complete Guide
- **[MCP Integration](mcp/MCP_INTEGRATION.md)** - Full integration guide
  - What is MCP?
  - Setup instructions
  - Usage examples
  - Architecture
  - Troubleshooting

### Decision Making
- **[Why MCP?](mcp/WHY_MCP.md)** - Should you use MCP?
  - Benefits analysis
  - Cost breakdown
  - Comparison with alternatives
  - Real-world examples

### Setup Details
- **[Setup Guide](mcp/SETUP_GUIDE.md)** - Detailed setup instructions
- **[Claude Setup](mcp/CLAUDE_SETUP.md)** - Claude Desktop specific setup
- **[Summary](mcp/SUMMARY.md)** - Quick overview

---

## 🔧 Troubleshooting

### Parser Issues
- **[Parser Issues](troubleshooting/PARSER_ISSUES.md)** - "Unknown Item" problems
  - Diagnostic tool usage
  - Common causes
  - Real-world scenarios
  - Solutions

- **[Item Class Bug](troubleshooting/ITEM_CLASS_BUG.md)** - Fixed: PoE clipboard format
  - Bug description
  - Root cause analysis
  - Fix implementation
  - Regression tests

### Other Issues
- **[Unknown Item](troubleshooting/UNKNOWN_ITEM.md)** - Legacy troubleshooting doc
  - Error messages
  - Log analysis
  - Step-by-step fixes

---

## 📋 Project Management

### Roadmap
- **[Roadmap](roadmap.md)** - Future features and milestones
  - Planned features
  - Timeline
  - Priorities

---

## 📊 Project Stats

### Test Suite
- **Tests:** 163 passing (98% pass rate)
- **Coverage:** ~60% overall
- **Runtime:** ~3 seconds
- **Status:** ✅ Production ready

### MCP Integration
- **Tools:** 4 (parse, price, sales, search)
- **Resources:** 1 (config)
- **Prompts:** 1 (analyze)
- **Status:** ✅ Ready to use

### Documentation
- **Total Docs:** 25+ files
- **Categories:** 4 (dev, test, mcp, troubleshooting)
- **Words:** ~20,000+
- **Status:** ✅ Comprehensive

---

## 🎯 Common Tasks

### First Time Setup
1. Read [Development Guide](development/DEVELOPMENT_GUIDE.md)
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `pytest`
4. Run app: `python poe_price_checker.py`

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=core --cov-report=html

# Specific category
pytest tests/unit/
```

### Setting Up MCP
```bash
# Install MCP
pip install "mcp[cli]"

# Test server
mcp dev mcp_poe_server.py

# Install to Claude
mcp install mcp_poe_server.py
```

### Building a Plugin
1. Read [Plugin Spec](development/PLUGIN_SPEC.md)
2. Create file in `plugins/` directory
3. Implement `register_plugin()` function
4. Restart app to load plugin

### Troubleshooting Parser
```bash
# Run diagnostic tool
python debug_clipboard.py

# Copy item from PoE
# Press ENTER in tool

# See diagnosis and fix
```

---

## 🔗 External Links

- **Python:** https://www.python.org/
- **pytest:** https://pytest.org/
- **MCP:** https://modelcontextprotocol.io
- **Claude Desktop:** https://claude.ai/download
- **Continue:** https://continue.dev
- **Path of Exile:** https://pathofexile.com

---

## 📝 Contributing

When adding documentation:
1. Place in appropriate subdirectory
2. Update this index
3. Link from README if major doc
4. Use clear, descriptive names
5. Include examples and code samples

---

## ✨ Documentation Quality

- ✅ **Organized** - Clear category structure
- ✅ **Comprehensive** - 25+ documents
- ✅ **Searchable** - Index with descriptions
- ✅ **Up-to-date** - Reflects current code
- ✅ **Practical** - Lots of examples
- ✅ **Well-linked** - Easy navigation

---

*Last Updated: 2024-11-23*  
*Total Documentation: 25+ files, ~20,000 words*  
*Status: Complete and Production Ready* ✅
