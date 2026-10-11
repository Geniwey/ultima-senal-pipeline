import os
import sys
import time
import base64
import requests
import re
import pytesseract
from PIL import Image

ESTILO_BASE = (
    "cinematic lighting, highly detailed 3D render, dark atmospheric background, "
    "Unreal Engine 5 style, pristine empty environment, pure visual art, blank surfaces"
)

PALABRAS_A_EVITAR = [
    "text", "words", "letters", "labels", "numbers", "diagram", "infographic", 
    "person", "face", "sign", "document", "panel", "dashboard", "hud", "screen"
]

def _limpiar_prompt(prompt: str) -> str:
    # Solución al bug: Usar Regex con \b (boundaries) para borrar la palabra exacta, sin distinguir mayúsculas
    p = prompt
    for palabra in PALABRAS_A_EVITAR:
        p = re.sub(rf'\b{palabra}\b', '', p, flags=re.IGNORECASE)
    # Evitar dobles espacios y negaciones implícitas
    p = p.replace(" no ", " ").replace(" without ", " ")
    return re.sub(r'\s+', ' ', p).strip()

def _contiene_texto_alienigena(ruta_imagen: str) -> bool:
    try:
        texto = pytesseract.image_to_string(Image.open(ruta_imagen))
        # Si detecta más de 4 caracteres alfanuméricos seguidos, la IA ha contaminado la imagen
        letras_detectadas = re.sub(r'[^A-Za-z0-9]', '', texto)
        return len(letras_detectadas) > 4
    except Exception as e:
        print(f"Aviso OCR: {e}")
        return False

def _intentar_cloudflare(prompt_completo: str, ruta_salida: str) -> bool:
    account_id = os.environ.get("CF_ACCOUNT_ID")
    api_token = os.environ.get("CF_API_TOKEN")
    if not account_id or not api_token: return False
    
    headers = {"Authorization": f"Bearer {api_token}"}
    modelos_cf = [
        "@cf/black-forest-labs/flux-1-schnell",
        "@cf/stabilityai/stable-diffusion-xl-base-1.0"
    ]
    
    for modelo in modelos_cf:
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{modelo}"
        try:
            # Control de Rate Limit estricto: Pausa ANTES de pedir
            time.sleep(4)
            resp = requests.post(url, headers=headers, json={"prompt": prompt_completo}, timeout=40)
            
            if resp.status_code == 200:
                # Soporte para binario (SDXL) o JSON base64 (Flux)
                content_type = resp.headers.get("Content-Type", "")
                if "image/" in content_type:
                    with open(ruta_salida, "wb") as f: f.write(resp.content)
                else:
                    b64_img = resp.json().get("result", {}).get("image")
                    if b64_img:
                        with open(ruta_salida, "wb") as f: f.write(base64.b64decode(b64_img))
                
                # Validación visual y OCR
                if os.path.exists(ruta_salida) and os.path.getsize(ruta_salida) > 10000:
                    if _contiene_texto_alienigena(ruta_salida):
                        print(f" ⚠️ [OCR] Texto alienígena detectado. Descartando imagen...")
                        os.remove(ruta_salida)
                        continue # Prueba el siguiente modelo
                    return True
            else:
                print(f"Error CF {modelo}: {resp.status_code}")
        except requests.RequestException as e:
            print(f"Fallo conexión CF: {e}")
    return False

def generar_imagen(prompt_escena: str, ruta_salida: str) -> bool:
    sujeto = _limpiar_prompt(prompt_escena)
    prompt_completo = f"{sujeto}, {ESTILO_BASE}"
    
    # 2 intentos de alta calidad
    for intento in range(2):
        print(f"  Intento visual {intento+1}/2...")
        if _intentar_cloudflare(prompt_completo, ruta_salida):
            return True
            
    print("  [ERROR] Fallaron todos los modelos visuales para esta escena.")
    return False

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(0 if generar_imagen(sys.argv[1], sys.argv[2]) else 1)
