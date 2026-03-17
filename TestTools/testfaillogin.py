from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

BASE_URL = "http://127.0.0.1:5000"

EMAIL = "noadmin@eventhub.com"
WRONG_PASSWORD = "ClaveIncorrecta123!"

driver = webdriver.Chrome()
wait = WebDriverWait(driver, 10)

try:
    # 1. Abrir login
    driver.get(f"{BASE_URL}/login")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="login-form"]')))
    time.sleep(2)

    # 2. Llenar credenciales inválidas
    driver.find_element(By.CSS_SELECTOR, '[data-testid="login-email"]').send_keys(EMAIL)
    driver.find_element(By.CSS_SELECTOR, '[data-testid="login-password"]').send_keys(WRONG_PASSWORD)
    time.sleep(2)

    # 3. Enviar formulario
    driver.find_element(By.CSS_SELECTOR, '[data-testid="login-submit"]').click()

    # 4. Validar mensaje de error
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="login-error-banner"]')))
    time.sleep(3)

    error_text = driver.find_element(By.CSS_SELECTOR, '[data-testid="login-error-banner"]').text
    print("Mensaje encontrado:", error_text)

    assert "Invalid" in error_text or "incorrect" in error_text.lower(), "No se encontró el mensaje esperado de error"
    print("Prueba exitosa: login no feliz validado correctamente.")

finally:
    driver.quit()