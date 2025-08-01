#!/usr/bin/env python3
"""
Reset checkpoint and check database status
"""
from src.db import profiles_collection, checkpoint_collection

def reset_and_check():
    print("🔍 Checking current status...")
    
    # Check current checkpoint
    checkpoint = checkpoint_collection.find_one({"type": "profile"})
    if checkpoint:
        print(f" Current checkpoint: {checkpoint}")
    else:
        print(" No checkpoint found")
    
    # Count profiles in database
    profile_count = profiles_collection.count_documents({})
    print(f"Profiles in database: {profile_count}")
    
    # Reset checkpoint if needed
    reset = input("\n Reset checkpoint to start from beginning? (y/n): ").lower().strip()
    if reset == 'y':
        checkpoint_collection.delete_many({"type": "profile"})
        print("Checkpoint reset")
    
    # Clear database if needed
    clear = input("Clear existing profiles from database? (y/n): ").lower().strip()
    if clear == 'y':
        result = profiles_collection.delete_many({})
        print(f"Deleted {result.deleted_count} profiles")

if __name__ == "__main__":
    reset_and_check()
