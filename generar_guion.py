import os
import json
import sys
import re
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres un director de documentales forenses de aviación para YouTube. Narra el caso en 38 escenas con una LÍNEA TEMPORAL ESTRICTAMENTE LINEAL (prohibido resumir todo el accidente al principio y luego volver atrás al hangar).

ESTRUCTURA CRONOLÓGICA ÚNICA (SIN SALTOS ATRÁS):
- Escenas 1 a 6 (El Error en Tierra): Noche del 1 al 2 de octubre de 1996 en el aeropuerto de Lima. El empleado Eleuterio Chacaliaza tapa los tres puertos estáticos del Boeing 757-200 con cinta adhesiva plateada para pulir el fuselaje. Termina el turno y nadie retira la cinta.
- Escenas 7 a 12 (El Despegue): 00:40 AM. El Capitán Eric Schreiber y el Copiloto David Fernández despegan con 70 personas rumbo a Santiago. Al cruzar los primeros 1000 pies en la niebla, el velocímetro y el altímetro quedan bloqueados.
- Escenas 13 a 24 (Ciegos sobre el Pacífico): La torre de Lima ve 9700 pies en su pantalla porque el transpondedor recibe el mismo dato falso del sensor tapado. En cabina saltan alarmas contradictorias: vibración de pérdida (baja velocidad) y alarma de exceso de velocidad al mismo tiempo.
- Escenas 25 a 30 (El Impacto): 01:11 AM (31 minutos de vuelo). Creyendo estar a 9700 pies, el ala izquierda roza las olas del océano Pacífico. El avión intenta elevarse pero invierte su giro y se estrella en el mar. Fallecen los 70 ocupantes.
- Escenas 31 a 38 (Hallazgo y Cambio Mundial): Barcos de la Marina iluminan los restos flotantes al amanecer.Un robot submarino recupera el registrador FDR a 150 metros de profundidad. Se descubre la cinta en el trozo de fuselaje y la FAA/OACI obligan a usar cubiertas rojas con banderines ("Remove Before Flight").

REGLAS DE RÓTULOS ("texto_pantalla"):
- 100% en ESPAÑOL correcto (escribe "FUSELAJE", nunca "FUSELAGE"; escribe "EXCESO DE VELOCIDAD", nunca "OVERSPEED").
- De 2 a 4 palabras informativas y únicas en MAYÚSCULAS.

REGLAS DE IMAGEN ("prompt_imagen" - CERO RADARES VERDES Y CERO ESCENAS OSCURAS):
- PROHIBIDO pedir radares verdes ("green radar").
- Cada "prompt_imagen" debe coincidir exactamente con el rótulo y pedir SIEMPRE buena iluminación ("well-lit, bright dramatic lighting, clear visibility"):
  * Si habla de la cinta: "Extreme close-up of smooth flat silver duct tape covering round static port holes on a glossy metallic airplane fuselage, bright studio spotlight, no text, no patterns".
  * Si habla del hangar: "Well-lit airport maintenance hangar at night with bright overhead floodlights illuminating the nose and landing gear of a commercial Boeing 757, no text".
  * Si habla de cabina: "Over-the-shoulder view of two pilots in a cockpit illuminated by bright amber and red instrument glow looking out at night clouds, no readable text".
  * Si habla del avión volando: "Commercial Boeing 757 flying above moonlit clouds at night, bright wing strobes and moonlight reflecting on fuselage, no logos, no text".
  * Si habla del roce o impacto en el mar: "Commercial airliner wingtip skimming across dark ocean waves at night with white water spray illuminated by landing lights, dramatic, no text".
  * Si habla de restos o fuselaje dañado: "Floating aircraft debris and metal fuselage fragments on the ocean surface at dawn illuminated by rescue searchlights, cinematic, no text".
  * Si habla de la caja negra: "Brightly lit underwater shot of an orange flight data recorder box on the sandy seabed illuminated by a bright white submersible spotlight, no text".

Devuelve ÚNICAMENTE un JSON válido:
{
  "titulo_video": "Título intrigante de máximo 60 caracteres",
  "descripcion_youtube": "Descripción de 3 párrafos con datos verificados y cita al Informe Oficial de la CIAA.",
  "tags_youtube": ["aviacion", "documental", "aeroperu 603", "caja negra"],
  "comentario_fijado": "Pregunta de debate sobre el caso",
  "prompt_miniatura": "Macro close-up of a piece of smooth flat silver adhesive tape partially covering a round chrome static port sensor on a dark blue metallic airplane fuselage, bright lightning bolt in the sky reflecting on the metal, well-lit, hyper-realistic photography, no geometric patterns, no text, no letters",
  "titulo_miniatura": "LA CINTA MORTAL",
  "escenas": [
    {
      "texto_narracion": "Narración en español de 18 a 25 palabras sin tecnicismos en inglés...",
      "texto_pantalla": "RÓTULO EN ESPAÑOL",
      "duracion_segundos": 6.0,
      "prompt_imagen": "Well-lit cinematic description matching the exact action of the scene, unmarked surface, no text"
    }
  ]
}"""


def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Documenta con orden cronológico estricto (1 sola línea temporal) y 38 escenas bien iluminadas el caso: {tema}"},
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
            {"role": "user", "content": f"Documenta con orden cronológico estricto (1 sola línea temporal) y 38 escenas bien iluminadas el caso: {tema}"},
        ],
        temperature=0.4,
        max_tokens=16000,
    )
    return respuesta.choices[0].message.content


def _deduplicar_y_blindar_escenas(escenas: list) -> list:
    escenas_filtradas = []
    rotulos_vistos = set()
    frases_vistas = set()

    correcciones_ortograficas = {
        "FUSELAGE": "FUSELAJE",
        "OVERSPEED": "EXCESO VELOCIDAD",
        "STICK SHAKER": "ALARMA DE PÉRDIDA",
    }

    for idx, esc in enumerate(escenas):
        narracion = esc.get("texto_narracion", "").strip()
        rotulo = esc.get("texto_pantalla", "").strip().upper()
        prompt_img = esc.get("prompt_imagen", "").strip()

        if not narracion:
            continue

        for mal, bien in correcciones_ortograficas.items():
            rotulo = rotulo.replace(mal, bien)

        narracion = re.sub(r"\boverspeed\b", "exceso de velocidad", narracion, flags=re.IGNORECASE)
        narracion = re.sub(r"\bstick shaker\b", "vibrador de palanca", narracion, flags=re.IGNORECASE)

        # Eliminar radares verdes si el LLM intenta colarlos y asegurar correspondencia visual
        if "radar" in prompt_img.lower() or "green" in prompt_img.lower():
            prompt_img = (
                "Over-the-shoulder view inside an airliner cockpit at night looking at a glowing flight path "
                "navigation line over the coast of Peru, warm cockpit lighting, no readable text"
            )
        if "fuselaje" in rotulo.lower() or "impacto" in rotulo.lower() or "raspa" in rotulo.lower():
            prompt_img = (
                "Dramatic shot of commercial airplane wingtip and damaged fuselage skimming dark ocean waves "
                "with white water spray illuminated by bright searchlights at night, well-lit, no text"
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
        "Macro close-up of a smooth flat silver adhesive tape strip partially covering a round metallic static port "
        "sensor on a dark blue Boeing 757 fuselage, bright lightning bolt in the night sky reflecting on the wet metal, "
        "well-lit studio spotlight, hyper-realistic photography, smooth tape texture, no geometric patterns, no text"
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
