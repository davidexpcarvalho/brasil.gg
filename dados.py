import pandas as pd
import requests
from io import BytesIO

def download_excel_from_github(url):
    response = requests.get(url)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        response.raise_for_status()

def excel_to_json(excel_file, json_file):
    df = pd.read_excel(excel_file)
    df.to_json(json_file, orient='records', indent=4)
    print(f"Arquivo JSON salvo em {json_file}")

if __name__ == "__main__":
    # URLs dos arquivos Excel no GitHub
    excel_urls = [
        ('https://github.com/davidexpcarvalho/brasil.gg/raw/main/player_statistics_rows.csv', 'player_statistics_rows.json'),
        ('https://github.com/davidexpcarvalho/brasil.gg/raw/main/underperforming_positions_rows.csv', 'underperforming_positions_rows.json')
    ]
    
    for excel_url, json_filename in excel_urls:
        try:
            excel_file = download_excel_from_github(excel_url)
            excel_to_json(excel_file, json_filename)
        except Exception as e:
            print(f"Erro ao processar {excel_url}: {e}")
