import logging
import sys
from redis import Redis

def broadcast(socketio, drink, message):
    socketio.emit(
        'incomming',
        {
            'drink': drink,
            'message': message
        },
        broadcast=True
    )

class CreateOrder():
    def __init__(self, redis):
        self.redis = redis

    def perform(self, json_data):
        self.redis.rpush('queue', json_data)

def get_redis_connection(decode_responses = False, attach_redis_connection = None):
    if attach_redis_connection is not None:
        return attach_redis_connection
    if 'docker' in sys.argv:
        return Redis(host='redis', decode_responses = decode_responses)
    return Redis(decode_responses = decode_responses)

def simple_logger(logfile, logname):
    logger = logging.getLogger(logname)
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(logfile)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger