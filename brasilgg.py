import requests
import pandas as pd
import time
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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
    match_id = Column(String)

Base.metadata.create_all(engine)

def get_puuid(game_name, tag_line, api_key):
    url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['puuid']
    else:
        print(f"Erro ao obter PUUID para {game_name}#{tag_line}: {response.status_code}")
        return None

def get_champion_translation():
    version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    versions = requests.get(version_url).json()
    latest_version = versions[0]

    champion_url = f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/pt_BR/champion.json"
    champions = requests.get(champion_url).json()["data"]

    return {int(value["key"]): value["name"] for key, value in champions.items()}

def save_progress_to_db(match_details):
    if not match_details:
        return
    for match_detail in match_details:
        session.add(match_detail)
    session.commit()

def get_existing_match_ids():
    match_ids = session.query(Player.match_id).all()
    return set([match_id for (match_id,) in match_ids])

# Processar jogadores
players = session.query(Player).all()
api_key = "RGAPI-5704b123-5507-4266-a9b2-076fecc49df0"

champion_translation = get_champion_translation()

for player in players:
    player_name = player.player_name
    game_name = player.nick
    tag_line = player.tag_line
    team_name = player.team_name
    print(f"Processando jogador {player_name} ({game_name}) do time {team_name}")

    puuid = player.puuid
    if not puuid:
        puuid = get_puuid(game_name, tag_line, api_key)
        if puuid:
            player.puuid = puuid
            session.commit()
    else:
        puuid = player.puuid

    if not puuid:
        print(f"PUUID não encontrado para o jogador {player_name}, pulando.")
        continue

    existing_match_ids = get_existing_match_ids()
    match_details = get_match_details(puuid, player_name, api_key, existing_match_ids, champion_translation)
    save_progress_to_db(match_details)

print("Coleta de dados concluída e salva no banco de dados")
