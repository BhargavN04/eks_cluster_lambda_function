import boto3
import os
from kubernetes import client, config
from kubernetes.stream import stream

def get_eks_cluster_credentials(cluster_name, region):
    eks = boto3.client("eks", region_name=region)
    cluster_info = eks.describe_cluster(name=cluster_name)
    return cluster_info['cluster']

def configure_k8s_client(cluster_info):
    # Use boto3 to get token
    import botocore
    from botocore.signers import RequestSigner

    def get_token(cluster_name, region):
        session = botocore.session.get_session()
        client = session.create_client("sts", region_name=region)
        signer = RequestSigner(
            service_id="sts",
            region_name=region,
            signing_name="sts",
            signature_version="v4",
            credentials=client._request_signer._credentials,
            event_emitter=client.meta.events,
        )

        request = signer.generate_presigned_url(
            request_dict={
                "method": "GET",
                "url_path": "/?Action=GetCallerIdentity&Version=2011-06-15",
                "body": {},
                "headers": {},
                "query_string": {},
            },
            expires_in=60,
            operation_name="GetCallerIdentity"
        )

        return f"k8s-aws-v1.{request.encode('utf-8').decode('utf-8')}"

    configuration = client.Configuration()
    configuration.host = cluster_info["endpoint"]
    configuration.verify_ssl = True
    configuration.ssl_ca_cert = "/tmp/ca.crt"
    
    with open("/tmp/ca.crt", "w") as f:
        f.write(cluster_info["certificateAuthority"]["data"])

    token = get_token(cluster_info["name"], cluster_info["arn"].split(":")[3])
    configuration.api_key = {"authorization": "Bearer " + token}
    client.Configuration.set_default(configuration)

def lambda_handler(event, context):
    cluster_name = os.environ.get("CLUSTER_NAME")
    region = os.environ.get("AWS_REGION")

    cluster_info = get_eks_cluster_credentials(cluster_name, region)
    configure_k8s_client(cluster_info)

    v1 = client.CoreV1Api()
    print("Fetching all namespaces...")
    namespaces = v1.list_namespace().items

    for ns in namespaces:
        ns_name = ns.metadata.name
        print(f"\nNamespace: {ns_name}")
        pods = v1.list_namespaced_pod(ns_name).items

        for pod in pods:
            pod_name = pod.metadata.name
            print(f"  Pod: {pod_name}")

    try:
        metrics_api = client.CustomObjectsApi()
        for ns in namespaces:
            ns_name = ns.metadata.name
            pod_metrics = metrics_api.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=ns_name,
                plural="pods"
            )
            for pod_metric in pod_metrics["items"]:
                pod_name = pod_metric["metadata"]["name"]
                containers = pod_metric["containers"]
                for c in containers:
                    name = c["name"]
                    memory = c["usage"]["memory"]
                    print(f"Pod: {pod_name}, Container: {name}, Memory: {memory}")
    except Exception as e:
        print("Error fetching metrics:", e)

    return {"statusCode": 200, "body": "Success"}
