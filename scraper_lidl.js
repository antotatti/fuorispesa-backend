require('dotenv').config();
const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs');

const NEGOZIO_ID = "lidl_italia";
const URL_LIDL_OFFERTE = "https://www.lidl.it/c/super-offerte-kw-29-26/a10098574"; 

// --- FUNZIONE 1: ALLARME TELEGRAM (Opzionale) ---
async function inviaAllarmeTelegram(messaggio) {
    const token = process.env.TELEGRAM_BOT_TOKEN;
    const chatId = process.env.TELEGRAM_CHAT_ID;
    
    if (!token || !chatId || token.includes('incolla_qui')) return;
    
    try {
        const url = `https://api.telegram.org/bot${token}/sendMessage`;
        await axios.post(url, { chat_id: chatId, text: `🚨 *FuoriSpesa Bot*\n\n${messaggio}`, parse_mode: 'Markdown' });
        console.log("Notifica Telegram inviata con successo.");
    } catch (e) {
        console.error("Impossibile inviare la notifica Telegram.");
    }
}

// --- FUNZIONE 2: CATEGORIZZAZIONE INTELLIGENTE LOCALE ---
function categorizzaProdottiLocalmente(prodotti) {
    console.log("Avvio classificazione intelligente dei prodotti...");
    
    prodotti.forEach(p => {
        const nome = p.nome.toLowerCase();
        
        if (nome.includes('anguria') || nome.includes('frutta') || nome.includes('verdura') || nome.includes('mela') || nome.includes('patate')) {
            p.categoria = "Ortofrutta";
        } else if (nome.includes('carne') || nome.includes('pollo') || nome.includes('tonno') || nome.includes('pesce') || nome.includes('bistecca')) {
            p.categoria = "Carne e Pesce";
        } else if (nome.includes('latte') || nome.includes('formaggio') || nome.includes('stracchino') || nome.includes('uova') || nome.includes('mozzarella') || nome.includes('burro')) {
            p.categoria = "Latticini e Formaggi";
        } else if (nome.includes('gelato') || nome.includes('cono') || nome.includes('coppette') || nome.includes('surgelati') || nome.includes('polaretti')) {
            p.categoria = "Surgelati";
        } else if (nome.includes('bibita') || nome.includes('coca cola') || nome.includes('acqua') || nome.includes('succo') || nome.includes('birra') || nome.includes('powerade') || nome.includes('aquavitamin')) {
            p.categoria = "Bevande";
        } else if (nome.includes('brioche') || nome.includes('biscotti') || nome.includes('kinder') || nome.includes('pesto') || nome.includes('pasta')) {
            p.categoria = "Dispensa";
        } else if (nome.includes('deodorante') || nome.includes('smacchia') || nome.includes('spray') || nome.includes('igiene')) {
            p.categoria = "Igiene e Cura";
        } else {
            p.categoria = "Altro";
        }
    });

    console.log("Classificazione completata!");
    return prodotti;
}

// --- MOTORE PRINCIPALE ---
async function avviaScraper() {
    console.log(`Avvio scraper potenziato per ${NEGOZIO_ID}...`);

    try {
        const { data } = await axios.get(URL_LIDL_OFFERTE, {
            headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }
        });

        const $ = cheerio.load(data);
        let prodottiEstratti = [];

        $('.ACampaignGrid__item, .AProductGridbox__GridTilePlaceholder').each((index, element) => {
            try {
                const rawData = $(element).attr('data-grid-data');
                if (!rawData) return;

                const dataJson = JSON.parse(rawData);
                if (!dataJson.havingPrice || !dataJson.price) return;

                const brand = dataJson.brand?.name || '';
                const titolo = dataJson.fullTitle || dataJson.title;
                const nome = brand && !titolo.toLowerCase().includes(brand.toLowerCase()) ? `${brand} ${titolo}` : titolo;

                if (!nome) return;

                let immagine_url = dataJson.image || '';
                let prezzo_scontato = dataJson.price.price;
                let prezzo_originale = dataJson.price.oldPrice || prezzo_scontato;
                
                let scontoText = dataJson.price.discount?.discountText || '';
                let percentuale_sconto = dataJson.price.discount?.percentageDiscount || 0;
                
                if (!percentuale_sconto && prezzo_originale > prezzo_scontato) {
                    percentuale_sconto = Math.round(((prezzo_originale - prezzo_scontato) / prezzo_originale) * 100);
                }

                const info_base = dataJson.price.basePrice?.text || '';
                const info_pacco = dataJson.price.packaging?.text || '';
                const prezzo_unita_testo = `${info_pacco} ${info_base}`.trim();

                const bollino_scorta = percentuale_sconto > 40;

                if (prezzo_scontato) {
                    prodottiEstratti.push({
                        id: `${NEGOZIO_ID}_${new Date().toISOString().split('T')[0]}_${index}`,
                        nome: nome,
                        categoria: "Da catalogare",
                        immagine_url: immagine_url,
                        prezzo_originale: prezzo_originale,
                        prezzo_scontato: prezzo_scontato,
                        percentuale_sconto: percentuale_sconto,
                        prezzo_unita_misura: prezzo_unita_testo,
                        bollino_scorta: bollino_scorta
                    });
                }
            } catch (err) {}
        });

        if (prodottiEstratti.length === 0) {
            console.log("Nessun prodotto trovato. Invio allarme...");
            await inviaAllarmeTelegram(`Scraping fallito per Lidl. Trovati 0 prodotti.`);
            return;
        }

        // Categorizzazione intelligente locale
        prodottiEstratti = categorizzaProdottiLocalmente(prodottiEstratti);

        const jsonFinale = {
            negozio: { id: NEGOZIO_ID, nome: "Lidl", colore_brand: "#0050AA" },
            volantino: { data_inizio: new Date().toISOString().split('T')[0] },
            prodotti: prodottiEstratti
        };

        fs.writeFileSync('lidl_offerte.json', JSON.stringify(jsonFinale, null, 2));
        console.log(`Completato! ${prodottiEstratti.length} prodotti salvati in lidl_offerte.json`);

    } catch (error) {
        console.error("Errore critico del server:", error.message);
        await inviaAllarmeTelegram(`Errore di rete provando a leggere la pagina di Lidl.`);
    }
}

avviaScraper();
