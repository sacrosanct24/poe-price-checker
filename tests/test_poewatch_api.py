"""
Test script for poe.watch API integration.

This script tests the poe.watch API endpoints to evaluate
if it can be added as an additional pricing data source.
"""

import requests


class PoeWatchAPI:
    """Simple wrapper for poe.watch API endpoints."""
    
    BASE_URL = "https://api.poe.watch"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PoE-Price-Checker-Test/1.0 (testing poe.watch integration)'
        })
    
    def get_leagues(self):
        """Get available leagues."""
        response = self.session.get(f"{self.BASE_URL}/leagues")
        response.raise_for_status()
        return response.json()
    
    def get_categories(self):
        """Get available item categories."""
        response = self.session.get(f"{self.BASE_URL}/categories")
        response.raise_for_status()
        return response.json()
    
    def get_items(self, league, category, **filters):
        """
        Get items by league and category.
        
        Args:
            league: League name (e.g., "Standard", "Necropolis")
            category: Category name (e.g., "currency", "unique")
            **filters: Optional filters (lowConfidence, linkCount, gemLevel, etc.)
        """
        params = {
            'league': league,
            'category': category,
            **filters
        }
        response = self.session.get(f"{self.BASE_URL}/get", params=params)
        response.raise_for_status()
        return response.json()
    
    def search_items(self, league, query):
        """Search for items by name."""
        params = {'league': league, 'q': query}
        response = self.session.get(f"{self.BASE_URL}/search", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_item_history(self, league, item_id):
        """Get price history for a specific item."""
        params = {'league': league, 'id': item_id}
        response = self.session.get(f"{self.BASE_URL}/history", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_enchants(self, league, item_id):
        """Get enchantment data for an item."""
        params = {'league': league, 'id': item_id}
        response = self.session.get(f"{self.BASE_URL}/enchants", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_corruptions(self, league, item_id):
        """Get corruption data for an item."""
        params = {'league': league, 'id': item_id}
        response = self.session.get(f"{self.BASE_URL}/corruptions", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_compact_data(self, league):
        """Get compact data for all items in a league."""
        params = {'league': league}
        response = self.session.get(f"{self.BASE_URL}/compact", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_status(self):
        """Get API status."""
        response = self.session.get(f"{self.BASE_URL}/status")
        response.raise_for_status()
        return response.json()


def test_poewatch_api():
    """Run tests on poe.watch API."""
    
    print("="*70)
    print("Testing poe.watch API Integration")
    print("="*70)
    
    api = PoeWatchAPI()
    
    # Test 1: Get Leagues
    print("\n[TEST 1] Getting available leagues...")
    try:
        leagues = api.get_leagues()
        print(f"[OK] Found {len(leagues)} leagues")

        # Find current league
        current_leagues = [league for league in leagues if league['end_date'].startswith('0001')]
        print(f"  Current/Permanent leagues: {[league['name'] for league in current_leagues[:5]]}")
        
        # Use Standard for testing
        test_league = "Standard"
        print(f"\n  Using '{test_league}' for tests")
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        return
    
    # Test 2: Get Categories
    print("\n[TEST 2] Getting item categories...")
    try:
        categories = api.get_categories()
        print(f"[OK] Found {len(categories)} categories")
        print(f"  Categories: {', '.join([c['name'] for c in categories[:10]])}")
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        return
    
    # Test 3: Get Currency Prices
    print("\n[TEST 3] Getting currency prices...")
    try:
        currency = api.get_items(test_league, "currency")
        print(f"[OK] Found {len(currency)} currency items")

        # Show Divine Orb price
        divine = next((c for c in currency if c['name'] == 'Divine Orb'), None)
        if divine:
            print("\n  Divine Orb:")
            print(f"    Mean: {divine['mean']} chaos")
            print(f"    Min: {divine['min']} chaos")
            print(f"    Max: {divine['max']} chaos")
            print(f"    Daily listings: {divine['daily']}")
            print(f"    Low confidence: {divine['lowConfidence']}")
    except Exception as e:
        print(f"[FAIL] Failed: {e}")

    # Test 4: Search for Specific Item
    print("\n[TEST 4] Searching for 'Headhunter'...")
    try:
        results = api.search_items(test_league, "Headhunter")
        if results:
            item = results[0]
            print(f"[OK] Found: {item['name']}")
            print(f"  Category: {item['category']}")
            print(f"  Mean price: {item['mean']} chaos")
            print(f"  Price range: {item['min']} - {item['max']} chaos")
            print(f"  Item ID: {item['id']}")
            
            # Save ID for next test
            test_item_id = item['id']
        else:
            print("  No results found")
            test_item_id = None
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        test_item_id = None
    
    # Test 5: Get Price History
    if test_item_id:
        print(f"\n[TEST 5] Getting price history for item ID {test_item_id}...")
        try:
            history = api.get_item_history(test_league, test_item_id)
            print(f"[OK] Found {len(history)} history entries")
            if len(history) >= 3:
                print("\n  Recent prices:")
                for entry in history[-3:]:
                    date = entry['date'][:10]  # Just the date part
                    print(f"    {date}: {entry['mean']:.2f} chaos")
        except Exception as e:
            print(f"[FAIL] Failed: {e}")

    # Test 6: Get Unique Items (with filters)
    print("\n[TEST 6] Getting 6-link unique body armours...")
    try:
        uniques = api.get_items(test_league, "armour", linkCount=6)
        print(f"[OK] Found {len(uniques)} items")

        if uniques:
            # Show top 3 by price
            sorted_uniques = sorted(uniques, key=lambda x: x['mean'], reverse=True)[:3]
            print("\n  Top 3 most expensive:")
            for item in sorted_uniques:
                print(f"    {item['name']}: {item['mean']:.2f} chaos")
    except Exception as e:
        print(f"[FAIL] Failed: {e}")

    # Test 7: Get API Status
    print("\n[TEST 7] Getting API status...")
    try:
        status = api.get_status()
        print("[OK] API Status:")
        print(f"  Change ID: {status['changeID']}")
        print(f"  Requested stashes: {status['requestedStashes']}")
        print(f"  Computed stashes: {status['computedStashes']}")
        print(f"  Success rate: {status['computedStashes']/status['requestedStashes']*100:.1f}%")
    except Exception as e:
        print(f"[FAIL] Failed: {e}")

    # Test 8: Compare data structure to poe.ninja
    print("\n[TEST 8] Data structure comparison...")
    try:
        # Get a currency item
        currency = api.get_items(test_league, "currency")
        chaos = next((c for c in currency if c['name'] == 'Chaos Orb'), None)
        
        if chaos:
            print("\n  poe.watch item structure:")
            print(f"    [+] Has 'mean' price: {chaos.get('mean')}")
            print(f"    [+] Has 'min' price: {chaos.get('min')}")
            print(f"    [+] Has 'max' price: {chaos.get('max')}")
            print(f"    [+] Has 'history' array: {len(chaos.get('history', []))} entries")
            print(f"    [+] Has 'daily' count: {chaos.get('daily')}")
            print(f"    [+] Has 'lowConfidence' flag: {chaos.get('lowConfidence')}")
            print(f"    [+] Has 'icon' URL: {chaos.get('icon')[:50]}...")

            print("\n  Additional fields:")
            print(f"    - Exalted ratio: {chaos.get('exalted')}")
            print(f"    - Change %: {chaos.get('change')}")
            print(f"    - Mode price: {chaos.get('mode')}")
    except Exception as e:
        print(f"[FAIL] Failed: {e}")

    print("\n" + "="*70)
    print("Integration Assessment")
    print("="*70)
    
    print("\n[+] PROS:")
    print("  - Simple, well-documented API")
    print("  - Good price statistics (mean, min, max, mode)")
    print("  - Historical data available")
    print("  - Enchantment & corruption data (unique feature!)")
    print("  - Low confidence flagging")
    print("  - No authentication required")
    print("  - Search functionality")
    
    print("\n[-] CONS:")
    print("  - Requires item ID for history/enchants/corruptions")
    print("  - Less popular than poe.ninja (potentially less data)")
    print("  - Unclear update frequency")
    print("  - 'Enchants' endpoint marked as deprecated")
    
    print("\n[!] RECOMMENDATION:")
    print("  YES - Add as secondary data source for:")
    print("    1. Cross-validation of poe.ninja prices")
    print("    2. Enchantment/corruption data (unique feature)")
    print("    3. Additional confidence through multiple sources")
    print("    4. Fallback when poe.ninja is unavailable")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    try:
        test_poewatch_api()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n[FAIL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
