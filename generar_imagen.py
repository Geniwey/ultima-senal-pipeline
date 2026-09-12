"""
Última Señal — Generador de imágenes con fallback automático (3 proveedores)
================================================================================
Intento 1: Pollinations.ai (gratis, sin key, pero inestable)
Intento 2: Cloudflare Workers AI - Flux Schnell (gratis con cuota diaria, más estable)
Intento 3: Hugging Face Serverless Inference API - Flux Schnell (gratis con rate-limit,
           tercera red de seguridad por si los dos anteriores fallan a la vez)

Uso:
    python generar_imagen.py "prompt de la escena" salida.png
    python generar_imagen.py --test   # genera 4 imágenes de prueba con el estilo del canal

Configuración necesaria (variables de entorno):
    CF_ACCOUNT_ID   -> ID de cuenta de Cloudflare
    CF_API_TOKEN    -> Token de API de Cloudflare Workers AI (gratis, se crea en dashboard)
    HF_API_TOKEN    -> Token de Hugging Face (gratis, se crea en huggingface.co/settings/tokens)
"""

import os
import sys
import time
import urllib.parse
import requests

# Cuánto esperar entre peticiones consecutivas a Pollinations en modo anónimo
# (sin esto, Pollinations empieza a fallar con timeouts y todo cae sobre
# Cloudflare, que entonces agota su cupo diario mucho antes de tiempo)
POLLINATIONS_ESPACIADO_SEGUNDOS = 16
_ultima_llamada_pollinations = [0.0]  # lista para poder mutarla desde la función

# Si Cloudflare responde que ha agotado su cupo diario, no tiene sentido
# seguir intentándolo el resto de la ejecución (no se libera hasta las
# 00:00 UTC) — lo marcamos y lo saltamos directamente para no perder tiempo.
_cloudflare_agotado = [False]

# ---------------------------------------------------------------------------
# ESTILO VISUAL DEL CANAL — esto es lo que le da identidad a "Última Señal"
# Se antepone a cada prompt de escena para que TODAS las imágenes se vean
# del mismo canal, sin importar qué proveedor las genere.
# ---------------------------------------------------------------------------
ESTILO_BASE = (
    "flat vector infographic illustration, bold flat colors, minimalist "
    "flat design, simple geometric icons, clean modern explainer-video "
    "style, high contrast, thick outlines, simple stick-figure or "
    "flat-icon characters when a person is needed, no photorealism, "
    "no gradients clutter, no text, no watermark, no logos, "
    "no detailed faces, no detailed hands, single clear focal subject "
    "centered in frame"
)

# Palabras a evitar en los prompts de escena (se filtran antes de enviar,
# porque son las que más fallos de caras/manos provocan en estos modelos):
PALABRAS_A_EVITAR = [
    "close-up face", "closeup face", "portrait", "detailed face",
    "person's face", "man's face", "woman's face", "crying face",
    "screaming", "detailed hands", "hands close up",
]


def _limpiar_prompt(prompt: str) -> str:
    """Quita frases que suelen disparar caras/manos deformes en modelos gratis."""
    prompt_limpio = prompt
    for palabra in PALABRAS_A_EVITAR:
        prompt_limpio = prompt_limpio.replace(palabra, "")
    return prompt_limpio.strip()

# Prompts de prueba para validar el estilo antes de seguir construyendo
PROMPTS_TEST = [
    "aircraft cockpit instrument panel at night, warning lights glowing, "
    "empty cockpit, tense atmosphere",
    "air traffic control radar room, dim blue monitors, empty chair, "
    "night shift, quiet tension",
    "aviation accident investigation team examining wreckage debris field "
    "at dawn, fog, investigators in the distance, respectful wide shot",
    "black box flight recorder on a metal table, evidence bag, "
    "forensic lab lighting, close up, investigation office",
]

TIMEOUT = 25
TIMEOUT_POLLINATIONS = 60  # 1920x1080 tarda más de 25s en generarse a menudo
MAX_REINTENTOS = 2
TAMANO_MINIMO_BYTES = 15_000  # por debajo de esto, la imagen casi seguro está rota/en blanco


def _validar_imagen(ruta: str) -> bool:
    """Comprueba que el archivo existe, pesa lo suficiente y es un PNG/JPEG válido."""
    if not os.path.exists(ruta):
        return False
    tamano = os.path.getsize(ruta)
    if tamano < TAMANO_MINIMO_BYTES:
        return False
    with open(ruta, "rb") as f:
        cabecera = f.read(8)
    es_png = cabecera.startswith(b"\x89PNG")
    es_jpeg = cabecera.startswith(b"\xff\xd8\xff")
    return es_png or es_jpeg


def _intentar_pollinations(prompt_completo: str, ruta_salida: str, semilla: int) -> bool:
    token = os.environ.get("POLLINATIONS_API_TOKEN")

    # Con token registrado, el límite de 1 petición/15-16s no aplica (o es
    # mucho más alto) — solo frenamos en modo anónimo, sin token.
    if not token:
        espera_necesaria = POLLINATIONS_ESPACIADO_SEGUNDOS - (time.time() - _ultima_llamada_pollinations[0])
        if espera_necesaria > 0:
            time.sleep(espera_necesaria)
        _ultima_llamada_pollinations[0] = time.time()

    prompt_codificado = urllib.parse.quote(prompt_completo)
    url = (
        f"https://image.pollinations.ai/prompt/{prompt_codificado}"
        f"?width=1920&height=1080&seed={semilla}&nologo=true&model=flux"
    )
    if token:
        url += f"&token={token}"
    try:
        resp = requests.get(url, timeout=TIMEOUT_POLLINATIONS)
        if resp.status_code == 200 and len(resp.content) > TAMANO_MINIMO_BYTES:
            with open(ruta_salida, "wb") as f:
                f.write(resp.content)
            return _validar_imagen(ruta_salida)
    except requests.RequestException as e:
        print(f"  [Pollinations] fallo de red: {e}")
    return False


def _intentar_cloudflare(prompt_completo: str, ruta_salida: str) -> bool:
    if _cloudflare_agotado[0]:
        return False  # ya sabemos que se quedó sin cupo hoy, no perdemos tiempo reintentando

    account_id = os.environ.get("CF_ACCOUNT_ID")
    api_token = os.environ.get("CF_API_TOKEN")
    if not account_id or not api_token:
        print("  [Cloudflare] faltan CF_ACCOUNT_ID / CF_API_TOKEN, se salta este proveedor")
        return False

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/ai/run/@cf/black-forest-labs/flux-1-schnell"
    )
    headers = {"Authorization": f"Bearer {api_token}"}
    try:
        # Confirmado con la documentación oficial de Cloudflare: este
        # endpoint solo acepta prompt, seed y steps — nada de width/height.
        resp = requests.post(
            url, headers=headers,
            json={"prompt": prompt_completo, "steps": 8},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            import base64
            b64_img = data.get("result", {}).get("image")
            if b64_img:
                with open(ruta_salida, "wb") as f:
                    f.write(base64.b64decode(b64_img))
                return _validar_imagen(ruta_salida)
        else:
            print(f"  [Cloudflare] respuesta {resp.status_code}: {resp.text[:200]}")
            if resp.status_code == 429 and "daily free allocation" in resp.text:
                print("  [Cloudflare] cupo diario agotado — se salta este proveedor el resto de la ejecución")
                _cloudflare_agotado[0] = True
    except requests.RequestException as e:
        print(f"  [Cloudflare] fallo de red: {e}")
    return False


def _intentar_huggingface(prompt_completo: str, ruta_salida: str) -> bool:
    api_token = os.environ.get("HF_API_TOKEN")
    if not api_token:
        print("  [Hugging Face] falta HF_API_TOKEN, se salta este proveedor")
        return False

    # FLUX.1-schnell fue retirado del servicio gratis de HF; usamos SDXL,
    # que lleva más tiempo estable en su catálogo gratuito.
    url = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {api_token}"}
    try:
        resp = requests.post(
            url, headers=headers, json={"inputs": prompt_completo}, timeout=TIMEOUT + 15
        )
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
            with open(ruta_salida, "wb") as f:
                f.write(resp.content)
            return _validar_imagen(ruta_salida)
        if resp.status_code == 503:
            print("  [Hugging Face] modelo cargando (cold start), no da tiempo en este intento")
        else:
            print(f"  [Hugging Face] respuesta {resp.status_code}: {resp.text[:200]}")
    except requests.RequestException as e:
        print(f"  [Hugging Face] fallo de red: {e}")
    return False


def generar_imagen(prompt_escena: str, ruta_salida: str, semilla: int = None) -> bool:
    """
    Genera una imagen para una escena, con reintentos y fallback de proveedor.
    Devuelve True si consiguió una imagen válida, False si fallaron todos los intentos.
    """
    if semilla is None:
        semilla = int(time.time()) % 100000

    prompt_completo = f"{ESTILO_BASE}, {_limpiar_prompt(prompt_escena)}"

    # --- Proveedor 1: Pollinations, con reintentos ---
    for intento in range(1, MAX_REINTENTOS + 1):
        print(f"  Intento {intento}/{MAX_REINTENTOS} con Pollinations...")
        if _intentar_pollinations(prompt_completo, ruta_salida, semilla + intento):
            print("  ✓ Imagen válida generada con Pollinations")
            return True
        time.sleep(2)

    # --- Proveedor 2 (fallback): Cloudflare Workers AI ---
    print("  Pollinations falló, probando Cloudflare Workers AI...")
    if _intentar_cloudflare(prompt_completo, ruta_salida):
        print("  ✓ Imagen válida generada con Cloudflare")
        return True

    # --- Proveedor 3 (última red de seguridad): Hugging Face ---
    print("  Cloudflare también falló, probando Hugging Face...")
    if _intentar_huggingface(prompt_completo, ruta_salida):
        print("  ✓ Imagen válida generada con Hugging Face")
        return True

    print(f"  ✗ FALLO TOTAL (3 proveedores agotados) generando imagen para: {prompt_escena[:60]}...")
    return False


def modo_test():
    """Genera las 4 imágenes de prueba del estilo del canal."""
    carpeta = "test_estilo"
    os.makedirs(carpeta, exist_ok=True)
    resultados = []
    for i, prompt in enumerate(PROMPTS_TEST, start=1):
        ruta = os.path.join(carpeta, f"prueba_{i}.png")
        print(f"\n[{i}/{len(PROMPTS_TEST)}] Generando: {prompt[:60]}...")
        ok = generar_imagen(prompt, ruta)
        resultados.append((ruta, ok))

    print("\n" + "=" * 50)
    print("RESUMEN")
    print("=" * 50)
    for ruta, ok in resultados:
        estado = "✓ OK" if ok else "✗ FALLÓ"
        print(f"{estado}  {ruta}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        modo_test()
    elif len(sys.argv) == 3:
        prompt_arg, salida_arg = sys.argv[1], sys.argv[2]
        exito = generar_imagen(prompt_arg, salida_arg)
        sys.exit(0 if exito else 1)
    else:
        print(__doc__)
