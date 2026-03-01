import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flasgger import Swagger
from scrum_44_escalation_demo_ui.routes import escalation_demo_bp

app = Flask(__name__)

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs",
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Escalation Demo UI API",
        "description": "Multi-channel escalation pipeline for the Flux Life Assistant.",
        "version": "1.0.0",
        "contact": {"name": "Flux Team 8"},
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "tags": [
        {"name": "escalation", "description": "Escalation management and triggering endpoints."},
        {"name": "health", "description": "Service health endpoints."},
    ],
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

app.register_blueprint(escalation_demo_bp)

@app.route("/")
def root():
    return {"service": "Escalation Demo UI API", "version": "1.0.0", "docs": "/docs"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8044, debug=True)
