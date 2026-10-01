# Código optimizado forzando fotorrealismo y mitigando clip-arts[span_4](start_span)[span_4](end_span)[span_5](start_span)[span_5](end_span)[span_6](start_span)[span_6](end_span)[span_7](start_span)[span_7](end_span)[span_8](start_span)[span_8](end_span)[span_9](start_span)[span_9](end_span)[span_10](start_span)[span_10](end_span)[span_11](start_span)[span_11](end_span)
import os
import sys
import time
import base64
import requests

ESTILO_BASE = (
    "hyper-realistic, cinematic lighting, 8k resolution, documentary photography, "
    "dramatic shadows, Unreal Engine 5 render, highly detailed, moody atmosphere, "
    "no text, no letters, no UI, raw photo"
)

PALABRAS_A_EVITAR = [
    "close-up face", "closeup face", "portrait", "detailed face",
    "person's face", "man's face", "woman's face", "crying face",
    "screaming", "detailed hands", "hands close up",
]

def _limpiar_prompt(prompt: str) -> str:
    prompt_limpio = prompt
    for palabra in PALABRAS_A_EVITAR:
        prompt_limpio = prompt_limpio.replace(palabra, "")
    return prompt_limpio.strip()

TIMEOUT = 30
TAMANO_MINIMO_BYTES = 15_000

_cloudflare_agotado = [False]
_gemini_claves_agotadas = set()
GEMINI_ESPACIADO_SEGUNDOS = 6.5
_ultima_llamada_gemini = [0.0]
_ultima_fue_emergencia = [False]

def _validar_imagen(ruta: str) -> bool:
    if not os.path.exists(ruta): return False
    if os.path.getsize(ruta) < TAMANO_MINIMO_BYTES: return False
    with open(ruta, "rb") as f:
        cabecera = f.read(8)
    return cabecera.startswith(b"\x89PNG") or cabecera.startswith(b"\xff\xd8\xff")

def _intentar_cloudflare(prompt_completo: str, ruta_salida: str) -> bool:
    if _cloudflare_agotado[0]: return False
    account_id = os.environ.get("CF_ACCOUNT_ID")
    api_token = os.environ.get("CF_API_TOKEN")
    if not account_id or not api_token: return False
    
    headers = {"Authorization": f"Bearer {api_token}"}
    url_klein = f"[https://api.cloudflare.com/client/v4/accounts/](https://api.cloudflare.com/client/v4/accounts/){account_id}/ai/run/@cf/black-forest-labs/flux-2-klein-9b"
    
    try:
        resp = requests.post(url_klein, headers=headers, json={"prompt": prompt_completo, "width": 1024, "height": 576}, timeout=TIMEOUT)
        if resp.status_code == 200:
            if resp.headers.get("content-type", "").startswith("image"):
                with open(ruta_salida, "wb") as f: f.write(resp.content)
                if _validar_imagen(ruta_salida): return True
            else:
                b64_img = resp.json().get("result", {}).get("image")
                if b64_img:
                    with open(ruta_salida, "wb") as f: f.write(base64.b64decode(b64_img))
                    if _validar_imagen(ruta_salida): return True
        if resp.status_code == 429 and "daily free allocation" in resp.text:
            _cloudflare_agotado[0] = True
            return False
    except requests.RequestException: pass
    
    url_schnell = f"[https://api.cloudflare.com/client/v4/accounts/](https://api.cloudflare.com/client/v4/accounts/){account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    try:
        resp = requests.post(url_schnell, headers=headers, json={"prompt": prompt_completo, "steps": 8}, timeout=TIMEOUT)
        if resp.status_code == 200:
            b64_img = resp.json().get("result", {}).get("image")
            if b64_img:
                with open(ruta_salida, "wb") as f: f.write(base64.b64decode(b64_img))
                return _validar_imagen(ruta_salida)
        if resp.status_code == 429 and "daily free allocation" in resp.text:
            _cloudflare_agotado[0] = True
    except requests.RequestException: pass
    return False

def _claves_gemini_disponibles() -> list:
    claves = []
    for nombre in ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"):
        valor = os.environ.get(nombre)
        if valor: claves.append((nombre, valor))
    return [c for c in claves if c[0] not in _gemini_claves_agotadas]

def _intentar_gemini(prompt_completo: str, ruta_salida: str) -> bool:
    claves = _claves_gemini_disponibles()
    if not claves: return False
    
    espera_necesaria = GEMINI_ESPACIADO_SEGUNDOS - (time.time() - _ultima_llamada_gemini[0])
    if espera_necesaria > 0: time.sleep(espera_necesaria)
    _ultima_llamada_gemini[0] = time.time()
    
    payload = {"contents": [{"parts": [{"text": prompt_completo}]}]}
    modelos = ["gemini-3.0-flash-lite-image", "gemini-3.0-flash-image"]
    
    for nombre_clave, api_key in claves:
        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        for modelo in modelos:
            url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){modelo}:generateContent"
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
                if resp.status_code == 200:
                    partes = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    for parte in partes:
                        inline = parte.get("inlineData") or parte.get("inline_data")
                        if inline and inline.get("data"):
                            with open(ruta_salida, "wb") as f: f.write(base64.b64decode(inline["data"]))
                            return _validar_imagen(ruta_salida)
                elif resp.status_code == 429:
                    _gemini_claves_agotadas.add(nombre_clave)
                    break
            except requests.RequestException: pass
    return False

def _intentar_gradio(prompt_completo: str, ruta_salida: str) -> bool:
    try:
        from gradio_client import Client
    except ImportError: return False
    
    espacios = [
        {"nombre": "black-forest-labs/FLUX.1-schnell", "kwargs": {"prompt": prompt_completo, "seed": 0, "randomize_seed": True, "width": 1024, "height": 576, "num_inference_steps": 4}},
        {"nombre": "stabilityai/stable-diffusion-3.5-large-turbo", "kwargs": {"prompt": prompt_completo, "negative_prompt": "text, cartoon", "seed": 0, "randomize_seed": True, "width": 1024, "height": 576, "num_inference_steps": 4}}
    ]
    
    for espacio in espacios:
        try:
            cliente = Client(espacio["nombre"], download_files=True)
            resultado = cliente.predict(**espacio["kwargs"], api_name="/infer")
            ruta_resultado = resultado[0] if isinstance(resultado, (list, tuple)) else resultado
            if isinstance(ruta_resultado, str) and os.path.exists(ruta_resultado):
                import shutil
                shutil.copy(ruta_resultado, ruta_salida)
                if _validar_imagen(ruta_salida): return True
        except Exception: pass
    return False

def _intentar_huggingface(prompt_completo: str, ruta_salida: str) -> bool:
    api_token = os.environ.get("HF_API_TOKEN")
    if not api_token: return False
    url = "[https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-3.5-large-turbo](https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-3.5-large-turbo)"
    headers = {"Authorization": f"Bearer {api_token}"}
    try:
        resp = requests.post(url, headers=headers, json={"inputs": prompt_completo}, timeout=TIMEOUT)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
            with open(ruta_salida, "wb") as f: f.write(resp.content)
            return _validar_imagen(ruta_salida)
    except requests.RequestException: pass
    return False

def _generar_imagen_emergencia(ruta_salida: str, semilla: int = 0) -> bool:
    import subprocess
    colores_fondo = ["0x0A0F1A", "0x121212"]
    color_fondo = colores_fondo[semilla % len(colores_fondo)]
    filtro = f"color=c={color_fondo}:s=1024x576:d=1,noise=alls=20:allf=t+u"
    comando = ["ffmpeg", "-y", "-f", "lavfi", "-i", filtro, "-frames:v", "1", ruta_salida]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    return resultado.returncode == 0 and os.path.exists(ruta_salida)

def fue_ultima_generacion_emergencia() -> bool:
    return _ultima_fue_emergencia[0]

def generar_imagen(prompt_escena: str, ruta_salida: str, semilla: int = None) -> bool:
    sujeto = _limpiar_prompt(prompt_escena)
    prompt_completo = f"{sujeto}, {ESTILO_BASE}"
    _ultima_fue_emergencia[0] = False
    
    for intento_cf in range(2):
        if _intentar_cloudflare(prompt_completo, ruta_salida): return True
        if intento_cf == 0: time.sleep(3)
        
    if _intentar_gemini(prompt_completo, ruta_salida): return True
    if _intentar_gradio(prompt_completo, ruta_salida): return True
    if _intentar_huggingface(prompt_completo, ruta_salida): return True
    
    if _generar_imagen_emergencia(ruta_salida, semilla or hash(prompt_escena) % 1000):
        _ultima_fue_emergencia[0] = True
        return True
    return False
