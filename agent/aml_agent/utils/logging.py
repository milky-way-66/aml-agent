import logging
import os
import sys
from typing import Optional

def setup_logger(name: str, log_level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """Set up and configure a logger. Always logs to file and console."""
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        logger.addHandler(console_handler)
    
    # Always log to file (in project folder if not specified)
    if not log_file:
        project_root = os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(project_root, "aml_agent.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == file_handler.baseFilename for h in logger.handlers):
        logger.addHandler(file_handler)
    
    return logger

# Create a default application logger
app_logger = setup_logger("aml_agent")

def log_tool_call(tool_name: str, params: dict, result: dict) -> None:
    """Log a tool call for audit purposes."""
    app_logger.info(f"Tool call: {tool_name}")
    app_logger.debug(f"Tool parameters: {params}")
    app_logger.debug(f"Tool result: {result}")

def log_agent_action(agent_name: str, action: str, details: dict) -> None:
    """Log an agent action for audit purposes."""
    app_logger.info(f"Agent action: {agent_name} - {action}")
    app_logger.debug(f"Action details: {details}")

def log_workflow_transition(from_node: str, to_node: str, reason: str) -> None:
    """Log a workflow transition for audit purposes."""
    app_logger.info(f"Workflow transition: {from_node} -> {to_node}")
    app_logger.debug(f"Transition reason: {reason}")
