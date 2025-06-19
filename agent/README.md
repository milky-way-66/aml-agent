# Agentic AML Detection Application

An agentic co-pilot application to assist AML (Anti-Money Laundering) detection on blockchain, using LangGraph for multi-agent orchestration.

## Features

- Modular AI agents (Orchestrator, Planner, Executor, Evaluator)
- Tool interfaces (RAG, MCP) for data retrieval and tool calls
- Memory/state management for context and history
- CLI interface with future extensibility
- Designed for explainability, traceability, and human-in-the-loop collaboration

## Installation

```bash
# Install with Poetry
poetry install

# Or with pip
pip install .
```

## Usage

```bash
# Get help
aml-agent --help

# Start a detection task
aml-agent start "Detect suspicious activity for address 0x123..."

# Check task status
aml-agent status <task_id>

# List recent tasks
aml-agent list

# Start a chat session
aml-agent chat

# Export task data
aml-agent export <task_id> --output-file results.json
```

## Development

```bash
# Install development dependencies
poetry install --with dev

# Run tests
poetry run pytest
```

## License

MIT
