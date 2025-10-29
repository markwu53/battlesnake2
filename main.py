from fastapi import FastAPI
from snake import info, start, move, end
import os

app = FastAPI(title="Battlesnake Webhook Handler")

@app.get("/")
async def info_endpoint():
    return info()

@app.post("/start")
async def start_endpoint():
    return start()

@app.post("/move")
async def move_endpoint():
    return move()

@app.post("/end")
async def end_endpoint():
    return end()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
