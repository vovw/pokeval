import asyncio
import io
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
from pyboy import PyBoy
from pyboy.utils import WindowEvent
from PIL import Image

app = FastAPI()

# Global variable for the emulator instance
pyboy = None

def init_emulator():
    global pyboy
    # Replace 'path_to_rom.gb' with the actual path to your Game Boy ROM
    # Use window="null" to run in headless mode (i.e., no graphical output window)
    pyboy = PyBoy("Pokemon Red.gb", window="null")
    # Additional configuration can be done here if necessary

@app.get("/screenshot")
async def get_screenshot():
    """
    Capture a screenshot from the emulator and return it as a PNG image.
    """
    global pyboy
    pyboy.tick()  # progress the emulator one frame
    screen = pyboy.screen.image  # get the screen image from the emulator's screen
    buf = io.BytesIO()
    screen.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Render a simple HTML page with the current emulator screen and control buttons.
    """
    return """
    <html>
        <head>
            <title>Pokémon OSS Eval Interface</title>
        </head>
        <body>
            <h1>Pokémon OSS Eval</h1>
            <img id="screen" src="/screenshot" style="width:400px; border:1px solid #000;">
            <br><br>
            <button onclick="sendCommand('UP')">Up</button>
            <button onclick="sendCommand('DOWN')">Down</button>
            <button onclick="sendCommand('LEFT')">Left</button>
            <button onclick="sendCommand('RIGHT')">Right</button>
            <button onclick="sendCommand('A')">A</button>
            <button onclick="sendCommand('B')">B</button>
            <script>
                async function sendCommand(command) {
                    await fetch('/command/' + command, { method: 'POST' });
                    // Refresh screenshot after command execution
                    document.getElementById('screen').src = '/screenshot?ts=' + Date.now();
                }
                // Optionally refresh the screenshot periodically
                setInterval(() => {
                    document.getElementById('screen').src = '/screenshot?ts=' + Date.now();
                }, 1000);
            </script>
        </body>
    </html>
    """

@app.post("/command/{button}")
async def command(button: str):
    """
    Accept a command and translate it into a game input.
    """
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
        event = mapping[button]
        pyboy.send_input(event)
        await asyncio.sleep(0.1)  # Brief delay to register the input
        # Optionally send a release event if needed:
        # pyboy.send_input(window release event here) 
    return {"status": "ok", "button": button}

if __name__ == "__main__":
    init_emulator()
    uvicorn.run(app, host="0.0.0.0", port=8000)

