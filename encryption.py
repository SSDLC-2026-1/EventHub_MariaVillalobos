"""
encryption.py

Laboratorio de Cifrado y Manejo de Credenciales

En este módulo deberás implementar:

- Descifrado AES (MODE_EAX)
- Hash de contraseña con salt usando PBKDF2-HMAC-SHA256
- Verificación de contraseña usando el mismo salt
- Funciones auxiliares para cifrar/descifrar datos sensibles

NO modificar la función encrypt_aes().
"""

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import hashlib
import os
import hmac
import base64

# Llave global para cifrado de datos sensibles
# En producción, esto debería venir de variables de entorno
ENCRYPTION_KEY = get_random_bytes(32)  # 256 bits


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


def encrypt_sensitive_data(data: str) -> dict:
    """
    Cifra datos sensibles usando AES-EAX con la llave global.
    
    Retorna un diccionario con:
        - encrypted_data: texto cifrado en hex
        - nonce: nonce usado en hex
        - tag: tag de autenticación en hex
    
    Si data es None o vacío, retorna None.
    """
    if not data:
        return None
    
    encrypted_hex, nonce_hex, tag_hex = encrypt_aes(data, ENCRYPTION_KEY)
    
    return {
        "encrypted_data": encrypted_hex,
        "nonce": nonce_hex,
        "tag": tag_hex
    }


def decrypt_sensitive_data(encrypted_dict: dict) -> str:
    """
    Descifra datos sensibles usando AES-EAX con la llave global.
    
    Args:
        encrypted_dict: Diccionario con encrypted_data, nonce y tag
    
    Returns:
        str: Datos descifrados o cadena vacía si hay error
    """
    if not encrypted_dict:
        return ""
    
    try:
        return decrypt_aes(
            encrypted_dict["encrypted_data"],
            encrypted_dict["nonce"],
            encrypted_dict["tag"],
            ENCRYPTION_KEY
        )
    except (ValueError, KeyError, TypeError, Exception) as e:
        print(f"Error al descifrar datos: {e}")
        return ""


def hash_password(password):
    """
    Genera un hash seguro usando:

        PBKDF2-HMAC-SHA256

    Requisitos:

    - Generar salt aleatoria de 16 bytes.
    - Usar al menos 200000 iteraciones.
    - Derivar clave de 32 bytes.
    - Retornar un diccionario con:

        {
            "algorithm": "pbkdf2_sha256",
            "iterations": ...,
            "salt": salt_en_hex,
            "hash": hash_en_hex
        }

    Pista:
        hashlib.pbkdf2_hmac(...)
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
    """
    Verifica una contraseña contra el hash almacenado.

    Debes:

    1. Extraer salt y iterations del diccionario.
    2. Convertir salt de hex a bytes.
    3. Recalcular el hash con la contraseña ingresada.
    4. Comparar usando hmac.compare_digest().
    5. Retornar True o False.

    stored_data tiene esta estructura:

        {
            "algorithm": "...",
            "iterations": ...,
            "salt": "...",
            "hash": "..."
        }
    """

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



if __name__ == "__main__":

    print("=== PRUEBA AES ===")

    texto = "Hola Mundo"
    clave = get_random_bytes(16)

    texto_cifrado, nonce, tag = encrypt_aes(texto, clave)

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
    
    print("\n=== PRUEBA CIFRADO DATOS SENSIBLES ===")
    
    email = "test@example.com"
    phone = "+1234567890"
    
    # Cifrar datos
    encrypted_email = encrypt_sensitive_data(email)
    encrypted_phone = encrypt_sensitive_data(phone)
    
    print("Email cifrado:", encrypted_email)
    print("Teléfono cifrado:", encrypted_phone)
    
    # Descifrar datos
    decrypted_email = decrypt_sensitive_data(encrypted_email)
    decrypted_phone = decrypt_sensitive_data(encrypted_phone)
    
    print("Email descifrado:", decrypted_email)
    print("Teléfono descifrado:", decrypted_phone)