import os
import json
import sys
import re
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres un documentalista forense de aviación para YouTube. Tu objetivo es narrar casos reales verificados con rigor histórico, alta tensión y claridad total para el espectador general.

PRECISIÓN HISTÓRICA Y CLARIDAD:
- Verifica fechas exactas (ej. Aeroperú 603 ocurrió el 2 de octubre de 1996, un Boeing 757-200 de Lima a Santiago con 70 personas, causado porque personal de mantenimiento dejó cinta adhesiva cubriendo los puertos estáticos tras limpiar el avión).
- NUNCA escribas números con puntos ni comas (escribe "12000 pies", NUNCA "12.000 pies").
- NUNCA uses códigos de aeropuerto sueltos como "LIM" o "SCL" (escribe "Lima" o "Santiago de Chile").
- NUNCA uses siglas crípticas sin explicar en los rótulos ni en la voz (en vez de "ADF ERRÁTICO" o "CVR GRITOS", usa "BRÚJULA SIN SEÑAL", "ALARMA EN CABINA", "GRABADORA DE VOZ", "TORRE DE CONTROL").

DURACIÓN Y RITMO (OBJETIVO 7 A 8 MINUTOS):
- Genera entre 60 y 70 escenas.
- Cada escena debe tener en "texto_narracion" 2 frases completas y tensas (entre 24 y 34 palabras por escena) para que cada clip dure unos 7 segundos y el documental alcance los 7-8 minutos de pura tensión sin relleno.
- PROHIBICIÓN ABSOLUTA DE DESPEDIDAS: NUNCA incluyas escenas diciendo "Gracias por ver", "Suscríbete" o "Memoria viva". Termina en seco con el dato final de la investigación.

COHERENCIA VISUAL ESTRICTA ("prompt_imagen" debe coincidir 100% con la escena):
- NO repitas siempre aviones en pista. Varía los planos según lo que ocurra en ese segundo:
  1. Si habla de los sensores o la cinta: "Extreme macro close-up of silver adhesive duct tape covering static port holes on a wet metallic aircraft fuselage at night, dramatic lighting, no text".
  2. Si habla del despegue o la torre: "Airport control tower illuminated in heavy night fog overlooking wet runway lights, cinematic, no text".
  3. Si habla de los pilotos en cabina: "Dark silhouette from behind of two airline pilots looking out the cockpit windshield into dark storm clouds and lightning over the ocean, no readable text".
  4. Si habla del vuelo en tormenta: "Commercial Boeing 757 flying high above dark ocean waves at night under lightning storm clouds, unmarked blank fuselage, no logos, no text".
  5. Si habla del impacto en el océano: "Dark turbulent ocean waves at night under heavy rain and searchlight beams, dramatic cinematic atmosphere, no airplanes on runway, no text".
  6. Si habla de búsqueda y rescate: "Rescue helicopters shining bright searchlights over dark ocean water at dawn, cinematic, no text".
  7. Si habla de las cajas negras: "Underwater shot of a damaged orange flight data recorder box resting on the dark sandy ocean floor, shafts of light, no text".

REGLAS DE MINIATURA:
- "titulo_miniatura": 2 a 3 palabras en MAYÚSCULAS que entienda todo el mundo y generen impacto inmediato (ej. "LA CINTA MORTAL", "TAPARON EL SENSOR", "CIEGOS EN EL MAR"). PROHIBIDO usar tecnicismos como "PITOT" o "ESTÁTICA".
- "prompt_miniatura": "Dramatic close-up of a commercial airliner wing and engine flying over dark ocean storm clouds at night, bright red emergency light reflecting on wet metal, lightning bolt in sky, high contrast, no text, no logos".

Devuelve ÚNICAMENTE un objeto JSON válido:
{
  "titulo_video": "Título magnético de máximo 60 caracteres",
  "descripcion_youtube": "Descripción documental de 3 párrafos con datos reales verificados y cita explícita al Informe Oficial.",
  "tags_youtube": ["aviacion", "documental", "misterio", "accidente aereo"],
  "comentario_fijado": "Pregunta de debate sobre el caso",
  "prompt_miniatura": "Dramatic close-up of a commercial airliner wing and engine flying over dark ocean storm clouds at night, bright red emergency light reflecting on wet metal, lightning bolt in sky, high contrast, no text, no logos",
  "titulo_miniatura": "LA CINTA MORTAL",
  "escenas": [
    {
      "texto_narracion": "Dos frases completas de 25 a 34 palabras narrando el suceso con números escritos sin puntos como 12000 pies...",
      "texto_pantalla": "RÓTULO CLARO DE 2-3 PALABRAS",
      "duracion_segundos": 7.0,
      "prompt_imagen": "Descripción en inglés exacta de la escena visual correspondiente, unmarked fuselage, no text, no logos"
    }
  ]
}"""


def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Documenta con rigor histórico y 65 escenas detalladas el caso: {tema}"},
        ],
        temperature=0.5,
        max_tokens=22000,
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
            {"role": "user", "content": f"Documenta con rigor histórico y 65 escenas detalladas el caso: {tema}"},
        ],
        temperature=0.5,
        max_tokens=22000,
    )
    return respuesta.choices[0].message.content


def _limpiar_y_parsear(texto: str) -> dict:
    if not texto or not texto.strip():
        raise ValueError("Respuesta vacía")
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    datos = json.loads(match.group(0)) if match else json.loads(texto.strip())

    # 1. Filtrar cualquier escena final que pida suscribirse o dé las gracias
    escenas_limpias = []
    palabras_prohibidas = ("suscr", "gracias por ver", "like", "campanita", "comenta")
    for esc in datos.get("escenas", []):
        narracion_lower = esc.get("texto_narracion", "").lower()
        rotulo_lower = esc.get("texto_pantalla", "").lower()
        if any(p in narracion_lower or p in rotulo_lower for p in palabras_prohibidas):
            continue
        escenas_limpias.append(esc)
    datos["escenas"] = escenas_limpias

    # 2. Blindaje del título de la miniatura (prohibido usar tecnicismos como PITOT o títulos genéricos)
    titulo_min = datos.get("titulo_miniatura", "").strip().upper()
    if not titulo_min or "PITOT" in titulo_min or "FALLO FATAL" in titulo_min:
        datos["titulo_miniatura"] = "LA CINTA MORTAL"

    # 3. Asegurar fuente oficial verificable en la descripción
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
            if "escenas" in datos and len(datos["escenas"]) >= 35:
                return datos
        except Exception as e:
            print(f" Fallo con {modelo}: {e}")

    try:
        print("Groq falló, probando Cerebras...")
        texto = _llamar_cerebras(tema)
        datos = _limpiar_y_parsear(texto)
        if "escenas" in datos and len(datos["escenas"]) >= 35:
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
