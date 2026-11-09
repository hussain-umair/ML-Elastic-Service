# ML-Elastic-Service

An **elastic Machine Learning (ML) inference service** deployed on **Minikube / Kubernetes** using a core **Producer-Consumer architecture** to handle dynamic inference request traffic.

---

## 📐 Architecture Diagram
View the full architecture diagram and design documentation in the project wiki: 👉 **[ML-Elastic-Service Architecture Diagram Wiki](https://github.com/hussain-umair/ML-Elastic-Service/wiki/Architecture_diagram)**

---

## 📂 Repository Structure
The repository consists of the following core services and components:

| Component / File | Description | 
| :--- | :--- | 
| **dispatcher/**         | Manages incoming inference request dispatching and queue logic between producers and consumer workers. | 
| **ml\_app/**            | The core Machine Learning inference worker service handling prediction models. |
| **custom_autos_caler/** | Custom autoscaling service that dynamically adjusts worker pod counts based on custom workload queue metrics. |
| **load_tester/**        | Load testing toolkit to simulate concurrent client requests and evaluate autoscaler responsiveness under stress. |
| **hpa\70.yaml**         | Kubernetes Horizontal Pod Autoscaler (HPA) specification configured with a 70% CPU/workload target threshold. |
| **custom_autoscaler_metrics.png** | Metrics graph visualization showing system scaling behavior under test traffic. |

---

## 🛠️ Prerequisites
Before running the project locally, ensure you have the following installed:
- **Python 3.x**
- **Docker**
- **Minikube** & **kubectl**
---

## 🚀 Step-by-Step Guide to Run the Project
### Step 1: Clone the Repository 
```bash
git clone https://github.com/hussain-umair/ML-Elastic-Service.git
cd ML-Elastic-Service
```

### Step 2: Start Minikube &amp; Configure Docker Environment
Start your local Minikube cluster and direct your terminal's Docker CLI to use Minikube's built-in Docker daemon:
```
minikube start
eval $(minikube docker-env)
```


### Step 3: Build Container Images
Build the Docker images for the dispatcher, ML inference app, and custom autoscaler:

# Build ML App worker image
```
docker build -t ml-app:latest ./ml_app
```
# Build Dispatcher image 
```
docker build -t dispatcher:latest ./dispatcher
```
# Build Custom Autoscaler image
```
docker build -t custom-autoscaler:latest ./custom_auto_scaler
```

### Step 4: Deploy Core Services &amp; ML Inference Workers

Apply your Kubernetes manifests to start the dispatcher queue and initial ML worker pods:
```
kubectl apply -f dispatcher/
kubectl apply -f ml_app/
```
### Step 5: Enable Autoscaling

You can enable autoscaling using either the custom autoscaler service or the standard Kubernetes HPA:

* **Option A — Custom Autoscaler:**

```
kubectl apply -f custom_auto_scaler/

```

* **Option B — Kubernetes HPA (70% Target Threshold):**

```
kubectl apply -f hpa_70.yaml
```

### Step 6: Execute Load Testing &amp; Verify Elastic Scaling

Run the load tester service to generate incoming request volume and verify horizontal autoscaling:

```
cd load_tester
python load_tester.py

```

To monitor pod scaling live:

```
kubectl get pods -w
```

## 📊 Performance &amp; Metrics

Visual metrics showing dynamic scaling events during load tests are captured below:

* **Direct Link to Image File:** [custom\_autoscaler\_metrics.png](https://github.com/hussain-umair/ML-Elastic-Service/blob/main/custom_autoscaler_metrics.png)
