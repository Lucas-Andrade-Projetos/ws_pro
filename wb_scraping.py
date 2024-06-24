import requests
from bs4 import BeautifulSoup
import pandas as pd
import shutil
import os

if not os.path.exists('images'):
    os.makedirs('images')

def get_player_data(url):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve content. Status code: {response.status_code}")
        return []

    content = response.content
    site = BeautifulSoup(content, 'html.parser')
    players = site.select('td.spstats-player')

    name_players = []
    for player in players:
        a_tag = player.find('a', class_=['catlink-players pWAG pWAN to_hasTooltip', 'catlink-players pWAN to_hasTooltip'])
        if a_tag:
            name = a_tag.get_text().strip()
            if name:
                name_players.append([name, f'https://lol.fandom.com{a_tag["href"]}'])
    
    return name_players

def get_player_image(url):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve content. Status code: {response.status_code}")
        return []

    content = response.content
    site = BeautifulSoup(content, 'html.parser')
    images = site.find('a', attrs={'class': 'image'})
    name = site.find('th', attrs={'class': 'infobox-title'})
    if not images or not name:
        print("No image or name found.")
        return []

    image_player = [[name.text, images['href']]]
    response = requests.get(images['href'], stream=True)
    if response.status_code == 200:
        with open(f'images/{name.text}.jpg', 'wb') as file:
            shutil.copyfileobj(response.raw, file)
    else:
        print(f"Failed to download image. Status code: {response.status_code}")
    
    return image_player

def get_player_stats(url, name):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve content. Status code: {response.status_code}")
        return [], {}

    content = response.content
    site = BeautifulSoup(content, 'html.parser')
    player_ages = site.findAll('div', class_=['tabheader-content'])
    
    ages_era = []
    for ages in player_ages:
        age = ages.find('a', attrs={'class': 'to_hasTooltip'})
        if age:
            ages_era.append(age.text.strip())
    ages_era.append('2024')
    
    if 'Career' not in ages_era:
        print("No 'Career' section found.")
        return [], {}

    ind = ages_era.index('Career')
    ages_era = ages_era[ind:]
    table = []
    table_g = []
    for year in ages_era:
        if year == 'Career':
            year_url = f'https://lol.fandom.com/wiki/Fuuu/Statistics'
        else:
            year_url = f'https://lol.fandom.com/wiki/Fuuu/Statistics/{year}'
        response = requests.get(year_url)
        if response.status_code != 200:
            print(f"Failed to retrieve content for {year}. Status code: {response.status_code}")
            continue
        
        content = response.content
        site = BeautifulSoup(content, 'html.parser')
        player_datas = site.findAll('div', class_='wide-content-scroll')
        
        for data in player_datas:
            split = data.findAll('a', class_='to_hasTooltip')
            test = data.findAll('td', class_='spstats-subject')
            game = data.findAll('td', class_='')
            if year == 'Career':
                for tests in test:
                    table.append({'year': year,'split': 'All Career', 'champs': tests.text.strip()})
            else:
                for splits in split:
                    if splits.text.strip() != name:
                        for tests in test:
                            table.append({'year': year,'split': splits.text.strip(), 'champs': tests.text.strip()})
                
            for games in game:
                table_g.append(games.text.strip())
    
    dic = {}
    for i in range(0, len(table_g), 17):
        chave = f'Linha {i // 17 + 1}'
        dic[chave] = table_g[i:i + 17]
    
    novo_dic = {}
    for linha, valores in dic.items():
        for coluna, valor in enumerate(valores):
            if coluna not in novo_dic:
                novo_dic[coluna] = []
            novo_dic[coluna].append(valor)
    
    return table, novo_dic


url = 'https://lol.fandom.com/wiki/CBLOL/2024_Season/Split_2/Player_Statistics'
name_players = get_player_data(url)
db_players = pd.DataFrame(name_players, columns=['names', 'links'])

url2 = 'https://lol.fandom.com/wiki/Fuuu'
images = get_player_image(url2)
db_image = pd.DataFrame(images, columns=['names', 'links'])

url3 = 'https://lol.fandom.com/wiki/Fuuu/Statistics/2024'
eras, nums = get_player_stats(url3, 'Fuuu')
db_era = pd.DataFrame(eras, columns=['year', 'split', 'champs'])
db_nums = pd.DataFrame(nums)
db_statistics = pd.merge(db_era, db_nums, left_index=True, right_index=True)
db_statistics = db_statistics.rename(columns={0: 'games', 1: 'wins', 2: 'loses', 3: 'winRate', 4: 'kills', 5: 'deaths', 6: 'assists', 7: 'KDA', 8: 'CS', 9: 'CS/M', 10: 'gold', 11: 'gold per minute', 12: 'damage', 13: 'damage per minute', 14: 'kill participation', 15: 'kill share', 16: 'gold share'})

print(db_players.head())
print(db_image.head())
print(db_statistics.head())
