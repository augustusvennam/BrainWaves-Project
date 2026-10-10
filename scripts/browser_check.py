"""Headless local checks. Protocol fixtures are isolated to this browser, never runtime feeds.
Install Playwright separately; run with the actual frontend/backend already started.
"""
import copy
import json
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

OUT = Path('artifacts')
OUT.mkdir(exist_ok=True)
with urlopen('http://localhost:8000/api/snapshot') as response:
    baseline = json.load(response)

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    errors = []
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://localhost:3000')
    page.wait_for_load_state('networkidle')
    page.get_by_text('Backend connected', exact=True).wait_for()
    page.get_by_role('button', name='Start session', exact=True).click()
    page.get_by_role('button', name='Collect baseline', exact=True).wait_for(state='visible')
    page.get_by_role('button', name='Collect baseline', exact=True).click()
    page.get_by_text('baseline', exact=True).wait_for()
    assert page.get_by_role('button', name='Begin assessment', exact=True).is_disabled()
    page.get_by_role('button', name='End / reset session', exact=True).click()
    page.get_by_role('button', name='Start session', exact=True).wait_for()
    page.screenshot(path=str(OUT/'desktop-empty.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path=str(OUT/'phone-empty.png'), full_page=True)
    page.get_by_role('button', name='Presentation view', exact=True).click()
    assert page.get_by_role('button', name='Start session', exact=True).count() == 0
    page.get_by_role('button', name='Operator view', exact=True).click()
    page.close()

    # All values below are explicit test fixtures, only in the intercepted page.
    fixture = copy.deepcopy(baseline)
    fixture.update(epoch=100, session_id='browser-test-only', eeg=[], latest={}, metric_history=[], events=[], sequence=0)
    fixture['participant'] = {'id': None, 'phase': 'idle', 'message': 'Controlled browser test fixture', 'valid_samples': 0,
                              'baseline': {}, 'estimate': {'state': 'Insufficient data', 'scores': {}, 'contributions': {}}}
    fixture['recording'].update(replay=False, active=False)
    sockets = []
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    page.on('pageerror', lambda error: errors.append(str(error)))
    def socket_connected(socket):
        sockets.append(socket)
        socket.send(json.dumps(fixture))
    page.route_web_socket('**/api/live', socket_connected)
    def broadcast():
        fixture['revision'] += 1
        sockets[-1].send(json.dumps(fixture))
    def session_request(route):
        action = route.request.post_data_json['action']
        transitions = {'start':'ready', 'baseline':'baseline', 'assess':'assessment', 'confirm':'confirmed', 'end':'idle', 'cancel':'idle'}
        fixture['participant']['phase'] = transitions[action]
        fixture['participant']['id'] = None if transitions[action] == 'idle' else 'test-participant'
        if action in ('start', 'end', 'cancel'):
            fixture['epoch'] += 1
            fixture['latest'] = {}
            fixture['eeg'] = []
            fixture['metric_history'] = []
        route.fulfill(json={'ok': True})
        broadcast()
    page.route('**/api/session', session_request)
    page.route('**/api/events/clear', lambda route: route.fulfill(json={'ok': True}))
    page.goto('http://localhost:3000')
    page.wait_for_load_state('networkidle')
    page.get_by_role('button', name='Start session', exact=True).click()
    page.get_by_role('button', name='Collect baseline', exact=True).click()
    fixture['participant'].update(phase='baseline_ready', valid_samples=10)
    broadcast()
    page.get_by_role('button', name='Begin assessment', exact=True).click()
    fixture['participant'].update(phase='review', estimate={'state':'Relaxed','scores':{'Relaxed':.5},'contributions':{'rel':.3,'str':-.2}})
    fixture['eeg'] = [{'time':100+i/256, 'values':{'AF3':4000+(i%20), 'F7':4010-(i%20)}, 'interpolated':False} for i in range(256)]
    fixture['latest'] = {'met':{'time':101,'values':{'rel':.7,'eng':.4,'exc':None,'str':.2}}}
    fixture['metric_history'] = [{'time':t,'values':{'rel':.5 if t != 80 else None}} for t in range(60,102,2)]
    broadcast()
    page.get_by_role('button', name='Confirm Temi expression', exact=True).click()
    page.get_by_role('button', name='Pause waveforms', exact=True).click()
    page.get_by_role('button', name='Resume waveforms', exact=True).click()
    page.get_by_label('Time window', exact=True).select_option('30')
    page.get_by_label('Vertical scale', exact=True).select_option('common')
    page.get_by_label('All channels', exact=True).check()
    assert page.locator('canvas').count() == 2
    page.screenshot(path=str(OUT/'desktop-fixture.png'), full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path=str(OUT/'phone-fixture.png'), full_page=True)
    sockets[-1].send('{}')
    page.get_by_text('Invalid data received from backend. Waiting for a valid update.', exact=True).wait_for()
    broadcast()
    page.get_by_text('Invalid data received from backend. Waiting for a valid update.', exact=True).wait_for(state='hidden')
    sockets[-1].close()
    page.get_by_text('Backend unavailable', exact=True).wait_for()
    page.get_by_text('Backend connected', exact=True).wait_for(timeout=15000)
    fixture['recording']['replay'] = True
    fixture['participant'].update(id=None, phase='idle')
    broadcast()
    page.get_by_text('Replay — recorded measurements · robot commands disabled', exact=True).wait_for()
    for name in ['Speak', 'Stop speech / movement', 'Start session', 'Refresh profiles']:
        assert page.get_by_role('button', name=name, exact=True).is_disabled()
    fixture['recording']['replay'] = False
    fixture['epoch'] += 1
    fixture['eeg'] = []
    fixture['latest'] = {}
    fixture['metric_history'] = []
    broadcast()
    page.locator('canvas').wait_for(state='hidden')
    assert not errors, errors
    browser.close()
print('Browser checks passed: desktop/mobile, empty states, sessions, controls, malformed recovery, reconnect, Replay isolation. Fixtures were browser-only.')
