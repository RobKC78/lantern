import argparse
import ctypes
import json
import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .collectors import collect, discover, interfaces, local_networks
from .analysis import analyze
from .repairs import prepare_plan, launch_helper
from .insights import BaselineStore, baseline, enrich, support_summary, research_packet, stamp
from .media import discover_media
from .research import Research


def elevated():
    return bool(ctypes.windll.shell32.IsUserAnAdmin()) if os.name == 'nt' else os.geteuid() == 0


def make_server(port=0, storage_dir=None):
    token = secrets.token_urlsafe(32)
    state = {'status': 'collecting', 'report': None, 'discovery': [], 'error': None, 'repair': None, 'history': [], 'media': None}
    research = Research()
    store = BaselineStore(storage_dir)
    repair_session = {'secret': None, 'plan': None}
    lock = threading.Lock()
    busy = threading.Lock()

    def finish_report(report):
        report['findings'] = analyze(report)
        from .guides import guides
        report['guides'] = guides()
        report['networks'] = local_networks(interfaces())
        report['privilege'] = 'elevated with launch consent' if elevated() else 'standard user'
        try:
            saved = store.read()
        except (OSError, ValueError) as exc:
            saved = None
            report['baseline_error'] = 'Saved baseline unavailable: ' + str(exc)[:200]
        with lock:
            previous = baseline(state['report']) if state['report'] else None
        enrich(report, previous, saved)
        return report

    def repair_job(plan):
        try:
            launch_helper(plan['actions'], server.server_port, repair_session['secret'])
            with lock:
                if not state['repair'] or state['repair'].get('stage') not in ('complete', 'failed'):
                    state['repair'] = {'stage': 'failed', 'message': 'The helper exited without a final report. Refresh before retrying; some actions may have completed.'}
        except Exception as exc:
            with lock:
                state['repair'] = {'stage': 'failed', 'message': str(exc)[:600]}
        finally:
            with lock:
                outcome = state['repair'] or {}
                record = {'id': secrets.token_hex(12), 'at': stamp(), 'stage': outcome.get('stage', 'failed'),
                          'results': outcome.get('results', []), 'backup': outcome.get('backup'),
                          'feedback': 'not provided', 'undo': 'No automatic undo is supported. Review the saved repair records and any Windows restore-point record. System Restore may affect other apps; stopping a service cannot reverse printed jobs or clock changes.'}
                state['history'] = (state['history'] + [record])[-20:]
            if outcome.get('stage') == 'complete':
                try:
                    refreshed = finish_report(collect())
                    with lock:
                        state['report'] = refreshed
                        record['changes_after'] = refreshed['insights']['since_last_check']
                except Exception as exc:
                    record['verification_error'] = 'Follow-up scan failed: ' + str(exc)[:200]
            with lock:
                repair_session['secret'] = None
                state['status'] = 'ready'
            busy.release()

    def job(cidr=None, media=False):
        try:
            if media:
                found = discover_media()
                with lock:
                    state['media'] = found
            elif cidr is not None:
                devices = discover(cidr)
                with lock:
                    state['discovery'] = devices
            else:
                report = finish_report(collect())
                with lock:
                    state['report'] = report
                    state['discovery'] = []
                    repair_session['plan'] = None
            with lock:
                state['status'] = 'ready'
        except Exception as exc:
            with lock:
                state.update(status='error', error=str(exc)[:300])
        finally:
            busy.release()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, body, content_type='application/json'):
            payload = body.encode() if isinstance(body, str) else json.dumps(body).encode()
            self.send_response(code)
            for name, value in {'Content-Type': content_type, 'Content-Length': str(len(payload)),
                                'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                                'Referrer-Policy': 'no-referrer',
                                'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"}.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

        def authorized(self):
            host = f'127.0.0.1:{self.server.server_port}'
            return (self.headers.get('Host') == host and
                    self.headers.get('Origin', 'http://' + host) == 'http://' + host and
                    secrets.compare_digest(self.headers.get('X-Lantern-Token', ''), token))

        def do_GET(self):
            if self.path == '/api/support-summary':
                if not self.authorized():
                    return self.reply(403, {'error': 'Forbidden'})
                with lock:
                    return self.reply(200, {'text': support_summary(state['report'] or {}, state['history'])})
            if self.path == '/api/state':
                if not self.authorized():
                    return self.reply(403, {'error': 'Forbidden'})
                with lock:
                    return self.reply(200, {**state, 'research': research.snapshot()})
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}' or self.path not in files:
                return self.reply(404, {'error': 'Not found'})
            filename, kind = files[self.path]
            self.reply(200, (Path(__file__).parent / 'ui' / filename).read_text(encoding='utf-8'), kind)

        def do_POST(self):
            if self.path == '/api/repair-event':
                supplied = self.headers.get('X-Repair-Token', '')
                with lock:
                    expected = repair_session['secret']
                if not expected or not secrets.compare_digest(supplied, expected):
                    return self.reply(403, {'error': 'Forbidden'})
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 32768:
                        raise ValueError('Invalid event size')
                    event = json.loads(self.rfile.read(length))
                    if not isinstance(event, dict) or event.get('stage') not in ('backing_up', 'repairing', 'verifying', 'complete', 'failed'):
                        raise ValueError('Invalid event')
                    with lock:
                        state['repair'] = {**(state['repair'] or {}), **event}
                    return self.reply(200, {'ok': True})
                except (ValueError, TypeError) as exc:
                    return self.reply(400, {'error': str(exc)})
            if not self.authorized():
                return self.reply(403, {'error': 'Forbidden'})
            if self.path not in ('/api/refresh', '/api/discover', '/api/stop', '/api/repair-plan', '/api/repair-approve', '/api/media-discover', '/api/baseline-save', '/api/baseline-forget', '/api/repair-feedback', '/api/research-packet', '/api/research-start'):
                return self.reply(404, {'error': 'Not found'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 <= length <= (50000 if self.path == '/api/research-start' else 2048):
                    raise ValueError('Invalid body size')
                body = json.loads(self.rfile.read(length) or b'{}')
                if not isinstance(body, dict):
                    raise ValueError('Expected object')
                if self.path == '/api/research-start':
                    research.start(body.get('text'), body.get('consent'))
                    return self.reply(202, {'status': 'running'})
                if self.path == '/api/research-packet':
                    with lock:
                        packet = research_packet(state['report'] or {}, body.get('id'), body.get('include_details') is True)
                    return self.reply(200, {'text': packet})
                if self.path in ('/api/baseline-save', '/api/baseline-forget'):
                    if body.get('consent') is not True:
                        raise ValueError('Explicit baseline consent required')
                    with lock:
                        if state['status'] != 'ready' or not state['report']:
                            return self.reply(409, {'error': 'Wait until checks finish'})
                        if self.path.endswith('save'):
                            store.save(baseline(state['report']))
                        else:
                            store.forget()
                        enrich(state['report'], saved=store.read())
                    return self.reply(200, {'status': 'saved' if self.path.endswith('save') else 'forgotten'})
                if self.path == '/api/repair-feedback':
                    if body.get('feedback') not in ('It works now', 'Still broken', 'Not tested'):
                        raise ValueError('Choose a supported outcome')
                    with lock:
                        record = next((r for r in state['history'] if r['id'] == body.get('id')), None)
                        if not record:
                            raise ValueError('Repair history item not found')
                        record['feedback'] = body['feedback']
                    return self.reply(200, {'ok': True})
                if self.path == '/api/repair-plan':
                    with lock:
                        if state['status'] != 'ready' or not state['report']:
                            return self.reply(409, {'error': 'Wait for the current check to finish'})
                        plan = prepare_plan(state['report'], body.get('ids'))
                        repair_session['plan'] = plan
                    return self.reply(200, plan)
                if self.path == '/api/repair-approve':
                    if body.get('consent') is not True:
                        raise ValueError('Review and approve the repair plan first')
                    if not busy.acquire(blocking=False):
                        return self.reply(409, {'error': 'Another operation is running'})
                    with lock:
                        plan = repair_session['plan']
                        if not plan or body.get('plan_id') != plan['id'] or time.time() > plan['expires_at']:
                            busy.release()
                            return self.reply(409, {'error': 'This plan expired or changed. Review it again.'})
                        repair_session.update(plan=None, secret=secrets.token_hex(32))
                        state.update(status='repairing', repair={'stage': 'permission', 'message': 'Waiting for operating-system permission. No repairs have started.'})
                    threading.Thread(target=repair_job, args=(plan,), daemon=True).start()
                    return self.reply(202, {'status': 'started'})
                if self.path == '/api/stop':
                    if state['status'] == 'repairing':
                        return self.reply(409, {'error': 'Wait for the repair helper to finish before stopping the app'})
                    self.reply(200, {'status': 'stopping'})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                cidr = None
                media = self.path == '/api/media-discover'
                if media and body.get('consent') is not True:
                    raise ValueError('Explicit nearby-media discovery consent required')
                if self.path == '/api/discover':
                    if body.get('consent') is not True or not isinstance(body.get('cidr'), str):
                        raise ValueError('Explicit discovery consent and subnet required')
                    cidr = body['cidr']
                if not busy.acquire(blocking=False):
                    return self.reply(409, {'error': 'A collection is already running'})
                with lock:
                    state.update(status='discovering' if cidr or media else 'collecting', error=None)
                threading.Thread(target=job, args=(cidr, media), daemon=True).start()
                self.reply(202, {'status': 'started'})
            except (ValueError, TypeError, OSError) as exc:
                self.reply(400, {'error': str(exc)})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    busy.acquire()
    threading.Thread(target=job, daemon=True).start()
    return server, token


def main():
    parser = argparse.ArgumentParser(description='Lantern local diagnostics')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--repair-helper', help=argparse.SUPPRESS)
    parser.add_argument('--consent-elevated', action='store_true', help='Explicitly permit collection in an already elevated session')
    args = parser.parse_args()
    if args.repair_helper:
        from .repairs import helper_main
        helper_main(args.repair_helper)
        return
    if elevated() and not args.consent_elevated:
        parser.error('Run as a standard user, or explicitly add --consent-elevated. This app never elevates itself.')
    server, token = make_server(args.port)
    url = f'http://127.0.0.1:{server.server_port}/#{token}'
    print('Lantern is running. Keep this window open. Close with Ctrl+C or Stop in the dashboard.', flush=True)
    if args.no_browser:
        print(url, flush=True)
    else:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
