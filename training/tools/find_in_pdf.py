import sys
from pathlib import Path


def parse_keywords(arg: str):
    # Split by comma and strip, ignore empty
    return [k.strip() for k in arg.split(",") if k.strip()]


def main():
    try:
        from PyPDF2 import PdfReader
    except Exception as e:
        print("ERROR: PyPDF2 is not installed or failed to import:", e)
        print("SUGGESTION: Install with 'pip install PyPDF2' and rerun.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("USAGE: python tools/find_in_pdf.py <pdf_path> [comma_separated_keywords]")
        print("EXAMPLE: python tools/find_in_pdf.py Mamba-YOLO-main/2408.12879v1.pdf 'FreqFusion, FFT, frequency' ")
        sys.exit(2)

    pdf_path = Path(sys.argv[1])
    keywords = (
        parse_keywords(sys.argv[2]) if len(sys.argv) > 2 else [
            "FreqFusion", "Freq Fusion", "frequency", "fusion", "FFT", "frequency domain",
        ]
    )

    if not pdf_path.exists():
        print(f"ERROR: PDF not found at '{pdf_path}'.")
        sys.exit(3)

    reader = PdfReader(str(pdf_path))

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
        target_snippet = None
        for pat in keywords:
            if pat.lower() in lower:
                matched.append(pat)
        if matched:
            # collect brief context
            full_text = text.strip().replace("\n", " ")
            snippet = (full_text[:500] + "...") if len(full_text) > 500 else full_text

            # try to center around first FreqFusion occurrence
            for needle in ("freqfusion", "freq fusion"):
                pos = lower.find(needle)
                if pos != -1:
                    start = max(0, pos - 300)
                    end = min(len(full_text), pos + 300)
                    target_snippet = full_text[start:end]
                    break

            hits.append({
                "page": idx + 1,  # human-friendly page number
                "matches": matched,
                "snippet": target_snippet or snippet,
            })

    if not hits:
        print("No keyword matches found. The PDF may be image-based or uses uncommon text encoding.")
        sys.exit(4)

    print("\nKeyword matches:")
    for h in hits:
        print(f"- Page {h['page']}: {', '.join(h['matches'])}")
        print(f"  Context: {h['snippet']}")

    # Simple summary indices
    freq_pages = sorted({h['page'] for h in hits if any(p.lower().startswith('freq') for p in h['matches'])})
    fusion_pages = sorted({h['page'] for h in hits if any('fusion' in p.lower() for p in h['matches'])})
    fft_pages = sorted({h['page'] for h in hits if any('fft' in p.lower() for p in h['matches'])})

    print("\nSummary:")
    print(f"- Pages mentioning 'Freq*': {freq_pages if freq_pages else 'None'}")
    print(f"- Pages mentioning 'fusion': {fusion_pages if fusion_pages else 'None'}")
    print(f"- Pages mentioning 'FFT': {fft_pages if fft_pages else 'None'}")
    print("\nTip: Check these pages and nearby sections (method/ablation/figures) for FreqFusion details.")


if __name__ == "__main__":
    main()