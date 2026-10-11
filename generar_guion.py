import os
import json
import sys
import re
from groq import Groq

MODELO_PRINCIPAL = "llama-3.1-70b-versatile"
MODELO_FALLBACK = "gemma2-9b-it"
MODELO_CEREBRAS = "llama3.1-70b"

SYSTEM_PROMPT = """Eres el mejor guionista de YouTube de misterios de aviación. El estilo visual es RENDER 3D CINEMÁTICO.

Reglas estrictas para evitar vídeos aburridos (EFECTO POWERPOINT):
1. RITMO FRENÉTICO: Crea un mínimo de 45 escenas. Cada escena debe durar máximo 4.5 segundos.
2. TEXTO DE PANTALLA DINÁMICO: El campo "texto_pantalla" (2-4 palabras MAYÚSCULAS) DEBE CAMBIAR en cada maldita escena. NUNCA dejes el mismo texto en escenas consecutivas.
3. CERO TEXTO EN IMÁGENES: En "prompt_imagen", NUNCA pidas carteles, documentos, pantallas con letras, ni palabras en inglés. Pide: "cinematic macro photography of airplane parts, dark clouds, glowing lights, NO TEXT".
4. ESTRUCTURA: Arranca con 5 segundos de tensión máxima en la escena 1. Luego da contexto, investiga y resuelve.
5. NO DESPEDIDAS.

Devuelve SOLO un JSON válido con esta estructura:
{
  "titulo_video": "titulo con brecha, máximo 60 caracteres",
  "descripcion_youtube": "descripción para YouTube",
  "tags_youtube": ["tags", "cortos"],
  "comentario_fijado": "pregunta polarizante para comentarios",
  "prompt_miniatura": "Hyper-realistic photography, terrifying view of a massive dark storm from an airplane window, red emergency light reflection, NO TEXT",
  "titulo_miniatura": "¿QUÉ VIERON LOS PILOTOS?",
  "escenas": [
    {
      "texto_narracion": "frase corta, 8-15 palabras, con pausas...",
      "texto_pantalla": "FALLO INICIAL",
      "duracion_segundos": 4.5,
      "prompt_imagen": "cinematic 3D render of an airplane flying into a massive dark storm cloud, dramatic lighting, NO TEXT"
    }
  ]
}"""

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
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match: return json.loads(match.group(0))
    return json.loads(texto.strip())

def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: raise RuntimeError("Falta GROQ_API_KEY")
    cliente = Groq(api_key=api_key)
    
    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            texto = _llamar_groq(cliente, tema, modelo)
            datos = _limpiar_y_parsear(texto)
            if "escenas" in datos and len(datos["escenas"]) >= 20: return datos
        except Exception: pass
            
    try:
        texto = _llamar_cerebras(tema)
        datos = _limpiar_y_parsear(texto)
        if "escenas" in datos and len(datos["escenas"]) >= 20: return datos
    except Exception: pass
        
    raise RuntimeError("No se pudo generar un guion válido")

if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(1)
    tema_arg, salida_arg = sys.argv[1], sys.argv[2]
    guion = generar_guion(tema_arg)
    with open(salida_arg, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
