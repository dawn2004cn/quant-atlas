"""Entry point — supports three modes:

1. Flask HTTP only (default):      python run.py
2. Standalone WS Gateway:          python -m ws_gateway
3. All-in-one (Flask + SocketIO):  ENABLE_SOCKETIO=1 python run.py
"""

import os

from app.core.runtime_config import _load_dotenv_if_present

# secret.cfg → .env（与 bootstrap 一致；勿用裸 load_dotenv，否则空 MYSQL_PASSWORD= 会挡住 secret.cfg）
_load_dotenv_if_present()

from app import create_app

app = create_app()

if __name__ == "__main__":
    mode = os.getenv("WS_GATEWAY_MODE", "0")
    if mode in ("1", "true"):
        port = int(os.getenv("WS_GATEWAY_PORT", "5001"))
        from ws_gateway import main as ws_main
        ws_main()
    elif os.getenv("ENABLE_SOCKETIO", "").strip() in ("1", "true", "yes") and hasattr(app, "socketio"):
        app.socketio.run(app, host="0.0.0.0", port=5000, debug=app.debug, allow_unsafe_werkzeug=True)
    else:
        app.run(host="0.0.0.0", port=5000, debug=app.debug, threaded=True)
