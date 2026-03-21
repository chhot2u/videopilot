"""VideoPilot — Task Router.

Auto-detects the best module(s) for given inputs.
Maps input combinations to available modules.
"""

from __future__ import annotations

from loguru import logger

from core.base_module import BaseModule, InputType, ModuleInputs
from core.input_handler import InputAnalysis


class TaskRouter:
    """Routes user inputs to the appropriate module(s)."""

    def __init__(self) -> None:
        self._modules: dict[str, BaseModule] = {}

    def register_module(self, module: BaseModule) -> None:
        """Register a module for routing."""
        info = module.get_info()
        self._modules[info.name] = module
        logger.debug(f"Router: registered {info.name}")

    def register_modules(self, modules: dict[str, BaseModule]) -> None:
        """Register multiple modules at once."""
        for name, module in modules.items():
            self._modules[name] = module

    def get_module(self, name: str) -> BaseModule | None:
        """Get a specific module by name."""
        return self._modules.get(name)

    def find_compatible_modules(
        self,
        input_types: list[InputType],
        category: str | None = None,
    ) -> list[BaseModule]:
        """Find all modules compatible with the given input types.

        Args:
            input_types: The types of inputs the user has provided.
            category: Optional category filter.

        Returns:
            List of compatible modules sorted by relevance.
        """
        compatible = []
        input_set = set(input_types)

        for _name, module in self._modules.items():
            info = module.get_info()

            # Filter by category if specified
            if category and info.category.value != category:
                continue

            # Check if module's required inputs are satisfied
            required = set(info.supported_inputs)
            if required.issubset(input_set):
                compatible.append(module)

        # Sort: CPU-friendly first, then by name
        return sorted(
            compatible,
            key=lambda m: (not m.get_info().cpu_friendly, m.get_info().name),
        )

    def suggest_modules(self, analysis: InputAnalysis) -> list[BaseModule]:
        """Suggest modules based on input analysis."""
        return self.find_compatible_modules(analysis.detected_input_types)

    def route(self, task_name: str, inputs: ModuleInputs) -> BaseModule:
        """Route a specific task to its module.

        Args:
            task_name: The module name to route to.
            inputs: The validated inputs.

        Returns:
            The matched module.

        Raises:
            ValueError: If module not found or inputs invalid.
        """
        module = self._modules.get(task_name)
        if module is None:
            available = ", ".join(sorted(self._modules.keys()))
            raise ValueError(
                f"Unknown task: '{task_name}'. Available: {available}"
            )

        is_valid, error = module.validate_inputs(inputs)
        if not is_valid:
            raise ValueError(f"Invalid inputs for {task_name}: {error}")

        return module

    def list_modules(self, category: str | None = None) -> list[dict[str, str | list[str] | bool]]:
        """List all registered modules with their info."""
        modules = []
        for _name, module in sorted(self._modules.items()):
            info = module.get_info()
            if category and info.category.value != category:
                continue
            modules.append({
                "name": info.name,
                "display_name": info.display_name,
                "category": info.category.value,
                "description": info.description,
                "inputs": [t.value for t in info.supported_inputs],
                "cpu_friendly": info.cpu_friendly,
            })
        return modules
