const puppeteer = require('puppeteer');
const fs = require('fs');

async function avviaScraperEsselunga() {
  console.log("Avvio del browser invisibile per Esselunga...");

  // Avviamo Chrome in modalità invisibile con i parametri di sicurezza per i server Linux di GitHub
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();

  try {
    // 1. Andiamo sulla pagina web reale (Questo link andrà aggiornato con la pagina esatta delle promozioni)
    console.log("Navigazione verso il sito...");
    await page.goto('https://www.esselunga.it/it-it/promozioni.html', { waitUntil: 'networkidle2' });

    // 2. Estraiamo i dati leggendo la "struttura" della pagina web
    const prodottiEstratti = await page.evaluate(() => {
      const listaProdotti = [];
      
      // ATTENZIONE: Questo è il "nodo" strutturale. 
      // ".box-product" è un nome di esempio. Dovremo ispezionare il sito vero per trovare il nome esatto usato dai loro ingegneri.
      const elementi = document.querySelectorAll('.box-product'); 

      elementi.forEach((el, index) => {
        // Estraiamo il testo dai vari nodi figli. (Anche questi ".product-name" ecc. sono esempi da tarare)
        const nome = el.querySelector('.product-name')?.innerText || 'Nome Sconosciuto';
        const prezzo = el.querySelector('.price')?.innerText || '0.00';
        const immagine = el.querySelector('img')?.src || '';

        listaProdotti.push({
          id: `esse_auto_${index}`,
          nome: nome,
          prezzo_scontato: prezzo,
          negozio: "Esselunga",
          immagine_url: immagine
        });
      });

      return listaProdotti;
    });

    console.log(`Trovati ${prodottiEstratti.length} prodotti!`);

    // 3. Creiamo l'oggetto finale e lo salviamo nel JSON
    const datiEsselunga = {
      negozio: "Esselunga",
      data_estrazione: new Date().toISOString().split('T')[0],
      prodotti: prodottiEstratti.length > 0 ? prodottiEstratti : [] 
    };

    fs.writeFileSync('esselunga_offerte.json', JSON.stringify(datiEsselunga, null, 2));
    console.log("File esselunga_offerte.json generato con successo dai dati reali.");

  } catch (errore) {
    console.error("Errore durante lo scraping:", errore);
  } finally {
    await browser.close();
  }
}

avviaScraperEsselunga();
