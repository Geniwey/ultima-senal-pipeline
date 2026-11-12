import os
import sys
import time
import base64
import requests
import urllib.parse
import re

ESTILO_BASE = (
    "cinematic documentary photography, photorealistic, completely blank and unmarked surfaces, "
    "NO PEOPLE, NO FACES, ABSOLUTELY NO TEXT, NO LETTERS, NO LOGOS, NO WATERMARKS, NO AIRLINE NAMES"
)
TIMEOUT = 35
TAMANO_MINIMO_BYTES = 12_000
_cloudflare_agotado = [False]

def _validar_imagen(ruta: str) -> bool:
    if not os.path.exists(ruta) or os.path.getsize(ruta) < TAMANO_MINIMO_BYTES: return False
    with open(ruta, "rb") as f: return f.read(8).startswith(b"\x89PNG") or f.read(8).startswith(b"\xff\xd8\xff")

def _evaluar_calidad_candidato(ruta: str) -> tuple:
    try:
        import pytesseract
        from PIL import Image
        texto_detectado = pytesseract.image_to_string(Image.open(ruta).convert("L"))
        letras = re.sub(r"[^A-Za-z]", "", texto_detectado)
        if len(letras) > 3: # Si hay más de 3 letras detectadas, es basura ("AIRSA", "YEARG")
            return (False, 0.0)
        return (True, 100.0)
    except Exception:
        return (True, 50.0)

def _descargar_candidato_cf(prompt_completo: str, ruta_destino: str) -> bool:
    if _cloudflare_agotado[0]: return False
    url = f"https://api.cloudflare.com/client/v4/accounts/{os.environ.get('CF_ACCOUNT_ID')}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    try:
        resp = requests.post(url, headers={"Authorization": f"Bearer {os.environ.get('CF_API_TOKEN')}"}, json={"prompt": prompt_completo, "steps": 8}, timeout=TIMEOUT)
        if resp.status_code == 200 and _validar_imagen(ruta_destino := open(ruta_destino, "wb").write(base64.b64decode(resp.json().get("result", {}).get("image"))) or ruta_destino):
            return True
        if resp.status_code == 429: _cloudflare_agotado[0] = True
    except: pass
    return False

def _descargar_candidato_pol(prompt_completo: str, ruta_destino: str, semilla: int) -> bool:
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt_completo)}?width=1280&height=720&seed={semilla}&model=flux&nologo=true"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=TIMEOUT)
        if resp.status_code == 200:
            with open(ruta_destino, "wb") as f: f.write(resp.content)
            return _validar_imagen(ruta_destino)
    except: pass
    return False

def generar_imagen(prompt_escena: str, ruta_salida: str, semilla: int = None) -> bool:
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    if prompt_escena.startswith("INFOGRAFIA:"):
        from generar_imagen_codigo import _generar_infografia_codigo # Asume que lo tienes separado o en el mismo archivo
        return _generar_infografia_codigo(prompt_escena, ruta_salida)

    sujeto = re.sub(r"\b(text|words|letters|logo|airsa)\b", "", prompt_escena, flags=re.IGNORECASE).strip()
    prompt_completo = f"{sujeto}, {ESTILO_BASE}"
    seed_base = semilla if semilla is not None else abs(hash(prompt_escena)) % 10000

    for i in range(4):
        ruta_cand = f"{ruta_salida}_cand_{i}.png"
        descargado = _descargar_candidato_cf(prompt_completo, ruta_cand) if i < 2 else _descargar_candidato_pol(prompt_completo, ruta_cand, seed_base + i)
        if descargado:
            es_valida, score = _evaluar_calidad_candidato(ruta_cand)
            if es_valida:
                os.replace(ruta_cand, ruta_salida)
                return True
            os.remove(ruta_cand)
        time.sleep(1.0)
    
    return _descargar_candidato_pol("Wide shot of dark storm clouds over the ocean at night, completely empty sky, 8k, no text", ruta_salida, seed_base)

if __name__ == "__main__":
    if len(sys.argv) == 3: sys.exit(0 if generar_imagen(sys.argv[1], sys.argv[2]) else 1)
