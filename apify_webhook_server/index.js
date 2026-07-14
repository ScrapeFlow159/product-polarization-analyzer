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

        let category = null;

        // ✅ SOURCE 1: Task se fetch karein
        const { runId, datasetId } = req.body;

        if (runId) {
            try {
                console.log(`📥 Fetching task details for runId: ${runId}`);
                const runUrl = `https://api.apify.com/v2/actor-runs/${runId}?token=${APIFY_TOKEN}`;
                const runResponse = await axios.get(runUrl);
                const runData = runResponse.data.data;
                const taskId = runData.actorTaskId;

                if (taskId) {
                    const taskUrl = `https://api.apify.com/v2/actor-tasks/${taskId}?token=${APIFY_TOKEN}`;
                    const taskResponse = await axios.get(taskUrl);
                    const taskInput = taskResponse.data.data.input;

                    category = taskInput.category || 
                              taskInput.search_keyword || 
                              taskInput.searchKeyword || 
                              null;
                    console.log("📂 Category from task:", category);
                }
            } catch (err) {
                console.log("⚠️ Could not fetch task:", err.message);
            }
        }

        // ✅ SOURCE 2: Agar task se nahi mila toh input se lein
        if (!category) {
            const inputData = req.body.input || {};
            category = inputData.category || 
                      inputData.search_keyword || 
                      inputData.searchKeyword || 
                      null;
            console.log("📂 Category from input:", category);
        }

        // ✅ SOURCE 3: Agar phir bhi nahi mila toh products se searchKeyword lein (SAB SE BEST!)
        if (!category) {
            const { datasetId } = req.body;
            if (datasetId) {
                try {
                    const url = `https://api.apify.com/v2/datasets/${datasetId}/items?clean=true&token=${APIFY_TOKEN}&limit=1`;
                    const response = await axios.get(url);
                    const items = response.data;
                    
                    if (items && items.length > 0) {
                        // ✅ Pehle product se searchKeyword lein
                        category = items[0].searchKeyword || 
                                  items[0].search_keyword || 
                                  null;
                        console.log("📂 Category from product searchKeyword:", category);
                    }
                } catch (err) {
                    console.log("⚠️ Could not fetch product:", err.message);
                }
            }
        }

        // ✅ SOURCE 4: FINAL FALLBACK
        if (!category) {
            category = "powerbanks";  // Default
            console.log("📂 Using fallback category:", category);
        }

        console.log(`📂 FINAL Category: ${category}`);

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

        await axios.post(BACKEND_URL, {
            category: category,
            products: items,
            platform: "daraz",
            input: req.body.input || {}
        }, { timeout: 60000 });

        console.log(`✅ Daraz forwarded`);
        res.status(200).send("OK");

    } catch (error) {
        console.error("❌ Daraz WEBHOOK ERROR:", error.message);
        res.status(500).send("Error: " + error.message);
    }
});
// ============================================================
// ETSY WEBHOOK
// ============================================================

// ============================================================
// ETSY CATEGORIES - 5 Dedicated Webhooks
// ============================================================

// 1. Custom Wooden Cake Topper
app.post("/webhook/apify/etsy/custom-wooden-cake-topper", async (req, res) => {
    await handleEtsyWebhook(req, res, "custom wooden cake topper");
});

// 2. Hand Stitched Leather Bookmark
app.post("/webhook/apify/etsy/hand-stitched-leather-bookmark", async (req, res) => {
    await handleEtsyWebhook(req, res, "hand stitched leather bookmark");
});

// 3. Personalized Brass Pet Tag
app.post("/webhook/apify/etsy/personalized-brass-pet-tag", async (req, res) => {
    await handleEtsyWebhook(req, res, "personalized brass pet tag");
});

// 4. Custom Embroidered Baby Onesie
app.post("/webhook/apify/etsy/custom-embroidered-baby-onesie", async (req, res) => {
    await handleEtsyWebhook(req, res, "custom embroidered baby onesie");
});

// 5. Personalized Wax Seal Stamp
app.post("/webhook/apify/etsy/personalized-wax-seal-stamp", async (req, res) => {
    await handleEtsyWebhook(req, res, "personalized wax seal stamp");
});

// ============================================================
// COMMON HANDLER FUNCTION
// ============================================================

// ============================================================
// COMMON HANDLER FUNCTION - UPDATED
// ============================================================

async function handleEtsyWebhook(req, res, category) {
    try {
        console.log(`🔥 ETSY WEBHOOK RECEIVED for: ${category}`);
        console.log("📦 Full Payload:", JSON.stringify(req.body, null, 2));

        let datasetId = req.body.datasetId;

        // ✅ Handle Apify webhook format (ACTOR.RUN.SUCCEEDED)
        if (req.body.eventType === "ACTOR.RUN.SUCCEEDED" && req.body.eventData) {
            const runId = req.body.eventData.actorRunId;
            console.log(`📥 Run ID: ${runId}`);
            
            const runUrl = `https://api.apify.com/v2/actor-runs/${runId}?token=${APIFY_TOKEN}`;
            const runResponse = await axios.get(runUrl);
            datasetId = runResponse.data.data.defaultDatasetId;
            console.log(`📥 Dataset ID: ${datasetId}`);
        }

        if (!datasetId) {
            console.log("⚠️ No datasetId found");
            return res.status(200).send("OK - no datasetId");
        }

        // ✅ Fetch products from dataset
        const url = `https://api.apify.com/v2/datasets/${datasetId}/items?clean=true&token=${APIFY_TOKEN}`;
        const { data: items } = await axios.get(url);

        if (!items || items.length === 0) {
            console.log("⚠️ No items found");
            return res.status(200).send("No items found");
        }

        console.log(`📦 Etsy: ${items.length} items for category: ${category}`);

        // ✅ Send to backend - CSV + Raw Table save ho jayega
        await axios.post(BACKEND_URL, {
            category: category,
            keyword: category,
            products: items,
            platform: "etsy"
        }, { timeout: 60000 });

        console.log(`✅ Etsy forwarded for: ${category}`);
        res.status(200).send("OK");

    } catch (error) {
        console.error(`❌ Etsy WEBHOOK ERROR (${category}):`, error.message);
        res.status(500).send("Error: " + error.message);
    }
}

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