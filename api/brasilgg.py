import requests
import pandas as pd
import time
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Configuração do banco de dados
DATABASE_URL = 'postgresql://postgres.ogwhaifbcpmhvavyeujd:mj4y,#3%EGP%7SZ@aws-0-sa-east-1.pooler.supabase.com:6543/postgres'
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# Definição da tabela matches
class Match(Base):
    __tablename__ = 'matches'
    match_id = Column(String, primary_key=True)
    player_name = Column(String)
    game_version = Column(String)
    game_datetime = Column(DateTime)
    duration = Column(String)
    win = Column(Integer)
    champion = Column(String)
    level = Column(Integer)
    kills = Column(Integer)
    deaths = Column(Integer)
    assists = Column(Integer)
    damage_dealt = Column(Integer)
    damage_taken = Column(Integer)
    vision_score = Column(Integer)
    cs = Column(Integer)
    gold_earned = Column(Integer)
    summoner1 = Column(String)
    summoner2 = Column(String)
    item0 = Column(String)
    item1 = Column(String)
    item2 = Column(String)
    item3 = Column(String)
    item4 = Column(String)
    item5 = Column(String)
    item6 = Column(String)
    bans = Column(Text)
    dragons = Column(Integer)
    towers = Column(Integer)
    inhibitors = Column(Integer)
    rift_heralds = Column(Integer)
    vilemaws = Column(Integer)
    barons = Column(Integer)
    kda = Column(Float)
    utility_score = Column(Float)
    damage_per_death = Column(Float)
    damage_share = Column(Float)
    damage_per_gold = Column(Float)
    gold_advantage_15 = Column(Float)
    cs_advantage_15 = Column(Float)
    cs_per_minute = Column(Float)
    objective_control = Column(Float)
    vision_score_advantage = Column(Float)
    map_domination = Column(Float)
    kill_to_objective_conversion = Column(Float)

# Definição da tabela players
class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    player_name = Column(String, unique=True, nullable=False)
    nick = Column(String, unique=True, nullable=False)
    tag_line = Column(String, nullable=False)
    team_name = Column(String)

# Criar as tabelas no banco de dados
Base.metadata.create_all(engine)

# Função para adicionar um novo jogador
def add_player(player_name, nick, tag_line, team_name):
    new_player = Player(player_name=player_name, nick=nick, tag_line=tag_line, team_name=team_name)
    try:
        session.add(new_player)
        session.commit()
        print("Jogador adicionado com sucesso.")
    except Exception as e:
        session.rollback()
        print(f"Erro ao adicionar jogador: {e}")

# Função para obter a PUUID do jogador
def get_puuid(game_name, tag_line, api_key):
    url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['puuid']
    else:
        print(f"Erro ao obter PUUID para {game_name}#{tag_line}: {response.status_code}")
        return None

# Função para extrair a versão principal do jogo
def extract_game_version(version):
    return '.'.join(version.split('.')[:2])

# Certifique-se de que o ponto seja utilizado como separador decimal
def correct_game_version(version):
    return version.replace(',', '.')

# Função para calcular as pontuações dos jogadores
def calculate_player_scores(participant):
    def normalize_score(value, max_value, scale=100):
        return min((value / max_value) * scale, scale)

    scores = {}
    scores['kda'] = normalize_score((participant['kills'] + participant['assists']) / max(1, participant['deaths']), 10)
    scores['utility_score'] = normalize_score(participant['challenges'].get('effectiveHealAndShielding', 0), 10000)
    scores['damage_per_death'] = normalize_score(
        participant['totalDamageDealtToChampions'] / max(1, participant['deaths']), 1000)
    scores['damage_share'] = normalize_score(participant['challenges']['teamDamagePercentage'], 1)
    scores['damage_per_gold'] = normalize_score(
        participant['totalDamageDealtToChampions'] / max(1, participant['goldEarned']), 10)
    scores['gold_advantage_15'] = normalize_score(participant['challenges'].get('goldAdvantageAt15', 0), 2000)
    scores['cs_advantage_15'] = normalize_score(participant['challenges'].get('csAdvantageOnLaneOpponent', 0), 50)
    scores['cs_per_minute'] = normalize_score(
        participant['totalMinionsKilled'] / max(1, participant['challenges']['gameLength']) * 60, 10)
    scores['objective_control'] = normalize_score(
        participant['challenges'].get('dragonTakedowns', 0) + participant['challenges'].get('baronTakedowns', 0), 10)
    scores['vision_score'] = normalize_score(participant['visionScore'], 100)
    scores['map_domination'] = normalize_score(participant['challenges'].get('visionScoreAdvantageLaneOpponent', 0), 10)
    scores['kill_to_objective_conversion'] = normalize_score((participant['challenges'].get('turretTakedowns', 0) +
                                                              participant['challenges'].get('inhibitorTakedowns',
                                                                                            0)) / max(1, participant[
        'kills']), 1)

    return scores

# Função para obter detalhes das partidas de um jogador
def get_match_details(puuid, player_name, api_key, existing_match_ids, champion_translation):
    url = f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=100&api_key={api_key}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Erro ao obter partidas para {player_name}: {response.status_code}")
        return []
    match_ids = response.json()
    match_details = []

    # Baixar dados do Data Dragon
    version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    versions = requests.get(version_url).json()
    latest_version = versions[0]

    item_url = f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/pt_BR/item.json"
    items = requests.get(item_url).json()["data"]

    summoner_url = f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/pt_BR/summoner.json"
    summoners = requests.get(summoner_url).json()["data"]

    # Mapear IDs para nomes
    item_translation = {int(key): value["name"] for key, value in items.items()}
    summoner_translation = {int(value["key"]): value["name"] for key, value in summoners.items()}

    for match_id in match_ids:
        if match_id in existing_match_ids:
            continue

        url = f"https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={api_key}"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Erro ao obter detalhes da partida {match_id} para {player_name}: {response.status_code}")
            continue

        match_data = response.json()
        info = match_data['info']

        for participant in info['participants']:
            if participant['puuid'] == puuid:
                scores = calculate_player_scores(participant)
                match_detail = {
                    'match_id': match_id,
                    'player_name': player_name,
                    'game_version': correct_game_version(extract_game_version(info.get('gameVersion'))),
                    'game_datetime': pd.to_datetime(info['gameCreation'], unit='ms'),
                    'duration': time.strftime('%H:%M:%S', time.gmtime(info['gameDuration'])),
                    'win': 1 if participant.get('win') else 0,
                    'champion': participant['championName'],
                    'level': participant['champLevel'],
                    'kills': participant['kills'],
                    'deaths': participant['deaths'],
                    'assists': participant['assists'],
                    'damage_dealt': participant['totalDamageDealtToChampions'],
                    'damage_taken': participant['totalDamageTaken'],
                    'vision_score': participant['visionScore'],
                    'cs': participant['totalMinionsKilled'],
                    'gold_earned': participant['goldEarned'],
                    'summoner1': summoner_translation.get(participant['summoner1Id'], participant['summoner1Id']),
                    'summoner2': summoner_translation.get(participant['summoner2Id'], participant['summoner2Id']),
                    'item0': item_translation.get(participant['item0'], participant['item0']),
                    'item1': item_translation.get(participant['item1'], participant['item1']),
                    'item2': item_translation.get(participant['item2'], participant['item2']),
                    'item3': item_translation.get(participant['item3'], participant['item3']),
                    'item4': item_translation.get(participant['item4'], participant['item4']),
                    'item5': item_translation.get(participant['item5'], participant['item5']),
                    'item6': item_translation.get(participant['item6'], participant['item6']),
                    'bans': ','.join([champion_translation[b] for b in info['teams'][participant['teamId'] // 100 - 1]['bans']]),
                    'dragons': participant['dragonKills'],
                    'towers': participant['turretTakedowns'],
                    'inhibitors': participant['inhibitorTakedowns'],
                    'rift_heralds': participant['riftHeraldKills'],
                    'vilemaws': participant['vilemawKills'],
                    'barons': participant['baronKills'],
                    'kda': scores['kda'],
                    'utility_score': scores['utility_score'],
                    'damage_per_death': scores['damage_per_death'],
                    'damage_share': scores['damage_share'],
                    'damage_per_gold': scores['damage_per_gold'],
                    'gold_advantage_15': scores['gold_advantage_15'],
                    'cs_advantage_15': scores['cs_advantage_15'],
                    'cs_per_minute': scores['cs_per_minute'],
                    'objective_control': scores['objective_control'],
                    'vision_score_advantage': scores['vision_score'],
                    'map_domination': scores['map_domination'],
                    'kill_to_objective_conversion': scores['kill_to_objective_conversion'],
                }
                match_details.append(match_detail)
                break
    return match_details

# Função para salvar progresso no banco de dados
def save_progress_to_db(df, engine):
    try:
        df.to_sql('matches', engine, if_exists='append', index=False)
        print("Progresso salvo no banco de dados.")
    except Exception as e:
        print(f"Erro ao salvar progresso no banco de dados: {e}")

# Função para obter IDs de partidas existentes no banco de dados
def get_existing_match_ids(engine):
    try:
        with engine.connect() as connection:
            result = connection.execute('SELECT match_id FROM matches')
            return [row['match_id'] for row in result]
    except Exception as e:
        print(f"Erro ao obter IDs de partidas existentes: {e}")
        return []

# Função principal para coletar dados do jogador e salvar no banco de dados
def collect_player_data_and_save(game_name, tag_line, api_key, engine):
    puuid = get_puuid(game_name, tag_line, api_key)
    if not puuid:
        print(f"Não foi possível obter o PUUID para {game_name}#{tag_line}")
        return

    existing_match_ids = get_existing_match_ids(engine)
    champion_translation = get_champion_translation()

    match_details = get_match_details(puuid, game_name, api_key, existing_match_ids, champion_translation)
    if not match_details:
        print(f"Nenhum novo detalhe de partida encontrado para {game_name}#{tag_line}")
        return

    df = pd.DataFrame(match_details)
    save_progress_to_db(df, engine)

# Exemplo de uso
game_name = "exemplo_de_nome"
tag_line = "1234"
api_key = "sua_chave_api"
engine = create_engine(DATABASE_URL)

# Adicionar um novo jogador
add_player("Novo Jogador", "NovoNick", "1234", "TimeExemplo")

# Coletar e salvar dados do jogador
collect_player_data_and_save(game_name, tag_line, api_key, engine)
