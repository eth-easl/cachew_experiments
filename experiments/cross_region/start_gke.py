from __future__ import print_function
from msilib.schema import LaunchCondition
from operator import truediv
import subprocess as sp
import os
import sys
import shlex
from subprocess import Popen, PIPE
import re
import jinja2
import time
from absl import app
from absl import flags
import yaml

FLAGS = flags.FLAGS
flags.DEFINE_boolean('stop', False, 'stops the services, and destroys all resources.')
flags.DEFINE_boolean('restart', False, 'restarts the tf.data service.')
flags.DEFINE_boolean('stop_service', False, 'stops the service only')
flags.DEFINE_string('image', 'tf_oto:lw', 'specifies the docker image to use for the service')
flags.DEFINE_string('vlog', '0', 'TF_CPP_MAX_VLOG_LEVEL level')
flags.DEFINE_integer('num_workers', 15, 'Specifies the number of worker nodes to spawn')
flags.DEFINE_string('cluster_name', 'otmraz-gke', 'GKE cluster service name')
flags.DEFINE_string('zone', 'europe-west4-a', 'GKE cluster service name')

def render_jinja_template(file):
    if len(sys.argv) != 2:
        print("usage: {} [template-file]".format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1], "r") as f:
        print(jinja2.Template(f.read()).render())

def get_exitcode_stdout_stderr(cmd):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    args = shlex.split(cmd)

    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    proc.wait()
    out, err = proc.communicate()
    exitcode = proc.returncode
    #
    return exitcode, out, err
   
def start_gke():
    print("Starting kubernetes cluster with GKE (this can take some time)...")

    command = "gcloud container clusters create {0} --zone {1} \
 		--scopes=cloud-platform --enable-ip-alias --num-nodes={2} \
 		--machine-type=n2-standard-8".format(FLAGS.cluster_name, FLAGS.zone, FLAGS.num_workers)
    get_exitcode_stdout_stderr(command)
    print("GKE cluster up")

def create_service_interfaces_and_yaml():
    ######## TODO: ADD Code from https://github.com/tensorflow/ecosystem/tree/master/data_service
    #cmd = "python3 ../render_template.py data_service_interfaces.yaml.jinja | kubectl apply -f -"
    cmd = "kubectl apply -f -"
    get_exitcode_stdout_stderr(cmd)
    print("Data service interfaces created")

def ip_missing(str):
    if '''""''' in str:
        return True
    else:
        return False

def get_worker_ips():
    cmd = '''kubectl get services -o=jsonpath='{"\n"}{range .items[*]}"{.metadata.name}": "{.status.loadBalancer.ingress[*].ip}",{"\n"}{end}{"\n"}' | grep data-service-worker'''
    not_ready = True
    exitcode, out, err = get_exitcode_stdout_stderr(cmd)
    while(not_ready):
        time.sleep(1)
        exitcode, out, err = get_exitcode_stdout_stderr(cmd)
        not_ready = ip_missing(cmd)

    return out

def launch_cachew_servers():
    worker_ips = get_worker_ips()

    with open("templates/data_service.yaml.jinja", "r") as f:
        lines = f.readlines()
        lines.insert(1, worker_ips)

    with open("data_service.yaml.jinja", "w") as f:
        f.writelines(lines)

    # Edit image, ports, etc.
    image = "gcr.io/tfdata-service/" + FLAGS.image
    vlog = "\"" + FLAGS.vlog + "\""
    with open('data_service.yaml.jinja') as f:
        template = jinja2.Template(f.read())
    rendered = template.render(image=image, port=31000, vlog=vlog)

    with open("data_service.yaml", "w") as f:
        f.write(rendered)

    # Actual server launch
    cmd='''kubectl apply -f -'''
    get_exitcode_stdout_stderr(cmd)

    print("Launched Cachew service")

def stop_service():
    print("Stopping services")
    c, out, err = get_exitcode_stdout_stderr("kubectl get services")
    
    names = []
    
    for line in out.decode('ascii').split("\n"):
        splits = line.split()
        if len(splits) < 5: break
        if "data-service-" in splits[0]:
            names.append(splits[0])
            
    for name in names:
        get_exitcode_stdout_stderr("kubectl delete rs " + name)
        get_exitcode_stdout_stderr("kubectl delete service " + name)
        
    print("Stopped services")

def stop_gke():
    print("Stopping GKE cluster")
    command = "gcloud container clusters delete {0} --zone {1}".format(FLAGS.cluster_name, FLAGS.zone) 
    get_exitcode_stdout_stderr(command)
    print("Stopped GKE cluster")

def main(argv):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if FLAGS.restart:
        stop_service()
        create_service_interfaces_and_yaml() # to regenerate yaml in case image changed.
        launch_cachew_servers()
    elif FLAGS.stop:
        stop_service()
        stop_gke()
    else:
        start_gke()
        create_service_interfaces_and_yaml()
        launch_cachew_servers()

if __name__ == '__main__':
    app.run(main)



