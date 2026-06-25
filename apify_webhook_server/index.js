const express = require("express");
const bodyParser = require("body-parser");
const axios = require("axios");

const app = express();
app.use(bodyParser.json());

const APIFY_TOKEN = "apify_api_HlY6edMSwNJqptH4B2FWttNUIIbHKV0z1JTy";

// ✅ BACKEND URL (Railway backend ka URL)
// ✅ Railway internal URL (public URL ki jagah)
const BACKEND_URL = process.env.BACKEND_URL; 
// Agar variable set nahi hai, toh log error de
if (!BACKEND_URL) {
    console.error("❌ ERROR: BACKEND_URL environment variable is not set!");
}
process.on('uncaughtException', (err) => {
    console.log('⚠️ Uncaught Exception:', err.message);
});
process.on('unhandledRejection', (reason) => {
    console.log('⚠️ Unhandled Rejection:', reason);
});

app.post("/webhook/apify/daraz", async (req, res) => {
    try {
        console.log("🔥 WEBHOOK RECEIVED");

        const { runId, datasetId } = req.body;
        
        let category = "unknown";

        // Get category from run details
        if (runId) {
            try {
                const runUrl = `https://api.apify.com/v2/actor-runs/${runId}?token=${APIFY_TOKEN}`;
                const runResponse = await axios.get(runUrl);
                const runData = runResponse.data.data;
                
                const taskId = runData.actorTaskId;
                
                if (taskId) {
                    const taskUrl = `https://api.apify.com/v2/actor-tasks/${taskId}?token=${APIFY_TOKEN}`;
                    const taskResponse = await axios.get(taskUrl);
                    const taskInput = taskResponse.data.data.input;
                    category = taskInput.category || taskInput.search_keyword || "unknown";
                    console.log("📦 CATEGORY FROM TASK:", category);
                } else {
                    const runInput = runData.input;
                    category = runInput.category || runInput.search_keyword || "unknown";
                    console.log("📦 CATEGORY FROM RUN INPUT:", category);
                }
            } catch (err) {
                console.log("Could not fetch details:", err.message);
            }
        }

        if (!datasetId) {
            return res.status(200).send("OK - no datasetId");
        }

        // ✅ Fetch dataset items from Apify
        const url = `https://api.apify.com/v2/datasets/${datasetId}/items?clean=true&token=${APIFY_TOKEN}`;
        const { data: items } = await axios.get(url);

        if (!items || items.length === 0) {
            console.log("No items found in dataset");
            return res.status(200).send("No items found");
        }

        console.log(`📦 Received ${items.length} items for category: ${category}`);

        // ✅ FORWARD TO BACKEND (CSV save nahi karega, backend karega)
        const response = await axios.post(BACKEND_URL, {
            category: category,
            products: items,
            count: items.length,
            platform: "daraz"
        }, { timeout: 60000 });  // ✅ 60 seconds timeout

        console.log(`✅ Forwarded ${items.length} items to backend`);
        console.log(`   Backend response: ${response.status}`);

        res.status(200).send("OK");

    } catch (error) {
        console.error("❌ WEBHOOK ERROR:", error.message);
        if (error.response) {
            console.error("   Backend response:", error.response.status, error.response.data);
        }
        res.status(500).send("Error: " + error.message);
    }
});

// Debug endpoint
app.post("/webhook/apify/debug", (req, res) => {
    console.log("🔍 DEBUG - Webhook payload received");
    console.log(JSON.stringify(req.body, null, 2));
    res.status(200).send("Logged");
});

// Health check
app.get("/health", (req, res) => {
    res.status(200).send("OK");
});

app.listen(3000, () => {
    console.log("🚀 Apify Webhook Server running on port 3000");
    console.log("   Webhook URL: /webhook/apify/daraz");
    console.log("   Forwarding to: " + BACKEND_URL);
});