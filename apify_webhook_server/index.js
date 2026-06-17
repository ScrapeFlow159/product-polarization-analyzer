const express = require("express");
const bodyParser = require("body-parser");
const axios = require("axios");
const { Parser } = require("json2csv");
const fs = require("fs");
const path = require("path");

const app = express();
app.use(bodyParser.json());

const APIFY_TOKEN = "apify_api_HlY6edMSwNJqptH4B2FWttNUIIbHKV0z1JTy";

// Error handlers to prevent crash
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

        // Fetch dataset items from Apify
        const url = `https://api.apify.com/v2/datasets/${datasetId}/items?clean=true&token=${APIFY_TOKEN}`;
        const { data: items } = await axios.get(url);

        if (!items || items.length === 0) {
            console.log("No items found in dataset");
            return res.status(200).send("No items found");
        }

        console.log(`📦 Received ${items.length} items for category: ${category}`);

        // Clean data for CSV
        const cleanedItems = items.map(item => ({
            name: item.name || '',
            itemId: item.itemId || '',
            price: item.price || item.currentPrice || 0,
            currentPrice: item.currentPrice || '',
            brandName: item.brandName || '',
            sellerName: item.sellerName || '',
            ratingScore: item.ratingScore || item.rating || 0,
            itemSold: item.itemSold || item.sold || 0,
            location: item.location || '',
            image: item.image || '',
            itemUrl: item.itemUrl || ''
        }));

        // Create CSV
        const fields = ["name", "itemId", "price", "currentPrice", "brandName", "sellerName", "ratingScore", "itemSold", "location", "image", "itemUrl"];
        const json2csvParser = new Parser({ fields });
        const csv = json2csvParser.parse(cleanedItems);

        // Ensure directory exists (backend/data folder)
        const dir = path.join(__dirname, "..", "backend", "data");
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
            console.log(`📁 Created directory: ${dir}`);
        }

        // Save CSV file
        const filePath = path.join(dir, `${category}.csv`);
        fs.writeFileSync(filePath, csv);

        console.log(`✅ CSV CREATED: ${filePath} with ${cleanedItems.length} items`);
        console.log(`   Category: ${category}`);
        console.log(`   File size: ${(csv.length / 1024).toFixed(2)} KB`);

        res.status(200).send("OK");

    } catch (error) {
        console.error("❌ WEBHOOK ERROR:", error.message);
        console.error(error.stack);
        res.status(500).send("Error: " + error.message);
    }
});

// Debug endpoint to test webhook
app.post("/webhook/apify/debug", async (req, res) => {
    console.log("🔍 DEBUG - Webhook payload received");
    console.log(JSON.stringify(req.body, null, 2));
    res.status(200).send("Logged");
});

// Health check endpoint
app.get("/health", (req, res) => {
    res.status(200).send("OK");
});

app.listen(3000, () => {
    console.log("🚀 Apify Webhook Server running on port 3000");
    console.log("   Webhook URL: http://localhost:3000/webhook/apify/daraz");
});