import os
import json
import pdfplumber
import pytesseract
from PIL import Image
from pathlib import Path
import re
import sys
from collections import Counter
import math

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configuration
PDF_PATH = r"ukpga_20250022_en.pdf"
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================================
# TASK 1: EXTRACT TEXT
# ================================
print("TASK 1: Extracting text from PDF...")

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF, using OCR for pages without text."""
    all_text = []
    pages_with_text = 0
    pages_with_ocr = 0
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages: {total_pages}")
        
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            
            if text and text.strip():
                all_text.append(text)
                pages_with_text += 1
            else:
                # Try OCR
                print(f"Page {i} has no text, attempting OCR...")
                try:
                    img = page.to_image(resolution=300)
                    img_pil = img.original
                    ocr_text = pytesseract.image_to_string(img_pil)
                    if ocr_text.strip():
                        all_text.append(ocr_text)
                        pages_with_ocr += 1
                    else:
                        all_text.append("")  # Empty page
                except Exception as e:
                    print(f"OCR failed for page {i}: {e}")
                    all_text.append("")
    
    return "\n".join(all_text), pages_with_text, pages_with_ocr, total_pages

def clean_text(text):
    """Clean extracted text: fix hyphens, merge lines, normalize whitespace."""
    # Fix hyphenated words split across lines
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    
    # Merge lines that are clearly continuations (not paragraph breaks)
    lines = text.split('\n')
    cleaned_lines = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            cleaned_lines.append('')
        elif i < len(lines) - 1 and lines[i+1].strip() and not line.endswith(('.', '!', '?', ':')):
            cleaned_lines.append(line + ' ')
        else:
            cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

# Extract text
raw_text, pages_with_text, pages_with_ocr, total_pages = extract_text_from_pdf(PDF_PATH)
raw_text_length = len(raw_text)

# Save raw text
with open(f"{OUTPUT_DIR}/extracted_text_raw.txt", "w", encoding="utf-8") as f:
    f.write(raw_text)

# Clean text
cleaned_text = clean_text(raw_text)
cleaned_text_length = len(cleaned_text)

# Save cleaned text
with open(f"{OUTPUT_DIR}/extracted_text.txt", "w", encoding="utf-8") as f:
    f.write(cleaned_text)

print(f"[OK] Task 1 complete: {total_pages} pages, {pages_with_text} with text, {pages_with_ocr} with OCR")
print(f"  Raw text: {raw_text_length} chars, Cleaned: {cleaned_text_length} chars")
sys.stdout.flush()

# ================================
# TASK 2: SUMMARIZE (EXTRACTIVE)
# ================================
print("\nTASK 2: Summarizing Act (extractive method)...")

def extract_keywords(text, top_n=20):
    """Extract most important keywords from text."""
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 
                  'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 
                  'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 
                  'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'}
    
    # Extract words (alphanumeric, at least 3 chars)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Count frequency
    word_freq = Counter(words)
    return [word for word, count in word_freq.most_common(top_n)]

def score_sentence(sentence, keywords):
    """Score a sentence based on keyword presence and position."""
    sentence_lower = sentence.lower()
    score = 0
    
    # Count keyword matches
    for keyword in keywords:
        if keyword in sentence_lower:
            score += 2
    
    # Bonus for sentences with definitions (contains "means", "is", "refers to")
    if re.search(r'\b(means?|is|are|refers? to|defined as)\b', sentence_lower):
        score += 3
    
    # Bonus for sentences with numbers/amounts
    if re.search(r'\d+', sentence):
        score += 1
    
    # Bonus for sentences with legal terms
    legal_terms = ['act', 'section', 'subsection', 'regulation', 'provision', 
                   'entitlement', 'payment', 'penalty', 'obligation', 'responsibility']
    for term in legal_terms:
        if term in sentence_lower:
            score += 1
    
    return score

def extractive_summarize(text, num_sentences=10):
    """Create extractive summary by selecting top-scoring sentences."""
    # Split into sentences
    sentences = re.split(r'[.!?]+\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    # Extract keywords
    keywords = extract_keywords(text, top_n=30)
    
    # Score sentences
    scored_sentences = [(score_sentence(s, keywords), s) for s in sentences]
    scored_sentences.sort(reverse=True, key=lambda x: x[0])
    
    # Select top sentences, maintaining some order
    top_sentences = scored_sentences[:num_sentences]
    top_sentences.sort(key=lambda x: sentences.index(x[1]))
    
    return [s for _, s in top_sentences]

# Create extractive summary
summary_sentences = extractive_summarize(cleaned_text, num_sentences=10)

# Format as bullets
summary_bullets = []
for sent in summary_sentences:
    # Clean up sentence
    sent = re.sub(r'\s+', ' ', sent).strip()
    if len(sent) > 10:
        summary_bullets.append(sent)

# Save summary
summary_data = {"summary_bullets": summary_bullets}
with open(f"{OUTPUT_DIR}/summary.json", "w", encoding="utf-8") as f:
    json.dump(summary_data, f, indent=2, ensure_ascii=False)

print(f"[OK] Task 2 complete: {len(summary_bullets)} summary points extracted")
sys.stdout.flush()

# ================================
# TASK 3: EXTRACT KEY SECTIONS (EXTRACTIVE)
# ================================
print("\nTASK 3: Extracting key sections (extractive method)...")

def find_definitions(text):
    """Extract definitions using pattern matching."""
    definitions = []
    
    # Pattern 1: "X means Y" or "X is Y"
    patterns = [
        r'([A-Z][a-zA-Z\s]+(?:element|allowance|payment|amount|rate|benefit)?)\s+(?:means?|is|are|refers? to|defined as)\s+([^\.]+)',
        r'["\']([^"\']+)["\']\s+(?:means?|is|are|refers? to)\s+([^\.]+)',
        r'(?:the|a|an)\s+([A-Z][a-zA-Z\s]+)\s+(?:means?|is|are)\s+([^\.]+)',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            definition = match.group(0)
            if len(definition) > 20 and len(definition) < 500:
                definitions.append(definition.strip())
    
    # Also look for numbered definitions
    numbered_def = re.findall(r'\((\d+)\)\s+([^\(\)]+(?:means?|is|are|refers? to)[^\.]+)', text)
    for num, def_text in numbered_def:
        if len(def_text) > 20:
            definitions.append(def_text.strip())
    
    return "\n\n".join(definitions[:15])  # Limit to top 15

def find_obligations(text):
    """Extract obligations using pattern matching."""
    obligations = []
    
    # Patterns for obligations
    patterns = [
        r'(?:must|shall|required to|obliged to|duty to)\s+([^\.]+(?:\.|$))',
        r'(?:it is (?:the )?duty|obligation|responsibility)\s+([^\.]+(?:\.|$))',
        r'(?:subject to|in accordance with)\s+([^\.]+(?:\.|$))',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            obligation = match.group(0)
            if len(obligation) > 30 and len(obligation) < 500:
                obligations.append(obligation.strip())
    
    # Look for sections about obligations
    obligation_sections = re.findall(r'(?:obligation|duty|must|shall)[^\.]{20,200}', text, re.IGNORECASE)
    obligations.extend(obligation_sections[:10])
    
    return "\n\n".join(obligations[:15])

def find_responsibilities(text):
    """Extract responsibilities using pattern matching."""
    responsibilities = []
    
    # Patterns for responsibilities
    patterns = [
        r'(?:Secretary of State|authority|department|minister)\s+(?:must|shall|will|is required to|has the (?:power|duty|responsibility))\s+([^\.]+(?:\.|$))',
        r'(?:responsibility|duty|power)\s+(?:of|to|for)\s+([^\.]+(?:\.|$))',
        r'(?:exercise|exercise of)\s+(?:a )?(?:power|function|duty)\s+([^\.]+(?:\.|$))',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            resp = match.group(0)
            if len(resp) > 30 and len(resp) < 500:
                responsibilities.append(resp.strip())
    
    # Look for sections mentioning Secretary of State actions
    sec_state_sections = re.findall(r'Secretary of State[^\.]{20,200}', text, re.IGNORECASE)
    responsibilities.extend(sec_state_sections[:10])
    
    return "\n\n".join(responsibilities[:15])

def find_eligibility(text):
    """Extract eligibility criteria using pattern matching."""
    eligibility = []
    
    # Patterns for eligibility
    patterns = [
        r'(?:eligible|entitled|qualify|qualification)\s+(?:for|to|if)\s+([^\.]+(?:\.|$))',
        r'(?:eligibility|entitlement|qualification)\s+(?:for|to|is|are)\s+([^\.]+(?:\.|$))',
        r'(?:meets?|satisfies?|fulfills?)\s+(?:the )?(?:criteria|conditions|requirements)\s+([^\.]+(?:\.|$))',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            el = match.group(0)
            if len(el) > 30 and len(el) < 500:
                eligibility.append(el.strip())
    
    # Look for conditional statements
    conditionals = re.findall(r'(?:if|where|when|provided that)\s+([^\.]{30,200})', text, re.IGNORECASE)
    eligibility.extend(conditionals[:10])
    
    return "\n\n".join(eligibility[:15])

def find_payments(text):
    """Extract payment/entitlement information."""
    payments = []
    
    # Patterns for payments
    patterns = [
        r'(?:payment|amount|allowance|entitlement|benefit|element)\s+(?:of|is|are|shall be|will be)\s+([^\.]+(?:\.|$))',
        r'£\s*[\d,]+(?:\.\d{2})?\s+([^\.]{10,100})',
        r'(?:standard allowance|LCWRA element|LCW element)[^\.]{20,200}',
        r'(?:tax year|financial year)\s+(\d{4}[-/]\d{2,4})[^\.]{20,200}',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            payment = match.group(0)
            if len(payment) > 20 and len(payment) < 500:
                payments.append(payment.strip())
    
    # Look for sections with amounts
    amount_sections = re.findall(r'[\d,]+(?:\.\d{2})?\s+(?:pounds?|£)[^\.]{10,150}', text, re.IGNORECASE)
    payments.extend(amount_sections[:10])
    
    return "\n\n".join(payments[:15])

def find_penalties(text):
    """Extract penalty/enforcement information."""
    penalties = []
    
    # Patterns for penalties
    patterns = [
        r'(?:penalty|penalties|fine|fines|sanction|sanctions|enforcement)\s+([^\.]+(?:\.|$))',
        r'(?:liable|subject to)\s+(?:a )?(?:penalty|fine|sanction)\s+([^\.]+(?:\.|$))',
        r'(?:offence|offense|violation)\s+([^\.]+(?:\.|$))',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            penalty = match.group(0)
            if len(penalty) > 20 and len(penalty) < 500:
                penalties.append(penalty.strip())
    
    # Look for enforcement sections
    enforcement = re.findall(r'(?:enforce|enforcement|compliance)[^\.]{20,200}', text, re.IGNORECASE)
    penalties.extend(enforcement[:10])
    
    return "\n\n".join(penalties[:15]) if penalties else "No explicit penalties or enforcement mechanisms found in the extracted text."

def find_record_keeping(text):
    """Extract record-keeping/reporting requirements."""
    record_keeping = []
    
    # Patterns for record keeping
    patterns = [
        r'(?:record|records|documentation|report|reporting|maintain|keep)\s+([^\.]+(?:\.|$))',
        r'(?:must|shall|required to)\s+(?:keep|maintain|retain|provide|submit)\s+(?:records?|documents?|information|data)\s+([^\.]+(?:\.|$))',
        r'(?:record-keeping|record keeping|documentation requirements?)[^\.]{20,200}',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            rec = match.group(0)
            if len(rec) > 20 and len(rec) < 500:
                record_keeping.append(rec.strip())
    
    return "\n\n".join(record_keeping[:15]) if record_keeping else "No explicit record-keeping requirements found in the extracted text."

# Extract all sections
print("  Extracting definitions...")
definitions = find_definitions(cleaned_text)

print("  Extracting obligations...")
obligations = find_obligations(cleaned_text)

print("  Extracting responsibilities...")
responsibilities = find_responsibilities(cleaned_text)

print("  Extracting eligibility...")
eligibility = find_eligibility(cleaned_text)

print("  Extracting payments...")
payments = find_payments(cleaned_text)

print("  Extracting penalties...")
penalties = find_penalties(cleaned_text)

print("  Extracting record-keeping...")
record_keeping = find_record_keeping(cleaned_text)

# Combine results
final_extraction = {
    "definitions": definitions,
    "obligations": obligations,
    "responsibilities": responsibilities,
    "eligibility": eligibility,
    "payments": payments,
    "penalties": penalties,
    "record_keeping": record_keeping
}

# Save extraction
with open(f"{OUTPUT_DIR}/report_task3.json", "w", encoding="utf-8") as f:
    json.dump(final_extraction, f, indent=2, ensure_ascii=False)

print("[OK] Task 3 complete")
sys.stdout.flush()

# ================================
# TASK 4: RULE CHECKS (EXTRACTIVE)
# ================================
print("\nTASK 4: Performing rule checks (extractive method)...")

rules = [
    "Act must define key terms",
    "Act must specify eligibility criteria",
    "Act must specify responsibilities of the administering authority",
    "Act must include enforcement or penalties",
    "Act must include payment/entitlement structure",
    "Act must include record-keeping or reporting requirements"
]

rule_checks = []

def check_rule_extractive(rule, text, relevant_section=""):
    """Check a rule using extractive text analysis."""
    search_text = relevant_section if relevant_section else text
    
    # Determine search terms based on rule
    if "define key terms" in rule.lower() or "terms" in rule.lower():
        search_terms = ["means", "is defined", "refers to", "definition", "term"]
        section_text = final_extraction.get("definitions", "")
        # Boost matches if definitional structure detected
        if section_text and re.search(r"\bmeans\b", section_text, re.IGNORECASE):
            section_has_definitions = True
        else:
            section_has_definitions = False
    elif "eligibility" in rule.lower():
        search_terms = ["eligible", "entitlement", "qualify", "qualification", "criteria"]
        section_text = final_extraction.get("eligibility", "")
    elif "responsibilities" in rule.lower():
        search_terms = ["Secretary of State", "authority", "responsibility", "duty", "must", "shall"]
        section_text = final_extraction.get("responsibilities", "")
    elif "enforcement" in rule.lower() or "penalties" in rule.lower():
        search_terms = ["penalty", "enforcement", "fine", "sanction", "offence"]
        section_text = final_extraction.get("penalties", "")
    elif "payment" in rule.lower() or "entitlement" in rule.lower():
        search_terms = ["payment", "amount", "allowance", "entitlement", "benefit", "element"]
        section_text = final_extraction.get("payments", "")
    elif "record" in rule.lower() or "reporting" in rule.lower():
        search_terms = ["record", "documentation", "report", "maintain", "keep"]
        section_text = final_extraction.get("record_keeping", "")
    else:
        search_terms = []
        section_text = ""
    
    # Use section text if available, otherwise search in full text
    text_to_search = section_text if section_text else search_text[:5000]
    
    # Count matches
    matches = 0
    evidence_snippets = []
    
    for term in search_terms:
        pattern = re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE)
        term_matches = pattern.findall(text_to_search)
        matches += len(term_matches)
        
        # Find context around matches
        for match in re.finditer(pattern, text_to_search):
            start = max(0, match.start() - 100)
            end = min(len(text_to_search), match.end() + 100)
            snippet = text_to_search[start:end].strip()
            if snippet and snippet not in evidence_snippets:
                evidence_snippets.append(snippet)
    
    # Boost matches for sections explicitly containing definitions
    if "define key terms" in rule.lower() and 'section_has_definitions' in locals() and section_has_definitions and matches < 3:
        matches = max(matches, 3)

    # Calculate confidence based on matches
    if matches > 10:
        confidence = min(95, 60 + (matches * 2))
        status = "pass"
    elif matches > 5:
        confidence = 70
        status = "pass"
    elif matches > 2:
        confidence = 50
        status = "pass"
    elif matches > 0:
        confidence = 30
        status = "fail"
    else:
        confidence = 10
        status = "fail"
    
    # Get best evidence snippet
    evidence = evidence_snippets[0] if evidence_snippets else "No relevant text found matching this rule."
    if len(evidence) > 200:
        evidence = evidence[:200] + "..."
    
    return {
        "rule": rule,
        "status": status,
        "evidence": evidence,
        "confidence": confidence
    }

for rule in rules:
    print(f"  Checking: {rule}...")
    
    # Determine which section to check
    section_key = None
    if "define key terms" in rule.lower() or "terms" in rule.lower():
        section_key = "definitions"
    elif "eligibility" in rule.lower():
        section_key = "eligibility"
    elif "responsibilities" in rule.lower():
        section_key = "responsibilities"
    elif "enforcement" in rule.lower() or "penalties" in rule.lower():
        section_key = "penalties"
    elif "payment" in rule.lower() or "entitlement" in rule.lower():
        section_key = "payments"
    elif "record" in rule.lower() or "reporting" in rule.lower():
        section_key = "record_keeping"
    
    # Get relevant text
    if section_key and final_extraction.get(section_key):
        text_to_check = final_extraction[section_key]
    else:
        text_to_check = cleaned_text[:5000]
    
    # Check rule
    check_result = check_rule_extractive(rule, cleaned_text, text_to_check)
    rule_checks.append(check_result)
    
    # Save incrementally
    with open(f"{OUTPUT_DIR}/rulechecks_task4.json", "w", encoding="utf-8") as f:
        json.dump(rule_checks, f, indent=2, ensure_ascii=False)

print("[OK] Task 4 complete")
sys.stdout.flush()

# ================================
# FINAL REPORT
# ================================
print("\n" + "="*60)
print("RUN REPORT")
print("="*60)

print(f"\nExtraction Statistics:")
print(f"  - Pages extracted: {total_pages}")
print(f"  - Pages with text: {pages_with_text}")
print(f"  - Pages with OCR: {pages_with_ocr}")
print(f"  - Raw text length: {raw_text_length:,} characters")
print(f"  - Cleaned text length: {cleaned_text_length:,} characters")

print(f"\nFiles Saved:")
files_saved = [
    "output/extracted_text_raw.txt",
    "output/extracted_text.txt",
    "output/summary.json",
    "output/report_task3.json",
    "output/rulechecks_task4.json"
]
for file in files_saved:
    if os.path.exists(file):
        size = os.path.getsize(file)
        print(f"  [OK] {file} ({size:,} bytes)")

print(f"\nTask 3 - Extracted Fields:")
for key, value in final_extraction.items():
    if not value or not value.strip():
        print(f"  [WARNING] {key}: EMPTY")
    else:
        print(f"  [OK] {key}: {len(value)} chars")

print(f"\nTask 4 - Rule Checks:")
low_confidence_rules = []
for check in rule_checks:
    status_icon = "[PASS]" if check["status"] == "pass" else "[FAIL]"
    print(f"  {status_icon} {check['rule']}: {check['status']} (confidence: {check['confidence']})")
    if check["confidence"] < 40:
        low_confidence_rules.append(check["rule"])

if low_confidence_rules:
    print(f"\n[WARNING] Rules with confidence < 40:")
    for rule in low_confidence_rules:
        print(f"  - {rule}")
else:
    print(f"\n[OK] All rules have confidence >= 40")

print("\n" + "="*60)
print("ALL TASKS COMPLETE (OFFLINE MODE)")
print("="*60)
print("\nNote: This analysis used extractive methods only - no LLM/API calls required.")

