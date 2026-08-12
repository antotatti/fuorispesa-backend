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
visti = set()

# Variabile globale che cambia: prima "volantino", poi "sito"
stato_scraper = {"current_fonte": "volantino"}

def esplora_json_ricorsivo(dato):
    if isinstance(dato, dict):
        chiavi = {k.lower(): v for k, v in dato.items()}
        ha_nome = 'name' in chiavi or 'nome' in chiavi or 'title' in chiavi or 'description' in chiavi or 'descrizione' in chiavi
        ha_prezzo = 'price' in chiavi or 'prezzo' in chiavi or 'currentprice' in chiavi or 'prezzoscontato' in chiavi or 'listprice' in chiavi
        
        if ha_nome and ha_prezzo:
            dato['custom_fonte'] = stato_scraper["current_fonte"]
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

async def scrape_esselunga_debug():
    print("\n" + "="*60)
    print(" 🚀 SUPER SPIDER ESSELUNGA - VOLANTINI E SITO 🚀")
    print("="*60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=50, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        page.on("response", cattura_traffico)

        try:
            print("➡️ Navigazione verso la HOMEPAGE principale...")
            await page.goto("https://spesaonline.esselunga.it/", timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(4) 
            
            try:
                await page.locator("text=/Accetta/i").locator("visible=true").first.click(timeout=3000)
            except:
                pass

            print("📍 Apro la schermata di inserimento indirizzo...")
            try:
                btn_verifica = page.locator("text=/VERIFICA INDIRIZZO/i").locator("visible=true").first
                await btn_verifica.click()
                await page.locator("input").locator("visible=true").first.wait_for(state="visible", timeout=8000)
                await asyncio.sleep(2) 
                
                inputs_visibili = page.locator("input").locator("visible=true")
                count = await inputs_visibili.count()
                
                if count >= 2:
                    await inputs_visibili.nth(count - 2).click(force=True)
                    await page.keyboard.type(CAP_UTENTE, delay=100)
                    await asyncio.sleep(1)
                    await inputs_visibili.nth(count - 1).click(force=True)
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
                        await page.locator("button:has-text('cerca')").locator("visible=true").first.click(timeout=3000)
                    except:
                        await page.keyboard.press("Enter")
                    await asyncio.sleep(4) 
                    
                    try:
                        await page.locator("text=/ESSELUNGA A CASA/i").locator("visible=true").first.click(force=True, timeout=5000)
                    except:
                        pass
                    await asyncio.sleep(8) 
            except Exception:
                pass

            await page.keyboard.press("Escape")
            await asyncio.sleep(1)
            
            # --- START FASE 1: VOLANTINI (HOME APP) ---
            print("\n" + "👁️"*20)
            print("👁️ FASE 1: CATTURA DEI VOLANTINI ATTUALI E FUTURI")
            stato_scraper["current_fonte"] = "volantino"

            urls_volantini = []
            try:
                await page.goto("https://www.esselunga.it/it-it/promozioni/volantini.html", timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(5)
                urls_volantini = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => a.href)
                        .filter(href => href.includes('volantino-digitale'));
                }''')
                urls_volantini = list(set(urls_volantini))
            except:
                pass

            for url in urls_volantini:
                print(f"📖 Sfoglio Volantino: {url}")
                try:
                    await page.goto(url, timeout=45000, wait_until="domcontentloaded")
                    await asyncio.sleep(5)
                    for i in range(4):
                        try:
                            await page.locator(".swiper-button-next, .next-page, button[aria-label*='Avanti']").first.click(timeout=1500)
                            await asyncio.sleep(2)
                        except:
                            await page.evaluate("window.scrollBy(0, 1000);")
                            await asyncio.sleep(2)
                except:
                    pass

            # --- START FASE 2: SITO COMPLETO (RICERCA APP) ---
            print("\n" + "*"*50)
            print("🚀 FASE 2: SCANSIONE DEL CATALOGO PROMOZIONALE SITO...")
            stato_scraper["current_fonte"] = "sito"

            REPARTI_SITO = [
                {"nome": "Tutte le Offerte", "url": "https://spesaonline.esselunga.it/store/promozioni"},
                {"nome": "Amici Animali", "url": "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/amici-animali/260724?filtri=promozioni"},
                {"nome": "Cura Persona", "url": "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/cura-della-persona/260723?filtri=promozioni"},
                {"nome": "Cura Casa", "url": "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/cura-della-casa/260722?filtri=promozioni"}
            ]

            for reparto in REPARTI_SITO:
                nome = reparto['nome']
                url = reparto['url']
                print(f"\n🛒 Navigo in: {nome}")
                try:
                    await page.goto(url, timeout=45000, wait_until="domcontentloaded")
                    await asyncio.sleep(4) 
                    for i in range(5):
                        await page.evaluate("window.scrollBy(0, 1500);")
                        await asyncio.sleep(2)
                        try:
                            btn_altro = page.locator("button:has-text('Mostra altri'), button:has-text('Carica altro')").first
                            if await btn_altro.is_visible(timeout=500):
                                await btn_altro.click(force=True)
                                await asyncio.sleep(2)
                        except:
                            pass
                except Exception as e:
                    print(f"⚠️ Errore di navigazione in '{nome}': {e}")

        except Exception as e:
            print(f"❌ Errore critico globale: {e}")

        await asyncio.sleep(3)
        await browser.close()

    # ELABORAZIONE DEI PRODOTTI TROVATI
    prodotti_finali = []
    nomi_inseriti = set()

    # Leggiamo i dati: Volantini hanno la priorità (sono salvati prima), il Sito colma i buchi.
    for raw in prodotti_catturati_raw:
        chiavi = {k.lower(): v for k, v in raw.items()}
        
        nome = chiavi.get('name') or chiavi.get('nome') or chiavi.get('title') or chiavi.get('description')
        if not nome or len(str(nome)) < 3: continue
        
        prezzo_raw = chiavi.get('price') or chiavi.get('prezzo') or chiavi.get('currentprice') or chiavi.get('discountedprice')
        if not prezzo_raw: continue
        
        try:
            p_scontato = float(str(prezzo_raw).replace(',', '.').replace('€', '').strip())
            if p_scontato <= 0: continue
        except:
            continue

        chiave_nome = str(nome).strip().lower()

        # PREVIENE I DOPPIONI DANDO PRIORITÀ AL VOLANTINO
        if chiave_nome not in nomi_inseriti:
            nomi_inseriti.add(chiave_nome)
            
            raw_str = json.dumps(raw).lower()
            date_match = re.search(r'dal (\d{2}/\d{2}/\d{4})\s*al\s*(\d{2}/\d{2}/\d{4})', raw_str)
            data_inizio = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
            data_fine = date_match.group(2) if date_match else "N/D"

            img_url = "https://via.placeholder.com/150"
            for k, v in raw.items():
                if ('image' in k.lower() or 'img' in k.lower() or 'url' in k.lower()) and isinstance(v, str) and 'http' in v:
                    img_url = v
                    break

            prodotti_finali.append({
                "id": str(uuid.uuid4())[:8],
                "nome": str(nome)[:100],
                "prezzo_scontato": f"{p_scontato:.2f}",
                "immagine_url": img_url,
                "categoria": "Esselunga", 
                "data_inizio": data_inizio,
                "data_fine": data_fine,
                "dati_grezzi_completi": raw,
                "fonte": raw.get('custom_fonte', 'volantino')
            })

    dati_da_salvare = {
        "metadata": {
            "data_scansione": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "prodotti": prodotti_finali
    }

    with open('esselunga_offerte.json', 'w', encoding='utf-8') as f:
        json.dump(dati_da_salvare, f, indent=4, ensure_ascii=False)
    
    print("\n" + "📊 "*15)
    print(f"🎯 PRODOTTI IBRIDI SALVATI: {len(prodotti_finali)}")
    print("📊 "*15 + "\n")

if __name__ == "__main__":
    asyncio.run(scrape_esselunga_debug())
