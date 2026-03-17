from flask import Flask, request, jsonify
from routes.index import index_blueprint

app = Flask(__name__)

app.register_blueprint(index_blueprint, url_prefix='/')

if __name__ == '__main__':
    app.run(debug=True,port=3000)