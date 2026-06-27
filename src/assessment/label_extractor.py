from src.llm.llm_factory import get_llm


class LabelExtractor:

    def __init__(self):
        self.llm = get_llm()

    def extract(self, image_path):

        prompt = f"""
The user uploaded an annotated anatomy image.

List the anatomical labels present in the image.

Return JSON:

{{ "labels": ["label1", "label2"] }}
"""

        response = self.llm.invoke(prompt)

        return response.content
