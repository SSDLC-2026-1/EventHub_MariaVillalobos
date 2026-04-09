from flask import Blueprint, redirect, request, jsonify
import json
import os

index_blueprint = Blueprint('index', __name__)


USERS_FILE = "users.json"



@index_blueprint.route('/', methods=["GET"])
def index():
    return "Hola Mundo"


@index_blueprint.route('/users', methods=["GET"])
def users():
    users = {
        'id':1, 'nombre': 'Juan',
        'id':2, 'nombre': 'Maria'
    }
    return jsonify(users)

@index_blueprint.route('/data', methods=["POST"])
def data():
    data = request.json
    return jsonify({
        'message':"datos recibidos",
        "data": data
    })


HTTP_STATUS_INFO = {
    200: "OK",
    201: "Created",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    429: "Too Many Requests",
    500: "Internal Server Error"
}



@index_blueprint.route("/cat-status/<int:code>", methods=["GET"])
def cat_status(code):
    if code not in HTTP_STATUS_INFO:
        return jsonify({
            "error": "Código HTTP no soportado",
            "supported_codes": list(HTTP_STATUS_INFO.keys())
        }), 400

    return redirect(f"https://http.cat/{code}")
