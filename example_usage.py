"""
Example usage of Zalo AI Broker Assistant

Demonstrates:
1. Processing customer messages
2. Extracting Vietnamese text data
3. Getting AI-generated reply suggestions
4. Managing follow-ups
"""

import requests
import json


# API base URL
BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")


def process_message(lead_id, message, is_broker=False):
    """Send a message to the API and get suggestions"""
    response = requests.post(
        f"{BASE_URL}/process",
        json={
            "lead_id": lead_id,
            "message": message,
            "is_broker": is_broker
        }
    )
    return response.json()


def main():
    print_section("Zalo AI Broker Assistant - Demo")
    
    # Example conversation
    lead_id = "demo_lead_001"
    
    # Customer message 1: Initial inquiry
    print_section("Step 1: Customer asks about property")
    customer_msg_1 = "Chào em, anh muốn tìm căn hộ 2PN ở Quận 2, tầm 2-3 tỷ"
    print(f"Customer: {customer_msg_1}\n")
    
    result1 = process_message(lead_id, customer_msg_1)
    
    print("📊 Extracted Information:")
    extracted = result1['extracted_data']
    print(f"  Budget: {extracted['budget_min']:,} - {extracted['budget_max']:,} VND")
    print(f"  Locations: {', '.join(extracted['locations'])}")
    print(f"  Intent: {extracted['intent']['value']}")
    print(f"  Interest Level: {extracted['interest_level']['value']}")
    
    print("\n🎯 Recommended Action:")
    action = result1['action']
    print(f"  Action: {action['action']}")
    print(f"  Priority: {action['priority']}")
    print(f"  Reasoning: {action['reasoning']}")
    
    print("\n💬 AI-Generated Reply Suggestions:")
    for i, suggestion in enumerate(result1['suggestions'], 1):
        print(f"\n  Option {i} (Confidence: {suggestion['confidence']*100:.0f}%):")
        print(f"  {suggestion['message']}")
        print(f"  Tactics: {', '.join(suggestion['tactics'])}")
    
    # Broker response
    print_section("Step 2: Broker sends reply")
    broker_msg = "Dạ chào anh, em có nhiều căn phù hợp với anh. Anh cần gấp không ạ?"
    print(f"Broker: {broker_msg}")
    process_message(lead_id, broker_msg, is_broker=True)
    
    # Customer message 2: More specific request
    print_section("Step 3: Customer provides more details")
    customer_msg_2 = "Anh đang tìm hiểu thôi, có căn nào view sông không em?"
    print(f"Customer: {customer_msg_2}\n")
    
    result2 = process_message(lead_id, customer_msg_2)
    
    print("📊 Updated Profile:")
    profile = result2['profile']
    print(f"  Interest Level: {profile['interest_level']} (was cold, now warm)")
    print(f"  Key Phrases: {', '.join(profile['key_phrases'])}")
    
    print("\n💬 New Reply Suggestions:")
    for i, suggestion in enumerate(result2['suggestions'], 1):
        print(f"\n  Option {i}:")
        print(f"  {suggestion['message']}")
    
    # Check follow-ups
    print_section("Step 4: Check follow-up tasks")
    response = requests.get(f"{BASE_URL}/follow-ups?hours=48")
    follow_ups = response.json()
    
    print(f"📅 Follow-ups in next 48 hours: {follow_ups['count']}")
    for task in follow_ups['tasks']:
        print(f"\n  Lead: {task['lead_id']}")
        print(f"  Scheduled: {task['scheduled_time']}")
        print(f"  Priority: {task['priority']}")
        print(f"  Action: {task['action']}")
    
    # Get hot leads
    print_section("Step 5: Check hot leads")
    response = requests.get(f"{BASE_URL}/leads/hot")
    hot_leads = response.json()
    
    print(f"🔥 Hot leads: {hot_leads['count']}")
    
    # Get stats
    print_section("Step 6: System statistics")
    response = requests.get(f"{BASE_URL}/stats")
    stats = response.json()
    
    print(f"📊 Total leads: {stats.get('total_leads', 0)}")
    print(f"   Hot: {stats.get('hot_leads', 0)}")
    print(f"   Warm: {stats.get('warm_leads', 0)}")
    print(f"   Cold: {stats.get('cold_leads', 0)}")
    
    print_section("Demo Complete!")
    print("Next steps:")
    print("1. Integrate with Zalo API webhooks")
    print("2. Add more message templates")
    print("3. Implement A/B testing for tactics")
    print("4. Connect to real customer conversations")
    print()


if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(BASE_URL)
        if response.status_code == 200:
            main()
        else:
            print("❌ Server not responding correctly")
    except requests.exceptions.ConnectionError:
        print("❌ Server not running!")
        print("Start it with: uvicorn main:app --reload")
