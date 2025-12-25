"""ML data collection package."""

__all__ = [
    "AffixExtractor",
    "ListingLifecycleTracker",
    "MLCollectionOrchestrator",
    "MLPollingService",
    "ML_COLLECTION_CONFIG",
]


def __getattr__(name: str):
    if name == "AffixExtractor":
        from ml.collection.affix_extractor import AffixExtractor

        return AffixExtractor
    if name == "ListingLifecycleTracker":
        from ml.collection.lifecycle_tracker import ListingLifecycleTracker

        return ListingLifecycleTracker
    if name == "MLCollectionOrchestrator":
        from ml.collection.orchestrator import MLCollectionOrchestrator

        return MLCollectionOrchestrator
    if name == "MLPollingService":
        from ml.collection.polling_service import MLPollingService

        return MLPollingService
    if name == "ML_COLLECTION_CONFIG":
        from ml.collection.config import ML_COLLECTION_CONFIG

        return ML_COLLECTION_CONFIG
    raise AttributeError(f"module {__name__} has no attribute {name}")
