"""VideoPilot — Model Manager.

Downloads, caches, and loads AI models with RAM-awareness.
Prevents OOM by tracking memory usage.
"""

from __future__ import annotations

import gc
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from core.config import get_config


@dataclass(frozen=True)
class ModelSpec:
    """Specification for a downloadable model."""

    name: str
    source: str  # "huggingface", "url", "local"
    repo_id: str | None = None  # HuggingFace repo ID
    filename: str | None = None  # Specific file in the repo
    url: str | None = None  # Direct download URL
    size_mb: float = 0  # Approximate size in MB
    ram_required_mb: float = 0  # RAM needed when loaded
    gpu_required: bool = False


@dataclass
class ModelRegistry:
    """Registry of all available models and their status."""

    _specs: dict[str, ModelSpec] = field(default_factory=dict)
    _loaded: dict[str, Any] = field(default_factory=dict)
    _ram_used_mb: float = 0.0

    def register(self, spec: ModelSpec) -> None:
        """Register a model specification."""
        self._specs[spec.name] = spec
        logger.debug(f"Registered model: {spec.name} ({spec.size_mb}MB)")

    def is_downloaded(self, name: str) -> bool:
        """Check if a model's weights are downloaded."""
        config = get_config()
        spec = self._specs.get(name)
        if spec is None:
            return False
        model_dir = config.models_dir / name
        return model_dir.exists() and any(model_dir.iterdir())

    def is_loaded(self, name: str) -> bool:
        """Check if a model is currently loaded in memory."""
        return name in self._loaded

    def get_loaded(self, name: str) -> Any | None:
        """Get a currently loaded model."""
        return self._loaded.get(name)

    def can_load(self, name: str) -> bool:
        """Check if there's enough RAM to load this model."""
        spec = self._specs.get(name)
        if spec is None:
            return False
        config = get_config()
        max_ram = config.max_ram_gb * 1024  # Convert to MB
        return (self._ram_used_mb + spec.ram_required_mb) <= max_ram

    def load(self, name: str, loader_fn: Any) -> Any:
        """Load a model into memory using the provided loader function.

        Args:
            name: Model name from registry.
            loader_fn: Callable that returns the loaded model.

        Returns:
            The loaded model object.
        """
        if self.is_loaded(name):
            logger.debug(f"Model {name} already loaded, reusing")
            return self._loaded[name]

        spec = self._specs.get(name)
        if spec is None:
            raise ValueError(f"Unknown model: {name}. Register it first.")

        if not self.can_load(name):
            # Try to free memory by unloading least recently used
            logger.warning(
                f"Not enough RAM for {name} "
                f"({spec.ram_required_mb}MB needed, "
                f"{self._ram_used_mb}MB used)"
            )
            self._evict_oldest()

        logger.info(f"Loading model: {name}...")
        model = loader_fn()
        self._loaded[name] = model
        self._ram_used_mb += spec.ram_required_mb
        logger.info(f"Loaded {name} (RAM: {self._ram_used_mb:.0f}MB used)")
        return model

    def unload(self, name: str) -> None:
        """Unload a model from memory."""
        if name in self._loaded:
            spec = self._specs.get(name)
            del self._loaded[name]
            gc.collect()
            if spec:
                self._ram_used_mb = max(0, self._ram_used_mb - spec.ram_required_mb)
            logger.info(f"Unloaded model: {name}")

    def unload_all(self) -> None:
        """Unload all models from memory."""
        for name in list(self._loaded.keys()):
            self.unload(name)
        gc.collect()
        self._ram_used_mb = 0.0
        logger.info("All models unloaded")

    def _evict_oldest(self) -> None:
        """Evict the first loaded model to free RAM."""
        if self._loaded:
            oldest = next(iter(self._loaded))
            logger.info(f"Evicting model {oldest} to free RAM")
            self.unload(oldest)

    def list_models(self) -> list[dict[str, Any]]:
        """List all registered models and their status."""
        return [
            {
                "name": name,
                "size_mb": spec.size_mb,
                "downloaded": self.is_downloaded(name),
                "loaded": self.is_loaded(name),
                "gpu_required": spec.gpu_required,
            }
            for name, spec in self._specs.items()
        ]


# Singleton
_registry: ModelRegistry | None = None


def get_model_registry() -> ModelRegistry:
    """Get or create the global model registry."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
