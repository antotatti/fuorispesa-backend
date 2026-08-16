import json
import uuid
import re
import urllib.request
from datetime import datetime
import os
import sys

# =======================================================
# Auto-installazione del modulo anti-bot di rete per GitHub Actions
try:
    from curl_cffi import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install curl-cffi")
    from curl_cffi import requests
# =======================================================

# CHIAVI SUPABASE
SUPABASE_URL = "https://sqxadjjbodjwozbqcqmk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNxeGFkampib2Rqd296YnFjcW1rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ2MjEyMzcsImV4cCI6MjEwMDE5NzIzN30.eL2xjp4S67j1IxWsl8NPi05-YYJz8SNPls0NlNcNgj4"

prodotti_estratti = {}

def parse_loyalty(raw_data):
    """Analizza il JSON per capire se serve la tessera Fidaty"""
    raw_str = json.dumps(raw_data).lower()
    if raw_data.get("requiresLoyaltyCard") is True: return True
    if raw_data.get("loyaltyPrice") is not None: return True
    if raw_data.get("fidatyPrice") is not None: return True
    if "fidaty" in str(raw_data.get("promotionType", "")).lower(): return True
    
    parole_chiave = ["fidaty", "fìdaty", "tessera fedeltà", "sconto cassa", "solo con tessera"]
    if any(parola in raw_str for parola in parole_chiave): return True
    return False

def extract_from_json(obj, context_volantino="OFFERTE VOLANTINO"):
    """Esplora ricorsivamente QUALSIASI blocco JSON per scovare prodotti"""
    if isinstance(obj, dict):
        chiavi = {k.lower(): v for k, v in obj.items()}
        nome = chiavi.get('name') or chiavi.get('nome') or chiavi.get('title')
        prezzo = chiavi.get('discountedprice') or chiavi.get('price') or chiavi.get('currentprice') or chiavi.get('prezzo')
        
        # Se ha un nome e un prezzo validi, è un prodotto!
        if nome and prezzo and isinstance(nome, str):
            try:
                p_val = float(str(prezzo).replace(',', '.').replace('€', '').strip())
                if p_val > 0:
                    firma = f"{str(nome).strip().lower()}_{p_val}"
                    if firma not in prodotti_estratti:
                        volantino = obj.get('promotionName', obj.get('catalogName', context_volantino))
                        if not volantino or str(volantino).strip() == "": volantino = context_volantino
                        
                        print(f"   [+] TROVATO: {str(nome)[:45]}... a €{p_val}")
                        prodotti_estratti[firma] = {
                            "raw": obj,
                            "nome": str(nome)[:100],
                            "prezzo": p_val,
                            "volantino": str(volantino).upper(),
                            "loyalty": parse_loyalty(obj)
                        }
                    else:
                        if parse_loyalty(obj): prodotti_estratti[firma]["loyalty"] = True
            except: pass
        
        # Continua a scavare dentro i dizionari
        for v in obj.values():
            extract_from_json(v, context_volantino)
            
    elif isinstance(obj, list):
        # Continua a scavare dentro le liste
        for item in obj:
            extract_from_json(item, context_volantino)


def run_scraper():
    print("🚀 AVVIO MOTORE GHOST API (ANTI-BLOCCO GITHUB ACTIONS) 🚀")
    
    # Questo comando 'impersonate' clona l'impronta di Chrome aggirando Akamai
    session = requests.Session(impersonate="chrome110")
    session.headers.update({
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    # Analizziamo le pagine dove Esselunga inietta i veri dati JSON
    urls_da_scandagliare = [
        "https://www.esselunga.it/it-it/promozioni/offerte.html",
        "https://spesaonline.esselunga.it/store/promozioni",
        "https://spesaonline.esselunga.it/commerce/nav/supermercato?filtri=promozioni"
    ]

    for url in urls_da_scandagliare:
        print(f"\n📍 Download codice profondo da: {url}")
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200:
                html = resp.text
                
                # Trucco: Estrarre i dati "nascosti" di Next.js che popolano le pagine web
                matches = re.findall(r'<script[^>]*>(.*?)</script>', html, re.IGNORECASE | re.DOTALL)
                for script_content in matches:
                    if '"price"' in script_content.lower() or '"discountedprice"' in script_content.lower():
                        try:
                            # Cerchiamo blocchi JSON all'interno del JavaScript
                            start = script_content.find('{')
                            end = script_content.rfind('}') + 1
                            if start != -1 and end != 0:
                                data = json.loads(script_content[start:end])
                                extract_from_json(data)
                        except:
                            pass
            else:
                print(f"⚠️ Errore {resp.status_code} dal server Esselunga.")
        except Exception as e:
            print(f"⚠️ Impossibile raggiungere l'URL: {e}")

    # ==========================================
    # FORMATTAZIONE E INVIO A SUPABASE
    # ==========================================
    records = []
    for item in prodotti_estratti.values():
        raw = item["raw"]
        prezzo_originale = raw.get('listPrice', raw.get('oldPrice', raw.get('originalPrice')))
        
        p_orig = None
        if prezzo_originale:
            try:
                p_orig = float(str(prezzo_originale).replace(',', '.').replace('€', '').strip())
                if p_orig <= item["prezzo"]: p_orig = None
            except: pass

        img_url = "https://via.placeholder.com/150"
        for k, v in raw.items():
            if "image" in k.lower() and isinstance(v, str) and "http" in v:
                img_url = v
                break

        date_match = re.search(r'dal (\d{2}/\d{2}/\d{4})\s*al\s*(\d{2}/\d{2}/\d{4})', json.dumps(raw).lower())
        data_inizio = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
        data_fine = date_match.group(2) if date_match else "N/D"
        
        records.append({
            "id": str(uuid.uuid4())[:8],
            "nome": item["nome"],
            "prezzo_scontato": f"{item['prezzo']:.2f}",
            "prezzo_originale": f"{p_orig:.2f}" if p_orig else None,
            "immagine_url": img_url,
            "categoria": "Esselunga",
            "data_inizio": data_inizio,
            "data_fine": data_fine,
            "richiede_tessera": item["loyalty"],
            "dati_grezzi_completi": raw,
            "fonte": "sito API",
            "volantino_nome": item["volantino"]
        })

    print(f"\n🌐 Inizio invio di {len(records)} prodotti a Supabase...")
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    if len(records) > 0:
        try:
            url_delete = f"{SUPABASE_URL}/rest/v1/prodotti?id=not.is.null"
            req_del = urllib.request.Request(url_delete, headers=headers, method='DELETE')
            with urllib.request.urlopen(req_del) as response:
                print("🧹 Vecchio Database Pulito.")
        except: pass

        chunk_size = 500
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i+chunk_size]
            url_insert = f"{SUPABASE_URL}/rest/v1/prodotti"
            req_ins = urllib.request.Request(url_insert, data=json.dumps(chunk).encode('utf-8'), headers=headers, method='POST')
            try:
                with urllib.request.urlopen(req_ins) as response:
                    print(f"✅ Inseriti {len(chunk)} prodotti con successo!")
            except Exception as e:
                print(f"❌ Errore inserimento: {e}")
    else:
        print("⚠️ Nessun prodotto trovato, il database NON è stato cancellato per sicurezza.")
            
    print("🎯 PROCESSO COMPLETATO TOTALMENTE!")

if __name__ == "__main__":
    run_scraper()
