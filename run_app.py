import subprocess
import webbrowser
import threading
from app import create_app

app = create_app()


def run_flask():
    app.run(port=5000)


threading.Thread(target=run_flask).start()

webbrowser.open("http://127.0.0.1:5000")
