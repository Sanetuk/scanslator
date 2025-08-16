import pytesseract
import os
pytesseract.pytesseract.tesseract_cmd = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'teserract', 'tesseract.exe'))
print(pytesseract.get_tesseract_version())