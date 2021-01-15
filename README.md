# Resource requirments for cluster with 1 master and 1 worker:
- 4 vcpu
- 8gb ram

# Deploy kubvirt on minikube using official documentation
https://kubevirt.io/quickstart_minikube/

# Deploy VM operator

helm3 upgrade --install vm_operator ./chart/ --debug
