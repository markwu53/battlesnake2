import logging
logging.getLogger("uvicorn").disabled = True
logging.getLogger("uvicorn.error").disabled = True
logging.getLogger("uvicorn.access").disabled = True

# main.py
import os
from fastapi import FastAPI
from snake import info, start, move, end   # your existing functions

app = FastAPI(title="Battlesnake Webhook Handler")

@app.get("/")
def info_endpoint():
    # info() probably doesn't need a body — call it directly
    return info()

@app.post("/start")
def start_endpoint(game_state: dict):
    # FastAPI will parse JSON body into a dict
    return start(game_state)

@app.post("/move")
def move_endpoint(game_state: dict):
    return move(game_state)

@app.post("/end")
def end_endpoint(game_state: dict):
    return end(game_state)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
