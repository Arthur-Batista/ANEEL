
import pandas as pd
caminho = rf"C:\Users\Arthur\Downloads\reclamacoes-n1e2-distribuidoras-2024.csv"
chunksize = 1_000_000
lista = []
i = 0

for chunk in pd.read_csv(caminho, encoding='latin1', sep=';', chunksize=chunksize):
    i += 1
    print(f"Lendo partição {i}")
    lista.append(chunk)

df_total = pd.concat(lista)

