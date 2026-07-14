import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import os
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_BASE_URL = os.getenv("API_BASE_URL", "https://product-polarization-analyzer-production.up.railway.app")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "daily_analysis_key")

PLATFORMS = {
    "daraz": ["earpods", "powerbanks", "gaming_accessories", "mobile_phone_accessories", "smart_watches"],
    "etsy": ["wall art", "handmade gifts", "jewelry", "vintage", "accessories"]
}

def run_daily_analysis():
    logging.info(f"🚀 Daily Analysis Started at {datetime.now()}")
    success, failed = 0, 0
    
    for platform, categories in PLATFORMS.items():
        for category in categories:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/analyze-internal",
                    json={
                        "platform": "DARAZ.PK" if platform == "daraz" else "ETSY.COM",
                        "category": category,
                        "subcategory": category,
                        "max_products": 100,
                        "analysis_type": "current",
                        "save_to_db": True,
                        "k_value": None,
                        "weights": None
                    },
                    headers={"Content-Type": "application/json", "X-API-Key": INTERNAL_API_KEY},
                    timeout=120
                )
                if response.status_code == 200:
                    logging.info(f"✅ {platform}/{category} - Score: {response.json().get('polarization_score', 'N/A')}")
                    success += 1
                else:
                    logging.error(f"❌ {platform}/{category} - Failed: {response.status_code}")
                    failed += 1
            except Exception as e:
                logging.error(f"❌ {platform}/{category} - Error: {e}")
                failed += 1
    
    logging.info(f"📊 Complete - Success: {success}, Failed: {failed}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_daily_analysis, 'cron', hour=2, minute=0)
    scheduler.start()
    logging.info("✅ Daily Scheduler Started - 2:00 AM Daily")
    return scheduler