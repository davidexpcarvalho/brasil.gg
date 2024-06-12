import os
import requests
import pandas as pd
import time
import psycopg2
from psycopg2 import sql
import json

def connect_to_db(retries=5, delay=5):
    for attempt in range(retries):
        try:
            connection = psycopg2.connect(
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                dbname=os.getenv("DB_NAME")
            )
            return connection
        except psycopg2.OperationalError as e:
            if attempt < retries - 1:
                print(f"Connection failed. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"Failed to connect to the database after {retries} attempts. Please check the database server and connection settings.")
                raise e

def get_puuid(game_name, tag_line, api_key):
    url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}?api_key={api_key}"
    while True:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['puuid']
        elif response.status_code == 429:
            print("Rate limit exceeded. Waiting for 2 minutes...")
            time.sleep(120)
        else:
            print(f"Erro ao obter PUUID para {game_name}#{tag_line}: {response.status_code}")
            return None

def update_puuid_in_db(connection, player_name, puuid):
    cursor = connection.cursor()
    update_query = """
    UPDATE players SET puuid = %s WHERE player_name = %s;
    """
    cursor.execute(update_query, (puuid, player_name))
    connection.commit()
    cursor.close()

def extract_game_version(version):
    return '.'.join(version.split('.')[:2])

def correct_game_version(version):
    return version.replace(',', '.')

def convert_timestamp(timestamp):
    if timestamp is None:
        return None
    return time.strftime('%H:%M:%S', time.gmtime(timestamp))

def get_match_details(puuid, player_name, api_key, existing_match_ids, champion_translation):
    url = f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?type=ranked&start=0&count=100&api_key={api_key}"
    while True:
        response = requests.get(url)
        if response.status_code == 200:
            break
        elif response.status_code == 429:
            print("Rate limit exceeded. Waiting for 2 minutes...")
            time.sleep(120)
        else:
            print(f"Erro ao obter partidas para {player_name}: {response.status_code}")
            return []

    match_ids = response.json()
    match_details = []

    version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    versions = requests.get(version_url).json()
    latest_version = versions[0]

    item_url = f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/pt_BR/item.json"
    items = requests.get(item_url).json()["data"]

    summoner_url = f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/pt_BR/summoner.json"
    summoners = requests.get(summoner_url).json()["data"]

    item_translation = {int(key): value["name"] for key, value in items.items()}
    summoner_translation = {int(value["key"]): value["name"] for key, value in summoners.items()}

    for match_id in match_ids:
        if match_id in existing_match_ids:
            continue

        url = f"https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={api_key}"
        while True:
            response = requests.get(url)
            if response.status_code == 200:
                break
            elif response.status_code == 429:
                print("Rate limit exceeded. Waiting for 2 minutes...")
                time.sleep(120)
            else:
                print(f"Erro ao obter detalhes da partida {match_id} para {player_name}: {response.status_code}")
                continue

        match_data = response.json()
        info = match_data['info']

        bans = info['teams'][1].get('bans', []) if len(info['teams']) > 1 else []

        for participant in info['participants']:
            if participant['puuid'] == puuid:
                match_detail = {
                    'match_id': match_id,
                    'player_name': player_name,
                    'game_version': correct_game_version(extract_game_version(info.get('gameVersion'))),
                    'game_datetime': pd.to_datetime(info['gameCreation'], unit='ms'),
                    'duration': time.strftime('%H:%M:%S', time.gmtime(info['gameDuration'])),
                    'win': True if participant.get('win') else False,
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
                    'ban1': champion_translation.get(bans[0].get('championId')) if len(bans) > 0 else None,
                    'ban2': champion_translation.get(bans[1].get('championId')) if len(bans) > 1 else None,
                    'ban3': champion_translation.get(bans[2].get('championId')) if len(bans) > 2 else None,
                    'ban4': champion_translation.get(bans[3].get('championId')) if len(bans) > 3 else None,
                    'ban5': champion_translation.get(bans[4].get('championId')) if len(bans) > 4 else None,
                    'dragons': info['teams'][0]['objectives']['dragon']['kills'] if len(info['teams']) > 0 else None,
                    'towers': info['teams'][0]['objectives']['tower']['kills'] if len(info['teams']) > 0 else None,
                    'inhibitors': info['teams'][0]['objectives']['inhibitor']['kills'] if len(info['teams']) > 0 else None,
                    'rift_heralds': info['teams'][0]['objectives']['riftHerald']['kills'] if len(info['teams']) > 0 else None,
                    'vilemaws': info['teams'][0]['objectives'].get('vilemaw', {}).get('kills') if len(info['teams']) > 0 else None,
                    'barons': info['teams'][0]['objectives']['baron']['kills'] if len(info['teams']) > 0 else None,
                    'champExperience': participant['champExperience'],
                    'champLevel': participant['champLevel'],
                    'individualPosition': participant['individualPosition'],
                    'teamPosition': participant['teamPosition'],
                    'role': participant['role'],
                    'lane': participant['lane'],
                    'baronpowerplay': participant['challenges'].get('baronBuffGoldAdvantageOverThreshold'),
                    'bounty': participant['challenges'].get('bountyGold'),
                    'buffsStolen': participant['challenges'].get('buffsStolen'),
                    'stackitemsup': participant['challenges'].get('completeSupportQuestInTime'),
                    'pinks': participant['challenges'].get('controlWardsPlaced'),
                    'damagePerMinute': participant['challenges'].get('damagePerMinute'),
                    'percentualdedanorecebido': participant['challenges'].get('damageTakenOnTeamPercentage'),
                    'passinhos': participant['challenges'].get('dodgeSkillShotsSmallWindow'),
                    'lanediff': participant['challenges'].get('earlyLaningPhaseGoldExpAdvantage'),
                    'curaescudo': participant['challenges'].get('effectiveHealAndShielding'),
                    'cc': participant['challenges'].get('enemyChampionImmobilizations'),
                    'jungleroubada': participant['challenges'].get('enemyJungleMonsterKills'),
                    'objetivosroubados': participant['challenges'].get('epicMonsterSteals'),
                    'objetivosroubadossemsmite': participant['challenges'].get('epicMonsterStolenWithoutSmite'),
                    'firstbrick': participant['challenges'].get('firstTurretKilled'),
                    'tempofirstbrick': convert_timestamp(participant['challenges'].get('firstTurretKilledTime')),
                    'sucessoemganks': participant['challenges'].get('getTakedownsInAllLanesEarlyJungleAsLaner'),
                    'goldPerMinute': participant['challenges'].get('goldPerMinute'),
                    'doublebuff': participant['challenges'].get('initialBuffCount'),
                    'primeiroaronga': participant['challenges'].get('initialCrabCount'),
                    'jungleCsBefore10Minutes': participant.get('jungleCsBefore10Minutes'),
                    'kda': participant.get('kda'),
                    'killParticipation': participant.get('killParticipation'),
                    'dives': participant.get('killsNearEnemyTurret'),
                    'ganksearly': participant.get('killsOnOtherLanesEarlyJungleAsLaner'),
                    'sobrevivenciadive': participant.get('killsUnderOwnTurret'),
                    'SkillShotsEarlyGame': participant.get('landSkillShotsEarlyGame'),
                    'laneMinionsFirst10Minutes': participant.get('laneMinionsFirst10Minutes'),
                    'laningPhaseGoldExpAdvantage': participant.get('laningPhaseGoldExpAdvantage'),
                    'maxCsAdvantageOnLaneOpponent': participant.get('maxCsAdvantageOnLaneOpponent'),
                    'maxKillDeficit': participant.get('maxKillDeficit'),
                    'maxLevelLeadLaneOpponent': participant.get('maxLevelLeadLaneOpponent'),
                    'moreEnemyJungleThanOpponent': participant.get('moreEnemyJungleThanOpponent'),
                    'multikills': participant.get('multikills'),
                    'multikillsAfterAggressiveFlash': participant.get('multikillsAfterAggressiveFlash'),
                    'outnumberedKills': participant.get('outnumberedKills'),
                    'pickKillWithAlly': participant.get('pickKillWithAlly'),
                    'playedChampSelectPosition': participant.get('playedChampSelectPosition'),
                    'quickCleanse': participant.get('quickCleanse'),
                    'quickFirstTurret': participant.get('quickFirstTurret'),
                    'quickSoloKills': participant.get('quickSoloKills'),
                    'saveAllyFromDeath': participant.get('saveAllyFromDeath'),
                    'scuttleCrabKills': participant.get('scuttleCrabKills'),
                    'skillshotsDodged': participant.get('skillshotsDodged'),
                    'skillshotsHit': participant.get('skillshotsHit'),
                    'soloKills': participant.get('soloKills'),
                    'soloTurretsLategame': participant.get('soloTurretsLategame'),
                    'stealthWardsPlaced': participant.get('stealthWardsPlaced'),
                    'takedownOnFirstTurret': participant.get('takedownOnFirstTurret'),
                    'takedowns': participant.get('takedowns'),
                    'takedownsAfterGainingLevelAdvantage': participant.get('takedownsAfterGainingLevelAdvantage'),
                    'takedownsBeforeJungleMinionSpawn': participant.get('takedownsBeforeJungleMinionSpawn'),
                    'takedownsFirstXMinutes': participant.get('takedownsFirstXMinutes'),
                    'teamDamagePercentage': participant.get('teamDamagePercentage'),
                    'turretPlatesTaken': participant.get('turretPlatesTaken'),
                    'turretTakedowns': participant.get('turretTakedowns'),
                    'visionScoreAdvantageLaneOpponent': participant.get('visionScoreAdvantageLaneOpponent'),
                    'visionScorePerMinute': participant.get('visionScorePerMinute'),
                    'wardTakedowns': participant.get('wardTakedowns'),
                    'wardTakedownsBefore20M': participant.get('wardTakedownsBefore20M'),
                    'wardsGuarded': participant.get('wardsGuarded'),
                    'damageDealtToBuildings': participant.get('damageDealtToBuildings'),
                    'damageDealtToObjectives': participant.get('damageDealtToObjectives'),
                    'damageDealtToTurrets': participant.get('damageDealtToTurrets'),
                    'damageSelfMitigated': participant.get('damageSelfMitigated'),
                    'detectorWardsPlaced': participant.get('detectorWardsPlaced'),
                    'doubleKills': participant.get('doubleKills'),
                    'firstBloodAssist': participant.get('firstBloodAssist'),
                    'firstBloodKill': participant.get('firstBloodKill'),
                    'firstTowerAssist': participant.get('firstTowerAssist'),
                    'firstTowerKill': participant.get('firstTowerKill'),
                    'gameEndedInEarlySurrender': participant.get('gameEndedInEarlySurrender'),
                    'gameEndedInSurrender': participant.get('gameEndedInSurrender'),
                    'goldEarned': participant.get('goldEarned'),
                    'goldSpent': participant.get('goldSpent'),
                    'inhibitorKills': participant.get('inhibitorKills'),
                    'killingSprees': participant.get('killingSprees'),
                    'largestCriticalStrike': participant.get('largestCriticalStrike'),
                    'largestKillingSpree': participant.get('largestKillingSpree'),
                    'largestMultiKill': participant.get('largestMultiKill'),
                    'longestTimeSpentLiving': participant.get('longestTimeSpentLiving'),
                    'neutralMinionsKilled': participant.get('neutralMinionsKilled'),
                    'objectivesStolen': participant.get('objectivesStolen'),
                    'objectivesStolenAssists': participant.get('objectivesStolenAssists'),
                    'participantId': participant.get('participantId'),
                    'pentaKills': participant.get('pentaKills'),
                    'quadraKills': participant.get('quadraKills'),
                    'role': participant.get('role'),
                    'sightWardsBoughtInGame': participant.get('sightWardsBoughtInGame'),
                    'teamEarlySurrendered': participant.get('teamEarlySurrendered'),
                    'teamPosition': participant.get('teamPosition'),
                    'timeCCingOthers': participant.get('timeCCingOthers'),
                    'timePlayed': participant.get('timePlayed'),
                    'totalDamageDealtToChampions': participant.get('totalDamageDealtToChampions'),
                    'totalDamageShieldedOnTeammates': participant.get('totalDamageShieldedOnTeammates'),
                    'totalDamageTaken': participant.get('totalDamageTaken'),
                    'totalHeal': participant.get('totalHeal'),
                    'totalHealsOnTeammates': participant.get('totalHealsOnTeammates'),
                    'totalMinionsKilled': participant.get('totalMinionsKilled'),
                    'totalTimeCCDealt': participant.get('totalTimeCCDealt'),
                    'totalTimeSpentDead': participant.get('totalTimeSpentDead'),
                    'tripleKills': participant.get('tripleKills'),
                    'turretKills': participant.get('turretKills'),
                    'turretsLost': participant.get('turretsLost'),
                    'unrealKills': participant.get('unrealKills'),
                    'visionWardsBoughtInGame': participant.get('visionWardsBoughtInGame'),
                    'wardsKilled': participant.get('wardsKilled'),
                    'wardsPlaced': participant.get('wardsPlaced'),
                }

                match_details.append(match_detail)
                break

        time.sleep(1.2)

    return match_details

def get_champion_translation():
    version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    versions = requests.get(version_url).json()
    latest_version = versions[0]

    champion_url = f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/pt_BR/champion.json"
    champions = requests.get(champion_url).json()["data"]

    return {int(value["key"]): value["name"] for key, value in champions.items()}

def add_missing_columns(connection, details):
    if not details:
        print("Nenhum detalhe de partida para processar.")
        return

    cursor = connection.cursor()
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='match_details';")
    existing_columns = {row[0] for row in cursor.fetchall()}

    for key in details[0].keys():
        if key not in existing_columns:
            alter_table_query = sql.SQL("ALTER TABLE match_details ADD COLUMN {} VARCHAR(50);").format(sql.Identifier(key))
            cursor.execute(alter_table_query)
            connection.commit()

    cursor.close()

def save_progress_to_db(connection, match_details):
    if not match_details:
        print("Nenhum detalhe de partida para salvar.")
        return

    cursor = connection.cursor()
    create_table_query = """
    CREATE TABLE IF NOT EXISTS match_details (
        match_id VARCHAR(50) PRIMARY KEY,
        player_name VARCHAR(50),
        game_version VARCHAR(10),
        game_datetime TIMESTAMP,
        duration VARCHAR(8),
        win BOOLEAN,
        champion VARCHAR(50),
        level INTEGER,
        kills INTEGER,
        deaths INTEGER,
        assists INTEGER,
        damage_dealt INTEGER,
        damage_taken INTEGER,
        vision_score INTEGER,
        cs INTEGER,
        gold_earned INTEGER,
        summoner1 VARCHAR(50),
        summoner2 VARCHAR(50),
        item0 VARCHAR(50),
        item1 VARCHAR(50),
        item2 VARCHAR(50),
        item3 VARCHAR(50),
        item4 VARCHAR(50),
        item5 VARCHAR(50),
        item6 VARCHAR(50),
        ban1 VARCHAR(50),
        ban2 VARCHAR(50),
        ban3 VARCHAR(50),
        ban4 VARCHAR(50),
        ban5 VARCHAR(50),
        dragons INTEGER,
        towers INTEGER,
        inhibitors INTEGER,
        rift_heralds INTEGER,
        vilemaws INTEGER,
        barons INTEGER
    );
    """
    cursor.execute(create_table_query)
    connection.commit()

    add_missing_columns(connection, match_details)

    for detail in match_details:
        insert_query = sql.SQL("""
        INSERT INTO match_details ({})
        VALUES ({})
        ON CONFLICT (match_id) DO NOTHING;
        """).format(
            sql.SQL(', ').join(map(sql.Identifier, detail.keys())),
            sql.SQL(', ').join(sql.Placeholder() * len(detail))
        )
        cursor.execute(insert_query, list(detail.values()))
    
    connection.commit()
    cursor.close()

def get_existing_match_ids(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT match_id FROM match_details;")
    existing_ids = cursor.fetchall()
    cursor.close()
    return {id[0] for id in existing_ids}

def get_players_from_db(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT player_name, nick, tag_line, team_name, puuid FROM players;")
    players = cursor.fetchall()
    cursor.close()
    return pd.DataFrame(players, columns=['player_name', 'nick', 'tag_line', 'team_name', 'puuid'])

# Verificar variáveis de ambiente
required_env_vars = ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME", "RIOT_API_KEY"]
for var in required_env_vars:
    if not os.getenv(var):
        raise EnvironmentError(f"A variável de ambiente {var} não está definida")

# Conectar ao banco de dados Supabase
connection = connect_to_db()

# Criar a tabela se não existir
cursor = connection.cursor()
create_table_query = """
CREATE TABLE IF NOT EXISTS match_details (
    match_id VARCHAR(50) PRIMARY KEY,
    player_name VARCHAR(50),
    game_version VARCHAR(10),
    game_datetime TIMESTAMP,
    duration VARCHAR(8),
    win BOOLEAN,
    champion VARCHAR(50),
    level INTEGER,
    kills INTEGER,
    deaths INTEGER,
    assists INTEGER,
    damage_dealt INTEGER,
    damage_taken INTEGER,
    vision_score INTEGER,
    cs INTEGER,
    gold_earned INTEGER,
    summoner1 VARCHAR(50),
    summoner2 VARCHAR(50),
    item0 VARCHAR(50),
    item1 VARCHAR(50),
    item2 VARCHAR(50),
    item3 VARCHAR(50),
    item4 VARCHAR(50),
    item5 VARCHAR(50),
    item6 VARCHAR(50),
    ban1 VARCHAR(50),
    ban2 VARCHAR(50),
    ban3 VARCHAR(50),
    ban4 VARCHAR(50),
    ban5 VARCHAR(50),
    dragons INTEGER,
    towers INTEGER,
    inhibitors INTEGER,
    rift_heralds INTEGER,
    vilemaws INTEGER,
    barons INTEGER,
    is_ranked BOOLEAN
);
"""
cursor.execute(create_table_query)
connection.commit()
cursor.close()

team_match_details = {}

players_df = get_players_from_db(connection)
api_key = os.getenv('RIOT_API_KEY')  # Usando a variável de ambiente para a chave da API

champion_translation = get_champion_translation()

for idx, player in players_df.iterrows():
    player_name = player['player_name']
    game_name = player['nick']
    tag_line = player['tag_line']
    team_name = player['team_name']
    print(f"Processando jogador {player_name} ({game_name}) do time {team_name}")

    if team_name not in team_match_details:
        team_match_details[team_name] = []

    puuid = player['puuid']
    if pd.isna(puuid) or not puuid:
        puuid = get_puuid(game_name, tag_line, api_key)
        if puuid:
            players_df.at[idx, 'puuid'] = puuid
            update_puuid_in_db(connection, player_name, puuid)
    else:
        puuid = player['puuid']

    if not puuid:
        print(f"PUUID não encontrado para o jogador {player_name}, pulando.")
        continue

    existing_match_ids = get_existing_match_ids(connection)
    match_details = get_match_details(puuid, player_name, api_key, existing_match_ids, champion_translation)
    team_match_details[team_name].extend(match_details)

    if len(team_match_details[team_name]) >= 100:
        save_progress_to_db(connection, team_match_details[team_name])
        team_match_details[team_name] = []

for team_name, match_details in team_match_details.items():
    save_progress_to_db(connection, match_details)

print("Coleta de dados concluída e salva no banco de dados")

connection.close()
