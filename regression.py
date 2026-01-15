from src import otava
import json
from datetime import datetime, timezone
import os
CURRENT_TIMEZONE = timezone.utc
webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
 
def get_date(time_val):
    dt_object = datetime.fromtimestamp(time_val, CURRENT_TIMEZONE)
    return dt_object.strftime("%Y-%m-%d")

def get_today():
    now = datetime.now(CURRENT_TIMEZONE)
    return now.strftime("%Y-%m-%d")

def send_slack_webhook(message):
    import requests
    if not webhook_url:
        print("SLACK_WEBHOOK_URL is not set. Skipping Slack notification.")
        return  
    payload = {"text": message}
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            print("✅ Slack notification sent successfully.")
        else:
            print(f"⚠️ Failed to send Slack notification. Status code: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Exception occurred while sending Slack notification: {e}")   

message=""
for config in ("otava-time.yaml", "otava-memory.yaml", "otava-cpu.yaml"):
    key=config.replace("otava-","").replace(".yaml","")
    
    for p in ("darwin-amd", "darwin-arm","linux-amd", "linux-arm", "windows-amd"):
        stdout = otava.run_otava(p, config, "json")
        data = json.loads(stdout)
        #print(data)
        changedata = data.get(p, [])
        
        for items in changedata:
            changes_list = items.get("changes", [])
            time = items.get("time", 0)
            changedate = get_date(time)

            if changedate == get_today():
                if(len(changes_list)>0):
                    message += f"CRC performance change found for `{key}` on `{p}` at {changedate}:\n"
                for change in changes_list:
                    message += f"{change.get('metric','')} : {round(float(change.get('mean_before','')), 2)} => {round(float(change.get('mean_after','')), 2)}\n"
                
if(message != ""):
    if "time-stop" in message:
        message += "https://crcqe-asia.s3.ap-south-1.amazonaws.com/nightly/crc/test/time-stop.png"+"\n"
    if "time-start" in message:
        message += "https://crcqe-asia.s3.ap-south-1.amazonaws.com/nightly/crc/test/time-start.png"+"\n"
    message += f"Check details in <https://crcqe-asia.s3.ap-south-1.amazonaws.com/nightly/crc/test/Performance_report.html|Performance Report>"
    send_slack_webhook(message)     