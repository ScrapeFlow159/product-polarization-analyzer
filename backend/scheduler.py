import threading
import time
from datetime import datetime, timedelta
import requests
import json

class PolarizationScheduler:
    """Scheduler for automatic weekly data collection"""
    
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.is_running = False
        self.thread = None
        self.categories = {
            'daraz': ['earpods', 'powerbanks', 'gaming_accessories', 'mobile_phone_accessories', 'smart_watches'],
            'etsy': ['art', 'handmade', 'jewelry', 'vintage', 'accessories']
        }
    
    def start(self):
        """Start the scheduler"""
        self.is_running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        print("📅 Weekly collection scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        print("📅 Weekly collection scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.is_running:
            now = datetime.now()
            
            # Check if it's Sunday at midnight (00:00)
            if now.weekday() == 6 and now.hour == 0 and now.minute == 0:
                print(f"\n📊 Running weekly data collection at {now}")
                self.collect_weekly_data()
                # Wait 24 hours before next check
                time.sleep(86400)
            else:
                # Check every hour
                time.sleep(3600)
    
    def collect_weekly_data(self):
        """Collect weekly data for all categories"""
        for platform, categories in self.categories.items():
            for category in categories:
                try:
                    print(f"  📡 Collecting {platform}/{category}...")
                    
                    response = requests.post(
                        f"{self.api_url}/api/analyze-and-save",
                        json={
                            'platform': platform,
                            'category': category,
                            'subcategory': category,
                            'analysis_type': 'weekly',
                            'max_products': 50,
                            'save_to_db': True
                        },
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        print(f"    ✅ Successfully saved {platform}/{category}")
                    else:
                        print(f"    ❌ Failed: {response.status_code}")
                        
                except Exception as e:
                    print(f"    ❌ Error: {str(e)}")
                
                # Small delay between requests
                time.sleep(2)
        
        print(f"✅ Weekly collection completed at {datetime.now()}")

# Global scheduler instance
scheduler = PolarizationScheduler()

def start_scheduler():
    """Start the background scheduler"""
    scheduler.start()

def stop_scheduler():
    """Stop the background scheduler"""
    scheduler.stop()