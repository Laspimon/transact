import unittest

from flask import url_for
from urllib.parse import urlparse

import server

class ServerTestCase(unittest.TestCase):

    def setUp(self):
        #self.db_fd, server.app.config['DATABASE'] = tempfile.mkstemp()
        server.app.testing = True
        self.client = server.app.test_client()
        #with server.app.app_context():
        #    server.init_db()

    def tearDown(self):
        #os.close(self.db_fd)
        #os.unlink(server.app.config['DATABASE'])
        pass

    def test_index_redirects_with_302_to_messages(self):
        with server.app.test_request_context():
            index = url_for('index')
            res = self.client.get(index, follow_redirects=False)
            self.assertEqual(res.status_code, 302)
            self.assertEqual(urlparse(res.location).path, '/messages')

    def test_messages_contains_greeting(self):
        with server.app.test_request_context():
            index = url_for('index')
            res = self.client.get(index, follow_redirects=True)
            assert b'<h1>hello world!</h1>' in res.data

if __name__ == '__main__':
    unittest.main()
