import time
from datetime import datetime, timedelta
from supabase import create_client
import app.config as config

supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

def is_in_analytics(device_id):
    # Check if the device is already in the analytics table
    query = f"SELECT COUNT(*) FROM analytics WHERE device_id = {device_id}"
    response = supabase.rpc("sql", {"query": query}).execute()
    return response.data[0]['count'] > 0


def insert_new_analytics_entry(household_code, device_id, user_id, start_time):
    # Insert a new row into the analytics table with start_time and date
    query = f"""INSERT INTO analytics (household_code, device_id, user_id, start_time, date)
    VALUES ({household_code}, {device_id}, {user_id}, '{start_time}', '{start_time.date()}')"""
    supabase.rpc("sql", {"query": query}).execute()


def update_device_wattage(device_id, power):
    # Update the wattage in the analytics table for the given device
    query = f"""
    UPDATE analytics
    SET wattage = wattage + {power}
    WHERE device_id = {device_id} AND end_time IS NULL
    """
    supabase.rpc("sql", {"query": query}).execute()


def get_off_devices_for_household(household_code):
    # Get the list of devices that have turned off for the given household
    query = f"SELECT device_id FROM devices WHERE household_code = {household_code} AND isOn = FALSE"
    response = supabase.rpc("sql", {"query": query}).execute()
    return response.data


def finalize_device_entry(device_id, end_time):
    # Finalize the entry in the analytics table by setting the end_time
    query = f"""
    UPDATE analytics
    SET end_time = '{end_time}'
    WHERE device_id = {device_id} AND end_time IS NULL"""
    supabase.rpc("sql", {"query": query}).execute()


def calculate_live_consumption(household_code):
    total_wattage = 0

    while True:
        query = f"SELECT device_id, power, user_id FROM devices WHERE household_code = {household_code} AND isOn = TRUE"
        response = supabase.rpc("sql", {"query": query}).execute()

        # Reset total wattage for each iteration
        total_wattage = 0

        # Fetch devices with matching household_code and isOn = TRUE
        for device in response.data:
            device_id = device["device_id"]
            user_id = device["user_id"]
            power = int((device["power"]).rstrip('W'))

            # If not in analytics, insert a new row with start_time and date
            if not is_in_analytics(device_id):
                insert_new_analytics_entry(
                    household_code, device_id, user_id, datetime.now()
                )
            
            # Update wattage in analytics
            update_device_wattage(device_id, power)

            # Increment total wattage
            total_wattage += power

        # Check if any devices have turned off and finalize those entries
        off_devices = get_off_devices_for_household(household_code)
        for device in off_devices:
            device_id = device["device_id"]
            finalize_device_entry(device_id, datetime.now())

        # Print the total wattage consumed
        print(f"Total wattage consumed: {total_wattage}W")

        # Wait for 5 seconds before the next iteration
        time.sleep(5)

    
    