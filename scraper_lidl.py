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
    print(" 🕷️ SPIDER AUTOMATICO LIDL - RICERCA GLOBALE 🕷️")
    print("="*50)
    
    prodotti_estratti = []

    async with async_playwright() as p:
        # HEADLESS=TRUE -> Nessuna finestra, lavora in modo invisibile e veloce per i server
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        # FASE 1: AUTO-SCOPERTA DEI LINK DELLE OFFERTE
        print("🔍 FASE 1: Scansione del sito per trovare i volantini e le categorie attive...")
        try:
            await page.goto("https://www.lidl.it/", timeout=60000)
            
            # Gestione Cookie
            try:
                await page.locator("button:has-text('Accetta'), button:has-text('Tutti')").first.click(timeout=3000)
            except:
                pass
            
            await page.wait_for_load_state("networkidle")

            # Tramite un comando Javascript estraiamo tutti i link del sito che portano a categorie ("/c/")
            links_estratti = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a'))
                            .map(a => a.href)
                            .filter(href => href.includes('lidl.it/c/') && !href.includes('newsletter') && !href.includes('servizio-clienti'));
            }''')
            
            # Rimuoviamo i doppioni
            urls_da_scansionare = list(set(links_estratti))
            print(f"🎯 Trovate {len(urls_da_scansionare)} pagine di offerte! Inizio l'estrazione a tappeto...\n")
            
        except Exception as e:
            print(f"❌ Errore durante la fase di scoperta: {e}")
            await browser.close()
            return

        # FASE 2: ESTRAZIONE PRODOTTI DA OGNI SINGOLA PAGINA TROVATA
        for url in urls_da_scansionare:
            print(f"➡️ Analizzo: {url.split('/c/')[1] if '/c/' in url else url} ...")
            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("domcontentloaded")
                
                # Scroll per sbloccare le immagini e i caricamenti dinamici
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

                        img_el = art.locator("img").first
                        immagine_url = await img_el.get_attribute("src") if await img_el.count() > 0 else "N/D"

                        prezzo_scontato = pulisci_prezzo(testo) or "N/D"
                        
                        percentuale_sconto = "0"
                        if "%" in testo:
                            ricerca_perc = re.search(r'(\d+)%', testo)
                            if ricerca_perc:
                                percentuale_sconto = "-" + ricerca_perc.group(1) + "%"
                        
                        descrizione = righe[1] if len(righe) > 1 else ""
                        if "Plus" in testo or "plus" in testo.lower() or "-2.00€" in testo:
                            descrizione = "Offerta riservata clienti Lidl Plus. " + descrizione

                        prodotto = {
                            "id": str(uuid.uuid4())[:8],
                            "nome": nome[:60],
                            "descrizione": descrizione[:120],
                            "prezzo_scontato": prezzo_scontato,
                            "prezzo_originale": None,
                            "prezzo_unita_misura": "",
                            "immagine_url": immagine_url,
                            "categoria": "Offerte Settimanali",
                            "percentuale_sconto": percentuale_sconto,
                            "data_inizio": datetime.now().strftime("%Y-%m-%d"),
                            "data_fine": "N/D",
                            "negozio": "Lidl"
                        }

                        if prodotto['prezzo_scontato'] != "N/D":
                            prodotti_estratti.append(prodotto)
                    except:
                        continue

            except Exception as e:
                print(f"⚠️ Salto la pagina per errore: {str(e)[:50]}")
                continue

        await browser.close()

    # FASE 3: PULIZIA DOPPIONI E SALVATAGGIO
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

    # SISTEMA SALVAVITA: Sovrascrive il file SOLO se ha trovato un numero ragionevole di offerte
    if len(prodotti_unici) > 50:
        with open('lidl_offerte.json', 'w', encoding='utf-8') as f:
            json.dump(dati_finali, f, indent=4, ensure_ascii=False)
        print("\n" + "="*50)
        print(f"✅ SPIDER COMPLETATO! File aggiornato con {len(prodotti_unici)} offerte TOTALI.")
        print("="*50)
    else:
        print("\n" + "="*50)
        print(f"⚠️ ALLARME: Trovate solo {len(prodotti_unici)} offerte.")
        print("Il file JSON NON è stato sovrascritto per evitare di svuotare l'App.")
        print("="*50)

if __name__ == "__main__":
    asyncio.run(scrape_lidl_completamente_automatico())