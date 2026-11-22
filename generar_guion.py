import os
import json
import sys
import re
from collections import Counter
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

FICHA_POR_DEFECTO = {
    "caso": "Vuelo Aeroperú 603",
    "fecha": "2 de octubre de 1996",
    "avion": "Boeing 757-200 (matrícula N52AW)",
    "ruta": "Lima (Perú) a Santiago (Chile)",
    "ocupantes": "70 personas (61 pasajeros y 9 tripulantes, sin sobrevivientes)",
    "causa_oficial": "Un operario de limpieza cubrió los 3 puertos estáticos del lado izquierdo con cinta adhesiva plateada y nadie la retiró antes del despegue (Informe Final CIAA).",
    "cronologia": [
        {"hora": "00:40 AM", "hecho": "Despegue desde el aeropuerto de Lima bajo niebla densa"},
        {"hora": "00:42 AM", "hecho": "Velocímetro y altímetro muestran lecturas erróneas en ascenso"},
        {"hora": "00:44 AM", "hecho": "La tripulación declara emergencia y pide vectores de regreso"},
        {"hora": "00:58 AM", "hecho": "El radar de Lima lee 9700 pies falsos enviados por el transpondedor"},
        {"hora": "01:11 AM", "hecho": "El ala izquierda golpea el mar frente a Chancay tras 31 minutos de vuelo"},
    ],
    "consecuencias": [
        "Prohibición de cinta camuflada y uso obligatorio de cubiertas de alta visibilidad con banderines",
        "Refuerzo de las listas de verificación prevuelo y doble inspección de sensores",
    ],
    "fuentes": [
        "Informe Final de la Comisión Investigadora de Accidentes de Aviación (CIAA - Perú)",
        "Registros técnicos y recomendaciones de seguridad de la OACI",
    ],
}

BANCO_PLANOS = {
    "cinta_puerto": "Extreme macro close-up of wrinkled silver metallic duct tape wrapped over and completely sealing a round chrome static port sensor on a smooth matte dark blue aircraft fuselage, warm directional spotlight, shallow depth of field",
    "cabina_pilotos": "Dark cinematic view from behind empty cockpit seats looking through windshield into dense night fog and distant lightning over the black ocean, moody blue instrument glow, smooth unmarked surfaces",
    "ala_nubes": "Close-up of a commercial airliner wingtip with red navigation strobe light cutting through dense dark storm clouds and rain at night, dramatic rim lighting, smooth unmarked metal",
    "pista_lluvia": "Low angle shot of wet dark airport runway centerlines reflecting distant amber lights in dense night fog, dark vignette at bottom edge, smooth wet asphalt",
    "turbina": "Close-up exterior shot of commercial jet engine fan blades illuminated by subtle blue and amber night lights in mist, smooth unmarked metallic cowling",
    "mar_tormenta": "Dramatic low-angle close-up of a commercial airliner wingtip slicing into dark turbulent Pacific ocean waves at night sending white sea spray into the air, storm lighting",
    "barco_rescate": "Night maritime search vessel silhouette with a white searchlight beam scanning dark rough ocean waves under rain and fog, completely unmarked plain dark hull",
    "caja_negra": "Underwater spotlight illuminating a plain smooth bright orange rectangular flight data recorder box resting on dark sandy seabed, completely unmarked painted metal surface",
    "hangar": "Wide cinematic shot of a commercial Boeing 757 parked inside a dimly lit maintenance hangar at night under overhead floodlights, smooth unmarked white and blue fuselage",
    "avion_frontal": "Dramatic low-angle three-quarter view of an unmarked commercial airliner climbing into dark stormy night clouds, landing lights glowing, smooth clean fuselage",
    "torre_noche": "Exterior shot of an airport air traffic control tower at night surrounded by dense mist with glowing green radar room windows, moody cinematic lighting",
}

ROTULOS_POR_PLANO = {
    "cinta_puerto": ["CINTA SOBRE PUERTOS ESTÁTICOS", "3 SENSORES BLOQUEADOS", "CINTA CAMUFLADA PROHIBIDA"],
    "cabina_pilotos": ["ALARMAS CONTRADICTORIAS", "ALTÍMETRO Y VELOCÍMETRO FALLAN", "EMERGENCIA EN CABINA"],
    "pista_lluvia": ["DESPEGUE 00:40 AM LIMA", "PISTA BAJO NIEBLA DENSA"],
    "turbina": ["BOEING 757-200 N52AW", "ASCENSO SOBRE EL PACÍFICO"],
    "ala_nubes": ["VUELO CIEGO EN TORMENTA", "RUTA LIMA A SANTIAGO"],
    "mar_tormenta": ["01:11 AM IMPACTO EN EL MAR", "FRENTE A CHANCAY"],
    "barco_rescate": ["BÚSQUEDA MARÍTIMA NOCTURNA", "OPERATIVO DE RESCATE"],
    "caja_negra": ["CAJA NEGRA RECUPERADA", "DATOS DEL REGISTRADOR FDR"],
    "hangar": ["INVESTIGACIÓN OFICIAL CIAA", "DOBLE INSPECCIÓN PREVUELO"],
    "avion_frontal": ["31 MINUTOS DE VUELO CIEGO", "SIN SOBREVIVIENTES"],
    "torre_noche": ["RADAR DE LIMA ENGAÑADO", "VECTORES DE REGRESO"],
}

CORRECCIONES = {
    r"\bOCCUPANTES\b": "OCUPANTES", r"\bNIEBLA DENSAS\b": "NIEBLA DENSA",
    r"\bIMPÁCTO\b": "IMPACTO", r"\bAEROPERU\b": "AEROPERÚ",
    r"\bFUSELAGE\b": "FUSELAJE", r"\bRESCUE\b": "RESCATE",
    r"\bla ala\b": "el ala", r"\b9\.700\b": "9700",
    r"\btubos?\s+pitot\b": "puertos estáticos", r"\bpitot\b": "puerto estático",
}


def _limpiar_texto(texto: str) -> str:
    res = texto.strip()
    for pat, rep in CORRECCIONES.items():
        res = re.sub(pat, rep, res, flags=re.IGNORECASE)
    res = re.sub(r",?\s*\ben\s+20\d{2}\b", "", res, flags=re.IGNORECASE)
    return re.sub(r"\s+([.,;?¿!¡])", r"\1", res).strip()


def _cargar_ficha() -> dict:
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ficha.json")
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return FICHA_POR_DEFECTO


def _asignar_plano_semantico(esc: dict, idx: int) -> str:
    txt = f"{esc.get('texto_narracion', '')} {esc.get('texto_pantalla', '')}".lower()
    reglas = [
        (("cinta", "puerto", "estático", "sensor", "lavado", "operario", "cubierta", "bander", "adhesiv"), "cinta_puerto"),
        (("impact", "olas", "superficie", "chancay", "golpea el mar", "sumerge"), "mar_tormenta"),
        (("caja negra", "grabadora", "registrador", "fdr", "módulos de vuelo"), "caja_negra"),
        (("rescate", "barco", "búsqueda", "escombros"), "barco_rescate"),
        (("cabina", "piloto", "tripulación", "alarma", "altímetro", "velocímetro", "stick"), "cabina_pilotos"),
        (("torre", "radar", "controlador", "vectores", "transpondedor"), "torre_noche"),
        (("pista", "despeg", "jorge chávez", "niebla"), "pista_lluvia"),
        (("ciaa", "investig", "informe", "hangar", "inspección", "verificación", "oaci"), "hangar"),
        (("turbina", "motor", "boeing 757"), "turbina"),
        (("nubes", "ala", "tormenta", "ruta"), "ala_nubes"),
    ]
    for claves, destino in reglas:
        if any(k in txt for k in claves):
            return destino
    plano_llm = str(esc.get("plano", "")).strip().lower()
    if plano_llm in BANCO_PLANOS:
        return plano_llm
    claves_all = list(BANCO_PLANOS.keys())
    return claves_all[idx % len(claves_all)]


def _validar_escenas(escenas_brutas: list) -> list:
    filtradas, vistas = [], set()
    for esc in escenas_brutas:
        narr = _limpiar_texto(esc.get("texto_narracion", ""))
        narr = re.sub(r"Si este v[íi]deo te result[óo].*$", "", narr, flags=re.IGNORECASE).strip()
        if not narr or any(p in narr.lower() for p in ("suscr", "compártelo", "comparte este", "dale like")):
            continue
        firma = " ".join(re.findall(r"[a-záéíóúñ]+", narr.lower())[:7])
        if firma in vistas:
            continue
        vistas.add(firma)
        esc["texto_narracion"] = narr
        filtradas.append(esc)

    filtradas = filtradas[:34]
    uso_planos = Counter()
    uso_rotulos_plano = Counter()
    rotulos_globales = set()
    plano_ant = ""

    for idx, esc in enumerate(filtradas):
        plano = _asignar_plano_semantico(esc, idx)
        lim = 3 if plano == "cinta_puerto" else 2
        if uso_planos[plano] >= lim or plano == plano_ant:
            cands = sorted(BANCO_PLANOS.keys(), key=lambda p: uso_planos[p])
            for c in cands:
                lim_c = 3 if c == "cinta_puerto" else 2
                if c != plano_ant and uso_planos[c] < lim_c:
                    plano = c
                    break

        uso_planos[plano] += 1
        plano_ant = plano

        # Rótulo 100% vinculado al plano elegido (nunca desajustado ni cortado)
        opciones = ROTULOS_POR_PLANO[plano]
        rot = opciones[uso_rotulos_plano[plano] % len(opciones)]
        uso_rotulos_plano[plano] += 1
        if rot in rotulos_globales:
            for alt in opciones:
                if alt not in rotulos_globales:
                    rot = alt
                    break
        rotulos_globales.add(rot)

        esc.update({
            "texto_pantalla": rot,
            "tipo": "imagen",
            "plano": plano,
            "prompt_imagen": BANCO_PLANOS[plano],
        })

    # Asegurar 3 apariciones clave de cinta_puerto (flashback limpieza, despegue tapado, hallazgo informe)
    for pos, rot_cinta in [(4, "CINTA SOBRE PUERTOS ESTÁTICOS"), (9, "3 SENSORES BLOQUEADOS"), (29, "CINTA CAMUFLADA PROHIBIDA")]:
        if pos < len(filtradas):
            filtradas[pos].update({
                "tipo": "imagen",
                "plano": "cinta_puerto",
                "prompt_imagen": BANCO_PLANOS["cinta_puerto"],
                "texto_pantalla": rot_cinta,
            })

    # 6 gráficos distintos garantizados y equidistantes
    total = len(filtradas)
    graficos = [
        (max(2, int(total * 0.09)), "INFOGRAFIA:TARJETA_VUELO", "70 OCUPANTES A BORDO"),
        (max(5, int(total * 0.24)), "INFOGRAFIA:ESQUEMA_SENSORES", "3 PUERTOS ESTÁTICOS TAPADOS"),
        (max(8, int(total * 0.39)), "INFOGRAFIA:MAPA_RUTA", "DESVÍO HACIA EL PACÍFICO"),
        (max(11, int(total * 0.54)), "INFOGRAFIA:PANEL_ALARMAS", "ALARMAS CONTRADICTORIAS"),
        (max(14, int(total * 0.69)), "INFOGRAFIA:GRAFICA_ALTITUD", "9700 PIES FALSOS EN RADAR"),
        (max(17, int(total * 0.84)), "INFOGRAFIA:CRONOLOGIA", "31 MINUTOS DE VUELO CIEGO"),
    ]
    usadas = set()
    for pos, cod, rot in graficos:
        while pos in usadas and pos + 1 < total:
            pos += 1
        if pos < total:
            usadas.add(pos)
            filtradas[pos].update({"tipo": "grafico", "plano": "grafico", "prompt_imagen": cod, "texto_pantalla": rot})

    return filtradas


def _parsear_guion(texto: str, ficha: dict) -> dict:
    match = re.search(r"\{.*\}", texto or "", re.DOTALL)
    if not match:
        raise ValueError("Respuesta sin JSON válido")
    datos = json.loads(match.group(0))
    escenas = _validar_escenas(datos.get("escenas", []))
    if len(escenas) < 20:
        raise ValueError(f"Escenas insuficientes: {len(escenas)}")
    datos.update({
        "escenas": escenas,
        "titulo_miniatura": "LA CINTA MORTAL",
        "prompt_miniatura": f"{BANCO_PLANOS['cinta_puerto']}, 8k",
    })
    fuentes_txt = "\n".join(f"- {f}" for f in ficha.get("fuentes", []))
    desc = datos.get("descripcion_youtube", "").strip()
    if "Fuentes oficiales" not in desc:
        desc += f"\n\n📋 Fuentes oficiales verificadas:\n{fuentes_txt}\nℹ️ Nota: Este vídeo contiene recreaciones visuales e infografías generadas digitalmente para ilustrar hechos históricos documentados."
    datos["descripcion_youtube"] = desc
    return datos


def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GROQ_API_KEY")
    cliente = Groq(api_key=api_key)
    ficha = _cargar_ficha()
    sys_prompt = (
        f"Director documental de aviación. Escribe un guion de exactamente 34 escenas (16 a 22 palabras por escena) basado SOLO en esta ficha (NO inventes años como 2023 ni menciones pitot, son puertos estáticos):\n"
        f"{json.dumps(ficha, ensure_ascii=False)}\n"
        f"Bloques: 1-3 clímax 01:10 AM; 4-10 cinta en puertos estáticos; 11-18 despegue 00:40 AM y emergencia; 19-26 9700 pies falsos e impacto 01:11 AM; 27-31 caja negra e informe CIAA; 32-34 normas OACI y pregunta final.\n"
        f"Devuelve SOLO JSON con: titulo_video, descripcion_youtube, tags_youtube, comentario_fijado, escenas:[{{texto_narracion, texto_pantalla, plano}}]."
    )
    msgs = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"Tema: {tema}"}]
    for intento in range(1, 4):
        modelo = MODELO_PRINCIPAL if intento <= 2 else MODELO_FALLBACK
        try:
            print(f"Llamando a Groq ({modelo}, intento {intento}/3)...")
            resp = cliente.chat.completions.create(model=modelo, messages=msgs, temperature=0.3, max_tokens=16000)
            return _parsear_guion(resp.choices[0].message.content, ficha)
        except Exception as e:
            print(f"  [Aviso] Intento {intento} fallido: {e}")
    from openai import OpenAI
    c_cer = OpenAI(api_key=os.environ.get("CEREBRAS_API_KEY"), base_url="https://api.cerebras.ai/v1")
    resp = c_cer.chat.completions.create(model=MODELO_CEREBRAS, messages=msgs, temperature=0.3, max_tokens=16000)
    return _parsear_guion(resp.choices[0].message.content, ficha)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)
    guion = generar_guion(sys.argv[1])
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
