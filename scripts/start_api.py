"""Start the AI.Trader local API server."""
import sys
import uvicorn
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

if __name__ == "__main__":
    uvicorn.run(
        "src.api.server:app",
        host="127.0.0.1",
        port=8888,
        reload=False,
    )
