import logging

from datetime import datetime

from flask import Flask, redirect, render_template, request
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger('input_log')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('transact.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    return render_template('/orders/index.html')

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
    save_order(drink, message)
    broadcast_message(drink, message)
    return ('drink', 204)

@app.route('/live', methods=['GET'])
def live_orders_list():
    return render_template('/orders/live-orders.html')

def broadcast_message(drink, message):
    socketio.emit(
        'incomming',
        {
            'drink': drink,
            'message': message
        },
        broadcast=True
    )

def save_order(drink, message):
    order = Order(drink, message)
    db.session.add(order)
    db.session.commit()

class Order(db.Model):

    pid = db.Column(db.Integer, primary_key = True)
    drink = db.Column(db.String(64), nullable = False)
    message = db.Column(db.String(256), nullable = False)
    order_received = db.Column(db.DateTime)

    def __init__(self, drink, message, order_received = None):
        if order_received is None:
            order_received = datetime.now()
        if not isinstance(order_received, datetime):
            raise ValueError('order_received must by datetime instance')
        if False in (isinstance(drink, str), isinstance(message, str)):
            raise ValueError('drink and message must by strings')
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

if __name__ == '__main__':
    db.create_all()
    try:
        socketio.run(app)
    except KeyboardInterrupt:
        logger.info('Server shut down by user')
        print ('Exiting.')
