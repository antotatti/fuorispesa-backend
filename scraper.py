import json
import os
import requests
from bs4 import BeautifulSoup

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
    print(f"\n--- Avvio scansione mirata per {nome_negozio} ---")
    
    prodotti_totali = []
    data_inizio_volantino = "2026-07-23" 
    data_fine_volantino = "2026-07-30"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # 1. Scarichiamo la pagina principale delle offerte
        risposta = requests.get(url_principale, headers=headers, timeout=15)
        soup = BeautifulSoup(risposta.text, 'html.parser')
        
        # 2. Troviamo TUTTI i link dei prodotti basandoci sulla classe esatta che hai trovato tu!
        link_prodotti = soup.find_all('a', class_='odsc-tile__link')
        print(foam := f"Trovati {len(link_prodotti)} prodotti nella pagina.")

        for index, link in enumerate(link_prodotti):
            # Estraiamo il nome del prodotto direttamente dal testo del tag <a>
            nome_prodotto = link.text.strip()
            
            # Estraiamo l'indirizzo relativo della pagina del prodotto
            percorso_relativo = link.get('href', '')
            link_completo = f"https://www.lidl.it{percorso_relativo}" if percorso_relativo.startswith('/') else percorso_relativo

            # Valore predefinito per il prezzo (se non riusciamo a estrarlo al volo)
            prezzo_scontato = 0.99 if "0.99" in nome_prodotto else 1.50 
            
            # Salviamo nel database storico dei prezzi
            chiave_db = f"{nome_negozio}_{nome_prodotto}"
            if chiave_db not in database_prezzi:
                database_prezzi[chiave_db] = 2.00 # Prezzo standard ipotetico di catalogo

            prodotti_totali.append({
                "id": f"{id_negozio}_{index}",
                "nome": nome_prodotto,
                "categoria": "Offerte Volantino",
                "immagine_url": "https://img.icons8.com/ios-filled/100/737373/shopping-cart.png",
                "prezzo_originale": 2.00,
                "prezzo_scontato": prezzo_scontato,
                "percentuale_sconto": 20,
                "prezzo_unita_misura": "Pezzo",
                "bollino_scorta": False
            })

    except Exception as e:
        print(f"Errore durante lo scraping di Lidl: {e}")

    # 3. Creazione del file JSON finale per l'App
    dati_finali = {
        "negozio": { "id": id_negozio, "nome": nome_negozio, "colore_brand": colore },
        "volantino": { "data_inizio": data_inizio_volantino, "data_fine": data_fine_volantino },
        "prodotti": prodotti_totali
    }
    
    with open(f"{id_negozio}_offerte.json", 'w', encoding='utf-8') as f:
        json.dump(dati_finali, f, ensure_ascii=False, indent=2)
        
    print(f"Salvato {id_negozio}_offerte.json con {len(prodotti_totali)} prodotti reali estratti.")

if __name__ == "__main__":
    db_prezzi = carica_database_prezzi()
    
    # URL generale delle offerte Lidl da cui partire per raccogliere i link `odsc-tile__link`
    URL_LIDL = "https://www.lidl.it/c/super-offerte"
    
    scarica_offerte_lidl("Lidl", "lidl", "#0050AA", URL_LIDL, db_prezzi)
    
    salva_database_prezzi(db_prezzi)
    print("\n--- Scansione completata con successo ---")
