# Continue Configuration

This directory contains the [Continue](https://continue.dev) AI assistant configuration for the PoE Price Checker project.

## 📁 Files

- **config.json** - Main Continue configuration (models, commands, context providers)
- **config.py.json** - Python-specific IDE settings
- **.continueignore** - Files/folders to exclude from AI context indexing

## 🚀 Quick Start

1. Install Continue plugin in PyCharm
2. Add your API key in Continue settings (gear icon ⚙️)
3. Press **Ctrl+L** (Cmd+L on Mac) to open chat
4. Start coding with AI assistance!

## 💡 Quick Commands

### Custom Commands (type `/` to see all)

- `/test` - Generate pytest tests
- `/docs` - Generate documentation
- `/review` - AI code review
- `/plugin` - Create plugin boilerplate
- `/edit` - Edit code inline
- `/commit` - Generate commit message
- `/cmd` - Generate shell command

### Context Providers (type `@` to see all)

- `@code` - Reference files/functions
- `@docs` - Search documentation
- `@codebase` - Search entire project
- `@diff` - Include git changes
- `@terminal` - Include terminal output
- `@problems` - Include IDE warnings

## 📖 Full Documentation

See **[docs/PYCHARM_SETUP.md](../docs/PYCHARM_SETUP.md)** for detailed setup and usage guide.

## ⚙️ Customization

Edit `config.json` to:
- Add/remove AI models
- Configure custom commands
- Adjust context providers
- Set up external docs

## 🔒 Privacy

- API keys are stored locally (not committed to git)
- Local cache excluded via `.gitignore`
- Telemetry disabled by default in config
