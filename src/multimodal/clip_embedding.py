from sentence_transformers import SentenceTransformer
from PIL import Image


class CLIPEmbedding:

    def __init__(self):
        self.model = SentenceTransformer("clip-ViT-B-32")

    def embed_text(self, texts):
        return self.model.encode(texts, convert_to_numpy=True)

    def embed_image(self, image_paths):

        images = [Image.open(p).convert("RGB") for p in image_paths]

        return self.model.encode(images, convert_to_numpy=True)
