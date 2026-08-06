import asyncio
from playwright.async_api import async_playwright
import json
import uuid
from datetime import datetime

# =======================================================
CAP_UTENTE = "20124"
VIA_UTENTE = "Via Vittor Pisani"
# =======================================================

prodotti_catturati_raw = []
reparti_completati = []

def esplora_json_ricorsivo(dato):
    if isinstance(dato, dict):
        chiavi = {k.lower(): v for k, v in dato.items()}
        ha_nome = 'name' in chiavi or 'nome' in chiavi or 'title' in chiavi or 'description' in chiavi or 'descrizione' in chiavi
        ha_prezzo = 'price' in chiavi or 'prezzo' in chiavi or 'currentprice' in chiavi or 'prezzoscontato' in chiavi or 'listprice' in chiavi
        
        if ha_nome and ha_prezzo:
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
    print(" 🚀 SPIDER ESSELUNGA - CACCIA AI VOLANTINI 🚀")
    print("="*60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=50) 
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

            # FASE 1: BYPASS INDIRIZZO 
            print("📍 Apro la schermata di inserimento indirizzo...")
            try:
                btn_verifica = page.locator("text=/VERIFICA INDIRIZZO/i").locator("visible=true").first
                await btn_verifica.wait_for(state="visible", timeout=5000)
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
                    await asyncio.sleep(8) 
                else:
                    print(f"⚠️ Impossibile trovare i campi.")
            except Exception as e:
                pass

            # FASE 2: ESTRAZIONE MIRATA DEI LINK DI VOLANTINI E OFFERTE
            print("\n" + "👁️"*20)
            print("👁️  AVVIO RADAR: CACCIA AI VOLANTINI E AGLI SCONTI...")
            
            await page.keyboard.press("Escape")
            await asyncio.sleep(1)
            
            # URL Forzati per essere sicuri di prendere le sezioni promozionali
            REPARTI_DA_ESPLORARE = [
                {
                    "nome": "🔥 SCONTI 30-40-50% (Volantino attuale)",
                    "url": "https://spesaonline.esselunga.it/commerce/nav/supermercato/store/landing/mix/sconti-30-40-50/260730/centrale-articoli"
                },
                {
                    "nome": "🏷️ TUTTE LE OFFERTE (Volantino Infrasettimanale)",
                    "url": "https://spesaonline.esselunga.it/store/promozioni"
                }
            ]

            # Estraiamo dinamicamente qualsiasi altro banner presente in HomePage che contenga "sconti" o "promozioni"
            promo_links = await page.evaluate('''() => {
                let links = document.querySelectorAll("a");
                let results = [];
                links.forEach(link => {
                    let text = link.innerText.toLowerCase();
                    let url = link.getAttribute('href');
                    if (url && (url.includes('sconti') || url.includes('promozioni') || url.includes('offerte') || text.includes('scont'))) {
                        if (url.startsWith('/')) url = "https://spesaonline.esselunga.it" + url;
                        if (url.includes('esselunga.it')) {
                            results.push({ "nome": "💥 " + (link.innerText.trim() || "Promozione Speciale"), "url": url });
                        }
                    }
                });
                return results;
            }''')

            visti_url = set([r['url'] for r in REPARTI_DA_ESPLORARE])
            for p_link in promo_links:
                if p_link['url'] not in visti_url:
                    visti_url.add(p_link['url'])
                    REPARTI_DA_ESPLORARE.append(p_link)

            print(f"🎯 BINGO! Trovate {len(REPARTI_DA_ESPLORARE)} vetrine esclusive di Volantini e Sconti.")

            # FASE 3: MOTORE DI NAVIGAZIONE "URL JUMPING"
            print("\n" + "*"*50)
            print("🚀 INIZIO SCANSIONE MEDIANTE SALTO DIRETTO DEGLI URL...")
            
            for reparto in REPARTI_DA_ESPLORARE:
                nome = reparto['nome']
                url = reparto['url']
                
                print(f"\n🛒 Salto direttamente a: {nome}")
                try:
                    await page.goto(url, timeout=45000, wait_until="domcontentloaded")
                    print(f"✅ OK! Atterrato! Attendo l'intercettazione dei file...")
                    
                    await asyncio.sleep(4) 
                    
                    for i in range(4):
                        await page.evaluate("window.scrollBy(0, 1500);")
                        await asyncio.sleep(2.5)
                        
                        try:
                            btn_altro = page.locator("button:has-text('Mostra altri'), button:has-text('Carica altro')").first
                            if await btn_altro.is_visible(timeout=500):
                                await btn_altro.click(force=True)
                                await asyncio.sleep(2)
                        except:
                            pass
                            
                    reparti_completati.append(nome)
                            
                except Exception as e:
                    print(f"⚠️ Errore di navigazione URL in '{nome}': {e}")

        except Exception as e:
            print(f"❌ Errore critico globale: {e}")

        await asyncio.sleep(3)
        await browser.close()

    prodotti_finali = []
    visti = set()

    for raw in prodotti_catturati_raw:
        chiavi_basse = {k.lower(): v for k, v in raw.items()}
        
        nome = chiavi_basse.get('name') or chiavi_basse.get('nome') or chiavi_basse.get('title') or chiavi_basse.get('description') or chiavi_basse.get('descrizione')
        if not nome or len(str(nome)) < 3: continue
        
        prezzo_raw = chiavi_basse.get('price') or chiavi_basse.get('prezzo') or chiavi_basse.get('currentprice') or chiavi_basse.get('prezzoscontato') or chiavi_basse.get('listprice')
        if not prezzo_raw: continue
        
        prezzo_str = str(prezzo_raw).replace(',', '.')
        try:
            prezzo_float = float(''.join(c for c in prezzo_str if c.isdigit() or c == '.'))
            if prezzo_float <= 0: continue
        except:
            continue

        img_url = "https://via.placeholder.com/150"
        for k, v in raw.items():
            if ('image' in k.lower() or 'img' in k.lower() or 'url' in k.lower()) and isinstance(v, str) and 'http' in v:
                img_url = v
                break

        chiave = f"{nome}_{prezzo_float}"
        if chiave not in visti:
            visti.add(chiave)
            prodotti_finali.append({
                "id": str(uuid.uuid4())[:8],
                "nome": str(nome)[:100],
                "prezzo_scontato": f"{prezzo_float:.2f}",
                "immagine_url": img_url,
                "categoria": "Esselunga", 
                "data_inizio": datetime.now().strftime("%Y-%m-%d"),
                "dati_grezzi_completi": raw 
            })

    dati_da_salvare = {
        "metadata": {
            "data_scansione": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reparti_trovati": len(REPARTI_DA_ESPLORARE),
            "reparti_scansionati_con_successo": len(reparti_completati)
        },
        "prodotti": prodotti_finali
    }

    with open('esselunga_offerte.json', 'w', encoding='utf-8') as f:
        json.dump(dati_da_salvare, f, indent=4, ensure_ascii=False)
    
    print("\n" + "📊 "*15)
    print(f"🎯 PRODOTTI VOLANTINO SALVATI: {len(prodotti_finali)}")
    print("📊 "*15 + "\n")

if __name__ == "__main__":
    asyncio.run(scrape_esselunga_debug())
