from flask import Flask, request, jsonify, Response
import cv2
from ultralytics import YOLO
import base64

app = Flask(__name__)

RTSP_URL = ""

# Load model
model = YOLO("yolov8n.pt")

def detect_function(image):
    results = model(image)
    return results

def draw_boxes(image, results):
    for result in results:
        for box in result.boxes:
            bbox = box.xywh.cpu().numpy()[0]
            confidence = box.conf.cpu().numpy()[0]
            x, y, w, h = bbox
            x1, y1, x2, y2 = int(x - w/2), int(y - h/2), int(x + w/2), int(y + h/2)
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(image, f'{confidence:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    return image

def convert_image_to_buffer(img, format='.jpg'):
    retval, buffer = cv2.imencode(format, img)
    if not retval:
        print("Error: Gagal mengencode gambar")
        return None

    img_str = base64.b64encode(buffer).decode('utf-8')
    return img_str

# def capture_frames(rtsp_url):
#     cap = cv2.VideoCapture(rtsp_url)
#     if not cap.isOpened():
#         return None, "Unable to open RTSP stream"
#     ret, frame = cap.read()
#     cap.release()
#     if not ret:
#         return None, "Failed to capture frame from RTSP stream"
#     return frame, None

def capture_frames(rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        return None, "Unable to open RTSP stream"
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        yield frame
    
    cap.release()


@app.route('/process-rtsp', methods=['POST'])
def process_rtsp():
    rtsp_url = request.json.get('rtsp_url')
    if not rtsp_url:
        return jsonify({'error': 'No RTSP URL provided'}), 400
    
    frames = capture_frames(rtsp_url)
    if not frames:
        return jsonify({'error': 'Failed to capture frames from RTSP stream'}), 500

    def generate():
        for frame in frames:
            detections = detect_function(frame)
            frame_with_bboxes = draw_boxes(frame, detections)

            # Encode image to JPEG format
            _, jpeg = cv2.imencode('.jpg', frame_with_bboxes)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/update-rtsp', methods=['POST'])
def update_rtsp():
    global RTSP_URL
    data = request.json
    if 'url' in data:
        RTSP_URL = data['url']
        return jsonify({"message": "RTSP URL updated successfully", "url": RTSP_URL}), 200
    else:
        return jsonify({"message": "URL not found in the request"}), 400

@app.route('/get-rtsp', methods=['GET'])
def get_rtsp():
    return jsonify({"url": RTSP_URL}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)