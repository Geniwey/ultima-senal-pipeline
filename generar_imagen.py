"""
Última Señal — Generador de imágenes con fallback automático (4 proveedores)
================================================================================
Orden: Cloudflare (principal) → Nano Banana/Gemini (bonus) →
Gradio/HF Spaces (bonus) → Hugging Face directo (último recurso) →
tarjeta de marca de emergencia (sin IA, nunca falla).

IMPORTANTE sobre el prompt: el SUJETO (qué dibujar) va SIEMPRE primero,
el estilo va corto y después. Con un modelo rápido/pequeño como
flux-2-klein, un bloque de estilo larguísimo puesto ANTES del sujeto
hace que el modelo "gaste" su atención ahí y produzca solo fondo/marco,
ignorando lo que realmente pedimos dibujar — eso es lo que causó las
tarjetas vacías repetidas en varias pruebas.
"""

import os
import sys
import time
import base64
import requests

ESTILO_BASE = (
    "flat technical icon illustration, dark navy or black background, "
    "burnt orange accent color, thick clean outlines, single object, "
    "no text, no people crowd, documentary style, not childish"
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


NEGATIVE_PROMPT = (
    "text, letters, words, watermark, logo, multiple panels, diagram, "
    "dashboard, powerpoint, infographic chart, crowd of people, "
    "blurry, low quality, empty background, blank frame"
)

PROMPTS_TEST = [
    "aircraft cockpit instrument panel at night, warning lights glowing",
    "air traffic control radar room, dim blue monitors, empty chair",
    "black box flight recorder on a metal table, evidence bag",
    "roll of adhesive tape covering an aircraft sensor, close up",
]

TIMEOUT = 30
TAMANO_MINIMO_BYTES = 15_000

_cloudflare_agotado = [False]
_gemini_claves_agotadas = set()

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


def _intentar_cloudflare(prompt_completo: str, ruta_salida: str) -> bool:
    if _cloudflare_agotado[0]:
        return False

    account_id = os.environ.get("CF_ACCOUNT_ID")
    api_token = os.environ.get("CF_API_TOKEN")
    if not account_id or not api_token:
        print("  [Cloudflare] faltan CF_ACCOUNT_ID / CF_API_TOKEN, se salta este proveedor")
        return False

    headers = {"Authorization": f"Bearer {api_token}"}

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
        print(f"  [Cloudflare/flux-1-schnell] fallo de red: {e}")
    return False


def _claves_gemini_disponibles() -> list:
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
                    break
                elif resp.status_code == 404:
                    print(f"  [Nano Banana/{nombre_clave}/{modelo}] modelo no encontrado (404), probando el siguiente...")
                    continue
                else:
                    print(f"  [Nano Banana/{nombre_clave}/{modelo}] respuesta {resp.status_code}: {resp.text[:200]}")
            except requests.RequestException as e:
                print(f"  [Nano Banana/{nombre_clave}/{modelo}] fallo de red: {e}")
    return False


def _intentar_gradio(prompt_completo: str, ruta_salida: str) -> bool:
    try:
        from gradio_client import Client
    except ImportError:
        print("  [Gradio] falta la librería gradio_client, se salta este proveedor")
        return False

    espacios_publicos = [
        {"nombre": "black-forest-labs/FLUX.1-schnell", "kwargs": {"prompt": prompt_completo}},
        {"nombre": "stabilityai/stable-diffusion-3.5-large-turbo",
         "kwargs": {"prompt": prompt_completo, "negative_prompt": "", "seed": 0, "randomize_seed": True}},
    ]
    for espacio in espacios_publicos:
        try:
            cliente = Client(espacio["nombre"], download_files=True)
            resultado = cliente.predict(**espacio["kwargs"], api_name="/infer")
            ruta_resultado = resultado[0] if isinstance(resultado, (list, tuple)) else resultado
            if isinstance(ruta_resultado, str) and os.path.exists(ruta_resultado):
                import shutil
                shutil.copy(ruta_resultado, ruta_salida)
                if _validar_imagen(ruta_salida):
                    return True
        except Exception as e:
            print(f"  [Gradio/{espacio['nombre']}] fallo: {str(e)[:150]}")
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


def _generar_imagen_emergencia(ruta_salida: str, semilla: int = 0) -> bool:
    import subprocess
    colores_fondo = ["0x1B2A4A", "0x2B2B2B"]
    color_fondo = colores_fondo[semilla % len(colores_fondo)]
    margen = 50 + (semilla % 5) * 15
    filtro = (
        f"color=c={color_fondo}:s=1024x576:d=1,"
        f"drawbox=x={margen}:y={margen}:w={1024-2*margen}:h={576-2*margen}:color=0xC1502E@1.0:t=4"
    )
    comando = ["ffmpeg", "-y", "-f", "lavfi", "-i", filtro, "-frames:v", "1", ruta_salida]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    return resultado.returncode == 0 and os.path.exists(ruta_salida)


def generar_imagen(prompt_escena: str, ruta_salida: str, semilla: int = None) -> bool:
    """
    ARREGLO CLAVE: el SUJETO (prompt_escena) va PRIMERO en el prompt
    final, y el estilo (corto) va DESPUÉS — al revés de como estaba antes,
    que ponía un bloque de estilo larguísimo por delante y hacía que el
    modelo ignorase el sujeto real, produciendo tarjetas vacías.
    """
    sujeto = _limpiar_prompt(prompt_escena)
    prompt_completo = f"{sujeto}, {ESTILO_BASE}"

    print("  Intentando con Cloudflare Workers AI...")
    if _intentar_cloudflare(prompt_completo, ruta_salida):
        print("  ✓ Imagen válida generada con Cloudflare")
        return True

    print("  Cloudflare falló, probando Nano Banana (Gemini)...")
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

    print("  Los 4 proveedores de IA fallaron — usando tarjeta de marca de emergencia (sin IA)...")
    if _generar_imagen_emergencia(ruta_salida, semilla=hash(prompt_escena) % 1000):
        print("  ✓ Imagen de emergencia generada (el vídeo se completa igual)")
        return True

    print(f"  ✗ FALLO TOTAL generando imagen para: {prompt_escena[:60]}...")
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
