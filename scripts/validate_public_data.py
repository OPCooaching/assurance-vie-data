from __future__ import annotations

import re
import sys
from pathlib import Path

ROOTS = [Path("config"), Path("data")]
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)

# Important: do not scan every 10-digit numeric sequence as a French phone number.
# ISINs and market identifiers frequently contain substrings such as 0974293251,
# which look like French phone numbers but are legitimate financial identifiers.
# A phone-like value is therefore flagged only when it appears next to an explicit
# phone-related label. CSV columns named phone/tel/etc. are also rejected below.
PHONE_CONTEXT = re.compile(
    r"(?i)\b(?:phone|telephone|t[eé]l[eé]phone|tel|t[eé]l|mobile)\b"
    r".{0,40}((?:\+33|0)[1-9](?:[ .-]?\d{2}){4})"
)

FORBIDDEN_EXT = {".pdf", ".doc", ".docx", ".htm", ".html", ".xlsx", ".xls"}
FORBIDDEN_COLUMNS = {
    "surname", "last_name", "email", "phone", "telephone", "téléphone",
    "tel", "mobile", "address", "contract_number", "client_id",
    "beneficiary_clause", "exact_contract_value", "birth_date"
}


def fail(message: str):
    print(f"PRIVACY ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main():
    for root in ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue

            if p.suffix.lower() in FORBIDDEN_EXT:
                fail(f"raw source document is not allowed: {p}")

            if p.suffix.lower() not in {".csv", ".json", ".yml", ".yaml", ".txt", ".md"}:
                continue

            text = p.read_text(encoding="utf-8", errors="ignore")

            if EMAIL.search(text):
                fail(f"email-like value found in {p}")

            if PHONE_CONTEXT.search(text):
                fail(f"phone-like value found in explicit phone context in {p}")

            if p.suffix.lower() == ".csv" and text:
                header = {x.strip().lower() for x in text.splitlines()[0].split(",")}
                bad = header & FORBIDDEN_COLUMNS
                if bad:
                    fail(f"forbidden column(s) {sorted(bad)} in {p}")

    portfolio = Path("config/portfolio_current.csv")
    if portfolio.exists():
        header = portfolio.read_text(encoding="utf-8").splitlines()[0].lower()
        if any(word in header for word in ["amount", "exact_value", "contract_value"]):
            fail("portfolio_current.csv must contain weights only")

    print("Public-data validation OK.")


if __name__ == "__main__":
    main()
