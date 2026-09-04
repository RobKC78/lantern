"""Run behind an HTTPS reverse proxy; never expose this loopback listener directly."""
import hashlib
import json
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from lantern.research import openai_research, valid_text


def make_service(port=8787):
    # One revocable random token per installation; configure hashes, not plaintext tokens.
    hashes = os.environ.get('LANTERN_CLIENT_TOKEN_SHA256', '').split(',')
    if not os.environ.get('OPENAI_API_KEY') or not all(len(h) == 64 for h in hashes):
        raise ValueError('Configure OPENAI_API_KEY and LANTERN_CLIENT_TOKEN_SHA256')
    gate = threading.BoundedSemaphore(4)
    lock, counts = threading.Lock(), {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log submissions, credentials or answers.

        def reply(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            self.connection.settimeout(10)
            auth = self.headers.get('Authorization', '')
            digest = hashlib.sha256(auth[7:].encode()).hexdigest()
            if not auth.startswith('Bearer ') or not any(secrets.compare_digest(digest, h) for h in hashes):
                return self.reply(401, {'error': 'Unauthorized'})
            if self.path != '/research':
                return self.reply(404, {'error': 'Not found'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 50000:
                    raise ValueError()
                body = json.loads(self.rfile.read(size))
                text = valid_text(body.get('text'))
            except (ValueError, AttributeError, OSError):
                return self.reply(400, {'error': 'Invalid summary'})
            with lock:
                day = int(time.time() // 86400)
                previous_day, count = counts.get(digest, (day, 0))
                count = count if previous_day == day else 0
                if count >= 20:
                    return self.reply(429, {'error': 'Daily research limit reached'})
                if not gate.acquire(blocking=False):
                    return self.reply(429, {'error': 'Service busy'})
                counts[digest] = (day, count + 1)
            try:
                result = openai_research(text)
                self.reply(200, result)
            except Exception:
                self.reply(502, {'error': 'Research provider unavailable'})
            finally:
                gate.release()

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    make_service().serve_forever()
