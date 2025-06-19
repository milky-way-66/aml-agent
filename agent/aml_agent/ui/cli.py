import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import json

from ..core.memory.memory_manager import MemoryManager
from ..core.conversation.conversation_manager import ConversationManager
from ..core.agents.orchestrator import Orchestrator
from ..core.agents.planner import Planner
from ..core.agents.executor import Executor
from ..core.agents.evaluator import Evaluator
from ..core.workflow import AMLWorkflow
from ..tools.rag_client import RAGClient
from ..tools.mcp_client import MCPClient
from .ui_controller import UIController
from ..config.settings import settings

app = typer.Typer(help="AML Detection Agent CLI")
console = Console()

# Initialize components
memory_manager = MemoryManager()
conversation_manager = ConversationManager(memory_manager)
orchestrator = Orchestrator(memory_manager)
rag_client = RAGClient(settings.rag_api_base_url, settings.rag_api_key)
mcp_client = MCPClient()
planner = Planner(memory_manager, mcp_client, rag_client)
executor = Executor(memory_manager, rag_client, mcp_client)
evaluator = Evaluator(memory_manager)
workflow = AMLWorkflow(memory_manager, orchestrator, planner, executor, evaluator)
ui_controller = UIController(orchestrator, conversation_manager, workflow)

@app.command("start")
def start_task(
    goal: str = typer.Argument(..., help="The goal of the AML detection task"),
    context: Optional[str] = typer.Option(None, help="Additional context as JSON string")
):
    """Start a new AML detection task."""
    try:
        context_dict = json.loads(context) if context else {}
    except json.JSONDecodeError:
        console.print("[bold red]Error:[/bold red] Context must be a valid JSON string")
        raise typer.Exit(1)
    
    response = ui_controller.handle_command("start_task", {
        "description": goal,
        "context": context_dict
    })
    
    formatted_response = ui_controller.display_response(response)
    
    console.print(Panel(
        formatted_response,
        title="Task Started",
        border_style="green"
    ))

@app.command("status")
def get_task_status(task_id: str = typer.Argument(..., help="The ID of the task")):
    """Get the status of an AML detection task."""
    response = ui_controller.handle_command("get_task_status", {"task_id": task_id})
    formatted_response = ui_controller.display_response(response)
    
    console.print(Panel(
        formatted_response,
        title=f"Task Status: {task_id}",
        border_style="blue"
    ))

@app.command("list")
def list_tasks(limit: int = typer.Option(10, help="Maximum number of tasks to list")):
    """List recent AML detection tasks."""
    response = ui_controller.handle_command("list_tasks", {"limit": limit})
    
    if response.get("status") == "success" and "tasks" in response:
        tasks = response["tasks"]
        
        if not tasks:
            console.print("No tasks found.")
            return
            
        table = Table(title="Recent Tasks")
        table.add_column("Task ID", style="cyan")
        table.add_column("Created At", style="green")
        table.add_column("Updated At", style="yellow")
        
        for task in tasks:
            table.add_row(
                task["task_id"],
                task["created_at"],
                task["updated_at"]
            )
        
        console.print(table)
    else:
        formatted_response = ui_controller.display_response(response)
        console.print(formatted_response)

@app.command("chat")
def chat():
    """Start an interactive chat session with the AML detection agent."""
    console.print("Starting AML Investigation Assistant...")
    
    # Start a new chat session
    response = ui_controller.handle_command("start_chat", {})
    
    if response.get("status") != "success":
        console.print(f"[bold red]Error:[/bold red] {response.get('message', 'Failed to start chat session')}")
        raise typer.Exit(1)
    
    session_id = response["session_id"]
    console.print(Panel(
        "Chat session started. Type 'exit' to end the session.",
        title="AML Detection Agent Chat",
        border_style="green"
    ))
    
    # Interactive chat loop
    while True:
        user_input = console.input("[bold green]You:[/bold green] ")
        
        if user_input.lower() in ["exit", "quit", "/exit", "/quit"]:
            console.print("Chat session ended.")
            break
        
        # Handle special commands
        if user_input.startswith("/"):
            if user_input == "/help":
                console.print(Panel(
                    "Available commands:\n"
                    "/exit - End the chat session\n"
                    "/help - Show this help message",
                    title="Help",
                    border_style="blue"
                ))
                continue
            else:
                console.print(f"[bold yellow]Unknown command:[/bold yellow] {user_input}")
                continue
        
        # Process the message
        response = ui_controller.handle_command("chat_message", {
            "session_id": session_id,
            "message": user_input
        })
        
        formatted_response = ui_controller.display_response(response)
        console.print(f"[bold blue]Agent:[/bold blue] {formatted_response}")

@app.command("export")
def export_task(
    task_id: str = typer.Argument(..., help="The ID of the task to export"),
    output_file: Optional[str] = typer.Option(None, help="Output file path (default: task_ID.json)")
):
    """Export a task's data to a JSON file."""
    response = ui_controller.handle_command("get_task_status", {"task_id": task_id})
    
    if response.get("status") != "success":
        console.print(f"[bold red]Error:[/bold red] {response.get('message', 'Failed to get task data')}")
        raise typer.Exit(1)
    
    state = response.get("state", {})
    
    # Determine output file name
    if not output_file:
        output_file = f"task_{task_id}.json"
    
    # Write to file
    try:
        with open(output_file, "w") as f:
            json.dump(state, f, indent=2)
        console.print(f"[bold green]Success:[/bold green] Task data exported to {output_file}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to write to file: {str(e)}")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
