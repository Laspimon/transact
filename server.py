import json
import logging
import sys
import os

from datetime import datetime

from flask import Flask, redirect, render_template, request, views
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from redis import Redis

def get_redis_connection(decode_responses = False):
    if 'docker' in sys.argv:
        return Redis(host='redis', decode_responses = decode_responses)
    return Redis(decode_responses = decode_responses)

ctime_format = "%a %b %d %H:%M:%S %Y"

logger = logging.getLogger('input_log')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('transact.log')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

app = Flask(__name__)

if not os.path.exists('data'):
    os.makedirs('data')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/transact_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

socketio = SocketIO(app)
db = SQLAlchemy(app)

# Orders API
@app.route('/api/v1/orders/')
def get_orders(order_id = None, methods=['GET']):
    all_orders = Order.query.all()
    as_dicts = [order.make_as_dict for order in all_orders]
    return json.dumps(all_orders)

@app.route('/api/v1/orders/<order_id>', defaults={'order_id': None}, methods=['GET'])
def get_order(order_id = None):
    raise NotImplementedError

@app.route('/api/v1/orders/', methods=['POST'])
def post_order(json_data):
    redis = get_redis_connection()
    redis.rpush('batch', json_data)

# Page: New order form
@app.route('/new', methods=['GET'])
def get_new_order():
    return render_template('orders/new-order.html')

@app.route('/new', methods=['POST'])
def post_new_order():
    message = request.form.get('message', '')
    drink = {
        'g&t': 'Gin & Tonic',
        'espresso-martini': 'Espresso Martini',
        'negroni': 'Negroni',
        'beer': 'Beer',
        'other': request.form.get('other')
    }.get(request.form.get('drink'))
    if drink is None:
        return (
            'Something\'s wrong with your order, '
            'perhaps you meant to select "Other".',
            400)
    order = Order(drink, message)
    broadcast(order)
    put_in_queue(order)
    return ('drink', 204)

@app.route('/', methods=['GET'])
def get_index_page():
    return redirect('/orders', code=302)

@app.route('/orders', methods=['GET'])
def get_orders_page():
    all_orders = Order.query.all()
    return render_template('/orders/index.html', orders = all_orders)

@app.route('/live', methods=['GET'])
def get_live_orders():
    return render_template('/orders/live-orders.html')

def broadcast(order):
    socketio.emit(
        'incomming',
        {
            'drink': order.drink,
            'message': order.message
        },
        broadcast=True
    )

def put_in_queue(order):
    json = order.make_as_json
    redis = get_redis_connection()
    redis.rpush('queue', json)

class Order(db.Model):

    pid = db.Column(db.Integer, primary_key = True)
    drink = db.Column(db.String(64), nullable = False)
    message = db.Column(db.String(256), nullable = False)
    order_received = db.Column(db.DateTime)

    def __init__(self, drink, message, order_received = None):
        if order_received is None:
            order_received = datetime.now()
        if not isinstance(order_received, datetime):
            try:
                order_received = datetime.strptime(order_received, ctime_format)
            except ValueError:
                raise ValueError('order_received must be datetime instance')
        if False in (isinstance(drink, str), isinstance(message, str)):
            raise ValueError('drink and message must be strings')
        self.order_received = order_received
        self.drink = drink
        self.message = message

    def save_order(self, database, commit=False):
        database.session.add(self)
        if commit: database.session.commit()

    def __repr__(self):
        return 'Order("{}", "{}", "{}")'.format(
            self.drink, self.message, self.order_received)

    @property
    def nicely_formatted(self):
        return '{}, {} (order received: {})'.format(
            self.drink, self.message, self.order_received.ctime())

    @property
    def make_as_json(self):
        return json.dumps(self.make_as_dict)

    @property
    def make_as_dict(self):
        return {
            'drink': self.drink,
            'message': self.message,
            'order_received': self.order_received.ctime()}

def consumer():
    redis = get_redis_connection(decode_responses = True)
    while True:
        source, orders = redis.blpop(['queue', 'batch'])
        if source == 'queue':
            order = json.loads(orders)
            Order(**order).save_order(db)
        if source == 'batch':
            for order in json.loads(orders):
                Order(**order).save_order(db, commit = False)
            db.session.commit()

def prepare_demo_data():
    api = OrdersAPI()
    dummy_data = api.transform_orders_to_dicts(Order(*_) for _ in (
        ('Negroni', 'If you bring it here fast, I\'ll sing you a song.'),
        ('Espresso Martini', 'Hurry up, I\'m thirsty!'),
        ('Strawberry Daiquiri', 'Last time I had this was at a Bieber concert'),
        ('Magic Potion', 'Ya wouldn\'t happen to have any tiramisu, would ya?'),
        ('Injection attack', '<script> a = function(){ return "DROP TABLE Users or whatever"}</script>'),
        ('Rosy Martini', 'Shaken not stirred')))
    json_data = json.dumps(dummy_data)
    api.put_orders(json_data)

if __name__ == '__main__':
    db.create_all()
    try:
        if 'dbwriter' in sys.argv:
            consumer()
        else:
            prepare_demo_data()
            socketio.run(app, host='0.0.0.0')
    except KeyboardInterrupt:
        logger.info('Server shut down by user')
