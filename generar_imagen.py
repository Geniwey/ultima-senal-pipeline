import os
import sys
import time
import base64
import requests
import urllib.parse

ESTILO_BASE = (
    "abstract glowing neon wireframe 3D render, HUD interface, digital telemetry visualization, "
    "dark mode background with bright cyan and orange glowing lines, pure geometry, "
    "highly detailed tech aesthetic, NO TEXT, ZERO WORDS, NO LABELS, NO LETTERS, empty interface"
)

PALABRAS_A_EVITAR = ["photo", "realistic", "person", "face", "hands", "text", "words", "letters", "labels"]

def _limpiar_prompt(prompt: str) -> str:
    prompt_limpio = prompt
    for palabra in PALABRAS_A_EVITAR: prompt_limpio = prompt_limpio.replace(palabra, "")
    return prompt_limpio.strip()

TIMEOUT = 30
TAMANO_MINIMO_BYTES = 10_000
_cloudflare_agotado = [False]
_ultima_fue_emergencia = [False]

def _validar_imagen(ruta: str) -> bool:
    if not os.path.exists(ruta): return False
    if os.path.getsize(ruta) < TAMANO_MINIMO_BYTES: return False
    with open(ruta, "rb") as f: cabecera = f.read(8)
    return cabecera.startswith(b"\x89PNG") or cabecera.startswith(b"\xff\xd8\xff")

def _intentar_cloudflare(prompt_completo: str, ruta_salida: str) -> bool:
    if _cloudflare_agotado[0]: return False
    account_id = os.environ.get("CF_ACCOUNT_ID")
    api_token = os.environ.get("CF_API_TOKEN")
    if not account_id or not api_token: return False
    headers = {"Authorization": f"Bearer {api_token}"}
    url_schnell = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    try:
        resp = requests.post(url_schnell, headers=headers, json={"prompt": prompt_completo, "steps": 8}, timeout=TIMEOUT)
        if resp.status_code == 200:
            b64_img = resp.json().get("result", {}).get("image")
            if b64_img:
                with open(ruta_salida, "wb") as f: f.write(base64.b64decode(b64_img))
                return _validar_imagen(ruta_salida)
        if resp.status_code == 429: _cloudflare_agotado[0] = True
    except requests.RequestException: pass
    return False

def _intentar_pollinations(prompt_completo: str, ruta_salida: str) -> bool:
    try:
        prompt_url = urllib.parse.quote(prompt_completo)
        url = f"https://image.pollinations.ai/prompt/{prompt_url}?width=1024&height=576&nologo=true"
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200:
            with open(ruta_salida, "wb") as f: f.write(resp.content)
            return _validar_imagen(ruta_salida)
    except Exception: pass
    return False

def _generar_imagen_emergencia(ruta_salida: str, semilla: int = 0) -> bool:
    import subprocess
    color_fondo = "0x0A0F1A"
    filtro = f"color=c={color_fondo}:s=1024x576:d=1,drawgrid=w=50:h=50:t=1:c=0x1B2A4A,noise=alls=10:allf=t+u"
    comando = ["ffmpeg", "-y", "-f", "lavfi", "-i", filtro, "-frames:v", "1", ruta_salida]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    return resultado.returncode == 0 and os.path.exists(ruta_salida)

def fue_ultima_generacion_emergencia() -> bool:
    return _ultima_fue_emergencia[0]

def generar_imagen(prompt_escena: str, ruta_salida: str, semilla: int = None) -> bool:
    sujeto = _limpiar_prompt(prompt_escena)
    prompt_completo = f"{sujeto}, {ESTILO_BASE}"
    _ultima_fue_emergencia[0] = False
    
    print(" Intentando con Cloudflare...")
    for intento_cf in range(2):
        if _intentar_cloudflare(prompt_completo, ruta_salida): return True
        if intento_cf == 0: time.sleep(3)
        
    print(" Probando Pollinations como respaldo...")
    if _intentar_pollinations(prompt_completo, ruta_salida): return True
    
    print(" Generando radar de emergencia...")
    if _generar_imagen_emergencia(ruta_salida, semilla or hash(prompt_escena) % 1000):
        _ultima_fue_emergencia[0] = True
        return True
    return False

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(0 if generar_imagen(sys.argv[1], sys.argv[2]) else 1)
