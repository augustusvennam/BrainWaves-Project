"""HTTP health/snapshot endpoints and a bounded live WebSocket feed."""
import asyncio
import time
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
temi = TemiBridge(settings.temi_url, settings.temi_token, state)


@asynccontextmanager
async def lifespan(app):
    cortex.start()
    temi.start()
    try:
        yield
    finally:
        await asyncio.gather(asyncio.to_thread(cortex.stop), asyncio.to_thread(temi.stop))
        state.acquisition.stop()
        state.acquisition.stop_replay()


app = FastAPI(title='BrainWaves local backend', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])


@app.get('/api/health')
def health():
    return {'ok': True, 'cortex': state.snapshot()['status'], 'temi_configured': bool(settings.temi_url), 'connections': state.snapshot()['connections']}


@app.get('/api/snapshot')
def snapshot():
    return state.snapshot()


@app.websocket('/api/live')
async def live(socket: WebSocket):
    if socket.headers.get('origin') not in {settings.frontend_origin, None}:
        await socket.close(code=1008)
        return
    await socket.accept()
    cursor = None
    eeg_cursor = None
    try:
        while True:
            batch = state.snapshot(cursor, eeg_cursor)
            cursor = batch['sequence']
            eeg_cursor = batch['eeg_sequence']
            await asyncio.wait_for(socket.send_json(batch), timeout=3)
            await asyncio.sleep(0.1)
    except (WebSocketDisconnect, RuntimeError, OSError, asyncio.TimeoutError):
        pass


class Speech(BaseModel):
    text: str = Field(min_length=1, max_length=300)


def send_robot(action, payload=None):
    try:
        if state.acquisition.replay:
            raise RuntimeError('Robot commands are disabled during Replay.')
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


class ParticipantAction(BaseModel):
    action: str


@app.post('/api/session', dependencies=[Depends(check_origin)])
def participant_action(body: ParticipantAction):
    try:
        if body.action in ('end', 'cancel') and not state.acquisition.replay:
            if any(c['status'] == 'accepted' for c in state.commands):
                try:
                    send_robot('stop')
                except HTTPException:
                    state.event('Participant reset: Temi cancellation could not be verified; check robot.')
            if cortex.token and state.headset:
                try:
                    cortex.submit('participant_reset', {})
                except RuntimeError:
                    state.event('Profile/training cleanup could not be verified; check Launcher before next participant.')
        with state.lock:
            if body.action == 'confirm':
                reason = state.participant.gate(state.latest, state.connections['headset']['status'] == 'connected', time.time())
                if reason:
                    raise ValueError(reason)
                if state.participant.phase != 'review' or state.participant.estimate['state'] not in ('Relaxed', 'Engaged', 'Excited', 'Stressed'):
                    raise ValueError('Review an estimate before confirming.')
                result = send_robot('expression', {'state': state.participant.estimate['state']})
                state.participant_action('confirm')
                return result
            state.participant_action(body.action)
            return state.participant.snapshot()
    except ValueError as error:
        raise HTTPException(409, str(error)) from error


@app.post('/api/events/clear', dependencies=[Depends(check_origin)])
def clear_events():
    with state.lock:
        state.events.clear()
    return {'ok': True}


class ProfileAction(BaseModel):
    operation: str
    profile: str = Field(default='', max_length=100)
    action: str = 'neutral'
    status: str = 'start'


@app.post('/api/profile', dependencies=[Depends(check_origin)])
def profile_action(body: ProfileAction):
    if state.acquisition.replay:
        raise HTTPException(409, 'Exit Replay before profile operations.')
    try:
        return cortex.submit(body.operation, body.model_dump())
    except RuntimeError as error:
        raise HTTPException(409, str(error)) from error


class RecordingAction(BaseModel):
    action: str
    consent: bool = False
    file: str = ''
    sample_rate: float | None = None
    rate_verified: bool = False


@app.get('/api/recordings')
def recordings():
    return state.acquisition.files()


@app.post('/api/recording', dependencies=[Depends(check_origin)])
def recording_action(body: RecordingAction):
    try:
        with state.lock:
            a = state.acquisition
            if body.action == 'start':
                if not state.participant.id:
                    raise ValueError('Start a participant session first.')
                a.start({'participant': state.participant.snapshot(), 'schemas': state.schemas,
                         'headset': state.headset}, body.consent)
            elif body.action == 'stop':
                a.stop()
            elif body.action == 'replay':
                if state.participant.phase != 'idle':
                    raise ValueError('End the participant before Replay.')
                a.start_replay(body.file)
                state.clear_history()
            elif body.action == 'exit_replay':
                a.stop_replay()
                state.clear_history()
            elif body.action == 'filter':
                actual_rate = (state.headset or {}).get('settings', {}).get('eegRate')
                if body.sample_rate is not None and (not actual_rate or body.sample_rate != actual_rate):
                    raise ValueError('Filter rate must match Cortex headset settings.eegRate; acquisition metadata unavailable or changed.')
                a.configure_filter(body.sample_rate)
                state.filtered_eeg.clear()
            else:
                raise ValueError('Unsupported recording action.')
            state.event('Recording/replay/filter: ' + body.action)
            return a.snapshot()
    except (ValueError, OSError, ImportError) as error:
        raise HTTPException(409, str(error)) from error
