from flask import Flask, redirect, render_template

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return redirect('/messages', code=302)

@app.route('/messages', methods=['GET'])
def list_messages():
    return render_template('/messages/index.html')

if __name__ == '__main__':
    app.run()
