import json
import os
import re
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

def pulisci_html(testo):
    if not testo: return ""
    # Rimuove i tag HTML ma mantiene gli a capo per le liste
    testo = re.sub(r'<li>', '• ', testo)
    testo = re.sub(r'<br\s*/?>|</li>', '\n', testo)
    testo = re.sub(r'<[^>]+>', '', testo)
    # Pulisce entità come &nbsp; e &euro;
    testo = testo.replace('&nbsp;', ' ').replace('&euro;', '€').replace('&deg;', '°')
    return testo.strip()

def scarica_tutto_lidl(nome_negozio, id_negozio, colore, db_prezzi):
    print(f"\n--- Avvio Spider Dinamico per {nome_negozio} ---")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    }

    base_url = "https://www.lidl.it"
    link_da_esplorare = set()

    # 1. ESPLORAZIONE DINAMICA: Troviamo tutte le sezioni attive
    try:
        print("Scansione della Homepage per trovare i link attuali...")
        risposta_home = requests.get(base_url, headers=headers, timeout=15)
        soup_home = BeautifulSoup(risposta_home.text, 'html.parser')
        
        for a in soup_home.find_all('a', href=True):
            href = a['href']
            # I volantini e le offerte speciali sono sempre sotto /c/ o /h/
            if href.startswith('/c/') or href.startswith('/h/'):
                link_da_esplorare.add(base_url + href)
                
        print(f"Trovate {len(link_da_esplorare)} sezioni promozionali dinamiche.")
    except Exception as e:
        print(f"Errore nella navigazione principale: {e}")
        return

    # 2. RACCOLTA DATI
    prodotti_totali = []
    id_visti = set() # Evitiamo doppioni se un prodotto è in due sezioni
    
    # Esploriamo un massimo di 25 sezioni per evitare blocchi del server
    for url_sezione in list(link_da_esplorare)[:25]:
        try:
            print(f"Analisi: {url_sezione}")
            risposta = requests.get(url_sezione, headers=headers, timeout=15)
            if risposta.status_code != 200: continue
            
            soup = BeautifulSoup(risposta.text, 'html.parser')
            nodi_prodotti = soup.find_all('div', attrs={'data-grid-data': True})
            
            for nodo in nodi_prodotti:
                item = json.loads(nodo['data-grid-data'])
                prod_id = item.get('productId')
                
                if not prod_id or prod_id in id_visti: continue
                id_visti.add(prod_id)
                
                # ESTRAZIONE INTELLIGENTE CATEGORIA
                categoria_grezza = item.get('keyfacts', {}).get('wonCategoryPrimary', '')
                if categoria_grezza:
                    # Prende l'ultimo pezzo del percorso (es. Carne di Maiale)
                    categoria_pulita = categoria_grezza.split('/')[-1].strip()
                else:
                    categoria_pulita = item.get('category', 'Offerte Speciali')
                
                # DATI BASE
                nome = item.get('fullTitle') or item.get('title', 'Prodotto')
                immagine = item.get('image', '')
                descrizione_html = item.get('keyfacts', {}).get('description', '')
                descrizione_pulita = pulisci_html(descrizione_html)
                
                # PREZZI E DATE
                info_prezzo = item.get('price', {})
                prezzo_scontato = info_prezzo.get('price', "N/D")
                prezzo_originale = info_prezzo.get('oldPrice', None)
                perc_sconto = info_prezzo.get('discount', {}).get('percentageDiscount', 0)
                prezzo_unita = info_prezzo.get('basePrice', {}).get('text', '')
                
                start_ts = item.get('storeStartDate')
                end_ts = item.get('storeEndDate')
                data_inizio = datetime.fromtimestamp(start_ts).strftime('%Y-%m-%d') if start_ts else "N/D"
                data_fine = datetime.fromtimestamp(end_ts).strftime('%Y-%m-%d') if end_ts else "N/D"
                
                if prezzo_originale is not None:
                    db_prezzi[f"{nome_negozio}_{nome}"] = float(prezzo_originale)
                    
                prodotti_totali.append({
                    "id": f"{id_negozio}_{prod_id}",
                    "nome": nome,
                    "categoria": categoria_pulita,
                    "descrizione": descrizione_pulita,
                    "immagine_url": immagine,
                    "prezzo_originale": prezzo_originale,
                    "prezzo_scontato": prezzo_scontato,
                    "percentuale_sconto": perc_sconto,
                    "prezzo_unita_misura": prezzo_unita,
                    "negozio": nome_negozio,
                    "data_inizio": data_inizio,
                    "data_fine": data_fine
                })
        except Exception: pass

    # 3. SALVATAGGIO
    if prodotti_totali:
        # Troviamo i margini temporali generali per il file
        date_inizio = [p['data_inizio'] for p in prodotti_totali if p['data_inizio'] != "N/D"]
        date_fine = [p['data_fine'] for p in prodotti_totali if p['data_fine'] != "N/D"]
        
        dati_finali = {
            "negozio": { "id": id_negozio, "nome": nome_negozio, "colore_brand": colore },
            "volantino": { 
                "data_inizio": min(date_inizio) if date_inizio else "N/D", 
                "data_fine": max(date_fine) if date_fine else "N/D" 
            },
            "prodotti": prodotti_totali
        }
        with open(f"{id_negozio}_offerte.json", 'w', encoding='utf-8') as f:
            json.dump(dati_finali, f, ensure_ascii=False, indent=2)
        print(f"Scansione globale terminata. Salva {len(prodotti_totali)} offerte.")

if __name__ == "__main__":
    db_prezzi = carica_database_prezzi()
    # Il bot ora parte solo dal nome del negozio, trova lui i link!
    scarica_tutto_lidl("Lidl", "lidl", "#0050AA", db_prezzi)
    salva_database_prezzi(db_prezzi)
