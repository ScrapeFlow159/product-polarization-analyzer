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

        // ✅ Category extract - Template variable handle karein
        let category = req.body.category;
        
        // ✅ Agar category template variable hai ({{...}}) toh input se lein
        if (!category || category.startsWith("{{")) {
            const inputData = req.body.input || {};
            category = inputData.category || inputData.searchKeyword || "unknown";
            console.log("📂 Category from input:", category);
        }
        
        // ✅ Agar phir bhi unknown hai toh ALL_INPUT se lein
        if (!category || category === "unknown" || category.startsWith("{{")) {
            const allInput = req.body.ALL_INPUT || {};
            if (typeof allInput === "string") {
                try {
                    const parsed = JSON.parse(allInput);
                    category = parsed.category || parsed.searchKeyword || "unknown";
                } catch {
                    category = "unknown";
                }
            } else {
                category = allInput.category || allInput.searchKeyword || "unknown";
            }
            console.log("📂 Category from ALL_INPUT:", category);
        }

        // ✅ Final fallback
        if (!category || category === "unknown" || category.startsWith("{{")) {
            category = "earpods";
            console.log("📂 Using fallback category:", category);
        }

        console.log(`📂 Final Category: ${category}`);

        const { datasetId } = req.body;
        if (!datasetId || datasetId.startsWith("{{")) {
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
app.post("/webhook/apify/etsy", async (req, res) => {
    try {
        console.log("🔥 ETSY WEBHOOK RECEIVED");
        console.log("📦 Full Payload:", JSON.stringify(req.body, null, 2));

        // ✅ Category extract - Template variable handle karein
        let category = req.body.category || req.body.keyword;
        
        // ✅ Agar category template variable hai ({{...}}) toh input se lein
        if (!category || category.startsWith("{{")) {
            const inputData = req.body.input || {};
            category = inputData.keyword || inputData.category || "unknown";
            console.log("📂 Category from input:", category);
        }
        
        // ✅ Agar phir bhi unknown hai toh ALL_INPUT se lein
        if (!category || category === "unknown" || category.startsWith("{{")) {
            const allInput = req.body.ALL_INPUT || {};
            if (typeof allInput === "string") {
                try {
                    const parsed = JSON.parse(allInput);
                    category = parsed.keyword || parsed.category || "unknown";
                } catch {
                    category = "unknown";
                }
            } else {
                category = allInput.keyword || allInput.category || "unknown";
            }
            console.log("📂 Category from ALL_INPUT:", category);
        }

        // ✅ Final fallback
        if (!category || category === "unknown" || category.startsWith("{{")) {
            category = "wall_art";
            console.log("📂 Using fallback category:", category);
        }

        console.log(`📂 Final Category: ${category}`);

        const { datasetId } = req.body;
        if (!datasetId || datasetId.startsWith("{{")) {
            return res.status(200).send("OK - no datasetId");
        }

        const url = `https://api.apify.com/v2/datasets/${datasetId}/items?clean=true&token=${APIFY_TOKEN}`;
        const { data: items } = await axios.get(url);

        if (!items || items.length === 0) {
            console.log("No items found");
            return res.status(200).send("No items found");
        }

        console.log(`📦 Etsy: ${items.length} items for category: ${category}`);

        await axios.post(BACKEND_URL, {
            category: category,
            keyword: category,
            products: items,
            platform: "etsy",
            input: req.body.input || {}
        }, { timeout: 60000 });

        console.log(`✅ Etsy forwarded`);
        res.status(200).send("OK");

    } catch (error) {
        console.error("❌ Etsy WEBHOOK ERROR:", error.message);
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