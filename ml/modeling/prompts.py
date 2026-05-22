from __future__ import annotations

SYSTEM_PROMPT = (
    "You are an expert SQL assistant. "
    "Given a database schema (CREATE TABLE statements) and a natural language question, "
    "generate a correct SQL query. Output SQL only — no explanation."
)

_TEMPLATE = """\
### System:
{system}

### Schema:
{context}

### Question:
{question}

### SQL:
{answer}"""


def build_prompt(context: str, question: str, answer: str = "") -> str:
    return _TEMPLATE.format(
        system=SYSTEM_PROMPT,
        context=context.strip(),
        question=question.strip(),
        answer=answer.strip(),
    )
