import os
import sys
import time
import base64
import random
import requests
import urllib.parse
import re

ESTILO_BASE = (
    "cinematic documentary photography, dramatic moody lighting, 8k resolution, photorealistic, "
    "unmarked blank metallic surface, no airline logos, NO TEXT, NO LETTERS, NO NUMBERS, NO SIGNS, NO LABELS"
)

TIMEOUT = 35
TAMANO_MINIMO_BYTES = 12_000
_cloudflare_agotado = [False]
_ultima_fue_emergencia = [False]


def _enriquecer_prompt_sin_machacar(prompt: str) -> str:
    """
    Respeta la variedad de escenas del guion (cabina, torre, cinta, avión, radar, rescate, caja negra)
    y solo limpia términos que inducen a la IA a escribir texto en inglés.
    """
    limpio = re.sub(
        r"\b(text|words|letters|labels|sign|signs|logo|logos|title|caption|inscription|stencil|writing|numbers)\b",
        "",
        prompt,
        flags=re.IGNORECASE,
    )
    # Si el prompt habla de cinta o sensores, reforzamos que el metal sea liso y sin inscripciones como "STATIC SENSOR"
    if any(k in limpio.lower() for k in ("tape", "static", "port", "sensor", "pitot")):
        limpio += ", completely blank smooth black metal without any engraved words or markings"
    return limpio.strip()


def _validar_imagen(ruta: str) -> bool:
    if not os.path.exists(ruta):
        return False
    if os.path.getsize(ruta) < TAMANO_MINIMO_BYTES:
        return False
    with open(ruta, "rb") as f:
        cabecera = f.read(8)
    return cabecera.startswith(b"\x89PNG") or cabecera.startswith(b"\xff\xd8\xff")


def _detectar_y_limpiar_texto_ocr(ruta: str, inpaint_si_falla: bool = False) -> bool:
    """
    Detecta cualquier texto en inglés o números (incluso letras grabadas como 'STATIC SEFNSOR')
    con umbral sensible (conf > 22) y usa OpenCV Inpainting con máscara dilatada para borrarlo sin rastro.
    """
    try:
        import pytesseract
        import cv2
        import numpy as np
        from PIL import Image, ImageOps, ImageEnhance

        img_pil = Image.open(ruta).convert("RGB")
        gris = img_pil.convert("L")
        gris_contraste = ImageEnhance.Contrast(gris).enhance(2.8)
        gris_invertido = ImageOps.invert(gris_contraste)

        cajas_detectadas = []
        palabras_detectadas = []

        for var in (gris, gris_contraste, gris_invertido):
            datos = pytesseract.image_to_data(var, config="--psm 11", output_type=pytesseract.Output.DICT)
            for i, texto in enumerate(datos["text"]):
                limpio = re.sub(r"[^A-Za-z0-9]", "", texto.strip())
                conf = int(datos["conf"][i]) if str(datos["conf"][i]).lstrip("-").isdigit() else 0
                if len(limpio) >= 2 and conf > 22:
                    palabras_detectadas.append(limpio)
                    x, y, w, h = datos["left"][i], datos["top"][i], datos["width"][i], datos["height"][i]
                    cajas_detectadas.append((x, y, w, h))

        if len(palabras_detectadas) >= 1:
            if inpaint_si_falla and cajas_detectadas:
                img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
                mascara = np.zeros(img_cv.shape[:2], dtype=np.uint8)
                for (x, y, w, h) in cajas_detectadas:
                    pad = 12
                    x1, y1 = max(0, x - pad), max(0, y - pad)
                    x2, y2 = min(img_cv.shape[1], x + w + pad), min(img_cv.shape[0], y + h + pad)
                    mascara[y1:y2, x1:x2] = 255
                # Dilatar la máscara para cubrir bordes de letras curvadas o grabadas en el metal
                kernel = np.ones((7, 7), np.uint8)
                mascara = cv2.dilate(mascara, kernel, iterations=2)
                img_limpia = cv2.inpaint(img_cv, mascara, inpaintRadius=11, flags=cv2.INPAINT_TELEA)
                Image.fromarray(cv2.cvtColor(img_limpia, cv2.COLOR_BGR2RGB)).save(ruta, quality=95)
                print(f"  ✨ [Inpaint] Inscripciones borradas limpiamente ({palabras_detectadas[:3]}).")
                return False
            print(f"  ⚠️ [OCR] Inscripción detectada ({palabras_detectadas[:3]}). Regenerando...")
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
                if _validar_imagen(ruta_salida) and not _detectar_y_limpiar_texto_ocr(ruta_salida, inpaint_si_falla=ultimo_intento):
                    return True
        if resp.status_code == 429:
            _cloudflare_agotado[0] = True
    except requests.RequestException:
        pass
    return False


def _intentar_pollinations(prompt_completo: str, ruta_salida: str, semilla: int = 42, ultimo_intento: bool = False) -> bool:
    try:
        prompt_url = urllib.parse.quote(prompt_completo)
        url = f"https://image.pollinations.ai/prompt/{prompt_url}?width=1280&height=720&seed={semilla}&model=flux&nologo=true"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        if resp.status_code == 200:
            with open(ruta_salida, "wb") as f:
                f.write(resp.content)
            if _validar_imagen(ruta_salida) and not _detectar_y_limpiar_texto_ocr(ruta_salida, inpaint_si_falla=ultimo_intento):
                return True
    except Exception:
        pass
    return False


def _reciclar_imagen_existente(ruta_salida: str) -> bool:
    try:
        from PIL import Image, ImageOps, ImageEnhance
        carpeta = os.path.dirname(os.path.abspath(ruta_salida))
        candidatas = [
            os.path.join(carpeta, f)
            for f in os.listdir(carpeta)
            if f.startswith("escena_") and f.endswith(".png") and os.path.getsize(os.path.join(carpeta, f)) > TAMANO_MINIMO_BYTES
        ]
        if candidatas:
            origen = random.choice(candidatas)
            img = Image.open(origen).convert("RGB")
            img = ImageOps.mirror(img)
            w, h = img.size
            img = img.crop((int(w * 0.06), int(h * 0.06), int(w * 0.94), int(h * 0.94))).resize((w, h), Image.Resampling.LANCZOS)
            img = ImageEnhance.Brightness(img).enhance(0.94)
            img.save(ruta_salida, quality=95)
            return True
    except Exception:
        pass
    return False


def _generar_imagen_emergencia(ruta_salida: str, semilla: int = 0) -> bool:
    if _reciclar_imagen_existente(ruta_salida):
        return True
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
    sujeto = _enriquecer_prompt_sin_machacar(prompt_escena)
    prompt_completo = f"{sujeto}, {ESTILO_BASE}"
    _ultima_fue_emergencia[0] = False
    seed_base = semilla if semilla is not None else abs(hash(prompt_escena)) % 10000

    for intento_cf in range(2):
        if _intentar_cloudflare(prompt_completo, ruta_salida, ultimo_intento=(intento_cf == 1)):
            return True
        time.sleep(1.5)

    for intento_pol in range(3):
        if _intentar_pollinations(prompt_completo, ruta_salida, seed_base + intento_pol * 37, ultimo_intento=(intento_pol == 2)):
            return True
        time.sleep(2.0)

    if _generar_imagen_emergencia(ruta_salida, seed_base):
        _ultima_fue_emergencia[0] = True
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(0 if generar_imagen(sys.argv[1], sys.argv[2]) else 1)
