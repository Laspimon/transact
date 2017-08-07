import json
import logging

from datetime import datetime

from flask import Flask, redirect, render_template, request
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

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
        return json.dumps({
            'drink': self.drink,
            'message': self.message,
            'order_received': self.order_received.ctime()})

    def save_order(self, database):
        database.session.add(self)
        database.session.commit()

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

if __name__ == '__main__':
    db.create_all()
    try:
        socketio.run(app)
    except KeyboardInterrupt:
        logger.info('Server shut down by user')
        print ('Exiting.')
