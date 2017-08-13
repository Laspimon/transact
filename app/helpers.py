"""
Helper functions for placing orders
"""
import logging
import sys
from redis import Redis

def broadcast(socketio, drink, message):
    """Broadcast orders through SocketIO connection"""
    socketio.emit(
        'incomming',
        {
            'drink': drink,
            'message': message
        },
        broadcast=True
    )

class CreateOrder():
    """Class for creating orders"""
    def __init__(self, redis):
        """Reversal of control"""
        self.redis = redis

    def perform(self, json_data):
        """Push order to Redis"""
        self.redis.rpush('queue', json_data)

def get_redis_connection(decode_responses = False, attach_redis_connection = None):
    """Get Redis connection, or attach existing connection"""
    if attach_redis_connection is not None:
        return attach_redis_connection
    if 'docker' in sys.argv:
        return Redis(host='redis', decode_responses = decode_responses)
    return Redis(decode_responses = decode_responses)

def simple_logger(logfile, logname):
    """Setup simple logger"""
    logger = logging.getLogger(logname)
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(logfile)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger