import os
import sys
import base64
import shutil
import requests
import urllib.parse
import re

ESTILO_BASE = "cinematic documentary photography, photorealistic, sharp focus, smooth unmarked metallic surfaces, dramatic moody lighting, 8k"
TIMEOUT = 40
TAMANO_MINIMO_BYTES = 12_000
_agotado = {"cf_flux": False, "cf_sdxl": False, "hf": False, "pol": False}
_ultima_fue_emergencia = [False]
_hashes_usados = []
_aprobadas_por_plano = {}
_aprobadas_generales = []
_reutilizaciones = {}
_idx_banco = [0]
_urls_usadas = set()
_stats = {"generadas_ia": 0, "archivo_real": 0, "rechazadas_qa": 0, "reutilizadas_banco": 0, "infografias": 0}

QUERIES_ARCHIVO = {
    "cinta_puerto": "Boeing 757 fuselage static port",
    "cabina_pilotos": "Boeing 757 cockpit night instruments",
    "ala_nubes": "aircraft wing storm clouds night",
    "pista_lluvia": "airport runway night lights rain",
    "turbina": "jet engine turbofan blades close up",
    "mar_tormenta": "stormy ocean waves dark sea night",
    "barco_rescate": "coast guard ship night ocean",
    "caja_negra": "flight data recorder orange box",
    "hangar": "Boeing 757 maintenance hangar night",
    "avion_frontal": "Boeing 757 airliner clouds",
    "torre_noche": "airport control tower night fog",
    "general": "commercial airliner night sky",
}


def fue_ultima_generacion_emergencia() -> bool:
    return _ultima_fue_emergencia[0]


def obtener_estadisticas_imagenes() -> dict:
    return dict(_stats)


def obtener_mejor_imagen_plano(plano: str) -> str:
    for _, ruta in sorted(_aprobadas_por_plano.get(plano, []), key=lambda x: x[0], reverse=True):
        if os.path.exists(ruta):
            return ruta
    return ""


def _generar_infografia_codigo(tipo: str, ruta_salida: str) -> bool:
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
            ax.set_title("EXPEDIENTE TÉCNICO: VUELO AEROPERÚ 603", color="#00E5FF", fontsize=28, fontweight="bold", pad=22)
            for x, txt, col in [
                (0.18, "AERONAVE\n\nBOEING 757-200\nMatrícula N52AW", "#00E5FF"),
                (0.50, "OCUPANTES\n\n70 PERSONAS\n61 Pasajeros · 9 Tripul.", "#FFAA00"),
                (0.82, "RUTA Y FECHA\n\nLIMA → SANTIAGO\n2 Octubre 1996", "#FF3333"),
            ]:
                bbox = dict(boxstyle="round,pad=0.65", facecolor="#101C2E", edgecolor=col, linewidth=4)
                ax.text(x, 0.56, txt, color="#FFFFFF", fontsize=22, fontweight="bold", ha="center", va="center", bbox=bbox, transform=ax.transAxes)

        elif "ESQUEMA_SENSORES" in tipo:
            ax.axis("off")
            ax.set_title("INFORME FORENSE: CÓMO LA CINTA ENGAÑÓ AL AVIÓN", color="#FFFFFF", fontsize=28, fontweight="bold", pad=22)
            for x, txt, col in [
                (0.18, "1. SENSOR TAPADO\n\nBloquea presión\natmosférica real", "#FF3333"),
                (0.50, "2. COMPUTADORA\n\nCongela altitud en\n9.700 pies falsos", "#FFAA00"),
                (0.82, "3. RADAR DE LIMA\n\nRecibe lectura falsa\ndel transpondedor", "#00E5FF"),
            ]:
                bbox = dict(boxstyle="round,pad=0.65", facecolor="#101C2E", edgecolor=col, linewidth=4)
                ax.text(x, 0.56, txt, color="#FFFFFF", fontsize=22, fontweight="bold", ha="center", va="center", bbox=bbox, transform=ax.transAxes)
            ax.annotate("", xy=(0.35, 0.56), xytext=(0.31, 0.56), arrowprops=dict(facecolor="#FFFFFF", width=4), transform=ax.transAxes)
            ax.annotate("", xy=(0.67, 0.56), xytext=(0.63, 0.56), arrowprops=dict(facecolor="#FFFFFF", width=4), transform=ax.transAxes)

        elif "MAPA_RUTA" in tipo:
            cx, cy = [-77.05, -77.12, -77.16, -77.22, -77.27, -77.32], [-12.20, -12.05, -11.90, -11.75, -11.60, -11.45]
            ax.plot(cx, cy, color="#4A7A9C", linewidth=5.0, label="COSTA DEL PERÚ")
            ax.fill_betweenx(cy, cx, -76.80, color="#142230", alpha=0.85)
            rx, ry = [-77.11, -77.28, -77.42, -77.36, -77.25], [-12.02, -12.08, -11.92, -11.76, -11.65]
            ax.plot(rx, ry, color="#00E5FF", linewidth=6.0, label="TRAYECTORIA VUELO 603")
            ax.scatter([-77.11], [-12.02], color="#00FF88", s=280, zorder=5)
            ax.text(-77.08, -12.04, "1. DESPEGUE LIMA (00:40 AM)", color="#00FF88", fontweight="bold", fontsize=22)
            ax.scatter([-77.25], [-11.65], color="#FF2222", s=320, marker="X", zorder=6)
            ax.text(-77.22, -11.66, "2. IMPACTO EN EL MAR (01:11 AM)", color="#FF4444", fontweight="bold", fontsize=22)
            ax.set_title("TRAYECTORIA RADAR: SALIDA DE LIMA Y GIRO AL PACÍFICO", color="#FFFFFF", fontsize=27, fontweight="bold", pad=22)
            ax.set_xlabel("LONGITUD OESTE", color="#B0C4DE", fontsize=20, fontweight="bold")
            ax.set_ylabel("LATITUD SUR", color="#B0C4DE", fontsize=20, fontweight="bold")
            ax.set_xlim(-77.52, -76.88)
            ax.set_ylim(-12.18, -11.48)
            ax.grid(True, color="#1C2D42", linestyle="--", linewidth=1.2)
            ax.tick_params(colors="#FFFFFF", labelsize=18)
            leg = ax.legend(loc="lower left", facecolor="#070B12", edgecolor="#2A3F5F", fontsize=19)
            for t in leg.get_texts():
                t.set_color("#FFFFFF")

        elif "PANEL_ALARMAS" in tipo:
            ax.axis("off")
            ax.set_title("CABINA DE MANDO: CONFLICTO DE ALERTAS SIMULTÁNEAS", color="#FFAA00", fontsize=28, fontweight="bold", pad=22)
            for x, txt, col in [
                (0.26, "ALARMA DE PÉRDIDA\n(STICK SHAKER)\n\nIndica velocidad\ndemasiado BAJA", "#FF3333"),
                (0.74, "EXCESO VELOCIDAD\n(OVERSPEED)\n\nIndica velocidad\ndemasiado ALTA", "#00E5FF"),
            ]:
                bbox = dict(boxstyle="round,pad=0.7", facecolor="#101C2E", edgecolor=col, linewidth=4)
                ax.text(x, 0.56, txt, color="#FFFFFF", fontsize=23, fontweight="bold", ha="center", va="center", bbox=bbox, transform=ax.transAxes)
            ax.text(0.50, 0.56, "VS", color="#FFAA00", fontsize=34, fontweight="bold", ha="center", va="center", transform=ax.transAxes)

        elif "GRAFICA_ALTITUD" in tipo:
            m = np.linspace(0, 31, 200)
            alt_f = np.piecewise(m, [m < 6, m >= 6], [lambda t: (t / 6.0) * 9700, 9700])
            alt_r = np.piecewise(
                m, [m < 6, (m >= 6) & (m < 18), m >= 18],
                [lambda t: (t / 6.0) * 9700, lambda t: 9700 - ((t - 6.0) / 12.0) * 5200, lambda t: 4500 * (1.0 - ((t - 18.0) / 13.0) ** 1.4)],
            )
            ax.plot(m, alt_f, color="#FFAA00", linewidth=5.5, linestyle="--", label="LECTURA FALSA EN CABINA / RADAR (9700 PIES)")
            ax.plot(m, alt_r, color="#FF2A2A", linewidth=6.5, label="ALTITUD REAL DEL AVIÓN (DESCENSO AL MAR)")
            ax.fill_between(m, alt_r, 0, color="#FF2A2A", alpha=0.18)
            ax.scatter([31], [0], color="#FFFFFF", s=260, zorder=5)
            ax.annotate("01:11 AM - IMPACTO (0 PIES)", xy=(30.8, 200), xytext=(15.5, 2800), color="#FFFFFF", fontweight="bold", fontsize=22, arrowprops=dict(facecolor="#FF2A2A", shrink=0.08, width=3))
            ax.set_title("DATOS CAJA NEGRA (FDR): ALTITUD FALSA VS REAL", color="#FFFFFF", fontsize=27, fontweight="bold", pad=22)
            ax.set_xlabel("MINUTOS DE VUELO DESDE LIMA", color="#B0C4DE", fontsize=20, fontweight="bold", labelpad=12)
            ax.set_ylabel("ALTITUD (PIES)", color="#B0C4DE", fontsize=20, fontweight="bold", labelpad=12)
            ax.set_ylim(-600, 12500)
            ax.set_xlim(0, 34)
            ax.grid(True, color="#1C2D42", linestyle=":", linewidth=1.5)
            ax.tick_params(colors="#FFFFFF", labelsize=18)
            leg = ax.legend(loc="upper left", facecolor="#070B12", edgecolor="#2A3F5F", fontsize=19)
            for t in leg.get_texts():
                t.set_color("#FFFFFF")

        else:
            ax.axis("off")
            ax.set_title("CRONOLOGÍA OFICIAL (INFORME CIAA - 2 OCT 1996)", color="#FFFFFF", fontsize=27, fontweight="bold", pad=20)
            hitos = [
                ("00:40 AM", "DESPEGUE EN LIMA", "El Boeing 757 despega con los puertos estáticos tapados.", 0.85),
                ("00:42 AM", "INSTRUMENTOS BLOQUEADOS", "Velocímetro y altímetro dejan de marcar datos reales.", 0.67),
                ("00:44 AM", "EMERGENCIA DECLARADA", "Los pilotos piden vectores para regresar a Lima.", 0.49),
                ("00:58 AM", "DATO FALSO (9700 PIES)", "El transpondedor envía altitud congelada al radar.", 0.31),
                ("01:11 AM", "IMPACTO EN EL OCÉANO", "El ala izquierda golpea el agua tras 31 min de vuelo.", 0.13),
            ]
            ax.plot([0.21, 0.21], [0.13, 0.85], color="#00E5FF", linewidth=5, transform=ax.transAxes)
            for hora, tit, det, y in hitos:
                col_p = "#FF2A2A" if "IMPACTO" in tit else "#FFAA00"
                ax.scatter([0.21], [y], color=col_p, s=280, zorder=5, transform=ax.transAxes)
                ax.text(0.03, y, hora, color="#00E5FF", fontsize=22, fontweight="bold", va="center", transform=ax.transAxes)
                ax.text(0.25, y + 0.025, tit, color="#FFFFFF", fontsize=22, fontweight="bold", va="center", transform=ax.transAxes)
                ax.text(0.25, y - 0.035, det, color="#C0D4EE", fontsize=20, va="center", transform=ax.transAxes)

        fig.savefig(ruta_salida, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        _stats["infografias"] += 1
        print(f"  📊 [Infografía 1080p] Generada: {tipo}")
        return _validar_imagen(ruta_salida)
    except Exception as e:
        print(f"  [Aviso] Falló infografía ({e})")
        return False


def _validar_imagen(ruta: str) -> bool:
    if not os.path.exists(ruta) or os.path.getsize(ruta) < TAMANO_MINIMO_BYTES:
        return False
    with open(ruta, "rb") as f:
        cab = f.read(8)
        return cab.startswith(b"\x89PNG") or cab.startswith(b"\xff\xd8\xff")


def _normalizar_16_9(ruta: str, recortar_wm: bool = False, tono_doc: bool = False):
    try:
        import numpy as np
        from PIL import Image, ImageEnhance, ImageOps

        img = Image.open(ruta).convert("RGB")
        if recortar_wm:
            w, h = img.size
            img = img.crop((int(w * 0.02), int(h * 0.02), int(w * 0.95), int(h * 0.93)))
        img = ImageOps.fit(img, (1920, 1080), method=Image.Resampling.LANCZOS)
        arr = np.array(img, dtype=np.float32)
        if tono_doc:
            arr[:, :, 0] *= 0.62
            arr[:, :, 1] *= 0.72
            arr[:, :, 2] *= 0.88
            img = ImageEnhance.Contrast(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))).enhance(1.18)
        elif float(arr.mean()) < 52.0:
            gamma = 0.68 if float(arr.mean()) < 32.0 else 0.78
            arr_g = np.power(np.clip(arr / 255.0, 0.0, 1.0), gamma) * 255.0
            img = ImageEnhance.Contrast(Image.fromarray(np.clip(arr_g, 0, 255).astype(np.uint8))).enhance(1.10)
        img.save(ruta, quality=95)
    except Exception:
        pass


def _calcular_dhash(img_rgb) -> int:
    from PIL import Image
    pix = list(img_rgb.convert("L").resize((9, 8), Image.Resampling.LANCZOS).getdata())
    bits = 0
    for r in range(8):
        for c in range(8):
            if pix[r * 9 + c] > pix[r * 9 + c + 1]:
                bits |= 1 << (r * 8 + c)
    return bits


def _evaluar_calidad(ruta: str, permitir_dup: bool = False, es_mini: bool = False) -> tuple:
    import numpy as np
    import pytesseract
    from PIL import Image, ImageFilter, ImageOps

    img_rgb = Image.open(ruta).convert("RGB")
    arr = np.array(img_rgb, dtype=np.float32)
    brillo, contraste = float(arr.mean()), float(arr.std())
    pct_quemado = float((arr.mean(axis=2) > 245).mean())
    if brillo < 12.0 or brillo > 215.0 or contraste < 16.0:
        return (False, f"brillo/contraste ({brillo:.1f}/{contraste:.1f})")
    if es_mini and pct_quemado > 0.08:
        return (False, f"zona quemada ({pct_quemado:.2f})")

    nitidez = float(np.array(img_rgb.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32).std())
    if nitidez < 1.5:
        return (False, f"borrosa ({nitidez:.1f})")

    # Doble escaneo OCR (normal e invertido) para detectar texto blanco en cascos/fuselajes
    gris = img_rgb.resize((1024, 576), Image.Resampling.LANCZOS).convert("L")
    for variante in (gris, ImageOps.invert(gris)):
        datos = pytesseract.image_to_data(variante, config="--psm 11", output_type=pytesseract.Output.DICT)
        for txt, conf in zip(datos["text"], datos["conf"]):
            letras = re.sub(r"[^A-Za-z]", "", txt.strip())
            c_val = float(conf) if str(conf).lstrip("-").isdigit() else 0.0
            if len(letras) >= 3 and c_val >= 58.0:
                return (False, f"texto basura OCR: '{txt}'")

    dh = _calcular_dhash(img_rgb)
    if not permitir_dup and any(bin(dh ^ h).count("1") <= 6 for h in _hashes_usados):
        return (False, "imagen duplicada")
    return (True, contraste + nitidez * 2.5 - pct_quemado * 150.0)


def _descargar_cf(prompt: str, destino: str, modelo: str) -> bool:
    clave = "cf_flux" if "flux" in modelo else "cf_sdxl"
    if _agotado[clave]:
        return False
    acc, tok = os.environ.get("CF_ACCOUNT_ID"), os.environ.get("CF_API_TOKEN")
    if not acc or not tok:
        return False
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{modelo}"
    try:
        payload = {"prompt": prompt, "steps": 4} if clave == "cf_flux" else {"prompt": prompt}
        r = requests.post(url, headers={"Authorization": f"Bearer {tok}"}, json=payload, timeout=TIMEOUT)
        if r.status_code == 200:
            if "application/json" in r.headers.get("Content-Type", ""):
                b64 = r.json().get("result", {}).get("image")
                if b64:
                    open(destino, "wb").write(base64.b64decode(b64))
            else:
                open(destino, "wb").write(r.content)
            if _validar_imagen(destino):
                _normalizar_16_9(destino)
                return True
        elif r.status_code == 429:
            _agotado[clave] = True
    except Exception:
        pass
    return False


def _descargar_hf(prompt: str, destino: str) -> bool:
    if _agotado["hf"]:
        return False
    tok = os.environ.get("HF_TOKEN", "").strip()
    if not tok:
        return False
    url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {tok}"}, json={"inputs": prompt}, timeout=TIMEOUT)
        if r.status_code == 200:
            open(destino, "wb").write(r.content)
            if _validar_imagen(destino):
                _normalizar_16_9(destino)
                return True
        elif r.status_code in (402, 429):
            _agotado["hf"] = True
    except Exception:
        pass
    return False


def _descargar_pol(prompt: str, destino: str, semilla: int) -> bool:
    if _agotado["pol"]:
        return False
    key = os.environ.get("POLLINATIONS_API_KEY", "").strip()
    q = urllib.parse.quote(prompt)
    url = f"https://gen.pollinations.ai/image/{q}?model=flux&width=1280&height=720&seed={semilla}" if key else f"https://image.pollinations.ai/prompt/{q}?width=1280&height=720&seed={semilla}&model=flux&nologo=true"
    headers = {"Authorization": f"Bearer {key}", "User-Agent": "Mozilla/5.0"} if key else {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code == 200:
            open(destino, "wb").write(r.content)
            if _validar_imagen(destino):
                _normalizar_16_9(destino, recortar_wm=(not key))
                return True
        elif r.status_code in (401, 402, 429) and not key:
            _agotado["pol"] = True
    except Exception:
        pass
    return False


def _descargar_archivo(plano: str, destino: str, semilla: int) -> bool:
    query = QUERIES_ARCHIVO.get(plano, QUERIES_ARCHIVO["general"])
    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if pexels_key:
        try:
            rp = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": pexels_key}, params={"query": query, "orientation": "landscape", "per_page": 10}, timeout=20)
            fotos = rp.json().get("photos", []) if rp.status_code == 200 else []
            for f in fotos[semilla % max(1, len(fotos)):] + fotos[:semilla % max(1, len(fotos))]:
                u = f.get("src", {}).get("large2x")
                if u and u not in _urls_usadas:
                    ri = requests.get(u, timeout=25)
                    if ri.status_code == 200:
                        open(destino, "wb").write(ri.content)
                        if _validar_imagen(destino):
                            _normalizar_16_9(destino, tono_doc=True)
                            _urls_usadas.add(u)
                            _stats["archivo_real"] += 1
                            return True
        except Exception:
            pass

    headers = {"User-Agent": "UltimaSenalDocBot/1.0 (aviation documentary)"}
    params = {"action": "query", "generator": "search", "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6, "gsrlimit": 15, "prop": "imageinfo", "iiprop": "url|size", "iiurlwidth": 1280, "format": "json"}
    try:
        r = requests.get("https://commons.wikimedia.org/w/api.php", params=params, headers=headers, timeout=20)
        pages = list(r.json().get("query", {}).get("pages", {}).values()) if r.status_code == 200 else []
        if pages:
            off = semilla % len(pages)
            for p in pages[off:] + pages[:off]:
                info = (p.get("imageinfo") or [{}])[0]
                u = info.get("thumburl") or info.get("url")
                if u and info.get("width", 0) >= 800 and info.get("height", 0) >= 450 and u not in _urls_usadas:
                    ri = requests.get(u, headers=headers, timeout=25)
                    if ri.status_code == 200:
                        open(destino, "wb").write(ri.content)
                        if _validar_imagen(destino):
                            _normalizar_16_9(destino, tono_doc=True)
                            _urls_usadas.add(u)
                            _stats["archivo_real"] += 1
                            return True
    except Exception:
        pass
    return False


def generar_imagen(prompt_escena: str, ruta_salida: str, semilla: int = None, es_miniatura: bool = False, plano: str = "general") -> bool:
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    _ultima_fue_emergencia[0] = False
    if prompt_escena.startswith("INFOGRAFIA:"):
        return _generar_infografia_codigo(prompt_escena, ruta_salida)

    prompt_limpio = re.sub(r"\bno\s+\w+\b", "", prompt_escena, flags=re.IGNORECASE).strip(" ,.")
    prompt_completo = f"{prompt_limpio}, {ESTILO_BASE}"
    seed_base = semilla if semilla is not None else abs(hash(prompt_escena)) % 10000

    validas, objetivo = [], (3 if es_miniatura else 1)
    intentos = [("cf_flux", 0), ("cf_sdxl", 1), ("hf", 2), ("pol", seed_base + 11)] + ([("cf_flux_2", 3)] if es_miniatura else [])

    for i, (prov, s) in enumerate(intentos):
        cand = f"{ruta_salida}_cand_{i}.png"
        if prov.startswith("cf_flux"):
            ok = _descargar_cf(prompt_completo, cand, "@cf/black-forest-labs/flux-1-schnell")
        elif prov.startswith("cf_sdxl"):
            ok = _descargar_cf(prompt_completo, cand, "@cf/bytedance/stable-diffusion-xl-lightning")
        elif prov == "hf":
            ok = _descargar_hf(prompt_completo, cand)
        else:
            ok = _descargar_pol(prompt_completo, cand, s)

        if ok:
            es_val, info = _evaluar_calidad(cand, permitir_dup=es_miniatura, es_mini=es_miniatura)
            if es_val:
                validas.append((info, cand))
                if len(validas) >= objetivo:
                    break
            else:
                _stats["rechazadas_qa"] += 1
                print(f"  ⚠️ [QA] Descartada: {info}")
                if os.path.exists(cand):
                    os.remove(cand)

    if validas:
        validas.sort(key=lambda x: x[0], reverse=True)
        score, ganadora = validas[0]
        os.replace(ganadora, ruta_salida)
        for _, sob in validas[1:]:
            if os.path.exists(sob):
                os.remove(sob)
        if not es_miniatura:
            _stats["generadas_ia"] += 1
            from PIL import Image
            _hashes_usados.append(_calcular_dhash(Image.open(ruta_salida).convert("RGB")))
            _aprobadas_por_plano.setdefault(plano, []).append((score, ruta_salida))
            if plano != "cinta_puerto":
                _aprobadas_generales.append(ruta_salida)
        return True

    if not es_miniatura and _descargar_archivo(plano, ruta_salida, seed_base):
        _aprobadas_por_plano.setdefault(plano, []).append((40.0, ruta_salida))
        if plano != "cinta_puerto":
            _aprobadas_generales.append(ruta_salida)
        return True

    _ultima_fue_emergencia[0] = True
    mismo_p = [r for _, r in _aprobadas_por_plano.get(plano, []) if _reutilizaciones.get(r, 0) < 1]
    gen_libre = [r for r in _aprobadas_generales if _reutilizaciones.get(r, 0) < 1]
    pool = mismo_p or gen_libre or _aprobadas_generales
    fuente = pool[_idx_banco[0] % len(pool)] if pool else None
    _idx_banco[0] += 1

    if fuente and os.path.exists(fuente):
        shutil.copy2(fuente, ruta_salida)
        _reutilizaciones[fuente] = _reutilizaciones.get(fuente, 0) + 1
        _stats["reutilizadas_banco"] += 1
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(0 if generar_imagen(sys.argv[1], sys.argv[2]) else 1)
