# ADR-002: Dependency Injection with AppContext

## Status
Accepted

## Context

Early versions of the codebase used global singletons and direct instantiation for services (Database, Config, PriceService, etc.). This led to:

- **Testing difficulties**: Hard to mock dependencies, tests had side effects
- **Hidden dependencies**: Classes instantiated services internally
- **Singleton conflicts**: GUI singletons (ThemeManager, WindowManager) caused test isolation issues
- **Initialization order problems**: Services depending on other services in unclear order

## Decision

Implement a centralized dependency injection container via `AppContext`:

```python
# core/app_context.py
class AppContext:
    """Centralized factory for application services."""

    _instance = None

    def __init__(self):
        self._config = None
        self._database = None
        self._price_service = None
        # ... lazy-initialized services

    def get_config(self) -> Config:
        if self._config is None:
            self._config = Config()
        return self._config

    def get_database(self) -> Database:
        if self._database is None:
            self._database = Database(self.get_config())
        return self._database

    def get_price_service(self) -> PriceService:
        if self._price_service is None:
            self._price_service = PriceService(
                self.get_config(),
                self.get_database()
            )
        return self._price_service
```

Usage pattern:
```python
# In application code
ctx = AppContext()
price_service = ctx.get_price_service()

# In tests
ctx = AppContext()
ctx._database = MockDatabase()  # Inject mock
```

## Consequences

### Positive
- **Testability**: Easy to inject mocks and stubs
- **Explicit dependencies**: All services obtained through AppContext
- **Lazy initialization**: Services created only when needed
- **Single source of truth**: One place to see all service relationships
- **Thread safety**: Can add locking if needed

### Negative
- **Service locator pattern**: Some consider this an anti-pattern vs. constructor injection
- **Runtime errors**: Missing dependencies discovered at runtime, not compile time
- **Hidden global state**: AppContext itself can become a hidden singleton

### Neutral
- Migration was incremental - old code still works during transition
- GUI singletons reset in `conftest.py` for test isolation

## References
- `core/app_context.py`
- `tests/conftest.py` (singleton reset fixtures)
