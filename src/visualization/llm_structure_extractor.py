import json
from src.llm.llm_factory import get_llm


class StructureExtractor:

    def __init__(self):
        self.llm = get_llm()

    def extract(self, query):

        prompt = f"""
Extract the anatomical structure names that should be highlighted.

Return ONLY valid JSON in this format:

{{
  "structures": ["structure1", "structure2"]
}}

Query: {query}
"""

        response = self.llm.invoke(prompt)

        try:
            data = json.loads(response.content)
            return data["structures"]
        except Exception:
            return []
