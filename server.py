"""
Persist messages to a database server, while also pushing to live view
on html page in browser Utilizing Websockets, Redis and Flask.

Best enjoyed with a big, cold glass of anything.
"""

import json
import sys
import os

from flask import Flask, redirect, render_template, request
from flask_socketio import SocketIO

from app.consumer import consumer
from app.helpers import get_redis_connection, broadcast, simple_logger, CreateOrder
from app.members import db, Order, prepare_demo_data

def config_app():
    """Create app and set configuration.
    """
    if not os.path.exists('data'):
        os.makedirs('data')
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/transact_data.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    db.app = app
    app.db = db
    app.redis = get_redis_connection(decode_responses = True)
    app.socketio = SocketIO(app)
    return app

app = config_app()

# Orders API
@app.route('/api/v1/orders/', methods=['GET'])
def get_orders():
    """Get json of all orders"""
    all_orders = Order.query.all()
    as_dicts = [order.make_as_dict for order in all_orders]
    return json.dumps(as_dicts)

@app.route('/api/v1/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """Get json of single order by passing order_number"""
    try:
        order_id = int(order_id)
    except ValueError:
        return ('Error: order_id must be a number', 422)
    one_order = Order.query.filter(Order.order_id == order_id).first()
    if one_order is None:
        return ('No such record', 404)
    return one_order.make_as_json

@app.route('/api/v1/orders/', methods=['POST'])
def post_order(json_data):
    """Pass one or more orders as a json object"""
    handler = CreateOrder(app.redis)
    handler.perform(json_data)

@app.route('/new', methods=['POST'])
def receive_new_order():
    """Endpoind for ordering through web interface"""
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
            'Unable to process Entry: Something\'s wrong with '
            'your order, perhaps you meant to select "Other".',
            422)
    broadcast(app.socketio, drink, message)
    order = Order(drink, message)
    json_data = order.make_as_json
    post_order(json_data)
    return ('Order created', 201)

@app.route('/', methods=['GET'])
def get_index_page():
    """Redirect to the orders page"""
    return redirect('/orders', code=302)

@app.route('/orders', methods=['GET'])
def get_orders_page():
    """Render the orders page"""
    all_orders = Order.query.all()
    return render_template('/orders/index.html', orders = all_orders)

# Live orders page
@app.route('/live', methods=['GET'])
def get_live_orders():
    """Render live view of orders page"""
    return render_template('/orders/live-orders.html')

# Page: New order form
@app.route('/new', methods=['GET'])
def get_new_order():
    """Render page for posting new orders"""
    return render_template('orders/new-order.html')

if __name__ == '__main__':
    db.create_all()
    logger = simple_logger('transact.log', 'input_log')
    try:
        # If 'dbwriter' is passed as an argument, launch
        # the consumer, else launch the main app.
        # At least one of each is required.
        if 'dbwriter' in sys.argv:
            if len(Order.query.all()) == 0:
                print('Preparing demo data...')
                json_data = prepare_demo_data()
                post_order(json_data)
            consumer(app.redis, db, Order)
        else:
            app.socketio.run(app, host='0.0.0.0')
    except KeyboardInterrupt:
        logger.info('Server shut down by user')
