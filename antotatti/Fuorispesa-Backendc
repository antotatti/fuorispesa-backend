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

async def scrape_eurospin():
    print("\n" + "="*50)
    print(" 🛒 SPIDER EUROSPIN - INIZIO ESTRAZIONE 🛒")
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
            print("➡️ Navigazione verso la pagina volantino Eurospin...")
            await page.goto("https://www.eurospin.it/offerte/", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")

            # Cerca di chiudere eventuali popup dei cookie
            try:
                await page.locator("button:has-text('Accetta'), button:has-text('Accetto')").first.click(timeout=3000)
            except:
                pass

            # Scroll lento per ingannare il lazy loading delle immagini
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, 800);")
                await asyncio.sleep(1)

            # Seleziona le card dei prodotti (adatteremo i selettori se il sito cambia)
            articoli = await page.locator(".product-item-info, article").all()
            print(f"🎯 Trovate {len(articoli)} potenziali offerte in pagina.")

            for art in articoli:
                try:
                    testo = await art.inner_text()
                    if "€" not in testo: continue

                    # 1. Nome prodotto
                    nome_el = art.locator(".product-item-link, .name")
                    if await nome_el.count() > 0:
                        nome = await nome_el.first.inner_text()
                    else:
                        righe = [r.strip() for r in testo.split('\n') if len(r.strip()) > 2]
                        nome = righe[0] if righe else "Prodotto"

                    # 2. Prezzo Nuovo e Vecchio
                    prezzo_scontato = "N/D"
                    el_prezzo = art.locator(".special-price, .price")
                    if await el_prezzo.count() > 0:
                        prezzo_scontato = pulisci_prezzo(await el_prezzo.first.inner_text())

                    prezzo_originale = None
                    el_vecchio = art.locator(".old-price, strike")
                    if await el_vecchio.count() > 0:
                        prezzo_originale = pulisci_prezzo(await el_vecchio.first.inner_text())

                    # 3. Immagine
                    immagini = await art.locator("img").all()
                    immagine_url = "N/D"
                    for img in immagini:
                        src = await img.get_attribute("src") or ""
                        if src and "logo" not in src.lower() and "badge" not in src.lower():
                            immagine_url = src
                            break

                    # Struttura Dati Speculare a Lidl
                    prodotto = {
                        "id": str(uuid.uuid4())[:8],
                        "nome": nome.strip()[:60],
                        "descrizione": "",
                        "prezzo_scontato": prezzo_scontato or "N/D",
                        "prezzo_originale": prezzo_originale,
                        "prezzo_unita_misura": "",
                        "immagine_url": immagine_url,
                        "categoria": "🍔 Cibo e Bevande", # Eurospin è al 95% alimentare
                        "percentuale_sconto": "0",
                        "data_inizio": datetime.now().strftime("%Y-%m-%d"),
                        "data_fine": "N/D",
                        "negozio": "Eurospin"
                    }

                    if prodotto['prezzo_scontato'] != "N/D":
                        prodotti_estratti.append(prodotto)

                except Exception as e:
                    continue

        except Exception as e:
            print(f"❌ Errore bloccante: {e}")

        await browser.close()

    # Rimuovi duplicati
    prodotti_unici = []
    nomi_visti = set()
    for p in prodotti_estratti:
        if p['nome'] not in nomi_visti:
            nomi_visti.add(p['nome'])
            prodotti_unici.append(p)

    # Salvataggio su file separato
    if len(prodotti_unici) > 0:
        dati_finali = {
            "volantino": {
                "data_inizio": datetime.now().strftime("%Y-%m-%d"),
                "data_fine": "N/D",
                "titolo": "Offerte Eurospin"
            },
            "prodotti": prodotti_unici
        }
        with open('eurospin_offerte.json', 'w', encoding='utf-8') as f:
            json.dump(dati_finali, f, indent=4, ensure_ascii=False)
        print(f"\n✅ SPIDER EUROSPIN COMPLETATO! Salvate {len(prodotti_unici)} offerte.")
    else:
        print("\n⚠️ Nessun prodotto trovato. Nessun file salvato.")

if __name__ == "__main__":
    asyncio.run(scrape_eurospin())
