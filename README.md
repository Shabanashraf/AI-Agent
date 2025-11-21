## Universal Credit Act 2025 – Offline Legal Extraction & Analysis

This project processes the **Universal Credit Act 2025** PDF and performs **fully offline, extractive legal analysis**.  
No OpenAI API or any other online LLM is used – everything runs locally with Python.

### Main Files

- **`process_act_offline.py`** – Main script that performs all 4 tasks in offline mode
- **`requirements.txt`** – Python dependencies (offline only)
- **`ukpga_20250022_en.pdf`** – Input Act (Universal Credit Act 2025)
- **`offline_output.txt`** – Run log / final report from the last execution
- **`output/`** – Folder containing all generated results:
  - `extracted_text_raw.txt`
  - `extracted_text.txt`
  - `summary.json`
  - `report_task3.json`
  - `rulechecks_task4.json`

### 1. Install Python Packages (Offline)

- `pdfplumber` – PDF text extraction
- `pytesseract` – OCR fallback (optional, needs Tesseract installed)
- `Pillow` – Image handling for OCR

#### Optional: Install Tesseract OCR
If some pages have no extractable text, the script *can* use OCR. To enable OCR:
- Download Tesseract: https://github.com/UB-Mannheim/tesseract/wiki  
- Install it and add it to your `PATH`

If Tesseract is not installed, the script still runs; it just logs OCR failures and continues.

### 2. Running the Offline Script

From the project folder:

```powershell
cd "path"
python process_act_offline.py > offline_output.txt 2>&1
```

- This runs **all 4 tasks** end‑to‑end.
- All console output is captured in `offline_output.txt`.
- When the command finishes (prompt returns), open `offline_output.txt` to see the full run report.

### 3. Outputs (All Offline & Extractive)

After a successful run, the following files are created in `output/`:

1. **`extracted_text_raw.txt`**  
   - Raw text extracted from the PDF (21 pages).

2. **`extracted_text.txt`**  
   - Cleaned and normalized text:
     - Fixed broken hyphenations
     - Merged line breaks into proper paragraphs
     - Normalized whitespace

3. **`summary.json`**  
   - Extractive summary using keyword‑based sentence scoring (no LLM):
   - Format:
     ```json
     {
       "summary_bullets": ["...", "..."]
     }
     ```
   - Contains 5–10 key sentences selected from the Act.

4. **`report_task3.json`**  
   - Extracted key sections using regex and pattern‑matching over the Act text:
   - Schema:
     ```json
     {
       "definitions": "...",
       "obligations": "...",
       "responsibilities": "...",
       "eligibility": "...",
       "payments": "...",
       "penalties": "...",
       "record_keeping": "..."
     }
     ```
   - All values are **extractive snippets** from the Act (or an explicit note if not found).

5. **`rulechecks_task4.json`**  
   - Offline heuristic checks for 6 rules:
     - Act defines key terms
     - Act specifies eligibility criteria
     - Act specifies responsibilities of the administering authority
     - Act includes enforcement or penalties
     - Act includes payment/entitlement structure
     - Act includes record‑keeping or reporting requirements
   - Format:
     ```json
     [
       {
         "rule": "...",
         "status": "pass|fail",
         "evidence": "...",
         "confidence": 0–100
       }
     ]
     ```
   - Confidence scores are based on keyword hits and context windows in the extracted text.

### 4. Tasks Performed (Offline)

- **Task 1 – Extract Text**
  - Uses `pdfplumber` to extract text from all 21 pages of the Act.
  - If a page has no text, attempts OCR via `pytesseract` (logs failures if Tesseract is missing).
  - Saves raw and cleaned text files.

- **Task 2 – Summarize (Extractive)**
  - No LLM used.
  - Finds keywords using frequency analysis (ignoring stop words).
  - Scores sentences based on keyword hits, legal terms, numbers, and definition‑like patterns.
  - Picks the top‑scoring sentences as the summary.

- **Task 3 – Extract Key Sections (Extractive)**
  - Uses regex/patterns to identify:
    - Definitions (e.g. “X means…”, “In this section… ‘X’ means…”)
    - Obligations and responsibilities (e.g. “Secretary of State must…”, “shall…”)
    - Eligibility conditions (e.g. “entitled to…”, “if… where…”)
    - Payments/entitlements (amounts, elements, tax years)
    - Penalties/enforcement (if present)
    - Record‑keeping/reporting (if present)
  - Populates `report_task3.json` accordingly.

- **Task 4 – Rule Checks (Extractive Heuristics)**
  - For each rule, searches the relevant extracted section / text for indicative terms.
  - Counts matches and extracts short evidence snippets.
  - Sets `status` and `confidence` based on match counts and context.
  - Saves results in `rulechecks_task4.json`.

### 5. Final Run Report

The script prints a final RUN REPORT (also captured in `offline_output.txt`), including:

- Number of pages extracted and OCR attempts
- Raw and cleaned text lengths
- List and sizes of all saved output files
- For Task 3: which fields were filled and their length
- For Task 4: each rule, status, confidence, and which rules had low confidence
