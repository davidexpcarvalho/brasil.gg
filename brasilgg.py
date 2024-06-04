import requests
import pandas as pd
import time
import os

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
                    'bans': [champion_translation.get(ban['championId'], ban['championId']) for ban in
                             info['teams'][1].get('bans', [])],
                    'dragons': info['teams'][0]['objectives']['dragon']['kills'],
                    'towers': info['teams'][0]['objectives']['tower']['kills'],
                    'inhibitors': info['teams'][0]['objectives']['inhibitor']['kills'],
                    'rift_heralds': info['teams'][0]['objectives']['riftHerald']['kills'],
                    'vilemaws': info['teams'][0]['objectives'].get('vilemaw', {}).get('kills', 0),
                    'barons': info['teams'][0]['objectives']['baron']['kills'],
                    **scores
                }
                match_details.append(match_detail)
                break
        time.sleep(1.2)  # Respeitar limite de requisições da API
    return match_details

def get_champion_translation():
    version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    versions = requests.get(version_url).json()
    latest_version = versions[0]

    champion_url = f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/pt_BR/champion.json"
    champions = requests.get(champion_url).json()["data"]

    return {int(value["key"]): value["name"] for key, value in champions.items()}

# Função para salvar progresso em arquivos Excel
def save_progress_to_excel(all_match_details, team_name):
    if not all_match_details:
        return
    file_name = f"match_history_{team_name}.xlsx"
    match_details_df = pd.DataFrame(all_match_details)
    if os.path.exists(file_name):
        existing_df = pd.read_excel(file_name)
        match_details_df = pd.concat([existing_df, match_details_df], ignore_index=True)
    match_details_df.to_excel(file_name, index=False)

# Obter IDs das partidas já processadas, se existirem
def get_existing_match_ids(file_name):
    if os.path.exists(file_name):
        existing_data = pd.read_excel(file_name)
        return set(existing_data['match_id'].astype(str).tolist())
    return set()

# Dicionário para armazenar detalhes das partidas por time
team_match_details = {}

players_df = pd.read_excel('players.xlsx')
api_key = os.getenv("RIOT_API_KEY")  # Obtém a chave da API a partir das variáveis de ambiente

if not api_key:
    raise ValueError("A chave da API não foi encontrada nas variáveis de ambiente.")

# Obter tradução dos campeões
champion_translation = get_champion_translation()

# Processar jogadores
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
    else:
        puuid = player['puuid']

    if not puuid:
        print(f"PUUID não encontrado para o jogador {player_name}, pulando.")
        continue

    existing_match_ids = get_existing_match_ids(f"match_history_{team_name}.xlsx")
    match_details = get_match_details(puuid, player_name, api_key, existing_match_ids, champion_translation)
    team_match_details[team_name].extend(match_details)

    # Salvar progresso a cada 100 partidas por time
    if len(team_match_details[team_name]) >= 100:
        save_progress_to_excel(team_match_details[team_name], team_name)
        team_match_details[team_name] = []  # Resetar lista após salvar

# Salvar quaisquer dados restantes após o loop
for team_name, match_details in team_match_details.items():
    save_progress_to_excel(match_details, team_name)

# Salvar planilha de jogadores atualizada
players_df.to_excel('players.xlsx', index=False)

print("Coleta de dados concluída e salva nos arquivos específicos de cada time")
