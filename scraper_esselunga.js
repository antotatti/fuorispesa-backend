const puppeteer = require('puppeteer');
const fs = require('fs');

async function avviaScraperEsselunga() {
  console.log("Avvio del browser invisibile per Esselunga...");

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();

  try {
    console.log("Navigazione verso il sito...");
    await page.goto('https://www.esselunga.it/it-it/promozioni.html', { waitUntil: 'networkidle2' });

    // === ESTRAZIONE AUTOMATICA DEL PERIODO DALLA PAGINA ESSELUNGA ===
    const periodoVolantino = await page.evaluate(() => {
      const elementoData = document.querySelector('.flyer-date, .validity-period, h1, .promo-title');
      return elementoData ? elementoData.innerText.trim() : "Offerte Attive";
    });

    // Estrazione dei prodotti e iniezione automatica del periodo
    const prodottiEstratti = await page.evaluate((periodoTrovato) => {
      const listaProdotti = [];
      
      const elementi = document.querySelectorAll('.box-product, .product-card, article'); 

      elementi.forEach((el, index) => {
        const nome = el.querySelector('.product-name, h3, .title')?.innerText || 'Nome Sconosciuto';
        const prezzo = el.querySelector('.price, .current-price')?.innerText || '0.00';
        const immagine = el.querySelector('img')?.src || '';

        listaProdotti.push({
          id: `esse_auto_${index}_${Date.now()}`,
          nome: nome,
          prezzo_scontato: prezzo,
          negozio: "Esselunga",
          periodo: periodoTrovato, // <-- Inserisce automaticamente la data estratta dal sito
          immagine_url: immagine
        });
      });

      return listaProdotti;
    }, periodoVolantino);

    console.log(`Trovati ${prodottiEstratti.length} prodotti!`);

    const datiEsselunga = {
      negozio: { id: "esselunga_italia", nome: "Esselunga", colore_brand: "#990000" },
      volantino: { data_inizio: new Date().toISOString().split('T')[0], periodo: periodoVolantino },
      prodotti: prodottiEstratti.length > 0 ? prodottiEstratti : [
        {
          id: "esse_default_1",
          nome: "Prodotto in arrivo da volantino Esselunga",
          prezzo_scontato: "1.00",
          negozio: "Esselunga",
          periodo: periodoVolantino,
          immagine_url: ""
        }
      ] 
    };

    fs.writeFileSync('esselunga_offerte.json', JSON.stringify(datiEsselunga, null, 2));
    console.log("File esselunga_offerte.json generato con successo con gestione automatica del periodo.");

  } catch (errore) {
    console.error("Errore durante lo scraping:", errore);
  } finally {
    await browser.close();
  }
}

avviaScraperEsselunga();
