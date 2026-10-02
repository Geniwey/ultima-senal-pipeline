import os
import json
import sys
from groq import Groq

MODELO_PRINCIPAL = "llama-3.1-70b-versatile"
MODELO_FALLBACK = "gemma2-9b-it"
MODELO_CEREBRAS = "llama3.1-70b"

SYSTEM_PROMPT = """Eres guionista de un canal de YouTube de misterios de aviación. El estilo visual es INFOGRAFÍA DE DATOS.

Reglas estrictas:
- Nunca describir restos humanos o cuerpos.
- Español neutro, apto para España y Latinoamérica. Tono grave de investigación.
- TÍTULO CON BRECHA DE CURIOSIDAD: nunca descriptivo. Usa un título que genere una pregunta.
- GANCHO INICIAL: Arranca en medio de la alerta, caos o advertencia.
- PAUSAS: Usa puntos suspensivos (...) y comas estratégicas en "texto_narracion" para la voz TTS.
- CERO DESPEDIDAS: Termina el guion en seco con la resolución final. NUNCA digas "suscríbete" ni "hasta el próximo vídeo".
- Devuelve SOLO un JSON válido, sin texto adicional:
{
  "titulo_video": "titulo con brecha, máximo 60 caracteres",
  "descripcion_youtube": "descripción para YouTube",
  "tags_youtube": ["tags", "cortos"],
  "comentario_fijado": "pregunta polarizante para comentarios",
  "prompt_miniatura": "infographic vector style diagram of [un solo objeto clave], radar background",
  "titulo_miniatura": "2-4 palabras MAYÚSCULAS",
  "escenas": [
    {
      "texto_narracion": "frase corta, 8-15 palabras, con pausas...",
      "texto_pantalla": "2-5 palabras MAYÚSCULAS",
      "duracion_segundos": 4.5,
      "prompt_imagen": "vector infographic, technical aviation schematic diagram of [sujeto exacto], dark mode, neon accents, flat design, no text"
    }
  ]
}

Genera entre 70 y 90 escenas para un ritmo ágil."""

def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Tema del video: {tema}"}],
        temperature=0.6, max_tokens=20000,
    )
    return respuesta.choices[0].message.content

def _llamar_cerebras(tema: str) -> str:
    from openai import OpenAI
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key: raise RuntimeError("Falta CEREBRAS_API_KEY")
    cliente = OpenAI(api_key=api_key, base_url="https://api.cerebras.ai/v1")
    respuesta = cliente.chat.completions.create(
        model=MODELO_CEREBRAS,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Tema del video: {tema}"}],
        temperature=0.6, max_tokens=20000,
    )
    return respuesta.choices[0].message.content

def _limpiar_y_parsear(texto: str) -> dict:
    if not texto or not texto.strip(): raise ValueError("Respuesta vacía")
    texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(texto)

def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: raise RuntimeError("Falta GROQ_API_KEY")
    cliente = Groq(api_key=api_key)
    
    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            print(f"Generando guion con Groq/{modelo}...")
            texto = _llamar_groq(cliente, tema, modelo)
            datos = _limpiar_y_parsear(texto)
            if "escenas" in datos and len(datos["escenas"]) >= 40: return datos
        except Exception as e: print(f" Fallo con {modelo}: {e}")
            
    try:
        print(f"Groq falló, probando Cerebras...")
        texto = _llamar_cerebras(tema)
        datos = _limpiar_y_parsear(texto)
        if "escenas" in datos and len(datos["escenas"]) >= 40: return datos
    except Exception as e: print(f" Fallo con Cerebras: {e}")
        
    raise RuntimeError("Fallo total al generar guion")

if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(1)
    tema_arg, salida_arg = sys.argv[1], sys.argv[2]
    guion = generar_guion(tema_arg)
    with open(salida_arg, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
