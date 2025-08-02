import os
import subprocess
import json

def run_cmd(cmd):
    debug_cmd = f"set -x; {cmd}"
    print(f"\n[DEBUG] Running command:\n{cmd}\n")

    result = subprocess.run(debug_cmd, shell=True, capture_output=True, text=True, executable="/bin/bash")

    print(f"[DEBUG] STDOUT:\n{result.stdout.strip()}")
    print(f"[DEBUG] STDERR:\n{result.stderr.strip()}")

    if result.returncode != 0:
        raise Exception(f"[ERROR] Command failed:\n{cmd}\n\nSTDERR:\n{result.stderr.strip()}")
    
    return result.stdout.strip()

def lambda_handler(event, context):
    region = os.environ.get("AWS_REGION", "us-west-1")
    cluster_name = os.environ.get("CLUSTER_NAME","fabulous-pop-mountain")

    try:
        # Set up kubeconfig
        print("Updating kubeconfig...")
        run_cmd(f"aws eks update-kubeconfig --name {cluster_name} --region {region} --kubeconfig /tmp/config ")

        # Get all namespaces
        print("Fetching namespaces...")
        namespaces = run_cmd("kubectl get ns -o jsonpath='{.items[*].metadata.name}'").split()

        response_data = []

        for ns in namespaces:
            ns_data = {
                "namespace": ns,
                "pods": []
            }

            try:
                pods = run_cmd(f"kubectl get pods -n {ns} -o jsonpath='{{.items[*].metadata.name}}'").split()

                for pod in pods:
                    try:
                        metrics = run_cmd(f"kubectl top pod {pod} -n {ns} --no-headers")
                        mem_usage = metrics.split()[2]  # Assuming: <name> <cpu> <memory>
                        pod_data = {
                            "pod_name": pod,
                            "memory_usage": mem_usage
                        }
                    except Exception as e:
                        pod_data = {
                            "pod_name": pod,
                            "error": f"Could not fetch metrics: {str(e)}"
                        }

                    ns_data["pods"].append(pod_data)

            except Exception as e:
                ns_data["error"] = f"Error fetching pods: {str(e)}"

            response_data.append(ns_data)

        return {
            "statusCode": 200,
            "body": json.dumps(response_data, indent=2)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "error": str(e)
        }
