const express = require("express");
const bodyParser = require("body-parser");
const axios = require("axios");
const { Parser } = require("json2csv");
const fs = require("fs");

const Item = require("./models/items");
require("./db");

const app = express();
app.use(bodyParser.json());

const APIFY_TOKEN = "apify_api_HlY6edMSwNJqptH4B2FWttNUIIbHKV0z1JTy";

// ✅ Webhook route
app.post("/webhook/apify/daraz", async (req, res) => {
    console.log("----- Webhook received -----");

    const { datasetId, eventType } = req.body;

    // Ignore test events
    if (!datasetId) {
        console.log("⚠️ Test webhook received");
        return res.status(200).send("OK");
    }

    console.log("Dataset ID:", datasetId);

    const url = `https://api.apify.com/v2/datasets/${datasetId}/items?clean=true&token=${APIFY_TOKEN}`;

    try {
        const response = await axios.get(url);
        const items = response.data;

        console.log(`Fetched ${items.length} items`);

        if (items.length > 0) {

            // ✅ CLEAN DATA (IMPORTANT)
            const cleanedItems = items.map(item => ({
                name: item.name,
                itemId: Number(item.itemId),
                price: Number(item.price),
                currentPrice: item.currentPrice,
                brandName: item.brandName,
                sellerName: item.sellerName,
                ratingScore: Number(item.ratingScore),
                itemSold: Number(item.itemSold),
                location: item.location,
                image: item.image,
                itemUrl: item.itemUrl
            }));

            // ✅ Save to MongoDB
            await Item.insertMany(cleanedItems);

            // ✅ Convert to CSV
            const fields = [
                "name","itemId","price","currentPrice",
                "brandName","sellerName","ratingScore",
                "itemSold","location","image","itemUrl"
            ];

            const parser = new Parser({ fields });
            const csv = parser.parse(cleanedItems);

            // ✅ Save CSV file
            fs.writeFileSync("../backend/data/latest_data.csv", csv);

            console.log("✅ CSV generated");
        }

    } catch (error) {
        console.error("❌ Error:", error.message);
    }

    res.status(200).send("OK");
});

app.listen(3000, () => {
    console.log("Server running on port 3000");
});