# transact
Persist messages to a database server, while also pushing to live view on html page in browser
Utilizing Websockets, Redis and Flask.
Best enjoyed with a big, cold glass of anything.

## To install:

```
git clone https://github.com/Laspimon/transact.git
cd transact
pip install -r requirements.txt
```

## Trying it out:
To run tests:

```
python -m unittest discover tests
```

For code coverage:
```
coverage run --source . tests/test_app.py
coverage html
coverage report
```

To run the server, run docker-compose:
```
docker-compose up --build
```

Alternatively, execute the following commands in separate terminal windows::
```
python server.py
python server.py dbwriter
```

User interface is implemented at the following adresses:
```
List of all orders: http://0.0.0.0:5000/orders
Live updating list of orders: http://0.0.0.0:5000/live
Form for sending new orders: http://0.0.0.0:5000/new
```

An API available for POST and GET of order batches in json format. Query the following end point:
```
http://0.0.0.0:5000/api/v1/orders/
http://0.0.0.0:5000/api/v1/orders/<order_id>
```

Data format accepted is as follows:
```
{
    'drink': '{String: Name of your favourite cocktail}',
    'message': '{String: If you have a message you'd like to relay to the bar}',
    'order_received': '(Optional) String: A timestamp in the following form {%a %b %d %H:%M:%S %Y}'
}
```

## Future work
The application could be improved in several ways:

1. First off, the database is currently hard-coded to a sqlite file. We should look at other options.
2. If we are focusing on the front end, we might want to do some sanitation of the output from the database.
3. We could do more extensive logging of orders.