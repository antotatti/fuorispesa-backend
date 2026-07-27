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
    print(" 🕷️ SPIDER AVANZATO LIDL - PRECISIONE MASSIMA 🕷️")
    print("="*50)
    
    prodotti_estratti = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        print("🔍 FASE 1: Ricerca delle categorie URL...")
        try:
            await page.goto("https://www.lidl.it/", timeout=60000)
            try:
                await page.locator("button:has-text('Accetta'), button:has-text('Tutti')").first.click(timeout=3000)
            except:
                pass
            await page.wait_for_load_state("networkidle")

            links_estratti = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a'))
                            .map(a => a.href)
                            .filter(href => href.includes('lidl.it/c/') && !href.includes('newsletter') && !href.includes('servizio-clienti'));
            }''')
            
            urls_da_scansionare = list(set(links_estratti))
            print(f"🎯 Trovate {len(urls_da_scansionare)} categorie! Inizio estrazione...\n")
            
        except Exception as e:
            print(f"❌ Errore in fase di scoperta: {e}")
            await browser.close()
            return

        for url in urls_da_scansionare:
            # ESTRAZIONE CATEGORIA PURA DALL'URL
            categoria_estratta = "Altro"
            if "/c/" in url:
                pezzo_url = url.split('/c/')[1].split('/')[0]
                categoria_estratta = pezzo_url.replace('-', ' ').title()

            print(f"➡️ Analizzo: {categoria_estratta} ...")
            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("domcontentloaded")
                
                for _ in range(4):
                    await page.evaluate("window.scrollBy(0, 1000);")
                    await asyncio.sleep(1)

                articoli = await page.locator("article, div[class*='product-grid'], a[data-qa='product-card']").all()
                
                for art in articoli:
                    try:
                        testo = await art.inner_text()
                        if "€" not in testo: continue

                        righe = [r.strip() for r in testo.split('\n') if len(r.strip()) > 3]
                        nome = righe[0] if righe else "Prodotto Sconosciuto"

                        # FIX IMMAGINI: Filtro anti-badge e anti-banco frigo
                        immagini = await art.locator("img").all()
                        immagine_url = "N/D"
                        for img in immagini:
                            src = await img.get_attribute("src") or ""
                            src_lower = src.lower()
                            if src and "badge" not in src_lower and "icon" not in src_lower and "ribbon" not in src_lower and "banco" not in src_lower:
                                immagine_url = src
                                break 

                        # FIX PREZZI: Prezzo Barrato (Vecchio) e Nuovo
                        el_prezzo_vecchio = art.locator("s, strike, [class*='old-price'], .m-price__price--small")
                        prezzo_originale = None
                        if await el_prezzo_vecchio.count() > 0:
                            prezzo_originale = pulisci_prezzo(await el_prezzo_vecchio.first.inner_text())

                        el_prezzo_nuovo = art.locator("[class*='price-pill__price'], [class*='current-price'], strong:has-text('€'), .m-price__price")
                        prezzo_scontato = "N/D"
                        if await el_prezzo_nuovo.count() > 0:
                            prezzo_scontato = pulisci_prezzo(await el_prezzo_nuovo.first.inner_text()) or "N/D"
                        
                        # Fallback di sicurezza
                        if prezzo_scontato == "N/D":
                            testo_pulito = testo
                            if prezzo_originale:
                                testo_pulito = testo.replace(str(prezzo_originale), "")
                            prezzo_scontato = pulisci_prezzo(testo_pulito) or "N/D"

                        # FIX UNITA' DI MISURA (es. 1 kg = 0.92 €)
                        el_unita = art.locator("[class*='price-base'], .m-price__base")
                        unita_misura = ""
                        if await el_unita.count() > 0:
                            unita_misura = await el_unita.first.inner_text()
                            unita_misura = unita_misura.replace('\n', ' ').strip()

                        # FIX SCONTI PERCENTUALI
                        percentuale_sconto = "0"
                        if "%" in testo:
                            ricerca_perc = re.search(r'(\d+)%', testo)
                            if ricerca_perc:
                                percentuale_sconto = "-" + ricerca_perc.group(1) + "%"
                        
                        # FIX DATE VOLANTINO
                        data_inizio = datetime.now().strftime("%Y-%m-%d")
                        data_fine = "N/D"
                        if "Dal " in testo and " al " in testo:
                            try:
                                date_str = re.search(r'Dal (\d{2}/\d{2}) al (\d{2}/\d{2})', testo)
                                if date_str:
                                    anno = datetime.now().strftime("%Y")
                                    data_inizio = f"{anno}-{date_str.group(1).split('/')[1]}-{date_str.group(1).split('/')[0]}"
                                    data_fine = f"{anno}-{date_str.group(2).split('/')[1]}-{date_str.group(2).split('/')[0]}"
                            except:
                                pass

                        descrizione = righe[1] if len(righe) > 1 else ""
                        if "Plus" in testo or "plus" in testo.lower() or "-2.00€" in testo:
                            descrizione = "Offerta riservata clienti Lidl Plus. " + descrizione

                        prodotto = {
                            "id": str(uuid.uuid4())[:8],
                            "nome": nome[:60],
                            "descrizione": descrizione[:120],
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

                        if prodotto['prezzo_scontato'] != "N/D":
                            prodotti_estratti.append(prodotto)
                    except:
                        continue
            except Exception as e:
                continue

        await browser.close()

    # Rimuovi i duplicati
    prodotti_unici = []
    nomi_visti = set()
    for p in prodotti_estratti:
        chiave_univoca = f"{p['nome']}_{p['prezzo_scontato']}"
        if chiave_univoca not in nomi_visti:
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

    # SISTEMA SALVAVITA
    if len(prodotti_unici) > 50:
        with open('lidl_offerte.json', 'w', encoding='utf-8') as f:
            json.dump(dati_finali, f, indent=4, ensure_ascii=False)
        print("\n✅ SPIDER COMPLETATO! File aggiornato con successo.")
    else:
        print("\n⚠️ ALLARME: Trovate poche offerte. Non sovrascrivo nulla.")

if __name__ == "__main__":
    asyncio.run(scrape_lidl_completamente_automatico())
