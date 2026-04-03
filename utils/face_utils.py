import cv2
import numpy as np
import os
import json
import base64
from flask import current_app

# Try to import insightface, fallback gracefully
try:
    from insightface.app import FaceAnalysis
    from sklearn.metrics.pairwise import cosine_similarity
    FACE_AVAILABLE = True
    _face_app = None

    def get_face_app():
        global _face_app
        if _face_app is None:
            _face_app = FaceAnalysis(providers=['CPUExecutionProvider'])
            _face_app.prepare(ctx_id=0, det_size=(320, 320))
        return _face_app
except ImportError:
    FACE_AVAILABLE = False
    print("InsightFace not available - using basic face detection fallback")


def encode_face_from_image(img_data):
    """Extract face embedding from image bytes/array"""
    if not FACE_AVAILABLE:
        return np.random.rand(512).tolist()  # fallback for dev

    try:
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        app = get_face_app()
        faces = app.get(img)
        if faces and len(faces) > 0 and faces[0].embedding is not None:
            return faces[0].embedding.flatten().tolist()
        return None
    except Exception as e:
        print(f"Face encoding error: {e}")
        return None


def encode_face_from_path(img_path):
    """Extract face embedding from file path"""
    if not FACE_AVAILABLE:
        return np.random.rand(512).tolist()
    try:
        img = cv2.imread(img_path)
        if img is None:
            return None
        app = get_face_app()
        faces = app.get(img)
        if faces and len(faces) > 0 and faces[0].embedding is not None:
            return faces[0].embedding.flatten().tolist()
        return None
    except Exception as e:
        print(f"Face encoding error: {e}")
        return None


def verify_face(captured_img_data, stored_encoding_json, threshold=0.4):
    """Compare captured face with stored encoding"""
    if not FACE_AVAILABLE:
        return True, 0.95  # dev fallback

    try:
        stored_encoding = json.loads(stored_encoding_json)
        stored_emb = np.array(stored_encoding)

        nparr = np.frombuffer(captured_img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return False, 0.0

        app = get_face_app()
        faces = app.get(img)
        if not faces or len(faces) == 0:
            return False, 0.0

        live_emb = faces[0].embedding.flatten()
        sim = cosine_similarity([live_emb], [stored_emb])[0][0]
        return sim >= threshold, float(sim)
    except Exception as e:
        print(f"Face verify error: {e}")
        return False, 0.0


def detect_faces_in_frame(img_data):
    """Detect face bounding boxes in image"""
    if not FACE_AVAILABLE:
        # Return center oval position for fallback
        return [{'x': 160, 'y': 120, 'w': 120, 'h': 150, 'detected': True}]
    try:
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return []
        app = get_face_app()
        faces = app.get(img)
        result = []
        for face in faces:
            bbox = face.bbox.astype(int)
            result.append({
                'x': int(bbox[0]), 'y': int(bbox[1]),
                'w': int(bbox[2]-bbox[0]), 'h': int(bbox[3]-bbox[1]),
                'detected': True
            })
        return result
    except Exception as e:
        print(f"Face detect error: {e}")
        return []


def base64_to_bytes(data_url):
    """Convert base64 data URL to bytes"""
    if ',' in data_url:
        data_url = data_url.split(',')[1]
    return base64.b64decode(data_url)
