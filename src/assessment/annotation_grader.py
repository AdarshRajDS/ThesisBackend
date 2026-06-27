from src.llm.llm_factory import get_llm


class AnnotationGrader:

    def __init__(self):
        self.llm = get_llm()

    def grade(self, user_labels, reference_text):

        prompt = f"""
Compare the student labels with the reference anatomy.

Student labels:
{user_labels}

Reference:
{reference_text}

Return:

Correct:
Missing:
Incorrect:
"""

        response = self.llm.invoke(prompt)

        return response.content
