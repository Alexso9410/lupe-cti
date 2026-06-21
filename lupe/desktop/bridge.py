"""PyWebView bridge — the only Python surface exposed to JavaScript.

Every public method here is callable from JS as:
    window.pywebview.api.method_name(args)

All methods are synchronous (PyWebView manages threading internally).
Async Centinela functions are wrapped with asyncio.run().

Contract: every method returns a plain dict with at minimum:
    {"success": bool, "error": str | null}
No exceptions are ever raised from bridge methods.
"""

from __future__ import annotations

import asyncio
import traceback
from pathlib import Path
from typing import Any

import webview

try:
    _OPEN = webview.FileDialog.OPEN_DIALOG
    _FOLDER = webview.FileDialog.FOLDER_DIALOG
except AttributeError:
    _OPEN = webview.OPEN_DIALOG
    _FOLDER = webview.FOLDER_DIALOG

from lupe.analysis import analyze_ioc
from lupe.config import get_settings
from lupe.db import Database
from lupe.enrichment import run_enrichment
from lupe.export.obsidian import export_ioc_to_obsidian, save_obsidian_note
from lupe.ioc_detect import detect_ioc
from lupe.models import IOC, EnrichmentResult


def _enrichment_to_dict(result: EnrichmentResult) -> dict[str, Any]:
    """Serialize an EnrichmentResult to a JSON-safe dict."""
    return {
        "source": result.source,
        "ioc_value": result.ioc_value,
        "severity": result.severity.value,
        "summary": result.summary,
        "raw_data": result.raw_data,
        "enriched_at": result.enriched_at.isoformat(),
    }


def _ioc_to_dict(ioc: IOC) -> dict[str, Any]:
    """Serialize an IOC to a JSON-safe dict."""
    return {"type": ioc.type.value, "value": ioc.value}


def _mask_key(key: str | None) -> str | None:
    """Return a masked version of an API key, showing only the last 4 chars."""
    if not key:
        return None
    if len(key) <= 4:
        return "****"
    return "****" + key[-4:]


class CentinelaAPI:
    """All methods here are callable from JavaScript as window.pywebview.api.methodName().

    One instance lives for the lifetime of the desktop window. The Database
    connection is opened once in __init__ and reused across all calls.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._db = Database(settings.db_path)

    # ------------------------------------------------------------------
    # IOC Enrichment
    # ------------------------------------------------------------------

    def enrich_ioc(self, ioc_value: str, no_ai: bool = False) -> dict[str, Any]:
        """Enrich a single IOC and return results as a JSON-serializable dict.

        Args:
            ioc_value: Raw IOC string (IP, domain, hash, URL, etc.).
            no_ai: If True, skip the Ollama AI analysis step.

        Returns:
            {
                "success": true,
                "ioc": {"type": "ipv4", "value": "..."},
                "enrichments": [...],
                "analysis": "AI text or null",
                "error": null
            }
        """
        try:
            ioc_value = ioc_value.strip()
            ioc = detect_ioc(ioc_value)
            if ioc is None:
                return {
                    "success": False,
                    "ioc": None,
                    "enrichments": [],
                    "analysis": None,
                    "error": f"No se pudo detectar el tipo de IOC para: {ioc_value!r}",
                }

            settings = get_settings()
            enrichments: list[EnrichmentResult] = asyncio.run(run_enrichment(ioc, settings))

            analysis: str | None = None
            if not no_ai:
                analysis = asyncio.run(analyze_ioc(ioc, enrichments, settings))

            return {
                "success": True,
                "ioc": _ioc_to_dict(ioc),
                "enrichments": [_enrichment_to_dict(e) for e in enrichments],
                "analysis": analysis,
                "error": None,
            }
        except Exception:
            return {
                "success": False,
                "ioc": None,
                "enrichments": [],
                "analysis": None,
                "error": traceback.format_exc(limit=3),
            }

    def enrich_person(
        self,
        phone: str = "",
        username: str = "",
        email: str = "",
        name: str = "",
        no_ai: bool = False,
        case_id: int | None = None,
    ) -> dict[str, Any]:
        """Enrich a person by phone, username and/or email."""
        try:
            if not phone.strip() and not username.strip() and not email.strip():
                return {
                    "success": False,
                    "phone_results": [],
                    "username_results": [],
                    "email_results": [],
                    "analysis": None,
                    "error": "Debés proveer al menos un teléfono, username o email.",
                }

            settings = get_settings()
            phone_results: list[dict] = []
            username_results: list[dict] = []
            email_results: list[dict] = []
            all_enrichments: list = []

            # --- Phone enrichment ---
            if phone.strip():
                phone_ioc = detect_ioc(phone.strip())
                if phone_ioc is None or phone_ioc.type.value != "phone":
                    return {
                        "success": False,
                        "phone_results": [],
                        "username_results": [],
                        "email_results": [],
                        "analysis": None,
                        "error": f"'{phone}' no es un número válido. Usá formato +XX...",
                    }
                enrichments = asyncio.run(run_enrichment(phone_ioc, settings))
                phone_results = [_enrichment_to_dict(e) for e in enrichments]
                all_enrichments.extend(enrichments)

                if case_id:
                    ioc_id = self._db.upsert_ioc(phone_ioc)
                    for e in enrichments:
                        self._db.save_enrichment(ioc_id, e)
                    self._db.link_ioc_to_case(ioc_id, case_id)

            # --- Username enrichment ---
            if username.strip():
                from lupe.models import IOC, IOCType

                user_ioc = IOC(type=IOCType.username, value=username.strip())
                enrichments = asyncio.run(run_enrichment(user_ioc, settings))
                username_results = [_enrichment_to_dict(e) for e in enrichments]
                all_enrichments.extend(enrichments)

                if case_id:
                    ioc_id = self._db.upsert_ioc(user_ioc)
                    for e in enrichments:
                        self._db.save_enrichment(ioc_id, e)
                    self._db.link_ioc_to_case(ioc_id, case_id)

            # --- Email enrichment ---
            if email.strip():
                from lupe.models import IOC, IOCType

                email_ioc = IOC(type=IOCType.email, value=email.strip())
                enrichments = asyncio.run(run_enrichment(email_ioc, settings))
                email_results = [_enrichment_to_dict(e) for e in enrichments]
                all_enrichments.extend(enrichments)

                if case_id:
                    ioc_id = self._db.upsert_ioc(email_ioc)
                    for e in enrichments:
                        self._db.save_enrichment(ioc_id, e)
                    self._db.link_ioc_to_case(ioc_id, case_id)

            # --- AI analysis ---
            analysis: str | None = None
            if not no_ai and all_enrichments:
                if phone.strip():
                    ref_ioc = detect_ioc(phone.strip())
                elif email.strip():
                    from lupe.models import IOC, IOCType

                    ref_ioc = IOC(type=IOCType.email, value=email.strip())
                else:
                    from lupe.models import IOC, IOCType

                    ref_ioc = IOC(type=IOCType.username, value=username.strip())
                analysis = asyncio.run(analyze_ioc(ref_ioc, all_enrichments, settings))

            return {
                "success": True,
                "phone_results": phone_results,
                "username_results": username_results,
                "email_results": email_results,
                "analysis": analysis,
                "error": None,
            }
        except Exception:
            return {
                "success": False,
                "phone_results": [],
                "username_results": [],
                "email_results": [],
                "analysis": None,
                "error": traceback.format_exc(limit=3),
            }

    # ------------------------------------------------------------------
    # Cases
    # ------------------------------------------------------------------

    def get_cases(self) -> dict[str, Any]:
        """List all investigation cases.

        Returns:
            {"success": true, "cases": [...]}
        """
        try:
            cases = self._db.list_cases()
            return {"success": True, "cases": cases, "error": None}
        except Exception as exc:
            return {"success": False, "cases": [], "error": str(exc)}

    def create_case(self, name: str, description: str = "") -> dict[str, Any]:
        """Create a new investigation case.

        Args:
            name: Short display name for the case.
            description: Optional longer description.

        Returns:
            {"success": true, "case_id": 1, "name": "..."}
        """
        try:
            case_id = self._db.create_case(name.strip(), description.strip())
            return {
                "success": True,
                "case_id": case_id,
                "name": name.strip(),
                "error": None,
            }
        except Exception as exc:
            return {"success": False, "case_id": None, "name": None, "error": str(exc)}

    def get_case(self, case_id: int) -> dict[str, Any]:
        """Get a case with its IOCs and timeline.

        Args:
            case_id: Primary key of the case.

        Returns:
            Full case dict including iocs and timeline lists.
        """
        try:
            case = self._db.get_case(case_id)
            if case is None:
                return {
                    "success": False,
                    "case": None,
                    "error": f"Caso {case_id} no encontrado",
                }
            case["iocs"] = self._db.get_case_iocs(case_id)
            case["timeline"] = self._db.get_case_timeline(case_id)
            case["notes"] = self._db.get_case_notes(case_id)
            return {"success": True, "case": case, "error": None}
        except Exception as exc:
            return {"success": False, "case": None, "error": str(exc)}

    def close_case(self, case_id: int) -> dict[str, Any]:
        """Close a case.

        Args:
            case_id: Primary key of the case to close.

        Returns:
            {"success": true}
        """
        try:
            self._db.close_case(case_id)
            return {"success": True, "error": None}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def add_case_note(self, case_id: int, content: str) -> dict[str, Any]:
        """Add a free-text note to a case.

        Args:
            case_id: Primary key of the case.
            content: Note text.

        Returns:
            {"success": true, "note_id": 1}
        """
        try:
            note_id = self._db.add_case_note(case_id, content.strip())
            return {"success": True, "note_id": note_id, "error": None}
        except Exception as exc:
            return {"success": False, "note_id": None, "error": str(exc)}

    # ------------------------------------------------------------------
    # Enrich + Save (combined flow)
    # ------------------------------------------------------------------

    def enrich_and_save(self, ioc_value: str, case_id: int, no_ai: bool = False) -> dict[str, Any]:
        """Enrich an IOC and persist all results linked to a case.

        Args:
            ioc_value: Raw IOC string.
            case_id: Case the IOC will be linked to.
            no_ai: If True, skip Ollama analysis.

        Returns:
            Same structure as enrich_ioc() plus:
                "saved": true,
                "ioc_id": <int>,
                "enrichment_ids": [<int>, ...],
                "analysis_id": <int | null>
        """
        try:
            ioc_value = ioc_value.strip()
            ioc = detect_ioc(ioc_value)
            if ioc is None:
                return {
                    "success": False,
                    "ioc": None,
                    "enrichments": [],
                    "analysis": None,
                    "saved": False,
                    "ioc_id": None,
                    "enrichment_ids": [],
                    "analysis_id": None,
                    "error": f"No se pudo detectar el tipo de IOC para: {ioc_value!r}",
                }

            settings = get_settings()
            enrichments: list[EnrichmentResult] = asyncio.run(run_enrichment(ioc, settings))

            analysis: str | None = None
            if not no_ai:
                analysis = asyncio.run(analyze_ioc(ioc, enrichments, settings))

            # Persist
            ioc_id = self._db.upsert_ioc(ioc.type.value, ioc.value)
            enrichment_ids: list[int] = []
            for result in enrichments:
                eid = self._db.save_enrichment(
                    ioc_id=ioc_id,
                    source=result.source,
                    severity=result.severity.value,
                    summary=result.summary,
                    raw_data=result.raw_data,
                )
                enrichment_ids.append(eid)

            self._db.link_ioc_to_case(case_id, ioc_id)

            analysis_id: int | None = None
            if analysis:
                analysis_id = self._db.save_analysis(
                    ioc_id=ioc_id,
                    model=settings.ollama_model,
                    summary=analysis,
                )

            return {
                "success": True,
                "ioc": _ioc_to_dict(ioc),
                "enrichments": [_enrichment_to_dict(e) for e in enrichments],
                "analysis": analysis,
                "saved": True,
                "ioc_id": ioc_id,
                "enrichment_ids": enrichment_ids,
                "analysis_id": analysis_id,
                "error": None,
            }
        except Exception:
            return {
                "success": False,
                "ioc": None,
                "enrichments": [],
                "analysis": None,
                "saved": False,
                "ioc_id": None,
                "enrichment_ids": [],
                "analysis_id": None,
                "error": traceback.format_exc(limit=3),
            }

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def get_config(self) -> dict[str, Any]:
        """Return the current configuration with API keys masked.

        Returns:
            Dict of config values; keys show only last 4 chars (e.g. "****abcd").
        """
        try:
            settings = get_settings()
            return {
                "success": True,
                "config": {
                    "ollama_base_url": settings.ollama_base_url,
                    "ollama_model": settings.ollama_model,
                    "db_path": settings.db_path,
                    "abuseipdb_key": _mask_key(settings.abuseipdb_key),
                    "virustotal_key": _mask_key(settings.virustotal_key),
                    "shodan_key": _mask_key(settings.shodan_key),
                    "otx_key": _mask_key(settings.otx_key),
                    "urlscan_key": _mask_key(settings.urlscan_key),
                    "hibp_key": _mask_key(settings.hibp_key),
                    "greynoise_key": _mask_key(settings.greynoise_key),
                    "ipqs_key": _mask_key(settings.ipqs_key),
                    "numverify_key": _mask_key(settings.numverify_key),
                    "emailrep_key": _mask_key(settings.emailrep_key),
                    "googlesb_key": _mask_key(settings.googlesb_key),
                    "phishtank_key": _mask_key(settings.phishtank_key),
                    "pulsedive_key": _mask_key(settings.pulsedive_key),
                },
                "error": None,
            }
        except Exception as exc:
            return {"success": False, "config": {}, "error": str(exc)}

    def save_config(self, updates: dict[str, str]) -> dict[str, Any]:
        """Persist configuration values to the .env file.

        Reads the existing .env (if any), updates or adds the provided keys,
        and writes the file back. Uses CENTINELA_ prefixed env var names.

        Args:
            updates: Mapping of env var name -> new value.
                     E.g. {"CENTINELA_VIRUSTOTAL_KEY": "abc123"}

        Returns:
            {"success": true}
        """
        try:
            env_path = Path(".env")

            # Read existing lines
            existing_lines: list[str] = []
            if env_path.exists():
                existing_lines = env_path.read_text(encoding="utf-8").splitlines()

            # Build a dict of current key -> line-index for fast replacement
            key_to_idx: dict[str, int] = {}
            for idx, line in enumerate(existing_lines):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" in stripped:
                    k = stripped.split("=", 1)[0].strip()
                    key_to_idx[k] = idx

            # Apply updates
            for env_key, value in updates.items():
                env_key = env_key.upper()
                # Skip placeholder masked values (unchanged)
                if value.startswith("****") and len(value) <= 8:
                    continue
                if env_key in key_to_idx:
                    existing_lines[key_to_idx[env_key]] = f"{env_key}={value}"
                else:
                    existing_lines.append(f"{env_key}={value}")

            env_path.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")

            # Invalidate settings cache so next call picks up new values
            get_settings.cache_clear()

            return {"success": True, "error": None}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Obsidian Export
    # ------------------------------------------------------------------

    def export_case_obsidian(self, case_id: int, output_dir: str) -> dict[str, Any]:
        """Export all IOCs linked to a case as Obsidian markdown notes.

        Args:
            case_id: Primary key of the case to export.
            output_dir: Directory where .md files will be written.

        Returns:
            {"success": true, "files": ["/path/to/note.md", ...]}
        """
        try:
            case = self._db.get_case(case_id)
            if case is None:
                return {
                    "success": False,
                    "files": [],
                    "error": f"Caso {case_id} no encontrado",
                }

            case_name = case["name"]
            iocs = self._db.get_case_iocs(case_id)
            saved_paths: list[str] = []

            for ioc_row in iocs:
                from lupe.models import IOCType, Severity

                ioc = IOC(
                    type=IOCType(ioc_row["type"]),
                    value=ioc_row["value"],
                )
                # Reconstruct EnrichmentResult objects from stored dicts
                enrichments: list[EnrichmentResult] = []
                from datetime import datetime

                for e in ioc_row.get("enrichments", []):
                    enrichments.append(
                        EnrichmentResult(
                            source=e["source"],
                            ioc_value=ioc_row["value"],
                            severity=Severity(e["severity"]),
                            summary=e["summary"],
                            raw_data=e["raw_data"],
                            enriched_at=datetime.fromisoformat(e["enriched_at"]),
                        )
                    )

                # Best available analysis: look for a saved one in DB
                analysis: str | None = None
                analyses_cur = self._db._conn.execute(
                    "SELECT summary FROM analyses "
                    "WHERE ioc_id = ? "
                    "ORDER BY analyzed_at DESC LIMIT 1",
                    (ioc_row["id"],),
                )
                row = analyses_cur.fetchone()
                if row:
                    analysis = row["summary"]

                content = export_ioc_to_obsidian(
                    ioc=ioc,
                    enrichments=enrichments,
                    analysis=analysis,
                    case_name=case_name,
                )
                path = save_obsidian_note(content, output_dir, ioc.value)
                saved_paths.append(path)

            return {"success": True, "files": saved_paths, "error": None}
        except Exception:
            return {
                "success": False,
                "files": [],
                "error": traceback.format_exc(limit=3),
            }

    # ------------------------------------------------------------------
    # Dashboard Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return dashboard statistics.

        Returns:
            {
                "success": true,
                "total_iocs": int,
                "total_cases": int,
                "open_cases": int,
                "total_enrichments": int
            }
        """
        try:
            conn = self._db._conn

            total_iocs: int = conn.execute("SELECT COUNT(*) FROM iocs").fetchone()[0]
            total_cases: int = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
            open_cases: int = conn.execute(
                "SELECT COUNT(*) FROM cases WHERE status != 'closed'"
            ).fetchone()[0]
            total_enrichments: int = conn.execute("SELECT COUNT(*) FROM enrichments").fetchone()[0]

            return {
                "success": True,
                "total_iocs": total_iocs,
                "total_cases": total_cases,
                "open_cases": open_cases,
                "total_enrichments": total_enrichments,
                "error": None,
            }
        except Exception as exc:
            return {
                "success": False,
                "total_iocs": 0,
                "total_cases": 0,
                "open_cases": 0,
                "total_enrichments": 0,
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Email Analysis
    # ------------------------------------------------------------------

    def analyze_email_file(
        self,
        file_path: str,
        case_id: int | None = None,
        no_ai: bool = False,
        export_pdf_dir: str | None = None,
    ) -> dict[str, Any]:
        """Analizar un archivo .eml en busca de indicadores de phishing.

        Args:
            file_path: Ruta absoluta al archivo .eml
            case_id: ID del caso al que vincular el análisis (opcional)
            no_ai: Si True, omite el análisis de IA
            export_pdf_dir: Directorio donde guardar el PDF (opcional)

        Returns:
            {
                "success": bool,
                "analysis": dict | None,
                "pdf_path": str | None,
                "analysis_id": int | None,
                "error": str | None
            }
        """
        try:
            from lupe.email_analyzer import analyze_email
            from lupe.email_parser import parse_eml

            path = Path(file_path)
            if not path.exists() or path.suffix.lower() != ".eml":
                return {
                    "success": False,
                    "analysis": None,
                    "pdf_path": None,
                    "analysis_id": None,
                    "error": f"Archivo no válido: {file_path}",
                }

            settings = get_settings()
            parsed = parse_eml(path)
            result = asyncio.run(analyze_email(parsed, settings, no_ai=no_ai))

            pdf_path: str | None = None
            if export_pdf_dir:
                from lupe.export.pdf_report import generate_email_report

                pdf_path = generate_email_report(result, export_pdf_dir)

            analysis_id: int | None = None
            if case_id is not None:
                analysis_id = self._db.save_email_analysis(
                    result.model_dump(mode="json"), case_id, pdf_path
                )

            return {
                "success": True,
                "analysis": result.model_dump(mode="json"),
                "pdf_path": pdf_path,
                "analysis_id": analysis_id,
                "error": None,
            }
        except Exception:
            return {
                "success": False,
                "analysis": None,
                "pdf_path": None,
                "analysis_id": None,
                "error": traceback.format_exc(limit=3),
            }

    # ------------------------------------------------------------------
    # Native File Dialogs
    # ------------------------------------------------------------------

    def open_url(self, url: str) -> dict:
        """Abrir una URL en el navegador predeterminado del sistema."""
        import webbrowser

        try:
            webbrowser.open(url)
            return {"success": True, "error": None}
        except Exception:
            return {"success": False, "error": traceback.format_exc(limit=3)}

    def open_file_dialog(self) -> dict:
        """Abrir diálogo nativo de selección de archivo .eml"""
        try:
            result = webview.windows[0].create_file_dialog(
                _OPEN,
                file_types=("Email files (*.eml)", "All files (*.*)"),
            )
            if not result:
                return {"success": True, "file_path": None, "error": None}
            return {"success": True, "file_path": result[0], "error": None}
        except Exception:
            return {
                "success": False,
                "file_path": None,
                "error": traceback.format_exc(limit=3),
            }

    def open_directory_dialog(self) -> dict:
        """Abrir diálogo nativo de selección de directorio (para exportar PDF)"""
        try:
            result = webview.windows[0].create_file_dialog(_FOLDER)
            if not result:
                return {"success": True, "dir_path": None, "error": None}
            return {"success": True, "dir_path": result[0], "error": None}
        except Exception:
            return {
                "success": False,
                "dir_path": None,
                "error": traceback.format_exc(limit=3),
            }
