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

async def scrape_conad():
    print("\n" + "="*50)
    print(" 🛒 SPIDER CONAD - FASE 3 (STEALTH) 🛒")
    print("="*50)
    
    prodotti_estratti = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        try:
            print("➡️ Navigazione verso Conad Spesa Online...")
            await page.goto("https://spesaonline.conad.it/", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)

            # Cookie
            try:
                await page.locator("button:has-text('Accetta'), button#onetrust-accept-btn-handler").first.click(timeout=3000)
            except:
                pass

            # Aggiramento Selettore Negozio
            input_citta = page.locator("input[placeholder*='indirizzo'], input[placeholder*='Città']")
            if await input_citta.count() > 0:
                print("🔓 Selettore negozio rilevato. Forzatura in corso...")
                await input_citta.first.type("Milano", delay=150)
                await asyncio.sleep(2)
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)
                # Clicca il primo negozio della lista
                try:
                    await page.locator("button:has-text('Scegli'), [class*='store-select']").first.click(timeout=3000)
                except:
                    pass

            # Salto alle Offerte
            await page.goto("https://spesaonline.conad.it/offerte", timeout=60000)
            await asyncio.sleep(4)

            # Scroll
            for _ in range(8):
                await page.evaluate("window.scrollBy(0, 700);")
                await asyncio.sleep(1.5)

            articoli = await page.locator("article, [class*='product-card'], [class*='ItemCard']").all()
            print(f"🎯 Trovate {len(articoli)} potenziali offerte.")

            for art in articoli:
                try:
                    testo = await art.inner_text()
                    if "€" not in testo: continue

                    el_titolo = art.locator("h3, [class*='Title'], [class*='name']")
                    nome = await el_titolo.first.inner_text() if await el_titolo.count() > 0 else testo.split('\n')[0]
                    if not nome or "€" in nome: continue

                    el_prezzo = art.locator("[class*='Price'], strong:has-text('€'), .current-price")
                    prezzo_scontato = pulisci_prezzo(await el_prezzo.first.inner_text()) if await el_prezzo.count() > 0 else "N/D"
                    if prezzo_scontato == "N/D": continue

                    el_vecchio = art.locator("s, strike, [class*='OldPrice']")
                    prezzo_originale = pulisci_prezzo(await el_vecchio.first.inner_text()) if await el_vecchio.count() > 0 else None

                    immagine_url = "N/D"
                    immagini = await art.locator("img").all()
                    for img in immagini:
                        src = await img.get_attribute("src") or ""
                        if src and "data:image" not in src.lower() and "badge" not in src.lower():
                            immagine_url = src
                            break

                    percentuale_sconto = "0"
                    match = re.search(r'(\d+)%', testo)
                    if match: percentuale_sconto = f"-{match.group(1)}%"

                    descrizione = "Plus" if "Carta Insieme" in testo or "Conad Card" in testo else ""

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
                        "negozio": "Conad"
                    }
                    prodotti_estratti.append(prodotto)

                except Exception:
                    continue

        except Exception as e:
            print(f"❌ Errore bloccante su Conad: {e}")

        await browser.close()

    prodotti_unici = []
    nomi_visti = set()
    for p in prodotti_estratti:
        chiave = f"{p['nome']}_{p['prezzo_scontato']}"
        if chiave not in nomi_visti:
            nomi_visti.add(chiave)
            prodotti_unici.append(p)

    if len(prodotti_unici) > 0:
        dati_finali = {
            "volantino": {"data_inizio": datetime.now().strftime("%Y-%m-%d"), "data_fine": "N/D", "titolo": "Offerte Conad"},
            "prodotti": prodotti_unici
        }
        with open('conad_offerte.json', 'w', encoding='utf-8') as f:
            json.dump(dati_finali, f, indent=4, ensure_ascii=False)
        print(f"\n✅ CONAD COMPLETATA: {len(prodotti_unici)} offerte estratte dal database.")
    else:
        print("\n⚠️ Conad ha respinto l'attacco. Nessun prodotto trovato.")

if __name__ == "__main__":
    asyncio.run(scrape_conad())
