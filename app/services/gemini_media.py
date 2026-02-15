import base64
import time
from io import BytesIO
from typing import List, Optional

from google import genai
from google.genai import types
from PIL import Image


def _decode_b64_maybe(data) -> bytes:
    """
    En Nano Banana / Imagen es común recibir base64 en string.
    Si ya es bytes crudos, se devuelve tal cual.
    """
    if data is None:
        return b""
    if isinstance(data, (bytes, bytearray)):
        # a veces ya viene raw; a veces viene base64 bytes
        try:
            # si es base64, esto suele funcionar
            return base64.b64decode(data, validate=False)
        except Exception:
            return bytes(data)
    if isinstance(data, str):
        return base64.b64decode(data, validate=False)
    return bytes(data)

def _extract_first_image_bytes_from_response(resp) -> Optional[bytes]:
    # Nano Banana devuelve parts con inline_data (base64)
    for part in getattr(resp, "parts", []) or []:
        if getattr(part, "inline_data", None) is not None:
            # En python-genai: part.inline_data.data suele ser base64
            blob = part.inline_data
            raw = getattr(blob, "data", None)
            if raw:
                return _decode_b64_maybe(raw)
        # En algunos builds hay part.as_image()
        try:
            img = part.as_image()
            if img:
                buf = BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue()
        except Exception:
            pass
    return None

class GeminiMedia:
    def __init__(
        self,
        model_image_fast: str,
        model_image_hd: str,
        model_video: str,
    ):
        self.model_image_fast = model_image_fast
        self.model_image_hd = model_image_hd
        self.model_video = model_video

    def validate_api_key(self, api_key: str) -> bool:
        # prueba sencilla: generar contenido de texto sin costo grande
        client = genai.Client(api_key=api_key)
        r = client.models.generate_content(model="gemini-2.0-flash", contents=["ping"])
        return bool(getattr(r, "text", None) or getattr(r, "parts", None))

    def generate_image(self, api_key: str, prompt: str, hd: bool) -> bytes:
        client = genai.Client(api_key=api_key)

        model = self.model_image_hd if hd else self.model_image_fast
        config = types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])

        if hd:
            # ayudamos al modelo a priorizar calidad
            prompt = f"{prompt}\n\nOutput: photorealistic, high fidelity, upscale to 4K, sharp details."

        resp = client.models.generate_content(
            model=model,
            contents=[prompt],
            config=config,
        )

        img_bytes = _extract_first_image_bytes_from_response(resp)
        if not img_bytes:
            raise RuntimeError("No se recibió imagen del modelo.")
        return img_bytes

    def edit_images_realistic_montage(self, api_key: str, instruction: str, images: List[bytes], hd: bool) -> bytes:
        """
        Montaje realista por defecto con 2 imágenes.
        Usamos Nano Banana (gemini-2.5-flash-image) o Pro en HD.
        """
        if len(images) != 2:
            raise ValueError("Se requieren exactamente 2 imágenes para montaje.")

        client = genai.Client(api_key=api_key)

        model = self.model_image_hd if hd else self.model_image_fast
        config = types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])

        # reglas duras (lo que definiste)
        hard_rules = (
            "Make a single, realistic, natural-looking photo montage.\n"
            "Do NOT change faces or bodies. Keep identities exactly the same.\n"
            "No cartoon, no stylization, no collage look.\n"
            "Match lighting, shadows, perspective and color grading naturally.\n"
            "Avoid artifacts and obvious compositing.\n"
        )
        if hd:
            hard_rules += "Upscale to 4K, high fidelity detail preservation.\n"

        prompt = f"{hard_rules}\nUser instruction: {instruction}"

        # Enviar 2 imágenes + texto (text-and-image-to-image)
        # Docs: contents=[prompt, image] (y múltiples imágenes también). 4
        pil_images = [Image.open(BytesIO(b)) for b in images]

        resp = client.models.generate_content(
            model=model,
            contents=[prompt, *pil_images],
            config=config,
        )

        img_bytes = _extract_first_image_bytes_from_response(resp)
        if not img_bytes:
            raise RuntimeError("No se recibió imagen editada del modelo.")
        return img_bytes

    def generate_video(self, api_key: str, prompt: str, resolution: str = "720p") -> bytes:
        client = genai.Client(api_key=api_key)

        operation = client.models.generate_videos(
            model=self.model_video,
            prompt=prompt,
            config=types.GenerateVideosConfig(resolution=resolution),
        )

        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)

        generated_video = operation.response.generated_videos[0]
        client.files.download(file=generated_video.video)

        tmp_path = "/tmp/veo_out.mp4"
        generated_video.video.save(tmp_path)

        with open(tmp_path, "rb") as f:
            return f.read()
