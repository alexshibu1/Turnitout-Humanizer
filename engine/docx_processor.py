import io
from docx import Document


def read_docx(file_bytes: bytes) -> list[dict]:
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = []
    for idx, para in enumerate(doc.paragraphs):
        paragraphs.append({"text": para.text, "paragraph_index": idx})
    return paragraphs


def write_docx(original_bytes: bytes, transformed_paragraphs: list[str]) -> bytes:
    doc = Document(io.BytesIO(original_bytes))

    for para, new_text in zip(doc.paragraphs, transformed_paragraphs):
        if not para.runs:
            para.text = new_text
            continue

        if para.text == new_text:
            continue

        # Distribute new text across existing runs to preserve formatting.
        # First run gets all the text; remaining runs are emptied.
        # This keeps the first run's font/style applied to the full paragraph.
        runs = para.runs
        runs[0].text = new_text
        for run in runs[1:]:
            run.text = ""

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
