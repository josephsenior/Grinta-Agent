---
name: kubernetes
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - kubernetes
  - k8s
  - kube
---

# Kubernetes with KIND

KIND (Kubernetes IN Docker) for local k8s testing.

## Setup

```bash
# Install KIND
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.22.0/kind-linux-amd64
chmod +x ./kind && sudo mv ./kind /usr/local/bin/

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv ./kubectl /usr/local/bin/

# Create cluster
kind create cluster --name my-cluster
```

## Common Commands

```bash
# Cluster management
kind get clusters
kind delete cluster --name my-cluster

# Deploy
kubectl apply -f deployment.yaml
kubectl get pods
kubectl logs <pod-name>
kubectl exec -it <pod-name> -- /bin/bash

# Services
kubectl expose deployment my-app --port=8080 --type=NodePort
kubectl port-forward service/my-app 8080:8080
```

## Example Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        ports:
        - containerPort: 8080
```

## Troubleshooting

**Pods not starting:** `kubectl describe pod <name>` for events
**Connection refused:** Check service with `kubectl get svc`
**Image pull errors:** Load local images: `kind load docker-image my-app:latest`
