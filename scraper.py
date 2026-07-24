import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

DATABASE_PREZZI = "prezzi_storici.json"

def carica_database_prezzi():
    if os.path.exists(DATABASE_PREZZI):
        with open(DATABASE_PREZZI, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except json.JSONDecodeError: return {}
    return {}

def salva_database_prezzi(database):
    with open(DATABASE_PREZZI, 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)

def scarica_offerte_lidl(nome_negozio, id_negozio, colore, url_principale, database_prezzi):
    print(f"\n--- Avvio estrazione dati JSON da HTML per {nome_negozio} ---")
    
    prodotti_totali = []
    
    # Mascheriamo il bot come se fosse un normale iPhone o PC
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    try:
        print(f"Scaricando la pagina: {url_principale}")
        risposta = requests.get(url_principale, headers=headers, timeout=15)
        
        # Se il server ci blocca (Errore 403), ce ne accorgiamo subito
        if risposta.status_code != 200:
            print(f"ATTENZIONE! Il sito ha bloccato la richiesta. Codice errore: {risposta.status_code}")
            return

        soup = BeautifulSoup(risposta.text, 'html.parser')
        
        # Cerchiamo tutti i blocchi HTML che contengono l'attributo segreto 'data-grid-data'
        nodi_prodotti = soup.find_all('div', attrs={'data-grid-data': True})
        print(f"Trovati {len(nodi_prodotti)} prodotti nascosti nella pagina.")

        for index, nodo in enumerate(nodi_prodotti):
            try:
                dati_grezzi = nodo['data-grid-data']
                # Trasformiamo il testo dell'attributo HTML in un vero oggetto Python (JSON)
                item = json.loads(dati_grezzi)
                
                # ESTRAZIONE DATI PURI
                nome = item.get('fullTitle') or item.get('title', 'Prodotto Sconosciuto')
                immagine = item.get('image', 'https://img.icons8.com/ios-filled/100/737373/shopping-cart.png')
                categoria = item.get('category', 'Volantino')
                
                # ESTRAZIONE PREZZI
                info_prezzo = item.get('price', {})
                prezzo_scontato = info_prezzo.get('price', "N/D")
                prezzo_originale = info_prezzo.get('oldPrice', None)
                
                info_sconto = info_prezzo.get('discount', {})
                perc_sconto = info_sconto.get('percentageDiscount', 0)
                prezzo_unita = info_prezzo.get('basePrice', {}).get('text', '')
                
                # ESTRAZIONE E CONVERSIONE DATE DA TIMESTAMP A YYYY-MM-DD
                start_ts = item.get('storeStartDate')
                end_ts = item.get('storeEndDate')
                
                data_inizio = datetime.fromtimestamp(start_ts).strftime('%Y-%m-%d') if start_ts else "N/D"
                data_fine = datetime.fromtimestamp(end_ts).strftime('%Y-%m-%d') if end_ts else "N/D"
                
                # AGGIORNAMENTO STORICO PREZZI (Cervello dell'App)
                if prezzo_originale is not None:
                    chiave_db = f"{nome_negozio}_{nome}"
                    database_prezzi[chiave_db] = float(prezzo_originale)
                    
                # ASSEMBLAGGIO FINALE DEL PRODOTTO PER L'APP
                prodotti_totali.append({
                    "id": f"{id_negozio}_{item.get('productId', index)}",
                    "nome": nome,
                    "categoria": categoria,
                    "immagine_url": immagine,
                    "prezzo_originale": prezzo_originale,
                    "prezzo_scontato": prezzo_scontato,
                    "percentuale_sconto": perc_sconto,
                    "prezzo_unita_misura": prezzo_unita,
                    "negozio": nome_negozio,
                    "data_inizio": data_inizio,
                    "data_fine": data_fine
                })
            except Exception as e_item:
                print(f"Errore nella lettura di un singolo prodotto: {e_item}")

    except Exception as e:
        print(f"Errore critico durante lo scraping: {e}")

    # SALVATAGGIO DEI DATI NEL FILE JSON PER L'APP REACT NATIVE
    if prodotti_totali:
        # Troviamo la data minima e massima di tutto il volantino
        date_inizio_valide = [p['data_inizio'] for p in prodotti_totali if p['data_inizio'] != "N/D"]
        date_fine_valide = [p['data_fine'] for p in prodotti_totali if p['data_fine'] != "N/D"]
        
        vol_inizio = min(date_inizio_valide) if date_inizio_valide else "N/D"
        vol_fine = max(date_fine_valide) if date_fine_valide else "N/D"

        dati_finali = {
            "negozio": { "id": id_negozio, "nome": nome_negozio, "colore_brand": colore },
            "volantino": { "data_inizio": vol_inizio, "data_fine": vol_fine },
            "prodotti": prodotti_totali
        }
        
        with open(f"{id_negozio}_offerte.json", 'w', encoding='utf-8') as f:
            json.dump(dati_finali, f, ensure_ascii=False, indent=2)
            
        print(f"Salvato con successo: {id_negozio}_offerte.json ({len(prodotti_totali)} prodotti trovati)")
    else:
        print("Nessun prodotto estratto. Il file non è stato sovrascritto.")

if __name__ == "__main__":
    db_prezzi = carica_database_prezzi()
    
    # Inserisci qui l'URL della pagina in cui hai catturato il codice (es. /c/super-offerte-kw-30-26/a10099203)
    URL_LIDL = "https://www.lidl.it/c/super-offerte-kw-30-26/a10099203"
    
    scarica_offerte_lidl("Lidl", "lidl", "#0050AA", URL_LIDL, db_prezzi)
    
    salva_database_prezzi(db_prezzi)
    print("\n--- Scansione e aggiornamento completati ---")
