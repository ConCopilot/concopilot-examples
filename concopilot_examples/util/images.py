import io
import base64
import numpy as np
from PIL import Image


def pillow_image_to_data_url(image_in_pillow: Image.Image, format: str = 'png'):
    buffered = io.BytesIO()
    image_in_pillow.save(buffered, format=format)
    return f'data:image/{format};base64,{base64.b64encode(buffered.getvalue()).decode()}'


def data_url_to_pillow_image(data_url: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.decodebytes(data_url[data_url.find(',')+1:].encode())))


def ndarray_image_to_data_url(image_in_ndarray: np.ndarray, format: str = 'png'):
    img=Image.fromarray(image_in_ndarray)
    return pillow_image_to_data_url(img, format=format)


def data_url_to_ndarray_image(data_url):
    img=data_url_to_pillow_image(data_url)
    return np.asarray(img)
