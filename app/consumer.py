import json

def consumer(redis, database, model_class, queues = None):
    if queues is None:
        queues = ['queue']
    while True:
        source, orders = redis.blpop(queues)
        for order in json.loads(orders):
            model_class(**order).save_order(database, commit = False)
        database.session.commit()