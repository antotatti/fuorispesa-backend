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

async def scrape_esselunga():
    print("\n" + "="*50)
    print(" 🛒 SPIDER ESSELUNGA - FASE 3 (STEALTH) 🛒")
    print("="*50)
    
    prodotti_estratti = []

    async with async_playwright() as p:
        # Usiamo parametri avanzati per sembrare un vero browser
        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="it-IT"
        )
        page = await context.new_page()

        try:
            print("➡️ Navigazione stealth verso Esselunga...")
            await page.goto("https://www.esselungaacasa.it/", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)

            # 1. Chiusura Cookie
            try:
                await page.locator("button:has-text('Accetta'), #onetrust-accept-btn-handler").first.click(timeout=3000)
                await asyncio.sleep(1)
            except:
                pass

            # 2. Aggiramento Blocco CAP (Digitazione lenta umana)
            input_cap = page.locator("input[placeholder*='CAP'], input[placeholder*='indirizzo'], input[name*='address']")
            if await input_cap.count() > 0:
                print("🔓 Richiesta CAP rilevata. Inserimento in corso...")
                await input_cap.first.click()
                await input_cap.first.type("20124", delay=200) # Digita lentamente come un umano
                await asyncio.sleep(1)
                await page.keyboard.press("Enter")
                await asyncio.sleep(4)
                
                # Se c'è un bottone "Conferma" o "Scegli"
                try:
                    await page.locator("button:has-text('Conferma'), button:has-text('Inizia la spesa')").first.click(timeout=3000)
                except:
                    pass

            # 3. Salto diretto alle Offerte
            await page.goto("https://www.esselungaacasa.it/ecommerce/nav/offerte.html", timeout=60000)
            await asyncio.sleep(3)

            # Scroll lento
            for _ in range(8):
                await page.evaluate("window.scrollBy(0, 600);")
                await asyncio.sleep(1.5)

            articoli = await page.locator("article, .product-grid-item, [class*='product-card']").all()
            print(f"🎯 Trovate {len(articoli)} potenziali offerte.")

            for art in articoli:
                try:
                    testo = await art.inner_text()
                    if "€" not in testo: continue

                    # Titolo
                    el_titolo = art.locator("h3, [class*='title'], [class*='name']")
                    nome = await el_titolo.first.inner_text() if await el_titolo.count() > 0 else testo.split('\n')[0]
                    if not nome or "€" in nome: continue

                    # Prezzi
                    el_prezzo = art.locator(".price, [class*='current'], strong:has-text('€')")
                    prezzo_scontato = pulisci_prezzo(await el_prezzo.first.inner_text()) if await el_prezzo.count() > 0 else "N/D"
                    if prezzo_scontato == "N/D": continue

                    el_vecchio = art.locator("s, strike, .old-price, [class*='original']")
                    prezzo_originale = pulisci_prezzo(await el_vecchio.first.inner_text()) if await el_vecchio.count() > 0 else None

                    # Immagine
                    immagine_url = "N/D"
                    immagini = await art.locator("img").all()
                    for img in immagini:
                        src = await img.get_attribute("src") or ""
                        if src and "data:image" not in src.lower() and "badge" not in src.lower():
                            immagine_url = src
                            break

                    # Percentuale e Fidaty
                    percentuale_sconto = "0"
                    match = re.search(r'(\d+)%', testo)
                    if match: percentuale_sconto = f"-{match.group(1)}%"

                    descrizione = "Plus" if "Fìdaty" in testo or "Fidaty" in testo else ""

                    prodotto = {
                        "id": str(uuid.uuid4())[:8],
                        "nome": nome.strip()[:60],
                        "descrizione": descrizione,
                        "prezzo_scontato": prezzo_scontato,
                        "prezzo_originale": prezzo_originale,
                        "prezzo_unita_misura": "",
                        "immagine_url": immagine_url,
                        "categoria": "🍔 Cibo e Bevande", 
                        "percentuale_sconto": percentuale_sconto,
                        "data_inizio": datetime.now().strftime("%Y-%m-%d"),
                        "data_fine": "N/D",
                        "negozio": "Esselunga"
                    }
                    prodotti_estratti.append(prodotto)

                except Exception:
                    continue

        except Exception as e:
            print(f"❌ Errore bloccante su Esselunga: {e}")

        await browser.close()

    # Salvataggio
    prodotti_unici = []
    nomi_visti = set()
    for p in prodotti_estratti:
        chiave = f"{p['nome']}_{p['prezzo_scontato']}"
        if chiave not in nomi_visti:
            nomi_visti.add(chiave)
            prodotti_unici.append(p)

    if len(prodotti_unici) > 0:
        dati_finali = {
            "volantino": {"data_inizio": datetime.now().strftime("%Y-%m-%d"), "data_fine": "N/D", "titolo": "Offerte Esselunga"},
            "prodotti": prodotti_unici
        }
        with open('esselunga_offerte.json', 'w', encoding='utf-8') as f:
            json.dump(dati_finali, f, indent=4, ensure_ascii=False)
        print(f"\n✅ ESSELUNGA COMPLETATA: {len(prodotti_unici)} offerte violate e salvate.")
    else:
        print("\n⚠️ Esselunga ha respinto l'attacco. Nessun prodotto trovato.")

if __name__ == "__main__":
    asyncio.run(scrape_esselunga())
