# transact
Persist messages to a database server, while also pushing to live view on html page in browser

To install:

```
pip install -r requirements.txt
```

To run tests:

```
python -m unittest discover tests
```

To run the server, execute the following commands in separate terminal windows::
```
python server.py
python server.py dbwriter
```

Alternatively run docker-compose:
```
docker-compose up --build
```

User interface is implemented at the following adresses:
```
List of all orders: http://0.0.0.0:5000/orders
Live updating list of orders: http://0.0.0.0:5000/live
Form for sending new orders: http://0.0.0.0:5000/new
```

An API available for POST and GET of order batches in json format. Query the following end point:
```
/api/v1/orders/all
```

Data format accepted is as follows:
```
{
    'drink': '{String: Name of your favourite cocktail}',
    'message': '{String: If you have a message you'd like to relay to the bar}',
    'order_received': '(Optional) String: A timestamp in the following form {%a %b %d %H:%M:%S %Y}'
}
```
