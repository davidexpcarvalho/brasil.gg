from flask import Flask, jsonify, request
from brasilgg import Player, session, get_puuid, save_progress_to_db, get_existing_match_ids, get_champion_translation

app = Flask(__name__)

@app.route('/api/add_player', methods=['POST'])
def add_player():
    data = request.json
    player_name = data.get('player_name')
    nick = data.get('nick')
    tag_line = data.get('tag_line')
    team_name = data.get('team_name')
    match_id = data.get('match_id')

    if not all([player_name, nick, tag_line, team_name]):
        return jsonify({"error": "Missing player data"}), 400

    player = Player(player_name=player_name, nick=nick, tag_line=tag_line, team_name=team_name, match_id=match_id)
    session.add(player)
    session.commit()
    return jsonify({"message": "Player added successfully!"}), 201

@app.route('/api/process_players', methods=['POST'])
def process_players():
    api_key = request.json.get('api_key')
    if not api_key:
        return jsonify({"error": "API key is required"}), 400

    champion_translation = get_champion_translation()
    players = session.query(Player).all()

    for player in players:
        player_name = player.player_name
        game_name = player.nick
        tag_line = player.tag_line
        team_name = player.team_name
        print(f"Processing player {player_name} ({game_name}) from team {team_name}")

        puuid = player.puuid
        if not puuid:
            puuid = get_puuid(game_name, tag_line, api_key)
            if puuid:
                player.puuid = puuid
                session.commit()
        else:
            puuid = player.puuid

        if not puuid:
            print(f"PUUID not found for player {player_name}, skipping.")
            continue

        existing_match_ids = get_existing_match_ids()
        match_details = get_match_details(puuid, player_name, api_key, existing_match_ids, champion_translation)
        save_progress_to_db(match_details)

    return jsonify({"message": "Players processed successfully!"}), 200

if __name__ == '__main__':
    app.run(debug=True)
