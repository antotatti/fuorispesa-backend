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

async def scrape_coop():
    print("\n" + "="*50)
    print(" 🛒 SPIDER COOP - FASE 2 🛒")
    print("="*50)
    
    prodotti_estratti = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        try:
            print("➡️ Navigazione verso CoopShop Offerte...")
            await page.goto("https://www.coopshop.it/p/offerte", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")

            try:
                await page.locator("button:has-text('Accetta'), button:has-text('OK')").first.click(timeout=3000)
            except:
                pass

            print("🔄 Scansione griglie Coop...")
            for _ in range(8):
                await page.evaluate("window.scrollBy(0, 800);")
                await asyncio.sleep(1.5)

            articoli = await page.locator("article, .product-card, [class*='product-item']").all()
            print(f"🎯 Trovate {len(articoli)} potenziali offerte.")

            for art in articoli:
                try:
                    testo = await art.inner_text()
                    if "€" not in testo: continue

                    el_titolo = art.locator(".product-title, h3, [class*='name']")
                    nome = await el_titolo.first.inner_text() if await el_titolo.count() > 0 else testo.split('\n')[0]
                    if not nome or "€" in nome: continue

                    el_prezzo = art.locator(".price, .current-price, strong:has-text('€')")
                    prezzo_scontato = pulisci_prezzo(await el_prezzo.first.inner_text()) if await el_prezzo.count() > 0 else "N/D"
                    if prezzo_scontato == "N/D": continue

                    el_vecchio = art.locator(".old-price, strike, s")
                    prezzo_originale = pulisci_prezzo(await el_vecchio.first.inner_text()) if await el_vecchio.count() > 0 else None

                    immagine_url = "N/D"
                    immagini = await art.locator("img").all()
                    for img in immagini:
                        src = await img.get_attribute("src") or ""
                        data_src = await img.get_attribute("data-src") or ""
                        img_vera = data_src if data_src else src
                        if img_vera and "data:image" not in img_vera.lower() and "badge" not in img_vera.lower():
                            immagine_url = img_vera
                            break

                    percentuale_sconto = "0"
                    match = re.search(r'(\d+)%', testo)
                    if match: percentuale_sconto = f"-{match.group(1)}%"

                    descrizione = "Plus" if "Socio" in testo or "Coop" in testo.split('\n')[0] else ""

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
                        "negozio": "Coop"
                    }
                    prodotti_estratti.append(prodotto)

                except Exception:
                    continue

        except Exception as e:
            print(f"❌ Errore bloccante: {e}")

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
            "volantino": {"data_inizio": datetime.now().strftime("%Y-%m-%d"), "data_fine": "N/D", "titolo": "Offerte Coop"},
            "prodotti": prodotti_unici
        }
        with open('coop_offerte.json', 'w', encoding='utf-8') as f:
            json.dump(dati_finali, f, indent=4, ensure_ascii=False)
        print(f"\n✅ COOP COMPLETATO: {len(prodotti_unici)} offerte salvate.")
    else:
        print("\n⚠️ Nessun prodotto trovato.")

if __name__ == "__main__":
    asyncio.run(scrape_coop())
