import unittest

from flask import url_for
from urllib.parse import urlparse

import server

class ServerTestCase(unittest.TestCase):

    def setUp(self):
        server.app.testing = True
        self.app_client = server.app.test_client()
        self.socketio_client = server.socketio.test_client(server.app)
        server.db.create_all()

    def tearDown(self):
        server.db.session.remove()
        server.db.drop_all()

    def test_index_redirects_with_302_to_orders(self):
        with server.app.test_request_context():
            index = url_for('index')
        res = self.app_client.get(index, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(urlparse(res.location).path, '/orders')

    def test_list_orders_contains_greeting(self):
        with server.app.test_request_context():
            index = url_for('list_orders')
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

    def test_live_orders_list_contains_Orders_header(self):
        with server.app.test_request_context():
            index = url_for('live_orders_list')
        res = self.app_client.get(index)
        self.assertEqual(res.status_code, 200)
        assert b'<h1>Orders:</h1>' in res.data

    def test_app_broadcasts_orders(self):
        data = {'drink': 'g&t', 'message': 'Make it strong.'}
        with server.app.test_request_context():
            res = self.app_client.post('/new', data=data)
        received = self.socketio_client.get_received()
        data = received[0]
        name = data.get('name')
        args = data.get('args')[0]
        self.assertEqual(len(received), 1)
        self.assertEqual(name, 'incomming')
        self.assertEqual(
            args,
            {'drink': 'Gin & Tonic', 'message': 'Make it strong.'}
        )

    def test_Order_is_created(self):
        order = server.Order('Gin', 'Now')
        self.assertEqual(str(order)[:19], 'Order("Gin", "Now",')
        self.assertEqual(
            order.nicely_formatted[:25], 'Gin, Now (order received:')

    def test_Order_throws_up(self):
        self.assertRaises(ValueError, server.Order, 1, 'Now')
        self.assertRaises(ValueError, server.Order, 'Wine', 1)
        self.assertRaises(
            ValueError, server.Order, 'Whatever Liquor', 'Lots of it, Please',
            '2000-01-01')

    def test_empty_database_returns_empty_result(self):
        all_orders = server.Order.query.all()
        self.assertEqual(len(all_orders), 0)

    def test_save_order_saves_order(self):
        server.save_order('Gin', 'Now')
        all_orders = server.Order.query.all()
        self.assertEqual(len(all_orders), 1)

if __name__ == '__main__':
    unittest.main()
