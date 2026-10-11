"""Small authenticated JSON API. Expose to internet only behind HTTPS proxy."""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from .core import ConfigurationError, Hive, ProviderError, SESSION_RE, Store, load_config


def make_handler(hive: Hive, token: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'HiveBridge/0.1'

        def _send(self, status, data):
            body = json.dumps(data).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self):
            given = self.headers.get('Authorization', '')
            if not hmac.compare_digest(given.encode(), ('Bearer ' + token).encode()):
                self._send(401, {'error': 'unauthorized'})
                return False
            return True

        def do_GET(self):
            path = urlsplit(self.path)
            if path.path == '/health':
                self._send(200, {'status': 'ok', 'version': '0.1.0'})
                return
            if not self._authorized():
                return
            if path.path == '/v1/roster':
                self._send(200, {'agents': [{'id': a.id, 'label': a.label, 'provider': a.provider}
                                           for a in hive.agents.values()],
                                 'modes': hive.config['modes']})
            elif path.path == '/v1/events':
                session_id = parse_qs(path.query).get('session_id', [''])[0]
                if not SESSION_RE.fullmatch(session_id):
                    self._send(400, {'error': 'invalid_session'})
                else:
                    self._send(200, {'session_id': session_id, 'events': hive.store.events(session_id)})
            else:
                self._send(404, {'error': 'not_found'})

        def do_POST(self):
            if self.path != '/v1/turn':
                self._send(404, {'error': 'not_found'})
                return
            if not self._authorized():
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 8192:
                    self._send(413, {'error': 'payload_size_invalid'})
                    return
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError('Not a JSON object')
                result = hive.run(payload.get('text'), payload.get('mode', 'trinity'),
                                  payload.get('session_id'))
                self._send(200, result)
            except (ValueError, TypeError, json.JSONDecodeError):
                self._send(400, {'error': 'invalid_request'})
            except ConfigurationError:
                self._send(503, {'error': 'configuration_incomplete'})
            except ProviderError:
                self._send(502, {'error': 'provider_failed'})

        def log_message(self, fmt, *args):
            # Never log user prompts or the authorization header.
            pass
    return Handler


def serve(config_path, db_path, host='127.0.0.1', port=8765):
    token = os.environ.get('HIVE_TOKEN', '')
    if len(token) < 24:
        raise ConfigurationError('Set a random HIVE_TOKEN (minimum 24 characters) before serving')
    hive = Hive(load_config(config_path), Store(db_path))
    with ThreadingHTTPServer((host, port), make_handler(hive, token)) as server:
        print(f'HiveBridge listening on http://{host}:{port} (authenticated, {len(hive.agents)} agents)')
        server.serve_forever()
