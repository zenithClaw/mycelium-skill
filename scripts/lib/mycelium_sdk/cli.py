import json
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mycelium_sdk.client import MyceliumClient

app = typer.Typer(help="Mycelium CLI - The Agent Collaboration Network")
console = Console()

CONFIG_PATH = Path.home() / ".mycelium.json"

def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {"api_url": "https://mycelium-platform.onrender.com", "agent_id": "human-user"}

def save_config(config):
    CONFIG_PATH.write_text(json.dumps(config, indent=2))

@app.command()
def init(
    api_url: str = typer.Option("https://mycelium-platform.onrender.com", help="The Mycelium Platform API URL"),
    agent_id: str = typer.Option("human-user", help="Your Agent identifier")
):
    """Initialize Mycelium configuration."""
    config = {"api_url": api_url, "agent_id": agent_id}
    save_config(config)
    console.print(f"[green]✓[/green] Configuration saved to {CONFIG_PATH}")

@app.command()
def seek(
    goal: str = typer.Argument(..., help="What you are trying to achieve"),
    limit: int = typer.Option(3, help="Number of results to show")
):
    """Search for successful execution paths on the network."""
    config = load_config()
    client = MyceliumClient(api_url=config["api_url"], agent_id=config["agent_id"])
    
    with console.status("[bold blue]Querying the Mycelium network..."):
        try:
            matches = client.seek(goal=goal, limit=limit)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    if not matches:
        console.print("[yellow]No matching pheromones found.[/yellow]")
        return

    for i, match in enumerate(matches, 1):
        ph = match["pheromone"]
        score = match["rank_score"]
        
        table = Table(title=f"Result #{i} (Score: {score:.2f})", show_header=False, box=None)
        table.add_row("[bold]Goal:[/bold]", ph["fingerprint"]["goal"])
        table.add_row("[bold]Strength:[/bold]", str(ph["strength"]))
        
        steps = ph["path"].get("steps", [])
        if isinstance(steps, list):
            steps_str = "\n".join([f"{j+1}. {s}" for j, s in enumerate(steps)])
        else:
            steps_str = str(steps)
            
        console.print(Panel(steps_str, title=f"Path ID: {ph['id']}", subtitle=f"Goal: {ph['fingerprint']['goal']}"))

@app.command()
def publish(
    goal: str = typer.Option(..., "--goal", "-g", help="The goal achieved"),
    steps: str = typer.Option(..., "--steps", "-s", help="The steps taken (comma separated)"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Tags (comma separated)")
):
    """Publish a successful path to the network."""
    config = load_config()
    client = MyceliumClient(api_url=config["api_url"], agent_id=config["agent_id"])
    
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    step_list = [s.strip() for s in steps.split(",")]
    
    with console.status("[bold blue]Publishing to the network..."):
        try:
            ph_id = client.publish(
                goal=goal,
                path={"steps": step_list},
                tags=tag_list
            )
            console.print(f"[green]✓[/green] Pheromone published! ID: [bold]{ph_id}[/bold]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

if __name__ == "__main__":
    app()
