import requests
from bs4 import BeautifulSoup
import pandas as pd
import shutil

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
            name = a_tag.get_text()
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
    image_player = []
    image_player.append([name.text, images['href']])
    response = requests.get(images['href'], stream=True)
    with open('images/fuuu.jpg', 'wb') as file:
        shutil.copyfileobj(response.raw, file)
    #print(image_player)
    return image_player

url = 'https://lol.fandom.com/wiki/CBLOL/2024_Season/Split_2/Player_Statistics'
name_players = get_player_data(url)
db_players = pd.DataFrame(name_players, columns=['names', 'links'])

url2 = 'https://lol.fandom.com/wiki/Fuuu'
images = get_player_image(url2)
db_image = pd.DataFrame(images, columns=['names', 'links'])
