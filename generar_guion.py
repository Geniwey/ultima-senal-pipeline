import os
import json
import sys
import re
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres un director de documentales forenses de aviación para YouTube. Tu objetivo es narrar una historia cronológica impecable, sin repetir jamás escenas ni rótulos, de unos 5 a 6 minutos de duración (entre 36 y 42 escenas en total).

HECHOS HISTÓRICOS ESTRICTOS (SI EL TEMA ES AEROPERÚ 603):
- Fecha exacta: 2 de octubre de 1996 (madrugada, despegue 00:40 hora local). Avión: Boeing 757-200. Ruta: Lima a Santiago de Chile.
- Ocupantes: 70 personas a bordo (61 pasajeros y 9 tripulantes). Fallecieron los 70 (CERO sobrevivientes; NUNCA inventes sobrevivientes ni tornados).
- Pilotos: Capitán Eric Schreiber y Copiloto David Fernández.
- Causa real: El empleado de mantenimiento Eleuterio Chacaliaza colocó cinta adhesiva sobre los puertos estáticos para pulir y limpiar el fuselaje, y nadie la retiró antes del vuelo.
- Secuencia real: Al despegar a las 00:40, los altímetros y velocímetros empezaron a dar lecturas falsas. Se activó la alarma de pérdida (stick shaker) y de exceso de velocidad (overspeed) al mismo tiempo. La torre de Lima les daba una altitud de 9700 pies en el radar porque el transpondedor del avión leía el mismo sensor tapado. A las 01:11 AM, mientras volaban en la oscuridad sobre el mar pensando que estaban a 9700 pies, el ala izquierda rozó el agua y se estrellaron a los 31 minutos de vuelo.

PROHIBICIÓN ABSOLUTA DE BUCLES Y REPETICIONES:
- Avanza SIEMPRE hacia adelante en el tiempo desde la escena 1 hasta la escena 40. El avión solo despega UNA vez y solo impacta UNA vez.
- Cada "texto_pantalla" (rótulo) DEBE SER 100% ÚNICO en todo el vídeo. PROHIBIDO usar palabras sueltas genéricas como "TORRE", "PILOTOS", "OCÉANO", "TORNADO" o "RESCATE".
- Cada "texto_pantalla" debe ser un dato informativo o cronológico de 2 a 4 palabras en MAYÚSCULAS: "MANTENIMIENTO EN LIMA", "PUERTOS ESTÁTICOS TAPADOS", "00:40 AM - DESPEGUE", "ALTÍMETRO CONGELADO", "ALARMA CONTRADICTORIA", "FALSO DATO DE RADAR", "DESCENSO EN LA NIEBLA", "IMPACTO EN EL PACÍFICO", "70 VÍCTIMAS MORTALES", "HALLAZGO DEL FDR".

VARIEDAD VISUAL OBLIGATORIA ("prompt_imagen"):
- Cada escena debe mostrar exactamente lo que narra la voz en ese segundo, alternando entre estos planos sin texto:
  1. Cinta en el avión: "Extreme macro close-up of silver adhesive duct tape covering three small round static port sensor holes on a dark wet Boeing 757 fuselage at night, dramatic studio lighting, no text".
  2. Mantenimiento en hangar: " silhouette of an aircraft mechanic inspecting the lower fuselage of a commercial airliner inside a dark airport hangar at night, moody amber lights, no text".
  3. Torre de control: "Airport air traffic control tower illuminated in night fog overlooking wet runway lights, cinematic, no text".
  4. Cabina de pilotos (desde atrás): "Dark over-the-shoulder silhouette of two airline pilots inside a cockpit looking out the windshield into dark night clouds over the ocean, red warning glow, no readable text".
  5. Avión volando en la noche: "Commercial Boeing 757 airliner flying through dark night clouds above the ocean, unmarked blank fuselage, no logos, no text".
  6. Trayectoria / Radar abstracto: "Minimalist glowing green radar sweep line on a dark circular glass screen in a dark room, pure geometry, no numbers, no text".
  7. Impacto / Mar nocturno: "Dark turbulent Pacific ocean waves at night under heavy mist, searchlight beam reflecting on water, no text".
  8. Búsqueda con barcos y helicópteros: "Naval rescue ship and helicopter with bright searchlights over the ocean at dawn, cinematic documentary shot, no text".
  9. Caja negra submarina: "Underwater close-up of a damaged orange flight recorder box resting on the dark sandy seabed, rays of light, no text".

REGLAS DE MINIATURA:
- "titulo_miniatura": "LA CINTA MORTAL" (o 3 palabras de impacto directo sin tecnicismos).
- "prompt_miniatura": "Dramatic close-up of silver adhesive duct tape stuck over a round metallic sensor port on the side of a dark commercial airplane fuselage, with a stormy night sky and red emergency light reflecting on the wet metal, hyper-realistic, 8k, no text, no letters".

Devuelve ÚNICAMENTE un objeto JSON válido con entre 36 y 42 escenas:
{
  "titulo_video": "Título intrigante de máximo 60 caracteres",
  "descripcion_youtube": "Descripción documental de 3 párrafos con datos verificados y cita al Informe Oficial de la CIAA.",
  "tags_youtube": ["aviacion", "documental", "aeroperu 603", "caja negra"],
  "comentario_fijado": "Pregunta de debate sobre el caso",
  "prompt_miniatura": "Dramatic close-up of silver adhesive duct tape stuck over a round metallic sensor port on the side of a dark commercial airplane fuselage, with a stormy night sky and red emergency light reflecting on the wet metal, hyper-realistic, 8k, no text, no letters",
  "titulo_miniatura": "LA CINTA MORTAL",
  "escenas": [
    {
      "texto_narracion": "Narración clara y tensa de 18 a 25 palabras con números sin puntos como 9700 pies...",
      "texto_pantalla": "DATO CONCRETO DE 2-4 PALABRAS",
      "duracion_segundos": 6.0,
      "prompt_imagen": "Descripción en inglés específica y variada de la escena, unmarked surface, no text"
    }
  ]
}"""


def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Documenta de forma lineal, sin bucles y en 38 escenas únicas el caso real: {tema}"},
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
            {"role": "user", "content": f"Documenta de forma lineal, sin bucles y en 38 escenas únicas el caso real: {tema}"},
        ],
        temperature=0.4,
        max_tokens=16000,
    )
    return respuesta.choices[0].message.content


def _deduplicar_y_blindar_escenas(escenas: list) -> list:
    """
    Corta de raíz cualquier intento del LLM de entrar en bucle, repetir rótulos
    o inventar datos falsos (como sobrevivientes o tornados).
    """
    escenas_filtradas = []
    rotulos_vistos = set()
    frases_vistas = set()

    reemplazos_rotulos_genericos = {
        "CINTA ADHESIVA": "PUERTOS ESTÁTICOS TAPADOS",
        "TORRE": "TORRE DE CONTROL LIMA",
        "PILOTOS": "INCERTIDUMBRE EN CABINA",
        "TORNADO": "NOCHE CERRADA EN EL MAR",
        "OCÉANO": "DESCENSO HACIA EL PACÍFICO",
        "RESCATE": "OPERATIVO DE BÚSQUEDA",
        "CAJAS NEGRAS": "ANÁLISIS DE DATOS FDR",
    }

    palabras_corte = ("suscr", "gracias por ver", "like", "campanita", "comenta")

    for idx, esc in enumerate(escenas):
        narracion = esc.get("texto_narracion", "").strip()
        rotulo = esc.get("texto_pantalla", "").strip().upper()

        if not narracion or any(p in narracion.lower() or p in rotulo.lower() for p in palabras_corte):
            continue

        # Corregir alucinaciones históricas si el LLM menciona sobrevivientes o tornados
        narracion = re.sub(r"[Ss]olo dos (pasajeros|sobrevivientes).*?\.", "Lamentablemente, ninguno de los 70 ocupantes a bordo logró sobrevivir al impacto.", narracion)
        narracion = re.sub(r"[Ll]os dos sobrevivientes.*?\.", "Los equipos de rescate recuperaron los restos del fuselaje en la costa de Chancay.", narracion)
        narracion = narracion.replace("tornado", "frente de niebla").replace("TORNADO", "NIEBLA")

        if rotulo in reemplazos_rotulos_genericos:
            rotulo = reemplazos_rotulos_genericos[rotulo]

        # Evitar escenas duplicadas o en bucle comparando las primeras palabras
        firma_narracion = " ".join(re.findall(r"[a-záéíóúñ]+", narracion.lower())[:7])
        if firma_narracion in frases_vistas:
            continue
        frases_vistas.add(firma_narracion)

        # Si un rótulo se repite, lo hacemos único según el progreso del documental
        if rotulo in rotulos_vistos:
            rotulo = f"{rotulo} ({idx + 1})"
        rotulos_vistos.add(rotulo)

        esc["texto_narracion"] = narracion
        esc["texto_pantalla"] = rotulo
        escenas_filtradas.append(esc)

    # Limitar a máximo 42 escenas para mantener el vídeo en el rango óptimo de 5 a 6 minutos
    return escenas_filtradas[:42]


def _limpiar_y_parsear(texto: str) -> dict:
    if not texto or not texto.strip():
        raise ValueError("Respuesta vacía")
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    datos = json.loads(match.group(0)) if match else json.loads(texto.strip())

    datos["escenas"] = _deduplicar_y_blindar_escenas(datos.get("escenas", []))

    titulo_min = datos.get("titulo_miniatura", "").strip().upper()
    if not titulo_min or "PITOT" in titulo_min or "FALLO FATAL" in titulo_min:
        datos["titulo_miniatura"] = "LA CINTA MORTAL"

    # Forzar que la miniatura muestre siempre la cinta adhesiva en el sensor del avión
    datos["prompt_miniatura"] = (
        "Dramatic close-up of silver adhesive duct tape stuck over a round metallic sensor port on the side of a "
        "dark commercial Boeing 757 fuselage, with a stormy night sky, lightning bolt and red emergency light "
        "reflecting on the wet metal, hyper-realistic, 8k, no text, no letters"
    )

    desc = datos.get("descripcion_youtube", "")
    desc = desc.replace("2 de marzo de 1996", "2 de octubre de 1996")
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
