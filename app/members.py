"""
Defines the database models
"""
import json

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Order(db.Model):
    """ORM object for the orders.

    Takes drink, message and optional time of order.
    order_id is automatically assigned.
    Running eval on the output of __repr__() initializes
    a new copy of the original object.
    """

    order_id = db.Column(db.Integer, primary_key = True)
    drink = db.Column(db.String(64), nullable = False)
    message = db.Column(db.String(256), nullable = False)
    order_received = db.Column(db.DateTime)

    ctime_format = "%a %b %d %H:%M:%S %Y"

    def __init__(self, drink, message, order_received = None):
        if order_received is None:
            order_received = datetime.now()
        if not isinstance(order_received, datetime):
            try:
                order_received = datetime.strptime(order_received, self.ctime_format)
            except ValueError:
                raise ValueError('order_received must be datetime instance')
        if False in (isinstance(drink, str), isinstance(message, str)):
            raise ValueError('drink and message must be strings')
        self.order_received = order_received
        self.drink = drink
        self.message = message

    def save_order(self, database, commit=True):
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
        return json.dumps([self.make_as_dict])

    @property
    def make_as_dict(self):
        return {
            'drink': self.drink,
            'message': self.message,
            'order_received': self.order_received.ctime()}

def prepare_demo_data():
    """Prepare demo data and return it as json

    Now it wont feel so lonely, when we launch the app.
    """
    dummy_orders = [Order(*_) for _ in (
        ('Negroni', 'If you bring it here fast, I\'ll sing you a song.'),
        ('Espresso Martini', 'Hurry up, I\'m thirsty!'),
        ('Strawberry Daiquiri', 'Last time I had this was at a Bieber concert'),
        ('Magic Potion', 'Ya wouldn\'t happen to have any tiramisu, would ya?'),
        ('Injection attack', '<script> a = function(){ return "DROP TABLE Users or whatever"}</script>'),
        ('Rosy Martini', 'Shaken not stirred'))]
    dummy_data = [order.make_as_dict for order in dummy_orders]
    json_data = json.dumps(dummy_data)
    return json_data
