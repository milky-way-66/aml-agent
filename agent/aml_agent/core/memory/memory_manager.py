import json
import os
import sqlite3
from typing import Dict, Any, Optional, List
import uuid

class MemoryManager:
    """Manages state, conversation context, and persistence."""
    
    def __init__(self, storage_dir: str = "./.aml_agent_data"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.db_path = os.path.join(storage_dir, "sessions.db")
        self._init_db()
        
    def _init_db(self):
        """Initialize the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            state TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            history TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
        conn.close()
    
    def get_state(self, task_id: str) -> Dict[str, Any]:
        """Retrieve the state for a given task."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT state FROM tasks WHERE task_id = ?", (task_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return {}
    
    def update_state(self, task_id: str, state_delta: Dict[str, Any]) -> None:
        """Update the state for a given task."""
        current_state = self.get_state(task_id)
        
        # Deep merge the current state with the delta
        for key, value in state_delta.items():
            if key in current_state and isinstance(current_state[key], dict) and isinstance(value, dict):
                current_state[key].update(value)
            else:
                current_state[key] = value
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        state_json = json.dumps(current_state)
        
        cursor.execute(
            "INSERT OR REPLACE INTO tasks (task_id, state, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (task_id, state_json)
        )
        conn.commit()
        conn.close()
    
    def create_task(self, initial_state: Optional[Dict[str, Any]] = None) -> str:
        """Create a new task and return its ID."""
        task_id = str(uuid.uuid4())
        self.update_state(task_id, initial_state or {})
        return task_id
    
    def get_conversation_context(self, session_id: str) -> Dict[str, Any]:
        """Retrieve the conversation context for a given session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT history FROM conversations WHERE session_id = ?", (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return {"messages": []}
    
    def update_conversation(self, session_id: str, turn: Dict[str, Any]) -> None:
        """Update the conversation with a new turn."""
        context = self.get_conversation_context(session_id)
        
        if "messages" not in context:
            context["messages"] = []
        
        context["messages"].append(turn)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        history_json = json.dumps(context)
        
        cursor.execute(
            "INSERT OR REPLACE INTO conversations (session_id, history, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (session_id, history_json)
        )
        conn.commit()
        conn.close()
    
    def list_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent tasks."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT task_id, created_at, updated_at FROM tasks ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        )
        results = cursor.fetchall()
        conn.close()
        
        return [
            {"task_id": row[0], "created_at": row[1], "updated_at": row[2]}
            for row in results
        ]
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
