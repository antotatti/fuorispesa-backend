const fs = require('fs');

async function avviaScraperConad() {
  console.log("Avvio estrazione dati Conad...");
  
  const datiConad = {
    negozio: "Conad",
    data_estrazione: new Date().toISOString().split('T')[0],
    prodotti: [
      {
        id: "conad_1",
        nome: "Passata di Pomodoro Mutti",
        prezzo_scontato: 0.99,
        prezzo_originale: 1.45,
        prezzo_unita_misura: "700 g",
        percentuale_sconto: 31,
        categoria: "Dispensa",
        immagine_url: "https://via.placeholder.com/150/E3000F/FFFFFF?text=Mutti",
        testo_disponibilita: "dal 25.07. al 31.07.",
        data_inizio: "2026-07-25T08:00:00",
        data_fine: "2026-07-31T20:00:00"
      }
    ]
  };

  fs.writeFileSync('conad_offerte.json', JSON.stringify(datiConad, null, 2));
  console.log("File conad_offerte.json salvato con successo.");
}

avviaScraperConad();