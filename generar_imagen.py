import os
import sys
import time
import base64
import random
import requests
import urllib.parse
import re

ESTILO_BASE = (
    "cinematic documentary photography, well-lit scene, bright rim lighting, clear visibility, "
    "8k resolution, photorealistic, unmarked blank metallic surface, smooth texture, "
    "no airline logos, NO TEXT, NO LETTERS, NO NUMBERS, NO SIGNS"
)

TIMEOUT = 35
TAMANO_MINIMO_BYTES = 12_000
_cloudflare_agotado = [False]
_ultima_fue_emergencia = [False]


def _enriquecer_prompt_sin_machacar(prompt: str) -> str:
    limpio = re.sub(
        r"\b(text|words|letters|labels|sign|signs|logo|logos|title|caption|inscription|stencil|writing|numbers|tunnel|subway)\b",
        "",
        prompt,
        flags=re.IGNORECASE,
    )
    if any(k in limpio.lower() for k in ("tape", "static", "port", "sensor")):
        limpio += ", glossy metallic silver-grey adhesive duct tape with sticky edges, completely blank smooth metal"
    return limpio.strip()


def _validar_imagen(ruta: str) -> bool:
    if not os.path.exists(ruta):
        return False
    if os.path.getsize(ruta) < TAMANO_MINIMO_BYTES:
        return False
    with open(ruta, "rb") as f:
        cabecera = f.read(8)
    return cabecera.startswith(b"\x89PNG") or cabecera.startswith(b"\xff\xd8\xff")


def _corregir_exposicion_oscura(ruta: str):
    try:
        import numpy as np
        from PIL import Image, ImageEnhance

        img = Image.open(ruta).convert("RGB")
        arr = np.array(img, dtype=np.float32)
        brillo_medio = float(arr.mean())

        if brillo_medio < 62.0:
            gamma = 0.62 if brillo_medio < 38.0 else 0.74
            arr_norm = np.clip(arr / 255.0, 0.0, 1.0)
            arr_gamma = np.power(arr_norm, gamma) * 255.0
            img_clara = Image.fromarray(np.clip(arr_gamma, 0, 255).astype(np.uint8))
            img_clara = ImageEnhance.Contrast(img_clara).enhance(1.12)
            img_clara.save(ruta, quality=95)
    except Exception:
        pass


def _tiene_texto_real_ocr(ruta: str) -> bool:
    """
    Detecta letreros en paredes o fuselajes (conf > 52 y >= 3 caracteres alfanuméricos)
    y descarta la imagen para pedir una limpia, sin emborronar jamás la foto.
    """
    try:
        import pytesseract
        from PIL import Image, ImageEnhance

        img_pil = Image.open(ruta).convert("L")
        img_contraste = ImageEnhance.Contrast(img_pil).enhance(2.0)
        datos = pytesseract.image_to_data(img_contraste, config="--psm 11", output_type=pytesseract.Output.DICT)
        palabras_claras = []

        for i, texto in enumerate(datos["text"]):
            solo_alfanum = re.sub(r"[^A-Za-z0-9]", "", texto.strip())
            conf = int(datos["conf"][i]) if str(datos["conf"][i]).lstrip("-").isdigit() else 0
            if len(solo_alfanum) >= 3 and conf > 52:
                palabras_claras.append(solo_alfanum)

        if len(palabras_claras) >= 1:
            print(f"  ⚠️ [OCR] Letrero detectado ({palabras_claras[:2]}). Regenerando toma limpia...")
            return True
    except Exception:
        pass
    return False


def _intentar_cloudflare(prompt_completo: str, ruta_salida: str, ignorar_ocr: bool = False) -> bool:
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
                if _validar_imagen(ruta_salida):
                    if not ignorar_ocr and _tiene_texto_real_ocr(ruta_salida):
                        return False
                    _corregir_exposicion_oscura(ruta_salida)
                    return True
        if resp.status_code == 429:
            _cloudflare_agotado[0] = True
    except requests.RequestException:
        pass
    return False


def _intentar_pollinations(prompt_completo: str, ruta_salida: str, semilla: int = 42, ignorar_ocr: bool = False) -> bool:
    try:
        prompt_url = urllib.parse.quote(prompt_completo)
        url = f"https://image.pollinations.ai/prompt/{prompt_url}?width=1280&height=720&seed={semilla}&model=flux&nologo=true"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        if resp.status_code == 200:
            with open(ruta_salida, "wb") as f:
                f.write(resp.content)
            if _validar_imagen(ruta_salida):
                if not ignorar_ocr and _tiene_texto_real_ocr(ruta_salida):
                    return False
                _corregir_exposicion_oscura(ruta_salida)
                return True
    except Exception:
        pass
    return False


def _reciclar_imagen_existente(ruta_salida: str) -> bool:
    try:
        from PIL import Image, ImageOps
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
        if _intentar_cloudflare(prompt_completo, ruta_salida, ignorar_ocr=(intento_cf == 1)):
            return True
        time.sleep(1.5)

    for intento_pol in range(3):
        if _intentar_pollinations(prompt_completo, ruta_salida, seed_base + intento_pol * 43, ignorar_ocr=(intento_pol == 2)):
            return True
        time.sleep(2.0)

    if _generar_imagen_emergencia(ruta_salida, seed_base):
        _ultima_fue_emergencia[0] = True
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(0 if generar_imagen(sys.argv[1], sys.argv[2]) else 1)
