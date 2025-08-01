import os
import subprocess
import json
import re
from collections import defaultdict

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Error running command `{cmd}`: {result.stderr}")
    return result.stdout.strip()

def parse_kubectl_top_output(output):
    metrics = {}
    lines = output.strip().splitlines()
    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            pod_name = parts[0]
            cpu = parts[1]
            memory = parts[2]
            metrics[pod_name] = {"cpu": cpu, "memory": memory}
    return metrics

def get_workload_prefix(pod_name):
    # Remove replica hash and suffix (e.g. deployment-1234567890-abcde -> deployment)
    return "-".join(pod_name.split("-")[:-2])

def lambda_handler(event, context):
    region = os.environ.get("AWS_REGION", "us-east-1")
    cluster_name = os.environ["CLUSTER_NAME"]

    print("Setting up kubeconfig...")
    run_cmd(f"aws eks update-kubeconfig --name {cluster_name} --region {region}")

    print("Getting namespaces...")
    namespaces = run_cmd("kubectl get ns -o jsonpath='{.items[*].metadata.name}'").split()

    result_json = {}

    for ns in namespaces:
        print(f"\nProcessing namespace: {ns}")
        try:
            top_output = run_cmd(f"kubectl top pod -n {ns} --no-headers")
        except Exception as e:
            print(f"  Skipping metrics collection for namespace '{ns}' due to error: {e}")
            continue

        pod_metrics = parse_kubectl_top_output(top_output)
        grouped_data = defaultdict(lambda: {
            "replica_count": 0,
            "total_cpu": 0,
            "total_memory": 0,
            "pods": []
        })

        for pod_name, usage in pod_metrics.items():
            prefix = get_workload_prefix(pod_name)
            cpu = usage["cpu"]
            memory = usage["memory"]

            # Convert CPU to millicores
            cpu_val = int(cpu.replace("m", "")) if "m" in cpu else int(cpu) * 1000
            # Convert Memory to MiB
            if "Ki" in memory:
                mem_val = int(int(memory.replace("Ki", "")) / 1024)
            elif "Mi" in memory:
                mem_val = int(memory.replace("Mi", ""))
            elif "Gi" in memory:
                mem_val = int(memory.replace("Gi", "")) * 1024
            else:
                mem_val = 0  # fallback

            grouped_data[prefix]["replica_count"] += 1
            grouped_data[prefix]["total_cpu"] += cpu_val
            grouped_data[prefix]["total_memory"] += mem_val
            grouped_data[prefix]["pods"].append({
                "name": pod_name,
                "cpu": cpu,
                "memory": memory
            })

        # Convert totals back to readable format
        ns_result = {}
        for group, data in grouped_data.items():
            data["total_cpu"] = f'{data["total_cpu"]}m'
            data["total_memory"] = f'{data["total_memory"]}Mi'
            ns_result[group] = data

        result_json[ns] = ns_result

    print("Final JSON:")
    print(json.dumps(result_json, indent=2))
    return {
        "statusCode": 200,
        "body": json.dumps(result_json)
    }
