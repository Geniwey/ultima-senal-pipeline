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
_cf_flux_agotado = [False]
_cf_sdxl_agotado = [False]
_pol_agotado = [False]
_ultima_fue_emergencia = [False]
_hashes_usados = []
_aprobadas_por_plano = {}
_aprobadas_generales = []
_reutilizaciones_por_ruta = {}
_indice_rotacion_banco = [0]
_urls_wikimedia_usadas = set()
_stats = {"generadas_ia": 0, "wikimedia_real": 0, "rechazadas_qa": 0, "reutilizadas_banco": 0, "infografias": 0}

QUERIES_WIKIMEDIA_POR_PLANO = {
    "cinta_puerto": "Boeing 757 fuselage static port close up",
    "cabina_pilotos": "Boeing 757 cockpit night instruments",
    "ala_nubes": "aircraft wing clouds sunset sky",
    "pista_lluvia": "airport runway night lights rain",
    "turbina": "jet engine turbofan blades close up",
    "mar_tormenta": "stormy ocean waves dark sea",
    "barco_rescate": "coast guard rescue ship ocean",
    "caja_negra": "flight data recorder black box aviation",
    "hangar": "Boeing 757 aircraft maintenance hangar",
    "avion_frontal": "Boeing 757 commercial airliner",
    "torre_noche": "airport air traffic control tower night",
    "general": "commercial airliner clouds sky",
}


def fue_ultima_generacion_emergencia() -> bool:
    return _ultima_fue_emergencia[0]


def obtener_estadisticas_imagenes() -> dict:
    return dict(_stats)


def obtener_mejor_imagen_plano(plano: str) -> str:
    candidatas = sorted(_aprobadas_por_plano.get(plano, []), key=lambda x: x[0], reverse=True)
    for _, ruta in candidatas:
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
            tarjetas = [
                (0.18, "AERONAVE\n\nBOEING 757-200\nMatrícula N52AW", "#00E5FF"),
                (0.50, "OCUPANTES\n\n70 PERSONAS\n61 Pasajeros · 9 Tripul.", "#FFAA00"),
                (0.82, "RUTA Y FECHA\n\nLIMA → SANTIAGO\n2 Octubre 1996", "#FF3333"),
            ]
            for x, txt, col in tarjetas:
                bbox = dict(boxstyle="round,pad=0.65", facecolor="#101C2E", edgecolor=col, linewidth=4)
                ax.text(x, 0.56, txt, color="#FFFFFF", fontsize=22, fontweight="bold", ha="center", va="center", bbox=bbox, transform=ax.transAxes)

        elif "ESQUEMA_SENSORES" in tipo:
            ax.axis("off")
            ax.set_title("INFORME FORENSE: CÓMO LA CINTA ENGAÑÓ AL AVIÓN", color="#FFFFFF", fontsize=28, fontweight="bold", pad=22)
            bloques = [
                (0.18, "1. SENSOR TAPADO\n\nBloquea presión\natmosférica real", "#FF3333"),
                (0.50, "2. COMPUTADORA\n\nCongela altitud en\n9.700 pies falsos", "#FFAA00"),
                (0.82, "3. RADAR DE LIMA\n\nRecibe lectura falsa\ndel transpondedor", "#00E5FF"),
            ]
            for x, txt, col in bloques:
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


def _recortar_y_normalizar_16_9(ruta: str, recortar_wm: bool = False, tono_doc: bool = False):
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
    try:
        import numpy as np
        import pytesseract
        from PIL import Image, ImageFilter

        img_rgb = Image.open(ruta).convert("RGB")
        arr = np.array(img_rgb, dtype=np.float32)
        brillo, contraste = float(arr.mean()), float(arr.std())
        pct_quemado = float((arr.mean(axis=2) > 245).mean())
        if brillo < 12.0 or brillo > 215.0 or contraste < 16.0:
            return (False, f"brillo/contraste fuera de rango ({brillo:.1f}/{contraste:.1f})")
        if es_mini and pct_quemado > 0.08:
            return (False, f"zona quemada ({pct_quemado:.2f})")

        nitidez = float(np.array(img_rgb.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32).std())
        if nitidez < 1.5:
            return (False, f"borrosa ({nitidez:.1f})")

        peq = img_rgb.resize((1024, 576), Image.Resampling.LANCZOS)
        datos = pytesseract.image_to_data(peq, config="--psm 11", output_type=pytesseract.Output.DICT)
        for txt, conf in zip(datos["text"], datos["conf"]):
            letras = re.sub(r"[^A-Za-z]", "", txt.strip())
            c_val = float(conf) if str(conf).lstrip("-").isdigit() else 0.0
            if len(letras) >= 3 and c_val >= 65.0:
                return (False, f"texto OCR: '{txt}'")

        dh = _calcular_dhash(img_rgb)
        if not permitir_dup and any(bin(dh ^ h).count("1") <= 6 for h in _hashes_usados):
            return (False, "duplicada")
        return (True, contraste + nitidez * 2.5 - pct_quemado * 150.0)
    except Exception:
        return (True, 50.0)


def _descargar_cf(prompt: str, destino: str, modelo: str) -> bool:
    es_flux = "flux" in modelo
    if (es_flux and _cf_flux_agotado[0]) or (not es_flux and _cf_sdxl_agotado[0]):
        return False
    acc, tok = os.environ.get("CF_ACCOUNT_ID"), os.environ.get("CF_API_TOKEN")
    if not acc or not tok:
        return False
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{modelo}"
    try:
        payload = {"prompt": prompt, "steps": 4} if es_flux else {"prompt": prompt}
        r = requests.post(url, headers={"Authorization": f"Bearer {tok}"}, json=payload, timeout=TIMEOUT)
        if r.status_code == 200:
            if "application/json" in r.headers.get("Content-Type", ""):
                b64 = r.json().get("result", {}).get("image")
                if b64:
                    open(destino, "wb").write(base64.b64decode(b64))
            else:
                open(destino, "wb").write(r.content)
            if _validar_imagen(destino):
                _recortar_y_normalizar_16_9(destino)
                return True
        else:
            print(f"  [API Cloudflare {modelo.split('/')[-1]}] HTTP {r.status_code}")
            if r.status_code == 429:
                if es_flux:
                    _cf_flux_agotado[0] = True
                else:
                    _cf_sdxl_agotado[0] = True
    except Exception as e:
        print(f"  [API Cloudflare] Error: {e}")
    return False


def _descargar_pol(prompt: str, destino: str, semilla: int) -> bool:
    if _pol_agotado[0]:
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
                _recortar_y_normalizar_16_9(destino, recortar_wm=(not key))
                return True
        else:
            print(f"  [API Pollinations] HTTP {r.status_code}")
            if r.status_code in (401, 402, 429) and not key:
                _pol_agotado[0] = True
    except Exception as e:
        print(f"  [API Pollinations] Error: {e}")
    return False


def _descargar_wikimedia(plano: str, destino: str, semilla: int) -> bool:
    query = QUERIES_WIKIMEDIA_POR_PLANO.get(plano, QUERIES_WIKIMEDIA_POR_PLANO["general"])
    headers = {"User-Agent": "UltimaSenalDocBot/1.0 (educational aviation documentary)"}
    params = {"action": "query", "generator": "search", "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6, "gsrlimit": 15, "prop": "imageinfo", "iiprop": "url|size", "iiurlwidth": 1280, "format": "json"}
    try:
        r = requests.get("https://commons.wikimedia.org/w/api.php", params=params, headers=headers, timeout=20)
        pages = list(r.json().get("query", {}).get("pages", {}).values()) if r.status_code == 200 else []
        if not pages:
            return False
        off = semilla % len(pages)
        for p in pages[off:] + pages[:off]:
            info = (p.get("imageinfo") or [{}])[0]
            img_url = info.get("thumburl") or info.get("url")
            if not img_url or info.get("width", 0) < 800 or info.get("height", 0) < 450 or img_url in _urls_wikimedia_usadas:
                continue
            ri = requests.get(img_url, headers=headers, timeout=25)
            if ri.status_code == 200:
                open(destino, "wb").write(ri.content)
                if _validar_imagen(destino):
                    _recortar_y_normalizar_16_9(destino, tono_doc=True)
                    _urls_wikimedia_usadas.add(img_url)
                    _stats["wikimedia_real"] += 1
                    print(f"  📷 [Archivo Fotográfico] Foto real obtenida para '{plano}'.")
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
    intentos = [("cf_flux", 0), ("cf_sdxl", 1), ("pol", seed_base + 11), ("cf_sdxl_2", 2)] + ([("cf_flux_2", 3)] if es_miniatura else [])

    for i, (prov, s) in enumerate(intentos):
        cand = f"{ruta_salida}_cand_{i}.png"
        ok = _descargar_cf(prompt_completo, cand, "@cf/black-forest-labs/flux-1-schnell") if prov.startswith("cf_flux") else (
            _descargar_cf(prompt_completo, cand, "@cf/bytedance/stable-diffusion-xl-lightning") if prov.startswith("cf_sdxl") else _descargar_pol(prompt_completo, cand, s)
        )
        if ok:
            es_val, info = _evaluar_calidad(cand, permitir_dup=es_miniatura, es_mini=es_miniatura)
            if es_val:
                validas.append((info, cand))
                if len(validas) >= objetivo:
                    break
            else:
                _stats["rechazadas_qa"] += 1
                print(f"  ⚠️ [QA] Candidata descartada: {info}")
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
            try:
                from PIL import Image
                _hashes_usados.append(_calcular_dhash(Image.open(ruta_salida).convert("RGB")))
            except Exception:
                pass
            _aprobadas_por_plano.setdefault(plano, []).append((score, ruta_salida))
            if plano != "cinta_puerto":
                _aprobadas_generales.append(ruta_salida)
        return True

    if not es_miniatura and _descargar_wikimedia(plano, ruta_salida, seed_base):
        _aprobadas_por_plano.setdefault(plano, []).append((40.0, ruta_salida))
        if plano != "cinta_puerto":
            _aprobadas_generales.append(ruta_salida)
        return True

    _ultima_fue_emergencia[0] = True
    mismo_p = [r for _, r in _aprobadas_por_plano.get(plano, []) if _reutilizaciones_por_ruta.get(r, 0) < 1]
    gen_libre = [r for r in _aprobadas_generales if _reutilizaciones_por_ruta.get(r, 0) < 1]
    pool = mismo_p or gen_libre or _aprobadas_generales
    fuente = pool[_indice_rotacion_banco[0] % len(pool)] if pool else None
    _indice_rotacion_banco[0] += 1

    if fuente and os.path.exists(fuente):
        shutil.copy2(fuente, ruta_salida)
        _reutilizaciones_por_ruta[fuente] = _reutilizaciones_por_ruta.get(fuente, 0) + 1
        _stats["reutilizadas_banco"] += 1
        print(f"  🔄 [Banco Planos] Reutilizada toma aprobada de '{plano}'.")
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(0 if generar_imagen(sys.argv[1], sys.argv[2]) else 1)
