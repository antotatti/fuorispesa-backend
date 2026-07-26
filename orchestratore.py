import asyncio
import time
from scraper_lidl import scrape_lidl_completamente_automatico
# Qui in futuro aggiungeremo: from scraper_coop import scrape_coop, ecc.

async def aggiorna_tutti_i_negozi():
    inizio = time.time()
    print("🌟 AVVIO ORCHESTRATORE FUORISPESA 🌟")
    print("Inizio aggiornamento globale dei database...")
    
    # 1. Aggiornamento Lidl
    try:
        print("\n---> Lancio modulo: LIDL")
        await scrape_lidl_completamente_automatico()
    except Exception as e:
        print(f"❌ Errore critico nel modulo Lidl: {e}")

    # 2. Aggiornamento Futuro (es. Coop)
    # try:
    #     print("\n---> Lancio modulo: COOP")
    #     await scrape_coop()
    # except Exception as e:
    #     print(f"❌ Errore critico nel modulo Coop: {e}")

    fine = time.time()
    minuti_trascorsi = round((fine - inizio) / 60, 2)
    print(f"\n✅ Aggiornamento Globale terminato in {minuti_trascorsi} minuti.")

if __name__ == "__main__":
    asyncio.run(aggiorna_tutti_i_negozi())