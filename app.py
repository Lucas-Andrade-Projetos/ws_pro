import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
import shutil
import tempfile
from io import BytesIO

st.set_page_config(layout="wide")

@st.cache_data
def site_status(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.status_code
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao acessar o site: {e}")
        return None

@st.cache_data
def get_player_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
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
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao recuperar dados dos jogadores: {e}")
        return []

@st.cache_data
def get_player_image(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.content
        site = BeautifulSoup(content, 'html.parser')
        images = site.find('a', attrs={'class': 'image'})
        name = site.find('th', attrs={'class': 'infobox-title'})
        if images and name:
            return [[name.text, images['href']]]
        else:
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao recuperar imagem do jogador: {e}")
        return []

@st.cache_data
def get_player_stats(url, name):
    print(name)
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
    
    if 'Career' in ages_era:
        ind = ages_era.index('Career')
        ages_era[ind] = 'All Career'
    else:
        print("No 'Career' section found.")
        return [], {}

    ind = ages_era.index('All Career')
    ages_era = ages_era[ind:]
    table = []
    table_g = []
    url = url.split('/2024')
    for year in ages_era:
        if year == 'All Career':
            year_url = f'{url[0]}'
        else:
            year_url = f'{url[0]}/{year}'
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
            if year == 'All Career':
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

options_names = ['Escreva um nome'] + db_players['names'].tolist()

col1, col2, col3 = st.columns([.2, .4, .6], gap='large')

with col1:
    selected_name = st.selectbox('Selecione um nome para buscar:', options=options_names)

if selected_name == 'Escreva um nome':
    with col2:
        st.write('Carregando...')
else:
    search_results = db_players[db_players['names'] == selected_name]
    if not search_results.empty:
        with col2:
            st.write('Resultados da busca:')
            status = site_status(search_results.iloc[0]['links'])
            if status == 200:
                images = get_player_image(search_results.iloc[0]['links'])
                if images:
                    db_image = pd.DataFrame(images, columns=['names', 'links'])
                    if not db_image.empty:
                        image_link = db_image.iloc[0]['links']
                        image_name = db_image.iloc[0]['names']
                        try:
                            response = requests.get(image_link, stream=True)
                            response.raise_for_status()
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                shutil.copyfileobj(response.raw, tmp_file)
                                st.image(tmp_file.name, width=200, caption=image_name)
                        except requests.exceptions.RequestException as e:
                            st.error(f"Erro ao baixar a imagem: {e}")
                    else:
                        st.write('Imagem não encontrada')
                else:
                    st.write('Imagem não encontrada')
            else:
                st.write('Erro ao acessar o site do jogador')
        with col3:
            name_url = search_results.iloc[0]['links'].split("wiki/")
            url3 = 'https://lol.fandom.com/wiki/'+ name_url[1] +'/Statistics/2024'
            #st.write(url3)
            eras, nums = get_player_stats(url3, name_url[1].replace('_', ' '))
            db_era = pd.DataFrame(eras, columns=['year', 'split', 'champs'])
            db_nums = pd.DataFrame(nums)
            db_statistics = pd.merge(db_era, db_nums, left_index=True, right_index=True)
            print(db_statistics.head())
            db_statistics = db_statistics.rename(columns={0: 'games', 1: 'wins', 2: 'loses', 
                                                          3: 'winRate', 4: 'kills', 5: 'deaths', 
                                                          6: 'assists', 7: 'KDA', 8: 'CS', 9: 'CS/M', 
                                                          10: 'gold', 11: 'gold per minute', 
                                                          12: 'damage', 13: 'damage per minute', 
                                                          14: 'kill participation', 15: 'kill share', 
                                                          16: 'gold share'})
            
            options_years = ['escolha um ano'] + db_statistics['year'].unique().tolist()

            options_splits = ['escolha um SPLIT'] + db_statistics['split'].unique().tolist()
            
            with col1:
                selected_years = st.selectbox('Selecione um ano para buscar:', options=options_years)
                    
                if selected_years != 'escolha um ano':
                    if selected_years != 'All Career':
                        filtered_splits =db_statistics[db_statistics['year'] == selected_years]['split'].unique().tolist()
                        options_splits = ['escolha um camp'] + filtered_splits
                        selected_splits = st.selectbox('Selecione um split para buscar:', options=options_splits)
                    if selected_years == 'All Career':
                        filtered_stats = db_statistics[(db_statistics['year'] == selected_years)]    
                        with col3:
                            st.dataframe(filtered_stats)
                    else: 
                        if selected_splits != 'escolha um camp':
                            filtered_stats = db_statistics[(db_statistics['year'] == selected_years) & (db_statistics['split'] == selected_splits)]    
                            with col3:
                                st.dataframe(filtered_stats)

            
