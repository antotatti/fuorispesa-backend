require('dotenv').config();
const axios = require('axios');

async function scopriModelli() {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey || apiKey.includes('incolla_qui')) {
        console.log("Errore: Chiave API non trovata o non valida nel file .env");
        return;
    }
    
    console.log("Interrogo Google sui modelli disponibili per il tuo account...");
    
    try {
        const response = await axios.get(`https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`);
        console.log("\n✅ --- I TUOI MODELLI ATTIVI ---");
        
        let trovati = 0;
        response.data.models.forEach(m => {
            // Filtriamo solo quelli che generano testo (generateContent)
            if (m.supportedGenerationMethods.includes("generateContent")) {
                console.log(`Nome esatto da usare: "${m.name.replace('models/', '')}"`);
                trovati++;
            }
        });
        
        if (trovati === 0) {
            console.log("Nessun modello di testo attivo trovato per questa chiave.");
        }
        console.log("---------------------------------\n");
        
    } catch (error) {
        console.error("\n❌ Errore di connessione API Google:", error.response ? error.response.data.error.message : error.message);
    }
}

scopriModelli();