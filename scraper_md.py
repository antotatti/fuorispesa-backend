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

async def scrape_md():
    print("\n" + "="*50)
    print(" 🛒 SPIDER MD - INIZIO ESTRAZIONE 🛒")
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
            print("➡️ Navigazione verso le offerte MD...")
            # MD Web Store / Offerte
            await page.goto("https://www.mdwebstore.it/offerte", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")

            # Click sui cookie se presente
            try:
                await page.locator("button:has-text('Accetta'), .cookie-accept").first.click(timeout=3000)
            except:
                pass

            # Infinite Scroll: MD carica i prodotti man mano che si scende
            print("🔄 Forzo il caricamento dei prodotti...")
            for _ in range(8):
                await page.evaluate("window.scrollBy(0, 1000);")
                await asyncio.sleep(1.5)

            # Estrazione dei box prodotto
            articoli = await page.locator("article, .product-item, [class*='product-card']").all()
            print(f"🎯 Trovate {len(articoli)} potenziali offerte.")

            for art in articoli:
                try:
                    testo_intero = await art.inner_text()
                    if "€" not in testo_intero: continue

                    # 1. NOME
                    el_titolo = art.locator("h3, h2, .product-name, [class*='title']")
                    if await el_titolo.count() > 0:
                        nome = await el_titolo.first.inner_text()
                    else:
                        righe = [r.strip() for r in testo_intero.split('\n') if len(r.strip()) > 3]
                        nome = righe[0] if righe else "Prodotto Sconosciuto"
                        
                    nome = nome.strip()
                    if not nome or "€" in nome: continue

                    # 2. PREZZI
                    el_prezzo = art.locator(".special-price, .price, [class*='current-price'], strong:has-text('€')")
                    prezzo_scontato = "N/D"
                    if await el_prezzo.count() > 0:
                        prezzo_scontato = pulisci_prezzo(await el_prezzo.first.inner_text())

                    if not prezzo_scontato or prezzo_scontato == "N/D": continue

                    el_vecchio = art.locator(".old-price, strike, s, [class*='regular-price']")
                    prezzo_originale = None
                    if await el_vecchio.count() > 0:
                        prezzo_originale = pulisci_prezzo(await el_vecchio.first.inner_text())

                    # 3. IMMAGINI (Lazy loading bypass)
                    immagini = await art.locator("img").all()
                    immagine_url = "N/D"
                    for img in immagini:
                        src = await img.get_attribute("src") or ""
                        data_src = await img.get_attribute("data-src") or ""
                        img_vera = data_src if data_src else src
                        img_lower = img_vera.lower()
                        
                        if img_vera and "data:image" not in img_lower and "badge" not in img_lower and "logo" not in img_lower:
                            immagine_url = img_vera
                            break

                    # 4. SCONTO
                    percentuale_sconto = "0"
                    match = re.search(r'(\d+)%', testo_intero)
                    if match:
                        percentuale_sconto = f"-{match.group(1)}%"

                    prodotto = {
                        "id": str(uuid.uuid4())[:8],
                        "nome": nome[:60],
                        "descrizione": "",
                        "prezzo_scontato": prezzo_scontato,
                        "prezzo_originale": prezzo_originale,
                        "prezzo_unita_misura": "",
                        "immagine_url": immagine_url,
                        "categoria": "🍔 Cibo e Bevande", 
                        "percentuale_sconto": percentuale_sconto,
                        "data_inizio": datetime.now().strftime("%Y-%m-%d"),
                        "data_fine": "N/D",
                        "negozio": "MD"
                    }
                    
                    prodotti_estratti.append(prodotto)

                except Exception:
                    continue

        except Exception as e:
            print(f"❌ Errore bloccante su MD: {e}")

        await browser.close()

    # Salvataggio sicuro e rimozione duplicati
    prodotti_unici = []
    nomi_visti = set()
    for p in prodotti_estratti:
        chiave = f"{p['nome']}_{p['prezzo_scontato']}"
        if chiave not in nomi_visti:
            nomi_visti.add(chiave)
            prodotti_unici.append(p)

    if len(prodotti_unici) > 0:
        dati_finali = {
            "volantino": {
                "data_inizio": datetime.now().strftime("%Y-%m-%d"),
                "data_fine": "N/D",
                "titolo": "Offerte MD"
            },
            "prodotti": prodotti_unici
        }
        with open('md_offerte.json', 'w', encoding='utf-8') as f:
            json.dump(dati_finali, f, indent=4, ensure_ascii=False)
        print(f"\n✅ SPIDER MD COMPLETATO! Salvate {len(prodotti_unici)} offerte.")
    else:
        print("\n⚠️ Nessun prodotto MD trovato.")

if __name__ == "__main__":
    asyncio.run(scrape_md())
