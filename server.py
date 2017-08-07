import json
import logging
import sys

from datetime import datetime

from flask import Flask, redirect, render_template, request
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from redis import Redis

def get_redis_connection(decode_responses = False):
    return Redis(host='redis', decode_responses = decode_responses)

ctime_format = "%a %b %d %H:%M:%S %Y"

logger = logging.getLogger('input_log')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('transact.log')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/transact_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

socketio = SocketIO(app)
db = SQLAlchemy(app)

@app.route('/api/v1/orders/all', methods=['GET'])
def get_all_orders():
    all_orders = transform_orders_to_dicts(Order.query.all())
    return json.dumps(all_orders)

def transform_orders_to_dicts(list_of_orders):
    return [order.make_as_dict for order in list_of_orders]

@app.route('/api/v1/orders/all', methods=['POST'])
def put_orders_api(json_data):
    put_orders(json_data)

def put_orders(json_data):
    redis = get_redis_connection()
    redis.rpush('batch', json_data)

@app.route('/', methods=['GET'])
def index():
    return redirect('/orders', code=302)

@app.route('/orders', methods=['GET'])
def list_orders():
    all_orders = Order.query.all()
    return render_template('/orders/index.html', orders = all_orders)

@app.route('/new', methods=['GET'])
def new_order_form():
    return render_template('orders/new-order.html')

@app.route('/new', methods=['POST'])
def receive_order():
    message = request.form.get('message', '')
    drink = {
        'g&t': 'Gin & Tonic',
        'espresso-martini': 'Espresso Martini',
        'negroni': 'Negroni',
        'beer': 'Beer',
        'other': request.form.get('other')
    }.get(request.form.get('drink'))
    logger.info(str(drink) + ': ' + message)
    if drink is None:
        return (
            'Something\'s wrong with your order, '
            'perhaps you meant to select "Other".',
            400)
    Order(drink, message).make_a_note()
    return ('drink', 204)

@app.route('/live', methods=['GET'])
def live_orders_list():
    return render_template('/orders/live-orders.html')

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

    def save_order(self, database, commit=False):
        database.session.add(self)
        if commit: database.session.commit()

    def make_a_note(self):
        self.broadcast()
        self.put_in_queue()

    def broadcast(self):
        socketio.emit(
            'incomming',
            {
                'drink': self.drink,
                'message': self.message
            },
            broadcast=True
        )

    def put_in_queue(self):
        json = self.make_as_json
        if self.message == 'do nothing': return
        redis = get_redis_connection()
        redis.rpush('queue', json)

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
    dummy_data = transform_orders_to_dicts(Order(*_) for _ in (
        ('Negroni', 'If you bring it here fast, I\'ll sing you a song.'),
        ('Espresso Martini', 'Hurry up, I\'m thirsty!'),
        ('Strawberry Daiquiri', 'Last time I had this was at a Bieber concert'),
        ('Magic Potion', 'Ya wouldn\'t happen to have any tiramisu, would ya?'),
        ('Injection attack', '<script> a = function(){ return "DROP TABLE Users or whatever"}</script>'),
        ('Rosy Martini', 'Shaken not stirred')))
    json_data = json.dumps(dummy_data)
    put_orders(json_data)

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
