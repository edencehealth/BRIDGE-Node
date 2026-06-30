import typer
import logging
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# Import app modules
from . import config, crypto, logger, credentials, dcr
from .registration_client import RegistrationClient, RegistrationApiError

from git import Repo

# Initialize App
app = typer.Typer(no_args_is_help=True)
console = Console()

# Configuration
APP_CONFIG = config.load_config()
SSH_KEY_PATH = Path.home() / ".ssh" / "id_rsa"
DESTINATION_DIR = config.CONFIG_DIR / "ohdsi"
VOCAB_DIR = DESTINATION_DIR / "vocab"
OUTPUT_DIR = DESTINATION_DIR / "output"

@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging to file")):
    """
    Bridge Node Registration CLI Tool.
    """
    logger.setup_logging(verbose)


@app.command()
def configure(
        api_url: str = typer.Option(None, help="Set Registration API URL"),
        token_url: str = typer.Option(None, help="Set OIDC Token URL"),
        dcr_url: str = typer.Option(None, help="Set Keycloak DCR URL"),
):
    """
    Update configuration settings.
    """
    if not api_url and not token_url and not dcr_url:
        console.print(Panel("🔧 Configuration Setup", style="bold cyan", box=box.ROUNDED))
        api_url = typer.prompt("Registration API URL", default=APP_CONFIG.get("api_url"))
        token_url = typer.prompt("OIDC Token URL", default=APP_CONFIG.get("oidc_token_url"))
        dcr_url = typer.prompt("Keycloak DCR URL", default=APP_CONFIG.get("dcr_url"))

    if api_url:
        config.save_config_value("api_url", api_url)
        logging.info(f"Updated API URL to: {api_url}")

    if token_url:
        config.save_config_value("oidc_token_url", token_url)
        logging.info(f"Updated Token URL to: {token_url}")

    if dcr_url:
        config.save_config_value("dcr_url", dcr_url)
        logging.info(f"Updated DCR URL to: {dcr_url}")

    console.print(f"[green]✔[/green] Configuration saved to [dim]{config.CONFIG_FILE}[/dim]")


@app.command()
def register(
        site_name: str = typer.Option(..., prompt="Enter Site Name"),
        api_url: str = typer.Option(APP_CONFIG.get("api_url"), help="Override API URL"),
        token_url: str = typer.Option(APP_CONFIG.get("oidc_token_url"), help="Override Token URL"),
        dcr_url: str = typer.Option(APP_CONFIG.get("dcr_url"), help="Override Keycloak DCR URL"),
):
    """
    Register a new site.
    """
    logging.info(f"Starting registration for site: {site_name}")

    if not api_url or not token_url or not dcr_url:
        console.print("[bold red]❌ Error:[/bold red] API URL, Token URL and DCR URL must be configured first.")
        console.print("Run [yellow]configure[/yellow] command or provide arguments.")
        raise typer.Exit(code=1)

    console.print(f"Starting registration for site: {site_name}")

    # 1. SSH Keys
    try:
        with console.status("[bold yellow]Checking SSH keys...", spinner="dots"):
            public_key = crypto.generate_ssh_key_if_missing(SSH_KEY_PATH)
        console.print(f"[green]✔[/green] SSH Key loaded from {SSH_KEY_PATH.name}")
        logging.info("SSH Key loaded successfully")
    except Exception:
        console.print("[bold red]❌ Failed to load SSH keys.[/bold red]")
        logging.exception("Failed to generate SSH keys")
        raise typer.Exit(code=1)

    # 2. Node OIDC credentials: reuse if present, else register via DCR
    try:
        node_creds = credentials.load()
    except Exception:
        console.print("[bold red]❌ Credentials file appears corrupted.[/bold red]")
        console.print(f"[dim]Delete {credentials.CREDENTIALS_FILE} and re-run to re-register. Logs: {config.LOG_FILE}[/dim]")
        logging.exception("Failed to parse credentials file")
        raise typer.Exit(code=1)
    if node_creds is None:
        iat = typer.prompt("Keycloak Initial Access Token", hide_input=True)
        try:
            with console.status("[bold yellow]Registering OIDC client...", spinner="dots"):
                node_creds = dcr.register_oidc_client(dcr_url, iat, f"bridge-node-{site_name}")
            credentials.save(node_creds)
            console.print("[green]✔[/green] OIDC client registered and credentials saved")
            logging.info("OIDC client registered via DCR")
        except dcr.DcrError as e:
            console.print("[bold red]❌ Client registration failed[/bold red]")
            console.print(f"[yellow]{e}[/yellow]")
            console.print(f"[dim]Detailed logs written to : {config.LOG_FILE}[/dim]")
            logging.exception("DCR failed")
            raise typer.Exit(code=1)
    else:
        console.print("[green]✔[/green] Reusing existing node credentials")
        logging.info("Reusing persisted node credentials")

    # 3. Client Setup
    client = RegistrationClient(
        api_url=api_url,
        oidc_token_url=token_url,
        oidc_client_id=node_creds.client_id,
        oidc_client_secret=node_creds.client_secret,
    )

    # 4. API Call
    try:
        with console.status("[bold cyan]Registering...", spinner="earth"):
            resp = client.register_site(site_name=site_name, public_key=public_key)

        created_at_date = resp.created_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold cyan", justify="right")
        grid.add_column(style="white")
        grid.add_row("Assigned ID:", str(resp.id))
        grid.add_row("Site Name:", resp.site_name)
        grid.add_row("Created At:", created_at_date)
        grid.add_row("Repo name:", resp.github_repo_name)
        console.print(
            Panel(
                grid,
                title="[bold green]Registration Successful! :tada:[/]",
                border_style="green",
                expand=False,
            )
        )
        logging.info(f"Registration successful! ID: {resp.id}")
        repo_name = f"git@github.com:{resp.github_org_name}/{resp.github_repo_name}.git"
    except RegistrationApiError as e:
        console.print("\n[bold red]❌ Registration Failed[/bold red]")
        console.print(f"Server returned: [yellow]{e}[/yellow]")
        console.print(f"[dim]Detailed logs written to : {config.LOG_FILE}[/dim]")
        logging.exception("API Error during registration")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print("\n[bold red]💥 Unexpected Error[/bold red]")
        console.print(f"An unexpected error occurred: {e}")
        console.print(f"[dim]Detailed logs written to : {config.LOG_FILE}[/dim]")
        logging.exception("Unexpected crash in register command")
        raise typer.Exit(code=1)

    # 5. Clone repo (idempotent)
    try:
        if DESTINATION_DIR.exists() and any(DESTINATION_DIR.iterdir()):
            console.print(f"[yellow]ℹ[/yellow] Repo already present at {DESTINATION_DIR}, skipping clone")
            logging.info("Destination already populated; skipping clone")
        else:
            with console.status("[bold cyan]Cloning repo...", spinner="earth"):
                Repo.clone_from(repo_name, DESTINATION_DIR)
            console.print(Panel("Git clone Successful! :tada:", style="bold green", box=box.ROUNDED))
    except Exception as e:
        console.print("\n[bold red]💥 Unexpected Error[/bold red]")
        console.print(f"An unexpected error occurred: {e}")
        console.print(f"[dim]Detailed logs written to : {config.LOG_FILE}[/dim]")
        raise typer.Exit(code=1)

    # 6. Data directories (idempotent, owner+group only)
    VOCAB_DIR.mkdir(mode=0o750, parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(mode=0o750, parents=True, exist_ok=True)

if __name__ == "__main__":
    app()