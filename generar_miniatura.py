import os
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance
from generar_imagen import _detectar_y_limpiar_texto_ocr

ANCHO, ALTO = 1280, 720
URL_FUENTE_ANTON = "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf"
RUTA_FUENTE_LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Anton-Regular.ttf")


def _obtener_fuente(tamano: int) -> ImageFont.FreeTypeFont:
    if not os.path.exists(RUTA_FUENTE_LOCAL) or os.path.getsize(RUTA_FUENTE_LOCAL) < 10_000:
        try:
            req = urllib.request.Request(URL_FUENTE_ANTON, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp, open(RUTA_FUENTE_LOCAL, "wb") as f:
                f.write(resp.read())
        except Exception as e:
            print(f" [Aviso] No se pudo descargar Anton.ttf, usando fuente del sistema: {e}")

    rutas_candidatas = [
        RUTA_FUENTE_LOCAL,
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for ruta in rutas_candidatas:
        if os.path.exists(ruta):
            try:
                return ImageFont.truetype(ruta, tamano)
            except Exception:
                continue
    return ImageFont.load_default()


def _realzar_iluminacion_y_degradado(imagen: Image.Image) -> Image.Image:
    """Ilumina la escena y aplica un degradado inferior más corto y suave para no oscurecer en exceso la base."""
    img_iluminada = ImageEnhance.Brightness(imagen).enhance(1.32)
    img_iluminada = ImageEnhance.Contrast(img_iluminada).enhance(1.15)
    base = img_iluminada.convert("RGBA")

    capa_oscura = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    draw = ImageDraw.Draw(capa_oscura)

    # Degradado más bajo (del píxel 440 al 720) y menos opaco (175) para que la parte inferior no quede demasiado negra
    inicio_y = 440
    for y in range(inicio_y, ALTO):
        progreso = (y - inicio_y) / (ALTO - inicio_y)
        alpha = int(175 * (progreso ** 1.7))
        draw.line([(0, y), (ANCHO, y)], fill=(0, 0, 0, alpha))

    return Image.alpha_composite(base, capa_oscura)


def _crear_gradiente_vertical(ancho: int, alto: int, color_arriba: tuple, color_abajo: tuple) -> Image.Image:
    gradiente = Image.new("RGBA", (ancho, alto))
    draw = ImageDraw.Draw(gradiente)
    for y in range(alto):
        t = y / max(alto - 1, 1)
        r = int(color_arriba[0] + (color_abajo[0] - color_arriba[0]) * t)
        g = int(color_arriba[1] + (color_abajo[1] - color_arriba[1]) * t)
        b = int(color_arriba[2] + (color_abajo[2] - color_arriba[2]) * t)
        draw.line([(0, y), (ancho, y)], fill=(r, g, b, 255))
    return gradiente


def generar_miniatura_desde_imagen(ruta_imagen_base: str, titulo_corto: str, ruta_salida: str):
    if not os.path.exists(ruta_imagen_base):
        raise RuntimeError(f"No existe imagen base: {ruta_imagen_base}")

    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)

    # Limpieza mediante Inpainting (sin oscurecer ni crear parches negros)
    _detectar_y_limpiar_texto_ocr(ruta_imagen_base, inpaint_si_falla=True)

    img_original = Image.open(ruta_imagen_base).convert("RGB")
    lienzo = ImageOps.fit(img_original, (ANCHO, ALTO), method=Image.Resampling.LANCZOS)
    lienzo = _realzar_iluminacion_y_degradado(lienzo)

    texto_limpio = titulo_corto[:32].upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "").strip()
    if not texto_limpio or "PITOT" in texto_limpio or "FALLO FATAL" in texto_limpio:
        texto_limpio = "LA CINTA MORTAL"
    palabras = texto_limpio.split()

    tamano_fuente = 152
    margen_maximo = 1140
    dummy_draw = ImageDraw.Draw(lienzo)

    while tamano_fuente > 65:
        fuente = _obtener_fuente(tamano_fuente)
        espacio = int(tamano_fuente * 0.28)
        anchos_palabras = [dummy_draw.textbbox((0, 0), p, font=fuente)[2] for p in palabras]
        ancho_total = sum(anchos_palabras) + espacio * (len(palabras) - 1)
        if ancho_total <= margen_maximo:
            break
        tamano_fuente -= 4

    bbox_ref = dummy_draw.textbbox((0, 0), texto_limpio, font=fuente)
    alto_texto = bbox_ref[3] - bbox_ref[1]
    x_inicial = (ANCHO - ancho_total) // 2
    y_pos = ALTO - alto_texto - 70 - bbox_ref[1]

    capa_sombra_amplia = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    draw_sombra_amplia = ImageDraw.Draw(capa_sombra_amplia)

    capa_sombra_corta = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    draw_sombra_corta = ImageDraw.Draw(capa_sombra_corta)

    x_cursor = x_inicial
    for i, palabra in enumerate(palabras):
        draw_sombra_amplia.text(
            (x_cursor, y_pos + 10),
            palabra,
            font=fuente,
            fill=(0, 0, 0, 255),
            stroke_width=14,
            stroke_fill=(0, 0, 0, 255),
        )
        draw_sombra_corta.text(
            (x_cursor, y_pos + 6),
            palabra,
            font=fuente,
            fill=(0, 0, 0, 230),
            stroke_width=6,
            stroke_fill=(0, 0, 0, 230),
        )
        x_cursor += anchos_palabras[i] + espacio

    capa_sombra_amplia = capa_sombra_amplia.filter(ImageFilter.GaussianBlur(radius=18))
    capa_sombra_corta = capa_sombra_corta.filter(ImageFilter.GaussianBlur(radius=4))

    lienzo = Image.alpha_composite(lienzo, capa_sombra_amplia)
    lienzo = Image.alpha_composite(lienzo, capa_sombra_corta)

    capa_trazo = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    draw_trazo = ImageDraw.Draw(capa_trazo)

    mascara_blanca = Image.new("L", (ANCHO, ALTO), 0)
    draw_blanca = ImageDraw.Draw(mascara_blanca)

    mascara_acento = Image.new("L", (ANCHO, ALTO), 0)
    draw_acento = ImageDraw.Draw(mascara_acento)

    x_cursor = x_inicial
    for i, palabra in enumerate(palabras):
        draw_trazo.text(
            (x_cursor, y_pos),
            palabra,
            font=fuente,
            fill=(0, 0, 0, 255),
            stroke_width=4,
            stroke_fill=(10, 10, 10, 255),
        )
        if len(palabras) > 1 and i < len(palabras) - 1:
            draw_blanca.text((x_cursor, y_pos), palabra, font=fuente, fill=255)
        else:
            draw_acento.text((x_cursor, y_pos), palabra, font=fuente, fill=255)
        x_cursor += anchos_palabras[i] + espacio

    lienzo = Image.alpha_composite(lienzo, capa_trazo)

    y_top = max(0, ALTO - alto_texto - 90)
    alto_grad = min(ALTO - y_top, alto_texto + 60)

    grad_blanco = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    grad_blanco.paste(_crear_gradiente_vertical(ANCHO, alto_grad, (255, 255, 255), (215, 220, 230)), (0, y_top))
    lienzo.paste(grad_blanco, (0, 0), mascara_blanca)

    grad_acento = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    grad_acento.paste(_crear_gradiente_vertical(ANCHO, alto_grad, (255, 240, 40), (255, 165, 0)), (0, y_top))
    lienzo.paste(grad_acento, (0, 0), mascara_acento)

    lienzo.convert("RGB").save(ruta_salida, quality=95)
    return ruta_salida
