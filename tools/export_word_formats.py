"""Export局域网聊天室课程设计报告.docx to both .doc and .pdf using MS Word COM."""
import os
from pathlib import Path
import win32com.client

ROOT = Path(__file__).resolve().parent.parent
DOCX_PATH = ROOT / "局域网聊天室课程设计报告.docx"
DOC_PATH = ROOT / "局域网聊天室课程设计报告.doc"
PDF_PATH = ROOT / "局域网聊天室课程设计报告.pdf"

def export_formats():
    print(f"Opening Word to convert {DOCX_PATH.name}...")
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(DOCX_PATH.resolve()))
        print(f"Exporting to {DOC_PATH.name} (Word 97-2003 .doc)...")
        # wdFormatDocument = 0
        doc.SaveAs(str(DOC_PATH.resolve()), FileFormat=0)
        
        print(f"Exporting to {PDF_PATH.name} (PDF)...")
        # wdFormatPDF = 17
        doc.SaveAs(str(PDF_PATH.resolve()), FileFormat=17)
        
        doc.Close()
        print("Export completed successfully!")
    finally:
        word.Quit()

if __name__ == "__main__":
    export_formats()
