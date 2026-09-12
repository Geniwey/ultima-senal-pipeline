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

# ---------------------------------------------------------------------------
# ESTILO VISUAL DEL CANAL — esto es lo que le da identidad a "Última Señal"
# Se antepone a cada prompt de escena para que TODAS las imágenes se vean
# del mismo canal, sin importar qué proveedor las genere.
# ---------------------------------------------------------------------------
ESTILO_BASE = (
    "cinematic documentary photography, investigative journalism aesthetic, "
    "desaturated cold color grading, deep blues and grays, dramatic low-key "
    "lighting, film grain, 35mm lens look, somber and serious tone, "
    "photorealistic, high detail, no text, no watermark, no logos"
)

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
    prompt_codificado = urllib.parse.quote(prompt_completo)
    url = (
        f"https://image.pollinations.ai/prompt/{prompt_codificado}"
        f"?width=1280&height=720&seed={semilla}&nologo=true&model=flux"
    )
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200 and len(resp.content) > TAMANO_MINIMO_BYTES:
            with open(ruta_salida, "wb") as f:
                f.write(resp.content)
            return _validar_imagen(ruta_salida)
    except requests.RequestException as e:
        print(f"  [Pollinations] fallo de red: {e}")
    return False


def _intentar_cloudflare(prompt_completo: str, ruta_salida: str) -> bool:
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
        resp = requests.post(
            url, headers=headers, json={"prompt": prompt_completo}, timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            # Cloudflare devuelve la imagen en base64 dentro de result.image
            import base64
            b64_img = data.get("result", {}).get("image")
            if b64_img:
                with open(ruta_salida, "wb") as f:
                    f.write(base64.b64decode(b64_img))
                return _validar_imagen(ruta_salida)
    except requests.RequestException as e:
        print(f"  [Cloudflare] fallo de red: {e}")
    return False


def _intentar_huggingface(prompt_completo: str, ruta_salida: str) -> bool:
    api_token = os.environ.get("HF_API_TOKEN")
    if not api_token:
        print("  [Hugging Face] falta HF_API_TOKEN, se salta este proveedor")
        return False

    url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
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

    prompt_completo = f"{ESTILO_BASE}, {prompt_escena}"

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
