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
    "cinta_puerto": "Extreme macro close-up of glossy silver-grey metallic duct tape covering a round chrome static port sensor on a smooth unmarked dark blue aircraft fuselage, dramatic hangar spotlight, shallow depth of field",
    "cabina_pilotos": "Dark cinematic view from behind empty cockpit seats looking through windshield into dense night fog and distant lightning over the black ocean, moody blue instrument glow, smooth unmarked surfaces",
    "ala_nubes": "Close-up of a commercial airliner wingtip with red navigation strobe light cutting through dense dark storm clouds and rain at night, dramatic rim lighting, smooth unmarked metal",
    "pista_lluvia": "Low angle shot of wet airport runway centerlines reflecting amber approach lights in dense night fog, cinematic documentary atmosphere, smooth wet asphalt",
    "turbina": "Close-up exterior shot of commercial jet engine fan blades illuminated by amber runway lights in night mist, smooth unmarked metallic cowling",
    "mar_tormenta": "Dramatic low-angle close-up of a commercial airliner wingtip slicing into dark turbulent Pacific ocean waves at night sending white sea spray into the air, storm lighting",
    "barco_rescate": "Night maritime search vessel with a powerful white searchlight beam scanning dark rough ocean waves under rain and fog, cinematic documentary shot",
    "caja_negra": "Underwater spotlight illuminating a plain smooth bright orange rectangular flight data recorder box resting on dark sandy seabed, completely unmarked painted metal surface",
    "hangar": "Wide cinematic shot of a commercial Boeing 757 parked inside a dimly lit maintenance hangar at night under overhead floodlights, smooth unmarked white and blue fuselage",
    "avion_frontal": "Dramatic low-angle three-quarter view of an unmarked commercial airliner climbing into dark stormy night clouds, landing lights glowing, smooth clean fuselage",
    "torre_noche": "Exterior shot of an airport air traffic control tower at night surrounded by dense mist with glowing green radar room windows, moody cinematic lighting",
}

REGLAS_COHERENCIA = {
    "IMPACTO": {"mar_tormenta", "ala_nubes"},
    "OCÉANO": {"mar_tormenta", "barco_rescate"},
    "MAR": {"mar_tormenta", "barco_rescate"},
    "PUERTO": {"cinta_puerto"},
    "SENSOR": {"cinta_puerto"},
    "CINTA": {"cinta_puerto"},
    "CUBIERTA": {"cinta_puerto"},
    "BANDERÍN": {"cinta_puerto"},
    "INSPECCIÓN": {"hangar", "avion_frontal"},
    "VERIFICACIÓN": {"hangar", "cabina_pilotos"},
    "EMERGENCIA": {"cabina_pilotos", "torre_noche"},
    "ALARMA": {"cabina_pilotos"},
    "CABINA": {"cabina_pilotos"},
    "ALTÍMETRO": {"cabina_pilotos"},
    "VELOCÍMETRO": {"cabina_pilotos"},
    "CAJA NEGRA": {"caja_negra"},
    "GRABADORA": {"caja_negra"},
    "TORRE": {"torre_noche"},
    "RADAR": {"torre_noche"},
    "DESPEGUE": {"pista_lluvia", "avion_frontal"},
    "PISTA": {"pista_lluvia"},
    "TURBINA": {"turbina"},
    "MOTOR": {"turbina"},
    "RESCATE": {"barco_rescate"},
}

PALABRAS_VACIAS = {
    "REFLEXIÓN", "MEMORIAL", "ESTADÍSTICAS", "PREGUNTA", "TECNOLOGÍA",
    "LECCIÓN", "CONCLUSIÓN", "LEGADO", "DECISIÓN", "INTERROGANTE", "ESTUDIO",
    "INFORMACIÓN", "ANÁLISIS", "COMPARTE", "SUSCRÍBETE", "TRAGEDIA",
    "RESUMEN FINAL", "CASOS SIMILARES", "HONOR LIMA", "MEDIDA CRÍTICA",
    "INSPECCIÓN AUTOMATIZADA", "LISTA DOBLE INSPECCIÓN", "REDUNDANCIA DE SENSORES",
    "PITOT INFLUENCIADO",
}

ROTULOS_DATOS_VERIFICADOS = [
    "BOEING 757-200 N52AW",
    "RUTA LIMA A SANTIAGO",
    "70 PERSONAS A BORDO",
    "SIN SOBREVIVIENTES",
    "31 MINUTOS DE VUELO",
    "IMPACTO FRENTE A CHANCAY",
    "INFORME OFICIAL CIAA",
    "BANDERINES OBLIGATORIOS OACI",
    "CINTA CAMUFLADA PROHIBIDA",
    "DOBLE VERIFICACIÓN PREVUELO",
]

CORRECCIONES_ORTOGRAFICAS = {
    r"\bOCCUPANTES\b": "OCUPANTES",
    r"\bNIEBLA DENSO\b": "NIEBLA DENSA",
    r"\bIMPÁCTO\b": "IMPACTO",
    r"\bININTERUMPIDA\b": "ININTERRUMPIDA",
    r"\bAEROPERU\b": "AEROPERÚ",
    r"\bADICIONA\b": "ADICIONAL",
    r"\bla ala\b": "el ala",
    r"\b9\.700\b": "9700",
    r"\btubos?\s+pitot\b": "puertos estáticos",
    r"\bdel\s+pitot\b": "de los puertos estáticos",
    r"\bpitot\b": "puerto estático",
}


def _limpiar_narracion_y_datos(texto: str) -> str:
    res = texto.strip()
    for patron, reemplazo in CORRECCIONES_ORTOGRAFICAS.items():
        res = re.sub(patron, reemplazo, res, flags=re.IGNORECASE)
    res = re.sub(r",?\s*\ben\s+20\d{2}\b", "", res, flags=re.IGNORECASE)
    res = re.sub(r"\s+([.,;?¿!¡])", r"\1", res)
    return res.strip()


def _recortar_palabras_limpio(texto: str, max_chars: int = 28, max_palabras: int = 4) -> str:
    palabras = [w.strip(".,;:¡!¿?\"'#") for w in texto.split() if w.strip(".,;:¡!¿?\"'#")]
    resultado = []
    for p in palabras[:max_palabras]:
        candidato = " ".join(resultado + [p])
        if len(candidato) <= max_chars:
            resultado.append(p)
        else:
            break
    if len(resultado) < 2 and len(palabras) >= 2:
        resultado = palabras[:2]
    return " ".join(resultado).upper()


def rotulo_coherente(rotulo: str, plano: str) -> bool:
    rot_up = rotulo.upper()
    for clave, permitidos in REGLAS_COHERENCIA.items():
        if clave in rot_up and plano not in permitidos:
            return False
    return True


def _corregir_plano_por_rotulo(rotulo: str, plano_actual: str) -> str:
    rot_up = rotulo.upper()
    for clave, permitidos in REGLAS_COHERENCIA.items():
        if clave in rot_up and plano_actual not in permitidos:
            return sorted(permitidos)[0]
    return plano_actual


def _cargar_ficha(tema: str) -> dict:
    ruta_ficha = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ficha.json")
    if os.path.exists(ruta_ficha):
        try:
            with open(ruta_ficha, "r", encoding="utf-8") as f:
                ficha = json.load(f)
            print("📋 Ficha verificada cargada desde ficha.json")
            return ficha
        except Exception as e:
            print(f"  [Aviso] No se pudo leer ficha.json ({e}), usando ficha integrada.")
    return FICHA_POR_DEFECTO


def _build_system_prompt(ficha: dict) -> str:
    planos_lista = ", ".join(BANCO_PLANOS.keys())
    return f"""Eres el director jefe de un canal documental forense de aviación en YouTube. Escribe un guion de exactamente 34 escenas (duración total 4:20 a 5:00 min) con máximo rigor técnico y tono respetuoso con las víctimas.

FICHA DE HECHOS VERIFICADA (USA SOLO ESTOS DATOS; PROHIBIDO INVENTAR AÑOS COMO 2023 O HABLAR DE TUBOS PITOT):
{json.dumps(ficha, ensure_ascii=False, indent=2)}

DISTRIBUCIÓN OBLIGATORIA POR BLOQUES:
- Escenas 1 a 3: Gancho en frío a las 01:10 AM sobre el Pacífico con las alarmas activas antes de rebobinar al despegue.
- Escenas 4 a 10: Preparación del Boeing 757-200 en Lima, lavado del fuselaje y colocación de cinta plateada sobre los 3 puertos estáticos (NO tubos pitot).
- Escenas 11 a 18: Despegue a las 00:40 AM bajo niebla densa, conflicto entre velocímetro y altímetro y llamada de emergencia.
- Escenas 19 a 26: Lectura falsa de 9700 pies en el radar de Lima, descenso ciego sobre el océano e impacto a las 01:11 AM frente a Chancay.
- Escenas 27 a 31: Operación de búsqueda marítima, recuperación de la caja negra (FDR) y conclusiones técnicas del informe oficial CIAA.
- Escenas 32 a 34: ÚNICAMENTE aquí menciona las medidas de la OACI (cubiertas con banderines de alta visibilidad y doble verificación prevuelo) y cierra con una pregunta técnica reflexiva.

REGLAS ESTRICTAS DE RÓTULOS ("texto_pantalla"):
- MAYÚSCULAS, entre 2 y 4 palabras completas (MÁXIMO 28 caracteres), con un dato concreto verificable que coincida con "plano".
- NUNCA repitas un rótulo, nunca uses signos '#' ni frases vagas ({", ".join(sorted(PALABRAS_VACIAS))}).

REGLAS DE PLANOS ("plano" y "prompt_imagen"):
- El campo "plano" DEBE ser exactamente uno de estos: {planos_lista}.
- Usa cada plano como máximo 2 veces (máximo 3 veces "cinta_puerto") y NUNCA pongas el mismo plano en dos escenas consecutivas.
- Describe siempre en inglés: sujeto físico + plano + luz + ambiente, con superficies lisas ("smooth unmarked metal"). PROHIBIDO pedir personas, caras, pantallas con texto, relojes, papeles o logos.

Devuelve ÚNICAMENTE un JSON válido:
{{
  "titulo_video": "El error de 2$ que derribó al Vuelo 603 (Caso Aeroperú)",
  "descripcion_youtube": "Resumen documental de 3 párrafos citando las fuentes oficiales de la ficha.",
  "tags_youtube": ["aeroperu 603", "misterios de aviacion", "documental aereo", "caja negra", "seguridad aerea"],
  "comentario_fijado": "¿Qué medida de control crees que es más crítica para evitar un fallo así: las cubiertas con banderín o la doble inspección prevuelo?",
  "prompt_miniatura": "{BANCO_PLANOS['cinta_puerto']}, 8k",
  "titulo_miniatura": "LA CINTA MORTAL",
  "escenas": [
    {{
      "texto_narracion": "Frase documental clara de 14 a 22 palabras...",
      "texto_pantalla": "01:10 AM SOBRE EL PACÍFICO",
      "tipo": "imagen",
      "plano": "cabina_pilotos",
      "duracion_segundos": 5.5,
      "prompt_imagen": "Dark cinematic view from behind empty cockpit seats looking into dense night fog and lightning over the ocean, smooth unmarked surfaces"
    }}
  ]
}}"""


def _llamar_groq(cliente: Groq, messages: list, modelo: str, temperatura: float = 0.3) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=messages,
        temperature=temperatura,
        max_tokens=16000,
    )
    return respuesta.choices[0].message.content


def _llamar_cerebras(messages: list, temperatura: float = 0.3) -> str:
    from openai import OpenAI
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        raise RuntimeError("Falta CEREBRAS_API_KEY")
    cliente = OpenAI(api_key=api_key, base_url="https://api.cerebras.ai/v1")
    respuesta = cliente.chat.completions.create(
        model=MODELO_CEREBRAS,
        messages=messages,
        temperature=temperatura,
        max_tokens=16000,
    )
    return respuesta.choices[0].message.content


def _auditar_ortografia_llm(cliente: Groq, escenas: list) -> list:
    payload = [{"i": idx, "n": e["texto_narracion"], "r": e["texto_pantalla"]} for idx, e in enumerate(escenas)]
    prompt_editor = (
        "Eres corrector ortográfico y editor de documentales de aviación. Revisa este JSON de escenas:\n"
        "1. Corrige cualquier falta de ortografía o concordancia ('el ala', '9700', 'puertos estáticos' nunca 'pitot').\n"
        "2. Elimina cualquier mención inventada a años como 'en 2023'.\n"
        "3. Asegúrate de que cada 'r' tenga entre 2 y 4 palabras completas en MAYÚSCULAS (MÁXIMO 28 caracteres), sin signos '#' ni frases vagas.\n"
        "4. Asegura que ningún 'r' esté repetido.\n"
        "Devuelve SOLO el array JSON [{\"i\":0,\"n\":\"...\",\"r\":\"...\"}, ...]."
    )
    try:
        raw = _llamar_groq(
            cliente,
            [
                {"role": "system", "content": prompt_editor},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            MODELO_PRINCIPAL,
            temperatura=0.0,
        )
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        items = json.loads(match.group(0)) if match else json.loads(raw.strip())
        por_id = {it["i"]: it for it in items if isinstance(it, dict) and "i" in it}
        for idx, esc in enumerate(escenas):
            if idx in por_id:
                esc["texto_narracion"] = _limpiar_narracion_y_datos(por_id[idx].get("n", esc["texto_narracion"]))
                esc["texto_pantalla"] = _limpiar_narracion_y_datos(por_id[idx].get("r", esc["texto_pantalla"])).upper()
    except Exception as e:
        print(f"  [Aviso] Segunda pasada ortográfica omitida ({e}).")
    return escenas


def _asignar_plano_valido(esc: dict, idx: int) -> str:
    plano = str(esc.get("plano", "")).strip().lower()
    if plano in BANCO_PLANOS:
        return plano
    texto = f"{esc.get('texto_narracion', '')} {esc.get('texto_pantalla', '')}".lower()
    if any(k in texto for k in ("cinta", "puerto", "estático", "sensor", "lavado", "operario", "cubierta", "bander")):
        return "cinta_puerto"
    if any(k in texto for k in ("impact", "olas", "superficie", "invert", "chancay", "mar", "océano")):
        return "mar_tormenta"
    if any(k in texto for k in ("caja negra", "grabadora", "registrador", "submar")):
        return "caja_negra"
    if any(k in texto for k in ("rescate", "barco", "búsqueda")):
        return "barco_rescate"
    if any(k in texto for k in ("cabina", "piloto", "tripulación", "palanca", "alarma", "altímetro", "velocímetro")):
        return "cabina_pilotos"
    if any(k in texto for k in ("torre", "radar", "controlador")):
        return "torre_noche"
    if any(k in texto for k in ("pista", "despeg", "lima", "aeropuerto")):
        return "pista_lluvia"
    if any(k in texto for k in ("hangar", "mantenimiento", "inspección", "verificación")):
        return "hangar"
    if any(k in texto for k in ("turbina", "motor")):
        return "turbina"
    claves = [k for k in BANCO_PLANOS.keys() if k != "cinta_puerto"]
    return claves[idx % len(claves)]


def _validar_y_normalizar_escenas(escenas_brutas: list, cliente_groq: Groq = None) -> list:
    filtradas = []
    frases_vistas = set()

    for esc in escenas_brutas:
        narracion = _limpiar_narracion_y_datos(esc.get("texto_narracion", ""))
        narracion = re.sub(r"Si este v[íi]deo te result[óo].*$", "", narracion, flags=re.IGNORECASE).strip()
        if not narracion or any(p in narracion.lower() for p in ("suscr", "compártelo", "comparte este", "dale like")):
            continue

        firma = " ".join(re.findall(r"[a-záéíóúñ]+", narracion.lower())[:7])
        if firma in frases_vistas:
            continue
        frases_vistas.add(firma)

        rotulo = _limpiar_narracion_y_datos(esc.get("texto_pantalla", "")).upper()
        rotulo = rotulo.replace("...", "").replace("…", "").strip()
        esc["texto_narracion"] = narracion
        esc["texto_pantalla"] = rotulo
        filtradas.append(esc)

    filtradas = filtradas[:34]

    if cliente_groq is not None:
        filtradas = _auditar_ortografia_llm(cliente_groq, filtradas)

    rotulos_vistos = set()
    uso_planos = Counter()
    plano_anterior = ""
    idx_respaldo_rotulo = 0

    for idx, esc in enumerate(filtradas):
        narracion = _limpiar_narracion_y_datos(esc["texto_narracion"])
        rotulo = _limpiar_narracion_y_datos(esc["texto_pantalla"]).replace("...", "").replace("…", "").strip()
        rotulo = re.sub(r"#\d+", "", rotulo).strip()

        if any(v in rotulo for v in PALABRAS_VACIAS) or len(rotulo.split()) < 2 or len(rotulo) > 28:
            rotulo = _recortar_palabras_limpio(narracion, max_chars=28, max_palabras=4)

        if rotulo in rotulos_vistos or any(v in rotulo for v in PALABRAS_VACIAS):
            while idx_respaldo_rotulo < len(ROTULOS_DATOS_VERIFICADOS):
                cand_rot = ROTULOS_DATOS_VERIFICADOS[idx_respaldo_rotulo]
                idx_respaldo_rotulo += 1
                if cand_rot not in rotulos_vistos:
                    rotulo = cand_rot
                    break
        rotulos_vistos.add(rotulo)

        plano = _asignar_plano_valido(esc, idx)
        if not rotulo_coherente(rotulo, plano):
            plano = _corregir_plano_por_rotulo(rotulo, plano)

        limite_plano = 3 if plano == "cinta_puerto" else 2
        if uso_planos[plano] >= limite_plano or plano == plano_anterior:
            candidatos = sorted(
                [p for p in BANCO_PLANOS.keys() if (p != "cinta_puerto" or uso_planos["cinta_puerto"] < 3)],
                key=lambda p: uso_planos[p],
            )
            for cand in candidatos:
                lim_c = 3 if cand == "cinta_puerto" else 2
                if cand != plano_anterior and uso_planos[cand] < lim_c and rotulo_coherente(rotulo, cand):
                    plano = cand
                    break

        uso_planos[plano] += 1
        plano_anterior = plano

        esc["texto_narracion"] = narracion
        esc["texto_pantalla"] = rotulo
        esc["tipo"] = "imagen"
        esc["plano"] = plano
        esc["prompt_imagen"] = BANCO_PLANOS[plano]

    if uso_planos["cinta_puerto"] < 2 and len(filtradas) > 10:
        for pos in (4, 9):
            if filtradas[pos]["plano"] != "cinta_puerto":
                filtradas[pos]["plano"] = "cinta_puerto"
                filtradas[pos]["prompt_imagen"] = BANCO_PLANOS["cinta_puerto"]

    total = len(filtradas)
    plan_graficos = [
        (max(2, int(total * 0.09)), "INFOGRAFIA:TARJETA_VUELO", "70 OCUPANTES A BORDO"),
        (max(5, int(total * 0.24)), "INFOGRAFIA:ESQUEMA_SENSORES", "3 PUERTOS ESTÁTICOS TAPADOS"),
        (max(8, int(total * 0.39)), "INFOGRAFIA:MAPA_RUTA", "DESVÍO HACIA EL PACÍFICO"),
        (max(11, int(total * 0.54)), "INFOGRAFIA:PANEL_ALARMAS", "ALARMAS CONTRADICTORIAS"),
        (max(14, int(total * 0.69)), "INFOGRAFIA:GRAFICA_ALTITUD", "9700 PIES FALSOS EN RADAR"),
        (max(17, int(total * 0.84)), "INFOGRAFIA:CRONOLOGIA", "31 MINUTOS DE VUELO CIEGO"),
    ]
    posiciones_usadas = set()
    for pos, codigo_inf, rotulo_inf in plan_graficos:
        while pos in posiciones_usadas and pos + 1 < total:
            pos += 1
        if pos < total:
            posiciones_usadas.add(pos)
            filtradas[pos]["tipo"] = "grafico"
            filtradas[pos]["plano"] = "grafico"
            filtradas[pos]["prompt_imagen"] = codigo_inf
            filtradas[pos]["texto_pantalla"] = rotulo_inf

    return filtradas


def _parsear_guion(texto: str, ficha: dict, cliente_groq: Groq = None) -> dict:
    if not texto or not texto.strip():
        raise ValueError("Respuesta vacía del modelo")
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    datos = json.loads(match.group(0)) if match else json.loads(texto.strip())
    escenas = _validar_y_normalizar_escenas(datos.get("escenas", []), cliente_groq=cliente_groq)
    if len(escenas) < 20:
        raise ValueError(f"Escenas insuficientes tras validación: {len(escenas)}")

    datos["escenas"] = escenas
    datos["titulo_miniatura"] = "LA CINTA MORTAL"
    datos["prompt_miniatura"] = f"{BANCO_PLANOS['cinta_puerto']}, 8k"

    desc = datos.get("descripcion_youtube", "").strip()
    fuentes_txt = "\n".join(f"- {f}" for f in ficha.get("fuentes", []))
    bloque_legal = (
        f"\n\n📋 Fuentes oficiales verificadas:\n{fuentes_txt}\n"
        "ℹ️ Nota: Este vídeo contiene recreaciones visuales e infografías generadas digitalmente para ilustrar hechos históricos documentados."
    )
    if "Fuentes oficiales" not in desc:
        desc += bloque_legal
    datos["descripcion_youtube"] = desc
    return datos


def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GROQ_API_KEY")
    cliente = Groq(api_key=api_key)
    ficha = _cargar_ficha(tema)
    system_prompt = _build_system_prompt(ficha)

    mensajes = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Genera el guion documental completo basado en la ficha verificada sobre: {tema}"},
    ]

    for intento in range(1, 4):
        modelo = MODELO_PRINCIPAL if intento <= 2 else MODELO_FALLBACK
        try:
            print(f"Llamando a Groq ({modelo}, intento {intento}/3)...")
            texto = _llamar_groq(cliente, mensajes, modelo, temperatura=0.3)
            return _parsear_guion(texto, ficha, cliente_groq=cliente)
        except Exception as e:
            print(f"  [Aviso] Intento {intento} fallido con {modelo}: {e}")

    print("Groq falló, probando Cerebras...")
    texto = _llamar_cerebras(mensajes, temperatura=0.3)
    return _parsear_guion(texto, ficha, cliente_groq=cliente)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)
    guion = generar_guion(sys.argv[1])
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
