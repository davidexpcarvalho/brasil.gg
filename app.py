from flask import Flask, jsonify, request
from api.app import app as application

# Verificação simples para ver se o servidor está funcionando
@application.route("/")
def index():
    return jsonify({"message": "API está funcionando!"})

if __name__ == "__main__":
    application.run(debug=True)
