from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import cv2
import time
import numpy as np
from src.backend.ar_engine import AREngine
from src.backend.stylist_engine import StylistEngine

app = FastAPI(
    title="AI-Powered AR Virtual Try-On API",
    description="Backend API for real-time camera overlay and high-fidelity virtual try-on.",
    version="1.0.0"
)

# Allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def gen_frames():
    """Generator yielding video frames from the webcam processed by MediaPipe."""
    # Open the webcam device (0 is default built-in camera)
    camera = cv2.VideoCapture(0)
    
    # Set lower resolution to ensure high-performance real-time processing on CPU
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    ar_engine = AREngine()
    
    try:
        while True:
            success, frame = camera.read()
            if not success:
                # Fallback: Send a black frame indicating camera is locked or not found
                dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(
                    dummy_frame, 
                    "Camera Error: Locked or Unplugged", 
                    (50, 240), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.8, 
                    (0, 0, 255), 
                    2
                )
                ret, buffer = cv2.imencode('.jpg', dummy_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                time.sleep(1.0)
                continue
            
            # Process the frame to detect pose landmarks and draw skeleton lines
            processed_frame = ar_engine.process_frame(frame)
            
            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            if not ret:
                continue
                
            frame_bytes = buffer.tobytes()
            
            # Yield frame in multipart format for boundary-based rendering
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Control frame rate limit to match standard webcam (approx 30 FPS)
            time.sleep(0.03)
            
    except Exception as e:
        print(f"[ERROR] Exception in video stream: {e}")
    finally:
        camera.release()
        ar_engine.close()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "AI AR Virtual Try-On Backend API is running successfully.",
        "module": 1
    }

@app.get("/api/video_feed")
def video_feed():
    """
    Streaming endpoint returning the processed real-time camera frames.
    """
    return StreamingResponse(
        gen_frames(), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

import base64

# Global AREngine instance to avoid reloading weights on every single frame request
ar_engine = AREngine()
stylist_engine = StylistEngine()

import zipfile
import os
from fastapi.responses import Response

def get_category_by_id(garment_id: str):
    """Deterministically classifies garment assets into genders and categories."""
    try:
        digits = "".join([c for c in garment_id if c.isdigit()])
        val = int(digits) if digits else 0
    except:
        val = 0
        
    categories = [
        {"category": "T-shirts", "gender": "Men's Clothing"},
        {"category": "Shirts", "gender": "Men's Clothing"},
        {"category": "Hoodies", "gender": "Women's Clothing"},
        {"category": "Jackets", "gender": "Men's Clothing"},
        {"category": "Dresses", "gender": "Women's Clothing"},
        {"category": "Shirts", "gender": "Women's Clothing"},
        {"category": "T-shirts", "gender": "Women's Clothing"},
        {"category": "Jackets", "gender": "Women's Clothing"},
        {"category": "Hoodies", "gender": "Men's Clothing"}
    ]
    return categories[val % len(categories)]

@app.get("/api/garments")
def get_garments():
    """
    Dynamically scans viton.zip, parses all top-level garment files inside test/cloth/,
    and returns them categorized to build a dynamic catalog in the React frontend.
    """
    try:
        zip_path = r"c:\Users\Siri\OneDrive\Desktop\AI-AR-Virtual-TryOn-PSCI\Datasets_mini\viton.zip"
        garments_list = []
        if os.path.exists(zip_path):
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Retrieve all files from test/cloth/ ending with .jpg
                cloth_files = [x for x in z.namelist() if x.startswith("test/cloth/") and x.endswith(".jpg")]
                # Sort alphabetically to maintain catalog order
                cloth_files.sort()
                
                # Expose the first 80 garments to avoid page rendering lags
                for f in cloth_files[:80]:
                    filename = os.path.basename(f)
                    garment_id = os.path.splitext(filename)[0]
                    cat_info = get_category_by_id(garment_id)
                    garments_list.append({
                        "id": garment_id,
                        "name": f"{cat_info['category']} {garment_id}",
                        "category": cat_info['category'],
                        "gender": cat_info['gender'],
                        "image_url": f"http://127.0.0.1:8000/api/garments/image/{garment_id}"
                    })
        return garments_list
    except Exception as e:
        print(f"[ERROR] Failed to load catalog garments: {e}")
        return []

@app.get("/api/garments/image/{garment_id}")
def get_garment_image(garment_id: str):
    """
    Fetches the requested garment image from viton.zip in-memory
    and returns it as a direct JPEG HTTP response.
    """
    try:
        garment_img, _ = ar_engine._load_garment(garment_id)
        if garment_img is not None:
            _, buffer = cv2.imencode('.jpg', garment_img)
            return Response(content=buffer.tobytes(), media_type="image/jpeg")
    except Exception as e:
        print(f"[ERROR] Failed to fetch garment image {garment_id}: {e}")
    return Response(status_code=404)


@app.post("/api/tryon/realtime")
def tryon_realtime(
    file: UploadFile = File(...), 
    garment_id: str = Form(None),
    user_height: float = Form(None)
):
    """
    Process incoming webcam frame sent from browser:
    - Decodes frame bytes.
    - Runs MediaPipe landmark detector, warps garment if garment_id is provided.
    - Returns processed frame as a Base64-encoded URI.
    """
    try:
        contents = file.file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return {"status": "error", "message": "Failed to decode image frame"}
            
        processed_frame = ar_engine.process_frame(frame, garment_id, user_height)
        
        _, buffer = cv2.imencode('.jpg', processed_frame)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        
        measurements = getattr(ar_engine, "smooth_measurements", {})
        confidence = getattr(ar_engine, "measurements_confidence", "low")
        guidance = getattr(ar_engine, "measurements_guidance", "")
        
        # Cast measurements to native float to prevent numpy.float32 serialization errors
        serializable_measurements = {}
        for k, v in measurements.items():
            try:
                serializable_measurements[k] = float(v)
            except Exception:
                serializable_measurements[k] = 0.0
                
        # Cast landmarks to native float
        landmarks = getattr(ar_engine, "last_pose_landmarks", [])
        serializable_landmarks = []
        for pt in landmarks:
            try:
                serializable_landmarks.append([float(pt[0]), float(pt[1])])
            except Exception:
                pass
                
        return {
            "status": "success",
            "image": f"data:image/jpeg;base64,{jpg_as_text}",
            "measurements": serializable_measurements,
            "confidence": confidence,
            "guidance": guidance,
            "landmarks": serializable_landmarks
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/tryon/high-fidelity")
def tryon_high_fidelity(file: UploadFile = File(...), garment_id: str = None):
    """
    Placeholder endpoint for offline/static high-fidelity try-on using CP-VTON network.
    Will be implemented in Step 5.
    """
    return {
        "status": "success",
        "message": "High-fidelity static try-on endpoint (placeholder)",
        "output_image_url": "http://localhost:8000/static/output_placeholder.jpg"
    }

@app.post("/api/stylist/face-analysis")
def stylist_face_analysis(file: UploadFile = File(...)):
    """
    Process face capture frame for Face Shape detection and confidence estimation.
    """
    try:
        contents = file.file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return {"status": "error", "message": "Failed to decode image frame"}
            
        res = stylist_engine.analyze_face(frame)
        return res
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/stylist/hairstyles/image/{hairstyle_name}")
def get_hairstyle_image(hairstyle_name: str):
    """
    Serves static hairstyle mockup images from the local backend directory.
    """
    try:
        clean_name = "".join([c for c in hairstyle_name if c.isalnum() or c in ("_", "-")])
        img_path = os.path.join("src", "backend", "hairstyles", f"{clean_name}.jpg")
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                return Response(content=f.read(), media_type="image/jpeg")
    except Exception as e:
        print(f"[ERROR] Failed to fetch hairstyle image {hairstyle_name}: {e}")
    return Response(status_code=404)

@app.get("/api/stylist/accessories/image/{accessory_name}")
def get_accessory_image(accessory_name: str):
    """
    Serves static accessory mockup images from the local backend directory.
    """
    try:
        clean_name = "".join([c for c in accessory_name if c.isalnum() or c in ("_", "-")])
        img_path = os.path.join("src", "backend", "accessories", f"{clean_name}.jpg")
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                return Response(content=f.read(), media_type="image/jpeg")
    except Exception as e:
        print(f"[ERROR] Failed to fetch accessory image {accessory_name}: {e}")
    return Response(status_code=404)

