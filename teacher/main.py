# main.py

import threading
import server
import gui

# start server thread
threading.Thread(target=server.start_server, daemon=True).start()

# start GUI (blocking)
gui.start_gui()


                #                cd /d  H:\class9\student 