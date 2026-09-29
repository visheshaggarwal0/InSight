import pandas as pd, re
from pathlib import Path

csv_path = Path('d:/Documents/InSight/InSight_ML/data/processed/cosmetics/cosmetics_10k.csv')
df = pd.read_csv(csv_path)
reviews = df['review_text'].astype(str).tolist()

_PATTERN = re.compile(r"\b(?:but|however|except\s+that|except|although|unfortunately|until|cracked|jammed|leaked|burning|stinging|rash|dermatitis|crash|crashes|freeze|freezes|failed|fails|limbo|terrible|horrible)\b.*", re.IGNORECASE)

def extract(text):
    m = _PATTERN.search(text)
    if m:
        return True, m.group(0), m.start(), m.end()
    return False, "", None, None

counts = {'detected': 0, 'none': 0}
examples = []
for rev in reviews[:1000]:
    det, txt, s, e = extract(rev)
    if det:
        counts['detected'] += 1
        if len(examples) < 5:
            examples.append((rev, txt, s, e))
    else:
        counts['none'] += 1

report_lines = []
report_lines.append('# Complaint Extraction Validation')
report_lines.append('')
report_lines.append('**Dataset**: cosmetics_10k.csv (first 1000 reviews)')
report_lines.append('')
report_lines.append(f'- Reviews processed: 1000')
report_lines.append(f'- Detections: {counts["detected"]}')
report_lines.append(f'- No extraction: {counts["none"]}')
report_lines.append('')
report_lines.append('## Representative extracted complaints')
report_lines.append('')
for rev, txt, s, e in examples:
    snippet = rev[:80].replace('\n', ' ')
    report_lines.append(f'* Review snippet: `{snippet}...`')
    report_lines.append(f'* Extracted span: `{txt}` (offset {s}-{e})')
    report_lines.append('')

report_path = Path('d:/Documents/InSight/InSight_ML/reports/complaint_extraction_validation.md')
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text('\n'.join(report_lines))
print('Report written to', report_path)
