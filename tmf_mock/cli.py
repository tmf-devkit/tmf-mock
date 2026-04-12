"""
tmf-mock CLI — `tmf-mock start --apis 638,639,641`
"""
import click
import uvicorn


@click.group()
@click.version_option(package_name="tmf-mock")
def main():
    """TMF Mock Server — Smart TMForum Open API mock with domain-aware data."""


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Bind host")
@click.option("--port", default=8000, show_default=True, type=int, help="Bind port")
@click.option(
    "--apis",
    default="638,639,641",
    show_default=True,
    help="Comma-separated list of TMF API numbers to enable",
)
@click.option("--no-seed", is_flag=True, default=False, help="Start with empty store (no seed data)")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload (dev mode)")
def start(host: str, port: int, apis: str, no_seed: bool, reload: bool):
    """Start the TMF mock server."""
    api_list = [int(a.strip()) for a in apis.split(",")]
    supported = {638, 639, 641}
    unsupported = set(api_list) - supported
    if unsupported:
        click.secho(
            f"⚠  Unsupported API numbers: {sorted(unsupported)}. "
            f"v0.1 supports: {sorted(supported)}",
            fg="yellow",
        )
        api_list = [a for a in api_list if a in supported]

    base_url = f"http://{host}:{port}" if host != "0.0.0.0" else f"http://localhost:{port}"

    click.secho("╔══════════════════════════════════════════════════╗", fg="cyan")
    click.secho("║           TMF Mock Server  v0.1.0                ║", fg="cyan")
    click.secho("╚══════════════════════════════════════════════════╝", fg="cyan")
    click.echo(f"  APIs     : {', '.join(f'TMF{a}' for a in sorted(api_list))}")
    click.echo(f"  Base URL : {base_url}")
    click.echo(f"  Seed data: {'disabled' if no_seed else 'enabled'}")
    click.echo(f"  Docs     : {base_url}/docs")
    click.echo()

    import os
    os.environ["TMF_MOCK_APIS"] = ",".join(str(a) for a in api_list)
    os.environ["TMF_MOCK_SEED"] = "0" if no_seed else "1"
    os.environ["TMF_MOCK_BASE_URL"] = base_url

    uvicorn.run(
        "tmf_mock._app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@main.command()
def apis():
    """List supported TMF APIs."""
    click.echo("\nSupported APIs in tmf-mock v0.1:\n")
    supported = [
        ("TMF638", "Service Inventory Management", "/tmf-api/serviceInventoryManagement/v4/service"),
        ("TMF639", "Resource Inventory Management", "/tmf-api/resourceInventoryManagement/v4/resource"),
        ("TMF641", "Service Ordering Management", "/tmf-api/serviceOrdering/v4/serviceOrder"),
    ]
    for api, name, path in supported:
        click.secho(f"  {api}", fg="cyan", nl=False)
        click.echo(f"  {name}")
        click.echo(f"         {path}\n")
