import os
import subprocess

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Error: {result.stderr}")
    return result.stdout.strip()

def lambda_handler(event, context):
    region = os.environ.get("AWS_REGION", "us-east-1")
    cluster_name = os.environ["CLUSTER_NAME"]

    # Step 1: Set up kubeconfig
    print("Setting up kubeconfig...")
    run_cmd(f"aws eks update-kubeconfig --name {cluster_name} --region {region}")

    # Step 2: Get namespaces
    print("Getting namespaces...")
    namespaces = run_cmd("kubectl get ns -o jsonpath='{.items[*].metadata.name}'").split()
    print(f"Namespaces: {namespaces}")

    for ns in namespaces:
        print(f"\nNamespace: {ns}")
        pods = run_cmd(f"kubectl get pods -n {ns} -o jsonpath='{{.items[*].metadata.name}}'").split()
        for pod in pods:
            print(f"  Pod: {pod}")
            try:
                mem = run_cmd(f"kubectl top pod {pod} -n {ns} --no-headers | awk '{{print $3}}'")
                print(f"    Memory usage: {mem}")
            except Exception as e:
                print(f"    Failed to get metrics for pod {pod}: {e}")

    return {"statusCode": 200, "body": "Metrics fetched"}
