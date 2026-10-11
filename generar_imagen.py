import os
import sys
import time
import base64
import requests

ESTILO_BASE = (
    "cinematic lighting, highly detailed 3D render, dark background, "
    "Unreal Engine 5 style, unmarked clean surfaces, pure visual art, empty scene without labels"
)

PALABRAS_A_EVITAR = ["text", "words", "letters", "labels", "numbers", "diagram", "infographic", "person", "face", "sign", "document"]

def _limpiar_prompt(prompt: str) -> str:
    prompt_limpio = prompt
    for palabra in PALABRAS_A_EVITAR: prompt_limpio = prompt_limpio.replace(palabra, "")
    return prompt_limpio.strip()

TIMEOUT = 40
TAMANO_MINIMO_BYTES = 10_000
_ultima_fue_emergencia = [False]

def _validar_imagen(ruta: str) -> bool:
    if not os.path.exists(ruta): return False
    if os.path.getsize(ruta) < TAMANO_MINIMO_BYTES: return False
    with open(ruta, "rb") as f: cabecera = f.read(8)
    return cabecera.startswith(b"\x89PNG") or cabecera.startswith(b"\xff\xd8\xff")

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
            resp = requests.post(url, headers=headers, json={"prompt": prompt_completo, "steps": 8}, timeout=TIMEOUT)
            if resp.status_code == 200:
                b64_img = resp.json().get("result", {}).get("image")
                if b64_img:
                    with open(ruta_salida, "wb") as f: f.write(base64.b64decode(b64_img))
                    if _validar_imagen(ruta_salida): return True
        except requests.RequestException: continue
    return False

def _generar_imagen_emergencia(ruta_salida: str) -> bool:
    import subprocess
    # En vez de una cuadrícula fea, ahora es un radar azul oscuro y sutil
    filtro = "color=c=0x050A15:s=1024x576:d=1,noise=alls=10:allf=t+u"
    comando = ["ffmpeg", "-y", "-f", "lavfi", "-i", filtro, "-frames:v", "1", ruta_salida]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    return resultado.returncode == 0 and os.path.exists(ruta_salida)

def generar_imagen(prompt_escena: str, ruta_salida: str, semilla: int = None) -> bool:
    sujeto = _limpiar_prompt(prompt_escena)
    prompt_completo = f"{sujeto}, {ESTILO_BASE}"
    _ultima_fue_emergencia[0] = False
    
    # 3 INTENTOS con pausas largas para evitar que Cloudflare nos bloquee (Pantalla negra)
    for intento in range(3):
        if _intentar_cloudflare(prompt_completo, ruta_salida): return True
        time.sleep(5) # PAUSA VITAL para no saturar la API
    
    if _generar_imagen_emergencia(ruta_salida):
        _ultima_fue_emergencia[0] = True
        return True
    return False

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(0 if generar_imagen(sys.argv[1], sys.argv[2]) else 1)
