import os
import sys
import time
import base64
import requests
import urllib.parse
import re

ESTILO_BASE = (
    "cinematic documentary photography, photorealistic, high detail, sharp focus, "
    "completely blank unmarked smooth surfaces, NO PEOPLE, NO FACES, "
    "ABSOLUTELY NO TEXT, NO LETTERS, NO NUMBERS, NO SERIAL NUMBERS, NO LOGOS, NO WATERMARKS"
)

TIMEOUT = 35
TAMANO_MINIMO_BYTES = 12_000
_cloudflare_agotado = [False]
_ultima_fue_emergencia = [False]
_hashes_usados = []


def fue_ultima_generacion_emergencia() -> bool:
    return _ultima_fue_emergencia[0]


def _generar_infografia_codigo(tipo: str, ruta_salida: str) -> bool:
    """
    Biblioteca de 8 infografías y tarjetas de telemetría 1920x1080 renderizadas por código.
    Márgenes seguros para no solapar jamás el rótulo inferior ni cortarse por los bordes.
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
        fig.subplots_adjust(left=0.11, right=0.92, top=0.84, bottom=0.22)

        if "TARJETA_VUELO" in tipo:
            ax.axis("off")
            ax.set_title("EXPEDIENTE TÉCNICO: VUELO AEROPERÚ 603", color="#00E5FF", fontsize=25, fontweight="bold", pad=20)
            tarjetas = [
                (0.20, "AERONAVE", "BOEING 757-200\nMatrícula N52AW", "#00E5FF"),
                (0.50, "OCUPANTES", "70 PERSONAS\n61 Pasajeros · 9 Tripulantes", "#FFAA00"),
                (0.80, "RUTA Y FECHA", "LIMA → SANTIAGO\n2 de Octubre de 1996", "#FF3333"),
            ]
            for x, tit, val, col in tarjetas:
                bbox = dict(boxstyle="round,pad=0.8", facecolor="#101C2E", edgecolor=col, linewidth=4)
                ax.text(x, 0.56, f"{tit}\n\n{val}", color="#FFFFFF", fontsize=20, fontweight="bold", ha="center", va="center", bbox=bbox, transform=ax.transAxes)

        elif "ESQUEMA_SENSORES" in tipo:
            ax.axis("off")
            ax.set_title("INFORME FORENSE: CÓMO LA CINTA ENGAÑÓ AL AVIÓN", color="#FFFFFF", fontsize=25, fontweight="bold", pad=20)
            bloques = [
                (0.19, "1. SENSOR TAPADO\nCON CINTA", "Bloquea la presión\natmosférica real", "#FF3333"),
                (0.50, "2. COMPUTADORA\nCONGELADA", "Calcula una altitud\nfalsa de 9700 pies", "#FFAA00"),
                (0.81, "3. RADAR DE LIMA\nENGAÑADO", "Recibe el dato falso\ndel transpondedor", "#00E5FF"),
            ]
            for x, tit, desc, col in bloques:
                bbox = dict(boxstyle="round,pad=0.7", facecolor="#101C2E", edgecolor=col, linewidth=4)
                ax.text(x, 0.55, f"{tit}\n\n{desc}", color="#FFFFFF", fontsize=18, fontweight="bold", ha="center", va="center", bbox=bbox, transform=ax.transAxes)
            ax.annotate("", xy=(0.35, 0.55), xytext=(0.32, 0.55), arrowprops=dict(facecolor="#FFFFFF", width=4), transform=ax.transAxes)
            ax.annotate("", xy=(0.66, 0.55), xytext=(0.63, 0.55), arrowprops=dict(facecolor="#FFFFFF", width=4), transform=ax.transAxes)

        elif "MAPA_RUTA" in tipo:
            costa_x = [-77.05, -77.12, -77.16, -77.22, -77.27, -77.32]
            costa_y = [-12.20, -12.05, -11.90, -11.75, -11.60, -11.45]
            ax.plot(costa_x, costa_y, color="#4A7A9C", linewidth=4.5, label="COSTA DEL PERÚ")
            ax.fill_betweenx(costa_y, costa_x, -76.80, color="#142230", alpha=0.85)
            ruta_x = [-77.11, -77.28, -77.42, -77.36, -77.25]
            ruta_y = [-12.02, -12.08, -11.92, -11.76, -11.65]
            ax.plot(ruta_x, ruta_y, color="#00E5FF", linewidth=5.5, label="TRAYECTORIA VUELO 603")
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
            for t in leg.get_texts():
                t.set_color("#FFFFFF")

        elif "PANEL_ALARMAS" in tipo:
            ax.axis("off")
            ax.set_title("CABINA DE MANDO: CONFLICTO DE ALERTAS SIMULTÁNEAS", color="#FFAA00", fontsize=25, fontweight="bold", pad=20)
            paneles = [
                (0.28, "ALARMA DE PÉRDIDA\n(STICK SHAKER)", "Indica velocidad\ndemasiado BAJA", "#FF3333"),
                (0.72, "ALARMA EXCESO VELOCIDAD\n(OVERSPEED)", "Indica velocidad\ndemasiado ALTA", "#00E5FF"),
            ]
            for x, tit, desc, col in paneles:
                bbox = dict(boxstyle="round,pad=0.8", facecolor="#101C2E", edgecolor=col, linewidth=4)
                ax.text(x, 0.56, f"{tit}\n\n{desc}", color="#FFFFFF", fontsize=20, fontweight="bold", ha="center", va="center", bbox=bbox, transform=ax.transAxes)
            ax.text(0.50, 0.56, "VS", color="#FFAA00", fontsize=30, fontweight="bold", ha="center", va="center", transform=ax.transAxes)

        elif "GRAFICA_ALTITUD" in tipo:
            minutos = np.linspace(0, 31, 200)
            alt_falsa = np.piecewise(minutos, [minutos < 6, minutos >= 6], [lambda t: (t / 6.0) * 9700, 9700])
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
            ax.annotate("01:11 AM - IMPACTO (0 PIES)", xy=(30.8, 200), xytext=(16.5, 2600), color="#FFFFFF", fontweight="bold", fontsize=18, arrowprops=dict(facecolor="#FF2A2A", shrink=0.08, width=3))
            ax.set_title("DATOS CAJA NEGRA (FDR): ALTITUD FALSA VS REAL", color="#FFFFFF", fontsize=24, fontweight="bold", pad=22)
            ax.set_xlabel("MINUTOS DE VUELO DESDE LIMA", color="#B0C4DE", fontsize=17, fontweight="bold", labelpad=12)
            ax.set_ylabel("ALTITUD (PIES)", color="#B0C4DE", fontsize=17, fontweight="bold", labelpad=12)
            ax.set_ylim(-600, 12200)
            ax.set_xlim(0, 34)
            ax.grid(True, color="#1C2D42", linestyle=":", linewidth=1.5)
            ax.tick_params(colors="#FFFFFF", labelsize=15)
            leg = ax.legend(loc="upper left", facecolor="#070B12", edgecolor="#2A3F5F", fontsize=16)
            for t in leg.get_texts():
                t.set_color("#FFFFFF")

        elif "PERFIL_IMPACTO" in tipo:
            ax.axis("off")
            ax.set_title("ÚLTIMOS 60 SEGUNDOS: EL ENGAÑO DEL ALTÍMETRO", color="#FF3333", fontsize=25, fontweight="bold", pad=20)
            datos_impacto = [
                (0.22, "ALTITUD EN PANTALLA", "9.700 PIES", "Los pilotos creían tener margen seguro", "#FFAA00"),
                (0.50, "ALTITUD REAL", "0 PIES", "El ala izquierda tocó las olas a oscuras", "#FF3333"),
                (0.78, "TIEMPO TOTAL", "31 MINUTOS", "Desde el despegue hasta el impacto", "#00E5FF"),
            ]
            for x, tit, cifra, sub, col in datos_impacto:
                bbox = dict(boxstyle="round,pad=0.8", facecolor="#101C2E", edgecolor=col, linewidth=4)
                ax.text(x, 0.56, f"{tit}\n\n{cifra}\n\n{sub}", color="#FFFFFF", fontsize=18, fontweight="bold", ha="center", va="center", bbox=bbox, transform=ax.transAxes)

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

        else:  # CAMBIOS_NORMATIVA
            ax.axis("off")
            ax.set_title("CAMBIOS OBLIGATORIOS TRAS EL ACCIDENTE (OACI)", color="#00FF88", fontsize=25, fontweight="bold", pad=20)
            medidas = [
                (0.20, "1. CINTAS DE ALTA\nVISIBILIDAD", "Prohibido usar cinta\nplateada camuflada", "#00FF88"),
                (0.50, "2. BANDERINES\nCOLGANTES", "Señalización física\nvisible desde tierra", "#00E5FF"),
                (0.80, "3. DOBLE FIRMA\nDE INSPECCIÓN", "Verificación cruzada\nantes de cada vuelo", "#FFAA00"),
            ]
            for x, tit, desc, col in medidas:
                bbox = dict(boxstyle="round,pad=0.8", facecolor="#101C2E", edgecolor=col, linewidth=4)
                ax.text(x, 0.56, f"{tit}\n\n{desc}", color="#FFFFFF", fontsize=18, fontweight="bold", ha="center", va="center", bbox=bbox, transform=ax.transAxes)

        fig.savefig(ruta_salida, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        print(f"  📊 [Infografía 1080p] Generada: {tipo}")
        return _validar_imagen(ruta_salida)
    except Exception as e:
        print(f"  [Aviso] Falló infografía ({e})")
        return False


def _validar_imagen(ruta: str) -> bool:
    if not os.path.exists(ruta) or os.path.getsize(ruta) < TAMANO_MINIMO_BYTES:
        return False
    with open(ruta, "rb") as f:
        cabecera = f.read(8)
        return cabecera.startswith(b"\x89PNG") or cabecera.startswith(b"\xff\xd8\xff")


def _recortar_marca_agua_y_exponer(ruta: str, recortar_borde: bool = False):
    try:
        import numpy as np
        from PIL import Image, ImageEnhance
        img = Image.open(ruta).convert("RGB")
        w, h = img.size
        if recortar_borde:
            img = img.crop((int(w * 0.03), int(h * 0.03), int(w * 0.94), int(h * 0.92))).resize((1920, 1080), Image.Resampling.LANCZOS)
        arr = np.array(img, dtype=np.float32)
        if float(arr.mean()) < 58.0:
            gamma = 0.65 if float(arr.mean()) < 36.0 else 0.76
            img = Image.fromarray(np.clip(np.power(np.clip(arr / 255.0, 0.0, 1.0), gamma) * 255.0, 0, 255).astype(np.uint8))
            img = ImageEnhance.Contrast(img).enhance(1.12)
        img.save(ruta, quality=95)
    except Exception:
        pass


def _calcular_dhash(img_rgb) -> int:
    from PIL import Image
    gris = img_rgb.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pix = list(gris.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            if pix[row * 9 + col] > pix[row * 9 + col + 1]:
                bits |= 1 << (row * 8 + col)
    return bits


def _es_duplicada(dhash_val: int) -> bool:
    for h in _hashes_usados:
        if bin(dhash_val ^ h).count("1") <= 6:
            return True
    return False


def _evaluar_puerta_calidad(ruta: str, permitir_duplicado: bool = False) -> tuple:
    """
    Puerta de calidad en código:
    1. Rechaza imágenes vacías/abstractas (contraste < 28 o nitidez < 30).
    2. Rechaza imágenes quemadas en blanco (> 6% píxeles > 245).
    3. Rechaza texto/grabados basura mediante OCR de doble contraste (--psm 11).
    4. Rechaza duplicados mediante hash perceptual.
    """
    try:
        import numpy as np
        import pytesseract
        from PIL import Image, ImageEnhance, ImageFilter

        img_rgb = Image.open(ruta).convert("RGB")
        arr = np.array(img_rgb, dtype=np.float32)

        brillo = float(arr.mean())
        contraste = float(arr.std())
        pct_quemado = float((arr.mean(axis=2) > 245).mean())

        if contraste < 28.0 or brillo < 22.0 or pct_quemado > 0.06:
            print(f"  ⚠️ [Puerta Calidad] Rechazada por imagen vacía/quemada (std={contraste:.1f}, quemado={pct_quemado:.2f}).")
            return (False, 0.0)

        # Medir nitidez/estructura para matar círculos borrosos vacíos
        bordes = np.array(img_rgb.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)
        nitidez = float(bordes.std())
        if nitidez < 18.0:
            print(f"  ⚠️ [Puerta Calidad] Rechazada por falta de detalle/sujeto (nitidez={nitidez:.1f}).")
            return (False, 0.0)

        # OCR de doble pasada para cazar textos grabados en metal o cinta ("Reolscort", "N0770210", "STU GOINNE")
        img_gris = img_rgb.convert("L")
        for version in (img_gris, ImageEnhance.Contrast(img_gris).enhance(2.4)):
            datos = pytesseract.image_to_data(version, config="--psm 11", output_type=pytesseract.Output.DICT)
            for i, txt in enumerate(datos["text"]):
                limpio = re.sub(r"[^A-Za-z0-9]", "", txt.strip())
                conf = int(datos["conf"][i]) if str(datos["conf"][i]).lstrip("-").isdigit() else 0
                if len(limpio) >= 3 and conf > 40:
                    print(f"  ⚠️ [Puerta OCR] Rechazada por texto detectado: '{limpio}' (conf={conf}).")
                    return (False, 0.0)

        dhash_val = _calcular_dhash(img_rgb)
        if not permitir_duplicado and _es_duplicada(dhash_val):
            print("  ⚠️ [Puerta Duplicados] Rechazada por similitud visual excesiva.")
            return (False, 0.0)

        score = contraste + nitidez - pct_quemado * 200.0
        return (True, score)
    except Exception:
        return (True, 50.0)


def _descargar_candidato_cf(prompt_completo: str, ruta_destino: str) -> bool:
    if _cloudflare_agotado[0]:
        return False
    account_id = os.environ.get("CF_ACCOUNT_ID")
    api_token = os.environ.get("CF_API_TOKEN")
    if not account_id or not api_token:
        return False
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    try:
        resp = requests.post(url, headers={"Authorization": f"Bearer {api_token}"}, json={"prompt": prompt_completo, "steps": 8}, timeout=TIMEOUT)
        if resp.status_code == 200:
            b64 = resp.json().get("result", {}).get("image")
            if b64:
                with open(ruta_destino, "wb") as f:
                    f.write(base64.b64decode(b64))
                if _validar_imagen(ruta_destino):
                    _recortar_marca_agua_y_exponer(ruta_destino, False)
                    return True
        if resp.status_code == 429:
            _cloudflare_agotado[0] = True
    except Exception:
        pass
    return False


def _descargar_candidato_pol(prompt_completo: str, ruta_destino: str, semilla: int) -> bool:
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt_completo)}?width=1280&height=720&seed={semilla}&model=flux&nologo=true"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=TIMEOUT)
        if resp.status_code == 200:
            with open(ruta_destino, "wb") as f:
                f.write(resp.content)
            if _validar_imagen(ruta_destino):
                _recortar_marca_agua_y_exponer(ruta_destino, True)
                return True
    except Exception:
        pass
    return False


def generar_imagen(prompt_escena: str, ruta_salida: str, semilla: int = None, es_miniatura: bool = False) -> bool:
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    _ultima_fue_emergencia[0] = False

    if prompt_escena.startswith("INFOGRAFIA:"):
        return _generar_infografia_codigo(prompt_escena, ruta_salida)

    sujeto = re.sub(r"\b(text|words|letters|logo|airsa)\b", "", prompt_escena, flags=re.IGNORECASE).strip()
    prompt_completo = f"{sujeto}, {ESTILO_BASE}"
    seed_base = semilla if semilla is not None else abs(hash(prompt_escena)) % 10000

    # Evaluar hasta 4 candidatas (3 candidatas obligatorias para miniatura) y elegir la de mayor puntuación
    candidatas_validas = []
    max_intentos = 5 if es_miniatura else 4
    objetivo_candidatas = 3 if es_miniatura else 2

    for i in range(max_intentos):
        ruta_cand = f"{ruta_salida}_cand_{i}.png"
        descargado = _descargar_candidato_cf(prompt_completo, ruta_cand) if i < 2 else _descargar_candidato_pol(prompt_completo, ruta_cand, seed_base + i * 37)
        if descargado:
            es_valida, score = _evaluar_puerta_calidad(ruta_cand, permitir_duplicado=es_miniatura)
            if es_valida:
                candidatas_validas.append((score, ruta_cand))
                if len(candidatas_validas) >= objetivo_candidatas:
                    break
            else:
                if os.path.exists(ruta_cand):
                    os.remove(ruta_cand)
        time.sleep(0.9)

    if candidatas_validas:
        candidatas_validas.sort(key=lambda x: x[0], reverse=True)
        ganadora = candidatas_validas[0][1]
        if not es_miniatura:
            try:
                from PIL import Image
                _hashes_usados.append(_calcular_dhash(Image.open(ganadora).convert("RGB")))
            except Exception:
                pass
        os.replace(ganadora, ruta_salida)
        for _, sobrante in candidatas_validas[1:]:
            if os.path.exists(sobrante):
                os.remove(sobrante)
        return True

    # Fallback limpio garantizado
    _ultima_fue_emergencia[0] = True
    prompt_respaldo = "Wide shot of an unmarked commercial airliner flying above dark stormy ocean waves at night under moonlight, sharp detail, no text, no logos"
    if _descargar_candidato_pol(prompt_respaldo, ruta_salida, seed_base + 999):
        return True
    return _generar_infografia_codigo("INFOGRAFIA:CRONOLOGIA", ruta_salida)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(0 if generar_imagen(sys.argv[1], sys.argv[2]) else 1)
