const express = require("express");
const bodyParser = require("body-parser");
const axios = require("axios");

const app = express();
app.use(bodyParser.json());

const APIFY_TOKEN = "apify_api_HlY6edMSwNJqptH4B2FWttNUIIbHKV0z1JTy";

const BACKEND_URL = process.env.BACKEND_URL || "https://product-polarization-analyzer-production.up.railway.app/api/apify-webhook";

process.on('uncaughtException', (err) => {
    console.log('⚠️ Uncaught Exception:', err.message);
});
process.on('unhandledRejection', (reason) => {
    console.log('⚠️ Unhandled Rejection:', reason);
});

// ============================================================
// DARAZ WEBHOOK
// ============================================================
app.post("/webhook/apify/daraz", async (req, res) => {
    try {
        console.log("🔥 DARAZ WEBHOOK RECEIVED");
        console.log("📦 Full Payload:", JSON.stringify(req.body, null, 2));

        // ✅ STEP 1: Direct payload se category lein
        let category = req.body.category || "unknown";
        console.log("📂 Category from payload:", category);

        // ✅ STEP 2: Agar unknown hai toh input se lein
        if (category === "unknown") {
            const inputData = req.body.input || {};
            category = inputData.category || inputData.searchKeyword || "unknown";
            console.log("📂 Category from input:", category);
        }

        // ✅ STEP 3: Agar phir bhi unknown hai toh task se fetch karein (fallback)
        if (category === "unknown") {
            const { runId } = req.body;
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
                        category = taskInput.category || taskInput.searchKeyword || "unknown";
                        console.log("📂 Category from task:", category);
                    }
                } catch (err) {
                    console.log("Could not fetch task details:", err.message);
                }
            }
        }

        const { datasetId } = req.body;
        if (!datasetId) {
            return res.status(200).send("OK - no datasetId");
        }

        const url = `https://api.apify.com/v2/datasets/${datasetId}/items?clean=true&token=${APIFY_TOKEN}`;
        const { data: items } = await axios.get(url);

        if (!items || items.length === 0) {
            console.log("No items found");
            return res.status(200).send("No items found");
        }

        console.log(`📦 Daraz: ${items.length} items for category: ${category}`);

        const response = await axios.post(BACKEND_URL, {
            category: category,
            products: items,
            count: items.length,
            platform: "daraz"
        }, { timeout: 60000 });

        console.log(`✅ Daraz forwarded: ${response.status}`);
        res.status(200).send("OK");

    } catch (error) {
        console.error("❌ Daraz WEBHOOK ERROR:", error.message);
        if (error.response) {
            console.error("   Backend response:", error.response.status, error.response.data);
        }
        res.status(500).send("Error: " + error.message);
    }
});

// ============================================================
// ETSY WEBHOOK
// ============================================================
app.post("/webhook/apify/etsy", async (req, res) => {
    try {
        console.log("🔥 ETSY WEBHOOK RECEIVED");
        console.log("📦 Full Payload:", JSON.stringify(req.body, null, 2));

        // ✅ STEP 1: Direct payload se category lein
        let category = req.body.category || req.body.keyword || "unknown";
        console.log("📂 Category from payload:", category);

        // ✅ STEP 2: Agar unknown hai toh input se lein
        if (category === "unknown") {
            const inputData = req.body.input || {};
            category = inputData.keyword || inputData.category || "unknown";
            console.log("📂 Category from input:", category);
        }

        // ✅ STEP 3: Agar phir bhi unknown hai toh task se fetch karein (fallback)
        if (category === "unknown") {
            const { runId } = req.body;
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
                        category = taskInput.keyword || taskInput.category || "unknown";
                        console.log("📂 Category from task:", category);
                    }
                } catch (err) {
                    console.log("Could not fetch task details:", err.message);
                }
            }
        }

        const { datasetId } = req.body;
        if (!datasetId) {
            return res.status(200).send("OK - no datasetId");
        }

        const url = `https://api.apify.com/v2/datasets/${datasetId}/items?clean=true&token=${APIFY_TOKEN}`;
        const { data: items } = await axios.get(url);

        if (!items || items.length === 0) {
            console.log("No items found");
            return res.status(200).send("No items found");
        }

        console.log(`📦 Etsy: ${items.length} items for category: ${category}`);

        const response = await axios.post(BACKEND_URL, {
            category: category,
            products: items,
            count: items.length,
            platform: "etsy"
        }, { timeout: 60000 });

        console.log(`✅ Etsy forwarded: ${response.status}`);
        res.status(200).send("OK");

    } catch (error) {
        console.error("❌ Etsy WEBHOOK ERROR:", error.message);
        if (error.response) {
            console.error("   Backend response:", error.response.status, error.response.data);
        }
        res.status(500).send("Error: " + error.message);
    }
});

// ============================================================
// DEBUG & HEALTH
// ============================================================
app.post("/webhook/apify/debug", (req, res) => {
    console.log("🔍 DEBUG - Webhook payload received");
    console.log(JSON.stringify(req.body, null, 2));
    res.status(200).send("Logged");
});

app.get("/health", (req, res) => {
    res.status(200).send("OK");
});

app.listen(3000, () => {
    console.log("🚀 Apify Webhook Server running on port 3000");
    console.log("   Webhook URL: /webhook/apify/daraz");
    console.log("   Etsy Webhook: /webhook/apify/etsy"); 
    console.log("   Forwarding to: " + BACKEND_URL);
});