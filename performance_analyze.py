from opensearchpy import OpenSearch
import pandas as pd
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import os
import shutil
import subprocess
from src import otava
import gc

OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST")  
USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")
RESULT_FOLDER = "result"

def connect_opensearch():
    # --- Create client ---
    client = OpenSearch(
        OPENSEARCH_HOST,
        http_auth=(USERNAME, PASSWORD),
        use_ssl=True,
        verify_certs=False,     # set False if using a self-signed certificate
        ssl_show_warn=False    # optional: hides SSL warnings if verify_certs=False
    )
    if client.ping():
        print("✅ Successfully connected to OpenSearch!")
    else:
        print("⚠️ Connection established but ping failed.")
        exit(1)

    index_name = "crc-test"
    query = {
        "size": 10000, 
        "query": {
            "wildcard": {
                "category.keyword": "openshift-*"   # use the .keyword field for exact matching
            }
        }
    }
    response = client.search(index=index_name, body=query)
    hits = [hit["_source"] for hit in response["hits"]["hits"]]
    print(f"Total {len(hits)} records")

    df = pd.DataFrame(hits)
    df["category"] = df["category"].astype("category")
    platform_map = {
        "openshift-darwin-amd64": "darwin-amd64",
        "openshift-darwin-arm64": "darwin-arm64",
        "openshift-linux-amd64": "linux-amd64",
        "openshift-linux-arm64": "linux-arm64",
        "openshift-windows-amd64": "windows-amd64",
    }
    df = df[df["category"].isin(platform_map.keys())]
    Platform_DATA = {
        platform_map[k]: v.reset_index(drop=True)
        for k, v in df.groupby("category", observed=True)
    }
    '''
    MAC_AMD_data = df[df['category'] == 'openshift-darwin-amd64']
    MAC_ARM_data = df[df['category'] == 'openshift-darwin-arm64']
    LINUX_AMD_data = df[df['category'] == 'openshift-linux-amd64']
    LINUX_ARM_data = df[df['category'] == 'openshift-linux-arm64']
    WINDOWS_data = df[df['category'] == 'openshift-windows-amd64']
    Platform_DATA={
        "darwin-amd64": MAC_AMD_data,
        "darwin-arm64": MAC_ARM_data,
        "linux-amd64": LINUX_AMD_data,
        "linux-arm64": LINUX_ARM_data,
        "windows-amd64": WINDOWS_data,
    }
    '''
    time_platform = time_by_platform(df)
    memory_platform = memory_by_platform(df)
    return time_platform, memory_platform, Platform_DATA

def export_time_csv(Platform_DATA):
    for key, value in Platform_DATA.items():
        cols = ["time-start", "time-stop", "bundle", "timestamp"]
        df_to_export = (
            value
            .loc[:, cols]                 
            .dropna(subset=["time-start"]) 
        )

        df_to_export.to_csv(
            f"{RESULT_FOLDER}/time_consume_{key}.csv",
            index=False
        )
        del df_to_export
        gc.collect()
        '''
        df_to_export = value[['time-start', 'time-stop', 'bundle', 'timestamp']].copy()
        df_to_export = df_to_export.dropna(subset=["time-start"])
        df_to_export.to_csv(f"{RESULT_FOLDER}/time_consume_{key}.csv", index=False)
        '''
def export_memory_csv(Platform_DATA):
    cols = [
        "memory-start",
        "memory-deployment",
        "memory-stop",
        "bundle",
        "timestamp",
    ]
    for key, value in Platform_DATA.items():
        df_to_export = (
            value
            .loc[:, cols]                       
            .dropna(subset=["memory-start"])   
        )
        df_to_export.to_csv(
            f"{RESULT_FOLDER}/memory_consume_{key}.csv",
            index=False
        )
        del df_to_export
        gc.collect()
        '''
        df_to_export = value[['memory-start', 'memory-deployment', 'memory-stop', 'bundle', 'timestamp']]
        df_to_export = df_to_export.dropna(subset=["memory-start"])
        df_to_export.to_csv(f"{RESULT_FOLDER}/memory_consume_{key}.csv", index=False)
        '''

def flatten_nested(obj):
    items = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = k
            if isinstance(v, (dict, list)):
                items.extend(flatten_nested(v).items())
            else:
                items.append((new_key, v))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key =  str(i)
            if isinstance(v, (dict, list)):
                items.extend(flatten_nested(v).items())
            else:
                items.append((new_key, v))
    return dict(items)

def get_cpu_data(item, Platform_DATA):#item list["cpu-Start","cpu-Stop"]
    CPU_data={}
    for key, value in Platform_DATA.items():
        mask = value[item].apply(lambda x: isinstance(x, dict) and "derived" in x)
        if not mask.any():
            continue
        filtered = value.loc[mask]
        derived_df = pd.json_normalize(
            filtered[item].map(lambda x: flatten_nested(x["derived"]))
        )
        derived_df = derived_df.assign(
            timestamp=filtered["timestamp"].values,
            bundle=filtered["bundle"].values,
            platform=key,
        )
        cpudata = derived_df.sort_values(
            "timestamp", kind="mergesort"
        ).reset_index(drop=True)
        
        CPU_data[key] = cpudata
    return CPU_data


def draw_by_platform(item, image_folder, data):
    plt.figure(figsize=(8, 5), dpi=150)
    for key, value in data.items():
        value = value.copy()
        value['timestamp'] = pd.to_datetime(value['timestamp'])
        plt.plot(value['timestamp'], value[item], label=key)

    plt.title(f"Performance {item} over Time")
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{image_folder}/{item}.png")
    plt.close()

def draw_all(Platform_DATA):
    draw_by_platform("time-start",RESULT_FOLDER, Platform_DATA)
    draw_by_platform("time-stop",RESULT_FOLDER, Platform_DATA)
    draw_by_platform("memory-start",RESULT_FOLDER, Platform_DATA)
    draw_by_platform("memory-stop",RESULT_FOLDER, Platform_DATA)
    draw_by_platform("memory-deployment",RESULT_FOLDER, Platform_DATA)


def sort_by_bundle(data,item):
    return data.groupby('bundle')[item].mean().reset_index().to_dict(orient='records')

def time_by_bundle(Platform_DATA):
    start_result={}
    stop_result={}
    for key, value in Platform_DATA.items():
        start_result[key]=sort_by_bundle(value,"time-start")
        conver_time_format(start_result[key],"time-start")
        stop_result[key]=sort_by_bundle(value,"time-stop")
        conver_time_format(stop_result[key],"time-stop")
    return start_result, stop_result

def memory_by_bundle(Platform_DATA):
    start_result={}
    deployment_result={}
    stop_result={}
    for key, value in Platform_DATA.items():
        start_result[key]=sort_by_bundle(value,"memory-start")
        deployment_result[key]=sort_by_bundle(value,"memory-deployment")
        stop_result[key]=sort_by_bundle(value,"memory-stop")
    return start_result, deployment_result, stop_result

def sort_by_platform(df,item):
    return df.groupby('category', observed=True)[item].mean().reset_index().to_dict(orient='records')

def time_by_platform(df):
    result={}
    for field in ("time-start", "time-stop"):
        data = sort_by_platform(df, field)
        conver_time_format(data, field)
        result[field.split("-")[1]] = data
    return result

def conver_time_format(datalist, item):
    for row in datalist:
        row[item] = seconds_to_mmss(row[item])

def seconds_to_mmss(seconds):
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    return f"{minutes}m{sec:02d}s"

def memory_by_platform(df):
    result={}
    for field, name in [
        ("memory-start", "start"),
        ("memory-deployment", "deployment"),
        ("memory-stop", "stop"),
    ]:
        result[name] = sort_by_platform(df, field)
    return result

def export_cpu_csv(Platform_DATA):
    folder="result"
    Path(folder).mkdir(parents=True, exist_ok=True)

    items = ["cpu-Start","cpu-Stop"]
    for item in items:
        cpudata = get_cpu_data(item, Platform_DATA)
        for key, _ in Platform_DATA.items(): 
            filtered_df = cpudata[key]
            filtered_df.to_csv(f"{folder}/{item}_{key}.csv", index=False)

def generate_html_report(time_platform, memory_platform, Platform_DATA, regression):
    start_time, stop_time = time_by_bundle(Platform_DATA)
    timeData = {
        "platform" : time_platform,
        "bundle": {
            "start": start_time,
            "stop": stop_time
        }
    }
    start, deploy, stop = memory_by_bundle(Platform_DATA)
    memoryData = {
        "platform" : memory_platform,
        "bundle": {
            "start": start,
            "stop": stop,
            "deployment": deploy
        }
    }



    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('ReportTemplate.html')
    html_output = template.render(timeData=timeData, memoryData=memoryData, regression=regression)

    with open(f"{RESULT_FOLDER}/Performance_report.html", 'w', encoding='utf-8') as f:
        f.write(html_output)
    print("✅ HTML file generated: Performance_report.html")

def otava_regression_check(config_path):
    RegressionResult = ""
    for p in ("darwin-amd", "darwin-arm","linux-amd", "linux-arm", "windows-amd"):
        stdout = otava.run_otava(p, config_path)
        RegressionResult += otava.handle_regression_result(stdout)+"\n"
    return RegressionResult

def get_regression_result():
    RegressionResult={}
    for config in ("otava-time.yaml", "otava-memory.yaml", "otava-cpu.yaml"):
        key=config.replace("otava-","").replace(".yaml","")
        RegressionResult[key] = otava_regression_check(config)
    return RegressionResult

if __name__ == "__main__":
    # Remove the result folder if it exists, then create it
    if os.path.exists(RESULT_FOLDER):
        shutil.rmtree(RESULT_FOLDER)
    os.makedirs(RESULT_FOLDER)

    time_platform, memory_platform, Platform_DATA = connect_opensearch()
    export_time_csv(Platform_DATA)
    export_memory_csv(Platform_DATA)
    export_cpu_csv(Platform_DATA)
    #draw_all(Platform_DATA)
    regression = get_regression_result()
    generate_html_report(time_platform, memory_platform, Platform_DATA, regression)
    