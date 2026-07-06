# .docx XML Manipulation (zipfile + regex)

Techniques for programmatically editing `.docx` files by directly manipulating the XML inside the ZIP archive. Use this when python-docx cannot handle the document structure (complex tables, merged cells, custom XML), or when you need precise control over cell-level content.

## Prerequisites

- Python stdlib only: `zipfile`, `re`, `shutil`
- No external dependencies needed — .docx files are ZIP archives

## Core Pattern: Read → Modify → Write Back

```python
import zipfile, re, shutil

# 1. BACKUP first — always
shutil.copy2('file.docx', 'file.docx.bak')

# 2. Read XML from the ZIP
with zipfile.ZipFile('file.docx', 'r') as z:
    content = z.read('word/document.xml').decode('utf-8')

# 3. Modify XML (see sections below)
new_content = content  # ... your modifications ...

# 4. Write back to a new ZIP, then replace
tmp = 'file.docx.tmp'
with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
    with zipfile.ZipFile('file.docx', 'r') as zin:
        for item in zin.namelist():
            data = zin.read(item)
            if item == 'word/document.xml':
                data = new_content.encode('utf-8')
            zout.writestr(item, data)
shutil.move(tmp, 'file.docx')
```

## Understanding the XML Structure

Word documents use the Office Open XML (OOXML) format. Key elements for table editing:

| XML Element | Meaning | Notes |
|---|---|---|
| `<w:tbl>` | Table | Contains rows |
| `<w:tr>` | Table Row | Contains cells |
| `<w:tc>` | Table Cell | Contains paragraphs |
| `<w:p>` | Paragraph | Contains runs |
| `<w:r>` | Run (text span) | Contains text |
| `<w:t>` | Actual text | The visible text content |
| `<w:trPr>` | Row Properties | ⚠️ NOT a row — starts with `<w:tr` but is a child element |
| `<w:tcPr>` | Cell Properties | ⚠️ NOT a cell — starts with `<w:tc` but is a child element |
| `<w:trHeight>` | Row Height | ⚠️ NOT a row — starts with `<w:tr` but is a child element |

### ⚠️ CRITICAL: Regex Pitfalls with Word XML

Word XML contains elements like `<w:trPr>`, `<w:tcPr>`, and `<w:trHeight/>` that **start with `<w:tr` or `<w:tc`** but are NOT actual row/cell tags. A naive regex like `r'</?w:tr[^>]*>'` will match `<w:trPr>` as if it were a `<w:tr>` tag, breaking depth counting.

**Correct regex for matching actual `<w:tr>` tags:**
```python
r'</?w:tr(?:[ >][^>]*)?>'
```
This requires `>` or a space after `w:tr`, excluding `<w:trPr>` and `<w:trHeight>`.

**Correct regex for matching actual `<w:tc>` tags:**
```python
r'</?w:tc(?:[ >][^>]*)?>'
```

## Finding and Replacing Content in Table Cells

### Typical教案 Table Layout

In教案 (lesson plan) documents, sections like "七、教学反思" follow this pattern:

```
Row N:   [七、教学反思] (label cell)
Row N+1: [content cell, full-width with gridSpan="10"]
```

The content row after a section header often has a **single** `<w:tc>` with `gridSpan` spanning the full width — NOT two cells.

### Finding All Section Positions First

**DO NOT use `rfind` in a loop** — after replacing content at one position, `rfind('教学反思')` may find the **same position again** (since the label cell wasn't modified), causing the loop to process the same occurrence twice.

**Correct approach: find ALL positions first, then process in reverse:**

```python
# Find all positions first
positions = []
pos = -1
while True:
    pos = content.find('教学反思', pos + 1)
    if pos == -1:
        break
    positions.append(pos)

# Process in reverse order (last to first) so earlier positions stay valid
for idx in reversed(positions):
    after_ref = content[idx:]
    # Find the content row (next <w:tr> after the header row)
    tr_match = re.search(r'<w:tr(?:[ >][^>]*)?>', after_ref)
    if not tr_match:
        continue
    # ... process row ...
```

### Extracting Visible Text from XML

```python
texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', content)
full_text = ''.join(texts)
```

### Building New Cell Content

When replacing cell content, construct a new `<w:tc>` element with proper formatting:

```python
def build_cell(text):
    """Build a <w:tc> cell with the given text as paragraphs."""
    paragraphs = text.split('\n')
    runs = ''
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        runs += (
            '<w:p>'
            '<w:r>'
            '<w:rPr>'
            '<w:rFonts w:ascii="仿宋" w:hAnsi="仿宋" w:eastAsia="仿宋"/>'
            '<w:sz w:val="24"/>'
            '<w:szCs w:val="24"/>'
            '</w:rPr>'
            '<w:t xml:space="preserve">' + para + '</w:t>'
            '</w:r>'
            '</w:p>'
        )
    return (
        '<w:tc>'
        '<w:tcPr><w:tcW w:w="8505" w:type="dxa"/></w:tcPr>'
        + runs +
        '</w:tc>'
    )
```

## User Preferences (from prior sessions)

### Content Placement
When filling in content under section headers (e.g., "做的工作：", "2，设想和建议："), place the content on the **NEXT LINE after the header**, NOT above it. The content should follow the header, not precede it.

### Class Differentiation
When writing content for multiple classes (e.g., 2401班 and 2405班) studying the same subject, each class must get **DIFFERENT content** tailored to that class's specific characteristics. Never copy identical content across classes — adjust based on:
- Class performance (grade distribution)
- Teaching observations specific to that class
- Different emphasis areas for different cohorts

## Complete Example: Replacing Teaching Reflections

```python
import zipfile, re, shutil, os

def process_docx(doc_name, reflections):
    """Replace teaching reflection content in a .docx file."""
    # Backup
    shutil.copy2(doc_name, doc_name + '.bak')

    # Read
    with zipfile.ZipFile(doc_name, 'r') as z:
        content = z.read('word/document.xml').decode('utf-8')

    new_content = content

    # Find all 教学反思 positions first
    positions = []
    pos = -1
    while True:
        pos = new_content.find('教学反思', pos + 1)
        if pos == -1:
            break
        positions.append(pos)

    # Process in reverse order
    for i in reversed(range(len(positions))):
        idx = positions[i]
        after_ref = new_content[idx:]

        # Find the content row (next <w:tr> after the header row)
        tr_match = re.search(r'<w:tr(?:[ >][^>]*)?>', after_ref)
        if not tr_match:
            continue
        tr_start = tr_match.start()
        content_row = after_ref[tr_start:]

        # Find matching </w:tr>
        depth = 0
        tr_end = 0
        for m in re.finditer(r'</?w:tr(?:[ >][^>]*)?>', content_row):
            tag = m.group()
            if tag.startswith('</w:tr'):
                depth -= 1
                if depth == 0:
                    tr_end = m.end()
                    break
            elif tag.startswith('<w:tr') and not tag.startswith('</w:tr'):
                depth += 1

        if tr_end == 0:
            continue

        full_content_row = content_row[:tr_end]

        # Find <w:tc> cells in this row
        tc_positions = []
        tc_depth = 0
        tc_start = -1
        for m in re.finditer(r'</?w:tc(?:[ >][^>]*)?>', full_content_row):
            tag = m.group()
            if tag.startswith('</w:tc'):
                tc_depth -= 1
                if tc_depth == 0 and tc_start >= 0:
                    tc_positions.append((tc_start, m.end()))
                    tc_start = -1
            elif tag.startswith('<w:tc') and not tag.startswith('</w:tc'):
                if tc_depth == 0:
                    tc_start = m.start()
                tc_depth += 1

        if not tc_positions:
            continue

        # Use the last cell (or only cell) — content rows often have 1 cell
        cell_idx = 1 if len(tc_positions) >= 2 else 0
        cell_start, cell_end = tc_positions[cell_idx]

        # Build new cell
        new_cell = build_cell(reflections[i])
        new_row = full_content_row[:cell_start] + new_cell + full_content_row[cell_end:]
        new_content = new_content[:idx] + new_content[idx:].replace(full_content_row, new_row, 1)

    # Write back
    tmp = doc_name + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        with zipfile.ZipFile(doc_name, 'r') as zin:
            for item in zin.namelist():
                data = zin.read(item)
                if item == 'word/document.xml':
                    data = new_content.encode('utf-8')
                zout.writestr(item, data)
    shutil.move(tmp, doc_name)
```

## Common Pitfalls

### ⚠️ `rfind` After Modification
After replacing content at one position, `rfind('教学反思')` may find the **same position again** (since the label cell wasn't modified). Always find ALL positions first, then process in reverse.

### ⚠️ `<w:trPr>` / `<w:tcPr>` Confusion
These elements start with `<w:tr` or `<w:tc` but are NOT row/cell tags. Use the corrected regex patterns above to avoid depth-counting errors.

### ⚠️ Backup Before Editing
Always create a `.bak` copy before modifying .docx files. XML manipulation errors can corrupt the document, and there's no undo.

### ⚠️ Encoding
Word XML is UTF-8. Always decode with `.decode('utf-8')` and encode with `.encode('utf-8')`.

### ⚠️ Self-Closing Tags
Some XML elements are self-closing (`<w:trHeight .../>`). The corrected regex patterns handle these gracefully.

### ⚠️ Content Row Has One Cell, Not Two
In教案 documents, the content row after a section header often has a **single** `<w:tc>` with `gridSpan` spanning the full width. Don't assume two cells.
