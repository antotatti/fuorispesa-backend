import asyncio
from playwright.async_api import async_playwright
import json
import uuid
from datetime import datetime

# Variabile globale dove salveremo tutti i prodotti intercettati al volo
prodotti_catturati_raw = []

def esplora_json_ricorsivo(dato):
    """
    Funzione INDISTRUTTIBILE: non ci interessa che forma abbia il JSON di Esselunga.
    Questa funzione scava in ogni lista e dizionario della risposta di rete. 
    Se trova un blocco che contiene sia un nome che un prezzo, lo salva.
    """
    if isinstance(dato, dict):
        # Convertiamo tutte le chiavi in minuscolo per trovarle facilmente
        chiavi = {k.lower(): v for k, v in dato.items()}
        
        # Cerchiamo indizi che questo dizionario sia un "Prodotto"
        ha_nome = 'name' in chiavi or 'nome' in chiavi or 'title' in chiavi or 'description' in chiavi
        ha_prezzo = 'price' in chiavi or 'prezzo' in chiavi or 'currentprice' in chiavi or 'prezzoscontato' in chiavi
        
        if ha_nome and ha_prezzo:
            prodotti_catturati_raw.append(dato)
        
        # Continuiamo a scavare nei sotto-livelli
        for valore in dato.values():
            esplora_json_ricorsivo(valore)
            
    elif isinstance(dato, list):
        for item in dato:
            esplora_json_ricorsivo(item)

async def cattura_traffico(response):
    """
    L'intercettatore. Viene richiamato in automatico per OGNI file che il sito scarica in background.
    """
    # Ci interessano solo le chiamate API (xhr o fetch) e non immagini o css
    if response.request.resource_type in ["xhr", "fetch"]:
        if "esselunga" in response.url.lower():
            try:
                # Se è un JSON, lo esploriamo per cercare i prodotti!
                dati = await response.json()
                esplora_json_ricorsivo(dati)
            except:
                pass # Ignoriamo file che non sono JSON validi

async def scrape_esselunga_definitivo():
    print("\n" + "="*50)
    print(" 🛒 SPIDER ESSELUNGA v4.0 - NETWORK INTERCEPTION 🛒")
    print("="*50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Usiamo un User-Agent reale per non sembrare un bot
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        # 🎯 ATTIVIAMO IL RADAR: Diciamo alla pagina di intercettare tutte le risposte
        page.on("response", cattura_traffico)

        try:
            print("➡️ Navigazione verso Esselunga...")
            # Puntiamo direttamente alla pagina delle offerte (o alla home di spesaonline)
            await page.goto("https://spesaonline.esselunga.it/", timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            # 1. BYPASS DEI COOKIE
            try:
                await page.locator("button:has-text('Accetta'), button:has-text('Accept')").first.click(timeout=3000)
                print("🍪 Cookie accettati.")
            except:
                pass

            # 2. BYPASS DEL CAP / STORE LOCATOR (Il vero scudo di Esselunga)
            print("📍 Tentativo di inserimento CAP (Milano - 20124)...")
            try:
                # Cerchiamo input generici per il CAP
                cap_input = page.locator("input[placeholder*='CAP'], input[name*='cap'], input[type='text']").first
                await cap_input.wait_for(state="visible", timeout=5000)
                await cap_input.fill("20124")
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)
                # Clicchiamo eventuali bottoni "Conferma" o "Scegli"
                await page.locator("button:has-text('Scegli'), button:has-text('Conferma')").first.click(timeout=3000)
                print("✅ CAP inserito con successo.")
            except:
                print("⚠️ Nessun popup CAP rilevato, proseguiamo...")

            # 3. SCROLL PROFONDO PER INNESCARE LE API
            print("📜 Simulo il comportamento umano per far scattare le API...")
            # Andiamo su una pagina di categorie/offerte se c'è un link
            try:
                await page.locator("a:has-text('Offerte'), a:has-text('Promozioni')").first.click(timeout=5000)
            except:
                pass
                
            for i in range(8):
                await page.evaluate("window.scrollBy(0, 800);")
                await asyncio.sleep(1.5)

        except Exception as e:
            print(f"❌ Errore durante la navigazione: {e}")

        await browser.close()

    print(f"\n📡 Dati grezzi intercettati dal radar: {len(prodotti_catturati_raw)} blocchi.")

    # ========================================================
    # NORMALIZZAZIONE DEI DATI NEL FORMATO DELLA TUA APP
    # ========================================================
    prodotti_finali = []
    visti = set()

    for raw in prodotti_catturati_raw:
        # Esselunga JSON parser intelligente
        chiavi_basse = {k.lower(): v for k, v in raw.items()}
        
        # Estraiamo il nome
        nome = chiavi_basse.get('name') or chiavi_basse.get('nome') or chiavi_basse.get('title') or chiavi_basse.get('description')
        if not nome or len(str(nome)) < 3: continue
        
        # Estraiamo il prezzo
        prezzo_raw = chiavi_basse.get('price') or chiavi_basse.get('prezzo') or chiavi_basse.get('currentprice') or chiavi_basse.get('prezzoscontato')
        if not prezzo_raw: continue
        
        prezzo_str = str(prezzo_raw).replace(',', '.')
        try:
            prezzo_float = float(''.join(c for c in prezzo_str if c.isdigit() or c == '.'))
            if prezzo_float <= 0: continue
        except:
            continue

        # Estraiamo immagine (cerchiamo chiavi che contengano 'image' o 'img')
        img_url = "https://via.placeholder.com/150"
        for k, v in raw.items():
            if ('image' in k.lower() or 'img' in k.lower() or 'picture' in k.lower()) and isinstance(v, str) and 'http' in v:
                img_url = v
                break

        # Check duplicati
        chiave = f"{nome}_{prezzo_float}"
        if chiave not in visti:
            visti.add(chiave)
            prodotti_finali.append({
                "id": str(uuid.uuid4())[:8],
                "nome": str(nome)[:70],
                "prezzo_scontato": f"{prezzo_float:.2f}",
                "prezzo_originale": None, 
                "prezzo_unita_misura": "",
                "immagine_url": img_url,
                "categoria": "Dispensa", 
                "percentuale_sconto": "In Offerta",
                "data_inizio": datetime.now().strftime("%Y-%m-%d"),
                "data_fine": "N/D",
                "negozio": "Esselunga"
            })

    # ========================================================
    # FALLBACK: PIANO B SE L'INTERCETTAZIONE FALLISCE
    # ========================================================
    if not prodotti_finali:
        print("⚠️ Nessun prodotto intercettato. Attivazione sistema di FALLBACK.")
        prodotti_finali.append({
            "id": "esselunga_fallback",
            "nome": "Volantino Esselunga - In Aggiornamento",
            "prezzo_scontato": "N/D",
            "prezzo_originale": None,
            "prezzo_unita_misura": "Controlla l'app store o il sito ufficiale",
            "immagine_url": "https://via.placeholder.com/150",
            "categoria": "Altro",
            "percentuale_sconto": "0%",
            "data_inizio": datetime.now().strftime("%Y-%m-%d"),
            "data_fine": "N/D",
            "negozio": "Esselunga"
        })

    dati_da_salvare = {
        "volantino": {
            "data_inizio": datetime.now().strftime("%Y-%m-%d"),
            "data_fine": "N/D",
            "titolo": "Offerte Esselunga"
        },
        "prodotti": prodotti_finali
    }

    with open('esselunga_offerte.json', 'w', encoding='utf-8') as f:
        json.dump(dati_da_salvare, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ Salvataggio completato: {len(prodotti_finali)} prodotti Esselunga pronti per l'app!")

if __name__ == "__main__":
    asyncio.run(scrape_esselunga_definitivo())
