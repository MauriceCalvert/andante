"""OCR a scanned PDF to text file - batch processing for large files."""
from pathlib import Path
from pdf2image import convert_from_path, pdfinfo_from_path
import pytesseract

# Explicit paths
POPPLER_PATH = r"C:\poppler\Library\bin"
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def ocr_pdf_batched(pdf_path: Path, output_path: Path, dpi: int = 500, batch_size: int = 10) -> None:
    """Convert scanned PDF to text via OCR in batches."""
    info = pdfinfo_from_path(pdf_path, poppler_path=POPPLER_PATH)
    total_pages = info["Pages"]
    print(f"Total pages: {total_pages}")

    with open(output_path, "w", encoding="utf-8") as f:
        for start in range(1, total_pages + 1, batch_size):
            end = min(start + batch_size - 1, total_pages)
            print(f"Processing pages {start}-{end}...")

            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=start,
                last_page=end,
                poppler_path=POPPLER_PATH
            )

            for i, image in enumerate(images):
                page_num = start + i
                print(f"  OCR page {page_num}/{total_pages}")
                text = pytesseract.image_to_string(image)
                f.write(f"\n\n=== PAGE {page_num} ===\n\n")
                f.write(text)

            # Free memory
            del images

    print(f"Done. Output: {output_path}")

if __name__ == "__main__":
    pdf = Path(r"D:\projects\Barok\barok\source\andante\docs\Tier4_Reference\gradusadparnassum.pdf")
    out = pdf.with_suffix(".txt")
    ocr_pdf_batched(pdf, out, dpi=200, batch_size=10)