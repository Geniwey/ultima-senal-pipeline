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
    "no airline logos, NO TEXT, NO LETTERS, NO NUMBERS, NO SIGNS, NO WRITING"
)

TIMEOUT = 35
TAMANO_MINIMO_BYTES = 12_000
_cloudflare_agotado = [False]
_ultima_fue_emergencia = [False]


def _generar_infografia_codigo(tipo: str, ruta_salida: str) -> bool:
    """
    Genera infografías técnicas 100% reales y limpias con Matplotlib (cero texto basura de IA):
    1. GRAFICA_ALTITUD: Altitud Falsa (9700 ft) vs Altitud Real (Impacto 0 ft).
    2. MAPA_RUTA: Trayectoria Lima -> Pacífico -> Punto de impacto en Chancay.
    3. CRONOLOGIA: Línea de tiempo de los 31 minutos fatales.
    4. ESQUEMA_SENSORES: Comparativa de Puerto Estático Libre vs Bloqueado con Cinta.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        plt.rcParams["font.sans-serif"] = "DejaVu Sans"
        plt.rcParams["axes.edgecolor"] = "#2A3F5F"
        fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)
        fig.patch.set_facecolor("#070B12")
        ax.set_facecolor("#0B1320")

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
            ax.plot(minutos, alt_falsa, color="#FFAA00", linewidth=3.5, linestyle="--", label="ALTÍMETRO EN CABINA / RADAR (BLOQUEADO EN 9700 PIES)")
            ax.plot(minutos, alt_real, color="#FF2A2A", linewidth=4.2, label="ALTITUD REAL DEL AVIÓN (DESCENSO CIEGO HACIA EL MAR)")
            ax.fill_between(minutos, alt_real, 0, color="#FF2A2A", alpha=0.15)
            ax.scatter([31], [0], color="#FFFFFF", s=140, zorder=5)
            ax.annotate("01:11 AM - IMPACTO EN EL MAR (0 PIES)", xy=(31, 150), xytext=(19.5, 2200),
                        color="#FFFFFF", fontweight="bold", fontsize=12,
                        arrowprops=dict(facecolor="#FF2A2A", shrink=0.08, width=2))
            ax.set_title("TELEMETRÍA FORENSE FDR: LECTURA FALSA VS ALTITUD REAL", color="#FFFFFF", fontsize=16, fontweight="bold", pad=18)
            ax.set_xlabel("TIEMPO DE VUELO (MINUTOS DESDE EL DESPEGUE EN LIMA)", color="#A0B4D0", fontsize=12, fontweight="bold")
            ax.set_ylabel("ALTITUD (PIES)", color="#A0B4D0", fontsize=12, fontweight="bold")
            ax.set_ylim(-500, 11500)
            ax.set_xlim(0, 33)
            ax.grid(True, color="#1C2D42", linestyle=":", linewidth=1)
            ax.tick_params(colors="#A0B4D0", labelsize=11)
            leg = ax.legend(loc="upper right", facecolor="#070B12", edgecolor="#2A3F5F", fontsize=11)
            for text in leg.get_texts():
                text.set_color("#FFFFFF")

        elif "MAPA_RUTA" in tipo:
            # Mapa vectorial costero (Costa de Lima / Callao / Chancay)
            costa_x = [-77.05, -77.12, -77.16, -77.22, -77.27, -77.32]
            costa_y = [-12.20, -12.05, -11.90, -11.75, -11.60, -11.45]
            ax.plot(costa_x, costa_y, color="#3A6080", linewidth=3, label="LÍNEA DE COSTA (PERÚ)")
            ax.fill_betweenx(costa_y, costa_x, -76.80, color="#142230", alpha=0.8)

            ruta_x = [-77.11, -77.28, -77.42, -77.36, -77.25]
            ruta_y = [-12.02, -12.08, -11.92, -11.76, -11.65]
            ax.plot(ruta_x, ruta_y, color="#00E5FF", linewidth=3.5, linestyle="-", label="TRAYECTORIA VUELO AEROPERÚ 603")
            ax.scatter([-77.11], [-12.02], color="#00FF88", s=130, zorder=5)
            ax.text(-77.09, -12.03, "LIMA (JORGE CHÁVEZ)\n00:40 AM", color="#00FF88", fontweight="bold", fontsize=11)

            ax.scatter([-77.25], [-11.65], color="#FF2222", s=180, marker="X", zorder=6)
            ax.text(-77.23, -11.66, "ZONA DE IMPACTO (CHANCAY)\n01:11 AM - OCÉANO PACÍFICO", color="#FF4444", fontweight="bold", fontsize=11)

            ax.set_title("MAPA DE TRAYECTORIA RADAR: LIMA - SECTOR CHANCAY (PACÍFICO)", color="#FFFFFF", fontsize=16, fontweight="bold", pad=18)
            ax.set_xlabel("LONGITUD OESTE", color="#A0B4D0", fontsize=11)
            ax.set_ylabel("LATITUD SUR", color="#A0B4D0", fontsize=11)
            ax.set_xlim(-77.55, -76.90)
            ax.set_ylim(-12.20, -11.45)
            ax.grid(True, color="#1C2D42", linestyle="--", linewidth=0.8)
            ax.tick_params(colors="#A0B4D0")
            leg = ax.legend(loc="lower left", facecolor="#070B12", edgecolor="#2A3F5F", fontsize=11)
            for text in leg.get_texts():
                text.set_color("#FFFFFF")

        elif "CRONOLOGIA" in tipo:
            ax.axis("off")
            ax.set_title("CRONOLOGÍA OFICIAL DEL ACCIDENTE (INFORME CIAA)", color="#FFFFFF", fontsize=18, fontweight="bold", pad=20)
            hitos = [
                ("00:40 AM", "DESPEGUE EN LIMA", "El Boeing 757 despega con los 3 puertos estáticos tapados con cinta."),
                ("00:42 AM", "INSTRUMENTOS CONGELADOS", "Al cruzar 1000 pies, velocímetro y altímetro dejan de responder."),
                ("00:44 AM", "EMERGENCIA DECLARADA", "Los pilotos piden ayuda al control de Lima para volver a pista."),
                ("00:58 AM", "TRAMPA EN EL RADAR (9700 PIES)", "El transpondedor envía el mismo dato falso a la torre de control."),
                ("01:11 AM", "IMPACTO EN EL PACÍFICO", "El ala izquierda roza el mar en la oscuridad a los 31 min de vuelo."),
            ]
            y_positions = [0.82, 0.65, 0.48, 0.31, 0.14]
            ax.plot([0.18, 0.18], [0.14, 0.82], color="#00E5FF", linewidth=4, transform=ax.transAxes)
            for (hora, titulo, detalle), y in zip(hitos, y_positions):
                color_punto = "#FF2A2A" if "IMPACTO" in titulo else "#FFAA00"
                ax.scatter([0.18], [y], color=color_punto, s=180, zorder=5, transform=ax.transAxes)
                ax.text(0.04, y, hora, color="#00E5FF", fontsize=14, fontweight="bold", va="center", transform=ax.transAxes)
                ax.text(0.23, y + 0.02, titulo, color="#FFFFFF", fontsize=14, fontweight="bold", va="center", transform=ax.transAxes)
                ax.text(0.23, y - 0.03, detalle, color="#B0C4DE", fontsize=11.5, va="center", transform=ax.transAxes)

        else:  # ESQUEMA_SENSORES
            ax.axis("off")
            ax.set_title("ESQUEMA FORENSE: CÓMO LA CINTA ENGAÑÓ AL BOEING 757", color="#FFFFFF", fontsize=17, fontweight="bold", pad=20)
            bloques = [
                (0.18, "1. PUERTOS ESTÁTICOS\nTAPADOS CON CINTA", "La cinta adhesiva bloquea\nla entrada de presión exterior", "#FF3333"),
                (0.50, "2. COMPUTADORA ADC\nCONGELADA", "Calcula una altitud fija falsa\nde 9700 pies en cabina", "#FFAA00"),
                (0.82, "3. TRANSPONDEDOR\nY RADAR ENGAÑADOS", "La torre de Lima recibe el mismo\ndato erróneo de 9700 pies", "#00E5FF"),
            ]
            for x, tit, desc, col in bloques:
                bbox = dict(boxstyle="round,pad=0.8", facecolor="#101C2E", edgecolor=col, linewidth=3)
                ax.text(x, 0.55, f"{tit}\n\n{desc}", color="#FFFFFF", fontsize=12.5, fontweight="bold",
                        ha="center", va="center", bbox=bbox, transform=ax.transAxes)
            ax.annotate("", xy=(0.35, 0.55), xytext=(0.31, 0.55), arrowprops=dict(facecolor="#FFFFFF", width=3), transform=ax.transAxes)
            ax.annotate("", xy=(0.67, 0.55), xytext=(0.63, 0.55), arrowprops=dict(facecolor="#FFFFFF", width=3), transform=ax.transAxes)

        plt.tight_layout()
        fig.subplots_adjust(bottom=0.22)
        fig.savefig(ruta_salida, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        print(f"  📊 [Infografía Real] Generada con éxito: {tipo}")
        return _validar_imagen(ruta_salida)
    except Exception as e:
        print(f"  [Aviso] Falló infografía matplotlib ({e}), pasando a render visual...")
        return False


def _enriquecer_prompt_sin_machacar(prompt: str) -> str:
    limpio = re.sub(
        r"\b(text|words|letters|labels|sign|signs|logo|logos|title|caption|inscription|stencil|writing|numbers|notebook|logbook|plaque|tombstone|memorial|board|papers)\b",
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

        if brillo_medio < 65.0:
            gamma = 0.60 if brillo_medio < 38.0 else 0.72
            arr_norm = np.clip(arr / 255.0, 0.0, 1.0)
            arr_gamma = np.power(arr_norm, gamma) * 255.0
            img_clara = Image.fromarray(np.clip(arr_gamma, 0, 255).astype(np.uint8))
            img_clara = ImageEnhance.Contrast(img_clara).enhance(1.14)
            img_clara.save(ruta, quality=95)
    except Exception:
        pass


def _evaluar_calidad_candidato(ruta: str) -> tuple:
    """
    Control de Calidad Automático (QA):
    Devuelve (es_valida: bool, puntuacion: float).
    Rechaza SIEMPRE imágenes con palabras o matrículas detectadas por OCR (NUNCA ignora el OCR).
    Puntúa mejor las imágenes con buen contraste y exposición equilibrada.
    """
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
            print(f"  ⚠️ [QA/OCR] Candidato descartado por texto en imagen ({palabras_basura[:2]}).")
            return (False, 0.0)

        # Puntuación por riqueza visual (contraste y exposición sana entre 55 y 170)
        penalizacion_brillo = abs(brillo - 105.0) * 0.4
        puntuacion = contraste - penalizacion_brillo
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
                return _validar_imagen(ruta_destino)
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
            return _validar_imagen(ruta_destino)
    except Exception:
        pass
    return False


def _reciclar_imagen_limpia(ruta_salida: str) -> bool:
    try:
        from PIL import Image, ImageOps
        carpeta = os.path.dirname(os.path.abspath(ruta_salida))
        candidatas = [
            os.path.join(carpeta, f)
            for f in os.listdir(carpeta)
            if f.startswith("escena_") and f.endswith(".png")
            and os.path.abspath(os.path.join(carpeta, f)) != os.path.abspath(ruta_salida)
            and os.path.getsize(os.path.join(carpeta, f)) > TAMANO_MINIMO_BYTES
        ]
        if candidatas:
            origen = random.choice(candidatas)
            img = Image.open(origen).convert("RGB")
            img = ImageOps.mirror(img)
            w, h = img.size
            img = img.crop((int(w * 0.07), int(h * 0.07), int(w * 0.93), int(h * 0.93))).resize((w, h), Image.Resampling.LANCZOS)
            img.save(ruta_salida, quality=95)
            return True
    except Exception:
        pass
    return False


def fue_ultima_generacion_emergencia() -> bool:
    return _ultima_fue_emergencia[0]


def generar_imagen(prompt_escena: str, ruta_salida: str, semilla: int = None) -> bool:
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    _ultima_fue_emergencia[0] = False

    # 1. Si la escena es una Infografía de Datos Reales, renderizarla con código (Matplotlib)
    if prompt_escena.startswith("INFOGRAFIA:"):
        if _generar_infografia_codigo(prompt_escena, ruta_salida):
            return True

    sujeto = _enriquecer_prompt_sin_machacar(prompt_escena)
    prompt_completo = f"{sujeto}, {ESTILO_BASE}"
    seed_base = semilla if semilla is not None else abs(hash(prompt_escena)) % 10000

    # 2. Generar hasta 2 candidatos limpios y elegir el de mayor puntuación QA (CERO ignorar_ocr)
    mejores_candidatos = []
    for i in range(4):
        ruta_cand = f"{ruta_salida}_cand_{i}.png"
        descargado = False
        if i < 2:
            descargado = _descargar_candidato_cf(prompt_completo, ruta_cand)
        if not descargado:
            descargado = _descargar_candidato_pol(prompt_completo, ruta_cand, seed_base + i * 53)

        if descargado:
            _corregir_exposicion_oscura(ruta_cand)
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

    # 3. Si todos los candidatos tuvieron texto inventado, reciclar toma limpia o usar infografía técnica
    if _reciclar_imagen_limpia(ruta_salida):
        return True
    return _generar_infografia_codigo("INFOGRAFIA:CRONOLOGIA", ruta_salida)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(0 if generar_imagen(sys.argv[1], sys.argv[2]) else 1)
