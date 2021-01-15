#!/bin/bash

apt-get update
apt-get install vim -y

# Disable unintended upgrades
sed -i 's/1/0/g' /etc/apt/apt.conf.d/20auto-upgrades
sed -i 's/1/0/g' /etc/apt/apt.conf.d/10periodic
