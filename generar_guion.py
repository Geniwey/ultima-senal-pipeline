import os
import json
import sys
import re
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres un director de documentales forenses de aviación para YouTube. Narra el caso en 38 escenas con una LÍNEA TEMPORAL ESTRICTAMENTE LINEAL de principio a fin.

ESTRUCTURA CRONOLÓGICA ÚNICA:
- Escenas 1 a 6 (El Error en Tierra): Noche del 1 al 2 de octubre de 1996 en Lima. El empleado Eleuterio Chacaliaza tapa los tres puertos estáticos del Boeing 757-200 con cinta adhesiva plateada para pulir el fuselaje. Termina su turno y nadie retira la cinta.
- Escenas 7 a 12 (El Despegue): 00:40 de la madrugada. El Capitán Eric Schreiber y el Copiloto David Fernández entran a la cabina de mando y despegan con 70 personas rumbo a Santiago. Al cruzar los 1000 pies en la niebla, el velocímetro y el altímetro quedan bloqueados.
- Escenas 13 a 24 (Ciegos sobre el Pacífico): En la torre de Lima ven 9700 pies porque el transpondedor recibe el mismo dato falso del sensor tapado. En la cabina de mando saltan alarmas contradictorias de baja velocidad y exceso de velocidad.
- Escenas 25 a 30 (El Impacto): A la una y once de la madrugada (31 minutos de vuelo), creyendo estar a 9700 pies, el ala izquierda roza las olas del océano Pacífico. El avión se invierte y se estrella en el mar. Fallecen los 70 ocupantes.
- Escenas 31 a 38 (Hallazgo y Cambio Mundial): Barcos de la Marina iluminan fragmentos flotantes al amanecer. Un robot submarino recupera la caja negra a 150 metros de profundidad. Se descubre la cinta en el fuselaje y la OACI obliga a usar cubiertas protectoras con banderines rojos de retirar antes del vuelo.

REGLAS ESTRICTAS DE RÓTULOS ("texto_pantalla"):
- PROHIBIDO CORTAR O ABREVIAR PALABRAS (NUNCA escribas "VELOCÍMETRO BLO", "LISTA DE VERIF", "INDICADORES CONTRA", "VIBRACIÓN CRÍT", "SOLICITUD CONTRO", "TURBULENCIA INVIS", "CAJA NEGRA RECUP" ni "ENTRENAMIENTO PILOT"). Escribe SIEMPRE las palabras enteras.
- NUNCA traduzcas "cockpit" como "cocina"; escribe siempre "CABINA DE MANDO".
- Cuida la concordancia en español ("NIEBLA DENSA", nunca "NIEBLA DENSO").
- Usa de 2 a 3 palabras completas en MAYÚSCULAS (máximo 24 caracteres en total).

REGLAS DE VARIEDAD VISUAL ("prompt_imagen" - PROHIBIDO REPETIR PLANOS O PONER TÚNELES):
- NO repitas el plano de los dos pilotos de espaldas más de 2 veces en todo el vídeo.
- PROHIBIDO pedir túneles, pasillos subterráneos o interiores de edificios en las escenas finales.
- Alterna constantemente entre planos exteriores del avión en las nubes, motores, alas sobre el mar, torre de control en la niebla, barco de rescate, robot submarino, caja negra y primer plano de los banderines rojos "Remove Before Flight" en el fuselaje de un avión en pista al amanecer.

Devuelve ÚNICAMENTE un JSON válido:
{
  "titulo_video": "Título intrigante de máximo 60 caracteres",
  "descripcion_youtube": "Descripción de 3 párrafos con datos verificados y cita al Informe Oficial de la CIAA.",
  "tags_youtube": ["aviacion", "documental", "aeroperu 603", "caja negra"],
  "comentario_fijado": "Pregunta de debate sobre el caso",
  "prompt_miniatura": "Extreme macro close-up of a piece of glossy silver-grey industrial duct tape with sticky adhesive edges partially covering a round metallic static port sensor on a dark navy blue airplane fuselage, lightning bolt in the night sky, realistic studio lighting, no text, no letters",
  "titulo_miniatura": "LA CINTA MORTAL",
  "escenas": [
    {
      "texto_narracion": "Narración 100% en español (sin palabras en inglés como cockpit o Remove Before Flight) y números juntos como 9700 pies...",
      "texto_pantalla": "2-3 PALABRAS COMPLETAS",
      "duracion_segundos": 6.0,
      "prompt_imagen": "Well-lit cinematic description matching the exact action of the scene, unmarked surface, no text"
    }
  ]
}"""


# Diccionario que repara automáticamente cualquier palabra truncada o mal traducida por el LLM
REPARACION_ROTULOS = {
    r"\bCOCINA\b": "CABINA",
    r"\bNIEBLA DENSO\b": "NIEBLA DENSA",
    r"\bVERIF\b": "VERIFICACIÓN",
    r"\bBLO\b": "BLOQUEADO",
    r"\bCONTRA\b": "OPUESTOS",
    r"\bCRÍT\b": "CRÍTICA",
    r"\bCONTRO\b": "CONTROL",
    r"\bINVIS\b": "INVISIBLE",
    r"\bRECUP\b": "HALLADA",
    r"\bPILOT\b": "PILOTOS",
    r"\bESTÁT\b": "ESTÁTICOS",
    r"\bMANTENIM\b": "MANTENIMIENTO",
    r"\b VELOC\b": " VELOCIDAD",
    r"\bINSTRUM\b": "INSTRUMENTOS",
    r"\bFUSELAGE\b": "FUSELAJE",
}

# Rotación de planos cinematográficos variados para evitar que se repita la cabina o salgan túneles
PLANOS_VARIADOS_VUELO = [
    "Exterior side view of a commercial Boeing 757 flying through dark night clouds with moonbeams reflecting on the blank metallic fuselage, well-lit, no text",
    "Close-up of a commercial airliner jet engine turbine spinning in heavy night mist with warm runway lights reflecting on wet metal, no text",
    "View from the wingtip of a commercial airliner banking left above dark ocean clouds at night, glowing red navigation light, no text",
    "Airport air traffic control tower illuminated by amber floodlights in night fog overlooking a wet tarmac, cinematic, no text",
    "Low angle shot of a commercial airliner flying low over dark ocean waves at night with landing lights piercing the fog, no text",
    "Close-up of aircraft nose cone and windshield wipers in heavy night rain, dramatic studio lighting, no text",
]


def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Documenta con palabras completas sin truncar y máxima variedad visual el caso: {tema}"},
        ],
        temperature=0.4,
        max_tokens=16000,
    )
    return respuesta.choices[0].message.content


def _llamar_cerebras(tema: str) -> str:
    from openai import OpenAI
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        raise RuntimeError("Falta CEREBRAS_API_KEY")
    cliente = OpenAI(api_key=api_key, base_url="https://api.cerebras.ai/v1")
    respuesta = cliente.chat.completions.create(
        model=MODELO_CEREBRAS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Documenta con palabras completas sin truncar y máxima variedad visual el caso: {tema}"},
        ],
        temperature=0.4,
        max_tokens=16000,
    )
    return respuesta.choices[0].message.content


def _reparar_rotulo(rotulo: str) -> str:
    r = rotulo.strip().upper()
    for patron, reemplazo in REPARACION_ROTULOS.items():
        r = re.sub(patron, reemplazo, r)
    return r


def _deduplicar_y_blindar_escenas(escenas: list) -> list:
    escenas_filtradas = []
    rotulos_vistos = set()
    frases_vistas = set()
    contador_cabina = 0

    for idx, esc in enumerate(escenas):
        narracion = esc.get("texto_narracion", "").strip()
        rotulo = _reparar_rotulo(esc.get("texto_pantalla", ""))
        prompt_img = esc.get("prompt_imagen", "").strip()

        if not narracion:
            continue

        # Limpiar anglicismos y números partidos con espacio en la narración
        narracion = re.sub(r"(\d)\s+(\d{3})\b", r"\1\2", narracion)
        narracion = re.sub(r"\bcockpit\b", "cabina de mando", narracion, flags=re.IGNORECASE)
        narracion = re.sub(r"\bRemove Before Flight\b", "retirar antes del vuelo", narracion, flags=re.IGNORECASE)
        narracion = re.sub(r"[Aa] los (1:11|una once)", "A la una y once de la madrugada", narracion)

        # Limitar planos de cabina ("cockpit" / "pilots") a máximo 2 en todo el vídeo para no cansar
        es_plano_cabina = any(k in prompt_img.lower() for k in ("cockpit", "pilot", "shoulder", "windshield"))
        if es_plano_cabina:
            contador_cabina += 1
            if contador_cabina > 2:
                prompt_img = PLANOS_VARIADOS_VUELO[idx % len(PLANOS_VARIADOS_VUELO)]

        # Reemplazar túneles, pasillos o imágenes abstractas en las escenas de normas/investigación
        if any(k in prompt_img.lower() for k in ("tunnel", "corridor", "hallway", "subway", "radar", "abstract", "blur")):
            prompt_img = PLANOS_VARIADOS_VUELO[idx % len(PLANOS_VARIADOS_VUELO)]

        if any(k in rotulo.lower() for k in ("norma", "bander", "regla", "inspecc", "lecci", "entrenam")):
            prompt_img = (
                "Close-up of a bright red safety streamer ribbon hanging from a metallic sensor cover on the side "
                "of a commercial airliner parked on a sunlit airport apron at dawn, cinematic, no text, no letters"
            )

        if any(k in rotulo.lower() for k in ("resto", "silencio", "marina", "impacto", "pacífico")):
            prompt_img = (
                "Small floating metal aircraft debris fragments on dark ocean waves at dawn illuminated by "
                "a naval rescue ship searchlight in the distance, no whole airplanes, no text"
            )

        firma_narracion = " ".join(re.findall(r"[a-záéíóúñ]+", narracion.lower())[:7])
        if firma_narracion in frases_vistas:
            continue
        frases_vistas.add(firma_narracion)

        if rotulo in rotulos_vistos:
            rotulo = f"{rotulo} II"
        rotulos_vistos.add(rotulo)

        esc["texto_narracion"] = narracion
        esc["texto_pantalla"] = rotulo
        esc["prompt_imagen"] = prompt_img
        escenas_filtradas.append(esc)

    return escenas_filtradas[:40]


def _limpiar_y_parsear(texto: str) -> dict:
    if not texto or not texto.strip():
        raise ValueError("Respuesta vacía")
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    datos = json.loads(match.group(0)) if match else json.loads(texto.strip())

    datos["escenas"] = _deduplicar_y_blindar_escenas(datos.get("escenas", []))

    titulo_min = datos.get("titulo_miniatura", "").strip().upper()
    if not titulo_min or "PITOT" in titulo_min or "FALLO FATAL" in titulo_min:
        datos["titulo_miniatura"] = "LA CINTA MORTAL"

    datos["prompt_miniatura"] = (
        "Extreme macro close-up of a strip of glossy silver-grey metallic duct tape with sticky adhesive edges "
        "partially covering a round chrome static port sensor on a dark slate-blue Boeing 757 fuselage, "
        "lightning bolt in the night sky reflecting on wet metal, hyper-realistic photography, no fabric texture, no text"
    )

    desc = datos.get("descripcion_youtube", "")
    if "Fuente" not in desc and "Informe" not in desc:
        desc = (
            desc.strip()
            + "\n\n📋 Fuente oficial verificada: Informe Final de la Comisión Investigadora de Accidentes de Aviación (CIAA - Ministerio de Transportes del Perú), anexos de la OACI y NTSB."
        )
    datos["descripcion_youtube"] = desc
    return datos


def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GROQ_API_KEY")
    cliente = Groq(api_key=api_key)

    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            print(f"Llamando a Groq ({modelo})...")
            texto = _llamar_groq(cliente, tema, modelo)
            datos = _limpiar_y_parsear(texto)
            if "escenas" in datos and len(datos["escenas"]) >= 25:
                return datos
        except Exception as e:
            print(f" Fallo con {modelo}: {e}")

    try:
        print("Groq falló, probando Cerebras...")
        texto = _llamar_cerebras(tema)
        datos = _limpiar_y_parsear(texto)
        if "escenas" in datos and len(datos["escenas"]) >= 25:
            return datos
    except Exception as e:
        print(f" Fallo con Cerebras: {e}")

    raise RuntimeError("No se pudo generar un guion válido con ningún proveedor")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)
    tema_arg, salida_arg = sys.argv[1], sys.argv[2]
    guion = generar_guion(tema_arg)
    with open(salida_arg, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
