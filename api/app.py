# api/app.py
from flask import Flask, render_template, request, redirect, url_for
from brasilgg import Player, session, get_puuid

app = Flask(__name__)

@app.route("/")
def index():
    players = session.query(Player).all()
    return render_template("index.html", players=players)

@app.route("/add_player", methods=["GET", "POST"])
def add_player():
    if request.method == "POST":
        player_name = request.form["player_name"]
        nick = request.form["nick"]
        tag_line = request.form["tag_line"]
        team_name = request.form["team_name"]
        api_key = "RGAPI-5704b123-5507-4266-a9b2-076fecc49df0"  # Substitua pelo valor da sua chave de API

        # Obtém o PUUID do jogador
        puuid = get_puuid(nick, tag_line, api_key)

        if puuid:
            new_player = Player(player_name=player_name, nick=nick, tag_line=tag_line, team_name=team_name, puuid=puuid)
            session.add(new_player)
            session.commit()
            return redirect(url_for("index"))
        else:
            return "Erro ao obter o PUUID. Verifique os detalhes do jogador e tente novamente."

    return render_template("add_player.html")

if __name__ == "__main__":
    app.run(debug=True)
