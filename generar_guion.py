import os
import json
import sys
import re
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres el director jefe de un canal documental forense de aviación en YouTube. Escribe un guion de 34 escenas (5 minutos) con máxima retención y rigor histórico.

FICHA OFICIAL VERIFICADA (CASO AEROPERÚ 603):
- Vuelo: Aeroperú 603 (Boeing 757-200, matrícula N52AW). Fecha: 2 de octubre de 1996. Ruta: Lima (Perú) a Santiago (Chile).
- Ocupantes: 70 personas (61 pasajeros y 9 tripulantes). Fallecieron todos.
- Causa oficial (Informe CIAA): El operario Eleuterio Chacaliaza tapó los 3 puertos estáticos del lado izquierdo con cinta adhesiva plateada para lavar y pulir el fuselaje. Nadie retiró la cinta antes del despegue.
- Cronología:
  * 00:40 AM: Despegue de Lima con el Capitán Eric Schreiber y el Copiloto David Fernández.
  * 00:42 AM: Al subir entre la niebla nocturna, velocímetro y altímetro dan lecturas falsas.
  * 00:44 AM: Declaran emergencia. El radar de Lima muestra 9700 pies porque el transpondedor del avión envía el dato falso del sensor tapado.
  * 00:50 a 01:10 AM: Alarmas contradictorias en cabina (vibrador de pérdida por baja velocidad, alarma de exceso de velocidad y alerta de terreno GPWS).
  * 01:11 AM (31 min de vuelo): Creyendo volar a 9700 pies, el ala izquierda golpea las olas frente a Chancay. El avión se invierte y se estrella en el Pacífico.

ESTRUCTURA NARRATIVA:
1. GANCHO EN FRÍO (Escenas 1 y 2): Empieza en pleno clímax a medianoche sobre el Pacífico con las alarmas sonando antes de rebobinar al hangar.
2. GIROS CADA 5 ESCENAS: Introduce preguntas breves que mantengan la tensión.
3. PROHIBIDO PEDIR SUSCRIPCIONES: Termina el documental en seco con la pregunta de reflexión sobre la responsabilidad. NUNCA incluyas frases como "Suscríbete", "Gracias por acompañarnos" ni "Comparte este vídeo".

REGLAS ESTRICTAS DE IMAGEN ("prompt_imagen" - PROHIBIDO CARAS HUMANAS Y PANTALLAS):
- PROHIBIDO describir caras, rostros, retratos, personas de frente, pasajeros, mecánicos de frente, tablets, iPads, ordenadores, libretas, papeles o barcos repetidos.
- Usa SIEMPRE planos mecánicos, atmosféricos o siluetas extremas de espaldas en la oscuridad:
  * Para el mecánico o mantenimiento: "Extreme close-up of dark gloved hands applying silver duct tape over three small round static ports on a metallic Boeing 757 fuselage inside a dark hangar, no face, no people, no text".
  * Para inspección prevuelo: "Low angle exterior shot of commercial airliner landing gear tires and wet tarmac under amber hangar floodlights at night, no people, no text".
  * Para pilotos o cabina: "Dark silhouette from far behind of cockpit windshield looking out into dense night fog and lightning over the ocean, no faces, no dials, no text".
  * Para el vuelo sobre el mar: "Side view of a commercial Boeing 757 flying low through dark night mist above black ocean waves, glowing wingtip strobe light, unmarked fuselage, no text".
  * Para el golpe del ala en el agua: "Close-up of a commercial airliner wingtip slicing through a giant dark ocean wave at night sending white water spray into the air, dramatic lighting, no ships, no text".
  * Para la desintegración / impacto: "Turbulent dark ocean water surface at night covered in white sea foam and rain under storm clouds, no ships, no airplanes, no text".
  * Para normas o protocolos: "Close-up of a red safety streamer ribbon hanging from a metallic pitot cover on a parked airliner wing at dawn, no tablets, no papers, no text".

Devuelve ÚNICAMENTE un JSON válido con 34 escenas:
{
  "titulo_video": "El error de 2$ que derribó al Vuelo 603 (Caso Aeroperú)",
  "descripcion_youtube": "Descripción documental de 3 párrafos citando el Informe Oficial de la CIAA.",
  "tags_youtube": ["aeroperu 603", "misterios de aviacion", "documental aereo", "caja negra", "seguridad aerea"],
  "comentario_fijado": "¿Crees que la responsabilidad principal fue del técnico que colocó la cinta o del protocolo de inspección prevuelo?",
  "prompt_miniatura": "Extreme macro close-up of a strip of glossy silver-grey metallic duct tape covering a round chrome static port sensor on a dark navy-blue Boeing 757 fuselage, lightning bolt in the dark night sky, balanced studio lighting, 8k, no text, no numbers, no engravings",
  "titulo_miniatura": "LA CINTA MORTAL",
  "escenas": [
    {
      "texto_narracion": "Frase documental de 18 a 25 palabras...",
      "texto_pantalla": "RÓTULO CORTO DE 2-3 PALABRAS",
      "duracion_segundos": 6.0,
      "prompt_imagen": "Descripción cinematográfica en inglés SIN caras humanas, SIN pantallas y SIN barcos repetidos"
    }
  ]
}"""

# Banco de planos variados sin rostros ni barcos para sustituir automáticamente cualquier prompt con caras, tablets o mar repetido
PLANOS_SIN_CARAS_NI_BARCOS = [
    "Macro close-up of rain droplets running down the dark metallic fuselage of a commercial Boeing 757 at night, amber runway reflections, no text",
    "Exterior shot of a commercial airliner jet engine turbine spinning in heavy night fog, dramatic rim lighting, no people, no text",
    "Wide shot of a commercial airliner banking sharply through dark storm clouds at night over the ocean, unmarked fuselage, no text",
    "Close-up of an aircraft wingtip red navigation strobe light flashing inside dense night clouds, moody atmosphere, no text",
    "Low angle view of wet airport runway centerlines glowing in dense night mist as landing lights fade into the sky, no text",
    "Underwater view of a damaged orange flight data recorder box resting on dark sandy seabed illuminated by a spotlight beam, no text",
    "Close-up of a bright red safety ribbon hanging from a sensor cover on the side of an airplane fuselage at dawn, no text",
    "Aerial view looking straight down at dark churning Pacific ocean waves at night under moonlight and rain, no ships, no text",
]


def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Genera el guion definitivo sin caras humanas ni despedidas de suscripción sobre: {tema}"},
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
            {"role": "user", "content": f"Genera el guion definitivo sin caras humanas ni despedidas de suscripción sobre: {tema}"},
        ],
        temperature=0.4,
        max_tokens=16000,
    )
    return respuesta.choices[0].message.content


def _procesar_y_enriquecer_escenas(escenas: list) -> list:
    escenas_limpias = []
    rotulos_vistos = set()
    frases_vistas = set()
    barcos_usados = 0

    palabras_prohibidas_cierre = ("suscr", "gracias por acompa", "gracias por ver", "comparte este", "like", "campanita")
    patron_caras_o_tablets = re.compile(
        r"\b(face|faces|portrait|man|men|woman|women|person|people|pilot|pilots|captain|copilot|mechanic|technician|worker|passenger|passengers|crew|eleuterio|chacaliaza|schreiber|ipad|tablet|screen|pad|document|paper|clipboard|book|notebook|arrows)\b",
        re.IGNORECASE,
    )

    for idx, esc in enumerate(escenas):
        narracion = esc.get("texto_narracion", "").strip()
        rotulo = esc.get("texto_pantalla", "").strip().upper()
        prompt_img = esc.get("prompt_imagen", "").strip()

        if not narracion:
            continue

        # Eliminar de raíz cualquier escena final de "SUSCRÍBETE AHORA"
        if any(p in narracion.lower() or p in rotulo.lower() for p in palabras_prohibidas_cierre):
            continue

        narracion = re.sub(r"(\d)\s+(\d{3})\b", r"\1\2", narracion)
        narracion = re.sub(r"\bcockpit\b", "cabina de mando", narracion, flags=re.IGNORECASE)

        firma = " ".join(re.findall(r"[a-záéíóúñ]+", narracion.lower())[:7])
        if firma in frases_vistas:
            continue
        frases_vistas.add(firma)

        if rotulo in rotulos_vistos:
            rotulo = f"{rotulo} II"
        rotulos_vistos.add(rotulo)

        # MEDIDA DRÁSTICA: Si el prompt menciona personas, caras, nombres propios o tablets/papeles, sustituirlo por un plano mecánico limpio
        if patron_caras_o_tablets.search(prompt_img) or any(k in rotulo.lower() for k in ("eleuterio", "protocolo", "cultura", "factores", "inspección", "confianza", "emergencia")):
            prompt_img = PLANOS_SIN_CARAS_NI_BARCOS[idx % len(PLANOS_SIN_CARAS_NI_BARCOS)]

        # Evitar que el barco de rescate salga más de 1 sola vez en todo el vídeo
        if any(w in prompt_img.lower() for w in ("ship", "boat", "vessel", "searchlight")):
            barcos_usados += 1
            if barcos_usados > 1:
                prompt_img = PLANOS_SIN_CARAS_NI_BARCOS[(idx + 3) % len(PLANOS_SIN_CARAS_NI_BARCOS)]

        # Asegurar que el impacto/desintegración muestre el ala golpeando las olas y no un barco
        if any(k in rotulo.lower() for k in ("ala golpea", "invertido", "desintegrac", "impacto")):
            prompt_img = (
                "Dramatic close-up of a commercial airliner wingtip striking dark stormy ocean waves at night "
                "with massive white water spray, cinematic lighting, no ships, no people, no text"
            )

        esc["texto_narracion"] = narracion
        esc["texto_pantalla"] = rotulo
        esc["prompt_imagen"] = prompt_img
        escenas_limpias.append(esc)

    escenas_limpias = escenas_limpias[:35]
    total = len(escenas_limpias)

    # Inyectar las 4 Infografías de código exactamente 1 vez cada una
    if total >= 20:
        escenas_limpias[3]["prompt_imagen"] = "INFOGRAFIA:ESQUEMA_SENSORES"
        escenas_limpias[int(total * 0.36)]["prompt_imagen"] = "INFOGRAFIA:MAPA_RUTA"
        escenas_limpias[int(total * 0.58)]["prompt_imagen"] = "INFOGRAFIA:GRAFICA_ALTITUD"
        escenas_limpias[int(total * 0.80)]["prompt_imagen"] = "INFOGRAFIA:CRONOLOGIA"

    return escenas_limpias


def _limpiar_y_parsear(texto: str) -> dict:
    if not texto or not texto.strip():
        raise ValueError("Respuesta vacía")
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    datos = json.loads(match.group(0)) if match else json.loads(texto.strip())

    datos["escenas"] = _procesar_y_enriquecer_escenas(datos.get("escenas", []))
    datos["titulo_miniatura"] = "LA CINTA MORTAL"
    datos["prompt_miniatura"] = (
        "Extreme macro close-up of a strip of glossy silver-grey metallic duct tape covering a round chrome "
        "static port sensor on a dark navy-blue Boeing 757 fuselage, lightning bolt in the dark night sky, "
        "balanced studio lighting without overexposed highlights, completely smooth metal rim without engraved numbers, 8k, no text"
    )

    desc = datos.get("descripcion_youtube", "").strip()
    aviso_legal = (
        "\n\n📋 Fuente oficial verificada: Informe Final de la Comisión Investigadora de Accidentes de Aviación "
        "(CIAA - Ministerio de Transportes del Perú), anexos técnicos de la OACI y NTSB."
        "\nℹ️ Nota de transparencia: Las secuencias visuales de este documental son recreaciones cinematográficas "
        "e infografías técnicas generadas digitalmente para ilustrar los hechos reales del informe oficial."
    )
    if "Fuente oficial" not in desc:
        desc += aviso_legal
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
            if "escenas" in datos and len(datos["escenas"]) >= 24:
                return datos
        except Exception as e:
            print(f" Fallo con {modelo}: {e}")

    try:
        print("Groq falló, probando Cerebras...")
        texto = _llamar_cerebras(tema)
        datos = _limpiar_y_parsear(texto)
        if "escenas" in datos and len(datos["escenas"]) >= 24:
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
