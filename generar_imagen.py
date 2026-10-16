import os
import sys
import time
import base64
import requests
import urllib.parse
import re

ESTILO_BASE = (
    "cinematic exterior aviation photography, commercial Boeing airliner in dark storm clouds, "
    "dramatic lightning, rain droplets on dark metallic fuselage, moody lighting, 8k resolution, "
    "clean surfaces, NO TEXT, NO SIGNS, NO NUMBERS, NO PEOPLE, NO GAUGES, NO DASHBOARD"
)

# Diccionario de reemplazo automático: si el LLM pide algo que genera texto o caras raras, lo cambiamos por un plano exterior limpio
REEMPLAZOS_SEGUROS = {
    r"\b(cockpit|dashboard|hud|instrument\w*|gauge\w*|dial\w*|speedometer|tachometer|panel\w*|screen\w*|monitor\w*|display\w*)\b": "commercial airplane wing cutting through dark storm clouds",
    r"\b(book\w*|manual\w*|report\w*|paper\w*|document\w*|page\w*|letter\w*|checklist\w*|chart\w*|graph\w*)\b": "dark metallic aircraft black box recorder under dramatic studio light",
    r"\b(person|people|passenger\w*|pilot\w*|crew|man|men|woman|women|worker\w*|technic\w*|investigator\w*|family|families|face\w*|hand\w*|auditor\w*|student\w*)\b": "commercial airliner silhouette on a foggy airport runway at night",
    r"\b(insect\w*|ant\w*|bug\w*)\b": "close up of metallic aircraft pitot tube sensor on exterior fuselage in rain",
    r"\b(seal|badge|logo|emblem|medal|coin|sign\w*)\b": "commercial aircraft tail fin against a dark stormy sky",
    r"\b(cabin|aisle|seat\w*|interior)\b": "exterior view of commercial airliner windows glowing faintly in night storm",
}

TIMEOUT = 30
TAMANO_MINIMO_BYTES = 10_000
_cloudflare_agotado = [False]
_ultima_fue_emergencia = [False]


def _limpiar_prompt(prompt: str) -> str:
    prompt_limpio = prompt
    for patron, reemplazo in REEMPLAZOS_SEGUROS.items():
        prompt_limpio = re.sub(patron, reemplazo, prompt_limpio, flags=re.IGNORECASE)
    return prompt_limpio.strip()


def _validar_imagen(ruta: str) -> bool:
    if not os.path.exists(ruta):
        return False
    if os.path.getsize(ruta) < TAMANO_MINIMO_BYTES:
        return False
    with open(ruta, "rb") as f:
        cabecera = f.read(8)
    return cabecera.startswith(b"\x89PNG") or cabecera.startswith(b"\xff\xd8\xff")


def _detectar_y_limpiar_texto_ocr(ruta: str, tapar_si_falla: bool = False) -> bool:
    """
    Usa preprocesamiento multicapa (escala de grises, alto contraste e inversión de color)
    para detectar letreros brillantes (como 'ETTEY' o 'FLACT') sobre fondos oscuros.
    Devuelve True si hay texto alienígena. Si tapar_si_falla=True, borra el texto de la imagen.
    """
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageDraw

        img_orig = Image.open(ruta).convert("RGB")
        gris = img_orig.convert("L")
        gris_contraste = ImageEnhance.Contrast(gris).enhance(2.8)
        gris_invertido = ImageOps.invert(gris_contraste)

        # Binarización para cazar letreros luminosos (blancos/rojos/amarillos sobre fondo oscuro)
        umbral_brillante = gris.point(lambda p: 255 if p > 175 else 0)
        umbral_inv = ImageOps.invert(umbral_brillante)

        variantes = [gris_contraste, gris_invertido, umbral_inv]
        cajas_detectadas = []
        palabras_detectadas = []

        for var in variantes:
            datos = pytesseract.image_to_data(var, config="--psm 11", output_type=pytesseract.Output.DICT)
            for i, texto in enumerate(datos["text"]):
                limpio = re.sub(r"[^A-Za-z0-9]", "", texto.strip())
                conf = int(datos["conf"][i]) if str(datos["conf"][i]).lstrip("-").isdigit() else 0
                if len(limpio) >= 2 and conf > 35:
                    palabras_detectadas.append(limpio)
                    x, y, w, h = datos["left"][i], datos["top"][i], datos["width"][i], datos["height"][i]
                    cajas_detectadas.append((x, y, w, h))

        if len(palabras_detectadas) >= 1:
            if tapar_si_falla and cajas_detectadas:
                # Borrado quirúrgico: difumina y oscurece la zona exacta donde había letras inventadas
                img_edit = img_orig.copy()
                for (x, y, w, h) in cajas_detectadas:
                    pad = 14
                    x1, y1 = max(0, x - pad), max(0, y - pad)
                    x2, y2 = min(img_edit.width, x + w + pad), min(img_edit.height, y + h + pad)
                    recorte = img_edit.crop((x1, y1, x2, y2)).filter(ImageFilter.GaussianBlur(radius=22))
                    recorte = ImageEnhance.Brightness(recorte).enhance(0.25)
                    img_edit.paste(recorte, (x1, y1))
                img_edit.save(ruta)
                print(f"  🧹 [OCR] Letrero alienígena borrado automáticamente ({palabras_detectadas[:3]}).")
                return False
            print(f"  ⚠️ [OCR] Texto alienígena detectado ({palabras_detectadas[:3]}). Descartando...")
            return True
    except Exception:
        pass
    return False


def _intentar_cloudflare(prompt_completo: str, ruta_salida: str, ultimo_intento: bool = False) -> bool:
    if _cloudflare_agotado[0]:
        return False
    account_id = os.environ.get("CF_ACCOUNT_ID")
    api_token = os.environ.get("CF_API_TOKEN")
    if not account_id or not api_token:
        return False
    headers = {"Authorization": f"Bearer {api_token}"}
    url_schnell = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    try:
        resp = requests.post(url_schnell, headers=headers, json={"prompt": prompt_completo, "steps": 8}, timeout=TIMEOUT)
        if resp.status_code == 200:
            b64_img = resp.json().get("result", {}).get("image")
            if b64_img:
                with open(ruta_salida, "wb") as f:
                    f.write(base64.b64decode(b64_img))
                if _validar_imagen(ruta_salida) and not _detectar_y_limpiar_texto_ocr(ruta_salida, tapar_si_falla=ultimo_intento):
                    return True
        if resp.status_code == 429:
            _cloudflare_agotado[0] = True
    except requests.Timeout:
        print("  [AVISO] Timeout de Cloudflare. Reintentando...")
    except requests.RequestException:
        pass
    return False


def _intentar_pollinations(prompt_completo: str, ruta_salida: str, semilla: int = 42, ultimo_intento: bool = False) -> bool:
    try:
        prompt_url = urllib.parse.quote(prompt_completo)
        url = f"https://image.pollinations.ai/prompt/{prompt_url}?width=1280&height=720&seed={semilla}&nologo=true"
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200:
            with open(ruta_salida, "wb") as f:
                f.write(resp.content)
            if _validar_imagen(ruta_salida) and not _detectar_y_limpiar_texto_ocr(ruta_salida, tapar_si_falla=ultimo_intento):
                return True
    except Exception:
        pass
    return False


def _generar_imagen_emergencia(ruta_salida: str, semilla: int = 0) -> bool:
    import subprocess
    color_fondo = "0x0A0F1A"
    filtro = f"color=c={color_fondo}:s=1280x720:d=1,drawgrid=w=50:h=50:t=1:c=0x1B2A4A,noise=alls=10:allf=t+u"
    comando = ["ffmpeg", "-y", "-f", "lavfi", "-i", filtro, "-frames:v", "1", "-update", "1", ruta_salida]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    return resultado.returncode == 0 and os.path.exists(ruta_salida)


def fue_ultima_generacion_emergencia() -> bool:
    return _ultima_fue_emergencia[0]


def generar_imagen(prompt_escena: str, ruta_salida: str, semilla: int = None) -> bool:
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    sujeto = _limpiar_prompt(prompt_escena)
    prompt_completo = f"{sujeto}, {ESTILO_BASE}"
    _ultima_fue_emergencia[0] = False
    seed_base = semilla if semilla is not None else abs(hash(prompt_escena)) % 10000

    for intento_cf in range(3):
        es_ultimo = (intento_cf == 2)
        if _intentar_cloudflare(prompt_completo, ruta_salida, ultimo_intento=es_ultimo):
            return True
        time.sleep(1)

    for intento_pol in range(2):
        es_ultimo = (intento_pol == 1)
        if _intentar_pollinations(prompt_completo, ruta_salida, seed_base + intento_pol * 17, ultimo_intento=es_ultimo):
            return True

    if _generar_imagen_emergencia(ruta_salida, seed_base):
        _ultima_fue_emergencia[0] = True
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(0 if generar_imagen(sys.argv[1], sys.argv[2]) else 1)
