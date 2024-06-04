from api.app import app

# Verificação simples para ver se o servidor está funcionando
@app.route("/")
def index():
    return "API está funcionando!"

if __name__ == "__main__":
    app.run(debug=True)
