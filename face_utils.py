import face_recognition
import numpy as np
import base64
import cv2
import json

def get_face_encoding(base64_image):
    """
    Convert a base64 image string to a 128-d face encoding.
    """
    try:
        # Decode base64 string
        encoded_data = base64_image.split(',')[1] if ',' in base64_image else base64_image
        image_bytes = base64.b64decode(encoded_data)
        print(f"Decoded image size: {len(image_bytes)} bytes")
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            print("Failed to decode image with cv2.imdecode")
            return None
            
        print(f"Image shape: {img.shape}")
        
        # Convert BGR to RGB
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Detect face encodings
        print("Running face_recognition.face_encodings...")
        encodings = face_recognition.face_encodings(rgb_img)
        print(f"Number of faces detected: {len(encodings)}")
        
        if len(encodings) > 0:
            return encodings[0].tolist() 
        else:
            # Save image for debugging
            debug_path = r"c:\Users\DURVESH\OneDrive\Desktop\vote - Copy\debug_face.jpg"
            cv2.imwrite(debug_path, img)
            print(f"Face not detected. Image saved to {debug_path} for inspection.")
            
        return None
    except Exception as e:
        print(f"Error in get_face_encoding: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_faces(stored_encoding_list, current_encoding_list, tolerance=0.4):
    """
    Compare current face encoding with stored encoding.
    Lower tolerance = stricter.
    """
    if not stored_encoding_list or not current_encoding_list:
        return False
    
    stored_encoding = np.array(stored_encoding_list)
    current_encoding = np.array(current_encoding_list)
    
    # Calculate distance for debugging
    distance = np.linalg.norm(stored_encoding - current_encoding)
    print(f"Face distance: {distance:.4f} (Tolerance: {tolerance})")
    
    results = face_recognition.compare_faces([stored_encoding], current_encoding, tolerance=tolerance)
    print(f"Comparison Result: {results[0]}")
    return results[0]
def find_matching_face(new_encoding_list, stored_encodings_map, tolerance=0.4):
    """
    Search for a match between a new face encoding and a collection of stored encodings.
    stored_encodings_map: {email: [encoding_list]}
    Returns: email of the first match found, or None.
    """
    if not new_encoding_list or not stored_encodings_map:
        return None
    
    current_encoding = np.array(new_encoding_list)
    
    # Extract emails and their corresponding encodings
    emails = list(stored_encodings_map.keys())
    encodings = [np.array(enc) for enc in stored_encodings_map.values()]
    
    if not encodings:
        return None
        
    # Batch comparison
    results = face_recognition.compare_faces(encodings, current_encoding, tolerance=tolerance)
    
    # Find the first match
    for i, is_match in enumerate(results):
        if is_match:
            return emails[i]
            
    return None
