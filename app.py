import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st 
import shutil
import numpy as np
import tempfile
import matplotlib.pyplot as plt
import plotly.express as px
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

def replace_dash_with_mean(column):
    column_numeric = pd.to_numeric(column, errors='coerce')
    
    mean_value = column_numeric[column_numeric.notna()].mean()
    
    column = column.copy()
    
    column[column == "-"] = str(mean_value)
    
    return column


url = 'https://lol.fandom.com/wiki/CBLOL/2024_Season/Split_2/Player_Statistics'
name_players = get_player_data(url)
db_players = pd.DataFrame(name_players, columns=['names', 'links'])

options_names = ['Escreva um nome'] + db_players['names'].tolist()
tabs = ["Aba 1", "Aba 2"]
selected_tab = st.radio("", tabs, index=0, key="tabs_radio", horizontal=True)
col1, col2, col3, col4, col5 = st.columns([.2, .3, .4, .3, .1], gap='large')
col6, col7, col8, col9 = st.columns([.3, .2, .3, .2], gap='large')
col10, col11, col12, col13, col14 = st.columns([.05, .05, .16, .03, .05], gap='small')

# Conteúdo da Aba 1
if selected_tab == "Aba 1":
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
                db_statistics = db_statistics.rename(columns={0: 'games', 1: 'wins', 2: 'loses', 
                                                            3: 'winRate', 4: 'kills', 5: 'deaths', 
                                                            6: 'assists', 7: 'KDA', 8: 'CS', 9: 'CS/M', 
                                                            10: 'gold', 11: 'gold per minute', 
                                                            12: 'damage', 13: 'damage per minute', 
                                                            14: 'kill participation', 15: 'kill share', 
                                                            16: 'gold share'})
                for col in db_statistics.columns:
                    db_statistics[col] = replace_dash_with_mean(db_statistics[col])

                db_statistics['games'] = db_statistics['games'].astype(int)
                db_statistics['wins'] = db_statistics['wins'].astype(int)
                db_statistics['kills'] = db_statistics['kills'].astype(float)
                db_statistics['deaths'] = db_statistics['deaths'].astype(float)
                db_statistics['assists'] = db_statistics['assists'].astype(float)
                db_statistics['KDA'] = db_statistics['KDA'].astype(float)
                db_statistics['CS'] = db_statistics['CS'].astype(float)
                db_statistics['gold'] = db_statistics['gold'].str.replace('k', '')
                db_statistics['gold'] = db_statistics['gold'].astype(float)
                db_statistics['damage'] = db_statistics['damage'].str.replace('k', '')
                
                db_statistics['damage'] = db_statistics['damage'].astype(float)
                db_statistics['gold per minute'] = db_statistics['gold per minute'].astype(float)
                db_statistics['CS/M'] = db_statistics['CS/M'].astype(float)
                db_statistics['damage per minute'] = db_statistics['damage per minute'].astype(float)
                db_statistics['kill participation'] = db_statistics['kill participation'].str.replace('%', '')
                db_statistics['kill participation'] = db_statistics['kill participation'].astype(float)
                db_statistics['kill share'] = db_statistics['kill share'].str.replace('%', '')
                db_statistics['kill share'] = db_statistics['kill share'].astype(float)
                db_statistics['gold share'] = db_statistics['gold share'].str.replace('%', '')
                db_statistics['gold share'] = db_statistics['gold share'].astype(float)

                
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
                            max_lines = filtered_stats.nlargest(3, 'games')
                            with col3:
                                #st.dataframe(filtered_stats)
                                
                                sum_games = int(filtered_stats['games'].sum())
                                sum_games_win = int(filtered_stats['wins'].sum())
                                data = {
                                            'category': ['Winrate', 'Loserate'],
                                            'value':  [sum_games_win, (sum_games - sum_games_win)]
                                }
                                df = pd.DataFrame(data)
                                
                                fig = px.pie(df, values='value', names='category', 
                                            hole=0.5, color_discrete_sequence=['#FF6464', '#91C483'])

                                fig.update_layout(
                                    title="Winrate in " + selected_years,
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    width=320,  
                                    height=320  
                                )
                                st.plotly_chart(fig)
                            with col4:
                                st.write('Campeões mais jogados:')
                                st.write(max_lines['champs'].iloc[0])
                                valor_sem_percentagem = max_lines['winRate'].iloc[0].replace("%", "")
                                valor_float = float(valor_sem_percentagem)
                                progress_bar = st.progress(valor_float/100)                           
                                st.write(max_lines['champs'].iloc[1])
                                valor_sem_percentagem = max_lines['winRate'].iloc[1].replace("%", "")
                                valor_float = float(valor_sem_percentagem)
                                progress_bar = st.progress(valor_float/100)  
                                st.write(max_lines['champs'].iloc[2])
                                valor_sem_percentagem = max_lines['winRate'].iloc[2].replace("%", "")
                                valor_float = float(valor_sem_percentagem)
                                progress_bar = st.progress(valor_float/100)



                            with col5:
                                st.write('')
                                st.write('')
                                st.write('')
                                st.write('')
                                st.write('')
                                textwins = f"{max_lines['wins'].iloc[0]}V - {max_lines['loses'].iloc[0]}D"
                                st.write(textwins)
                                st.write('')
                                st.write('')
                                textwins = f"{max_lines['wins'].iloc[1]}V - {max_lines['loses'].iloc[1]}D"
                                st.write(textwins)
                                st.write('')
                                st.write('')
                                textwins = f"{max_lines['wins'].iloc[2]}V - {max_lines['loses'].iloc[2]}D"
                                st.write(textwins)
                            with col6:
                                mean_k = filtered_stats['kills'].mean()
                                mean_d = filtered_stats['deaths'].mean()
                                mean_a = filtered_stats['assists'].mean()
                                data = {
                                            'category': ['kills', 'deaths', 'assists'],
                                            'value':  [mean_k, mean_d, mean_a]
                                }
                                df = pd.DataFrame(data)
                                
                                fig = px.pie(df, values='value', names='category', 
                                            hole=0.5, color_discrete_sequence=['#FF6464', '#91C483', '#8BD3F8'])

                                fig.update_layout(
                                    title="Mean KDA",
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    width=320,  
                                    height=320  
                                )
                                st.plotly_chart(fig)
                            with col7:
                                mean_kda = filtered_stats['KDA'].mean()
                                mean_cs = filtered_stats['CS'].mean()
                                mean_gold = filtered_stats['gold'].mean()
                                mean_damage = filtered_stats['damage'].mean()
                                st.write('Important Status in Game:')
                                st.write('')
                                st.write('Avarage KDA: {:.1f}'.format(mean_kda))
                                st.write('')
                                st.write('Avarage CS: {:.1f}'.format(mean_cs))
                                st.write('')
                                st.write('Avarage Gold: {:.1f}K'.format(mean_gold))
                                st.write('')
                                st.write('Avarage Damage: {:.1f}K'.format(mean_damage))
                            with col8:
                                mean_gm = filtered_stats['gold per minute'].mean()
                                mean_dm = filtered_stats['damage per minute'].mean()
                                data = {
                                            'category': ['Gold per minute', 'Damage per minute'],
                                            'value':  [mean_gm, mean_dm]
                                }
                                df = pd.DataFrame(data)
                                
                                fig = px.pie(df, values='value', names='category', 
                                            hole=0.5, color_discrete_sequence=['#FF6464', '#91C483'])
                                
                                fig.update_traces(textinfo='label+value', texttemplate='%{label}: %{value:.2f}')

                                fig.update_layout(
                                    title="Gold and Damage per minute",
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    width=320,  
                                    height=320  
                                )
                                st.plotly_chart(fig)
                            with col9:
                                mean_csm = filtered_stats['CS/M'].mean()
                                mean_kp = filtered_stats['kill participation'].mean()
                                mean_ks = filtered_stats['kill share'].mean()
                                mean_gs = filtered_stats['gold share'].mean()
                                st.write('Participation in Game:')
                                st.write('')
                                st.write('Avarage CS pm: {:.1f}'.format(mean_csm))
                                st.write('')
                                st.write('Avarage KP: {:.1f}%'.format(mean_kp))
                                st.write('')
                                st.write('Avarage KS: {:.1f}%'.format(mean_ks))
                                st.write('')
                                st.write('Avarage GS: {:.1f}%'.format(mean_gs))
                            
                        else: 
                            if selected_splits != 'escolha um camp':
                                filtered_stats = db_statistics[(db_statistics['year'] == selected_years) & (db_statistics['split'] == selected_splits)]    
                            else:
                                filtered_stats = db_statistics[(db_statistics['year'] == selected_years)]
                            max_lines = filtered_stats.nlargest(3, 'games')
                            with col3:                                                          
                                #st.dataframe(filtered_stats)
                                sum_games = int(filtered_stats['games'].sum())
                                print(sum_games)
                                sum_games_win = int(filtered_stats['wins'].sum())
                                print(sum_games_win)
                                data = {
                                            'category': ['Winrate', 'Loserate'],
                                            'value':  [sum_games_win, (sum_games - sum_games_win)]
                                }
                                df = pd.DataFrame(data)
                                
                                fig = px.pie(df, values='value', names='category', 
                                            hole=0.5, color_discrete_sequence=['#FF6464', '#91C483'])
                                if selected_splits != 'escolha um camp':
                                    title="Winrate in " + selected_splits
                                else:
                                    title="Winrate in " + selected_years
                                fig.update_traces(textinfo='label+value', texttemplate='%{label}: %{value:.2f}')
                                fig.update_layout(
                                    title=title,
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    width=320,  # largura
                                    height=320  # altura
                                )
                                st.plotly_chart(fig)
                            with col4:
                                st.write('Campeões mais jogados:')
                                st.write(max_lines['champs'].iloc[0])
                                valor_sem_percentagem = max_lines['winRate'].iloc[0].replace("%", "")
                                valor_float = float(valor_sem_percentagem)
                                progress_bar = st.progress(valor_float/100)                           
                                st.write(max_lines['champs'].iloc[1])
                                valor_sem_percentagem = max_lines['winRate'].iloc[1].replace("%", "")
                                valor_float = float(valor_sem_percentagem)
                                progress_bar = st.progress(valor_float/100)  
                                st.write(max_lines['champs'].iloc[2])
                                valor_sem_percentagem = max_lines['winRate'].iloc[2].replace("%", "")
                                valor_float = float(valor_sem_percentagem)
                                progress_bar = st.progress(valor_float/100)
                            with col5:
                                st.write('')
                                st.write('')
                                st.write('')
                                st.write('')
                                st.write('')
                                textwins = f"{max_lines['wins'].iloc[0]}V - {max_lines['loses'].iloc[0]}D"
                                st.write(textwins)
                                st.write('')
                                st.write('')
                                textwins = f"{max_lines['wins'].iloc[1]}V - {max_lines['loses'].iloc[1]}D"
                                st.write(textwins)
                                st.write('')
                                st.write('')
                                textwins = f"{max_lines['wins'].iloc[2]}V - {max_lines['loses'].iloc[2]}D"
                                st.write(textwins)
                            with col6:
                                mean_k = filtered_stats['kills'].mean()
                                mean_d = filtered_stats['deaths'].mean()
                                mean_a = filtered_stats['assists'].mean()
                                data = {
                                            'category': ['kills', 'deaths', 'assists'],
                                            'value':  [mean_k, mean_d, mean_a]
                                }
                                df = pd.DataFrame(data)
                                
                                fig = px.pie(df, values='value', names='category', 
                                            hole=0.5, color_discrete_sequence=['#FF6464', '#91C483', '#8BD3F8'])
                                
                                fig.update_traces(textinfo='label+value', texttemplate='%{label}: %{value:.2f}')

                                fig.update_layout(
                                    title="Avarege status",
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    width=320,  
                                    height=320  
                                )
                                st.plotly_chart(fig)
                            with col7:
                                mean_kda = filtered_stats['KDA'].mean()
                                mean_cs = filtered_stats['CS'].mean()
                                mean_gold = filtered_stats['gold'].mean()
                                mean_damage = filtered_stats['damage'].mean()
                                st.write('Important Status in Game:')
                                st.write('')
                                st.write('Avarage KDA: {:.1f}'.format(mean_kda))
                                st.write('')
                                st.write('Avarage CS: {:.1f}'.format(mean_cs))
                                st.write('')
                                st.write('Avarage Gold: {:.1f}K'.format(mean_gold))
                                st.write('')
                                st.write('Avarage Damage: {:.1f}K'.format(mean_damage))
                            with col8:
                                mean_gm = filtered_stats['gold per minute'].mean()
                                mean_dm = filtered_stats['damage per minute'].mean()
                                data = {
                                            'category': ['Gold per minute', 'Damage per minute'],
                                            'value':  [mean_gm, mean_dm]
                                }
                                df = pd.DataFrame(data)
                                
                                fig = px.pie(df, values='value', names='category', 
                                            hole=0.5, color_discrete_sequence=['#FF6464', '#91C483'])
                                
                                fig.update_traces(textinfo='label+value', texttemplate='%{label}: %{value:.2f}')

                                fig.update_layout(
                                    title="Gold and Damage per minute",
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    width=320,  
                                    height=320  
                                )
                                st.plotly_chart(fig)
                            with col9:
                                mean_csm = filtered_stats['CS/M'].mean()
                                mean_kp = filtered_stats['kill participation'].mean()
                                mean_ks = filtered_stats['kill share'].mean()
                                mean_gs = filtered_stats['gold share'].mean()
                                st.write('Participation in Game:')
                                st.write('')
                                st.write('Avarage CS pm: {:.1f}'.format(mean_csm))
                                st.write('')
                                st.write('Avarage KP: {:.1f}%'.format(mean_kp))
                                st.write('')
                                st.write('Avarage KS: {:.1f}%'.format(mean_ks))
                                st.write('')
                                st.write('Avarage GS: {:.1f}%'.format(mean_gs))
if selected_tab == "Aba 2":
    for i in range(5):    
        with col10:
            chave = 'unique_key' + str(i)
            selected_name = st.selectbox('Selecione um nome para buscar:', options=options_names, key=chave)

        if selected_name != 'Escreva um nome':
            search_results = db_players[db_players['names'] == selected_name]
            if not search_results.empty:
                with col11:
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
                                        st.image(tmp_file.name, width=150, caption=image_name)
                                except requests.exceptions.RequestException as e:
                                    st.error(f"Erro ao baixar a imagem: {e}")
                            else:
                                st.write('Imagem não encontrada')
                        else:
                            st.write('Imagem não encontrada')
                    else:
                        st.write('Erro ao acessar o site do jogador')
                
                name_url = search_results.iloc[0]['links'].split("wiki/")
                url3 = 'https://lol.fandom.com/wiki/'+ name_url[1] +'/Statistics/2024'
                #st.write(url3)
                eras, nums = get_player_stats(url3, name_url[1].replace('_', ' '))
                db_era = pd.DataFrame(eras, columns=['year', 'split', 'champs'])
                db_nums = pd.DataFrame(nums)
                db_statistics = pd.merge(db_era, db_nums, left_index=True, right_index=True)
                db_statistics = db_statistics.rename(columns={0: 'games', 1: 'wins', 2: 'loses', 
                                                                3: 'winRate', 4: 'kills', 5: 'deaths', 
                                                                6: 'assists', 7: 'KDA', 8: 'CS', 9: 'CS/M', 
                                                                10: 'gold', 11: 'gold per minute', 
                                                                12: 'damage', 13: 'damage per minute', 
                                                                14: 'kill participation', 15: 'kill share', 
                                                                16: 'gold share'})
                for col in db_statistics.columns:
                        db_statistics[col] = replace_dash_with_mean(db_statistics[col])

                db_statistics['games'] = db_statistics['games'].astype(int)
                db_statistics['wins'] = db_statistics['wins'].astype(int)
                db_statistics['kills'] = db_statistics['kills'].astype(float)
                db_statistics['deaths'] = db_statistics['deaths'].astype(float)
                db_statistics['assists'] = db_statistics['assists'].astype(float)
                db_statistics['KDA'] = db_statistics['KDA'].astype(float)
                db_statistics['CS'] = db_statistics['CS'].astype(float)
                db_statistics['gold'] = db_statistics['gold'].str.replace('k', '')
                db_statistics['gold'] = db_statistics['gold'].astype(float)
                db_statistics['damage'] = db_statistics['damage'].str.replace('k', '')

                db_statistics['damage'] = db_statistics['damage'].astype(float)
                db_statistics['gold per minute'] = db_statistics['gold per minute'].astype(float)
                db_statistics['CS/M'] = db_statistics['CS/M'].astype(float)
                db_statistics['damage per minute'] = db_statistics['damage per minute'].astype(float)
                db_statistics['kill participation'] = db_statistics['kill participation'].str.replace('%', '')
                db_statistics['kill participation'] = db_statistics['kill participation'].astype(float)
                db_statistics['kill share'] = db_statistics['kill share'].str.replace('%', '')
                db_statistics['kill share'] = db_statistics['kill share'].astype(float)
                db_statistics['gold share'] = db_statistics['gold share'].str.replace('%', '')
                db_statistics['gold share'] = db_statistics['gold share'].astype(float)

                    
                options_years = ['escolha um ano'] + db_statistics['year'].unique().tolist()

                options_splits = ['escolha um SPLIT'] + db_statistics['split'].unique().tolist()
                    
                with col10:
                    chave2 = 'sec_key' + str(i)
                    selected_years = st.selectbox('Selecione um ano para buscar:', options=options_years, key=chave2)
                            
                    if selected_years != 'escolha um ano':
                        if selected_years != 'All Career':
                            filtered_stats = db_statistics[(db_statistics['year'] == selected_years)]
                        if selected_years == 'All Career':
                            filtered_stats = db_statistics[(db_statistics['year'] == selected_years)]
                            max_lines = filtered_stats.nlargest(3, 'games')

                    st.write('')
                    st.write('')
        with col14:
            chave3 = 'third_key' + str(i)
            selected_name1 = st.selectbox('Selecione um nome para buscar:', options=options_names, key=chave3)
            print(selected_name1)
        if selected_name1 != 'Escreva um nome':
            search_results1 = db_players[db_players['names'] == selected_name1]
            if not search_results1.empty:
                with col13:
                    status = site_status(search_results1.iloc[0]['links'])
                    if status == 200:
                        images1 = get_player_image(search_results1.iloc[0]['links'])
                        if images1:
                            db_image1 = pd.DataFrame(images1, columns=['names', 'links'])
                            if not db_image1.empty:
                                image_link1 = db_image1.iloc[0]['links']
                                image_name1 = db_image1.iloc[0]['names']
                                print(image_name1)
                                try:
                                    response = requests.get(image_link1, stream=True)
                                    response.raise_for_status()
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                        shutil.copyfileobj(response.raw, tmp_file)
                                        st.image(tmp_file.name, width=150, caption=image_name1)
                                except requests.exceptions.RequestException as e:
                                    st.error(f"Erro ao baixar a imagem: {e}")
                            else:
                                st.write('Imagem não encontrada')
                        else:
                            st.write('Imagem não encontrada')
                    else:
                        st.write('Erro ao acessar o site do jogador')
                
                name_url = search_results1.iloc[0]['links'].split("wiki/")
                url3 = 'https://lol.fandom.com/wiki/'+ name_url[1] +'/Statistics/2024'
                #st.write(url3)
                eras, nums = get_player_stats(url3, name_url[1].replace('_', ' '))
                db_era = pd.DataFrame(eras, columns=['year', 'split', 'champs'])
                db_nums = pd.DataFrame(nums)
                db_statistics = pd.merge(db_era, db_nums, left_index=True, right_index=True)
                db_statistics = db_statistics.rename(columns={0: 'games', 1: 'wins', 2: 'loses', 
                                                                3: 'winRate', 4: 'kills', 5: 'deaths', 
                                                                6: 'assists', 7: 'KDA', 8: 'CS', 9: 'CS/M', 
                                                                10: 'gold', 11: 'gold per minute', 
                                                                12: 'damage', 13: 'damage per minute', 
                                                                14: 'kill participation', 15: 'kill share', 
                                                                16: 'gold share'})
                for col in db_statistics.columns:
                        db_statistics[col] = replace_dash_with_mean(db_statistics[col])

                db_statistics['games'] = db_statistics['games'].astype(int)
                db_statistics['wins'] = db_statistics['wins'].astype(int)
                db_statistics['kills'] = db_statistics['kills'].astype(float)
                db_statistics['deaths'] = db_statistics['deaths'].astype(float)
                db_statistics['assists'] = db_statistics['assists'].astype(float)
                db_statistics['KDA'] = db_statistics['KDA'].astype(float)
                db_statistics['CS'] = db_statistics['CS'].astype(float)
                db_statistics['gold'] = db_statistics['gold'].str.replace('k', '')
                db_statistics['gold'] = db_statistics['gold'].astype(float)
                db_statistics['damage'] = db_statistics['damage'].str.replace('k', '')

                db_statistics['damage'] = db_statistics['damage'].astype(float)
                db_statistics['gold per minute'] = db_statistics['gold per minute'].astype(float)
                db_statistics['CS/M'] = db_statistics['CS/M'].astype(float)
                db_statistics['damage per minute'] = db_statistics['damage per minute'].astype(float)
                db_statistics['kill participation'] = db_statistics['kill participation'].str.replace('%', '')
                db_statistics['kill participation'] = db_statistics['kill participation'].astype(float)
                db_statistics['kill share'] = db_statistics['kill share'].str.replace('%', '')
                db_statistics['kill share'] = db_statistics['kill share'].astype(float)
                db_statistics['gold share'] = db_statistics['gold share'].str.replace('%', '')
                db_statistics['gold share'] = db_statistics['gold share'].astype(float)

                    
                options_years = ['escolha um ano'] + db_statistics['year'].unique().tolist()

                options_splits = ['escolha um SPLIT'] + db_statistics['split'].unique().tolist()
                    
                with col14:
                    chave4 = 'for_key' + str(i)
                    selected_years1 = st.selectbox('Selecione um ano para buscar:', options=options_years, key=chave4)
                            
                    if selected_years1 != 'escolha um ano':
                        if selected_years1 != 'All Career':
                            filtered_stats1 = db_statistics[(db_statistics['year'] == selected_years)]
                        if selected_years1 == 'All Career':
                            filtered_stats1 = db_statistics[(db_statistics['year'] == selected_years1)]
                            max_lines = filtered_stats1.nlargest(3, 'games')
                    st.write('')
                    st.write('')
        with col12:
            if selected_name1 != 'Escreva um nome' and selected_name != 'Escreva um nome':
                if selected_years1 != 'escolha um ano'and selected_years != 'escolha um ano':
                    mean_kp = filtered_stats['kill participation'].mean()
                    mean_ks = filtered_stats['kill share'].mean()
                    mean_gs = filtered_stats['gold share'].mean()
                    mean_damage = filtered_stats['damage'].mean()
                    mean_kp1 = filtered_stats1['kill participation'].mean()
                    mean_ks1 = filtered_stats1['kill share'].mean()
                    mean_gs1 = filtered_stats1['gold share'].mean()
                    mean_damage1 = filtered_stats1['damage'].mean()

                    if mean_kp > mean_kp1:
                        st.write(selected_name + ' tem {:.1f}% '.format(mean_kp - mean_kp1) + 'a mais de kill participation do que ' + selected_name1)
                    else:
                        st.write(selected_name1 + ' tem {:.1f}% '.format(mean_kp1 - mean_kp) + 'a mais de kill participation do que ' + selected_name)
                    if mean_ks > mean_ks1:
                        st.write(selected_name + ' tem {:.1f}% '.format(mean_ks - mean_ks1) + 'a mais de kill share do que ' + selected_name1)
                    else:
                        st.write(selected_name1 + ' tem {:.1f}% '.format(mean_ks1 - mean_ks) + 'a mais de kill share do que ' + selected_name)
                    if mean_gs > mean_gs1:
                        st.write(selected_name + ' tem {:.1f}% '.format(mean_gs - mean_gs1) + 'a mais de gold share do que ' + selected_name1)
                    else:
                        st.write(selected_name1 + ' tem {:.1f}% '.format(mean_gs1 - mean_gs) + 'a mais de gold share do que ' + selected_name)
                    if mean_kp > mean_kp1:
                        st.write(selected_name + ' tem {:.1f}% '.format(mean_damage - mean_damage1) + 'a mais de damage do que ' + selected_name1)
                    else:
                        st.write(selected_name1 + ' tem {:.1f}% '.format(mean_damage1 - mean_damage) + 'a mais de damage do que ' + selected_name)
                    st.write('')
    

                    
                    

                    
                
        
    
    
        


