"""HTTP health/snapshot endpoints and a bounded live WebSocket feed."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests

from backend.config import Settings
from backend.services.cortex import CortexService
from backend.services.temi import TemiBridge
from backend.state import DashboardState

settings = Settings.from_env()
state = DashboardState()
cortex = CortexService(settings, state)
temi = TemiBridge(settings.temi_url, settings.temi_token)


@asynccontextmanager
async def lifespan(app):
    cortex.start()
    yield
    await asyncio.to_thread(cortex.stop)


app = FastAPI(title='BrainWaves local backend', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])


@app.get('/api/health')
def health():
    return {'ok': True, 'cortex': state.snapshot()['status'], 'temi_configured': bool(settings.temi_url)}


@app.get('/api/snapshot')
def snapshot():
    return state.snapshot()


@app.websocket('/api/live')
async def live(socket: WebSocket):
    if socket.headers.get('origin') not in {settings.frontend_origin, None}:
        await socket.close(code=1008)
        return
    await socket.accept()
    try:
        while True:
            # Every client receives bounded current state; slow consumers cannot accumulate a queue.
            await asyncio.wait_for(socket.send_json(state.snapshot()), timeout=3)
            await asyncio.sleep(0.1)
    except (WebSocketDisconnect, RuntimeError, OSError, asyncio.TimeoutError):
        pass


class Speech(BaseModel):
    text: str = Field(min_length=1, max_length=300)


def send_robot(action, payload=None):
    try:
        return temi.send(action, payload)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail='Temi bridge unreachable or rejected the command.') from error


# Reject cross-site browser commands even when a page can send a simple POST without CORS.
async def check_origin(request: Request):
    if request.headers.get('origin') not in {settings.frontend_origin, None}:
        raise HTTPException(status_code=403, detail='Origin is not allowed.')


@app.post('/api/temi/stop', dependencies=[Depends(check_origin)])
def stop_robot():
    return send_robot('stop')


@app.post('/api/temi/speak', dependencies=[Depends(check_origin)])
def speak_robot(speech: Speech):
    return send_robot('speak', {'text': speech.text})
