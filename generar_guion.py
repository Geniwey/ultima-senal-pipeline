import os
import json
import sys
import re
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres el director jefe de un canal documental forense de aviación. Escribe un guion de 34 escenas (5 minutos).

FICHA OFICIAL VERIFICADA (CASO AEROPERÚ 603):
- Vuelo: Aeroperú 603. Fecha: 2 de octubre de 1996. Ruta: Lima a Santiago.
- Ocupantes: 70 personas. Fallecieron todos.
- Causa oficial: Un operario tapó los 3 puertos estáticos con cinta adhesiva plateada. Nadie la retiró.
- Cronología: 00:40 AM Despegue. 00:42 Lecturas falsas. 00:44 Radar engañado (9700 pies falsos). 01:11 AM Impacto en el mar.

REGLAS DE NARRATIVA Y RÓTULOS ("texto_pantalla"):
1. EL RÓTULO DEBE SER INFORMATIVO (3 a 6 palabras con datos). Ejemplos VÁLIDOS: "9700 PIES FALSOS", "31 MINUTOS DE VUELO", "CINTA ADHESIVA PLATEADA", "ALARMA DE PÉRDIDA".
2. ESTÁ TOTALMENTE PROHIBIDO usar palabras sueltas o genéricas como: "REFLEXIÓN", "ESTADÍSTICAS", "MEMORIAL", "TECNOLOGÍA", "CAUSA", "PREGUNTA".
3. NO pidas suscripciones ni despidas el vídeo.

REGLAS DE IMAGEN ("prompt_imagen"):
- PROHIBIDO caras humanas, personas, tablets, textos, letras, logos o marcas de aerolíneas.
- Usa SIEMPRE planos limpios:
  * "Extreme macro close-up of glossy silver-grey metallic duct tape covering a round chrome sensor on a blank dark metallic aircraft fuselage, no text, no numbers"
  * "Side view of an unmarked white commercial airliner flying through dark storm clouds at night, blank fuselage, no logos, no text"
  * "Underwater view of a plain orange flight data recorder box buried in dark sand, completely blank surface, absolutely no text, no logos"

Devuelve ÚNICAMENTE un JSON válido:
{
  "titulo_video": "El error de 2$ que derribó al Vuelo 603 (Caso Aeroperú)",
  "descripcion_youtube": "Descripción...",
  "tags_youtube": ["aeroperu 603"],
  "comentario_fijado": "¿Crees que la responsabilidad fue del técnico o del protocolo?",
  "prompt_miniatura": "Extreme macro close-up of a strip of glossy silver-grey metallic duct tape covering a round chrome static port sensor on a dark navy-blue Boeing 757 fuselage, lightning bolt in the dark night sky, balanced studio lighting, 8k, no text, no numbers",
  "titulo_miniatura": "LA CINTA MORTAL",
  "escenas": [
    {
      "texto_narracion": "Frase de 18 a 25 palabras...",
      "texto_pantalla": "RÓTULO CON DATOS EXACTOS",
      "duracion_segundos": 6.0,
      "prompt_imagen": "Descripción en inglés SIN textos, logos ni caras"
    }
  ]
}"""

PLANOS_SEGUROS = [
    "Extreme macro close-up of glossy silver-grey metallic duct tape covering a round chrome static port sensor on a blank dark metallic aircraft fuselage, no text, no numbers",
    "Macro close-up of rain droplets running down the dark unmarked metallic fuselage of a commercial airliner at night, amber runway reflections, no text",
    "Exterior shot of a commercial airliner jet engine turbine spinning in heavy night fog, dramatic rim lighting, no logos, no text",
    "Wide shot of an unmarked commercial airliner banking sharply through dark storm clouds at night over the ocean, blank fuselage, no text",
    "Close-up of an aircraft wingtip red navigation strobe light flashing inside dense night clouds, moody atmosphere, no text",
    "Underwater view of a plain orange flight data recorder box resting on dark sandy seabed, completely blank surface, absolutely no text, no logos, illuminated by a spotlight",
    "Aerial view looking straight down at dark churning Pacific ocean waves at night under moonlight and rain, no ships, no text",
]

def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Genera el guion con RÓTULOS INFORMATIVOS LARGOS y sin letras en imágenes sobre: {tema}"},
        ],
        temperature=0.4,
        max_tokens=16000,
    )
    return respuesta.choices[0].message.content

def _llamar_cerebras(tema: str) -> str:
    from openai import OpenAI
    api_key = os.environ.get("CEREBRAS_API_KEY")
    cliente = OpenAI(api_key=api_key, base_url="https://api.cerebras.ai/v1")
    respuesta = cliente.chat.completions.create(
        model=MODELO_CEREBRAS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Genera el guion con RÓTULOS INFORMATIVOS LARGOS y sin letras en imágenes sobre: {tema}"},
        ],
        temperature=0.4,
        max_tokens=16000,
    )
    return respuesta.choices[0].message.content

def _procesar_y_enriquecer_escenas(escenas: list) -> list:
    escenas_limpias = []
    patron_caras_textos = re.compile(r"\b(face|portrait|man|woman|person|pilot|mechanic|passenger|ipad|tablet|screen|document|paper|text|words|letters|logo|airsa|ribbon|red tag)\b", re.IGNORECASE)
    palabras_basura_rotulo = ["REFLEXIÓN", "ESTADÍSTICA", "MEMORIAL", "TECNOLOGÍA", "PREGUNTA", "CAUSA", "CONSECUENCIA", "TRAGEDIA"]

    for idx, esc in enumerate(escenas):
        narracion = esc.get("texto_narracion", "").strip()
        rotulo = esc.get("texto_pantalla", "").strip().upper()
        prompt_img = esc.get("prompt_imagen", "").strip()

        if any(p in narracion.lower() for p in ("suscr", "gracias por", "comparte")):
            continue

        # Si el rótulo es una sola palabra inútil, forzamos un dato de la narración
        if len(rotulo.split()) < 2 or any(b in rotulo for b in palabras_basura_rotulo):
            palabras_narracion = narracion.split()
            rotulo = " ".join(palabras_narracion[:4]).upper() + "..."

        # Limpiar prompts peligrosos e inyectar la cinta plateada donde haga falta
        if patron_caras_textos.search(prompt_img) or "AIRSA" in prompt_img.upper():
            prompt_img = PLANOS_SEGUROS[idx % len(PLANOS_SEGUROS)]
        if "cinta" in rotulo.lower() or "tape" in prompt_img.lower():
            prompt_img = PLANOS_SEGUROS[0] # Forzar siempre la cinta plateada

        esc["texto_narracion"] = narracion
        esc["texto_pantalla"] = rotulo
        esc["prompt_imagen"] = prompt_img
        escenas_limpias.append(esc)

    escenas_limpias = escenas_limpias[:35]
    total = len(escenas_limpias)

    # Inyectar las 4 Infografías exactas (Mapas, gráficas y esquemas de sensores)
    if total >= 20:
        escenas_limpias[3]["prompt_imagen"] = "INFOGRAFIA:ESQUEMA_SENSORES"
        escenas_limpias[3]["texto_pantalla"] = "BLOQUEO DE SENSORES"
        escenas_limpias[int(total * 0.36)]["prompt_imagen"] = "INFOGRAFIA:MAPA_RUTA"
        escenas_limpias[int(total * 0.36)]["texto_pantalla"] = "DESVÍO HACIA EL OCÉANO"
        escenas_limpias[int(total * 0.58)]["prompt_imagen"] = "INFOGRAFIA:GRAFICA_ALTITUD"
        escenas_limpias[int(total * 0.58)]["texto_pantalla"] = "9700 PIES FALSOS"
        escenas_limpias[int(total * 0.80)]["prompt_imagen"] = "INFOGRAFIA:CRONOLOGIA"
        escenas_limpias[int(total * 0.80)]["texto_pantalla"] = "31 MINUTOS DE TERROR"

    return escenas_limpias

def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    cliente = Groq(api_key=api_key)
    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            texto = _llamar_groq(cliente, tema, modelo)
            match = re.search(r"\{.*\}", texto, re.DOTALL)
            datos = json.loads(match.group(0)) if match else json.loads(texto.strip())
            datos["escenas"] = _procesar_y_enriquecer_escenas(datos.get("escenas", []))
            return datos
        except Exception:
            pass
    texto = _llamar_cerebras(tema)
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    datos = json.loads(match.group(0)) if match else json.loads(texto.strip())
    datos["escenas"] = _procesar_y_enriquecer_escenas(datos.get("escenas", []))
    return datos

if __name__ == "__main__":
    guion = generar_guion(sys.argv[1])
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
