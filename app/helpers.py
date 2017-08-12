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

def get_redis_connection(decode_responses = False, attach_redis_connection = None):
    if attach_redis_connection is not None:
        return attach_redis_connection
    if 'docker' in sys.argv:
        return Redis(host='redis', decode_responses = decode_responses)
    return Redis(decode_responses = decode_responses)

def simple_logger():
    logger = logging.getLogger('input_log')
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler('transact.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger