import { useEffect, useState } from 'react';
import type { Snapshot } from '../../types/dashboard';
import { request } from '../../services/api';

export function Operator({snapshot}: {snapshot: Snapshot | null}) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [speech, setSpeech] = useState('Welcome to BrainWaves.');
  const [profile, setProfile] = useState('');
  const [action, setAction] = useState('push');
  const [consent, setConsent] = useState(false);
  const [files, setFiles] = useState<string[]>([]);
  const [file, setFile] = useState('');
  const rate = snapshot?.headset?.settings?.eegRate;
  const session = snapshot?.participant;
  const replay = snapshot?.recording?.replay;
  useEffect(() => {setConsent(false); setProfile('');}, [session?.id]);
  async function send(path: string, body?: unknown) {
    setBusy(true); setError('');
    try { const result = await request(path, body); if (path === '/api/recordings') setFiles(result); }
    catch (e) {setError(e instanceof Error ? e.message : 'Request failed.');}
    finally {setBusy(false);}
  }
  return <div className="operator">
    <section className="panel"><h2>Participant session</h2><p className="command">{session?.phase.replaceAll('_', ' ') ?? 'Waiting for backend'}</p>
      <p aria-live="polite">{session?.message}</p><p className="hint">{session?.valid_samples ?? 0} valid measurements. Participant sessions are separate from the Cortex connection. Save training before End / reset; reset unloads profiles owned by this app.</p>
      <div className="controls">{[['start','Start session','idle'],['baseline','Collect baseline','ready'],['assess','Begin assessment','baseline_ready'],['confirm','Confirm Temi expression','review']].map(([a,label,phase]) => <button key={a} disabled={busy || !!replay || session?.phase !== phase || (a === 'confirm' && !['Relaxed','Engaged','Excited','Stressed'].includes(session?.estimate.state ?? ''))} onClick={() => send('/api/session',{action:a})}>{label}</button>)}
      <button disabled={busy || !session?.id} onClick={() => send('/api/session',{action:'end'})}>End / reset session</button><button disabled={busy || !session?.id} onClick={() => send('/api/session',{action:'cancel'})}>Cancel session</button></div>
    </section>
    {error && <p role="alert" className="error">{error}</p>}
    <div className="columns"><section className="panel"><h2>Profiles & guided training</h2>
      <p>Loaded: {snapshot?.profiles?.current.name ?? 'Unknown / none'}</p><p className="hint">Train neutral first, then one mental action. Wait for a successful sys event before accepting. Save explicitly after accepting.</p>
      <div className="controls"><button disabled={busy || !!replay} onClick={() => send('/api/profile',{operation:'refresh'})}>Refresh profiles</button>
      <label>Participant profile<input value={profile} list="profiles" onChange={e => setProfile(e.target.value)} /></label><datalist id="profiles">{snapshot?.profiles?.items.map(p => <option key={p.name} value={p.name}/>)}</datalist>
      {['create','load','unload','save'].map(operation => <button key={operation} disabled={busy || !!replay || (!profile && operation !== 'unload')} onClick={() => send('/api/profile',{operation,profile})}>{operation[0].toUpperCase()+operation.slice(1)} profile</button>)}</div>
      <label>One action<select value={action} onChange={e => setAction(e.target.value)}>{['push','pull','lift','drop','left','right'].map(a => <option key={a}>{a}</option>)}</select></label>
      <div className="controls"><button disabled={busy || !!replay} onClick={() => send('/api/profile',{operation:'training',action:'neutral',status:'start'})}>Train neutral</button><button disabled={busy || !!replay} onClick={() => send('/api/profile',{operation:'training',action,status:'start'})}>Train {action}</button>
      {['accept','reject','reset'].map(status => <button key={status} disabled={busy || !!replay || !snapshot?.profiles?.training_action || (status !== 'reset' && snapshot?.profiles?.training_event !== 'MC_Succeeded')} onClick={() => send('/api/profile',{operation:'training',action,status})}>{status === 'reset' ? 'Cancel training' : status+' result'}</button>)}</div><p aria-live="polite">{snapshot?.profiles?.training ?? 'Training idle'}</p></section>
      <section className="panel"><h2>Temi operator controls</h2><p>{snapshot?.connections.temi.message}</p>
      <label>Speech<textarea maxLength={300} value={speech} onChange={e => setSpeech(e.target.value)} /></label>
      <div className="controls">{['Welcome to BrainWaves.','Please relax while we collect your baseline.','Thank you for participating.'].map(text => <button key={text} onClick={() => setSpeech(text)}>{text}</button>)}</div>
      <div className="controls"><button disabled={busy || !!replay || !speech.trim()} onClick={() => send('/api/temi/speak',{text:speech})}>Speak</button><button disabled={busy || !!replay} onClick={() => send('/api/temi/stop',{})}>Stop speech / movement</button></div><p className="hint">Stop sends an SDK request; it is not a verified emergency-stop system. Acceptance and completion are separate.</p>
      <ol className="events">{snapshot?.commands?.map(c => <li key={c.id}><time>{new Date(c.time*1000).toLocaleTimeString()}</time><span>{c.action}: {c.status}</span></li>)}</ol></section></div>
    <section className="panel"><h2>Recording, Replay & optional filtering</h2><p role="status">{snapshot?.recording?.replay_error ?? (snapshot?.recording?.replay_finished ? 'Replay finished; exit Replay to resume live operation.' : '')}</p><p>Recording {snapshot?.recording?.active ? 'active' : 'off'} · reported loss {snapshot?.recording?.loss ?? 0}</p>
    <label><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)}/> Participant consent obtained for recording</label>
    <div className="controls"><button disabled={busy || !consent || !!replay || !!snapshot?.recording?.active || !session?.id} onClick={() => send('/api/recording',{action:'start',consent})}>Start recording</button><button disabled={busy || !snapshot?.recording?.active} onClick={() => send('/api/recording',{action:'stop'})}>Stop recording</button>
    <button disabled={busy} onClick={() => send('/api/recordings')}>List recordings</button><label>Recording<select value={file} onChange={e => setFile(e.target.value)}><option value="">Select a recording</option>{files.map(f => <option key={f}>{f}</option>)}</select></label><button disabled={busy || !file || !!replay} onClick={() => send('/api/recording',{action:'replay',file})}>Start Replay</button><button disabled={busy || !replay} onClick={() => send('/api/recording',{action:'exit_replay'})}>Exit Replay</button></div>
    <p>Acquisition metadata rate: {rate ?? 'Unavailable'} Hz (Cortex headset settings.eegRate)</p>
    <div className="controls"><button disabled={busy || !rate || !!replay} onClick={() => send('/api/recording',{action:'filter',sample_rate:rate})}>Enable causal 1–40 Hz view</button><button disabled={busy} onClick={() => send('/api/recording',{action:'filter',sample_rate:null})}>Disable filter</button></div><p className="hint">Raw recordings remain unchanged. Optional SciPy is required. Causal filtering has frequency-dependent delay and resets across discontinuities and participants.</p></section>
  </div>;
}

export function Estimate({snapshot}: {snapshot: Snapshot | null}) {
  const estimate = snapshot?.participant?.estimate;
  return <section className="panel estimate"><h2>Estimated state</h2><p className="command">{snapshot?.recording?.replay ? 'Replay — no live assessment' : estimate?.state ?? 'Insufficient data'}</p><p className="hint">Application heuristic relative to participant baseline; unvalidated, not a diagnosis or accurate emotion recognition.</p>
    <dl className="quality">{Object.entries(estimate?.scores ?? {}).map(([k,v]) => <div key={k}><dt>{k} score</dt><dd>{v.toFixed(3)}</dd></div>)}</dl><p className="hint">Contributing changes: {Object.entries(estimate?.contributions ?? {}).map(([k,v]) => `${k} ${v >= 0 ? '+' : ''}${v.toFixed(3)}`).join(', ') || 'No suitable measurements yet.'} Scores are not probabilities or validated confidence.</p></section>;
}
