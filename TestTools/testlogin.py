from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

BASE_URL = "http://127.0.0.1:5000"

EMAIL = "noadmin@eventhub.com"
PASSWORD = "Admin123!"

driver = webdriver.Chrome()
wait = WebDriverWait(driver, 10)

try:
    # 1. Abrir página de login
    driver.get(f"{BASE_URL}/login")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="login-form"]')))
    time.sleep(2)

    # 2. Llenar credenciales
    driver.find_element(By.CSS_SELECTOR, '[data-testid="login-email"]').send_keys(EMAIL)
    driver.find_element(By.CSS_SELECTOR, '[data-testid="login-password"]').send_keys(PASSWORD)
    time.sleep(2)

    # 3. Enviar formulario
    driver.find_element(By.CSS_SELECTOR, '[data-testid="login-submit"]').click()

    # 4. Validar dashboard
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="dashboard-title"]')))
    time.sleep(3)

    titulo = driver.find_element(By.CSS_SELECTOR, '[data-testid="dashboard-title"]').text
    print("Título encontrado:", titulo)

    assert "Welcome" in titulo, "No se encontró el mensaje esperado en el dashboard"
    print("Prueba exitosa: login correcto.")

finally:
    driver.quit()