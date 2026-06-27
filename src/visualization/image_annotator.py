from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


class ImageAnnotator:

    def annotate(self, image_path, labels):

        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        width, height = img.size

        y = 20

        for label in labels:

            draw.rectangle(
                [(20, y), (400, y + 40)],
                outline="red",
                width=3
            )

            draw.text((30, y + 8), label, fill="red")

            y += 55

        output_path = Path("outputs") / Path(image_path).name
        output_path.parent.mkdir(exist_ok=True)

        img.save(output_path)

        return str(output_path)
