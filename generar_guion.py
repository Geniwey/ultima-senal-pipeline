import os
import json
import sys
import re
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

PALABRAS_VACIAS = {
    "REFLEXIÓN", "MEMORIAL", "ESTADÍSTICAS", "PREGUNTA", "TECNOLOGÍA",
    "LECCIÓN", "CONCLUSIÓN", "LEGADO", "DECISIÓN", "INTERROGANTE", "ESTUDIO",
    "INFORMACIÓN", "ANÁLISIS", "COMPARTE", "SUSCRÍBETE", "TRAGEDIA",
}

CORRECCIONES_ORTOGRAFICAS = {
    r"\bOCCUPANTES\b": "OCUPANTES",
    r"\bNIEBLA DENSO\b": "NIEBLA DENSA",
    r"\bIMPÁCTO\b": "IMPACTO",
    r"\bININTERUMPIDA\b": "ININTERRUMPIDA",
    r"\bAEROPERU\b": "AEROPERÚ",
}


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


def _corregir_ortografia(texto: str) -> str:
    res = texto
    for patron, reemplazo in CORRECCIONES_ORTOGRAFICAS.items():
        res = re.sub(patron, reemplazo, res, flags=re.IGNORECASE)
    return res


def _build_system_prompt(ficha: dict) -> str:
    planos_lista = ", ".join(BANCO_PLANOS.keys())
    return f"""Eres el director jefe de un canal documental forense de aviación en YouTube. Escribe un guion de exactamente 34 escenas (duración total 4:45 a 5:15 min) con máximo rigor técnico y tono respetuoso con las víctimas.

FICHA DE HECHOS VERIFICADA (USA SOLO ESTOS DATOS; SI UN DATO NO ESTÁ AQUÍ, NO LO INVENTES):
{json.dumps(ficha, ensure_ascii=False, indent=2)}

REGLAS OBLIGATORIAS DE ESTRUCTURA Y NARRACIÓN:
1. GANCHO EN FRÍO (Escenas 1 y 2): Empieza a las 01:10 AM en pleno clímax nocturno sobre el Pacífico con las alarmas sonando antes de rebobinar al despegue en Lima.
2. RITMO NARRATIVO: Introduce una pregunta o giro técnico cada 5 escenas.
3. LONGITUD DE NARRACIÓN: Cada "texto_narracion" debe tener entre 14 y 22 palabras claras en español.
4. CIERRE DOCUMENTAL: Termina en seco con una pregunta técnica reflexiva para comentarios. PROHIBIDO pedir suscripciones, likes o que compartan el vídeo.

REGLAS ESTRICTAS DE RÓTULOS ("texto_pantalla"):
- Debe estar en MAYÚSCULAS, tener entre 2 y 5 palabras completas (máximo 30 caracteres) y contener un dato concreto (hora, cifra, lugar o hecho).
- PROHIBIDO usar puntos suspensivos (...), rótulos repetidos o palabras sueltas vacías ({", ".join(sorted(PALABRAS_VACIAS))}).

REGLAS DE PLANOS ("plano" y "prompt_imagen"):
- El campo "plano" DEBE ser exactamente uno de estos: {planos_lista}.
- Usa "cinta_puerto" en 3 escenas clave (al explicar el lavado/cinta, la inspección omitida y la causa oficial).
- Describe siempre en inglés: sujeto físico + plano + luz + ambiente, con superficies lisas ("smooth unmarked metal"). PROHIBIDO pedir personas, caras, pantallas con texto, relojes, papeles o logos.

Devuelve ÚNICAMENTE un JSON válido:
{{
  "titulo_video": "El error de 2$ que derribó al Vuelo 603 (Caso Aeroperú)",
  "descripcion_youtube": "Resumen documental de 3 párrafos citando las fuentes oficiales de la ficha.",
  "tags_youtube": ["aeroperu 603", "misterios de aviacion", "documental aereo", "caja negra", "seguridad aerea"],
  "comentario_fijado": "¿Qué medida de control crees que es más crítica para evitar un fallo así: las cubiertas con banderín o la doble inspección prevuelo?",
  "prompt_miniatura": "{BANCO_PLANOS['cinta_puerto']}, bright blue lightning bolt in dark storm sky behind the fuselage, 8k",
  "titulo_miniatura": "LA CINTA MORTAL",
  "escenas": [
    {{
      "texto_narracion": "Frase documental de 14 a 22 palabras...",
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
    """Segunda llamada al LLM a temperatura 0.0 exclusivamente para ortografía y rótulos."""
    payload = [{"i": idx, "n": e["texto_narracion"], "r": e["texto_pantalla"]} for idx, e in enumerate(escenas)]
    prompt_editor = (
        "Eres corrector ortográfico y editor de documentales. Revisa este JSON de escenas:\n"
        "1. Corrige cualquier falta de ortografía o concordancia (ej. 'OCCUPANTES'->'OCUPANTES', 'NIEBLA DENSO'->'NIEBLA DENSA', 'IMPÁCTO'->'IMPACTO').\n"
        "2. Asegúrate de que cada 'r' tenga entre 2 y 5 palabras en MAYÚSCULAS, máximo 30 caracteres, sin puntos suspensivos y con un dato real de 'n'.\n"
        "3. Elimina de 'n' cualquier invitación a compartir, dar like o suscribirse.\n"
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
                esc["texto_narracion"] = _corregir_ortografia(por_id[idx].get("n", esc["texto_narracion"]).strip())
                esc["texto_pantalla"] = _corregir_ortografia(por_id[idx].get("r", esc["texto_pantalla"]).strip().upper())
    except Exception as e:
        print(f"  [Aviso] Segunda pasada ortográfica omitida ({e}).")
    return escenas


def _asignar_plano_valido(esc: dict, idx: int) -> str:
    plano = str(esc.get("plano", "")).strip().lower()
    if plano in BANCO_PLANOS:
        return plano
    texto = f"{esc.get('texto_narracion', '')} {esc.get('texto_pantalla', '')}".lower()
    if any(k in texto for k in ("cinta", "puerto", "estático", "sensor", "lavado", "operario")):
        return "cinta_puerto"
    if any(k in texto for k in ("impact", "olas", "superficie", "invert", "chancay", "mar")):
        return "mar_tormenta"
    if any(k in texto for k in ("caja negra", "grabadora", "registrador", "submar")):
        return "caja_negra"
    if any(k in texto for k in ("rescate", "barco", "búsqueda")):
        return "barco_rescate"
    if any(k in texto for k in ("cabina", "piloto", "tripulación", "palanca", "alarma")):
        return "cabina_pilotos"
    if any(k in texto for k in ("torre", "radar", "controlador")):
        return "torre_noche"
    if any(k in texto for k in ("pista", "despeg", "lima", "aeropuerto")):
        return "pista_lluvia"
    if any(k in texto for k in ("hangar", "mantenimiento", "inspección")):
        return "hangar"
    if any(k in texto for k in ("turbina", "motor")):
        return "turbina"
    claves = list(BANCO_PLANOS.keys())
    return claves[idx % len(claves)]


def _validar_y_normalizar_escenas(escenas_brutas: list, cliente_groq: Groq = None) -> list:
    filtradas = []
    frases_vistas = set()

    for esc in escenas_brutas:
        narracion = _corregir_ortografia(esc.get("texto_narracion", "").strip())
        narracion = re.sub(r"Si este v[íi]deo te result[óo].*$", "", narracion, flags=re.IGNORECASE).strip()
        if not narracion or any(p in narracion.lower() for p in ("suscr", "compártelo", "comparte este", "dale like")):
            continue

        firma = " ".join(re.findall(r"[a-záéíóúñ]+", narracion.lower())[:7])
        if firma in frases_vistas:
            continue
        frases_vistas.add(firma)

        rotulo = _corregir_ortografia(esc.get("texto_pantalla", "").strip().upper())
        rotulo = rotulo.replace("...", "").replace("…", "").strip()
        esc["texto_narracion"] = narracion
        esc["texto_pantalla"] = rotulo
        filtradas.append(esc)

    filtradas = filtradas[:34]

    if cliente_groq is not None:
        filtradas = _auditar_ortografia_llm(cliente_groq, filtradas)

    rotulos_vistos = set()
    cinta_count = 0

    for idx, esc in enumerate(filtradas):
        narracion = _corregir_ortografia(esc["texto_narracion"])
        rotulo = _corregir_ortografia(esc["texto_pantalla"]).replace("...", "").replace("…", "").strip()

        palabras_rot = rotulo.split()
        if not (2 <= len(palabras_rot) <= 5) or len(rotulo) > 30 or any(v in rotulo for v in PALABRAS_VACIAS):
            tokens = [w.strip(".,;:¡!¿?") for w in narracion.split() if len(w.strip(".,;:¡!¿?")) > 2]
            rotulo = " ".join(tokens[:4]).upper()[:30].strip()

        if rotulo in rotulos_vistos:
            base_corta = " ".join(rotulo.split()[:3])
            rotulo = f"{base_corta} #{idx + 1}"[:30]
        rotulos_vistos.add(rotulo)

        plano = _asignar_plano_valido(esc, idx)
        if plano == "cinta_puerto":
            cinta_count += 1

        esc["texto_narracion"] = narracion
        esc["texto_pantalla"] = rotulo
        esc["tipo"] = "imagen"
        esc["plano"] = plano
        esc["prompt_imagen"] = BANCO_PLANOS[plano]

    # Asegurar que cinta_puerto aparezca al menos 2 veces en momentos clave (escenas 4 y 10)
    if cinta_count < 2 and len(filtradas) > 12:
        for pos in (4, 10):
            filtradas[pos]["plano"] = "cinta_puerto"
            filtradas[pos]["prompt_imagen"] = BANCO_PLANOS["cinta_puerto"]

    # RITMO FIJO POR CÓDIGO: Exactamente 6 gráficos distintos (1 cada 5 escenas, nunca 2 seguidos)
    plan_graficos = [
        (3, "INFOGRAFIA:TARJETA_VUELO", "70 OCUPANTES A BORDO"),
        (8, "INFOGRAFIA:ESQUEMA_SENSORES", "3 PUERTOS ESTÁTICOS TAPADOS"),
        (13, "INFOGRAFIA:MAPA_RUTA", "DESVÍO HACIA EL PACÍFICO"),
        (18, "INFOGRAFIA:PANEL_ALARMAS", "ALARMAS CONTRADICTORIAS"),
        (23, "INFOGRAFIA:GRAFICA_ALTITUD", "9700 PIES FALSOS EN RADAR"),
        (28, "INFOGRAFIA:CRONOLOGIA", "31 MINUTOS DE VUELO CIEGO"),
    ]
    for pos, codigo_inf, rotulo_inf in plan_graficos:
        if pos < len(filtradas):
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
    if len(escenas) < 24:
        raise ValueError(f"Escenas insuficientes tras validación: {len(escenas)}")

    datos["escenas"] = escenas
    datos["titulo_miniatura"] = "LA CINTA MORTAL"
    datos["prompt_miniatura"] = (
        f"{BANCO_PLANOS['cinta_puerto']}, bright blue lightning bolt in dark storm sky behind the fuselage, 8k"
    )

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
        json.dump(guion, f
