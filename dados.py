import pandas as pd
import requests
from io import BytesIO
from flask import Flask, jsonify

app = Flask(__name__)

def download_csv_from_github(url):
    response = requests.get(url)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        response.raise_for_status()

def csv_to_json(csv_file, json_file):
    df = pd.read_csv(csv_file, engine='python')
    df.to_json(json_file, orient='records', indent=4)
    print(f"Arquivo JSON salvo em {json_file}")

def fetch_items():
    ITEMS_URL = f'https://ddragon.leagueoflegends.com/cdn/14.11.1/data/pt_BR/item.json'
    response = requests.get(ITEMS_URL)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def calculate_gold_efficiency(item_data):
    efficiencies = {}
    for item_id, item in item_data.items():
        cost = item['gold']['total']
        stats = item.get('stats', {})
        efficiency = sum(stats.values()) / cost if cost > 0 else 0
        efficiencies[item_id] = {
            'name': item['name'],
            'efficiency': efficiency
        }
    return efficiencies

@app.route('/items/efficiency', methods=['GET'])
def get_item_efficiency():
    items_data = fetch_items()
    efficiencies = calculate_gold_efficiency(items_data['data'])
    return jsonify(efficiencies)

if __name__ == "__main__":
    # URLs dos arquivos CSV no GitHub
    csv_urls = [
        ('https://github.com/davidexpcarvalho/brasil.gg/raw/main/player_statistics_rows.csv', 'player_statistics_rows.json'),
        ('https://github.com/davidexpcarvalho/brasil.gg/raw/main/underperforming_positions_rows.csv', 'underperforming_positions_rows.json')
    ]
    
    for csv_url, json_filename in csv_urls:
        try:
            csv_file = download_csv_from_github(csv_url)
            csv_to_json(csv_file, json_filename)
        except Exception as e:
            print(f"Erro ao processar {csv_url}: {e}")

    # Executar o servidor Flask
    app.run(debug=True)
