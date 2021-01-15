import time
import socket
import yaml
import os


import paramiko
import pykube
import kopf
from jinja2 import Template
from pykube.objects import NamespacedAPIObject

class Host:
    def __init__(self, host, user, passwd, port=22):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.port = port

    def ssh_client(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        while True:
            try:
                client.connect(hostname=self.host, username=self.user,
                    password=self.passwd, port=self.port, timeout=30)
            except (paramiko.ssh_exception.SSHException, paramiko.ssh_exception.NoValidConnectionsError, socket.timeout) as e:
                print("ssh service not ready, wait 10 seconds and check again {}".format(e))
                client.close()
                time.sleep(10)
            else:
                break
        return client

    def ssh_execute(self, command):
        output = []

        client = self.ssh_client()
        for cmd in command:
            stdin, stdout, stderr = client.exec_command(cmd)
            output.append(stdout.read() + stderr.read())

        client.close()
        return output

#    def ssh_execute(self, command):
#        output = []
#        client = paramiko.SSHClient()
#        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#        client.connect(hostname=self.host, username=self.user,
#          password=self.passwd, port=self.port)
#        for cmd in command:
#          stdin, stdout, stderr = client.exec_command(cmd)
#          output.append(stdout.read() + stderr.read())
#        client.close()
#        return output

    def check_ssh_open(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while (s.connect_ex((self.host, self.port)) != 0):
            print("Ssh port is closed, wait 10 seconds and check again")
            time.sleep(10)

    def init_k8s_master(self):
        kubeadm_command = ["sudo kubeadm init --pod-network-cidr=192.168.0.0/16"]
        prepare_kubectl = ["mkdir -v /home/ubuntu/.kube",
            "sudo cp -v /etc/kubernetes/admin.conf /home/ubuntu/.kube/config",
            "sudo chown ubuntu: /home/ubuntu/.kube/config"]

        setup_calico = ["kubectl taint nodes --all node-role.kubernetes.io/master-",
            "kubectl create -f https://docs.projectcalico.org/manifests/tigera-operator.yaml",
            "kubectl create -f https://docs.projectcalico.org/manifests/custom-resources.yaml"]

        print(self.ssh_execute(["uptime"]))

        status_code = self.ssh_execute(kubeadm_command)
        print("Init kubeadm output {}".format(status_code))

        print("Wait 20 seconds while kube api is ready")
        time.sleep(20)

        status_code = self.ssh_execute(prepare_kubectl)
        print("Prepare kubectl output {}".format(status_code))

        status_code = self.ssh_execute(setup_calico)
        print("Setup calico output {}".format(setup_calico))

    def get_host_ip(self):
        ip_addr = self.ssh_execute(["sudo ip r sh|awk '/default/ {print $9}'"])
        return ip_addr[-1].decode('ascii').rstrip()

    def get_join_token(self):
        token = self.ssh_execute(["sudo kubeadm token create"])
        return token[-1].decode('ascii').rstrip()

    def init_k8s_worker(self, ip, token):
        kubeadm_command = ['sudo kubeadm join {0}:6443 --token {1} --discovery-token-unsafe-skip-ca-verification'.format(ip, token)]
        print(self.ssh_execute(["uptime"]))

        print("Excuted command {}".format(kubeadm_command))
        status_code = self.ssh_execute(kubeadm_command)
        print("Init kubeadm output {}".format(status_code))

        print("Wait 20 seconds while kube api is ready")
        time.sleep(20)

class VirtualMachine(NamespacedAPIObject):
    version = "kubevirt.io/v1alpha3"
    endpoint = "virtualmachines"
    kind = "VirtualMachine"

def create_node(name):
    tmpl_path = 'templates'

    # Render the pod yaml with some spec fields used in the template.
    with open(os.path.join(tmpl_path, 'virtualmachine.yaml.j2')) as fd:
        template = Template(fd.read())
        vm_template = yaml.safe_load(template.render(vm_name=name))

    with open(os.path.join(tmpl_path, 'service.yaml.j2')) as fd:
        template = Template(fd.read())
        svc_template = yaml.safe_load(template.render(vm_name=name))

    return vm_template, svc_template


@kopf.on.create('cloud.org', 'v1', 'kubeclusters')
def create_fn(spec, **kwargs):
    children_id = []
    common_label = kwargs['meta']['name']

    api = pykube.HTTPClient(pykube.KubeConfig.from_env())

    vm_tmlp, svc_tmpl = create_node('{}-master'.format(kwargs['name']))

    kopf.adopt(vm_tmlp)
    kopf.adopt(svc_tmpl)
    vm = VirtualMachine(api, vm_tmlp)
    svc = pykube.Service(api, svc_tmpl)

    vm.create()
    svc.create()
    children_id = [vm.metadata['uid'], svc.metadata['uid']]

    svc_ip = svc.obj['spec']['clusterIP']
    print("Trying to connect to VM {}".format(svc_ip))
    ubuntu_k8s = Host(host=svc_ip, user='ubuntu', passwd='ubuntu', port=22)
    ubuntu_k8s.init_k8s_master()
    master_ip = ubuntu_k8s.get_host_ip()
    join_token = ubuntu_k8s.get_join_token()

    # Create workers
    for worker in range(int(spec.get('worker', 0))):
      vm_tmlp, svc_tmpl = create_node('{0}-worker-{1}'.format(kwargs['name'], worker))
      kopf.adopt(vm_tmlp)
      kopf.adopt(svc_tmpl)

      vm = VirtualMachine(api, vm_tmlp)
      svc = pykube.Service(api, svc_tmpl)
      vm.create()
      svc.create()
      children_id += [vm.metadata['uid'], svc.metadata['uid']]
      svc_ip = svc.obj['spec']['clusterIP']
      print("Trying to connect to VM {}".format(svc_ip))
      ubuntu_k8s = Host(host=svc_ip, user='ubuntu', passwd='ubuntu', port=22)
      ubuntu_k8s.init_k8s_worker(master_ip, join_token)

    api.session.close()

    # Update the parent's status.
    return {'children': children_id}
