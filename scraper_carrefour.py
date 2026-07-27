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

async def scrape_carrefour():
    print("\n" + "="*50)
    print(" 🛒 SPIDER CARREFOUR - FASE 2 🛒")
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
            print("➡️ Navigazione verso Carrefour Offerte...")
            await page.goto("https://www.carrefour.it/spesa-online/offerte/", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")

            # 1. Distruzione del banner Cookie (Essenziale su Carrefour)
            try:
                await page.locator("#onetrust-accept-btn-handler, button:has-text('Accetta')").first.click(timeout=5000)
                await asyncio.sleep(1)
            except:
                pass

            # 2. Scroll umano (Micro-scatti per ingannare il lazy loading)
            print("🔄 Simulazione scroll umano...")
            for _ in range(12):
                await page.evaluate("window.scrollBy(0, 500);")
                await asyncio.sleep(1)

            # 3. Estrazione
            articoli = await page.locator(".product-tile, article, [class*='product-card']").all()
            print(f"🎯 Trovate {len(articoli)} potenziali offerte.")

            for art in articoli:
                try:
                    testo = await art.inner_text()
                    if "€" not in testo: continue

                    # Titolo
                    el_titolo = art.locator(".product-name, [class*='title']")
                    nome = await el_titolo.first.inner_text() if await el_titolo.count() > 0 else testo.split('\n')[0]
                    if not nome or "€" in nome: continue

                    # Prezzi
                    el_prezzo = art.locator(".sales, [class*='current-price'], .price, strong:has-text('€')")
                    prezzo_scontato = pulisci_prezzo(await el_prezzo.first.inner_text()) if await el_prezzo.count() > 0 else "N/D"
                    if prezzo_scontato == "N/D": continue

                    el_vecchio = art.locator(".strike-through, s, strike, [class*='old-price']")
                    prezzo_originale = pulisci_prezzo(await el_vecchio.first.inner_text()) if await el_vecchio.count() > 0 else None

                    # Immagine (Carrefour nasconde le immagini nei tag source a volte)
                    immagine_url = "N/D"
                    immagini = await art.locator("img").all()
                    for img in immagini:
                        src = await img.get_attribute("src") or ""
                        data_src = await img.get_attribute("data-src") or ""
                        img_vera = data_src if data_src else src
                        if img_vera and "data:image" not in img_vera.lower() and "badge" not in img_vera.lower():
                            immagine_url = img_vera
                            break

                    # Percentuale
                    percentuale_sconto = "0"
                    match = re.search(r'(\d+)%', testo)
                    if match: percentuale_sconto = f"-{match.group(1)}%"

                    # Badge "Con Tessera" (SpesAmica su Carrefour)
                    descrizione = "Plus" if "SpesAmica" in testo or "Payback" in testo else ""

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
                        "negozio": "Carrefour"
                    }
                    prodotti_estratti.append(prodotto)

                except Exception:
                    continue

        except Exception as e:
            print(f"❌ Errore bloccante: {e}")

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
            "volantino": {"data_inizio": datetime.now().strftime("%Y-%m-%d"), "data_fine": "N/D", "titolo": "Offerte Carrefour"},
            "prodotti": prodotti_unici
        }
        with open('carrefour_offerte.json', 'w', encoding='utf-8') as f:
            json.dump(dati_finali, f, indent=4, ensure_ascii=False)
        print(f"\n✅ CARREFOUR COMPLETATO: {len(prodotti_unici)} offerte salvate.")
    else:
        print("\n⚠️ Nessun prodotto trovato.")

if __name__ == "__main__":
    asyncio.run(scrape_carrefour())
