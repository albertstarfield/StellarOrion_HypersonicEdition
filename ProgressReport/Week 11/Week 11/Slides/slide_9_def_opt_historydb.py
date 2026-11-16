def get_slide_data() -> dict:
    return {
        'title': 'Optimization History Database',
        'content': '\n## Optimization History SQLite Database\n\nAll evaluation steps, design candidates, objective evaluations, and constraint violation states are saved to `optimization_history.db`.\n\n**Schema Information:**\n*   `iterations`: Stores design variables, computed objectives, and timestamps.\n*   `constraints`: Tracks violation flags (e.g. max temperature, minimum static margin).\n*   Enables post-optimization analysis, sensitivity plotting, and resumes optimization runs from interrupted states.\n'
    }
