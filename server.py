import json
import sys
import os

from flask import Flask, redirect, render_template, request, views
from flask_socketio import SocketIO

from app.members import db, Order, prepare_demo_data
from app.helpers import get_redis_connection, broadcast, simple_logger, CreateOrder
from app.consumer import consumer

def config_app():
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
    all_orders = Order.query.all()
    as_dicts = [order.make_as_dict for order in all_orders]
    return json.dumps(as_dicts)

@app.route('/api/v1/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    try:
        order_id = int(order_id)
    except ValueError:
        return 'Error: order_id must be a number'
    one_order = Order.query.filter(Order.order_id == order_id).first()
    if one_order is None:
        return 'Error: No such record'
    return one_order.make_as_json

@app.route('/api/v1/orders/', methods=['POST'])
def post_order(json_data):
    handler = CreateOrder(app.redis)
    handler.perform(json_data)

@app.route('/new', methods=['POST'])
def receive_new_order():
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

## Pages renderers

# Index page
@app.route('/', methods=['GET'])
def get_index_page():
    return redirect('/orders', code=302)

@app.route('/orders', methods=['GET'])
def get_orders_page():
    all_orders = Order.query.all()
    return render_template('/orders/index.html', orders = all_orders)

# Live orders page
@app.route('/live', methods=['GET'])
def get_live_orders():
    return render_template('/orders/live-orders.html')

# Page: New order form
@app.route('/new', methods=['GET'])
def get_new_order():
    return render_template('orders/new-order.html')

if __name__ == '__main__':
    db.create_all()
    logger = simple_logger()
    try:
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
