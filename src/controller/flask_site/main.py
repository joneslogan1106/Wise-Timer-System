from flask import Flask, render_template
import socket

app = Flask(__name__)

@app.route("/")
def hello_world():
    return render_template('base.html')


app.run()