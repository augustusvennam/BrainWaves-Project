import unittest

from backend.data import normalize_sample
from backend.state import DashboardState


class SampleTests(unittest.TestCase):
    def test_eeg_columns_exclude_metadata(self):
        sample = normalize_sample('eeg', ['COUNTER', 'INTERPOLATED', 'AF3', 'F7', 'MARKERS'],
                                  {'time': 10, 'eeg': [1, 1, 4200.2, 4100.1, []]})
        self.assertEqual(sample['values'], {'AF3': 4200.2, 'F7': 4100.1})
        self.assertTrue(sample['interpolated'])

    def test_nested_contact_quality(self):
        sample = normalize_sample('dev', ['Battery', 'Signal', ['AF3', 'F7', 'OVERALL'], 'BatteryPercent'],
                                  {'time': 10, 'dev': [3, 1, [4, 2, 75], 80]})
        self.assertEqual(sample['values']['AF3'], 4)
        self.assertEqual(sample['values']['OVERALL'], 75)

    def test_inactive_metrics_are_not_fabricated(self):
        sample = normalize_sample('met', ['eng.isActive', 'eng', 'rel.isActive', 'rel', 'lex'],
                                  {'time': 10, 'met': [False, 0.8, True, 0.2, None]})
        self.assertEqual(sample['values'], {'eng': None, 'rel': 0.2, 'lex': None})

    def test_malformed_samples_rejected(self):
        for values in ([1], [True, 3], [float('nan'), 3], ['bad', 3]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                normalize_sample('eeg', ['AF3', 'F7'], {'time': 10, 'eeg': values})

    def test_invalid_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            normalize_sample('eeg', ['AF3'], {'time': float('inf'), 'eeg': [4]})

    def test_band_power_uses_provided_labels(self):
        sample = normalize_sample('pow', ['AF3/alpha', 'AF3/gamma'], {'time': 10, 'pow': [1.2, 3.4]})
        self.assertEqual(sample['values'], {'AF3/alpha': 1.2, 'AF3/gamma': 3.4})


class StateTests(unittest.TestCase):
    def setUp(self):
        self.state = DashboardState()
        self.state.session_id = 'session-one'
        self.state.subscribe({'success': [{'streamName': 'eeg', 'cols': ['AF3']}],
                              'failure': [{'streamName': 'pow', 'message': 'License denied'}]})

    def test_bounded_history_and_partial_subscription(self):
        for i in range(500):
            self.state.receive({'sid': 'session-one', 'time': i / 128, 'eeg': [i]})
        snapshot = self.state.snapshot()
        self.assertEqual(len(snapshot['eeg']), 256)
        self.assertEqual(snapshot['eeg'][-1]['values']['AF3'], 499)
        self.assertEqual(snapshot['rejected_streams']['pow'], 'License denied')
        self.assertIsNotNone(snapshot['streams']['eeg']['observed_hz'])

    def test_invalid_and_stale_session_data(self):
        self.state.receive({'sid': 'old-session', 'time': 1, 'eeg': [3]})
        self.state.receive({'sid': 'session-one', 'time': 1, 'eeg': ['invalid']})
        self.assertEqual(len(self.state.eeg), 0)
        self.assertEqual(self.state.invalid_samples, 1)

    def test_session_reset_removes_old_data(self):
        self.state.receive({'sid': 'session-one', 'time': 1, 'eeg': [3]})
        self.state.reset_session()
        snapshot = self.state.snapshot()
        self.assertIsNone(snapshot['session_id'])
        self.assertEqual(snapshot['eeg'], [])
        self.assertEqual(snapshot['latest'], {})

    def test_snapshot_is_independent(self):
        self.state.receive({'sid': 'session-one', 'time': 1, 'eeg': [3]})
        snapshot = self.state.snapshot()
        snapshot['eeg'][0]['values']['AF3'] = 99
        self.assertEqual(self.state.eeg[0]['values']['AF3'], 3)
