"""
Última Señal — Generador de imágenes con fallback automático (4 proveedores)
================================================================================
Orden de proveedores (Cloudflare primero: es el que de verdad aguanta un
vídeo entero sin fallar; el cupo gratis de imágenes de Gemini se ha
recortado mucho en 2026 y no da ni para un tercio de un vídeo):
Intento 1: Cloudflare Workers AI - Flux Schnell (gratis, cuota diaria)
Intento 2: ModelsLab (gratis, 100 imágenes/día)
Intento 3: Nano Banana / Gemini (bonus si funciona — cupo gratis muy bajo
           ahora mismo, y con un bug conocido de Google que a veces lo deja
           en 0. Se deja como intento por si en algún momento funciona,
           pero no se cuenta con él.)
Intento 4: Hugging Face (última red de seguridad, modelo variable)

Uso:
    python generar_imagen.py "prompt de la escena" salida.png
    python generar_imagen.py --test   # genera 4 imágenes de prueba con el estilo del canal

Configuración necesaria (variables de entorno):
    CF_ACCOUNT_ID     -> ID de cuenta de Cloudflare
    CF_API_TOKEN      -> Token de API de Cloudflare Workers AI
    MODELSLAB_API_KEY -> clave gratis de modelslab.com
    GEMINI_API_KEY, GEMINI_API_KEY_2 -> claves gratis de aistudio.google.com (opcionales)
    HF_API_TOKEN      -> Token de Hugging Face (opcional, último recurso)
"""

import os
import sys
import time
import base64
import requests

# ---------------------------------------------------------------------------
# ESTILO VISUAL DEL CANAL
# ---------------------------------------------------------------------------
ESTILO_BASE = (
    "flat vector infographic illustration, minimalist flat design, "
    "simple geometric icons, clean modern explainer-video style, "
    "thick outlines, simple stick-figure or flat-icon characters when a "
    "person is needed, no photorealism, no gradients clutter, no text, "
    "no watermark, no logos, no detailed faces, no detailed hands, "
    "single clear focal subject centered in frame, clearly recognizable "
    "everyday object or icon, simple and literal illustration of the "
    "concept, not abstract art, no abstract shapes, no non-representational "
    "geometric composition, plain solid background, "
    "STRICT BRAND COLOR PALETTE ONLY: deep navy blue (#1B2A4A), burnt "
    "orange (#C1502E), off-white (#E8E6DE), charcoal black (#2B2B2B) — "
    "use only these four colors plus their light/dark shades, no other hues"
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

TIMEOUT = 30
TAMANO_MINIMO_BYTES = 15_000

_cloudflare_agotado = [False]
_gemini_claves_agotadas = set()

# Margen prudente entre peticiones a Nano Banana para no toparnos con su
# límite de peticiones/minuto del plan gratis (más generoso que el de
# Pollinations, pero sigue existiendo) — así 100 imágenes tardan unos
# 10-12 min, no 25+.
GEMINI_ESPACIADO_SEGUNDOS = 6.5
_ultima_llamada_gemini = [0.0]


def _validar_imagen(ruta: str) -> bool:
    if not os.path.exists(ruta):
        return False
    if os.path.getsize(ruta) < TAMANO_MINIMO_BYTES:
        return False
    with open(ruta, "rb") as f:
        cabecera = f.read(8)
    return cabecera.startswith(b"\x89PNG") or cabecera.startswith(b"\xff\xd8\xff")


def _claves_gemini_disponibles() -> list:
    """Lee todas las claves de Google configuradas (GEMINI_API_KEY,
    GEMINI_API_KEY_2, GEMINI_API_KEY_3...) que aún no se hayan agotado hoy."""
    claves = []
    for nombre in ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"):
        valor = os.environ.get(nombre)
        if valor:
            claves.append((nombre, valor))
    return [c for c in claves if c[0] not in _gemini_claves_agotadas]


def _intentar_gemini(prompt_completo: str, ruta_salida: str) -> bool:
    claves = _claves_gemini_disponibles()
    if not claves:
        if not any(os.environ.get(n) for n in ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3")):
            print("  [Nano Banana] falta GEMINI_API_KEY, se salta este proveedor")
        else:
            print("  [Nano Banana] todas las claves configuradas se agotaron hoy, se salta este proveedor")
        return False

    espera_necesaria = GEMINI_ESPACIADO_SEGUNDOS - (time.time() - _ultima_llamada_gemini[0])
    if espera_necesaria > 0:
        time.sleep(espera_necesaria)
    _ultima_llamada_gemini[0] = time.time()

    payload = {"contents": [{"parts": [{"text": prompt_completo}]}]}
    modelos = ["gemini-3.1-flash-lite-image", "gemini-3.1-flash-image"]

    # Rotamos entre todas las claves disponibles: si una se agota a mitad
    # de la ejecución, las siguientes imágenes usan automáticamente la
    # otra clave en vez de caer directamente a Cloudflare.
    for nombre_clave, api_key in claves:
        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        for modelo in modelos:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
                if resp.status_code == 200:
                    data = resp.json()
                    partes = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    for parte in partes:
                        inline = parte.get("inlineData") or parte.get("inline_data")
                        if inline and inline.get("data"):
                            with open(ruta_salida, "wb") as f:
                                f.write(base64.b64decode(inline["data"]))
                            return _validar_imagen(ruta_salida)
                    print(f"  [Nano Banana/{nombre_clave}/{modelo}] respuesta sin imagen: {resp.text[:200]}")
                elif resp.status_code == 429:
                    print(f"  [Nano Banana/{nombre_clave}] límite alcanzado, "
                          f"pasando a la siguiente clave si hay: {resp.text[:120]}")
                    _gemini_claves_agotadas.add(nombre_clave)
                    break  # probar la siguiente clave, no el otro modelo de esta misma
                elif resp.status_code == 404:
                    print(f"  [Nano Banana/{nombre_clave}/{modelo}] modelo no encontrado (404), probando el siguiente...")
                    continue
                else:
                    print(f"  [Nano Banana/{nombre_clave}/{modelo}] respuesta {resp.status_code}: {resp.text[:200]}")
            except requests.RequestException as e:
                print(f"  [Nano Banana/{nombre_clave}/{modelo}] fallo de red: {e}")
    return False


def _intentar_cloudflare(prompt_completo: str, ruta_salida: str) -> bool:
    if _cloudflare_agotado[0]:
        return False

    account_id = os.environ.get("CF_ACCOUNT_ID")
    api_token = os.environ.get("CF_API_TOKEN")
    if not account_id or not api_token:
        print("  [Cloudflare] faltan CF_ACCOUNT_ID / CF_API_TOKEN, se salta este proveedor")
        return False

    headers = {"Authorization": f"Bearer {api_token}"}

    # --- Intento A: FLUX.2 [klein] 9B — modelo nuevo, mejor calidad según
    # la propia Cloudflare. Usa multipart/form-data, no JSON. ---
    url_klein = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/ai/run/@cf/black-forest-labs/flux-2-klein-9b"
    )
    try:
        resp = requests.post(
            url_klein, headers=headers,
            data={"prompt": prompt_completo, "width": "1024", "height": "576"},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "")
            if content_type.startswith("image"):
                with open(ruta_salida, "wb") as f:
                    f.write(resp.content)
                if _validar_imagen(ruta_salida):
                    return True
            else:
                data = resp.json()
                b64_img = data.get("result", {}).get("image")
                if b64_img:
                    with open(ruta_salida, "wb") as f:
                        f.write(base64.b64decode(b64_img))
                    if _validar_imagen(ruta_salida):
                        return True
        else:
            print(f"  [Cloudflare/flux-2-klein] respuesta {resp.status_code}: {resp.text[:200]}")
            if resp.status_code == 429 and "daily free allocation" in resp.text:
                print("  [Cloudflare] cupo diario agotado — se salta el resto de la ejecución")
                _cloudflare_agotado[0] = True
                return False
    except requests.RequestException as e:
        print(f"  [Cloudflare/flux-2-klein] fallo de red: {e}")

    if _cloudflare_agotado[0]:
        return False

    # --- Intento B (respaldo dentro de Cloudflare): flux-1-schnell, el
    # modelo anterior, por si klein fallara por algún motivo puntual ---
    print("  [Cloudflare] flux-2-klein falló, probando flux-1-schnell...")
    url_schnell = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/ai/run/@cf/black-forest-labs/flux-1-schnell"
    )
    try:
        resp = requests.post(
            url_schnell, headers=headers,
            json={"prompt": prompt_completo, "steps": 8},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            b64_img = data.get("result", {}).get("image")
            if b64_img:
                with open(ruta_salida, "wb") as f:
                    f.write(base64.b64decode(b64_img))
                return _validar_imagen(ruta_salida)
        else:
            print(f"  [Cloudflare/flux-1-schnell] respuesta {resp.status_code}: {resp.text[:200]}")
            if resp.status_code == 429 and "daily free allocation" in resp.text:
                print("  [Cloudflare] cupo diario agotado — se salta el resto de la ejecución")
                _cloudflare_agotado[0] = True
    except requests.RequestException as e:
        print(f"  [Cloudflare] fallo de red: {e}")
    return False


def _intentar_modelslab(prompt_completo: str, ruta_salida: str) -> bool:
    api_key = os.environ.get("MODELSLAB_API_KEY")
    if not api_key:
        print("  [ModelsLab] falta MODELSLAB_API_KEY, se salta este proveedor")
        return False

    url = "https://modelslab.com/api/v6/realtime/text2img"
    payload = {
        "key": api_key,
        "prompt": prompt_completo,
        "width": "1024",
        "height": "576",
        "samples": "1",
        "safety_checker": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            urls = data.get("output") or []
            if urls:
                img_resp = requests.get(urls[0], timeout=TIMEOUT)
                if img_resp.status_code == 200:
                    with open(ruta_salida, "wb") as f:
                        f.write(img_resp.content)
                    return _validar_imagen(ruta_salida)
            else:
                print(f"  [ModelsLab] sin imagen en la respuesta: {resp.text[:200]}")
        else:
            print(f"  [ModelsLab] respuesta {resp.status_code}: {resp.text[:200]}")
    except requests.RequestException as e:
        print(f"  [ModelsLab] fallo de red: {e}")
    return False


def _intentar_huggingface(prompt_completo: str, ruta_salida: str) -> bool:
    api_token = os.environ.get("HF_API_TOKEN")
    if not api_token:
        print("  [Hugging Face] falta HF_API_TOKEN, se salta este proveedor")
        return False

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


def _intentar_gradio(prompt_completo: str, ruta_salida: str) -> bool:
    # Hugging Face Spaces públicos con Gradio (demos gratis, sin API key).
    # AVISO: menos fiable que Cloudflare/ModelsLab — dependen de que el
    # Space esté encendido y sin cola en ese momento. Es una capa extra
    # de reserva, no algo con lo que contar como principal.
    try:
        from gradio_client import Client
    except ImportError:
        print("  [Gradio] falta la librería gradio_client, se salta este proveedor")
        return False

    espacios_publicos = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-3.5-large-turbo",
    ]
    for espacio in espacios_publicos:
        try:
            cliente = Client(espacio, download_files=True)
            resultado = cliente.predict(prompt_completo, api_name="/infer")
            ruta_resultado = resultado[0] if isinstance(resultado, (list, tuple)) else resultado
            if isinstance(ruta_resultado, str) and os.path.exists(ruta_resultado):
                import shutil
                shutil.copy(ruta_resultado, ruta_salida)
                if _validar_imagen(ruta_salida):
                    return True
        except Exception as e:
            print(f"  [Gradio/{espacio}] fallo: {str(e)[:150]}")
    return False


def generar_imagen(prompt_escena: str, ruta_salida: str, semilla: int = None) -> bool:
    """
    Genera una imagen para una escena, con fallback en cascada:
    Cloudflare (principal) → ModelsLab → Nano Banana (bonus) →
    Gradio/HF Spaces (bonus) → Hugging Face directo (último recurso).
    """
    prompt_completo = f"{ESTILO_BASE}, {_limpiar_prompt(prompt_escena)}"

    print("  Intentando con Cloudflare Workers AI...")
    if _intentar_cloudflare(prompt_completo, ruta_salida):
        print("  ✓ Imagen válida generada con Cloudflare")
        return True

    print("  Cloudflare falló, probando ModelsLab...")
    if _intentar_modelslab(prompt_completo, ruta_salida):
        print("  ✓ Imagen válida generada con ModelsLab")
        return True

    print("  ModelsLab también falló, probando Nano Banana (Gemini)...")
    if _intentar_gemini(prompt_completo, ruta_salida):
        print("  ✓ Imagen válida generada con Nano Banana")
        return True

    print("  Nano Banana también falló, probando Gradio (HF Spaces públicos)...")
    if _intentar_gradio(prompt_completo, ruta_salida):
        print("  ✓ Imagen válida generada con Gradio")
        return True

    print("  Gradio también falló, probando Hugging Face directo...")
    if _intentar_huggingface(prompt_completo, ruta_salida):
        print("  ✓ Imagen válida generada con Hugging Face")
        return True

    print(f"  ✗ FALLO TOTAL (5 proveedores agotados) generando imagen para: {prompt_escena[:60]}...")
    return False


def modo_test():
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
