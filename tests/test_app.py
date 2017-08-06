import unittest

from flask import url_for
from urllib.parse import urlparse

import server

class ServerTestCase(unittest.TestCase):

    def setUp(self):
        server.app.testing = True
        self.app_client = server.app.test_client()

    def tearDown(self):
        pass

    def test_index_redirects_with_302_to_messages(self):
        with server.app.test_request_context():
            index = url_for('index')
        res = self.app_client.get(index, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(urlparse(res.location).path, '/messages')

    def test_list_messages_contains_greeting(self):
        with server.app.test_request_context():
            index = url_for('list_messages')
        res = self.app_client.get(index)
        self.assertEqual(res.status_code, 200)
        assert b'<h1>hello world!</h1>' in res.data

    def test_new_order_form_renders_choices(self):
        with server.app.test_request_context():
            index = url_for('new_order_form')
        res = self.app_client.get(index)
        self.assertEqual(res.status_code, 200)
        assert b'Gin & Tonic' in res.data
        assert b'Espresso Martini' in res.data
        assert b'Negroni' in res.data
        assert b'Beer' in res.data
        assert b'Other' in res.data

    def test_receive_order_returns_204_on_success(self):
        data = {'drink': 'g&t', 'message': 'Make it strong.'}
        with server.app.test_request_context():
            res = self.app_client.post('/new', data=data)
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.data, b'')

    def test_receive_order_returns_400_on_no_drink_selection(self):
        with server.app.test_request_context():
            response_data, status_code = server.receive_order()
        self.assertEqual(
            response_data,
            'Something\'s wrong with your order, perhaps you meant to '
            'select "Other".',)
        self.assertEqual(status_code, 400)

if __name__ == '__main__':
    unittest.main()
