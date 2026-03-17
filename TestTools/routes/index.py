from flask import Blueprint, redirect, request, jsonify
import json
import os

index_blueprint = Blueprint('index', __name__)


USERS_FILE = "users.json"


def inicializar_archivo():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)


def leer_usuarios():
    inicializar_archivo()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_usuarios(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)


@index_blueprint.route('/', methods=["GET"])
def index():
    return "Hola Mundo"


@index_blueprint.route('/users', methods=["GET"])
def users():
    users = leer_usuarios()
    return jsonify(users), 200


@index_blueprint.route('/users', methods=["POST"])
def crear_usuario():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No se enviaron datos en formato JSON"}), 400

    nombre = data.get("nombre")

    if not nombre:
        return jsonify({"error": "El campo 'nombre' es obligatorio"}), 400

    users = leer_usuarios()

    nuevo_id = 1
    if users:
        nuevo_id = max(user["id"] for user in users) + 1

    nuevo_usuario = {
        "id": nuevo_id,
        "nombre": nombre
    }

    users.append(nuevo_usuario)
    guardar_usuarios(users)

    return jsonify({
        "message": "Usuario creado correctamente",
        "user": nuevo_usuario
    }), 201


@index_blueprint.route('/users/<int:user_id>', methods=["GET"])
def get_user(user_id):
    users = leer_usuarios()

    usuario = next((user for user in users if user["id"] == user_id), None)

    if not usuario:
        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    return jsonify(usuario), 200


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