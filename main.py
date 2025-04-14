import asyncio
import io
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
from pyboy import PyBoy
from pyboy.utils import WindowEvent
from PIL import Image
import threading
import time

app = FastAPI()

# Global variables
pyboy = None
last_screenshot = None
screenshot_lock = threading.Lock()

def init_emulator():
    global pyboy
    pyboy = PyBoy("rom.rb", window="null")
    pyboy.set_emulation_speed(0)  # Disable speed limit

def update_screenshot_buffer():
    """Background thread to update screenshot buffer"""
    global last_screenshot
    while True:
        pyboy.tick()
        screen = pyboy.screen.image
        buf = io.BytesIO()
        screen.save(buf, format="PNG", optimize=True, quality=85)
        buf.seek(0)
        with screenshot_lock:
            last_screenshot = buf.getvalue()
        time.sleep(1/30)  # Cap at 30 FPS

@app.get("/screenshot")
async def get_screenshot():
    """Return the cached screenshot"""
    global last_screenshot
    with screenshot_lock:
        return StreamingResponse(io.BytesIO(last_screenshot), media_type="image/png")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return """
    <html>
        <head>
            <title>Pokémon OSS Eval Interface</title>
            <style>
                .controls { margin: 20px 0; }
                button { padding: 10px 20px; margin: 5px; }
            </style>
        </head>
        <body>
            <h1>Pokémon OSS Eval</h1>
            <img id="screen" src="/screenshot" style="width:400px; border:1px solid #000;">
            <div class="controls">
                <button onclick="sendCommand('UP')">Up</button>
                <button onclick="sendCommand('DOWN')">Down</button>
                <button onclick="sendCommand('LEFT')">Left</button>
                <button onclick="sendCommand('RIGHT')">Right</button>
                <button onclick="sendCommand('A')">A</button>
                <button onclick="sendCommand('B')">B</button>
            </div>
            <script>
                let lastUpdate = 0;
                const minUpdateInterval = 33; // ~30 FPS

                async function sendCommand(command) {
                    await fetch('/command/' + command, { method: 'POST' });
                    updateScreenshot();
                }

                function updateScreenshot() {
                    const now = Date.now();
                    if (now - lastUpdate >= minUpdateInterval) {
                        document.getElementById('screen').src = '/screenshot?ts=' + now;
                        lastUpdate = now;
                    }
                }

                // More efficient periodic update
                setInterval(updateScreenshot, 33);
            </script>
        </body>
    </html>
    """

@app.post("/command/{button}")
async def command(button: str):
    global pyboy
    mapping = {
        "UP": WindowEvent.PRESS_ARROW_UP,
        "DOWN": WindowEvent.PRESS_ARROW_DOWN,
        "LEFT": WindowEvent.PRESS_ARROW_LEFT,
        "RIGHT": WindowEvent.PRESS_ARROW_RIGHT,
        "A": WindowEvent.PRESS_BUTTON_A,
        "B": WindowEvent.PRESS_BUTTON_B,
    }
    if button in mapping:
        pyboy.send_input(mapping[button])
        await asyncio.sleep(0.05)  # Reduced delay
        release_event = mapping[button] + 1  # Get release event
        pyboy.send_input(release_event)
    return {"status": "ok", "button": button}

if __name__ == "__main__":
    init_emulator()
    # Start screenshot update thread
    screenshot_thread = threading.Thread(target=update_screenshot_buffer, daemon=True)
    screenshot_thread.start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
