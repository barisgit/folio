from __future__ import annotations

from pathlib import Path

from folio.dsl.model import Document
from folio.render.tokens import MM_TO_PT

_DEFAULT_PDF_NAME = "folio.pdf"


def write_pdf(
    document: Document,
    out_dir: Path,
    *,
    filename: str = _DEFAULT_PDF_NAME,
) -> Path:
    """Write a minimal valid PDF with one page per Folio page.

    The first PDF backend preserves document/page shape and physical page sizes. It
    intentionally leaves page drawing content empty until a richer SVG-to-PDF path
    is selected.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / _safe_pdf_name(filename)
    target.write_bytes(_pdf_bytes(document))
    return target


def _safe_pdf_name(filename: str) -> str:
    name = Path(filename).name or _DEFAULT_PDF_NAME
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return name


def _pdf_bytes(document: Document) -> bytes:
    pages = sorted(document.pages, key=lambda page: page.page_number)
    object_count = 2 + (len(pages) * 2)
    objects: list[bytes] = []

    catalog_id = 1
    pages_id = 2
    first_page_id = 3
    page_ids = [first_page_id + (index * 2) for index in range(len(pages))]
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii"))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii"))

    for index, page in enumerate(pages):
        page_id = first_page_id + (index * 2)
        content_id = page_id + 1
        width_pt = round(page.width_mm * MM_TO_PT, 2)
        height_pt = round(page.height_mm * MM_TO_PT, 2)
        objects.append(
            (
                f"<< /Type /Page /Parent {pages_id} 0 R "
                f"/MediaBox [0 0 {width_pt:g} {height_pt:g}] "
                f"/Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        objects.append(b"<< /Length 0 >>\nstream\n\nendstream")

    if len(objects) != object_count:
        raise AssertionError("PDF object count mismatch")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id, content in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode("ascii"))
        output.extend(content)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)
