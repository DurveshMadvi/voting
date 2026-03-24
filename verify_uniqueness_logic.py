import json
import numpy as np

# Mock face_recognition for testing without installing the actual lib in this script
class MockFaceRecognition:
    @staticmethod
    def compare_faces(known_face_encodings, face_encoding_to_check, tolerance=0.4):
        results = []
        for known in known_face_encodings:
            distance = np.linalg.norm(np.array(known) - np.array(face_encoding_to_check))
            results.append(distance <= tolerance)
        return results

import face_utils
# Inject mock
face_utils.face_recognition = MockFaceRecognition

def test_uniqueness_logic():
    print("Running Face Uniqueness Logic Test...")
    
    # Simulate a stored face for user1
    face1 = [0.1] * 128
    face2 = [0.5] * 128 # Different face
    face1_slightly_different = [0.101] * 128 # Same face, different capture
    
    stored_encodings_map = {
        "user1@gmail.com": face1
    }
    
    # 1. Test different face (should not match)
    print("Testing different face...")
    match = face_utils.find_matching_face(face2, stored_encodings_map)
    if match is None:
        print("✅ Success: Different face did not match.")
    else:
        print(f"❌ Failure: Different face matched with {match}")
        
    # 2. Test same face (should match)
    print("Testing same face...")
    match = face_utils.find_matching_face(face1_slightly_different, stored_encodings_map)
    if match == "user1@gmail.com":
        print("✅ Success: Same face matched correctly.")
    else:
        print(f"❌ Failure: Same face did not match. (Match: {match})")

    # 3. Test empty map
    print("Testing empty map...")
    match = face_utils.find_matching_face(face1, {})
    if match is None:
        print("✅ Success: Empty map handled.")
    else:
        print(f"❌ Failure: Empty map returned a match.")

if __name__ == "__main__":
    test_uniqueness_logic()
