import os
import time
import httpx
import math
import asyncio

from kubernetes import client, config

NAMESPACE = os.environ.get("NAMESPACE", "default")
DEPLOYMENT_NAME = os.environ.get("DEPLOYMENT_NAME", "ml-app-deployment")
POD_LABEL = os.environ.get("POD_LABEL", "ml-app")
MIN_REPLICAS = int(os.environ.get("MIN_REPLICAS", 1))
MAX_REPLICAS = int(os.environ.get("MAX_REPLICAS", 6))
DESIRED_QUEUE_SIZE = int(os.environ.get("DESIRED_QUEUE_SIZE", 20))
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://monitoring-kube-prometheus-prometheus.monitoring.svc:9090")
COOLDOWN_SECONDS = int(os.environ.get("COOLDOWN_SECONDS", 30))

async def get_metrics(query):
    """Fetch metrics from Prometheus based on the provided query."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": query},
                timeout=5
            )
            response.raise_for_status()
            result = response.json()
            if result["status"] == "success" and result["data"]["result"]:
                return float(result["data"]["result"][0]["value"][1])
            return 0.0
    except Exception as e:
        print(f"Error fetching metrics from Prometheus: {e}")
        return None

async def check_replicas(v1_api):
    """Check if all pods in the deployment are ready."""

    try:
        pods = v1_api.list_namespaced_pod(
            namespace=NAMESPACE,
            label_selector=f"app={POD_LABEL}"
            )
        for pod in pods.items:
            for condition in pod.status.conditions or []:
                if condition.type == "Ready" and condition.status != "True":
                    return False

        return True
    except Exception as e:
        print(f"Error checking pod readiness: {e}")
        return False

async def scale_deployment(queue_size, v1_api):
    """Scale the deployment based on the current queue size and cooldown period."""

    global last_scale_time
    if time.time() - last_scale_time < COOLDOWN_SECONDS:
        print("Cooldown period active. Skipping scaling.")
        return

    if not await check_replicas(v1_api):
        print("Not all pods are ready. Skipping scaling.")
        return

    try:
        deployment = apps_v1.read_namespaced_deployment(DEPLOYMENT_NAME, NAMESPACE)
        current_replicas = deployment.spec.replicas
    except Exception as e:
        print(f"Error fetching deployment details: {e}")
        current_replicas = MIN_REPLICAS

    desired_replicas = current_replicas
    if queue_size is not None:
        if queue_size == 0:
            desired_replicas = MIN_REPLICAS
        elif queue_size > DESIRED_QUEUE_SIZE:
            desired_replicas = math.ceil(current_replicas * (queue_size / DESIRED_QUEUE_SIZE))
        elif queue_size <= DESIRED_QUEUE_SIZE:
            desired_replicas = max(MIN_REPLICAS, math.ceil(current_replicas - (queue_size / DESIRED_QUEUE_SIZE)))

        desired_replicas = max(MIN_REPLICAS, min(MAX_REPLICAS, desired_replicas))

    if desired_replicas != current_replicas:
        apps_v1.patch_namespaced_deployment_scale(
            name=DEPLOYMENT_NAME,
            namespace=NAMESPACE,
            body={"spec": {"replicas": desired_replicas}}
        )
        last_scale_time = time.time()

async def main():
    """Main function to fetch metrics and scale the deployment."""

    qsize = await get_metrics('dispatcher_queue_size{job="dispatcher-service", namespace="default"}')
    await scale_deployment(qsize, v1_api)

if __name__ == "__main__":
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    apps_v1 = client.AppsV1Api()
    v1_api = client.CoreV1Api()
    last_scale_time = 0
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            loop.run_until_complete(main())
        except Exception as e:
            print(f"Error in main loop: {e}")

        loop.run_until_complete(asyncio.sleep(5))