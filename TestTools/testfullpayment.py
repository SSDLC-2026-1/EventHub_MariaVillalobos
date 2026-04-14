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
    # 1. Login
    driver.get(f"{BASE_URL}/login")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="login-form"]')))

    driver.find_element(By.CSS_SELECTOR, '[data-testid="login-email"]').send_keys(EMAIL)
    driver.find_element(By.CSS_SELECTOR, '[data-testid="login-password"]').send_keys(PASSWORD)
    time.sleep(2)

    driver.find_element(By.CSS_SELECTOR, '[data-testid="login-submit"]').click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="dashboard-title"]')))
    print("Login exitoso")
    time.sleep(2)

    # 2. Ir directo a un evento
    driver.get(f"{BASE_URL}/event/1")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="event-title"]')))
    print("Detalle del evento cargado")
    time.sleep(2)

    # 3. Comprar 1 boleta
    qty_input = driver.find_element(By.CSS_SELECTOR, '[data-testid="ticket-qty"]')
    qty_input.clear()
    qty_input.send_keys("1")
    time.sleep(1)

    driver.find_element(By.CSS_SELECTOR, '[data-testid="buy-ticket-submit"]').click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="checkout-form"]')))
    print("Checkout cargado")
    time.sleep(2)

    # 4. Llenar formulario de pago
    driver.find_element(By.CSS_SELECTOR, '[data-testid="checkout-card-number"]').send_keys("4111111111111111")
    driver.find_element(By.CSS_SELECTOR, '[data-testid="checkout-exp-date"]').send_keys("12/30")
    driver.find_element(By.CSS_SELECTOR, '[data-testid="checkout-cvv"]').send_keys("123")
    driver.find_element(By.CSS_SELECTOR, '[data-testid="checkout-name-on-card"]').send_keys("Ana Gomez")
    driver.find_element(By.CSS_SELECTOR, '[data-testid="checkout-billing-email"]').send_keys(EMAIL)
    time.sleep(2)

    # 5. Enviar pago
    driver.find_element(By.CSS_SELECTOR, '[data-testid="checkout-submit"]').click()

    # 6. Validar dashboard / compra exitosa
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="dashboard-page"]')))
    time.sleep(2)

    success_banner = driver.find_elements(By.CSS_SELECTOR, '[data-testid="payment-success-banner"]')
    tickets_table = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tickets-table"]')

    assert success_banner or tickets_table, "No se encontró evidencia visual de compra exitosa"

    print("Prueba exitosa: compra realizada correctamente.")

finally:
    driver.quit()