import pandas as pd
import aiohttp
import asyncio
from io import BytesIO
from flask import Flask, jsonify
from functools import lru_cache
import requests

app = Flask(__name__)

# Função assíncrona para baixar CSVs do GitHub
async def download_csv_from_github(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            return BytesIO(await response.read())
        else:
            response.raise_for_status()

async def process_csv_urls(csv_urls):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for csv_url, json_filename in csv_urls:
            task = asyncio.create_task(download_csv_from_github(session, csv_url))
            tasks.append((task, json_filename))

        for task, json_filename in tasks:
            try:
                csv_file = await task
                csv_to_json(csv_file, json_filename)
            except Exception as e:
                print(f"Erro ao processar {json_filename}: {e}")

def csv_to_json(csv_file, json_file):
    df = pd.read_csv(csv_file, engine='python')
    df.to_json(json_file, orient='records', indent=4)
    print(f"Arquivo JSON salvo em {json_file}")

# Cache para armazenar resultados de operações frequentes
@lru_cache(maxsize=128)
def fetch_items():
    ITEMS_URL = 'https://ddragon.leagueoflegends.com/cdn/14.11.1/data/pt_BR/item.json'
    response = requests.get(ITEMS_URL)
    if response.status == 200:
        return response.json()
    else:
        response.raise_for_status()

# Rota de exemplo para verificação de funcionamento
@app.route('/items/example', methods=['GET'])
def get_example_items():
    items_data = fetch_items()
    items = items_data['data']
    example_items = {item_id: items[item_id]['name'] for item_id in list(items.keys())[:10]}
    return jsonify(example_items)

if __name__ == "__main__":
    # URLs dos arquivos CSV no GitHub
    csv_urls = [
        ('https://github.com/davidexpcarvalho/brasil.gg/raw/main/player_statistics_rows.csv', 'player_statistics_rows.json'),
        ('https://github.com/davidexpcarvalho/brasil.gg/raw/main/underperforming_positions_rows.csv', 'underperforming_positions_rows.json')
    ]
    
    # Processamento assíncrono dos arquivos CSV
    asyncio.run(process_csv_urls(csv_urls))
    
    # Executar o servidor Flask
    app.run(debug=True)
