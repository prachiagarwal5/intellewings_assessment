#!/usr/bin/env python3
"""
Query and display scraped profile data from MongoDB
"""
from src.db import profiles_collection
import json
from datetime import datetime

def display_profiles():
    try:
        # Get all profiles from database
        profiles = list(profiles_collection.find())
        
        print(f"Found {len(profiles)} profiles in database\n")
        
        if not profiles:
            print("No profiles found. Run the scraper first.")
            return
        
        # Display each profile
        for i, profile in enumerate(profiles, 1):
            print(f"{'='*60}")
            print(f" PROFILE {i}")
            print(f"{'='*60}")
            
            # Basic information
            print(f" Name: {profile.get('name', 'N/A')}")
            print(f" Website: {profile.get('website', 'N/A')}")
            print(f" Authority: {profile.get('authority', 'N/A')}")
            print(f" Date: {profile.get('date', 'N/A')}")
            print(f" Status: {profile.get('status', 'N/A')}")
            
            # Violation and actions
            print(f" Nature of Violation: {profile.get('nature_of_violation', 'N/A')}")
            print(f"Actions Taken: {profile.get('actions_taken', 'N/A')}")
            
            # Additional metadata
            metadata = profile.get('additional_metadata', {})
            if metadata:
                print(f" Region: {metadata.get('region', 'N/A')}")
                print(f" Source: {metadata.get('source', 'N/A')}")
                
                if metadata.get('scraped_at'):
                    scraped_time = datetime.fromtimestamp(metadata['scraped_at'])
                    print(f"Scraped At: {scraped_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            print()  # Empty line between profiles
        
        # Summary statistics
        print(f"{'='*60}")
        print(f" SUMMARY STATISTICS")
        print(f"{'='*60}")
        
        # Count by authority
        authority_counts = {}
        region_counts = {}
        
        for profile in profiles:
            authority = profile.get('authority', 'Unknown')
            authority_counts[authority] = authority_counts.get(authority, 0) + 1
            
            region = profile.get('additional_metadata', {}).get('region', 'Unknown')
            region_counts[region] = region_counts.get(region, 0) + 1
        
        print(" By Authority:")
        for authority, count in sorted(authority_counts.items()):
            print(f"   {authority}: {count}")
        
        print("\n By Region:")
        for region, count in sorted(region_counts.items()):
            print(f"   {region}: {count}")
        
        # Export to JSON for further analysis
        export_data = []
        for profile in profiles:
            # Convert ObjectId to string for JSON serialization
            profile_copy = profile.copy()
            profile_copy['_id'] = str(profile_copy['_id'])
            export_data.append(profile_copy)
        
        with open('extracted_profiles.json', 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n Data exported to 'extracted_profiles.json'")
        
    except Exception as e:
        print(f" Error querying database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    display_profiles()
