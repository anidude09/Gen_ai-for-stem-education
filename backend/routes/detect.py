"""
detect.py

This module defines image-processing routes and functions for detecting circles and text 
from uploaded images using OpenCV and EasyOCR. 

Key functionalities:
- Detect circular regions in an image and extract text inside/near them.
- Detect textual regions across the entire image (excluding numeric-only text and quotes).
- Provide a FastAPI endpoint (`POST /`) that accepts an image file and returns 
  detected circles with text plus extracted non-numeric text regions.
"""

from fastapi import APIRouter, File, UploadFile
import cv2
import numpy as np
import easyocr
import re
import torch

print(torch.cuda.is_available())
if torch.cuda.is_available():
    print("cuda is available  on device: ", torch.cuda.get_device_name(0))



# Initialize FastAPI router for detection-related endpoints
router = APIRouter()

# Initialize EasyOCR reader (supports English by default)
reader = easyocr.Reader(['en'], gpu=True)



def detect_circles_with_text_from_image_bytes(image_bytes):
    """
    Detects circular shapes in the given image and extracts text within/around each circle.

    Steps:
    1. Convert image bytes into an OpenCV image.
    2. Convert to grayscale for circle detection.
    3. Use Hough Circle Transform to detect circles.
    4. For each detected circle:
       - Crop the circular region with some padding.
       - Perform OCR (EasyOCR) on the cropped region.
       - Identify possible `page_number` (format: a<digits>.<digits>) and 
         `circle_text` (purely numeric).
       - Collect raw texts recognized in that region.
    5. Return a structured list of circles with metadata.

    Returns:
        List of dictionaries containing:
        - id (int): Circle index
        - x, y (int): Circle center coordinates
        - r (int): Circle radius
        - page_number (str): Extracted page number if detected
        - circle_text (str): Extracted numeric text if detected
        - raw_texts (list): All OCR results from that circle region
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            print("Failed to decode image")
            return []
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect circles using Hough Circle Transform
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=20,
            param1=50,
            param2=100,
            minRadius=50,
            maxRadius=100
        )

        results = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            
            for i, (x, y, r) in enumerate(circles):
                # Crop region around circle with padding
                top = max(y - r - 20, 0)
                bottom = min(y + r + 20, img.shape[0])
                left = max(x - r - 20, 0)
                right = min(x + r + 20, img.shape[1])
                crop = img[top:bottom, left:right]

                try:
                    ocr_result = reader.readtext(crop)
                    texts = [res[1].strip() for res in ocr_result]  
                except Exception as e:
                    print(f"OCR error for circle {i}: {e}")
                    texts = []

                # Extract structured info
                page_number, circle_text = "", ""
                for t in texts:
                    t_clean = t.strip()
                    
                    if re.match(r"^a\d+\.\d+$", t_clean, re.IGNORECASE):
                        page_number = t_clean
                    
                    elif re.match(r"^\d+$", t_clean):
                        circle_text = t_clean

                results.append({
                    "id": i + 1,
                    "x": int(x),
                    "y": int(y),
                    "r": int(r),
                    "page_number": page_number,
                    "circle_text": circle_text,
                    "raw_texts": texts 
                })

        return results
    
    except Exception as e:
        print(f"Circle detection error: {e}")
        return []


def detect_text_from_image_bytes(image_bytes):
    """
    Detects text regions from the entire image, excluding numeric-only text and 
    strings with quotes.

    Steps:
    1. Convert image bytes to an OpenCV image.
    2. Run EasyOCR to detect text with bounding boxes.
    3. Skip text if it:
        - Contains quotes (single/double).
        - Contains any digits.
    4. Collect bounding box coordinates and the cleaned text.

    Returns:
        List of dictionaries containing:
        - id (int): Text index
        - x1, y1, x2, y2 (int): Bounding box coordinates
        - text (str): Extracted text string
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            print("Failed to decode image for text detection")
            return []

        results = reader.readtext(img)
        text_boxes = []

        for i, (bbox, text, confidence) in enumerate(results):
            # Skip text containing quotes or numbers
            if "'" in text or '"' in text:
                continue 

            if any(char.isdigit() for char in text):
                continue
         
            try:
                # Extract bounding box coordinates
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                
                x1, x2 = int(min(x_coords)), int(max(x_coords))
                y1, y2 = int(min(y_coords)), int(max(y_coords))

                text_boxes.append({
                    "id": i + 1,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "text": text.strip()
                })
            except Exception as e:
                print(f"Error processing text box {i}: {e}")
                continue

        return text_boxes
    
    except Exception as e:
        print(f"Text detection error: {e}")
        return []


@router.post("/")
async def detect_circles(file: UploadFile = File(...)):
    """
    FastAPI endpoint to detect circles and text from an uploaded image.

    Steps:
    1. Accepts an image file via POST request.
    2. Reads image bytes.
    3. Runs circle detection (with OCR inside circles).
    4. Runs general text detection across the entire image.
    5. Returns results as a JSON response containing:
        - circles: List of detected circles with text info
        - texts: List of detected text regions outside circles
    """
    try:
        image_bytes = await file.read()    
        circles_with_text = detect_circles_with_text_from_image_bytes(image_bytes)
        texts = detect_text_from_image_bytes(image_bytes)
        
        return {"circles": circles_with_text, "texts": texts}
    
    except Exception as e:
        print(f"Detection endpoint error: {e}")
        return {"error": str(e), "circles": [], "texts": []}
