import pytesseract
from PIL import Image

# --- 1. SET THE PATH TO YOUR TESSERACT.EXE ---

# The 'r' before the string is important.
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\aniruddh\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

print("--- Testing Pytesseract ---")

try:
    # --- 2. OPEN THE TEST IMAGE ---
    img = Image.open('test.png')
    print("Image loaded successfully.")

    # --- 3. RUN OCR ---
    print("Running OCR...")
    text = pytesseract.image_to_string(img)

    # --- 4. PRINT THE RESULT ---
    print("\n--- ✅ SUCCESS! ---")
    print("Text found in image:")
    print("--------------------")
    print(text)

except pytesseract.TesseractNotFoundError:
    print("\n--- ❌ TESSERACT NOT FOUND ERROR ---")
    print("Python could not find the Tesseract engine.")
    print("Please check the path in 'pytesseract.pytesseract.tesseract_cmd'")
    print("The path you have is:", pytesseract.pytesseract.tesseract_cmd)

except FileNotFoundError:
    print("\n--- ❌ FILE NOT FOUND ERROR ---")
    print("Could not find 'test_image.png'.")
    print("Did you create it and save it in the same folder as this script?")

except Exception as e:
    print(f"\n--- ❌ AN UNEXPECTED ERROR OCCURRED ---")
    print(e)