from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import os
import json
import urllib.request
import urllib.error
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Railway Environment Variable se URL lo
API_BASE_URL = os.getenv("API_BASE_URL", "https://your-main-app.up.railway.app")

PLATFORMS = {
    "daraz": ["earpods", "powerbanks", "gaming_accessories", "mobile_phone_accessories", "smart_watches"],
    "etsy": [
        "custom wooden cake topper",
        "hand stitched leather bookmark", 
        "personalized brass pet tag",
        "custom embroidered baby onesie",
        "personalized wax seal stamp"
    ]
}

def run_daily_analysis():
    """Daily analysis for all categories"""
    logging.info(f"🚀 Daily Analysis Started at {datetime.now()}")
    success, failed = 0, 0
    
    for platform, categories in PLATFORMS.items():
        for category in categories:
            try:
                url = f"{API_BASE_URL}/api/analyze-public"
                
                payload = {
                    "platform": platform,
                    "category": category,
                    "subcategory": category,
                    "max_products": 100,
                    "analysis_type": "current",
                    "save_to_db": True,
                    "k_value": None,
                    "weights": None
                }
                
                data = json.dumps(payload).encode('utf-8')
                
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=180) as response:
                    if response.status == 200:
                        result = json.loads(response.read().decode())
                        score = result.get('polarization_score', 'N/A')
                        logging.info(f"✅ SUCCESS {platform}/{category} → Score: {score}")
                        success += 1
                    else:
                        logging.error(f"❌ FAILED {platform}/{category} → Status: {response.status}")
                        failed += 1
                        
            except Exception as e:
                logging.error(f"❌ ERROR {platform}/{category} → {str(e)}")
                failed += 1
    
    logging.info(f"📊 Daily Analysis Completed → Success: {success} | Failed: {failed}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_daily_analysis,
        'cron',
        hour=2, minute=0,   # Raat 2 baje
        id='daily_analysis',
        replace_existing=True
    )
    scheduler.start()
    logging.info("✅ Scheduler Started Successfully - Daily at 2:00 AM")
    return scheduler


# Direct run karne ke liye (Railway ke liye zaroori)
if __name__ == "__main__":
    scheduler = start_scheduler()
    print("🟢 Scheduler is running... (Press Ctrl+C to stop)")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("⛔ Shutting down scheduler...")