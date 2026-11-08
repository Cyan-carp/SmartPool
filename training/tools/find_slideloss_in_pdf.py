import sys
from pathlib import Path

def main():
    try:
        from PyPDF2 import PdfReader
    except Exception as e:
        print("ERROR: PyPDF2 is not installed or failed to import:", e)
        print("SUGGESTION: Install with 'pip install PyPDF2' and rerun.")
        sys.exit(1)

    # Default path to local paper in repo
    default_path = Path("Mamba-YOLO-main") / "2208.02019v2.pdf"
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path

    if not pdf_path.exists():
        print(f"ERROR: PDF not found at '{pdf_path}'.")
        sys.exit(1)

    reader = PdfReader(str(pdf_path))

    # Keywords to search for
    patterns = [
        "Slide Loss", "SlideLoss", "Slide", "Ablation", "WiderFace",
        "Table", "Table 2", "validation dataset"
    ]

    print(f"Scanning: {pdf_path}")
    total_pages = len(reader.pages)
    print(f"Total pages: {total_pages}")

    hits = []
    for idx in range(total_pages):
        page = reader.pages[idx]
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if not text:
            continue
        lower = text.lower()
        matched = []
        for pat in patterns:
            if pat.lower() in lower:
                matched.append(pat)
        if matched:
            # collect brief context (first 200 chars)
            snippet = text.strip().replace("\n", " ")
            snippet = (snippet[:300] + "...") if len(snippet) > 300 else snippet
            hits.append({
                "page": idx + 1,  # human-friendly page number
                "matches": matched,
                "snippet": snippet
            })

    if not hits:
        print("No keyword matches found. The PDF may be image-based or use uncommon text encoding.")
        sys.exit(2)

    # Print compact report
    print("\nKeyword matches:")
    for h in hits:
        print(f"- Page {h['page']}: {', '.join(h['matches'])}")
        print(f"  Context: {h['snippet']}")

    # Heuristic: identify likely ablation table pages
    ablation_pages = sorted({h['page'] for h in hits if any(p in h['matches'] for p in ["Ablation", "Table", "Table 2"])})
    slide_pages = sorted({h['page'] for h in hits if any(p in h['matches'] for p in ["Slide Loss", "SlideLoss", "Slide"])})

    print("\nSummary:")
    print(f"- Pages mentioning Slide/SlideLoss: {slide_pages if slide_pages else 'None'}")
    print(f"- Pages mentioning Ablation/Table: {ablation_pages if ablation_pages else 'None'}")
    print("\nTip: Check the intersection/nearby of these pages to locate the exact table (e.g., 'Table 2: Ablation study results on the WiderFace validation dataset').")

if __name__ == "__main__":
    main()