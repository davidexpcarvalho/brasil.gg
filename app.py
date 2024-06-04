from flask import Flask, request, jsonify, render_template, redirect, url_for
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

# Configuração do banco de dados
DATABASE_URL = 'sqlite:///players.db'
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    player_name = Column(String)
    nick = Column(String)
    tag_line = Column(String)
    team_name = Column(String)
    puuid = Column(String)

Base.metadata.create_all(engine)

@app.route('/add_player', methods=['GET', 'POST'])
def add_player():
    if request.method == 'POST':
        player_name = request.form['player_name']
        nick = request.form['nick']
        tag_line = request.form['tag_line']
        team_name = request.form['team_name']
        new_player = Player(
            player_name=player_name,
            nick=nick,
            tag_line=tag_line,
            team_name=team_name
        )
        session.add(new_player)
        session.commit()
        return redirect(url_for('add_player'))
    return render_template('add_player.html')

@app.route('/players', methods=['GET'])
def get_players():
    players = session.query(Player).all()
    result = [{'player_name': player.player_name, 'nick': player.nick, 'tag_line': player.tag_line, 'team_name': player.team_name, 'puuid': player.puuid} for player in players]
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
