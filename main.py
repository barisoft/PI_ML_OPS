from typing import Union, List
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
from dateutil import parser
from typing import List
#import pyarrow.parquet as pq
import numpy as np  # Agregamos la importación de numpy
import os
import pyarrow.parquet as pq

app = FastAPI()

# App de prueba 
@app.get("/")
def read_root():
  return {
      'Proyecto': 'Proyecto Individual 1',
      'Empresa': 'HENRY',
      'Autor': 'Rafael Balestrini',
      'Cohorte': 'DATAPT09'
  }

# <1>

@app.get('/developer/{desarrollador}')
def developer(desarrollador: str):
  '''Devuelve la cantidad de items y porcentaje de contenido Free por año según empresa
     desarrolladora
  '''
  try:
    df = pq.read_table('./src/datasource/render/steam_games_4Api.parquet').to_pandas()
    #df = pd.read_csv('./src/datasource/render/steam_games_4Api.csv.gz')
  except Exception as err:
    return (f'{err}')
     
  # Filtrar el DataFrame por desarrollador
  dfFiltrado = df[df['developer'] == desarrollador]
  # Contar la cantidad de items por año
  cantidadItems = dfFiltrado.groupby('year').size().reset_index(name = 'Cantidad de Items')
  # Calcular el porcentaje de juegos gratuitos por año
  dfFiltrado['free'] = (dfFiltrado['tags_free_to_play'] == 1) | (dfFiltrado['price'] == 0)
  contenidoFree = dfFiltrado.groupby('year')['free'].mean().reset_index(name = 'Contenido Free')
  # Combinar los resultados en un nuevo DataFrame
  return cantidadItems.merge(contenidoFree, on = 'year').to_dict('records')

# <2>

@app.get('/userdata/{userId}')
def userdata(userId: str):
  try:
    dfUserItems = pq.read_table('./src/datasource/render/user_items_4Api.parquet').to_pandas()
    dfSteam = pq.read_table('./src/datasource/render/steam_games_4Api.parquet').to_pandas()
    dfUserReviews = pq.read_table('./src/datasource/render/user_reviews_4Api.parquet').to_pandas()
    #dfUserItems = pd.read_csv('./src/datasource/render/user_items_4Api.csv.gz') 
    #dfSteam = pd.read_csv('./src/datasource/render/steam_games_4Api.csv.gz') 
    #dfUserReviews = pd.read_csv('./src/datasource/render/user_reviews_4Api.csv.gz') 
  except Exception as err:
    return (f'{err}')

  # Filtrar el dataframe dfUserItems por usuario
  userItems = dfUserItems[dfUserItems['user_id'] == userId]

  # Unir el dataframe filtrado con los dfSteam que coincidan con 'item_id'
  itemsWithPrices = userItems.merge(dfSteam, left_on = 'item_id', right_on = 'id', how = 'inner')
  
  # Calcular el gasto total
  totalSpent = itemsWithPrices['price'].sum()
  
  # Calcular el porcentaje de reviews
  userRecommends = dfUserReviews.query('user_id == @userId and recommend == True').shape[0]
  per = (userRecommends * 100) / userItems.shape[0]

  # Crear el diccionario de resultados
  return {
      'Usuario': userId,
      'Dinero gastado': round(totalSpent, 2),
      '% de recomendacion': round(per, 2),
      'Cantidad de items': userItems.shape[0]
  }

# <3>

@app.get('/UserForGenre/{genero}')
def UserForGenre(genero: str):
  """
  Obtiene el usuario que acumula más horas jugadas y una lista de la acumulación de horas jugadas por año del juego.

  Parameters:
    genero (str): This is the genre on which the search will be based

  Returns:
    A dictionary with the following information:
      - "User with the most hours played": The ID of the user with the most hours played.
      - "Hours played": A list of dictionaries with the following information:
        - "Year": The year the game was released.
        - "Hours": The number of hours played in that year.
  """
  # Let's put together the name of the genre column to search in dfSteam
  try:
    dfUserItems = pq.read_table('./src/datasource/render/user_items_4Api.parquet').to_pandas()
    dfSteam = pq.read_table('./src/datasource/render/steam_games_4Api.parquet').to_pandas()
    #dfUserItems = pd.read_csv('./src/datasource/render/user_items_4Api.csv.gz') 
    #dfSteam = pd.read_csv('./src/datasource/render/steam_games_4Api.csv.gz') 
  except Exception as err:
    return (f'{err}')
  
  genreSteam = f'genres_{genero}'
    
  # In 'gamesGenre' I will only have Steam games that match the genre
  gamesGenre = dfSteam[dfSteam[genreSteam] == 1].reset_index(drop = True)

  # Let's add the 'gamesGenre' columns to 'dfUserItems'. Now we have the years of the games
  # next to the items!
  dfUnion = dfUserItems.merge(gamesGenre, left_on = 'item_id', right_on = 'id', how = 'inner')
    
  # Calculate total hours played per user
  totalPlaytimeXUser = dfUnion.groupby('user_id')['playtime_forever'].sum()

  # Let's find the user with the most hours played
  userWithMostPlaytime = totalPlaytimeXUser.idxmax()

  # Now that we have found the user, let's filter it to only be left with their items
  userItems = dfUnion[dfUnion['user_id'] == userWithMostPlaytime]

  # userItemsYear keeps only the columns we need
  userItems = userItems[['year','playtime_forever']]
  
  # Let's group the DataFrame 'userItems' by year and add the column 'playtime_forever'
  userItems = userItems.groupby('year')['playtime_forever'].sum().reset_index()

  # Let's rename the column titles to fit the result dictionary
  dictionary = userItems.rename(
    columns = {'year': 'Año', 'playtime_forever': 'Horas'}).to_dict(orient='records')

  # Create the results dictionary
  return {"Usuario con más horas jugadas para el género " + genero: userWithMostPlaytime,
          "Horas jugadas por año": dictionary}

# <4>

@app.get('/best_developer_year/{year}')
def best_developer_year(year: int):
  """
  Devuelve el top 3 de desarrolladores con juegos mas recomendados por usuarios para el año dado.
  Params:
    year (int): El año a considerar.
  Returns:
    pd.DataFrame: Un DataFrame con las columnas 'developer' y 'recomendaciones', ordenado por
    'recomendaciones' de forma descendente y limitado a las 3 primeras filas.
  """
  try:
    dfUnionLanguage = pd.read_csv('./src/datasource/render/user_reviews_2Api.csv.gz')
  except Exception as err:
    return (f'{err}')
  
  if not isinstance(year, int):
    return print(f'{year} fuera de rango')
  # Filtrar los juegos recomendados para el año dado
  juegosRecomendados = dfUnionLanguage[
      (dfUnionLanguage['year'] == year) &
      (dfUnionLanguage['recommend'] == True) &
      (dfUnionLanguage['sentimentAnalysis'] == 2)
  ]  
  
  # Contar las recomendaciones por desarrollador
  recomendacionesXDesarrollador = (
      juegosRecomendados.groupby('developer')['item_id'].nunique()
  )  
  
  # Convertir a DataFrame y ordenar por recomendaciones de forma descendente
  topDesarrolladores = recomendacionesXDesarrollador.to_frame(name = 'recomendaciones').reset_index()
  topDesarrolladores = topDesarrolladores.sort_values(by = 'recomendaciones', ascending = False)  

  topDesarrolladoresLista = []
  for i in range(0, 3):
      puesto = f"Puesto {i + 1}"
      try:
        desarrollador = topDesarrolladores.loc[i, 'developer']
      except Exception as e:
         return print(f'{year} fuera de rango\n{e}')
      topDesarrolladoresLista.append({puesto: desarrollador})
  return topDesarrolladoresLista

# <5>

@app.get('/developer_reviews_analysis/{developer}')
def developer_reviews_analysis(developer: str) -> dict:
  """Devuelve un diccionario con el nombre del desarrollador como llave y una lista con la
  cantidad de reseñas negativas y positivas del desarrollador.
  Params:
      developer (str): El nombre del desarrollador.
  Returns:
      dict: Un diccionario con la siguiente estructura: {'nombre_desarrollador': ['Negative = X', 'Positive = Y']}
  """
  # Filtrar las reseñas del desarrollador especificado

  try:
    dfUnionLanguage = pd.read_csv('./src/datasource/render/user_reviews_2Api.csv.gz')
  except Exception as err:
    return (f'{err}')

  developerReviews = dfUnionLanguage[dfUnionLanguage['developer'] == developer]

   # Contar las reseñas positivas y negativas
  negativeCount = developerReviews[developerReviews['sentimentAnalysis'] == 0].shape[0]
  positiveCount = developerReviews[developerReviews['sentimentAnalysis'] == 2].shape[0]

   # Crear el diccionario de resultados
  resultado = {
      developer: [f"Negative = {negativeCount}", f"Positive = {positiveCount}"]
  }

  return resultado