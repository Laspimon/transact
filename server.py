import logging

from flask import Flask, redirect, render_template, request
from flask_socketio import SocketIO

logger = logging.getLogger('input_log')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('transact.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

app = Flask(__name__)
socketio = SocketIO(app)

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
    #save_order()
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

if __name__ == '__main__':
    socketio.run(app)
