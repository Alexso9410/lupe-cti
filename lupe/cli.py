from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lupe.analysis import analyze_ioc
from lupe.config import Settings, get_settings
from lupe.db import Database
from lupe.email_analyzer import analyze_email
from lupe.email_parser import parse_eml
from lupe.enrichment import run_enrichment
from lupe.ioc_detect import detect_ioc
from lupe.models import EnrichmentResult, IOC, IOCType, Severity

app = typer.Typer(
    name="lupe",
    help="Lupe CTI — Cyber Threat Intelligence for OSINT & Forensics",
    add_completion=False,
)

config_app = typer.Typer(help="Manage API keys and configuration.")
app.add_typer(config_app, name="config")

case_app = typer.Typer(help="Manage investigation cases.")
app.add_typer(case_app, name="case")

person_app = typer.Typer(help="OSINT de personas — teléfono y username.")
app.add_typer(person_app, name="person")

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
    ("abuseipdb_key", "CENTINELA_ABUSEIPDB_KEY"),
    ("virustotal_key", "CENTINELA_VIRUSTOTAL_KEY"),
    ("shodan_key", "CENTINELA_SHODAN_KEY"),
    ("otx_key", "CENTINELA_OTX_KEY"),
    ("urlscan_key", "CENTINELA_URLSCAN_KEY"),
    ("hibp_key", "CENTINELA_HIBP_KEY"),
    ("greynoise_key", "CENTINELA_GREYNOISE_KEY"),
    ("ipqs_key", "CENTINELA_IPQS_KEY"),
    ("numverify_key", "CENTINELA_NUMVERIFY_KEY"),
    ("emailrep_key", "CENTINELA_EMAILREP_KEY"),
    ("googlesb_key", "CENTINELA_GOOGLESB_KEY"),
    ("phishtank_key", "CENTINELA_PHISHTANK_KEY"),
    ("pulsedive_key", "CENTINELA_PULSEDIVE_KEY"),
]

_PLAIN_FIELDS: list[tuple[str, str]] = [
    ("ollama_base_url", "CENTINELA_OLLAMA_BASE_URL"),
    ("ollama_model", "CENTINELA_OLLAMA_MODEL"),
    ("db_path", "CENTINELA_DB_PATH"),
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
    no_ai: Annotated[
        bool, typer.Option("--no-ai", help="Skip Ollama AI analysis")
    ] = False,
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
    ioc = detect_ioc(ioc_value)
    if ioc is None:
        err_console.print(
            f"[bold red]Error:[/bold red] IOC type not recognized for: "
            f"[yellow]{ioc_value}[/yellow]"
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
            analysis_text = asyncio.run(
                analyze_ioc(ioc, results, effective_settings)
            )
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
        line.strip()
        for line in raw_lines
        if line.strip() and not line.strip().startswith("#")
    ]

    if not ioc_values:
        err_console.print("[yellow]No IOC values found in file.[/yellow]")
        raise typer.Exit(code=1)

    settings = get_settings()
    enriched = 0
    failed = 0
    saved = 0

    console.print(
        f"\n[bold]Lupe CTI Bulk[/bold] — {len(ioc_values)} IOC(s) from "
        f"[cyan]{file.name}[/cyan]\n"
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
        _order = [s.value for s in [
            Severity.critical, Severity.high, Severity.medium, Severity.low, Severity.info
        ]]
        top = min(results, key=lambda r: _order.index(r.severity.value))
        style = _SEVERITY_STYLE.get(top.severity, "")
        console.print(
            f"  [{style}]{top.severity.value}[/{style}]  "
            f"[dim]{len(results)} source(s)[/dim]"
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
    no_ai: Annotated[
        bool, typer.Option("--no-ai", help="Omitir análisis de IA")
    ] = False,
    export_pdf: Annotated[
        Path | None,
        typer.Option("--export-pdf", help="Directorio donde guardar el PDF"),
    ] = None,
) -> None:
    """Analizar un archivo .eml en busca de indicadores de phishing."""
    if not eml_file.exists() or eml_file.suffix.lower() != ".eml":
        err_console.print(
            f"[bold red]Error:[/bold red] Archivo no encontrado o extensión inválida: "
            f"[yellow]{eml_file}[/yellow]"
        )
        raise typer.Exit(code=1)

    console.print(
        f"\n[bold]Lupe CTI[/bold] — Analizando email: "
        f"[cyan]{eml_file.name}[/cyan]\n"
    )

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
        f"[bold]Phishing Score:[/bold]  "
        f"[{score_color}]{score:.1f}/10[/{score_color}]  {bar}"
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
            err_console.print(f"[bold red]Error:[/bold red] Case [yellow]{case_id}[/yellow] not found.")
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
        f"[bold white]{case['name']}[/bold white]  "
        f"[{st}]{s}[/{st}]  "
        f"[dim]id={case['id']}[/dim]\n"
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

        _order = [s.value for s in [
            Severity.critical, Severity.high, Severity.medium, Severity.low, Severity.info
        ]]

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
            err_console.print(f"[bold red]Error:[/bold red] Case [yellow]{case_id}[/yellow] not found.")
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
            err_console.print(f"[bold red]Error:[/bold red] Case [yellow]{case_id}[/yellow] not found.")
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


# ---------------------------------------------------------------------------
# person subcommands
# ---------------------------------------------------------------------------


@person_app.command("enrich")
def person_enrich(
    name: Annotated[str | None, typer.Option("--name", "-n", help="Nombre completo (referencia)")] = None,
    phone: Annotated[str | None, typer.Option("--phone", "-p", help="Número de teléfono (ej: +54 9 2954 123456)")] = None,
    username: Annotated[str | None, typer.Option("--username", "-u", help="Nombre de usuario")] = None,
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
            console.print(f"[red]'{phone}' no es un número de teléfono válido. Usá formato +XX...[/red]")
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
    key: Annotated[str, typer.Argument(help="Variable name (e.g. CENTINELA_VT_KEY)")],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    """Write or update a key=value pair in the .env file."""
    env_path = Path(".env")

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
    console.print(f"[green]{action}[/green] [bold]{key_upper}[/bold] in [cyan]{env_path.resolve()}[/cyan]")


@config_app.command("test")
def config_test() -> None:
    """Test connectivity to all configured APIs."""
    import httpx as _httpx

    settings = get_settings()

    checks: list[tuple[str, str | None, str]] = [
        ("AbuseIPDB", settings.abuseipdb_key, "https://api.abuseipdb.com/api/v2/check"),
        ("VirusTotal", settings.virustotal_key, "https://www.virustotal.com/api/v3/ip_addresses/1.1.1.1"),
        ("Shodan", settings.shodan_key, "https://api.shodan.io/api-info"),
        ("OTX", settings.otx_key, "https://otx.alienvault.com/api/v1/user/me"),
        ("URLScan", settings.urlscan_key, "https://urlscan.io/api/v1/search/?q=domain:example.com&size=1"),
        ("HIBP", settings.hibp_key, "https://haveibeenpwned.com/api/v3/breachedaccount/test@example.com"),
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
            console.print(
                f"  [green]{name:<12}[/green]  reachable [dim](HTTP {status_code})[/dim]"
            )
        else:
            console.print(
                f"  [red]{name:<12}[/red]  unreachable [dim](HTTP {status_code})[/dim]"
            )

    console.print()
