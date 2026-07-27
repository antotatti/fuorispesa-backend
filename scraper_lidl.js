import asyncio
from playwright.async_api import async_playwright
import json
import uuid
import re
from datetime import datetime

def pulisci_prezzo(testo):
    if not testo: return None
    numeri = re.findall(r'\d+[.,]\d+', str(testo).replace(',', '.'))
    return numeri[0] if numeri else None

async def scrape_lidl_definitivo():
    print("\n" + "="*50)
    print(" 🕷️ SPIDER LIDL v3.0 - MODALITÀ FORZATA 🕷️")
    print("="*50)
    
    prodotti_estratti = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        try:
            print("➡️ Accesso diretto alla pagina volantini/offerte Lidl...")
            # Puntiamo direttamente alla sezione volantino/offerte che cambia meno frequentemente
            await page.goto("https://www.lidl.it/it/volantini", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)

            try:
                await page.locator("button:has-text('Accetta'), button:has-text('Tutti')").first.click(timeout=3000)
            except:
                pass

            # Scroll profondo per caricare tutto
            for _ in range(6):
                await page.evaluate("window.scrollBy(0, 1000);")
                await asyncio.sleep(1.5)

            # Raccogliamo qualsiasi blocco che assomigli a una card o a un elemento di volantino
            elementi = await page.locator("article, div[class*='product'], div[class*='flyer'], a[href*='offerte']").all()
            print(elementi)
            print(f"🎯 Analisi di {len(elementi)} elementi trovati...")

            for el in elementi:
                try:
                    testo = await el.inner_text()
                    if "€" not in testo: continue

                    # Cerchiamo un nome plausibile prendendo la prima riga sensata
                    righe = [r.strip() for r in testo.split('\n') if len(r.strip()) > 4]
                    if not righe: continue
                    nome = righe[0]

                    if "€" in nome or len(nome) < 3: continue

                    prezzo = pulisci_prezzo(testo)
                    if not prezzo: continue

                    # Immagine di fallback sicura se non trovata
                    immagine_url = "https://via.placeholder.com/150"
                    imgs = await el.locator("img").all()
                    for img in imgs:
                        src = await img.get_attribute("src") or await img.get_attribute("data-src") or ""
                        if src and "data:image" not in src.lower() and "http" in src:
                            immagine_url = src
                            break

                    prodotto = {
                        "id": str(uuid.uuid4())[:8],
                        "nome": nome[:60],
                        "descrizione": "Offerta Lidl",
                        "prezzo_scontato": prezzo,
                        "prezzo_originale": None,
                        "prezzo_unita_misura": "",
                        "immagine_url": immagine_url,
                        "categoria": "Dispensa",
                        "percentuale_sconto": "0%",
                        "data_inizio": datetime.now().strftime("%Y-%m-%d"),
                        "data_fine": "N/D",
                        "negozio": "Lidl"
                    }
                    prodotti_estratti.append(prodotto)
                except:
                    continue

        except Exception as e:
            print(f"❌ Errore critico Lidl: {e}")

        await browser.close()

    # Rimuoviamo i duplicati
    prodotti_unici = []
    visti = set()
    for p in prodotti_estratti:
        chiave = f"{p['nome']}_{p['prezzo_scontato']}"
        if chiave not in visti:
            visti.add(chiave)
            prodotti_unici.append(p)

    # Se per qualche motivo la pagina web fa i capricci, inseriamo almeno un prodotto reale di test 
    # per evitare il JSON vuoto che blocca l'app, ma marchiamolo chiaramente.
    if not prodotti_unici:
        prodotti_unici.append({
            "id": "lidl_fallback",
            "nome": "Offerte Settimanali Lidl (Verifica Volantino)",
            "descrizione": "Aggiornamento in corso",
            "prezzo_scontato": "0.00",
            "prezzo_originale": None,
            "prezzo_unita_misura": "",
            "immagine_url": "https://via.placeholder.com/150",
            "categoria": "Dispensa",
            "percentuale_sconto": "0%",
            "data_inizio": datetime.now().strftime("%Y-%m-%d"),
            "data_fine": "N/D",
            "negozio": "Lidl"
        })

    dati_finali = {
        "volantino": {
            "data_inizio": datetime.now().strftime("%Y-%m-%d"),
            "data_fine": "N/D",
            "titolo": "Offerte Lidl"
        },
        "prodotti": prodotti_unici
    }

    with open('lidl_offerte.json', 'w', encoding='utf-8') as f:
        json.dump(dati_finali, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Salvati {len(prodotti_unici)} prodotti Lidl.")

if __name__ == "__main__":
    asyncio.run(scrape_lidl_definitivo())
