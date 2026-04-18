const mongoose = require("mongoose");

// Replace <your_password> with the password you just created in Atlas
const MONGO_URI = "mongodb+srv://arobaarif271_db_user:arobaarif9852_db_user@cluster0.i8qzy2t.mongodb.net/?appName=Cluster0";

mongoose.connect(MONGO_URI); // no options needed

const db = mongoose.connection;

db.on("error", err => console.error("❌ MongoDB error:", err));

db.once("open", () => {
    console.log("✅ Connected to MongoDB Atlas");
});

module.exports = mongoose;