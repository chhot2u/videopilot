"""VideoPilot — Module Auto-Discovery Registry.

Automatically scans all subpackages for classes that inherit from BaseModule
and registers them. Just drop a new module file in the right folder and it works.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from loguru import logger

from core.base_module import BaseModule


def discover_modules() -> dict[str, BaseModule]:
    """Scan all module subpackages and instantiate BaseModule subclasses.

    Returns:
        Dictionary mapping module names to their instances.
    """
    modules: dict[str, BaseModule] = {}
    package_dir = Path(__file__).parent

    for _finder, module_name, _is_pkg in pkgutil.walk_packages(
        [str(package_dir)], prefix="modules."
    ):
        try:
            mod = importlib.import_module(module_name)
        except ImportError as e:
            logger.warning(f"Could not import {module_name}: {e}")
            continue

        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseModule)
                and attr is not BaseModule
            ):
                try:
                    instance = attr()
                    info = instance.get_info()
                    modules[info.name] = instance
                    logger.debug(f"Discovered module: {info.name} ({info.category.value})")
                except Exception as e:
                    logger.warning(f"Could not instantiate {attr_name}: {e}")

    logger.info(f"Auto-discovered {len(modules)} modules")
    return modules
