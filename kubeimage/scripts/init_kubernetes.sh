#!/bin/bash

kubeadm config images pull
docker pull docker.io/calico/node:v3.17.1
docker pull docker.io/calico/typha:v3.17.1
docker pull docker.io/calico/kube-controllers:v3.17.1
docker pull quay.io/tigera/operator:v1.13.2
sleep 300
#kubeadm init --pod-network-cidr=192.168.0.0/16
#
#mkdir -p $HOME/.kube
#cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
#chown $(id -u):$(id -g) $HOME/.kube/config
#
#
#kubectl taint nodes --all node-role.kubernetes.io/master-
#kubectl create -f https://docs.projectcalico.org/manifests/tigera-operator.yaml
#kubectl create -f https://docs.projectcalico.org/manifests/custom-resources.yaml
