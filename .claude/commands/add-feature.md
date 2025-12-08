# Add Feature Command

Scaffold a new feature with proper structure and test file.

## Usage
`/add-feature <feature_name> [module]`

## Arguments
- `$ARGUMENTS` - Feature name and optional module (default: core)

## Execution

When adding a new feature, follow these steps:

### 1. Parse Arguments
Extract feature name and module from: **$ARGUMENTS**
- If only one word: feature_name = argument, module = core
- If two words: feature_name = first, module = second

### 2. Create Feature Module
Create the feature file in the appropriate location:
- `core/` - Business logic (default)
- `gui_qt/widgets/` - UI components
- `gui_qt/dialogs/` - Modal dialogs
- `data_sources/` - External API clients

### 3. File Template
```python
"""
{Feature Name} - {Brief description}

This module provides:
-
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class {FeatureName}Config:
    """Configuration for {feature_name}."""
    pass


class {FeatureName}:
    """
    {Brief description of what this class does}.

    Usage:
        >>> feature = {FeatureName}()
        >>> result = feature.process(data)
    """

    def __init__(self, config: Optional[{FeatureName}Config] = None):
        self.config = config or {FeatureName}Config()

    def process(self, data):
        """Process the input data."""
        raise NotImplementedError("Implement this method")
```

### 4. Create Test File
Create corresponding test in `tests/unit/{module}/test_{feature_name}.py`:

```python
"""Tests for {feature_name} module."""

import pytest
from {module}.{feature_name} import {FeatureName}, {FeatureName}Config


class Test{FeatureName}:
    """Test suite for {FeatureName}."""

    @pytest.fixture
    def feature(self):
        """Create a {FeatureName} instance for testing."""
        return {FeatureName}()

    def test_init_default_config(self, feature):
        """Test initialization with default config."""
        assert feature.config is not None

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = {FeatureName}Config()
        feature = {FeatureName}(config=config)
        assert feature.config == config

    @pytest.mark.skip(reason="Implement when process() is defined")
    def test_process(self, feature):
        """Test the process method."""
        pass
```

### 5. Report
After creating files:
- List created files
- Remind about adding to `__init__.py` if needed
- Suggest next steps for implementation
