import logging

from flask import Flask, redirect, render_template, request

logger = logging.getLogger('input_log')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('transact.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return redirect('/messages', code=302)

@app.route('/messages', methods=['GET'])
def list_messages():
    return render_template('/messages/index.html')

@app.route('/new', methods=['GET'])
def new_order_form():
    return render_template('messages/new-order.html')

@app.route('/new', methods=['POST'])
def receive_message():
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
    #save_massage()
    #broadcast_message()
    return ('drink', 204)

if __name__ == '__main__':
    app.run()
