from flask import Flask, jsonify, request
from brasilgg import Player, session, get_puuid, save_progress_to_db, get_existing_match_ids, get_champion_translation

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"message": "API está funcionando!"})

@app.route("/players", methods=["GET"])
def get_players():
    players = session.query(Player).all()
    player_data = [{"player_name": player.player_name, "nick": player.nick, "team_name": player.team_name} for player in players]
    return jsonify(player_data)

# Adicione outros endpoints conforme necessário

if __name__ == "__main__":
    app.run(debug=True)
