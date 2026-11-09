import os
import sys
import time
import base64
import requests
import urllib.parse
import re

ESTILO_BASE = (
    "cinematic documentary photography, exterior or macro mechanical shot, balanced moody lighting, "
    "8k resolution, photorealistic, unmarked blank metallic surface, smooth texture, "
    "NO PEOPLE, NO FACES, NO PORTRAITS, NO TABLETS, NO SCREENS, NO TEXT, NO LETTERS, NO NUMBERS"
)

TIMEOUT = 35
TAMANO_MINIMO_BYTES = 12_000
_cloudflare_agotado = [False]
_ultima_fue_emergencia = [False]


def _generar_infografia_codigo(tipo: str, ruta_salida: str) -> bool:
    """
    Renderiza las 4 infografías en 1920x1080 nativo con márgenes de seguridad del 15%
    y fuentes grandes para que se lean perfecto en móvil y NUNCA se corten por los bordes.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        plt.rcParams["font.sans-serif"] = "DejaVu Sans"
        plt.rcParams["axes.edgecolor"] = "#2A3F5F"
        fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
        fig.patch.set_facecolor("#070B12")
        ax.set_facecolor("#0B1320")

        # Márgenes amplios de seguridad (deja espacio arriba para el título y abajo para el rótulo del vídeo)
        fig.subplots_adjust(left=0.12, right=0.92, top=0.84, bottom=0.22)

        if "GRAFICA_ALTITUD" in tipo:
            minutos = np.linspace(0, 31, 200)
            alt_falsa = np.piecewise(
                minutos,
                [minutos < 6, minutos >= 6],
                [lambda t: (t / 6.0) * 9700, 9700],
            )
            alt_real = np.piecewise(
                minutos,
                [minutos < 6, (minutos >= 6) & (minutos < 18), minutos >= 18],
                [
                    lambda t: (t / 6.0) * 9700,
                    lambda t: 9700 - ((t - 6.0) / 12.0) * 5200,
                    lambda t: 4500 * (1.0 - ((t - 18.0) / 13.0) ** 1.4),
                ],
            )
            ax.plot(minutos, alt_falsa, color="#FFAA00", linewidth=5.0, linestyle="--", label="LECTURA FALSA EN CABINA / RADAR (9700 PIES)")
            ax.plot(minutos, alt_real, color="#FF2A2A", linewidth=6.0, label="ALTITUD REAL DEL AVIÓN (DESCENSO AL MAR)")
            ax.fill_between(minutos, alt_real, 0, color="#FF2A2A", alpha=0.18)
            ax.scatter([31], [0], color="#FFFFFF", s=240, zorder=5)
            ax.annotate(
                "01:11 AM - IMPACTO (0 PIES)",
                xy=(30.8, 200),
                xytext=(16.5, 2600),
                color="#FFFFFF",
                fontweight="bold",
                fontsize=18,
                arrowprops=dict(facecolor="#FF2A2A", shrink=0.08, width=3),
            )
            ax.set_title("DATOS CAJA NEGRA (FDR): ALTITUD FALSA VS REAL", color="#FFFFFF", fontsize=24, fontweight="bold", pad=22)
            ax.set_xlabel("MINUTOS DE VUELO DESDE EL DESPEGUE (LIMA)", color="#B0C4DE", fontsize=17, fontweight="bold", labelpad=12)
            ax.set_ylabel("ALTITUD (PIES)", color="#B0C4DE", fontsize=17, fontweight="bold", labelpad=12)
            ax.set_ylim(-600, 12200)
            ax.set_xlim(0, 34)
            ax.grid(True, color="#1C2D42", linestyle=":", linewidth=1.5)
            ax.tick_params(colors="#FFFFFF", labelsize=15)
            leg = ax.legend(loc="upper left", facecolor="#070B12", edgecolor="#2A3F5F", fontsize=16)
            for text in leg.get_texts():
                text.set_color("#FFFFFF")

        elif "MAPA_RUTA" in tipo:
            costa_x = [-77.05, -77.12, -77.16, -77.22, -77.27, -77.32]
            costa_y = [-12.20, -12.05, -11.90, -11.75, -11.60, -11.45]
            ax.plot(costa_x, costa_y, color="#4A7A9C", linewidth=4.5, label="COSTA DEL PERÚ")
            ax.fill_betweenx(costa_y, costa_x, -76.80, color="#142230", alpha=0.85)

            ruta_x = [-77.11, -77.28, -77.42, -77.36, -77.25]
            ruta_y = [-12.02, -12.08, -11.92, -11.76, -11.65]
            ax.plot(ruta_x, ruta_y, color="#00E5FF", linewidth=5.5, linestyle="-", label="RUTA VUELO AEROPERÚ 603")
            ax.scatter([-77.11], [-12.02], color="#00FF88", s=240, zorder=5)
            ax.text(-77.08, -12.04, "1. DESPEGUE LIMA (00:40 AM)", color="#00FF88", fontweight="bold", fontsize=17)

            ax.scatter([-77.25], [-11.65], color="#FF2222", s=300, marker="X", zorder=6)
            ax.text(-77.22, -11.66, "2. IMPACTO EN EL MAR (01:11 AM)", color="#FF4444", fontweight="bold", fontsize=17)

            ax.set_title("TRAYECTORIA RADAR: SALIDA DE LIMA Y GIRO AL PACÍFICO", color="#FFFFFF", fontsize=24, fontweight="bold", pad=22)
            ax.set_xlabel("LONGITUD OESTE", color="#B0C4DE", fontsize=16, fontweight="bold")
            ax.set_ylabel("LATITUD SUR", color="#B0C4DE", fontsize=16, fontweight="bold")
            ax.set_xlim(-77.52, -76.88)
            ax.set_ylim(-12.18, -11.48)
            ax.grid(True, color="#1C2D42", linestyle="--", linewidth=1.2)
            ax.tick_params(colors="#FFFFFF", labelsize=14)
            leg = ax.legend(loc="lower left", facecolor="#070B12", edgecolor="#2A3F5F", fontsize=16)
            for text in leg.get_texts():
                text.set_color("#FFFFFF")

        elif "CRONOLOGIA" in tipo:
            ax.axis("off")
            ax.set_title("CRONOLOGÍA OFICIAL (INFORME CIAA - 2 OCT 1996)", color="#FFFFFF", fontsize=25, fontweight="bold", pad=20)
            hitos = [
                ("00:40 AM", "DESPEGUE EN LIMA", "El Boeing 757 despega con los puertos estáticos tapados con cinta."),
                ("00:42 AM", "INSTRUMENTOS BLOQUEADOS", "A los 2 minutos, velocímetro y altímetro dejan de marcar datos reales."),
                ("00:44 AM", "EMERGENCIA DECLARADA", "Los pilotos piden vectores a Lima para regresar a la pista."),
                ("00:58 AM", "DATO FALSO (9700 PIES)", "El transpondedor envía la misma altitud congelada al radar de tierra."),
                ("01:11 AM", "IMPACTO EN EL OCÉANO", "El ala izquierda golpea el agua en la oscuridad a los 31 min de vuelo."),
            ]
            y_positions = [0.85, 0.67, 0.49, 0.31, 0.13]
            ax.plot([0.20, 0.20], [0.13, 0.85], color="#00E5FF", linewidth=5, transform=ax.transAxes)
            for (hora, titulo, detalle), y in zip(hitos, y_positions):
                color_punto = "#FF2A2A" if "IMPACTO" in titulo else "#FFAA00"
                ax.scatter([0.20], [y], color=color_punto, s=260, zorder=5, transform=ax.transAxes)
                ax.text(0.04, y, hora, color="#00E5FF", fontsize=20, fontweight="bold", va="center", transform=ax.transAxes)
                ax.text(0.24, y + 0.025, titulo, color="#FFFFFF", fontsize=20, fontweight="bold", va="center", transform=ax.transAxes)
                ax.text(0.24, y - 0.035, detalle, color="#C0D4EE", fontsize=16, va="center", transform=ax.transAxes)

        else:  # ESQUEMA_SENSORES (Con posiciones centradas 0.20, 0.50, 0.80 para no salirse jamás por los lados)
            ax.axis("off")
            ax.set_title("INFORME FORENSE: CÓMO LA CINTA ENGAÑÓ AL AVIÓN", color="#FFFFFF", fontsize=25, fontweight="bold", pad=20)
            bloques = [
                (0.19, "1. SENSOR TAPADO\nCON CINTA", "Bloquea la entrada\nde presión exterior", "#FF3333"),
                (0.50, "2. COMPUTADORA\nCONGELADA", "Fija una altitud falsa\nde 9700 pies", "#FFAA00"),
                (0.81, "3. RADAR DE LIMA\nENGAÑADO", "Recibe el mismo dato\nfalso de 9700 pies", "#00E5FF"),
            ]
            for x, tit, desc, col in bloques:
                bbox = dict(boxstyle="round,pad=0.7", facecolor="#101C2E", edgecolor=col, linewidth=4)
                ax.text(
                    x, 0.55, f"{tit}\n\n{desc}",
                    color="#FFFFFF", fontsize=18, fontweight="bold",
                    ha="center", va="center", bbox=bbox, transform=ax.transAxes,
                )
            ax.annotate("", xy=(0.35, 0.55), xytext=(0.32, 0.55), arrowprops=dict(facecolor="#FFFFFF", width=4), transform=ax.transAxes)
            ax.annotate("", xy=(0.66, 0.55), xytext=(0.63, 0.55), arrowprops=dict(facecolor="#FFFFFF", width=4), transform=ax.transAxes)

        fig.savefig(ruta_salida, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        print(f"  📊 [Infografía 1080p] Generada con márgenes seguros: {tipo}")
        return _validar_imagen(ruta_salida)
    except Exception as e:
        print(f"  [Aviso] Falló infografía matplotlib ({e})...")
        return False


def _sanitizar_prompt_estricto(prompt: str) -> str:
    """Elimina cualquier término que pueda generar caras humanas, iPads, libretas o texto."""
    limpio = re.sub(
        r"\b(face|faces|portrait|man|men|woman|women|person|people|pilot|pilots|mechanic|technician|passenger|passengers|human|head|eyes|ipad|tablet|screen|monitor|pad|document|paper|book|notebook|text|words|letters|labels|sign|logo|numbers|arrows)\b",
        "",
        prompt,
        flags=re.IGNORECASE,
    )
    if any(k in limpio.lower() for k in ("tape", "static", "port", "sensor")):
        limpio += ", glossy metallic silver-grey duct tape on smooth blank aircraft metal without any markings"
    return limpio.strip()


def _validar_imagen(ruta: str) -> bool:
    if not os.path.exists(ruta):
        return False
    if os.path.getsize(ruta) < TAMANO_MINIMO_BYTES:
        return False
    with open(ruta, "rb") as f:
        cabecera = f.read(8)
    return cabecera.startswith(b"\x89PNG") or cabecera.startswith(b"\xff\xd8\xff")


def _recortar_marca_agua_y_exponer(ruta: str, recortar_borde_inferior: bool = False):
    """
    Si viene de Pollinations, recorta el 6% inferior/derecho para eliminar la marca 'pollinations.ai'.
    Además, equilibra la exposición si la imagen es demasiado oscura.
    """
    try:
        import numpy as np
        from PIL import Image, ImageEnhance

        img = Image.open(ruta).convert("RGB")
        w, h = img.size
        if recortar_borde_inferior:
            img = img.crop((int(w * 0.03), int(h * 0.03), int(w * 0.94), int(h * 0.92))).resize((1920, 1080), Image.Resampling.LANCZOS)

        arr = np.array(img, dtype=np.float32)
        brillo_medio = float(arr.mean())
        if brillo_medio < 62.0:
            gamma = 0.62 if brillo_medio < 38.0 else 0.74
            arr_norm = np.clip(arr / 255.0, 0.0, 1.0)
            arr_gamma = np.power(arr_norm, gamma) * 255.0
            img = Image.fromarray(np.clip(arr_gamma, 0, 255).astype(np.uint8))
            img = ImageEnhance.Contrast(img).enhance(1.12)

        img.save(ruta, quality=95)
    except Exception:
        pass


def _evaluar_calidad_candidato(ruta: str) -> tuple:
    try:
        import pytesseract
        import numpy as np
        from PIL import Image, ImageEnhance

        img_rgb = Image.open(ruta).convert("RGB")
        arr = np.array(img_rgb, dtype=np.float32)
        brillo = float(arr.mean())
        contraste = float(arr.std())

        img_gris = img_rgb.convert("L")
        img_contraste = ImageEnhance.Contrast(img_gris).enhance(2.2)
        datos = pytesseract.image_to_data(img_contraste, config="--psm 11", output_type=pytesseract.Output.DICT)

        palabras_basura = []
        for i, texto in enumerate(datos["text"]):
            solo_alfanum = re.sub(r"[^A-Za-z0-9]", "", texto.strip())
            conf = int(datos["conf"][i]) if str(datos["conf"][i]).lstrip("-").isdigit() else 0
            if len(solo_alfanum) >= 3 and conf > 45:
                palabras_basura.append(solo_alfanum)

        if len(palabras_basura) >= 1:
            print(f"  ⚠️ [QA/OCR] Descartado por texto detectado ({palabras_basura[:2]}).")
            return (False, 0.0)

        puntuacion = contraste - abs(brillo - 100.0) * 0.4
        return (True, puntuacion)
    except Exception:
        return (True, 50.0)


def _descargar_candidato_cf(prompt_completo: str, ruta_destino: str) -> bool:
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
                with open(ruta_destino, "wb") as f:
                    f.write(base64.b64decode(b64_img))
                if _validar_imagen(ruta_destino):
                    _recortar_marca_agua_y_exponer(ruta_destino, recortar_borde_inferior=False)
                    return True
        if resp.status_code == 429:
            _cloudflare_agotado[0] = True
    except requests.RequestException:
        pass
    return False


def _descargar_candidato_pol(prompt_completo: str, ruta_destino: str, semilla: int) -> bool:
    try:
        prompt_url = urllib.parse.quote(prompt_completo)
        url = f"https://image.pollinations.ai/prompt/{prompt_url}?width=1280&height=720&seed={semilla}&model=flux&nologo=true"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        if resp.status_code == 200:
            with open(ruta_destino, "wb") as f:
                f.write(resp.content)
            if _validar_imagen(ruta_destino):
                # Recorta siempre el borde inferior de Pollinations para eliminar el logo 'pollinations.ai'
                _recortar_marca_agua_y_exponer(ruta_destino, recortar_borde_inferior=True)
                return True
    except Exception:
        pass
    return False


def fue_ultima_generacion_emergencia() -> bool:
    return _ultima_fue_emergencia[0]


def generar_imagen(prompt_escena: str, ruta_salida: str, semilla: int = None) -> bool:
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    _ultima_fue_emergencia[0] = False

    # 1. Si es una de las 4 infografías de datos reales, renderizarla con código y márgenes seguros
    if prompt_escena.startswith("INFOGRAFIA:"):
        if _generar_infografia_codigo(prompt_escena, ruta_salida):
            return True

    sujeto = _sanitizar_prompt_estricto(prompt_escena)
    prompt_completo = f"{sujeto}, {ESTILO_BASE}"
    seed_base = semilla if semilla is not None else abs(hash(prompt_escena)) % 10000

    # 2. Evaluar candidatos limpios (PROHIBIDO usar ImageOps.mirror ni reciclar infografías)
    mejores_candidatos = []
    for i in range(4):
        ruta_cand = f"{ruta_salida}_cand_{i}.png"
        descargado = False
        if i < 2:
            descargado = _descargar_candidato_cf(prompt_completo, ruta_cand)
        if not descargado:
            descargado = _descargar_candidato_pol(prompt_completo, ruta_cand, seed_base + i * 71)

        if descargado:
            es_valida, score = _evaluar_calidad_candidato(ruta_cand)
            if es_valida:
                mejores_candidatos.append((score, ruta_cand))
                if len(mejores_candidatos) >= 2:
                    break
            else:
                if os.path.exists(ruta_cand):
                    os.remove(ruta_cand)
        time.sleep(1.0)

    if mejores_candidatos:
        mejores_candidatos.sort(key=lambda x: x[0], reverse=True)
        mejor_ruta = mejores_candidatos[0][1]
        os.replace(mejor_ruta, ruta_salida)
        for _, r_temp in mejores_candidatos[1:]:
            if os.path.exists(r_temp):
                os.remove(r_temp)
        return True

    # 3. Si los 4 candidatos tenían texto, pedir un plano limpio de nubes/océano sin letras (NUNCA espejo)
    prompt_ultra_limpio = (
        "Wide shot of dark storm clouds and lightning over the ocean at night seen from an airplane wing, "
        "photorealistic, 8k, completely empty sky and water, no text, no objects"
    )
    if _descargar_candidato_pol(prompt_ultra_limpio, ruta_salida, seed_base + 999):
        return True
    return _generar_infografia_codigo("INFOGRAFIA:CRONOLOGIA", ruta_salida)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(0 if generar_imagen(sys.argv[1], sys.argv[2]) else 1)
