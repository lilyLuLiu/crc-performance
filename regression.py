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
                for change in changes_list:
                    message=f"change point found for {key} on {p} at {changedate}\n{change.get('metric','')} : {change.get('mean_before','')} => {change.get('mean_after','')}"
                    send_slack_webhook(message)
        