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

async def scrape_lidl_completamente_automatico():
    print("\n" + "="*50)
    print(" 🕷️ SPIDER LIDL v2.0 - PRECISIONE LASER 🕷️")
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
            await page.goto("https://www.lidl.it/", timeout=60000)
            try:
                await page.locator("button:has-text('Accetta'), button:has-text('Tutti')").first.click(timeout=3000)
            except:
                pass

            # Estrazione URLCategorie
            links_estratti = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a'))
                            .map(a => a.href)
                            .filter(href => href.includes('lidl.it/c/') && !href.includes('newsletter'));
            }''')
            urls_da_scansionare = list(set(links_estratti))
            
        except Exception as e:
            print(f"❌ Errore in fase di scoperta: {e}")
            await browser.close()
            return

        for url in urls_da_scansionare:
            categoria_estratta = "Altro"
            if "/c/" in url:
                categoria_estratta = url.split('/c/')[1].split('/')[0].replace('-', ' ').title()

            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("domcontentloaded")
                
                # Scroll lento per forzare il caricamento delle immagini vere
                for _ in range(5):
                    await page.evaluate("window.scrollBy(0, 1000);")
                    await asyncio.sleep(1)

                articoli = await page.locator("article, div[class*='product-grid'], a[data-qa='product-card']").all()
                
                for art in articoli:
                    try:
                        # 1. TITOLO PRECISO: Cerchiamo specificamente gli header, evitiamo testi a caso
                        titolo_el = art.locator('h3, h2, [class*="headline"], [class*="title"]')
                        if await titolo_el.count() == 0: continue
                        nome = await titolo_el.first.inner_text()
                        nome = nome.strip()
                        
                        # Filtro anti-sporco: se il titolo è vuoto, è un numero o contiene €, saltiamo
                        if not nome or "€" in nome or len(nome) < 3: 
                            continue

                        testo_intero = await art.inner_text()

                        # 2. IMMAGINE REALE (No spazi bianchi o loghi)
                        immagini = await art.locator("img").all()
                        immagine_url = "N/D"
                        for img in immagini:
                            src = await img.get_attribute("src") or ""
                            data_src = await img.get_attribute("data-src") or ""
                            
                            # Il lazy loading di Lidl mette l'immagine vera nel data-src
                            img_vera = data_src if data_src else src
                            img_lower = img_vera.lower()
                            
                            # Escludiamo le immagini finte (base64) e i badge
                            if img_vera and "data:image" not in img_lower and "transparent" not in img_lower and "badge" not in img_lower:
                                immagine_url = img_vera
                                break 

                        # 3. PREZZI ESATTI
                        el_prezzo = art.locator('[class*="price-pill__price"], [class*="current-price"], .m-price__price, strong:has-text("€")')
                        prezzo_scontato = "N/D"
                        if await el_prezzo.count() > 0:
                            prezzo_scontato = pulisci_prezzo(await el_prezzo.first.inner_text())
                            
                        if not prezzo_scontato or prezzo_scontato == "N/D":
                            continue # Senza prezzo finale non è un'offerta valida

                        el_vecchio = art.locator('s, strike, [class*="old-price"], .m-price__price--small')
                        prezzo_originale = None
                        if await el_vecchio.count() > 0:
                            prezzo_originale = pulisci_prezzo(await el_vecchio.first.inner_text())

                        # 4. UNITA DI MISURA
                        el_unita = art.locator("[class*='price-base'], .m-price__base")
                        unita_misura = ""
                        if await el_unita.count() > 0:
                            unita_misura = (await el_unita.first.inner_text()).replace('\n', ' ').strip()

                        # 5. SCONTO PERCENTUALE E TESSERA (Fondamentali per i Badge React Native)
                        percentuale_sconto = "0"
                        el_perc = art.locator('.m-price__label, [class*="discount"]')
                        if await el_perc.count() > 0:
                            txt_perc = await el_perc.first.inner_text()
                            match = re.search(r'(\d+)%', txt_perc)
                            if match:
                                percentuale_sconto = f"-{match.group(1)}%"
                        elif "%" in testo_intero:
                            match = re.search(r'(\d+)%', testo_intero)
                            if match:
                                percentuale_sconto = f"-{match.group(1)}%"

                        # Innesco del Badge "Con Tessera" per la tua App
                        descrizione = ""
                        if "Lidl Plus" in testo_intero or "plus" in testo_intero.lower():
                            descrizione = "Plus" # Questa parola accende il badge blu nell'App

                        # 6. DATE (Per il Badge "In Arrivo")
                        data_inizio = datetime.now().strftime("%Y-%m-%d")
                        data_fine = "N/D"
                        if "Dal " in testo_intero and " al " in testo_intero:
                            try:
                                date_str = re.search(r'Dal (\d{2}/\d{2}) al (\d{2}/\d{2})', testo_intero)
                                if date_str:
                                    anno = datetime.now().strftime("%Y")
                                    data_inizio = f"{anno}-{date_str.group(1).split('/')[1]}-{date_str.group(1).split('/')[0]}"
                                    data_fine = f"{anno}-{date_str.group(2).split('/')[1]}-{date_str.group(2).split('/')[0]}"
                            except:
                                pass

                        prodotto = {
                            "id": str(uuid.uuid4())[:8],
                            "nome": nome[:60],
                            "descrizione": descrizione,
                            "prezzo_scontato": prezzo_scontato,
                            "prezzo_originale": prezzo_originale,
                            "prezzo_unita_misura": unita_misura,
                            "immagine_url": immagine_url,
                            "categoria": categoria_estratta,
                            "percentuale_sconto": percentuale_sconto,
                            "data_inizio": data_inizio,
                            "data_fine": data_fine,
                            "negozio": "Lidl"
                        }
                        prodotti_estratti.append(prodotto)

                    except Exception:
                        continue
            except Exception:
                continue

        await browser.close()

    # Filtro duplicati stringente
    prodotti_unici = []
    nomi_visti = set()
    for p in prodotti_estratti:
        chiave_univoca = f"{p['nome']}_{p['prezzo_scontato']}"
        if chiave_univoca not in nomi_visti and p['immagine_url'] != "N/D":
            nomi_visti.add(chiave_univoca)
            prodotti_unici.append(p)

    dati_finali = {
        "volantino": {
            "data_inizio": datetime.now().strftime("%Y-%m-%d"),
            "data_fine": "N/D",
            "titolo": "Tutte le Offerte Lidl"
        },
        "prodotti": prodotti_unici
    }

    with open('lidl_offerte.json', 'w', encoding='utf-8') as f:
        json.dump(dati_finali, f, indent=4, ensure_ascii=False)
    print(f"\n✅ SPIDER COMPLETATO! Trovate {len(prodotti_unici)} offerte pulite.")

if __name__ == "__main__":
    asyncio.run(scrape_lidl_completamente_automatico())
