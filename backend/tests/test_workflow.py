"""Controlled protocol fixtures only; no simulated runtime hardware data."""
from concurrent.futures import Future
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import Mock, patch

from backend.acquisition import Acquisition
from backend.config import Settings
from backend.participant import Participant
from backend.services.cortex import CortexService, CortexError
from backend.services.temi import TemiBridge
from backend.state import DashboardState


def measurements(t, values=None):
    return {'met': {'time': t, 'values': values or {'rel': .4, 'eng': .4, 'exc': .4, 'str': .4}},
            'dev': {'time': t, 'values': {'OVERALL': 90}},
            'eq': {'time': t, 'values': {'overall': 90, 'sampleRateQuality': 1}}}


class WorkflowTests(unittest.TestCase):
    def participant(self):
        p = Participant()
        p.config.update(baseline_seconds=2, assessment_seconds=2, minimum_samples=3, persistence_seconds=1)
        p.action('start')
        p.action('baseline')
        p.started = 100
        return p

    def test_duration_without_valid_samples_does_not_complete(self):
        p = self.participant()
        p.receive(measurements(100), False, 100)
        p.receive(measurements(100), True, 150)
        self.assertEqual(p.phase, 'baseline')
        self.assertEqual(len(p.samples), 0)
        bad = measurements(100)
        bad['met']['values']['rel'] = None
        p.receive(bad, True, 100)
        self.assertEqual(len(p.samples), 0)
        bad = measurements(100)
        bad['eq']['values']['sampleRateQuality'] = -1
        p.receive(bad, True, 100)
        self.assertEqual(len(p.samples), 0)

    def test_baseline_assessment_persistence_and_reset(self):
        p = self.participant()
        for t in (100, 101, 102):
            p.receive(measurements(t), True, t)
        self.assertEqual(p.phase, 'baseline_ready')
        p.action('assess')
        p.started = 103
        for t in (103, 104, 105):
            p.receive(measurements(t, {'rel': .8, 'eng': .4, 'exc': .4, 'str': .2}), True, t)
        self.assertEqual(p.phase, 'review')
        self.assertEqual(p.estimate['state'], 'Relaxed')
        self.assertGreater(p.estimate['scores']['Relaxed'], .1)
        p.action('confirm')
        p.action('end')
        self.assertIsNone(p.id)
        self.assertEqual(p.baseline, {})
        self.assertEqual(p.estimate['state'], 'Insufficient data')

    def test_sparse_samples_and_invalid_transitions(self):
        p = self.participant()
        for t in (100, 130, 160):
            p.receive(measurements(t), True, t)
        self.assertEqual(p.phase, 'baseline')
        with self.assertRaises(ValueError):
            p.action('confirm')
        with self.assertRaises(ValueError):
            p.action('start')

    def test_reset_preserves_cortex_license_session(self):
        state = DashboardState()
        state.session_id = 'cortex-one'
        state.headset = {'id': 'hardware', 'status': 'connected'}
        state.subscribe({'success': [{'streamName': 'eeg', 'cols': ['AF3']}]})
        state.participant_action('start')
        state.receive({'sid': 'cortex-one', 'time': 1, 'eeg': [3]})
        epoch = state.epoch
        state.participant_action('end')
        self.assertEqual(state.session_id, 'cortex-one')
        self.assertIn('eeg', state.schemas)
        self.assertEqual(state.latest, {})
        self.assertGreater(state.epoch, epoch)

    def test_incremental_delivery_duplicate_order_and_slow_consumer(self):
        state = DashboardState()
        state.session_id = 'one'
        state.schemas = {'eeg': ['AF3'], 'met': ['eng']}
        for t in range(300):
            state.receive({'sid': 'one', 'time': t, 'eeg': [t], 'met': [.5]})
        snapshot = state.snapshot(after=2, eeg_after=1)
        self.assertEqual(snapshot['feed_dropped'], 43)
        self.assertEqual(snapshot['counters']['buffer_overflow'], 44)
        state.receive({'sid': 'one', 'time': 299, 'eeg': [3]})
        state.receive({'sid': 'one', 'time': 1, 'eeg': [3]})
        self.assertEqual(state.counters['duplicates'], 1)
        self.assertEqual(state.counters['out_of_order'], 1)
        current = state.snapshot(state.sequence, state.eeg_sequence)
        self.assertEqual(current['eeg'], [])
        self.assertEqual(current['metric_history'], [])
        self.assertEqual(current['feed_dropped'], 0)

    def test_recording_independent_of_browser_feed_and_consent(self):
        with TemporaryDirectory() as temp, patch('backend.acquisition.ROOT', Path(temp)):
            state = DashboardState()
            state.session_id = 'one'
            state.schemas = {'eeg': ['AF3']}
            a = state.acquisition
            with self.assertRaises(ValueError):
                a.start({}, False)
            a.start({'schemas': state.schemas}, True)
            for t in range(600):
                state.receive({'sid': 'one', 'time': t, 'eeg': [t]})
            a.stop()
            entries = [json.loads(line) for line in (Path(temp)/a.path).read_text().splitlines()]
            self.assertEqual(len([e for e in entries if e['kind'] == 'sample']), 600)
            self.assertEqual(len(state.eeg), 256)
            self.assertEqual(entries[-1]['reported_loss'], 0)
            self.assertEqual(entries[1]['columns'], ['AF3'])
            self.assertEqual(entries[1]['raw_values'], [0])

    def test_replay_pacing_isolation_eof_and_disconnect(self):
        with TemporaryDirectory() as temp, patch('backend.acquisition.ROOT', Path(temp)):
            state = DashboardState()
            a = state.acquisition
            a.start({}, True)
            for t in (100, 101):
                a.record({'kind': 'sample', 'stream': 'eeg', 'sample': {'time': t, 'values': {'AF3': 5}, 'interpolated': False}})
            a.stop()
            a.start_replay(a.path)
            state.snapshot()
            self.assertEqual(len(state.eeg), 1)
            state.receive({'sid': None, 'time': 999, 'eeg': [99]})
            state.reset_session()
            self.assertEqual(len(state.eeg), 1)
            bridge = TemiBridge('http://robot/api', '', state)
            with patch('backend.services.temi.requests.post') as post, self.assertRaises(RuntimeError):
                bridge.send('stop')
            post.assert_not_called()
            a.replay_start -= 2
            state.snapshot()
            self.assertEqual(len(state.eeg), 2)
            state.snapshot()
            self.assertTrue(a.replay_finished)
            self.assertIsNotNone(a.replay)
            a.stop_replay()

    def test_queue_owner_and_profile_ownership(self):
        state = DashboardState()
        state.headset = {'id': 'one'}
        service = CortexService(Settings.from_env(), state)
        service.token = 'test'
        future = Future()
        service.requests.put(('refresh', {}, future))
        def rpc(method, params):
            if method == 'getCurrentProfile':
                return {'name': 'other', 'loadedByThisApp': False}
            return [{'name': 'one'}]
        with patch.object(service, 'request', side_effect=rpc) as request:
            service.process_requests()
            self.assertEqual(future.result()['items'], [{'name': 'one'}])
            with self.assertRaises(CortexError):
                service.operator_request('unload', {})
            self.assertNotIn('setupProfile', [c.args[0] for c in request.call_args_list])

    def test_training_sys_gate_and_neutral_action(self):
        state = DashboardState()
        state.headset = {'id': 'one'}
        state.session_id = 'sid'
        state.schemas['sys'] = ['event', 'msg']
        service = CortexService(Settings.from_env(), state)
        service.token = 'test'
        def rpc(method, params):
            if method == 'getCurrentProfile':
                return {'name': 'own', 'loadedByThisApp': True}
            if method == 'getDetectionInfo':
                return {'actions': ['neutral', 'push'], 'controls': ['start', 'accept', 'reject', 'reset']}
            return {}
        with patch.object(service, 'request', side_effect=rpc) as request:
            service.operator_request('training', {'action': 'neutral', 'status': 'start'})
            with self.assertRaises(CortexError):
                service.operator_request('training', {'action': 'push', 'status': 'accept'})
            state.receive({'sid': 'sid', 'time': 100, 'sys': ['mentalCommand', 'MC_Succeeded']})
            service.operator_request('training', {'action': 'push', 'status': 'accept'})
            self.assertEqual(request.call_args.args[1]['action'], 'neutral')
            self.assertTrue(state.profiles['neutral_accepted'])

    def test_command_completion_timeout_and_cancellation(self):
        state = DashboardState()
        bridge = TemiBridge('http://robot/api', '', state)
        state.commands.append({'id': 'one', 'status': 'accepted', 'time': time.time()})
        with patch('backend.services.temi.requests.get', return_value=Mock(json=Mock(return_value={'id': 'one', 'status': 'completed'}))):
            bridge.poll_commands()
        self.assertEqual(state.commands[-1]['status'], 'completed')
        state.commands.append({'id': 'two', 'status': 'accepted', 'time': time.time()-31})
        with patch('backend.services.temi.requests.get', return_value=Mock(json=Mock(return_value={'id': 'wrong', 'status': 'completed'}))):
            bridge.poll_commands()
        self.assertEqual(state.commands[-1]['status'], 'timed_out')

    def test_causal_filter_preserves_raw_and_resets_discontinuity(self):
        a = Acquisition()
        try:
            a.configure_filter(256)
        except ImportError:
            self.skipTest('Optional SciPy not installed.')
        raw = {'time': 1, 'values': {'AF3': 4000}, 'interpolated': False}
        a.filtered(raw)
        a.filtered({'time': 1+1/256, 'values': {'AF3': 4010}, 'interpolated': False})
        result = a.filtered({'time': 3, 'values': {'AF3': 4000}, 'interpolated': False})
        self.assertAlmostEqual(result['values']['AF3'], 0, places=6)
        self.assertEqual(raw['values']['AF3'], 4000)
        a.configure_filter(None)
        self.assertEqual(a.filter_state, {})

    def test_malformed_recording_pauses_without_leaving_replay(self):
        with TemporaryDirectory() as temp, patch('backend.acquisition.ROOT', Path(temp)):
            (Path(temp)/'bad.jsonl').write_text('{bad json}\n')
            a = Acquisition()
            a.start_replay('bad.jsonl')
            self.assertEqual(a.tick(), [])
            self.assertIn('Malformed recording', a.replay_error)
            self.assertTrue(a.replay_finished)
            self.assertIsNotNone(a.replay)
            a.stop_replay()

    def test_old_participant_queued_request_is_cancelled(self):
        state = DashboardState()
        service = CortexService(Settings.from_env(), state)
        future = Future()
        service.requests.put(('load', {'profile':'old', '_epoch':state.epoch}, future))
        state.participant_action('start')
        with patch.object(service, 'operator_request') as operation:
            service.process_requests()
            operation.assert_not_called()
        with self.assertRaises(CortexError):
            future.result()

    def test_stale_review_masks_estimate(self):
        state = DashboardState()
        state.participant.action('start')
        state.participant.phase = 'review'
        state.participant.estimate = {'state':'Relaxed','scores':{'Relaxed':.5},'contributions':{}}
        state.latest = measurements(time.time()-100)
        state.connections['headset']['status'] = 'connected'
        self.assertEqual(state.snapshot()['participant']['estimate']['state'], 'Insufficient data')

    def test_sample_rate_gap_loss_and_raw_markers(self):
        with TemporaryDirectory() as temp, patch('backend.acquisition.ROOT', Path(temp)):
            state = DashboardState()
            state.session_id = 'one'
            state.headset = {'settings':{'eegRate':256}}
            state.schemas = {'eeg':['AF3','MARKERS']}
            a = state.acquisition
            a.start({}, True)
            state.receive({'sid':'one','time':1,'eeg':[4000, []]})
            state.receive({'sid':'one','time':1+3/256,'eeg':[4001, [{'label':'real marker'}]]})
            a.stop()
            self.assertEqual(a.loss, 2)
            entries = [json.loads(line) for line in (Path(temp)/a.path).read_text().splitlines()]
            self.assertEqual(entries[2]['raw_values'][1][0]['label'], 'real marker')
