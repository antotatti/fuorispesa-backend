import json
import os
from datetime import datetime

# Nome del file che farà da "memoria" per i prezzi standard
DATABASE_PREZZI = "prezzi_storici.json"

def carica_database_prezzi():
    """Legge il database storico dei prezzi, se esiste."""
    if os.path.exists(DATABASE_PREZZI):
        with open(DATABASE_PREZZI, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def salva_database_prezzi(database):
    """Salva il dizionario aggiornato nel file JSON."""
    with open(DATABASE_PREZZI, 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    print("Database prezzi storici aggiornato con successo.")

def scarica_dati_negozio(nome_negozio, id_negozio, colore, urls_sezioni, database_prezzi):
    print(f"\n--- Avvio scansione per {nome_negozio} ---")
    
    prodotti_totali = []
    
    # 1. LOGICA DI ESTRAZIONE DATE DEL VOLANTINO
    # In un sistema reale, queste date verrebbero estratte leggendo l'HTML della pagina.
    # Per ora simuliamo che il bot le abbia trovate sul sito.
    data_inizio_volantino = "2026-07-23" 
    data_fine_volantino = "2026-07-30"
    
    # 2. NAVIGAZIONE MULTI-PAGINA
    for url in urls_sezioni:
        print(f"Scansionando la sezione: {url}")
        
        # Qui il bot si collegherebbe a 'url' e farebbe il parsing dell'HTML (es. BeautifulSoup)
        # requests.get(url)...
        
        # --- SIMULAZIONE PRODOTTI TROVATI NELLA SEZIONE ---
        # Immaginiamo che il bot trovi questo prodotto nella pagina corrente
        nome_prodotto_trovato = f"Prodotto da {url.split('/')[-1]}"
        prezzo_originale_trovato = 2.50
        
        # 3. AGGIORNAMENTO DEL DATABASE STORICO (L'intelligenza dell'app)
        # Se c'è un prezzo originale, lo salviamo o aggiorniamo nella memoria globale!
        if prezzo_originale_trovato is not None:
            # Creiamo una chiave univoca, es: "Lidl_Prodotto da super-offerte"
            chiave_db = f"{nome_negozio}_{nome_prodotto_trovato}"
            database_prezzi[chiave_db] = prezzo_originale_trovato
        
        prodotti_totali.append({
            "id": f"{id_negozio}_{data_inizio_volantino}_{len(prodotti_totali)}",
            "nome": nome_prodotto_trovato,
            "categoria": "Dispensa",
            "immagine_url": "https://via.placeholder.com/150", # Inserire qui l'estrazione dell'img vera
            "prezzo_originale": prezzo_originale_trovato,
            "prezzo_scontato": 1.50,
            "percentuale_sconto": 40,
            "prezzo_unita_misura": "1 kg",
            "bollino_scorta": False
        })

    # 4. CREAZIONE DEL JSON DEL NEGOZIO
    dati_finali = {
        "negozio": {
            "id": id_negozio,
            "nome": nome_negozio,
            "colore_brand": colore
        },
        "volantino": {
            "data_inizio": data_inizio_volantino,
            "data_fine": data_fine_volantino
        },
        "prodotti": prodotti_totali
    }
    
    # 5. SALVATAGGIO DEL FILE DEL NEGOZIO
    nome_file = f"{id_negozio}_offerte.json"
    with open(nome_file, 'w', encoding='utf-8') as f:
        json.dump(dati_finali, f, ensure_ascii=False, indent=2)
        
    print(f"Salvato {nome_file} con {len(prodotti_totali)} offerte.")

# --- ESECUZIONE PRINCIPALE ---
if __name__ == "__main__":
    # Carichiamo la memoria storica
    db_prezzi = carica_database_prezzi()
    
    # Configuriamo le scansioni definendo TUTTE le pagine da visitare per ogni negozio
    sezioni_lidl = [
        "https://www.lidl.it/c/super-offerte",
        "https://www.lidl.it/c/offerte-weekend",
        "https://www.lidl.it/c/sotto-costo"
    ]
    scarica_dati_negozio("Lidl", "lidl", "#0050AA", sezioni_lidl, db_prezzi)
    
    sezioni_conad = ["https://www.conad.it/offerte-locali", "https://www.conad.it/bis"]
    scarica_dati_negozio("Conad", "conad", "#E2231A", sezioni_conad, db_prezzi)
    
    sezioni_esselunga = ["https://www.esselunga.it/offerte"]
    scarica_dati_negozio("Esselunga", "esselunga", "#FFD700", sezioni_esselunga, db_prezzi)
    
    # Alla fine di tutte le scansioni, salviamo la memoria storica aggiornata
    salva_database_prezzi(db_prezzi)
    
    print("\n--- Aggiornamento notturno completato! ---")
