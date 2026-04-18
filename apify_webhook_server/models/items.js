const mongoose = require("mongoose");

const itemSchema = new mongoose.Schema({}, { strict: false });

module.exports = mongoose.model("Item", itemSchema);