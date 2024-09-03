import requests
import os
import datetime

#TODO security check integrity and signature of the code

def get_github_file_last_modified(raw_url):
    try:
        # Send a HEAD request to get the headers of the file
        response = requests.head(raw_url)
        if response.status_code == 200:
            # Get the Last-Modified header
            last_modified_str = response.headers.get('Last-Modified')
            if last_modified_str:
                # Convert the Last-Modified string to a datetime object
                last_modified = datetime.datetime.strptime(last_modified_str, '%a, %d %b %Y %H:%M:%S %Z')
                return last_modified
    except Exception as e:
        print(f"An error occurred while fetching the last modified date: {e}")

    return None

def update_script_if_newer(raw_url, local_path):
    # Get the last modified date of the file on GitHub
    github_last_modified = get_github_file_last_modified(raw_url)
    if github_last_modified:
        print(f"GitHub file last modified date: {github_last_modified}")

        # Get the last modified date of the local file
        if os.path.exists(local_path):
            local_last_modified_timestamp = os.path.getmtime(local_path)
            local_last_modified = datetime.datetime.fromtimestamp(local_last_modified_timestamp)
            print(f"Local file last modified date: {local_last_modified}")

            # Compare the dates
            if local_last_modified >= github_last_modified:
                print("Local file is up-to-date. No need to update.")
                return

    # If local file does not exist or is older, download and update it
    try:
        response = requests.get(raw_url)
        if response.status_code == 200:
            with open(local_path, 'w') as file:
                file.write(response.text)
            print(f"Successfully updated {local_path}")
        else:
            print(f"Failed to download file. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred while downloading the file: {e}")


raw_url = "https://raw.githubusercontent.com/samwithbeard/serial_logger/main/serial_logger.py"
local_path = "/home/pi/serial_logger/serial_logger.py"

update_script_if_newer(raw_url, local_path)