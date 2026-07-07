from io import BytesIO

from fastapi import UploadFile
from PyPDF2 import PdfReader


async def extract_text_from_pdf(upload_file: UploadFile) -> str:
    content = await upload_file.read()
    if not content:
        return ""

    reader = PdfReader(BytesIO(content))
    pages: list[str] = []

    for page in reader.pages:
        pages.append(page.extract_text() or "")

    return "\n".join(page.strip() for page in pages if page.strip())
