import json

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# Database models:

class Order(db.Model):

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