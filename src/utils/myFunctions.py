import pandas as pd
import gzip
import json
import ast
from langdetect import detect, LangDetectException

def jsonGzipToDataframe(file):
  '''
  Rafael Balestrini: It decompresses and reads a JSON file, converts it into a list, and converts the
  list into a pandas dataframe.
  Parameters:
    file (str): The JSON file that is compressed
  Returns:
    A dataframe resulting from having converted the list where the lines of the
    compressed JSON file were saved.
  '''
  recodset = []
  with gzip.open(file, 'rt', encoding = 'utf-8') as lines:
    for line in lines:
      try:
        decodeLine = json.loads(line.strip())
        recodset.append(decodeLine)
      except json.JSONDecodeError as e:
        print(f"Error en línea: {line.strip()}")
        print(e)
  return pd.DataFrame(recodset)

def jsonGzipToDataframe2(file):
  '''
  Rafael Balestrini: Unlike version 1 of this function, here we will read the JSON lines with
  'ast.literal_eval()' in order to deal with single and double quotes.
  Parameters:
    file (str): The JSON file that is compressed,
  Returns:
    A dataframe resulting from having converted the list where the lines of the
    compressed JSON file were saved.
  '''
  recodset = []
  with gzip.open(file, 'rb') as lines:
    for line in lines:
      try:
        decodeLine = line.decode('utf-8')
        recodset.append(ast.literal_eval(decodeLine.strip()))
      except json.JSONDecodeError as e:
        print(f"Error en línea: {line.strip()}")
        print(e)
    return pd.DataFrame(recodset)

def toDommyColumns(df, column):
  '''
  Rafael Balestrini: Converts the column of a dataframe that contains list type structure into
  several dummy columns.
  Parameters:
    df (dataframe): Dataframe with list type column.
    column (str): The name of the column to convert.
  Returns:
    The dataframe with the dummy columns.
  '''
  # Convertimos la columna a una estructura tipo listas y guardamos en otro dataframe
  df[column] = df[column].apply(lambda x: ast.literal_eval(x))
  dfTagsList = pd.DataFrame(df[column].tolist())

  # Cambiemos la forma de dfTagsList en una tabla con un nuevo nivel más interno de filas para cada
  # juego
  DataFramePanel = dfTagsList.stack()

  # Un dataframe en el que cada fila indica uno de los tags del juego, es decir, si el juego 1 tiene 3
  # tags entonces habran 3 filas, una para cada tag
  dummyColumns = pd.get_dummies(DataFramePanel, prefix = column, prefix_sep='_')

  # ¿Para qué tantas filas? Agrupemos todos los tags de cada juego en una sola fila
  dummyColumns = dummyColumns.groupby(level = [0], axis = 0).sum()

  return dummyColumns

def joinLanguage(df, column):
  '''
  Rafael Balestrini: Function that adds a column to the 'df' dataframe indicating the language
  detected in the text of the column 'column'.
  Parameters:
    df (dataframe): Dataframe with list type column.
    column (str): The name of the column to convert.
  Returns:
    The dataframe with language column.
  '''
  def detectLanguage(texto):
    try:
        return detect(texto)
    except LangDetectException as e:
        #print(f"Error al detectar idioma en el texto: {texto}")
        #print(f"Error: {e}")
        return None
  
  df['language'] = df[column].apply(detectLanguage)

  return df