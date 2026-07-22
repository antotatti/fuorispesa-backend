const fs = require('fs');

async function avviaScraperEsselunga() {
  console.log("Avvio estrazione dati Esselunga...");
  
  const datiEsselunga = {
    negozio: "Esselunga",
    data_estrazione: new Date().toISOString().split('T')[0],
    prodotti: [
      {
        id: "esse_1",
        nome: "Gocciole Pavesi",
        prezzo_scontato: 1.89,
        prezzo_originale: 2.59,
        prezzo_unita_misura: "500 g",
        percentuale_sconto: 27,
        categoria: "Colazione",
        immagine_url: "https://via.placeholder.com/150/FFD700/000000?text=Gocciole",
        testo_disponibilita: "dal 24.07. al 30.07.",
        data_inizio: "2026-07-24T08:00:00",
        data_fine: "2026-07-30T20:00:00"
      }
    ]
  };

  fs.writeFileSync('esselunga_offerte.json', JSON.stringify(datiEsselunga, null, 2));
  console.log("File esselunga_offerte.json salvato con successo.");
}

avviaScraperEsselunga();