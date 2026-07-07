from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lupe.analysis import analyze_ioc
from lupe.config import get_config_dir, get_settings
from lupe.db import Database
from lupe.email_analyzer import analyze_email
from lupe.email_parser import parse_eml
from lupe.enrichment import run_enrichment
from lupe.ioc_detect import detect_ioc
from lupe.logging_config import setup_logging
from lupe.models import IOC, EnrichmentResult, IOCType, Severity
from lupe.security.validation import validate_ioc_value

if TYPE_CHECKING:
    from lupe.integrations.misp import MISPClient

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="lupe",
    help="Lupe CTI — Cyber Threat Intelligence for OSINT & Forensics",
    add_completion=False,
)


@app.callback()
def _main_callback(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed error information for debugging."),
    ] = False,
) -> None:
    """Set up logging level based on verbose flag."""
    setup_logging("DEBUG" if verbose else "INFO")
    if verbose:
        logger.debug("Verbose mode enabled")

config_app = typer.Typer(help="Manage API keys and configuration.")
app.add_typer(config_app, name="config")

case_app = typer.Typer(help="Manage investigation cases.")
app.add_typer(case_app, name="case")

person_app = typer.Typer(help="OSINT de personas — teléfono y username.")
app.add_typer(person_app, name="person")

misp_app = typer.Typer(help="MISP integration — pull and push indicators.")
app.add_typer(misp_app, name="misp")

console = Console()
err_console = Console(stderr=True)

_SEVERITY_STYLE: dict[Severity, str] = {
    Severity.critical: "bold red",
    Severity.high: "yellow",
    Severity.medium: "blue",
    Severity.low: "green",
    Severity.info: "dim",
}

# Fields that hold API keys in Settings — used by config show/test
_KEY_FIELDS: list[tuple[str, str]] = [
    ("abuseipdb_key", "LUPE_ABUSEIPDB_KEY"),
    ("virustotal_key", "LUPE_VIRUSTOTAL_KEY"),
    ("shodan_key", "LUPE_SHODAN_KEY"),
    ("otx_key", "LUPE_OTX_KEY"),
    ("urlscan_key", "LUPE_URLSCAN_KEY"),
    ("hibp_key", "LUPE_HIBP_KEY"),
    ("greynoise_key", "LUPE_GREYNOISE_KEY"),
    ("ipqs_key", "LUPE_IPQS_KEY"),
    ("numverify_key", "LUPE_NUMVERIFY_KEY"),
    ("emailrep_key", "LUPE_EMAILREP_KEY"),
    ("googlesb_key", "LUPE_GOOGLESB_KEY"),
    ("phishtank_key", "LUPE_PHISHTANK_KEY"),
    ("pulsedive_key", "LUPE_PULSEDIVE_KEY"),
    # LLM providers (highest blast radius if leaked)
    ("openai_api_key", "LUPE_OPENAI_API_KEY"),
    ("anthropic_api_key", "LUPE_ANTHROPIC_API_KEY"),
    ("openrouter_api_key", "LUPE_OPENROUTER_API_KEY"),
    ("ollama_api_key", "LUPE_OLLAMA_API_KEY"),
    ("gemini_api_key", "LUPE_GEMINI_API_KEY"),
    # MISP integration
    ("misp_key", "LUPE_MISP_KEY"),
    # Censys
    ("censys_id", "LUPE_CENSYS_ID"),
    ("censys_secret", "LUPE_CENSYS_SECRET"),
    # Additional threat intel
    ("hybrid_analysis_key", "LUPE_HYBRID_ANALYSIS_KEY"),
    ("spamhaus_key", "LUPE_SPAMHAUS_KEY"),
]

_PLAIN_FIELDS: list[tuple[str, str]] = [
    ("ollama_base_url", "LUPE_OLLAMA_BASE_URL"),
    ("ollama_model", "LUPE_OLLAMA_MODEL"),
    ("db_path", "LUPE_DB_PATH"),
]


def _get_db() -> Database:
    """Return a Database instance using the configured db_path."""
    settings = get_settings()
    return Database(settings.db_path)


def _mask_key(value: str | None) -> str:
    """Return a masked representation of an API key."""
    if not value:
        return "[dim]not set[/dim]"
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


def _build_table(results: list[EnrichmentResult]) -> Table:
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="bright_black",
        expand=False,
    )
    table.add_column("Source", style="bold white", min_width=12)
    table.add_column("Finding", min_width=40)
    table.add_column("Severity", min_width=10, justify="center")

    for result in results:
        style = _SEVERITY_STYLE.get(result.severity, "")
        table.add_row(
            result.source,
            result.summary,
            f"[{style}]{result.severity.value}[/{style}]",
        )

    return table


# ---------------------------------------------------------------------------
# enrich subcommand
# ---------------------------------------------------------------------------


@app.command()
def enrich(
    ioc_value: Annotated[str, typer.Argument(help="IOC value to enrich")],
    output_json: Annotated[
        bool, typer.Option("--json", help="Output raw JSON instead of a table")
    ] = False,
    no_ai: Annotated[bool, typer.Option("--no-ai", help="Skip Ollama AI analysis")] = False,
    model: Annotated[
        str | None,
        typer.Option("--model", help="Override the Ollama model for this run"),
    ] = None,
    case_id: Annotated[
        int | None,
        typer.Option("--case", help="Save results to DB and link IOC to this case ID"),
    ] = None,
) -> None:
    """Enrich an IOC (IP, domain, hash, URL, or email) using multiple sources."""
    # Reject overlong / empty inputs before doing any work
    try:
        validate_ioc_value(ioc_value, ioc_type="url")  # most permissive max (2048)
    except ValueError as exc:
        err_console.print(f"[bold red]Error:[/bold red] Invalid IOC: {exc}")
        raise typer.Exit(code=1)

    ioc = detect_ioc(ioc_value)
    if ioc is None:
        err_console.print(
            f"[bold red]Error:[/bold red] IOC type not recognized for: [yellow]{ioc_value}[/yellow]"
        )
        raise typer.Exit(code=1)

    if not output_json:
        console.print(
            f"\n[bold]Lupe CTI[/bold] — Enriching [cyan]{ioc.type.value}[/cyan]: "
            f"[bold white]{ioc.value}[/bold white]\n"
        )

    settings = get_settings()

    # Allow per-run model override without mutating the cached settings object
    effective_settings = settings
    if model is not None:
        effective_settings = settings.model_copy(update={"ollama_model": model})

    try:
        results = asyncio.run(run_enrichment(ioc, effective_settings))
    except KeyboardInterrupt:
        err_console.print("\n[yellow]Interrupted.[/yellow]")
        raise typer.Exit(code=130)

    if output_json:
        output = [r.model_dump(mode="json") for r in results]
        console.print_json(json.dumps(output))
        return

    if not results:
        console.print("[dim]No enrichment data found for this IOC.[/dim]\n")
        return

    table = _build_table(results)
    console.print(table)
    console.print()

    analysis_text: str | None = None

    if not no_ai:
        # AI analysis via Ollama
        try:
            analysis_text = asyncio.run(analyze_ioc(ioc, results, effective_settings))
        except KeyboardInterrupt:
            err_console.print("\n[yellow]AI analysis interrupted.[/yellow]")

        if analysis_text:
            panel = Panel(
                analysis_text,
                title="[bold cyan]Analisis IA[/bold cyan]",
                border_style="cyan",
                expand=False,
            )
            console.print(panel)
            console.print()

    if case_id is not None:
        _save_to_db(
            ioc_type=ioc.type.value,
            ioc_value=ioc.value,
            results=results,
            analysis_text=analysis_text,
            model=effective_settings.ollama_model,
            case_id=case_id,
        )


# ---------------------------------------------------------------------------
# DB persistence helper
# ---------------------------------------------------------------------------


def _save_to_db(
    ioc_type: str,
    ioc_value: str,
    results: list[EnrichmentResult],
    analysis_text: str | None,
    model: str,
    case_id: int | None,
) -> None:
    """Persist an enrichment run to the database and optionally link to a case.

    Args:
        ioc_type: IOC type string.
        ioc_value: Raw IOC value.
        results: List of enrichment results from all plugins.
        analysis_text: AI analysis text, or None if skipped.
        model: Ollama model name used for analysis.
        case_id: If provided, link the IOC to this case after saving.
    """
    try:
        db = _get_db()
        ioc_id = db.upsert_ioc(ioc_type, ioc_value)
        for r in results:
            db.save_enrichment(ioc_id, r.source, r.severity.value, r.summary, r.raw_data)
        if analysis_text:
            db.save_analysis(ioc_id, model, analysis_text)
        if case_id is not None:
            case = db.get_case(case_id)
            if case is None:
                err_console.print(
                    f"[bold red]Error:[/bold red] Case [yellow]{case_id}[/yellow] not found. "
                    "IOC was saved to the database but not linked to a case."
                )
            else:
                db.link_ioc_to_case(case_id, ioc_id)
                console.print(
                    f"[green]Saved[/green] to DB — IOC id=[bold]{ioc_id}[/bold], "
                    f"linked to case [bold]{case_id}[/bold] ({case['name']})"
                )
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[bold red]DB error:[/bold red] {exc}")


# ---------------------------------------------------------------------------
# bulk command
# ---------------------------------------------------------------------------


@app.command()
def bulk(
    file: Annotated[Path, typer.Argument(help="Text file with one IOC per line")],
    case_id: Annotated[
        int | None,
        typer.Option("--case", help="Save all results to DB and link to this case ID"),
    ] = None,
    no_ai: Annotated[
        bool, typer.Option("--no-ai", help="Skip Ollama AI analysis for all IOCs")
    ] = False,
) -> None:
    """Enrich IOCs from a text file (one per line).

    Lines starting with # and blank lines are ignored.
    """
    if not file.exists():
        err_console.print(f"[bold red]Error:[/bold red] File not found: [yellow]{file}[/yellow]")
        raise typer.Exit(code=1)

    raw_lines = file.read_text(encoding="utf-8").splitlines()
    ioc_values = [
        line.strip() for line in raw_lines if line.strip() and not line.strip().startswith("#")
    ]

    if not ioc_values:
        err_console.print("[yellow]No IOC values found in file.[/yellow]")
        raise typer.Exit(code=1)

    settings = get_settings()
    enriched = 0
    failed = 0
    saved = 0

    console.print(
        f"\n[bold]Lupe CTI Bulk[/bold] — {len(ioc_values)} IOC(s) from [cyan]{file.name}[/cyan]\n"
    )

    for raw_value in ioc_values:
        ioc = detect_ioc(raw_value)
        if ioc is None:
            console.print(f"  [dim]SKIP[/dim]  [yellow]{raw_value}[/yellow]  — type not recognized")
            failed += 1
            continue

        console.print(
            f"  [cyan]{ioc.type.value:<10}[/cyan] [white]{ioc.value}[/white]",
            end="",
        )

        try:
            results = asyncio.run(run_enrichment(ioc, settings))
        except KeyboardInterrupt:
            err_console.print("\n[yellow]Interrupted.[/yellow]")
            raise typer.Exit(code=130)

        if not results:
            console.print("  [dim]no data[/dim]")
            failed += 1
            continue

        # Highest severity across all results
        _order = [
            s.value
            for s in [
                Severity.critical,
                Severity.high,
                Severity.medium,
                Severity.low,
                Severity.info,
            ]
        ]
        top = min(results, key=lambda r: _order.index(r.severity.value))
        style = _SEVERITY_STYLE.get(top.severity, "")
        console.print(
            f"  [{style}]{top.severity.value}[/{style}]  [dim]{len(results)} source(s)[/dim]"
        )
        enriched += 1

        analysis_text: str | None = None
        if not no_ai:
            try:
                analysis_text = asyncio.run(analyze_ioc(ioc, results, settings))
            except KeyboardInterrupt:
                err_console.print("\n[yellow]AI analysis interrupted.[/yellow]")
                raise typer.Exit(code=130)

        if case_id is not None:
            try:
                db = _get_db()
                ioc_id = db.upsert_ioc(ioc.type.value, ioc.value)
                for r in results:
                    db.save_enrichment(ioc_id, r.source, r.severity.value, r.summary, r.raw_data)
                if analysis_text:
                    db.save_analysis(ioc_id, settings.ollama_model, analysis_text)
                case = db.get_case(case_id)
                if case is not None:
                    db.link_ioc_to_case(case_id, ioc_id)
                    saved += 1
            except Exception as exc:  # noqa: BLE001
                err_console.print(f"\n  [bold red]DB error:[/bold red] {exc}")

    console.print()
    console.print(
        f"[bold]Summary:[/bold] {enriched} enriched, {failed} failed"
        + (f", {saved} saved to case {case_id}" if case_id is not None else "")
    )
    console.print()


# ---------------------------------------------------------------------------
# email-analyze command
# ---------------------------------------------------------------------------

_AUTH_STYLE: dict[str, str] = {
    "pass": "green",
    "fail": "red",
    "softfail": "yellow",
    "neutral": "yellow",
    "none": "yellow",
    "temperror": "red",
    "permerror": "red",
}


@app.command("email-analyze")
def email_analyze(
    eml_file: Annotated[Path, typer.Argument(help="Archivo .eml a analizar")],
    case_id: Annotated[
        int | None,
        typer.Option("--case", help="Vincular resultados a este caso"),
    ] = None,
    no_ai: Annotated[bool, typer.Option("--no-ai", help="Omitir análisis de IA")] = False,
    export_pdf: Annotated[
        Path | None,
        typer.Option("--export-pdf", help="Directorio donde guardar el PDF"),
    ] = None,
) -> None:
    """Analizar un archivo .eml en busca de indicadores de phishing."""
    # Defense in depth: reject empty / overlong path strings before hitting the FS
    try:
        validate_ioc_value(str(eml_file), ioc_type="url")
    except ValueError as exc:
        err_console.print(f"[bold red]Error:[/bold red] Invalid path: {exc}")
        raise typer.Exit(code=1)

    if not eml_file.exists() or eml_file.suffix.lower() != ".eml":
        err_console.print(
            f"[bold red]Error:[/bold red] Archivo no encontrado o extensión inválida: "
            f"[yellow]{eml_file}[/yellow]"
        )
        raise typer.Exit(code=1)

    console.print(f"\n[bold]Lupe CTI[/bold] — Analizando email: [cyan]{eml_file.name}[/cyan]\n")

    try:
        parsed = parse_eml(eml_file)
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[bold red]Error al parsear .eml:[/bold red] {exc}")
        raise typer.Exit(code=1)

    settings = get_settings()

    try:
        result = asyncio.run(analyze_email(parsed, settings, no_ai=no_ai))
    except KeyboardInterrupt:
        err_console.print("\n[yellow]Interrupted.[/yellow]")
        raise typer.Exit(code=130)
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[bold red]Error en análisis:[/bold red] {exc}")
        raise typer.Exit(code=1)

    # --- Metadata panel ---
    meta_lines = [
        f"[bold]From:[/bold]    {result.headers.from_addr}",
        f"[bold]To:[/bold]      {', '.join(result.headers.to_addr)}",
        f"[bold]Subject:[/bold] {result.headers.subject}",
        f"[bold]Date:[/bold]    {result.headers.date}",
    ]
    console.print(
        Panel(
            "\n".join(meta_lines),
            title="[bold cyan]Metadata[/bold cyan]",
            border_style="cyan",
            expand=False,
        )
    )
    console.print()

    # --- Auth results: SPF / DKIM / DMARC ---
    auth_table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="bright_black",
        expand=False,
    )
    auth_table.add_column("Check", style="bold white", min_width=8)
    auth_table.add_column("Result", min_width=12, justify="center")
    auth_table.add_column("Detail", min_width=40)

    for check_name, check_result, detail in [
        ("SPF", result.auth.spf, result.auth.spf_domain),
        ("DKIM", result.auth.dkim, result.auth.dkim_domain),
        ("DMARC", result.auth.dmarc, None),
    ]:
        st = _AUTH_STYLE.get((check_result or "none").lower(), "yellow")
        auth_table.add_row(
            check_name,
            f"[{st}]{check_result or 'none'}[/{st}]",
            detail or "",
        )

    console.print("[bold]Autenticación de email[/bold]")
    console.print(auth_table)
    console.print()

    # --- Phishing score ---
    score = result.phishing_score.total  # float 0.0–10.0
    bar_filled = int(round(score))
    bar = "[green]" + "█" * bar_filled + "[/green]" + "[dim]" + "░" * (10 - bar_filled) + "[/dim]"
    if score >= 7.0:
        score_color = "red"
    elif score >= 4.0:
        score_color = "yellow"
    else:
        score_color = "green"

    console.print(
        f"[bold]Phishing Score:[/bold]  [{score_color}]{score:.1f}/10[/{score_color}]  {bar}"
    )
    console.print()

    # --- Indicadores que activaron el score ---
    if result.phishing_score.indicators:
        console.print("[bold]Indicadores activos[/bold]")
        for indicator in result.phishing_score.indicators:
            console.print(f"  [yellow]•[/yellow] {indicator}")
        console.print()

    # --- Tabla de IOCs ---
    if result.iocs_found:
        ioc_table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            border_style="bright_black",
            expand=False,
        )
        ioc_table.add_column("Tipo", style="bold white", min_width=10)
        ioc_table.add_column("Valor", min_width=40)

        for ioc_item in result.iocs_found:
            ioc_table.add_row(
                ioc_item.type.value,
                ioc_item.value,
            )

        console.print("[bold]IOCs encontrados[/bold]")
        console.print(ioc_table)
        console.print()

    # --- Análisis IA ---
    if not no_ai and result.ai_classification:
        confidence = result.ai_confidence or 0.0
        conf_color = "green" if confidence >= 0.8 else "yellow" if confidence >= 0.5 else "red"
        ai_lines = [
            f"[bold]Clasificación:[/bold] {result.ai_classification}",
            f"[bold]Confianza:[/bold]     [{conf_color}]{confidence:.0%}[/{conf_color}]",
        ]
        if result.ai_techniques:
            techniques_str = ", ".join(result.ai_techniques)
            ai_lines.append(f"[bold]Técnicas:[/bold]      {techniques_str}")

        console.print(
            Panel(
                "\n".join(ai_lines),
                title="[bold cyan]Analisis IA[/bold cyan]",
                border_style="cyan",
                expand=False,
            )
        )
        console.print()

    # --- Recomendaciones ---
    if result.ai_recommendations:
        console.print("[bold]Recomendaciones[/bold]")
        for rec in result.ai_recommendations:
            console.print(f"  [green]→[/green] {rec}")
        console.print()

    # --- Export PDF ---
    pdf_path: str | None = None
    if export_pdf is not None:
        try:
            from lupe.export.pdf_report import generate_email_report

            pdf_path = generate_email_report(result, str(export_pdf))
            console.print(f"[green]PDF exportado:[/green] {pdf_path}")
        except Exception as exc:  # noqa: BLE001
            err_console.print(f"[bold red]Error al exportar PDF:[/bold red] {exc}")

    # --- Guardar en DB ---
    if case_id is not None:
        try:
            db = _get_db()
            analysis_id = db.save_email_analysis(result.model_dump(), case_id, pdf_path)
            console.print(
                f"[green]Guardado[/green] en caso [bold]#{case_id}[/bold] "
                f"(análisis [bold]#{analysis_id}[/bold])"
            )
        except Exception as exc:  # noqa: BLE001
            err_console.print(f"[bold red]DB error:[/bold red] {exc}")

    console.print()


# ---------------------------------------------------------------------------
# case subcommands
# ---------------------------------------------------------------------------


_STATUS_STYLE: dict[str, str] = {
    "open": "green",
    "closed": "dim",
}

_EVENT_STYLE: dict[str, str] = {
    "ioc_added": "cyan",
    "enrichment": "yellow",
    "analysis": "magenta",
    "note": "magenta",
}


@case_app.command("new")
def case_new(
    name: Annotated[str, typer.Argument(help="Short name for the case")],
    description: Annotated[
        str, typer.Option("--description", "-d", help="Optional case description")
    ] = "",
) -> None:
    """Create a new investigation case."""
    try:
        db = _get_db()
        case_id = db.create_case(name, description)
        console.print(
            f"\n[green]Case created[/green] — id=[bold]{case_id}[/bold]  "
            f"name=[bold white]{name}[/bold white]\n"
        )
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[bold red]DB error:[/bold red] {exc}")
        raise typer.Exit(code=1)


@case_app.command("list")
def case_list(
    status: Annotated[
        str | None,
        typer.Option("--status", "-s", help="Filter by status: open or closed"),
    ] = None,
) -> None:
    """List investigation cases."""
    try:
        db = _get_db()
        cases = db.list_cases(status=status)
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[bold red]DB error:[/bold red] {exc}")
        raise typer.Exit(code=1)

    if not cases:
        console.print("[dim]No cases found.[/dim]\n")
        return

    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="bright_black",
        expand=False,
    )
    table.add_column("ID", style="bold white", min_width=4, justify="right")
    table.add_column("Name", min_width=20)
    table.add_column("Status", min_width=8, justify="center")
    table.add_column("IOCs", min_width=5, justify="right")
    table.add_column("Created", min_width=20)

    for case in cases:
        s = case["status"]
        st = _STATUS_STYLE.get(s, "")
        table.add_row(
            str(case["id"]),
            case["name"],
            f"[{st}]{s}[/{st}]",
            str(case["ioc_count"]),
            case["created_at"],
        )

    console.print()
    console.print(table)
    console.print()


@case_app.command("show")
def case_show(
    case_id: Annotated[int, typer.Argument(help="Case ID to display")],
) -> None:
    """Show case details including linked IOCs and full timeline."""
    try:
        db = _get_db()
        case = db.get_case(case_id)
        if case is None:
            err_console.print(
                f"[bold red]Error:[/bold red] Case [yellow]{case_id}[/yellow] not found."
            )
            raise typer.Exit(code=1)
        iocs = db.get_case_iocs(case_id)
        timeline = db.get_case_timeline(case_id)
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[bold red]DB error:[/bold red] {exc}")
        raise typer.Exit(code=1)

    s = case["status"]
    st = _STATUS_STYLE.get(s, "")
    header = (
        f"[bold white]{case['name']}[/bold white]  [{st}]{s}[/{st}]  [dim]id={case['id']}[/dim]\n"
    )
    if case.get("description"):
        header += f"{case['description']}\n"
    header += f"\n[dim]Created: {case['created_at']}  Updated: {case['updated_at']}[/dim]"

    console.print()
    console.print(
        Panel(header, title="[bold cyan]Case[/bold cyan]", border_style="cyan", expand=False)
    )

    # Linked IOCs
    if iocs:
        ioc_table = Table(
            box=box.SIMPLE,
            show_header=True,
            header_style="bold cyan",
            border_style="bright_black",
            expand=False,
        )
        ioc_table.add_column("Type", min_width=10)
        ioc_table.add_column("Value", min_width=30)
        ioc_table.add_column("Sources", min_width=8, justify="right")
        ioc_table.add_column("Top Severity", min_width=12, justify="center")
        ioc_table.add_column("Added", min_width=20)

        _order = [
            s.value
            for s in [
                Severity.critical,
                Severity.high,
                Severity.medium,
                Severity.low,
                Severity.info,
            ]
        ]

        for ioc in iocs:
            enrichments = ioc.get("enrichments", [])
            if enrichments:
                top_sev = min(enrichments, key=lambda e: _order.index(e["severity"]))["severity"]
            else:
                top_sev = "info"
            sev_obj = Severity(top_sev)
            sev_style = _SEVERITY_STYLE.get(sev_obj, "")
            ioc_table.add_row(
                ioc["type"],
                ioc["value"],
                str(len(enrichments)),
                f"[{sev_style}]{top_sev}[/{sev_style}]",
                ioc["added_at"],
            )

        console.print()
        console.print("[bold]Linked IOCs[/bold]")
        console.print(ioc_table)

    # Timeline
    if timeline:
        tl_table = Table(
            box=box.SIMPLE,
            show_header=True,
            header_style="bold cyan",
            border_style="bright_black",
            expand=False,
        )
        tl_table.add_column("Time", min_width=20)
        tl_table.add_column("Type", min_width=12)
        tl_table.add_column("Event", min_width=50)

        for event in timeline:
            ev_type = event["event_type"]
            ev_style = _EVENT_STYLE.get(ev_type, "")
            tl_table.add_row(
                event["timestamp"],
                f"[{ev_style}]{ev_type}[/{ev_style}]",
                event["description"],
            )

        console.print()
        console.print("[bold]Timeline[/bold]")
        console.print(tl_table)

    console.print()


@case_app.command("close")
def case_close(
    case_id: Annotated[int, typer.Argument(help="Case ID to close")],
) -> None:
    """Close an investigation case."""
    try:
        db = _get_db()
        case = db.get_case(case_id)
        if case is None:
            err_console.print(
                f"[bold red]Error:[/bold red] Case [yellow]{case_id}[/yellow] not found."
            )
            raise typer.Exit(code=1)
        db.close_case(case_id)
        console.print(
            f"\n[green]Case {case_id}[/green] ([bold white]{case['name']}[/bold white]) "
            f"marked as [dim]closed[/dim].\n"
        )
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[bold red]DB error:[/bold red] {exc}")
        raise typer.Exit(code=1)


@case_app.command("add-note")
def case_add_note(
    case_id: Annotated[int, typer.Argument(help="Case ID to annotate")],
    content: Annotated[str, typer.Argument(help="Note text to append")],
) -> None:
    """Add an investigator note to a case."""
    try:
        db = _get_db()
        case = db.get_case(case_id)
        if case is None:
            err_console.print(
                f"[bold red]Error:[/bold red] Case [yellow]{case_id}[/yellow] not found."
            )
            raise typer.Exit(code=1)
        note_id = db.add_case_note(case_id, content)
        console.print(
            f"\n[green]Note {note_id} added[/green] to case [bold]{case_id}[/bold] "
            f"({case['name']}).\n"
        )
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[bold red]DB error:[/bold red] {exc}")
        raise typer.Exit(code=1)


@case_app.command("export")
def case_export(
    case_id: Annotated[int, typer.Argument(help="Case ID to export")],
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Export format: txt or docx"),
    ] = "txt",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path (auto-generated if omitted)"),
    ] = None,
    ioc_value: Annotated[
        str | None,
        typer.Option("--ioc", help="Export only this IOC value"),
    ] = None,
) -> None:
    """Export a case report to TXT or DOCX format."""
    from lupe.case import build_case_history

    try:
        db = _get_db()
        case = db.get_case(case_id)
        if case is None:
            err_console.print(
                f"[bold red]Error:[/bold red] Case [yellow]{case_id}[/yellow] not found."
            )
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[bold red]DB error:[/bold red] {exc}")
        raise typer.Exit(code=1)

    # Build history
    try:
        history = build_case_history(case_id)
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[bold red]Error building history:[/bold red] {exc}")
        raise typer.Exit(code=1)

    # Filter to single IOC if requested
    if ioc_value is not None:
        matching = [g for g in history["iocs"] if g["ioc"]["value"] == ioc_value]
        if not matching:
            err_console.print(
                f"[bold red]Error:[/bold red] IOC [yellow]{ioc_value}[/yellow] not found in case."
            )
            raise typer.Exit(code=1)
        history = {**history, "iocs": matching}

    # Determine output path
    if output is None:
        safe_name = case["name"].replace(" ", "_").replace("/", "_")[:40]
        suffix = ".txt" if format == "txt" else ".docx"
        output = Path(f"case_{case_id}_{safe_name}{suffix}")

    # Export
    try:
        if format == "docx":
            from lupe.export.docx_export import export_case_to_docx

            result_path = export_case_to_docx(history, output)
        else:
            from lupe.export.txt_export import export_case_to_txt

            content = export_case_to_txt(history)
            output.write_text(content, encoding="utf-8")
            result_path = output

        console.print(f"[green]Exported[/green] to [bold]{result_path}[/bold]")
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[bold red]Export error:[/bold red] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# person subcommands
# ---------------------------------------------------------------------------


@person_app.command("enrich")
def person_enrich(
    name: Annotated[
        str | None, typer.Option("--name", "-n", help="Nombre completo (referencia)")
    ] = None,
    phone: Annotated[
        str | None, typer.Option("--phone", "-p", help="Número de teléfono (ej: +54 9 2954 123456)")
    ] = None,
    username: Annotated[
        str | None, typer.Option("--username", "-u", help="Nombre de usuario")
    ] = None,
    email: Annotated[str | None, typer.Option("--email", "-e", help="Email a investigar")] = None,
    no_ai: Annotated[bool, typer.Option("--no-ai", help="Omitir análisis AI")] = False,
    case_id: Annotated[int | None, typer.Option("--case", help="ID de caso para guardar")] = None,
) -> None:
    """Enriquece una persona por teléfono, username y/o email."""
    if not phone and not username and not email:
        console.print("[red]Debés proveer al menos --phone, --username o --email.[/red]")
        raise typer.Exit(1)

    settings = get_settings()
    all_results: list[EnrichmentResult] = []
    iocs_processed: list[IOC] = []

    if phone:
        phone_ioc = detect_ioc(phone)
        if phone_ioc is None or phone_ioc.type != IOCType.phone:
            console.print(
                f"[red]'{phone}' no es un número de teléfono válido. Usá formato +XX...[/red]"
            )
            raise typer.Exit(1)
        with console.status(f"[bold cyan]Enriqueciendo teléfono {phone}...[/bold cyan]"):
            phone_results = asyncio.run(run_enrichment(phone_ioc, settings))
        all_results.extend(phone_results)
        iocs_processed.append(phone_ioc)

    if username:
        user_ioc = IOC(type=IOCType.username, value=username)
        with console.status(f"[bold cyan]Buscando username '{username}' en redes...[/bold cyan]"):
            user_results = asyncio.run(run_enrichment(user_ioc, settings))
        all_results.extend(user_results)
        iocs_processed.append(user_ioc)

    if email:
        email_ioc = IOC(type=IOCType.email, value=email)
        with console.status(f"[bold cyan]Investigando email {email}...[/bold cyan]"):
            email_results = asyncio.run(run_enrichment(email_ioc, settings))
        all_results.extend(email_results)
        iocs_processed.append(email_ioc)

    if not all_results:
        console.print("[yellow]Sin resultados.[/yellow]")
        return

    subject = name or phone or email or username or "persona"
    table = _build_table(all_results)
    console.print(f"\n[bold]OSINT Persona:[/bold] [cyan]{subject}[/cyan]\n")
    console.print(table)
    console.print()

    analysis_text: str | None = None
    if not no_ai and iocs_processed:
        ref_ioc = iocs_processed[0]
        with console.status("[bold magenta]Analizando con IA...[/bold magenta]"):
            try:
                analysis_text = asyncio.run(analyze_ioc(ref_ioc, all_results, settings))
            except KeyboardInterrupt:
                err_console.print("\n[yellow]AI analysis interrupted.[/yellow]")
        if analysis_text:
            console.print(
                Panel(
                    analysis_text,
                    title="[bold magenta]Análisis IA[/bold magenta]",
                    border_style="magenta",
                    expand=False,
                )
            )
            console.print()

    if case_id is not None:
        for ioc in iocs_processed:
            _save_to_db(
                ioc_type=ioc.type.value,
                ioc_value=ioc.value,
                results=[r for r in all_results if r.ioc_value == ioc.value],
                analysis_text=analysis_text,
                model=settings.ollama_model,
                case_id=case_id,
            )


# ---------------------------------------------------------------------------
# config subcommands
# ---------------------------------------------------------------------------


@config_app.command("show")
def config_show() -> None:
    """Show current configuration with API keys masked."""
    settings = get_settings()

    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan",
        border_style="bright_black",
    )
    table.add_column("Variable", style="bold white", min_width=30)
    table.add_column("Value", min_width=30)

    for attr, env_var in _PLAIN_FIELDS:
        value = str(getattr(settings, attr, "") or "")
        table.add_row(env_var, value)

    for attr, env_var in _KEY_FIELDS:
        raw = getattr(settings, attr, None)
        table.add_row(env_var, _mask_key(raw))

    console.print()
    console.print(table)
    console.print()


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Variable name (e.g. LUPE_VT_KEY)")],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    """Write or update a key=value pair in the .env file."""
    from re import fullmatch

    # Validate key name: only uppercase letters, digits, underscores
    if not fullmatch(r"^[A-Z][A-Z0-9_]*$", key.upper()):
        err_console.print(
            f"[bold red]Invalid key name:[/bold red] "
            f"[yellow]{key}[/yellow]\n"
            "Keys must start with a letter and contain only "
            "uppercase letters, digits, and underscores."
        )
        raise typer.Exit(code=1)

    # Validate value: no control characters
    if "\x00" in value or "\r\n" in value or "\n" in value:
        err_console.print(
            "[bold red]Invalid value:[/bold red] "
            "values cannot contain newlines or null characters."
        )
        raise typer.Exit(code=1)

    env_path = get_config_dir() / ".env"

    existing_lines: list[str] = []
    if env_path.exists():
        existing_lines = env_path.read_text(encoding="utf-8").splitlines()

    key_upper = key.upper()
    updated = False
    new_lines: list[str] = []

    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith(f"{key_upper}=") or stripped.startswith(f"{key_upper} ="):
            new_lines.append(f"{key_upper}={value}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"{key_upper}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    action = "Updated" if updated else "Added"
    console.print(
        f"[green]{action}[/green] [bold]{key_upper}[/bold] in [cyan]{env_path.resolve()}[/cyan]"
    )


@config_app.command("test")
def config_test() -> None:
    """Test connectivity to all configured APIs."""
    import httpx as _httpx

    settings = get_settings()

    checks: list[tuple[str, str | None, str]] = [
        ("AbuseIPDB", settings.abuseipdb_key, "https://api.abuseipdb.com/api/v2/check"),
        (
            "VirusTotal",
            settings.virustotal_key,
            "https://www.virustotal.com/api/v3/ip_addresses/1.1.1.1",
        ),
        ("Shodan", settings.shodan_key, "https://api.shodan.io/api-info"),
        ("OTX", settings.otx_key, "https://otx.alienvault.com/api/v1/user/me"),
        (
            "URLScan",
            settings.urlscan_key,
            "https://urlscan.io/api/v1/search/?q=domain:example.com&size=1",
        ),
        (
            "HIBP",
            settings.hibp_key,
            "https://haveibeenpwned.com/api/v3/breachedaccount/test@example.com",
        ),
        ("URLhaus", "configured", "https://urlhaus-api.abuse.ch/v1/urls/recent/"),
        ("MalwareBazaar", "configured", "https://mb-api.abuse.ch/api/v1/"),
        ("GreyNoise", settings.greynoise_key, "https://api.greynoise.io/v3/community/1.1.1.1"),
        ("IPQS", settings.ipqs_key, "https://www.ipqualityscore.com/api/json/ip"),
        ("Ollama", "configured", f"{settings.ollama_base_url.rstrip('/')}/api/tags"),
    ]

    console.print("\n[bold]Lupe CTI[/bold] — API Connectivity Test\n")

    for name, key, url in checks:
        if key is None:
            console.print(f"  [dim]{name:<12}[/dim]  [dim]skipped — key not configured[/dim]")
            continue

        try:
            with _httpx.Client(timeout=8.0) as client:
                resp = client.get(url)
            # Most APIs return 200, 400, or 401 when reachable
            reachable = resp.status_code < 500
            status_code = resp.status_code
        except _httpx.ConnectError:
            reachable = False
            status_code = 0
        except _httpx.RequestError:
            reachable = False
            status_code = 0

        if reachable:
            console.print(f"  [green]{name:<12}[/green]  reachable [dim](HTTP {status_code})[/dim]")
        else:
            console.print(f"  [red]{name:<12}[/red]  unreachable [dim](HTTP {status_code})[/dim]")

    console.print()


# ---------------------------------------------------------------------------
# migrate-from-centinela command
# ---------------------------------------------------------------------------


@app.command("migrate-from-centinela")
def migrate_from_centinela() -> None:
    """Migrate legacy Centinela DB to Lupe CTI XDG path."""
    from lupe.migrate import _LEGACY_DB_PATH
    from lupe.migrate import migrate_from_centinela as _do_migrate

    console.print("\n[bold]Lupe CTI[/bold] — Migration from Centinela\n")

    if not _LEGACY_DB_PATH.exists():
        console.print(f"  [yellow]Legacy DB not found at:[/yellow] {_LEGACY_DB_PATH}")
        console.print("  Nothing to migrate.")
        raise typer.Exit(code=1)

    console.print(f"  [bold]Source:[/bold] {_LEGACY_DB_PATH}")
    result = _do_migrate()

    if result.get("error"):
        console.print(f"  [bold red]Error:[/bold red] {result['error']}")
        raise typer.Exit(code=1)

    console.print(f"  [bold]Target:[/bold] {result['target']}")
    console.print(f"  [bold]Backup:[/bold] {result['backup_path']}")
    console.print()

    if result["tables"]:
        console.print("  [bold]Tables migrated:[/bold]")
        for table, count in result["tables"].items():
            console.print(f"    {table}: {count} rows")

    console.print()
    console.print("  [green]Migration complete![/green]")
    console.print()


# ---------------------------------------------------------------------------
# misp subcommands
# ---------------------------------------------------------------------------


def _get_misp_client() -> MISPClient:
    """Create a MISPClient from settings. Raises typer.Exit if not configured."""
    from lupe.integrations.misp import MISPClient

    settings = get_settings()
    if not settings.misp_url or not settings.misp_key:
        err_console.print(
            "[bold red]Error:[/bold red] MISP not configured.\n"
            "  Set [bold]LUPE_MISP_URL[/bold] and [bold]LUPE_MISP_KEY[/bold] "
            "environment variables.\n"
            "  See: https://lupe-cti.readthedocs.io/en/latest/misp/"
        )
        raise typer.Exit(code=1)
    return MISPClient(url=settings.misp_url, api_key=settings.misp_key)


@misp_app.command("pull")
def misp_pull(
    tag: Annotated[
        str | None,
        typer.Option("--tag", "-t", help="Filter by tag (e.g. osint)"),
    ] = None,
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Look back N days"),
    ] = 7,
) -> None:
    """Pull IOCs from MISP and display them."""
    from lupe.integrations.misp import MISPAuthError, MISPConnectionError

    client = _get_misp_client()

    console.print(f"\n[bold]Lupe CTI[/bold] — Pulling from MISP (last {days} days)\n")

    try:
        tags = [tag] if tag else None
        indicators = asyncio.run(client.get_indicators(tags=tags, days=days))
    except MISPAuthError as exc:
        err_console.print(f"[bold red]MISP Auth Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    except MISPConnectionError as exc:
        err_console.print(f"[bold red]MISP Connection Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    finally:
        asyncio.run(client.close())

    if not indicators:
        console.print("[dim]No indicators found.[/dim]\n")
        return

    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="bright_black",
        expand=False,
    )
    table.add_column("UUID", style="dim", min_width=8)
    table.add_column("Type", style="bold white", min_width=10)
    table.add_column("Value", min_width=30)
    table.add_column("Category", min_width=15)

    for ind in indicators[:50]:  # Cap display at 50
        table.add_row(
            ind["uuid"][:8],
            ind["type"],
            ind["value"],
            ind.get("category", ""),
        )

    console.print(table)
    console.print(f"\n[dim]{len(indicators)} indicator(s) found[/dim]\n")


@misp_app.command("push")
def misp_push(
    ioc_value: Annotated[str, typer.Argument(help="IOC value to push to MISP")],
    tag: Annotated[
        list[str] | None,
        typer.Option("--tag", "-t", help="Tag(s) to apply"),
    ] = None,
) -> None:
    """Push an analyzed IOC to MISP."""
    from lupe.integrations.misp import MISPAuthError, MISPConnectionError
    from lupe.ioc_detect import detect_ioc

    ioc = detect_ioc(ioc_value)
    if ioc is None:
        err_console.print(
            f"[bold red]Error:[/bold red] IOC type not recognized for: [yellow]{ioc_value}[/yellow]"
        )
        raise typer.Exit(code=1)

    client = _get_misp_client()

    console.print(f"\n[bold]Lupe CTI[/bold] — Pushing {ioc.type.value} to MISP\n")

    try:
        uuid = asyncio.run(
            client.add_indicator(
                {
                    "type": "ip-dst" if "ip" in ioc.type.value else ioc.type.value,
                    "value": ioc.value,
                    "category": "Network activity",
                },
                tags=tag,
                info=f"Lupe CTI enrichment: {ioc.value}",
            )
        )
    except MISPAuthError as exc:
        err_console.print(f"[bold red]MISP Auth Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    except MISPConnectionError as exc:
        err_console.print(f"[bold red]MISP Connection Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    finally:
        asyncio.run(client.close())

    console.print(f"[green]Pushed![/green] UUID: [bold]{uuid}[/bold]\n")


# ---------------------------------------------------------------------------
# upgrade command
# ---------------------------------------------------------------------------


@app.command()
def upgrade() -> None:
    """Check for updates and install the latest version from GitHub."""
    from lupe.updater import (
        download_wheel_with_verification,
        get_current_version,
        get_latest_version,
        install_wheel,
        is_update_available,
    )

    settings = get_settings()
    github_repo = settings.github_repo

    console.print("\n[bold]Lupe CTI[/bold] — Checking for updates\n")

    try:
        current = get_current_version()
    except Exception:
        current = "0.0.0"

    console.print(f"  Current version: [bold]{current}[/bold]")

    latest = get_latest_version(github_repo)
    if latest is None:
        err_console.print("  [yellow]Could not fetch latest version from GitHub.[/yellow]")
        raise typer.Exit(code=1)

    console.print(f"  Latest version:  [bold]{latest}[/bold]")

    if not is_update_available(current, latest):
        console.print(f"\n  [green]Already on the latest version ({current}).[/green]\n")
        return

    console.print(f"\n  [yellow]Update available: {current} → {latest}[/yellow]")

    # Confirm
    if not typer.confirm("  Update now?"):
        console.print("  [dim]Cancelled.[/dim]")
        raise typer.Exit()

    # Download wheel
    wheel_name = f"lupe_cti-{latest}-py3-none-any.whl"
    wheel_url = f"https://github.com/{github_repo}/releases/download/v{latest}/{wheel_name}"

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".whl", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    console.print(f"  Downloading {wheel_name}...")
    ok, reason = download_wheel_with_verification(
        wheel_url, tmp_path, github_repo, f"v{latest}"
    )
    if not ok:
        if reason == "mismatch":
            err_console.print(
                "  [bold red]Integrity check failed: SHA256 mismatch.[/bold red]\n"
                "  The downloaded wheel does not match the published checksum.\n"
                "  Refusing to install — please verify the release manually."
            )
        elif reason == "no_sha256sums":
            err_console.print(
                "  [bold red]Integrity check failed: "
                "no SHA256SUMS.txt found for this release.[/bold red]\n"
                "  Cannot verify the download. Refusing to install."
            )
        elif reason == "wheel_not_listed":
            err_console.print(
                "  [bold red]Integrity check failed: "
                "wheel not listed in SHA256SUMS.txt.[/bold red]\n"
                "  Cannot verify the download. Refusing to install."
            )
        else:
            err_console.print("  [bold red]Download failed.[/bold red]")
        tmp_path.unlink(missing_ok=True)
        raise typer.Exit(code=1)

    console.print("  Installing...")
    if not install_wheel(tmp_path):
        err_console.print("  [bold red]Installation failed.[/bold red]")
        tmp_path.unlink(missing_ok=True)
        raise typer.Exit(code=1)

    tmp_path.unlink(missing_ok=True)
    console.print(f"\n  [green]Updated to {latest}![/green] Please restart the app.\n")
