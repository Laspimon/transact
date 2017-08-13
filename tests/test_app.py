import json
import os
import unittest

from flask import url_for
from urllib.parse import urlparse

from app.consumer import consume
from app.helpers import broadcast, get_redis_connection, simple_logger
from app.members import Order, prepare_demo_data
from server import app

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
app.testing = True

class RedisStub():
    queues = {}

    def __init__(self, decode_responses = False):
        self.decode_responses = decode_responses

    def rpush(self, queue, json_string):
        if not isinstance(self.queues.get(queue), list):
            self.queues[queue] = []
        self.queues.get(queue).append(json_string)

    def blpop(self, queues, timeout = 0):
        """This is for testing; No reason to implement blocking behavior.
        """
        if isinstance(queues, str):
            queues = [queues]
        for queue in queues:
            if self.queues.get(queue) is None:
                continue
            if len(self.queues) == 0:
                continue
            val = self.queues.get(queue).pop(0)
            if self.decode_responses:
                val = json.loads(val)
            return (queue, val)
        # Returns None if empty

class ServerTestCase(unittest.TestCase):

    def setUp(self):
        self.db = app.db
        self.db.create_all()

        self.app_client = app.test_client()
        self.socketio_client = app.socketio.test_client(app)

    def tearDown(self):
        self.db.session.remove()
        self.db.drop_all()

    def test_index_redirects_with_302_to_orders(self):
        with app.test_request_context():
            index = url_for('get_index_page')
        res = self.app_client.get(index, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(urlparse(res.location).path, '/orders')

    def test_list_orders_contains_header(self):
        with app.test_request_context():
            orders_page = url_for('get_orders_page')
        res = self.app_client.get(orders_page)
        self.assertEqual(res.status_code, 200)
        assert b'<h1>All Orders Ever:</h1>' in res.data


    def test_list_orders_gets_updated(self):
        with app.test_request_context():
            orders_page = url_for('get_orders_page')
        res = self.app_client.get(orders_page)
        self.assertEqual(res.status_code, 200)
        assert b'<li >Gin, Now (order received:' not in res.data
        Order('Gin', 'Now').save_order(self.db)
        res = self.app_client.get(orders_page)
        self.assertEqual(res.status_code, 200)
        assert b'<li >Gin, Now (order received:' in res.data

    def test_new_order_form_renders_choices(self):
        with app.test_request_context():
            new_order_page = url_for('get_new_order')
        res = self.app_client.get(new_order_page)
        self.assertEqual(res.status_code, 200)
        assert b'Gin & Tonic' in res.data
        assert b'Espresso Martini' in res.data
        assert b'Negroni' in res.data
        assert b'Beer' in res.data
        assert b'Other' in res.data

    def test_new_returns_201_on_success(self):
        data = {'drink': 'g&t', 'message': 'do nothing'}
        app.redis = RedisStub()
        with app.test_request_context():
            new = url_for('receive_new_order')
        res = self.app_client.post(new, data=data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data, b'Order created')

    def test_new_returns_400_on_no_drink_selection(self):
        with app.test_request_context():
            new = self.app_client.post('/new', data={'drink': ''})
        self.assertEqual(
            new.get_data(),
            b'Unable to process Entry: Something\'s wrong with your order, perhaps you meant to select "Other".',)
        self.assertEqual(new.status_code, 422)

    def test_live_orders_list_contains_Orders_header(self):
        with app.test_request_context():
            live_page = url_for('get_live_orders')
        res = self.app_client.get(live_page)
        self.assertEqual(res.status_code, 200)
        assert b'<h1>Orders:</h1>' in res.data

    def test_app_broadcasts_orders(self):
        broadcast(app.socketio, 'Gin & Tonic', 'Make it strong.')
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
        order = Order('Gin', 'Now')
        self.assertEqual(str(order)[:19], 'Order("Gin", "Now",')
        self.assertEqual(
            order.nicely_formatted[:25], 'Gin, Now (order received:')

    def test_Order_throws_up(self):
        self.assertRaises(ValueError, Order, 1, 'Now')
        self.assertRaises(ValueError, Order, 'Wine', 1)
        self.assertRaises(ValueError, Order, 'Whatever Liquor',
                          'Lots of it, Please', '2000-01-01')


    def test_empty_database_returns_empty_result(self):
        all_orders = Order.query.all()
        self.assertEqual(len(all_orders), 0)

    def test_save_order_saves_order(self):
        Order('Gin', 'Now').save_order(self.db)
        all_orders = Order.query.all()
        self.assertEqual(len(all_orders), 1)

    def test_make_as_json_makes_json(self):
        json = Order('Green Tea Mambo', 'You only live once').make_as_json
        assert '{"drink": "Green Tea Mambo",' in json
        assert 'Mambo", "message": "You only live once"' in json

    def test_get_orders_returns_list(self):
        with app.test_request_context():
            get_orders = url_for('get_orders')
        res = self.app_client.get(get_orders)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data), [])

    def test_get_orders_returns_data_list(self):
        Order(
            'Banana Milkshake',
            'No, I would not like to buy a subscription '
            'to your newsletter, thank you very much').save_order(self.db)
        with app.test_request_context():
            get_orders = url_for('get_orders')
        res = self.app_client.get(get_orders)
        self.assertEqual(res.status_code, 200)
        data_0 = json.loads(res.data)[0]
        self.assertEqual(data_0['drink'], 'Banana Milkshake')
        assert 'newsletter' in data_0['message']

    def test_get_order_returns_404(self):
        with app.test_request_context():
            get_orders = url_for('get_order', order_id=1)
        res = self.app_client.get(get_orders)
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data, b'No such record')

    def test_get_order_returns_422(self):
        with app.test_request_context():
            get_orders = url_for('get_order', order_id='Mango Juice')
        res = self.app_client.get(get_orders)
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.data, b'Error: order_id must be a number')

    def test_get_order_returns_200(self):
        Order(
            'Chiquita Sunrise',
            'I\m not entirely sure if this is a man\'s drink').save_order(self.db)
        with app.test_request_context():
            get_orders = url_for('get_order', order_id=1)
        res = self.app_client.get(get_orders)
        self.assertEqual(res.status_code, 200)
        data_0 = json.loads(res.data)[0]
        self.assertEqual(data_0['drink'], 'Chiquita Sunrise')
        assert 'entirely sure' in data_0['message']

    def test_consume_empty_queue_writes_none(self):
        redis = RedisStub(decode_responses = True)
        consume(RedisStub(), self.db, Order, queues = ['queue'])
        self.assertIsNone(Order.query.first())

    def test_consume_writes_data_to_db(self):
        redis = RedisStub(decode_responses = True)
        order = Order('Jack Daniels', 'Where is my order, Louise?')
        redis.rpush('queue', order.make_as_json)
        consume(RedisStub(), self.db, Order, queues = ['queue'])
        self.assertEqual(Order.query.first().drink, 'Jack Daniels')
        self.assertEqual(Order.query.first().message, 'Where is my order, Louise?')

    def test_get_redis_connection_returns_passed_connection(self):
        redis = get_redis_connection(attach_redis_connection = 'Fake Connection')
        self.assertEqual(redis, 'Fake Connection')

    def test_get_redis_connection_returns_redis_client(self):
        redis = get_redis_connection()
        redis_type = str(type(redis))
        self.assertEqual(redis_type, "<class 'redis.client.Redis'>")

    def test_simple_logger_logs_stuff(self):
        if not os.path.exists('TMP'):
            os.makedirs('TMP')
        logger = simple_logger('TMP/transact.log', 'input_log')
        logger.info('Test')
        with open('TMP/transact.log') as log:
            logged_data = log.read()
        os.remove('TMP/transact.log')
        os.removedirs('TMP')
        self.assertEqual( logged_data[-24:], 'input_log - INFO - Test\n')

    def test_prepare_demo_data_returns_data(self):
        data = json.loads(prepare_demo_data())
        daiquiri = data[2]
        drink = daiquiri.get('drink')
        message = daiquiri.get('message')
        self.assertEqual(drink, 'Strawberry Daiquiri')
        self.assertEqual(
            message,
            'Last time I had this was at a Bieber concert')

if __name__ == '__main__':
    unittest.main()
