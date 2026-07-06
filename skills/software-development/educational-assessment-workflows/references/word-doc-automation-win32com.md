# Word (.doc) Automation with win32com

Techniques for programmatically manipulating legacy `.doc` files using Microsoft Word's COM automation (win32com.client). Required when files are in old `.doc` format (not `.docx`) — python-docx cannot open these.

## Prerequisites

- Windows OS (COM is Windows-only)
- Microsoft Word installed
- `pywin32` package: `pip install pywin32`

## Core Pattern: Open, Process, Close (One Document at a Time)

Word COM has stability issues when processing multiple documents in a single session. **Always open and close Word for each document**, with a short sleep between iterations.

```python
import win32com.client
import time

def process_document(fpath):
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(fpath)
        
        # ... processing logic ...
        
        doc.Save()
        doc.Close()
        word.Quit()
    except Exception as e:
        print(f"ERROR: {e}")
        try:
            word.Quit()
        except:
            pass

# Process multiple documents
for fname in files:
    process_document(os.path.join(folder, fname))
    time.sleep(1)  # Critical: give COM time to release
```

## Finding and Modifying Paragraphs

### Insert Content After a Specific Paragraph

```python
for para in doc.Paragraphs:
    txt = para.Range.Text.strip()
    if "做的工作" in txt:
        rng = para.Range
        rng.Collapse(0)  # wdCollapseEnd — collapse to end of paragraph
        rng.Text = "\n" + content_to_insert
```

**⚠️ Critical: Insert AFTER, not before.** `Collapse(0)` collapses to the end of the range. Setting `rng.Text` inserts text after the paragraph. If you search for a marker and insert before it, the content will appear above the marker instead of below it.

### Delete Content Between Two Markers

```python
# Find the two marker paragraphs
question_para = None
work_para = None

for para in doc.Paragraphs:
    txt = para.Range.Text.strip()
    if "2. 对今后教学工作的设想和建议" in txt:
        question_para = para
    if "做的工作" in txt:
        work_para = para

# Create range from end of first marker to start of second
rng_start = question_para.Range.Duplicate
rng_start.Collapse(0)  # End of question paragraph

rng_end = work_para.Range.Duplicate
rng_end.Collapse(1)  # Start of work paragraph

delete_range = doc.Range(rng_start.Start, rng_end.Start)
delete_range.Delete()
```

## Handling Chinese Characters in Python Strings

Chinese quotation marks (`""` / `""`, U+201C / U+201D) are visually similar to ASCII double quotes but are different Unicode characters. They can cause syntax errors when used inside Python strings delimited by ASCII double quotes.

**Safe approach: Store content in a separate JSON file and load it.**

```python
import json

with open('course_content.json', 'r', encoding='utf-8') as f:
    course_content = json.load(f)

work_content = course_content[course_key]['work']
```

In the JSON file, use `\u201c` and `\u201d` for Chinese quotation marks, or just write them directly (JSON handles them fine).

## Common Pitfalls

### ⚠️ COM "RPC server unavailable" Errors
- **Cause**: Word process from a previous call hasn't fully released
- **Fix**: Add `time.sleep(1)` between document processing; ensure `word.Quit()` is in a try/finally block

### ⚠️ Word.Application.Quit AttributeError
- **Cause**: COM object already released when trying to call Quit
- **Fix**: Wrap Quit in try/except — the document is already saved

### ⚠️ Duplicate Content from Multiple Matches
- **Cause**: A search string like "设想和建议" matches both the question heading ("2. 对今后教学工作的设想和建议。") and the section header ("设想和建议：")
- **Fix**: Use more specific search strings, or check which match is the correct one by position

### ⚠️ Content Placement Reversal
- **Cause**: Inserting content BEFORE a marker instead of AFTER it
- **Fix**: Always use `rng.Collapse(0)` (end of range) and set `rng.Text` to insert after the paragraph

## Batch Processing Pattern

Separate content from logic using a JSON file:

```
course_content.json        # Course-specific content (work + suggestions)
process_all.py             # Processing logic (COM automation)
```

This allows editing content without touching the automation code, and makes it easy to add new documents.
