import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
import shutil

def site_status(url):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve content. Status code: {response.status_code}")
        return []
    #else:
        #st.write('its works!')

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
    #print(image_player)
    return image_player

url = 'https://lol.fandom.com/wiki/CBLOL/2024_Season/Split_2/Player_Statistics'
name_players = get_player_data(url)
db_players = pd.DataFrame(name_players, columns=['names', 'links'])

st.set_page_config(layout="wide")
# Adiciona uma opção para não selecionar nenhum nome
options = ['Escreva um nome'] + db_players['names'].tolist()

# Layout em colunas
col1, col2 = st.columns([.2, .8], gap='large')

# Coluna para o seletor de nomes
with col1:
    #st.write("")
    # Campo de seleção para pesquisa
    selected_name = st.selectbox('Selecione um nome para buscar:', options=options)

# Filtrando o DataFrame com base na seleção
if selected_name == 'Escreva um nome':
    st.write('')
    with col2:
        st.write('Carregando...')
else:
    search_results = db_players[db_players['names'] == selected_name]
    # Verifica se há resultados antes de tentar acessar a coluna 'links'
    if not search_results.empty:
        with col2:
            # Mostrando resultados da pesquisa
            st.write('Resultados da busca:')
            site_status(search_results.iloc[0]['links'])  # Acessa a coluna correta 'links'
            images = get_player_image(search_results.iloc[0]['links'])
            db_image = pd.DataFrame(images, columns=['names', 'links'])
            if not db_image.empty:
                image_link = db_image.iloc[0]['links']
                image_name = db_image.iloc[0]['names']
                response = requests.get(image_link, stream=True)
                with open('images/imagem.jpg', 'wb') as file:
                    shutil.copyfileobj(response.raw, file)
                st.image("images/imagem.jpg", width=200
                         , caption=image_name)  # Exibe a imagem com st.image
            else:
                st.write('Imagem não encontrada')