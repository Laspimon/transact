import flask_testing
import logging
import unittest
import urllib

import server

logging.disable(logging.CRITICAL)

class TestIndex(unittest.TestCase):

    def test_index_returns_greeting(self):
        self.assertEqual(server.index(), 'Hello World')

class TestLiveIndex(flask_testing.LiveServerTestCase):

    def create_app(self):
        app = server.Flask(server.__name__)
        app = server.app
        app.config['TESTING'] = True
        app.config['LIVE_SERVERPORT'] = 0
        return app

    def test_server_awake(self):
        res = urllib.request.urlopen(self.get_server_url())
        self.assertEqual(res.code, 200)

if __name__ == '__main__':
    unittest.main()
