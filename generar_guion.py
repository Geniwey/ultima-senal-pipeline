import os
import json
import sys
from groq import Groq

# Modelos ultra-estables de Groq que no dan error 404
MODELO_PRINCIPAL = "llama3-70b-8192"
MODELO_FALLBACK = "mixtral-8x7b-32768"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres guionista de un canal de YouTube de documentales de investigación aérea estilo Thriller y True Crime.

Reglas estrictas:
- Nunca describir restos humanos, cuerpos o imágenes gráficas.
- Español neutro, apto para España y Latinoamérica. Tono grave, misterioso y cinematográfico.
- TÍTULO CON BRECHA DE CURIOSIDAD: nunca descriptivo. Usa un título que genere una pregunta inevitable.
- GANCHO INICIAL: Arranca in media res con la situación límite (alarmas, caos) ANTES de dar el contexto.
- PROHIBICIÓN ABSOLUTA DE DESPEDIDAS: El guion debe terminar abruptamente en el clímax o en la resolución técnica (Cliffhanger). NO uses jamás palabras como 'suscríbete', 'gracias por ver', 'hasta la próxima' o moralejas largas. Termina en seco.
- PAUSAS: Usa puntos suspensivos (...) y comas estratégicas en "texto_narracion" para obligar a la IA de voz a hacer pausas dramáticas.
- Devuelve SOLO un JSON válido, sin texto adicional, con esta forma exacta:
{
  "titulo_video": "titulo con brecha de curiosidad, máximo 60 caracteres",
  "descripcion_youtube": "descripción de 3-4 párrafos para YouTube",
  "tags_youtube": ["10 a 15 tags cortos en español"],
  "comentario_fijado": "una pregunta polarizante/de debate para fijar en comentarios",
  "prompt_miniatura": "hyper-realistic cinematic photo of [un solo objeto clave], dark atmosphere, 8k",
  "titulo_miniatura": "2-4 palabras MAYÚSCULAS de máximo impacto",
  "escenas": [
    {
      "texto_narracion": "frase corta, 8-15 palabras, con pausas...",
      "texto_pantalla": "2-5 palabras MAYÚSCULAS IMPACTANTES",
      "duracion_segundos": 4.5,
      "prompt_imagen": "hyper-realistic, cinematic lighting, [sujeto exacto], dark background, no text"
    }
  ]
}

Cada escena debe durar entre 3.5 y 5.5 segundos. Genera entre 80 y 110 escenas para mantener un ritmo frenético."""

def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Tema del video: {tema}"},
        ],
        temperature=0.6,
        max_tokens=20000,
    )
    return respuesta.choices[0].message.content

def _llamar_cerebras(tema: str) -> str:
    from openai import OpenAI
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        raise RuntimeError("Falta CEREBRAS_API_KEY en las variables de entorno")
    
    cliente = OpenAI(api_key=api_key, base_url="https://api.cerebras.ai/v1")
    respuesta = cliente.chat.completions.create(
        model=MODELO_CEREBRAS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Tema del video: {tema}"},
        ],
        temperature=0.6,
        max_tokens=20000,
    )
    return respuesta.choices[0].message.content

def _limpiar_y_parsear(texto: str) -> dict:
    if not texto or not texto.strip():
        raise ValueError("Respuesta vacía del modelo")
    
    texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    datos = json.loads(texto)
    return datos

def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Falta la variable de entorno GROQ_API_KEY")
    
    cliente = Groq(api_key=api_key)
    
    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            print(f"Generando guion con Groq/{modelo}...")
            texto = _llamar_groq(cliente, tema, modelo)
            datos = _limpiar_y_parsear(texto)
            if "escenas" in datos and len(datos["escenas"]) >= 40:
                return datos
            print(f" Respuesta incompleta con {modelo}, probando siguiente...")
        except Exception as e:
            print(f" Fallo con {modelo}: {e}")
            
    try:
        print(f"Groq falló, probando Cerebras/{MODELO_CEREBRAS}...")
        texto = _llamar_cerebras(tema)
        datos = _limpiar_y_parsear(texto)
        if "escenas" in datos and len(datos["escenas"]) >= 40:
            return datos
        print(" Respuesta incompleta con Cerebras también.")
    except Exception as e:
        print(f" Fallo con Cerebras: {e}")
        
    raise RuntimeError("No se pudo generar un guion válido con ningún proveedor")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python generar_guion.py 'tema del accidente' salida.json")
        sys.exit(1)
    
    tema_arg, salida_arg = sys.argv[1], sys.argv[2]
    guion = generar_guion(tema_arg)
    
    with open(salida_arg, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
    
    print(f" Guion guardado en {salida_arg} ({len(guion['escenas'])} escenas)")
