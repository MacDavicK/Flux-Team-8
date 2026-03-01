import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flasgger import Swagger
from scrum_42_whatsapp_message_integration.routes import whatsapp_bp

app = Flask(__name__)

swagger_config = {
    "headers": [],
    "specs": [{
        "endpoint": "apispec",
        "route": "/apispec.json",
        "rule_filter": lambda rule: True,
        "model_filter": lambda tag: True,
    }],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs",
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "WhatsApp Message Integration API",
        "description": "Send WhatsApp messages via the Flux Life Assistant.",
        "version": "1.0.0",
        "contact": {"name": "Flux Team 8"},
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "tags": [
        {"name": "whatsapp", "description": "WhatsApp messaging endpoints."},
        {"name": "health", "description": "Health check."},
    ],
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)
app.register_blueprint(whatsapp_bp)

@app.route("/")
def root():
    return {"service": "WhatsApp Message Integration API", "version": "1.0.0", "docs": "/docs"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8042, debug=True)
