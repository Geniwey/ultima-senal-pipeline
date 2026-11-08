import os
import json
import sys
import re
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres el director jefe de un canal documental de aviación de élite en YouTube. Tu misión es escribir un guion de 34 escenas (4.5 a 5.5 minutos) con retención magnética y rigor forense absoluto.

FICHA OFICIAL VERIFICADA (PROHIBIDO INVENTAR DATOS FUERA DE ESTA FICHA):
- Vuelo: Aeroperú 603 (Boeing 757-200, matrícula N52AW). Fecha: 2 de octubre de 1996. Ruta: Lima (Perú) a Santiago (Chile).
- Víctimas: 70 ocupantes (61 pasajeros y 9 tripulantes). Fallecieron todos. No hubo explosión submarina; el avión se partió al impactar el agua a alta velocidad tras rozar las olas con el ala izquierda.
- Causa oficial (Informe CIAA): El técnico Eleuterio Chacaliaza tapó los 3 puertos estáticos del lado izquierdo con cinta adhesiva plateada para lavar y pulir el fuselaje. Nadie retiró la cinta en el cambio de turno ni en la inspección exterior prevuelo.
- Cronología exacta:
  * 00:40 AM: Despegue de Lima con el Capitán Eric Schreiber y el Copiloto David Fernández.
  * 00:42 AM: Al subir entre la niebla nocturna, el altímetro y el velocímetro quedan congelados/erráticos.
  * 00:44 AM: Declaran emergencia. La torre de Lima ve 9700 pies en su radar porque el transpondedor del avión recibe el dato falso del mismo sensor tapado.
  * 00:50 a 01:10 AM: En cabina saltan alarmas contradictorias (vibrador de pérdida por baja velocidad y alarma de exceso de velocidad a la vez, más alarma de terreno GPWS que los pilotos creen falsa).
  * 01:11 AM (31 minutos de vuelo): Creyendo estar a 9700 pies sobre el mar, el ala izquierda golpea las olas frente a Chancay. El avión gira invertido y se estrella en el Pacífico.

ESTRUCTURA DE RETENCIÓN 10/10:
1. GANCHO EN FRÍO (Escenas 1 y 2): PROHIBIDO empezar con "En la noche del 1 de octubre...". Abre los primeros 10 segundos en pleno clímax: a medianoche sobre el Pacífico, todas las alarmas suenan a la vez mientras 70 personas caen hacia el mar negro por culpa de un trozo de cinta adhesiva de dos dólares. Luego rebobina al hangar.
2. GIROS DE RETENCIÓN CADA 5 ESCENAS: Plantea micro-preguntas o giros tensos ("Pero había una trampa oculta que ni siquiera la torre de control podía ver...", "Lo que los pilotos no sabían es que el radar les estaba mintiendo...").
3. CIERRE CON PREGUNTA ABIERTA: La última escena cierra con la lección del caso y una pregunta directa sobre la responsabilidad en seguridad aérea.

REGLAS DE RÓTULOS ("texto_pantalla"):
- 2 a 3 palabras COMPLETAS en español (máximo 22 caracteres). PROHIBIDO cortar palabras y PROHIBIDO inventar "EXPLOSIÓN SUBMARINA".

REGLAS DE IMAGEN ("prompt_imagen"):
- Cada prompt debe describir visualmente la frase exacta de esa escena, pero NUNCA pidas: libros, cuadernos, informes en papel, tablones con fotos, lápidas, cruces, monumentos con texto, ni aviones flotando enteros en el mar.
- Para el impacto y el mar, pide únicamente olas oscuras del océano de noche con haces de luz de búsqueda o pequeños fragmentos metálicos irreconocibles entre la espuma.

Devuelve ÚNICAMENTE un JSON válido con 34 escenas:
{
  "titulo_video": "El error de 2$ que derribó al Vuelo 603 (Caso Aeroperú)",
  "descripcion_youtube": "Descripción documental de 3 párrafos con ficha técnica, cita al Informe Oficial de la CIAA y aviso de recreación visual.",
  "tags_youtube": ["aeroperu 603", "misterios de aviacion", "documental aereo", "caja negra", "seguridad aerea"],
  "comentario_fijado": "¿Crees que la culpa principal fue del técnico que puso la cinta o del protocolo de inspección antes del despegue? Te leo abajo.",
  "prompt_miniatura": "Extreme macro close-up of a strip of glossy silver-grey metallic duct tape partially covering a round chrome static port sensor on a deep electric-blue Boeing 757 fuselage, bright white lightning bolt in the stormy night sky reflecting on wet metal, high contrast, 8k, no text",
  "titulo_miniatura": "LA CINTA MORTAL",
  "escenas": [
    {
      "texto_narracion": "Frase potente de 18 a 25 palabras...",
      "texto_pantalla": "RÓTULO CORTO Y REAL",
      "duracion_segundos": 6.0,
      "prompt_imagen": "Descripción cinematográfica en inglés sin texto ni papeles ni aviones flotando"
    }
  ]
}"""

REPARACION_ROTULOS = {
    r"\bEXPLOSI[ÓO]N SUBMARINA\b": "IMPACTO EN EL PACÍFICO",
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
    r"\bFUSELAGE\b": "FUSELAJE",
}


def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Escribe el guion definitivo con Gancho en Frío en la escena 1 y rigor total sobre: {tema}"},
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
            {"role": "user", "content": f"Escribe el guion definitivo con Gancho en Frío en la escena 1 y rigor total sobre: {tema}"},
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


def _procesar_y_enriquecer_escenas(escenas: list) -> list:
    escenas_limpias = []
    rotulos_vistos = set()
    frases_vistas = set()

    for idx, esc in enumerate(escenas):
        narracion = esc.get("texto_narracion", "").strip()
        rotulo = _reparar_rotulo(esc.get("texto_pantalla", ""))
        prompt_img = esc.get("prompt_imagen", "").strip()

        if not narracion:
            continue

        # Prohibir la alucinación de la explosión submarina en la voz y en el rótulo
        if "explosión" in narracion.lower() and "agua" in narracion.lower():
            narracion = "La violencia del impacto contra las olas partió la estructura del avión en segundos, apagando toda señal en mitad de la noche."
        narracion = re.sub(r"(\d)\s+(\d{3})\b", r"\1\2", narracion)
        narracion = re.sub(r"\bcockpit\b", "cabina de mando", narracion, flags=re.IGNORECASE)

        firma = " ".join(re.findall(r"[a-záéíóúñ]+", narracion.lower())[:7])
        if firma in frases_vistas:
            continue
        frases_vistas.add(firma)

        if rotulo in rotulos_vistos:
            rotulo = f"{rotulo} II"
        rotulos_vistos.add(rotulo)

        # Bloquear objetos que generan texto basura (libretas, lápidas, tablones, aviones flotando enteros)
        if any(w in prompt_img.lower() for w in ("notebook", "logbook", "book", "paper", "board", "chart", "plaque", "memorial", "tombstone", "cross", "grave")):
            prompt_img = (
                "Cinematic close-up of a commercial airliner metallic fuselage and wing under dramatic amber hangar floodlights at night, "
                "rain droplets on dark metal, shallow depth of field, no text, no letters"
            )
        if any(w in prompt_img.lower() for w in ("floating", "ocean", "sea", "water", "debris", "wreckage")) and "wingtip" not in prompt_img.lower():
            prompt_img = (
                "Dark turbulent ocean waves at night illuminated by a bright white searchlight beam from a distant naval rescue ship "
                "cutting through sea mist, dramatic atmosphere, no airplanes on water, no text"
            )

        esc["texto_narracion"] = narracion
        esc["texto_pantalla"] = rotulo
        esc["prompt_imagen"] = prompt_img
        escenas_limpias.append(esc)

    escenas_limpias = escenas_limpias[:36]
    total = len(escenas_limpias)

    # Inyectar las 4 Infografías de Datos Reales hechas con código en los puntos exactos de la historia
    if total >= 20:
        escenas_limpias[3]["prompt_imagen"] = "INFOGRAFIA:ESQUEMA_SENSORES"
        escenas_limpias[int(total * 0.35)]["prompt_imagen"] = "INFOGRAFIA:MAPA_RUTA"
        escenas_limpias[int(total * 0.55)]["prompt_imagen"] = "INFOGRAFIA:GRAFICA_ALTITUD"
        escenas_limpias[int(total * 0.78)]["prompt_imagen"] = "INFOGRAFIA:CRONOLOGIA"

    return escenas_limpias


def _limpiar_y_parsear(texto: str) -> dict:
    if not texto or not texto.strip():
        raise ValueError("Respuesta vacía")
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    datos = json.loads(match.group(0)) if match else json.loads(texto.strip())

    datos["escenas"] = _procesar_y_enriquecer_escenas(datos.get("escenas", []))
    datos["titulo_miniatura"] = "LA CINTA MORTAL"
    datos["prompt_miniatura"] = (
        "Extreme macro close-up of a strip of glossy silver-grey metallic duct tape partially covering a round chrome "
        "static port sensor on a vibrant deep electric-blue Boeing 757 fuselage, bright white lightning bolt in the "
        "stormy night sky reflecting on wet metal, high contrast, 8k, no text, no letters"
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
