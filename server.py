import os
os.environ["SDL_AUDIODRIVER"] = "dummy"  # Disable audio to suppress ALSA warnings

from flask import Flask, render_template, Response
from flask_socketio import SocketIO
import pygame as pg
import numpy as np
from PIL import Image
import io
import threading
import time
from main import VoxelEngine
import eventlet
import eventlet.wsgi

# Initialize Flask and SocketIO
app = Flask(__name__)
socketio = SocketIO(app)

# Initialize the Voxel Engine in a separate thread
engine = None
frame_lock = threading.Lock()
current_frame = None


def run_engine():
    """Run the Voxel Engine in a loop."""
    global engine, current_frame
    engine = VoxelEngine()

    while engine.is_running:
        engine.handle_events()
        engine.update()

        # Render the frame
        surface = pg.display.get_surface()
        pg_image = pg.surfarray.array3d(surface)

        # Convert to a format Flask can stream
        with frame_lock:
            current_frame = Image.fromarray(np.transpose(pg_image, (1, 0, 2)))

        engine.render()


@app.route('/')
def index():
    """Serve the HTML interface."""
    return render_template('index.html')


def generate_frames():
    """Stream frames to the browser."""
    global current_frame
    while True:
        time.sleep(0.03)  # Adjust frame rate (30 FPS)
        with frame_lock:
            if current_frame is not None:
                buffer = io.BytesIO()
                current_frame.save(buffer, format="JPEG")
                buffer.seek(0)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.read() + b'\r\n')


@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    # Run the Voxel Engine in a separate thread
    threading.Thread(target=run_engine, daemon=True).start()

    # Start the Flask server with Eventlet for production
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 5000)), app)
