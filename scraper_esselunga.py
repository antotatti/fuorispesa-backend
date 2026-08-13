import asyncio
from playwright.async_api import async_playwright
import json
import uuid
import re
from datetime import datetime

# =======================================================
CAP_UTENTE = "20124"
VIA_UTENTE = "Via Vittor Pisani"
# =======================================================

prodotti_catturati_raw = []
visti_json = set()
stato_scraper = {"current_fonte": "volantino", "current_volantino": ""}

def esplora_json_ricorsivo(dato):
    if isinstance(dato, dict):
        chiavi = {k.lower(): v for k, v in dato.items()}
        ha_nome = 'name' in chiavi or 'nome' in chiavi or 'title' in chiavi or 'description' in chiavi
        ha_prezzo = 'price' in chiavi or 'prezzo' in chiavi or 'currentprice' in chiavi or 'discountedprice' in chiavi
        
        if ha_nome and ha_prezzo:
            firma = str(chiavi.get('name', '')) + str(chiavi.get('price', ''))
            if firma not in visti_json:
                visti_json.add(firma)
                dato['custom_fonte'] = stato_scraper["current_fonte"]
                dato['custom_volantino_nome'] = stato_scraper["current_volantino"]
                prodotti_catturati_raw.append(dato)
        
        for valore in dato.values():
            esplora_json_ricorsivo(valore)
    elif isinstance(dato, list):
        for item in dato:
            esplora_json_ricorsivo(item)

async def cattura_traffico(response):
    if response.request.resource_type in ["xhr", "fetch"]:
        if "esselunga" in response.url.lower():
            try:
                dati = await response.json()
                esplora_json_ricorsivo(dati)
            except:
                pass 

async def run_scraper():
    print("🚀 AVVIO SUPER SPIDER ESSELUNGA IBRIDO 🚀")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        page.on("response", cattura_traffico)

        try:
            print("📍 Inserimento Indirizzo (Modalità Sicura Iniziale)...")
            await page.goto("https://spesaonline.esselunga.it/", timeout=60000)
            await asyncio.sleep(4)
            try:
                await page.locator("text=/Accetta/i").locator("visible=true").first.click(timeout=3000)
            except:
                pass

            btn_verifica = page.locator("text=/VERIFICA INDIRIZZO/i").locator("visible=true").first
            await btn_verifica.wait_for(state="visible", timeout=8000)
            await btn_verifica.click()
            
            await page.locator("input").locator("visible=true").first.wait_for(state="visible", timeout=8000)
            await asyncio.sleep(2) 
            
            inputs_visibili = page.locator("input").locator("visible=true")
            count = await inputs_visibili.count()
            
            if count >= 2:
                cap_index = count - 2
                via_index = count - 1
                
                print(f"✍️ Inserisco CAP: {CAP_UTENTE}")
                await inputs_visibili.nth(cap_index).click(force=True)
                await page.keyboard.type(CAP_UTENTE, delay=100)
                await asyncio.sleep(1)

                print(f"✍️ Inserisco VIA: {VIA_UTENTE}")
                await inputs_visibili.nth(via_index).click(force=True)
                await page.keyboard.type(VIA_UTENTE, delay=100)
                
                await asyncio.sleep(4) 
                
                await page.keyboard.press("Space")
                await asyncio.sleep(0.5)
                await page.keyboard.press("Backspace")
                await asyncio.sleep(2)

                await page.keyboard.press("ArrowDown")
                await asyncio.sleep(1)
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)

                try:
                    btn_cerca = page.locator("button:has-text('cerca')").locator("visible=true").first
                    await btn_cerca.click(timeout=3000)
                except:
                    await page.keyboard.press("Enter")
                await asyncio.sleep(4) 
                
                try:
                    btn_casa = page.locator("text=/ESSELUNGA A CASA/i").locator("visible=true").first
                    await btn_casa.click(force=True, timeout=5000)
                except:
                    pass
                await asyncio.sleep(5) 
        except Exception as e:
            print(f"⚠️ Indirizzo Fallito: {e}")

        # ---- FASE 1: I VOLANTINI DIGITALI ----
        print("📖 FASE 1: Ricerca e Sfogliamento Volantini Digitali")
        stato_scraper["current_fonte"] = "volantino"
        try:
            await page.goto("https://www.esselunga.it/it-it/promozioni/volantini.html", timeout=60000)
            await asyncio.sleep(4)
            urls_volantini = await page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a'));
                return links.map(a => a.href).filter(href => href.includes('volantino-digitale'));
            }''')
            
            for url in set(urls_volantini):
                try:
                    nome_estratto = url.split("volantino-digitale.")[-1].replace(".html", "").replace("-", " ").upper()
                    nome_estratto = nome_estratto.replace("%20", " ")
                except:
                    nome_estratto = "OFFERTE MISTE"
                    
                stato_scraper["current_volantino"] = nome_estratto
                print(f"-> Sfoglio: {nome_estratto}")
                
                try:
                    await page.goto(url, timeout=45000)
                    await asyncio.sleep(4)
                    for _ in range(40): 
                        try:
                            btn = page.locator(".swiper-button-next, button[aria-label*='Avanti']").first
                            if await btn.is_visible(timeout=1000):
                                await btn.click()
                                await asyncio.sleep(1.5)
                            else:
                                await page.evaluate("window.scrollBy(0, 1500);")
                                await asyncio.sleep(1)
                        except:
                            await page.evaluate("window.scrollBy(0, 1500);")
                            await asyncio.sleep(1)
                except:
                    pass
        except Exception as e:
            print(f"⚠️ Nessun Volantino Trovato: {e}")

        # ---- FASE 2: E-COMMERCE SPECIFICO (CON TUTTE LE CATEGORIE) ----
        print("🛒 FASE 2: Caricamento Intero Catalogo Promozionale")
        stato_scraper["current_fonte"] = "sito"
        stato_scraper["current_volantino"] = "" 
        
        reparti = [
            "https://spesaonline.esselunga.it/store/promozioni",
            "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/amici-animali/260724?filtri=promozioni",
            "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/cura-della-persona/260723?filtri=promozioni",
            "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/cura-della-casa/260722?filtri=promozioni",
            "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/frutta-e-verdura/260713?filtri=promozioni",
            "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/gastronomia-e-piatti-pronti/260716?filtri=promozioni",
            "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/carne/260714?filtri=promozioni",
            "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/pesce/260715?filtri=promozioni",
            "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/dispensa/260718?filtri=promozioni",
            "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/colazione/260719?filtri=promozioni"
        ]
        
        for rep_url in reparti:
            print(f"-> Accesso profondo: {rep_url}")
            try:
                await page.goto(rep_url, timeout=45000)
                await asyncio.sleep(5)
                for _ in range(40): 
                    await page.evaluate("window.scrollBy(0, 1500);")
                    await asyncio.sleep(2) 
                    try:
                        btn = page.locator("button:has-text('Mostra altri'), button:has-text('Carica altro')").first
                        if await btn.is_visible(timeout=1000):
                            await btn.click(force=True)
                            await asyncio.sleep(3)
                    except:
                        pass
            except:
                pass
        
        await browser.close()

    # ---- ELABORAZIONE FINALE E CREAZIONE DATABASE ----
    prodotti_finali = []
    nomi_inseriti = set()

    for raw in prodotti_catturati_raw:
        chiavi = {k.lower(): v for k, v in raw.items()}
        
        nome = chiavi.get('name') or chiavi.get('nome') or chiavi.get('title') or chiavi.get('description')
        if not nome or len(str(nome)) < 3: continue
        
        prezzo_scontato = chiavi.get('discountedprice') or chiavi.get('price') or chiavi.get('currentprice') or chiavi.get('prezzo')
        prezzo_originale = chiavi.get('listprice') or chiavi.get('oldprice') or chiavi.get('prezzo_originale')
        
        if not prezzo_scontato: continue
        
        try:
            p_scontato = float(str(prezzo_scontato).replace(',', '.').replace('€', '').strip())
            p_orig = float(str(prezzo_originale).replace(',', '.').replace('€', '').strip()) if prezzo_originale else None
            if p_orig and p_orig <= p_scontato: p_orig = None
        except:
            continue

        chiave_nome = str(nome).strip().lower()

        if chiave_nome not in nomi_inseriti:
            nomi_inseriti.add(chiave_nome)
            
            raw_str = json.dumps(raw).lower()
            date_match = re.search(r'dal (\d{2}/\d{2}/\d{4})\s*al\s*(\d{2}/\d{2}/\d{4})', raw_str)
            data_inizio = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
            data_fine = date_match.group(2) if date_match else "N/D"

            img_url = "https://via.placeholder.com/150"
            for k, v in raw.items():
                if isinstance(v, str) and 'http' in v and ('.png' in v.lower() or '.jpg' in v.lower() or '.jpeg' in v.lower()):
                    img_url = v
                    break

            req_tessera = 'fidaty' in raw_str or 'fìdaty' in raw_str or 'loyalty' in raw_str
            fonte_originale = raw.get('custom_fonte', 'volantino')
            
            prodotti_finali.append({
                "id": str(uuid.uuid4())[:8],
                "nome": str(nome)[:100],
                "prezzo_scontato": f"{p_scontato:.2f}",
                "prezzo_originale": f"{p_orig:.2f}" if p_orig else None,
                "immagine_url": img_url,
                "categoria": "Esselunga",
                "data_inizio": data_inizio,
                "data_fine": data_fine,
                "richiede_tessera": req_tessera,
                "dati_grezzi_completi": raw,
                "fonte": fonte_originale,
                "volantino_nome": raw.get('custom_volantino_nome', '')
            })

    dati_da_salvare = {
        "metadata": {
            "data_scansione": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "prodotti_totali": len(prodotti_finali)
        },
        "prodotti": prodotti_finali
    }

    with open('esselunga_offerte.json', 'w', encoding='utf-8') as f:
        json.dump(dati_da_salvare, f, indent=4, ensure_ascii=False)
        
    print(f"🎯 TUTTO COMPLETATO! Rilevati e compilati {len(prodotti_finali)} prodotti totali.")

if __name__ == "__main__":
    asyncio.run(run_scraper())
