import copy
import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from hivebridge.core import Hive, Store, load_config, ConfigurationError
from hivebridge.server import make_handler
from http.server import ThreadingHTTPServer

BASE = Path(__file__).resolve().parent.parent

class HiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'test.db')
        self.config = load_config(BASE / 'council.demo.json')

    def test_trinity_is_sequential(self):
        seen = []
        def respond(agent, prompt, position):
            seen.append((agent.id, position, prompt))
            return agent.id + ' response'
        hive = Hive(self.config, self.store, respond)
        result = hive.run('Anchor says hello.', mode='trinity', session_id='alpha')
        self.assertEqual([x[0] for x in seen], ['gemi', 'princess_meta'])
        self.assertIn('gemi: gemi response', seen[1][2])
        self.assertEqual([e['agent_id'] for e in self.store.events('alpha')], ['anchor', 'gemi', 'princess_meta'])
        self.assertEqual(result['session_id'], 'alpha')

    def test_full_council_includes_eight_distinct_agents(self):
        hive = Hive(self.config, self.store)
        reply = hive.run('Council readiness check', mode='council')
        self.assertTrue(reply['simulated'])
        self.assertEqual(len(reply['steps']), 8)
        self.assertEqual(len({a['agent_id'] for a in reply['steps']}), 8)
        self.assertTrue(all('[SIMULATED ' in a['content'] for a in reply['steps']))

    def test_events_are_session_isolated_and_persist(self):
        hive = Hive(self.config, self.store)
        hive.run('First', session_id='sessionA')
        hive.run('Second', session_id='sessionB')
        new_store = Store(Path(self.tmp.name) / 'test.db')
        self.assertEqual(len(new_store.events('sessionA')), 3)
        self.assertTrue(all('Second' not in e['content'] for e in new_store.events('sessionA')))

    def test_missing_live_key_does_not_fall_back_to_simulation(self):
        config = copy.deepcopy(self.config)
        config['agents'][0].update(provider='openai_compatible', model='demo', api_key_env='HIVE_IMPOSSIBLE_TEST_KEY')
        os.environ.pop('HIVE_IMPOSSIBLE_TEST_KEY', None)
        hive = Hive(config, self.store)
        with self.assertRaises(ConfigurationError):
            hive.run('Go', session_id='nokey')
        self.assertEqual(self.store.events('nokey'), [])

    def test_reject_invalid_session(self):
        hive = Hive(self.config, self.store)
        with self.assertRaises(ValueError):
            hive.run('Hello', session_id='../../private')

    def test_server_requires_auth(self):
        hive = Hive(self.config, self.store)
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(hive, 'a'*32))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_address[1]
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
        conn.request('POST', '/v1/turn', body=json.dumps({'text': 'hi'}),
                     headers={'Content-Type': 'application/json'})
        response = conn.getresponse()
        self.assertEqual(response.status, 401)
        response.read()
        conn.close()
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
        conn.request('POST', '/v1/turn', body=json.dumps({'text': 'hi'}),
                     headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + 'a'*32})
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        result = json.loads(response.read())
        self.assertEqual(len(result['steps']), 2)
        conn.close()

if __name__ == '__main__':
    unittest.main()
