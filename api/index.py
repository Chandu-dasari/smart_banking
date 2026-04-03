from flask import Flask, render_template
import sys
import os

# Fix path for templates/static
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

@app.route("/")
def home():
    return render_template("index.html")

# Vercel handler (IMPORTANT)
def handler(environ, start_response):
    return app(environ, start_response)