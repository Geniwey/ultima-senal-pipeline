import os
import json
import sys
import re
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres el director jefe de un canal documental forense de aviación en YouTube. Escribe un guion de 34 escenas (4:45 - 5:00 min) con rigor técnico y máxima retención.

FICHA OFICIAL VERIFICADA (NO INVENTES NINGÚN DATO FUERA DE ESTA FICHA):
- Vuelo: Aeroperú 603 (Boeing 757-200, matrícula N52AW). Fecha: 2 de octubre de 1996. Ruta: Lima (Perú) a Santiago (Chile).
- Ocupantes: 70 personas (61 pasajeros y 9 tripulantes). Fallecieron todos.
- Causa oficial (Informe CIAA): Durante el lavado y pulido previo, un operario tapó los 3 puertos estáticos del lado izquierdo con cinta adhesiva plateada. Nadie la retiró antes del despegue.
- Cronología verificada:
  * 00:40 AM: Despegue nocturno desde Lima bajo niebla densa.
  * 00:42 AM: A los 2 minutos, velocímetro y altímetro muestran datos erróneos.
  * 00:44 AM: Declaran emergencia. El radar de Lima lee 9700 pies falsos porque el transpondedor envía la presión atrapada en el sensor tapado.
  * 00:55 AM: Suenan a la vez la alarma de pérdida (stick shaker) y la alarma de exceso de velocidad (overspeed).
  * 01:11 AM (31 minutos de vuelo): Creyendo volar a 9700 pies, el ala izquierda golpea las olas frente a Chancay. El avión se invierte e impacta en el Pacífico.

ESTRUCTURA OBLIGATORIA:
1. GANCHO EN FRÍO (Escenas 1 y 2): Empieza a las 01:10 AM en plena emergencia nocturna sobre el Pacífico con las alarmas sonando antes de rebobinar al despegue en Lima.
2. UN GIRO O PREGUNTA TÉCNICA cada 5 escenas.
3. CIERRE DOCUMENTAL: Termina en seco con una pregunta técnica sobre seguridad aérea. PROHIBIDO pedir que compartan el vídeo, den like o se suscriban.

REGLAS ESTRICTAS DE RÓTULOS ("texto_pantalla"):
- Debe tener entre 2 y 5 palabras EN ESPAÑOL CORRECTO, con un dato concreto (hora, cifra, lugar o hecho).
- Ejemplos válidos: "01:10 AM SOBRE EL PACÍFICO", "70 OCUPANTES A BORDO", "CINTA ADHESIVA PLATEADA", "RADAR LEE 9700 PIES", "ALARMAS CONTRADICTORIAS", "IMPACTO A LAS 01:11 AM".
- PROHIBIDO usar puntos suspensivos (...), palabras sueltas o frases vacías como: "REFLEXIÓN", "ESTADÍSTICAS", "MEMORIAL", "TECNOLOGÍA", "PREGUNTA", "COMPARTE EL CONOCIMIENTO", "PRECISIÓN IMPRESCINDIBLE", "CIENCIA DE PRECISIÓN", "LEGADO DE SEGURIDAD".

REGLAS DE IMAGEN ("prompt_imagen"):
- Describe siempre un sujeto físico concreto + plano + iluminación nocturna cinematográfica.
- PROHIBIDO caras humanas, personas, tablets, pantallas con texto, logos o marcas de aerolíneas.

Devuelve ÚNICAMENTE un JSON válido con 34 escenas:
{
  "titulo_video": "El error de 2$ que derribó al Vuelo 603 (Caso Aeroperú)",
  "descripcion_youtube": "Descripción documental de 3 párrafos citando el Informe Oficial de la CIAA.",
  "tags_youtube": ["aeroperu 603", "misterios de aviacion", "documental aereo", "caja negra", "seguridad aerea"],
  "comentario_fijado": "¿Qué medida de control crees que es más crítica para evitar un error así: la cinta de advertencia visible o la doble verificación prevuelo?",
  "prompt_miniatura": "Extreme macro close-up of a strip of glossy silver-grey metallic duct tape covering a round chrome static port sensor on a dark navy-blue aircraft fuselage, bright blue lightning bolt in the dark storm sky, smooth clean metal plate without any engraved numbers or text, 8k, photorealistic",
  "titulo_miniatura": "LA CINTA MORTAL",
  "escenas": [
    {
      "texto_narracion": "Frase documental clara de 18 a 24 palabras...",
      "texto_pantalla": "RÓTULO CON DATO CONCRETO",
      "duracion_segundos": 6.0,
      "prompt_imagen": "Concrete cinematic shot in English without people, faces, or text"
    }
  ]
}"""

BANCO_PLANOS = {
    "cinta": "Extreme macro close-up of glossy silver-grey metallic duct tape covering a round chrome static port sensor on a blank dark metallic Boeing 757 fuselage, moody hangar spotlight, smooth clean surface, no text, no letters, no numbers",
    "cabina": "Dark interior view from behind empty pilot seats looking through cockpit windshield into dense night fog and distant lightning over the black ocean, no faces, no people, no readable screens, no text",
    "avion_noche": "Wide side shot of an unmarked white commercial Boeing 757 flying through dark storm clouds at night over the ocean, navigation lights glowing, completely blank fuselage, no logos, no text",
    "ala_tormenta": "Close-up of a commercial airliner wingtip with red navigation strobe light cutting through dense night clouds and rain, dramatic lighting, no text",
    "impacto_mar": "Dramatic low-angle close-up of a commercial airliner wingtip slicing into dark turbulent Pacific ocean waves at night sending white sea spray into the air, storm lighting, no text",
    "mar_nocturno": "Aerial view looking down at dark churning Pacific ocean waves covered in white sea foam under rain and moonlight at night, dramatic documentary lighting, no text",
    "pista_lluvia": "Low angle shot of wet airport runway centerlines reflecting amber approach lights in dense night fog at Lima airport, no people, no text",
    "turbina": "Close-up exterior shot of a commercial jet engine turbine blades illuminated by amber runway lights in night mist, completely blank metal cowling, no text",
    "caja_negra": "Underwater spotlight illuminating a plain unmarked bright orange rectangular flight data recorder box resting on dark ocean seabed sand, completely blank painted metal surface without any serial numbers or letters, no text",
}

PALABRAS_NEGRAS_ROTULO = (
    "REFLEXIÓN", "ESTADÍSTICA", "MEMORIAL", "TECNOLOGÍA", "PREGUNTA",
    "COMPARTE", "PRECISIÓN IMPRESCINDIBLE", "CIENCIA DE PRECISIÓN",
    "LEGADO", "CONCLUSIÓN", "SUSCRÍBETE", "INFORMACIÓN", "ANÁLISIS",
)

CORRECCIONES_ORTOGRAFICAS = {
    r"\bOCCUPANTES\b": "OCUPANTES",
    r"\bNIEBLA DENSO\b": "NIEBLA DENSA",
    r"\bIMPÁCTO\b": "IMPACTO",
    r"\bININTERUMPIDA\b": "ININTERRUMPIDA",
    r"\bAERO PERÚ\b": "AEROPERÚ",
    r"\bAEROPERU\b": "AEROPERÚ",
}


def _corregir_ortografia_basica(texto: str) -> str:
    res = texto
    for patron, reemplazo in CORRECCIONES_ORTOGRAFICAS.items():
        res = re.sub(patron, reemplazo, res, flags=re.IGNORECASE)
    return res


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


def _segunda_pasada_auditoria_llm(cliente: Groq, escenas: list) -> list:
    """
    Puerta de calidad a temperature=0.0: revisa ortografía, concordancia gramatical
    y elimina cualquier rótulo genérico o cortado antes de renderizar.
    """
    resumen_entrada = [
        {"i": idx, "n": e["texto_narracion"], "r": e["texto_pantalla"]}
        for idx, e in enumerate(escenas)
    ]
    prompt_auditor = (
        "Eres corrector ortográfico y editor documental. Revisa esta lista JSON de escenas en español:\n"
        "1. Corrige CUALQUIER falta de ortografía o concordancia (ej. 'OCCUPANTES'->'OCUPANTES', 'NIEBLA DENSO'->'NIEBLA DENSA', 'IMPÁCTO'->'IMPACTO').\n"
        "2. Cada campo 'r' (rótulo en pantalla) debe estar en MAYÚSCULAS, tener entre 2 y 5 palabras completas SIN puntos suspensivos (...), "
        "y contener un dato concreto extraído de 'n' (hora, cifra, pieza o acción). Prohibido rótulos genéricos.\n"
        "3. Elimina de 'n' cualquier invitación a compartir, dar like o suscribirse.\n"
        "Devuelve ÚNICAMENTE el array JSON corregido con el mismo formato [{\"i\":0,\"n\":\"...\",\"r\":\"...\"}, ...]."
    )
    try:
        raw = _llamar_groq(
            cliente,
            [
                {"role": "system", "content": prompt_auditor},
                {"role": "user", "content": json.dumps(resumen_entrada, ensure_ascii=False)},
            ],
            MODELO_PRINCIPAL,
            temperatura=0.0,
        )
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        corregidos = json.loads(match.group(0)) if match else json.loads(raw.strip())
        mapa = {item["i"]: item for item in corregidos if isinstance(item, dict) and "i" in item}
        for idx, esc in enumerate(escenas):
            if idx in mapa:
                esc["texto_narracion"] = _corregir_ortografia_basica(mapa[idx].get("n", esc["texto_narracion"]).strip())
                esc["texto_pantalla"] = _corregir_ortografia_basica(mapa[idx].get("r", esc["texto_pantalla"]).strip().upper())
    except Exception as e:
        print(f"  [Aviso] Auditoría LLM omitida ({e}), aplicando corrector local.")
    return escenas


def _seleccionar_plano_coherente(narracion: str, rotulo: str, prompt_original: str, idx: int) -> str:
    """Garantiza coherencia 1-a-1 entre lo que se dice, el rótulo y la imagen (sin abstractos vacíos)."""
    texto = f"{narracion} {rotulo}".lower()
    if any(k in texto for k in ("cinta", "adhesiva", "puerto", "estático", "sensor", "operario", "lavado")):
        return BANCO_PLANOS["cinta"]
    if any(k in texto for k in ("impact", "golpe", "olas", "superficie", "invert", "desintegr", "chancay")):
        return BANCO_PLANOS["impacto_mar"]
    if any(k in texto for k in ("caja negra", "grabadora", "registrador", "submar", "fondo marino")):
        return BANCO_PLANOS["caja_negra"]
    if any(k in texto for k in ("cabina", "piloto", "tripulación", "palanca", "parabrisas", "instrumento")):
        return BANCO_PLANOS["cabina"]
    if any(k in texto for k in ("pista", "despeg", "aeropuerto", "lima", "tierra", "inspección")):
        return BANCO_PLANOS["pista_lluvia"]
    if any(k in texto for k in ("turbina", "motor", "velocidad")):
        return BANCO_PLANOS["turbina"]
    if any(k in texto for k in ("ala", "niebla", "nube", "tormenta")):
        return BANCO_PLANOS["ala_tormenta"]
    if any(k in texto for k in ("océano", "pacífico", "mar", "agua")):
        return BANCO_PLANOS["mar_nocturno"]

    # Si el prompt original es limpio y concreto, conservarlo sin palabras prohibidas; si no, avión nocturno
    patron_prohibido = re.compile(r"\b(face|portrait|man|woman|person|pilot|mechanic|passenger|ipad|tablet|screen|text|words|letters|logo|airsa|circle|abstract)\b", re.IGNORECASE)
    if len(prompt_original) > 25 and not patron_prohibido.search(prompt_original):
        return prompt_original
    return BANCO_PLANOS["avion_noche"] if idx % 2 == 0 else BANCO_PLANOS["ala_tormenta"]


def _procesar_y_enriquecer_escenas(escenas: list, cliente_groq: Groq = None) -> list:
    escenas_filtradas = []
    frases_vistas = set()

    for esc in escenas:
        narracion = _corregir_ortografia_basica(esc.get("texto_narracion", "").strip())
        # Eliminar frases finales de CTA ("Si este video te resultó informativo, compártelo...")
        narracion = re.sub(r"Si este v[íi]deo te result[óo].*$", "", narracion, flags=re.IGNORECASE).strip()
        if not narracion or any(p in narracion.lower() for p in ("suscr", "compártelo", "comparte este", "dale like")):
            continue

        rotulo = _corregir_ortografia_basica(esc.get("texto_pantalla", "").strip().upper())
        rotulo = rotulo.replace("...", "").replace("…", "").strip()

        firma = " ".join(re.findall(r"[a-záéíóúñ]+", narracion.lower())[:7])
        if firma in frases_vistas:
            continue
        frases_vistas.add(firma)

        esc["texto_narracion"] = narracion
        esc["texto_pantalla"] = rotulo
        escenas_filtradas.append(esc)

    escenas_filtradas = escenas_filtradas[:34]

    if cliente_groq is not None:
        escenas_filtradas = _segunda_pasada_auditoria_llm(cliente_groq, escenas_filtradas)

    rotulos_usados = set()
    for idx, esc in enumerate(escenas_filtradas):
        narracion = _corregir_ortografia_basica(esc["texto_narracion"])
        rotulo = _corregir_ortografia_basica(esc["texto_pantalla"]).replace("...", "").replace("…", "").strip()

        if len(rotulo.split()) < 2 or len(rotulo.split()) > 5 or any(b in rotulo for b in PALABRAS_NEGRAS_ROTULO):
            palabras_limpias = [w.strip(".,;:¡!¿?") for w in narracion.split() if len(w.strip(".,;:¡!¿?")) > 2]
            rotulo = " ".join(palabras_limpias[:4]).upper()

        if rotulo in rotulos_usados:
            rotulo = f"{rotulo} (FASE {idx + 1})"
        rotulos_usados.add(rotulo)

        esc["texto_narracion"] = narracion
        esc["texto_pantalla"] = rotulo
        esc["prompt_imagen"] = _seleccionar_plano_coherente(narracion, rotulo, esc.get("prompt_imagen", ""), idx)

    # PLANTILLA DE RITMO FIJA: 8 Infografías y Tarjetas de Datos por código (1 cada 4 escenas)
    plantilla_infografias = [
        (2, "INFOGRAFIA:TARJETA_VUELO", "70 OCUPANTES A BORDO"),
        (6, "INFOGRAFIA:ESQUEMA_SENSORES", "3 PUERTOS ESTÁTICOS TAPADOS"),
        (10, "INFOGRAFIA:MAPA_RUTA", "DESVÍO HACIA EL PACÍFICO"),
        (14, "INFOGRAFIA:PANEL_ALARMAS", "ALARMAS CONTRADICTORIAS"),
        (18, "INFOGRAFIA:GRAFICA_ALTITUD", "9700 PIES FALSOS EN RADAR"),
        (22, "INFOGRAFIA:PERFIL_IMPACTO", "IMPACTO A LAS 01:11 AM"),
        (26, "INFOGRAFIA:CRONOLOGIA", "31 MINUTOS DE VUELO CIEGO"),
        (30, "INFOGRAFIA:CAMBIOS_NORMATIVA", "PROTOCOLO OACI REFORZADO"),
    ]
    for pos, codigo_infografia, rotulo_fijo in plantilla_infografias:
        if pos < len(escenas_filtradas):
            escenas_filtradas[pos]["prompt_imagen"] = codigo_infografia
            escenas_filtradas[pos]["texto_pantalla"] = rotulo_fijo

    return escenas_filtradas


def _parsear_y_validar(texto: str, cliente_groq: Groq = None) -> dict:
    if not texto or not texto.strip():
        raise ValueError("Respuesta vacía del modelo")
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    datos = json.loads(match.group(0)) if match else json.loads(texto.strip())
    datos["escenas"] = _procesar_y_enriquecer_escenas(datos.get("escenas", []), cliente_groq=cliente_groq)
    datos["titulo_miniatura"] = "LA CINTA MORTAL"
    datos["prompt_miniatura"] = (
        "Extreme macro close-up of a strip of glossy silver-grey metallic duct tape covering a round chrome "
        "static port sensor on a dark navy-blue aircraft fuselage, bright blue lightning bolt in the dark storm sky, "
        "smooth clean brushed metal without any engraved numbers, letters, or markings, 8k, photorealistic"
    )
    desc = datos.get("descripcion_youtube", "").strip()
    fuente = (
        "\n\n📋 Fuente oficial verificada: Informe Final de la Comisión Investigadora de Accidentes de Aviación "
        "(CIAA - Ministerio de Transportes del Perú) y registros técnicos de la OACI."
    )
    if "Fuente oficial" not in desc:
        desc += fuente
    datos["descripcion_youtube"] = desc
    return datos


def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GROQ_API_KEY")
    cliente = Groq(api_key=api_key)

    mensajes = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Genera el guion forense con gancho en frío y datos exactos sobre: {tema}"},
    ]

    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            print(f"Llamando a Groq ({modelo})...")
            texto = _llamar_groq(cliente, mensajes, modelo, temperatura=0.3)
            datos = _parsear_y_validar(texto, cliente_groq=cliente)
            if len(datos.get("escenas", [])) >= 24:
                return datos
        except Exception as e:
            print(f" Fallo con {modelo}: {e}")

    print("Groq falló, probando Cerebras...")
    texto = _llamar_cerebras(mensajes, temperatura=0.3)
    datos = _parsear_y_validar(texto, cliente_groq=cliente)
    if len(datos.get("escenas", [])) >= 24:
        return datos
    raise RuntimeError("No se pudo generar un guion válido")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)
    guion = generar_guion(sys.argv[1])
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
