from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only used for type checking — not imported at runtime unless bridge is active.
    pass

_HEIMDALL_TOOLS_PATH = Path(r"C:\Users\usuario\Documents\heimdall\tools")
_AGENT_WRITER_MODULE = _HEIMDALL_TOOLS_PATH / "agent_writer.py"

_DASHBOARD_ENABLED = os.getenv("LUPE_DASHBOARD_ENABLED", "").lower() in (
    "1",
    "true",
    "yes",
)


def _try_import_agent_writer():
    """Attempt to import AgentWriter from the Heimdall tools path.

    Returns the AgentWriter class on success, or None if the module is not
    found or cannot be imported.
    """
    if not _AGENT_WRITER_MODULE.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        "heimdall_agent_writer", str(_AGENT_WRITER_MODULE)
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except Exception:
        return None

    return getattr(module, "AgentWriter", None)


class CentinelaAgentBridge:
    """Reports Lupe CTI enrichment progress to the Heimdall agent-dashboard.

    This bridge is a noop when:
    - The environment variable ``LUPE_DASHBOARD_ENABLED`` is not set to a
      truthy value (``1``, ``true``, ``yes``).
    - ``agent_writer.py`` is not found at the expected Heimdall tools path.

    Usage::

        bridge = CentinelaAgentBridge()
        bridge.start_enrichment("185.220.101.34", plugin_count=4)
        bridge.plugin_complete("ipinfo", current=1, total=4)
        bridge.enrichment_done("185.220.101.34", result_count=4)
    """

    def __init__(self, agent_name: str = "lupe-cti") -> None:
        self._agent_name = agent_name
        self._writer = None
        self._active_ioc: str | None = None

        if not _DASHBOARD_ENABLED:
            return

        agent_writer_cls = _try_import_agent_writer()
        if agent_writer_cls is None:
            return

        try:
            # agent_id is kept simple and stable so the dashboard can track
            # this agent across enrichment calls in the same session.
            self._writer = agent_writer_cls(
                agent_name,
                agent_name,
                "Initializing",
            )
        except Exception:
            self._writer = None

    @property
    def is_active(self) -> bool:
        """True when the bridge is connected to a live AgentWriter instance."""
        return self._writer is not None

    def start_enrichment(self, ioc_value: str, plugin_count: int) -> None:
        """Signal that enrichment has started for an IOC.

        Args:
            ioc_value: The IOC being enriched (e.g. "185.220.101.34").
            plugin_count: Number of plugins that will run.
        """
        if self._writer is None:
            return

        self._active_ioc = ioc_value
        command_name = f"enrich-{ioc_value}"

        try:
            self._writer.update(
                progress=0,
                task=f"Enriching {ioc_value}",
            )
            self._writer.start_command(command_name)
            self._writer.log_command(
                command_name,
                f"Starting enrichment with {plugin_count} plugin(s)",
            )
        except Exception:
            pass

    def plugin_complete(self, plugin_name: str, current: int, total: int) -> None:
        """Signal that a single plugin has completed.

        Args:
            plugin_name: Name of the plugin that just finished.
            current: Number of plugins completed so far (1-based).
            total: Total number of plugins to run.
        """
        if self._writer is None or self._active_ioc is None:
            return

        progress = int(current / total * 100) if total > 0 else 0
        command_name = f"enrich-{self._active_ioc}"

        try:
            self._writer.update(progress=progress)
            self._writer.log_command(command_name, f"{plugin_name} completed")
        except Exception:
            pass

    def enrichment_done(self, ioc_value: str, result_count: int) -> None:
        """Signal that enrichment completed successfully.

        Args:
            ioc_value: The IOC that was enriched.
            result_count: Number of enrichment results collected.
        """
        if self._writer is None:
            return

        command_name = f"enrich-{ioc_value}"

        try:
            self._writer.complete_command(
                command_name,
                output=f"{result_count} result(s) collected",
            )
            self._writer.done(result=f"Enriched {ioc_value}: {result_count} findings")
        except Exception:
            pass
        finally:
            self._active_ioc = None

    def enrichment_failed(self, ioc_value: str, error: str) -> None:
        """Signal that enrichment failed.

        Args:
            ioc_value: The IOC that was being enriched.
            error: Human-readable error description.
        """
        if self._writer is None:
            return

        command_name = f"enrich-{ioc_value}"

        try:
            self._writer.fail_command(command_name, error=error)
            self._writer.error(f"Enrichment failed for {ioc_value}: {error}")
        except Exception:
            pass
        finally:
            self._active_ioc = None
