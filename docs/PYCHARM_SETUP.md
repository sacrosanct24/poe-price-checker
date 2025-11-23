# PyCharm + Continue Setup Guide

This guide explains how to use [Continue](https://continue.dev) as an AI coding assistant inside PyCharm for the PoE Price Checker project.

---

## 🚀 Quick Start

### 1. Install the Continue Plugin

1. Open PyCharm
2. Go to **Settings/Preferences** → **Plugins**
3. Search for **"Continue"**
4. Click **Install**
5. Restart PyCharm

### 2. Configure Continue

The repository already includes a `.continue/config.json` with project-specific settings. Continue will automatically detect and use this configuration.

#### API Key Setup

You'll need to add your API key for the AI model:

1. Open Continue panel in PyCharm (usually on the right sidebar)
2. Click the gear icon (⚙️) to open settings
3. Add your API key for Claude 3.5 Sonnet (or configure a different model)

**Supported providers:**
- **Anthropic** (Claude) - Recommended
- **OpenAI** (GPT-4)
- **Ollama** (Local models)
- **Azure OpenAI**
- **AWS Bedrock**

### 3. Start Using Continue

Press **Ctrl+L** (or **Cmd+L** on Mac) to open the Continue chat panel.

---

## 🎯 Project-Specific Commands

The configuration includes custom commands tailored for this project:

### `/test` - Generate Pytest Tests

Highlight code and run `/test` to generate unit tests following the project's patterns in `tests/`.

**Example:**
```python
# Highlight this function
def parse_item_rarity(text: str) -> str:
    if "Rarity: Unique" in text:
        return "unique"
    return "normal"
```

Then type `/test` in Continue to generate:
```python
def test_parse_item_rarity():
    assert parse_item_rarity("Rarity: Unique\nItem Name") == "unique"
    assert parse_item_rarity("Rarity: Normal\nItem Name") == "normal"
```

### `/docs` - Generate Documentation

Highlight code and run `/docs` to generate comprehensive documentation following the style in `docs/`.

### `/review` - Code Review

Get AI-powered code review checking for:
- Bugs and edge cases
- Performance issues
- Code style and best practices
- Type hints and documentation

### `/plugin` - Create Plugin Boilerplate

Generate plugin boilerplate following `PLUGIN_SPEC.md`.

---

## 🔧 Context Providers

Continue is configured with these context providers for the project:

| Provider | Shortcut | Description |
|----------|----------|-------------|
| **@code** | `@code` | Reference specific files/functions |
| **@docs** | `@docs` | Search project documentation |
| **@diff** | `@diff` | Include git diff in context |
| **@terminal** | `@terminal` | Include terminal output |
| **@problems** | `@problems` | Include PyCharm warnings/errors |
| **@folder** | `@folder` | Reference entire directories |
| **@codebase** | `@codebase` | Search entire codebase |

**Example usage:**
```
How does @code core/item_parser.py handle influenced items?
```

---

## 💡 Common Workflows

### 1. Understanding Existing Code

```
Explain how @code core/price_multi.py fetches prices from multiple sources
```

### 2. Adding a New Feature

```
I want to add support for pricing cluster jewels. 
Look at @code core/item_parser.py and @docs DEVELOPMENT_GUIDE.md 
and help me implement this.
```

### 3. Fixing a Bug

```
I'm getting an error when parsing divination cards.
Here's the @terminal output: [paste error]
Check @code core/item_parser.py and help me fix it.
```

### 4. Writing Tests

```
Highlight the function you want to test
Run: /test
```

### 5. Refactoring

```
This function @code core/database.py::get_sales is too complex.
Help me refactor it following the project's patterns.
```

---

## 🎨 Tab Autocomplete

Continue includes tab autocomplete powered by **Starcoder 7b** (local model via Ollama).

### Setup (Optional)

To enable local autocomplete:

1. Install [Ollama](https://ollama.ai)
2. Pull the model:
   ```bash
   ollama pull starcoder2:7b
   ```
3. Start coding - Continue will provide inline suggestions

You can change the autocomplete model in `.continue/config.json`:

```json
{
  "tabAutocompleteModel": {
    "title": "Your Model",
    "provider": "ollama",
    "model": "codellama:7b"
  }
}
```

---

## 📁 Configuration Files

The `.continue/` directory contains:

| File | Purpose |
|------|---------|
| **config.json** | Main Continue configuration |
| **config.py.json** | Python-specific settings |
| **.continueignore** | Files/folders to exclude from context |

### Customizing Configuration

Edit `.continue/config.json` to:
- Add/remove models
- Configure custom commands
- Adjust context providers
- Add external documentation sources

**Example: Adding OpenAI GPT-4**

```json
{
  "models": [
    {
      "title": "GPT-4",
      "provider": "openai",
      "model": "gpt-4-turbo-preview",
      "apiKey": "sk-..."
    }
  ]
}
```

---

## 🔍 Codebase Indexing

Continue automatically indexes the codebase for semantic search.

### What gets indexed?
- All Python files
- Documentation in `docs/`
- Test files
- Configuration files

### What's excluded?
Check `.continue/.continueignore` for excluded patterns:
- `__pycache__/`, `*.pyc`
- Virtual environments
- Test artifacts (`.coverage`, `.pytest_cache/`)
- Database files (`.db`, `.sqlite`)

---

## 🐛 Troubleshooting

### Continue panel not showing

1. Go to **View** → **Tool Windows** → **Continue**
2. Or use **Ctrl+Shift+A** and search "Continue"

### API key errors

1. Click gear icon (⚙️) in Continue panel
2. Verify your API key is correct
3. Check your API quota/billing

### Slow responses

1. Try switching to a different model
2. Use a local model via Ollama for faster responses
3. Reduce context by being more specific with queries

### Autocomplete not working

1. Ensure Ollama is installed and running
2. Pull the model: `ollama pull starcoder2:7b`
3. Check `.continue/config.json` has correct model config

---

## 🎓 Best Practices

### 1. Be Specific with Context

❌ **Bad:**
```
How does pricing work?
```

✅ **Good:**
```
How does @code core/price_multi.py aggregate prices from 
PoE Ninja and derived sources?
```

### 2. Reference Documentation

```
I want to add a new pricing source. 
Check @docs DEVELOPMENT_GUIDE.md and @docs PLUGIN_SPEC.md
and show me the steps.
```

### 3. Include Error Context

```
I'm getting this error:
@terminal [paste error]

Looking at @code core/database.py, what's causing this?
```

### 4. Iterative Refinement

Start broad, then drill down:
1. "Explain the pricing system architecture"
2. "Show me how PoE Ninja integration works"
3. "Help me add support for pricing influenced items"

---

## 📚 Additional Resources

- [Continue Documentation](https://continue.dev/docs)
- [Project Development Guide](./DEVELOPMENT_GUIDE.md)
- [Plugin Specification](./PLUGIN_SPEC.md)
- [Testing Guide](./TESTING_GUIDE.md)

---

## 🤝 Contributing

If you improve the Continue configuration or add useful custom commands, please:

1. Update `.continue/config.json`
2. Document changes in this file
3. Submit a PR

---

**Questions?** Open an issue or ask Continue:
```
@docs PYCHARM_SETUP.md - I have a question about [your question]
```
