"""
encryption.py

Laboratorio de Cifrado y Manejo de Credenciales

En este módulo deberás implementar:

- Descifrado AES (MODE_EAX)
- Hash de contraseña con salt usando PBKDF2-HMAC-SHA256
- Verificación de contraseña usando el mismo salt

NO modificar la función encrypt_aes().
"""

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import hashlib
import hmac

import secrets
import base64
import hashlib
# ==========================================================
# AES-GCM (requiere pip install pycryptodome)
# ==========================================================

def encrypt_aes(texto, clave):
    """
    Cifra un texto usando AES en modo EAX.

    Retorna:
        texto_cifrado_hex
        nonce_hex
        tag_hex
    """

    texto_bytes = texto.encode()

    cipher = AES.new(clave, AES.MODE_EAX)

    nonce = cipher.nonce
    texto_cifrado, tag = cipher.encrypt_and_digest(texto_bytes)

    return (
        texto_cifrado.hex(),
        nonce.hex(),
        tag.hex()
    )




def decrypt_aes(texto_cifrado_hex, nonce_hex, tag_hex, clave):
    """
    Descifra texto cifrado con AES-EAX.

    Debes:

    1. Convertir texto_cifrado_hex, nonce_hex y tag_hex a bytes.
    2. Crear el objeto AES usando:
           AES.new(clave, AES.MODE_EAX, nonce=nonce)
    3. Usar decrypt_and_verify() para validar integridad.
    4. Retornar el texto descifrado como string.
    """

    # TODO: Implementar conversión de hex a bytes
    texto_cifrado_bytes = bytes.fromhex(texto_cifrado_hex)
    nonce_bytes = bytes.fromhex(nonce_hex)
    tag_bytes = bytes.fromhex(tag_hex)

    # TODO: Crear objeto AES con nonce
    cipher = AES.new(clave, AES.MODE_EAX, nonce=nonce_bytes)

    # TODO: Usar decrypt_and_verify
    texto_descifrado_bytes = cipher.decrypt_and_verify(texto_cifrado_bytes, tag_bytes)

    # TODO: Convertir resultado a string y retornar
    return texto_descifrado_bytes.decode('utf-8')
def decrypt_aes(texto_cifrado_str, nonce_hex, tag_hex, clave):
    texto_cifrado = bytes.fromhex(texto_cifrado_str)
    nonce = bytes.fromhex(nonce_hex)
    tag = bytes.fromhex(tag_hex)

    cipher = AES.new(clave, AES.MODE_EAX, nonce=nonce)

    texto_descifrado = cipher.decrypt_and_verify(texto_cifrado, tag)

    return texto_descifrado.decode()

# ==========================================================
# PASSWORD HASHING (PBKDF2 - SHA256)
# ==========================================================


DEFAULT_ITERATIONS = 310_000
SALT_BYTES = 16


def hash_password(password: str) -> dict:
    """

    # TODO: Generar salt aleatoria
    salt = os.urandom(16)  # También podrías usar get_random_bytes(16)
    
    # TODO: Derivar clave usando pbkdf2_hmac
    iterations = 200000
    key_length = 32
    
    # Convertir la contraseña a bytes y derivar la clave
    password_bytes = password.encode('utf-8')
    key = hashlib.pbkdf2_hmac('sha256', password_bytes, salt, iterations, dklen=key_length)
    
    # TODO: Retornar diccionario con salt y hash en formato hex
    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": iterations,
        "salt": salt.hex(),
        "hash": key.hex()
    }



def verify_password(password, stored_data):
    Genera un hash seguro usando PBKDF2-HMAC-SHA256.
    Retorna un diccionario listo para guardar en JSON.
    """
    salt = secrets.token_bytes(SALT_BYTES)

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        DEFAULT_ITERATIONS,
        dklen=32
    )

    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": DEFAULT_ITERATIONS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "hash": base64.b64encode(derived_key).decode("ascii")
    }


def verify_password(password: str, stored: dict) -> bool:
    """
    Verifica si una contraseña coincide con el hash almacenado.
    Usa comparación constante.
    """
    salt = base64.b64decode(stored["salt"])
    expected_hash = base64.b64decode(stored["hash"])

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        int(stored["iterations"]),
        dklen=len(expected_hash)
    )

    # TODO: Extraer salt e iterations
    salt_hex = stored_data.get("salt")
    iterations = stored_data.get("iterations")
    original_hash_hex = stored_data.get("hash")
    
    # Convertir salt de hex a bytes
    salt_bytes = bytes.fromhex(salt_hex)
    
    # TODO: Recalcular hash
    password_bytes = password.encode('utf-8')
    key_length = 32  # Debería coincidir con el usado en hash_password
    
    recalculated_key = hashlib.pbkdf2_hmac(
        'sha256', 
        password_bytes, 
        salt_bytes, 
        iterations, 
        dklen=key_length
    )
    
    # Convertir el hash original de hex a bytes
    original_hash_bytes = bytes.fromhex(original_hash_hex)
    
    # TODO: Comparar con compare_digest
    return hmac.compare_digest(recalculated_key, original_hash_bytes)
    return hmac.compare_digest(derived_key, expected_hash)



if __name__ == "__main__":

    print("=== PRUEBA AES ===")

    texto = "Hola Mundo"
    clave = get_random_bytes(16)

    texto_cifrado, nonce, tag = encrypt_aes(texto, clave)
    print("Texto plano: ", texto)
    print("Texto cifrado:", texto_cifrado)
    print("Nonce:", nonce)
    print("Tag:", tag)

    # Cuando implementen decrypt_aes, esto debe funcionar
    texto_descifrado = decrypt_aes(texto_cifrado, nonce, tag, clave)
    print("Texto descifrado:", texto_descifrado)


    print("\n=== PRUEBA HASH ===")

    password = "Password123!"

    # Cuando implementen hash_password:
    pwd_data = hash_password(password)
    print("Hash generado:", pwd_data)

    # Cuando implementen verify_password:
    print("Verificación correcta:",
          verify_password("Password123!", pwd_data))
    print("Verificación incorrecta:",
          verify_password("WrongPassword", pwd_data))
          verify_password("Password123!", pwd_data))
