import json

def consumer(redis, database, model_class, queues = None):
    if queues is None:
        queues = ['queue']
    while True:
        consume(redis, database, model_class, queues)

def consume(redis, database, model_class, queues):
    popped = redis.blpop(queues)
    if popped is None:
        return
    source, orders = popped
    for order in json.loads(orders):
        model_class(**order).save_order(database, commit = False)
    database.session.commit()