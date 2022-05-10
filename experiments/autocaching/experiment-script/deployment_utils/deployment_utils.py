import os
import sys
import yaml

import config_wrapper
import system_utils
from system_utils import execute_cmd


def deploy_service(global_cfg, exp_cfg, restart=False):

    # Write temporary config file for service deployment:
    service_cfg_dict = exp_cfg.get("experiment/deployment/params")

    if service_cfg_dict["log_dumps"]:
        #log_bucket = global_cfg.get("dispatcher_log_dumps_bucket")
        # First make sure the bucket is empty.
        #code, out, err = execute_cmd("gsutil rm " + log_bucket)
        #service_cfg_dict["log_dir"] = log_bucket
        pass
    else:
        service_cfg_dict["log_dir"] = ""

    # Clean up the cache
    gluster_cache = global_cfg.get("glusterfs_mount_path") + "/cache"
    execute_cmd("sudo rm -r " + gluster_cache)

    #service_cfg_dict["glusterfs_ip"] = global_cfg.get("glusterfs_ip")

    tmp_dir = global_cfg.get("local_tmp_dir", "./tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    service_cfg_file = tmp_dir + "/tmp_service_cfg.yaml"
    with open(service_cfg_file, "w") as tmp_service_cfg_yaml:
        yaml.dump(service_cfg_dict, tmp_service_cfg_yaml)

    # Change to service deployment directory:
    cur_working_dir = os.getcwd()
    os.chdir(global_cfg.get("service_deployment_dir"))

    # Run service deployment script and check for error
    cmd = "./manage_cluster.sh restart_service -f " + service_cfg_file
    exitcode, out, err = execute_cmd(cmd)

    if exitcode != 0:
        print("Deployment utils: Could not deploy service properly:")
        print(out)
        print(err)
        sys.stdout.flush()
        sys.exit()
    # Come back to current working dir
    os.chdir(cur_working_dir)


def start_cluster(global_cfg, exp_cfg):

    # Write temporary config file for service deployment:
    service_cfg_dict = exp_cfg.get("experiment/deployment/params")
    #service_cfg_dict["glusterfs_ip"] = global_cfg.get("glusterfs_ip")

    tmp_dir = global_cfg.get("local_tmp_dir", "./tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    # Clean up the cache
    gluster_cache = global_cfg.get("glusterfs_mount_path") + "/cache"
    execute_cmd("sudo rm -r " + gluster_cache)

    service_cfg_file = tmp_dir + "/tmp_service_cfg.yaml"
    with open(service_cfg_file, "w") as tmp_service_cfg_yaml:
        yaml.dump(service_cfg_dict, tmp_service_cfg_yaml)

    # Change to service deployment directory:
    cur_working_dir = os.getcwd()
    os.chdir(global_cfg.get("service_deployment_dir"))

    # Run service deployment script and check for error
    cmd = "source venv/bin/activate ; python service_deploy.py --start_cluster --config " + service_cfg_file
    exitcode, out, err = execute_cmd(cmd)

    if exitcode != 0:
        print("Deployment utils: Could not start cluster properly:")
        print(out)
        print(err)
        sys.stdout.flush()
        sys.exit()
    # Come back to current working dir
    os.chdir(cur_working_dir)


def stop_service(global_cfg, exp_cfg):
    # Get pod logs
    code, out, err = execute_cmd("kubectl get pods")
    pods = []
    for line in out.decode('ascii').split("\n")[1:]:
        pods.append(line.split()[0])

    log_dir = exp_cfg.get("experiment/meta/path_to_log")
    os.makedirs(log_dir, exist_ok=True)
    for pod in pods:
        system_utils.execute_cmd_detach_log("kubectl logs " + pod, log_dir + "/" + pod + ".log")

    # Change to service deployment directory:
    cur_working_dir = os.getcwd()
    os.chdir(global_cfg.get("service_deployment_dir"))

    # Run service deployment script and check for error
    cmd = "source venv/bin/activate ; python service_deploy.py --stop_service"
    exitcode, out, err = execute_cmd(cmd)
    if exitcode != 0:
        print("Deployment utils: Could not stop service properly:")
        print(out)
        print(err)
        sys.stdout.flush()
        sys.exit()
    # Come back to current working dir
    os.chdir(cur_working_dir)

    # Recover log dumps if any:
    service_cfg_dict = exp_cfg.get("experiment/deployment/params")
    if service_cfg_dict["log_dumps"]:
        local_gluster_logs = global_cfg.get("local_tmp_dir") + "/cache/dispatcher_dumps/"
        #log_bucket = global_cfg.get("dispatcher_log_dumps_bucket")
        #execute_cmd("gsutil -m cp -r " + log_bucket + " " + log_dir)
        execute_cmd("sudo cp -r " + local_gluster_logs + " " + log_dir + "/")
        execute_cmd("sudo rm -r " + local_gluster_logs)



def get_service_ip():
    get_ips_command = "kubectl get services -o=jsonpath='{\"\\n\"}{range .items[*]}{.metadata.name}:{.status.loadBalancer.ingress[*].ip}{\"\\n\"}{end}{\"\\n\"}'"
    exitcode, out, err = execute_cmd(get_ips_command)

    ips = {}
    for line in out.decode('ascii').split("\n"):
        if "data-service-dispatcher" in line:
            split = line.split(":")
            return split[1]

def get_dispatcher_node():
    c, out, err = execute_cmd("kubectl get nodes")

    dispatcher_node = ""
    for line in out.decode('ascii').split("\n"):
        splits = line.split()
        if len(splits) < 5: break
        if "cachew-dispatcher-" in splits[0]:
            dispatcher_node = splits[0]

    return dispatcher_node

def get_service_logs(global_cfg, exp_cfg):
    # Get pod logs
    code, out, err = execute_cmd("kubectl get pods")
    pods = []
    for line in out.decode('ascii').split("\n")[1:-1]:
        pods.append(line.split()[0])

    log_dir = exp_cfg.get("experiment/meta/path_to_log")
    os.makedirs(log_dir, exist_ok=True)
    for pod in pods:
        system_utils.execute_cmd_detach_log("kubectl logs " + pod, log_dir + "/" + pod + ".log")

    # Recover log dumps if any:
    service_cfg_dict = exp_cfg.get("experiment/deployment/params")
    if service_cfg_dict["log_dumps"]:
        local_gluster_logs = global_cfg.get("glusterfs_mount_path") + "/dispatcher_dumps/"
        # log_bucket = global_cfg.get("dispatcher_log_dumps_bucket")
        # execute_cmd("gsutil -m cp -r " + log_bucket + " " + log_dir)
        execute_cmd("sudo cp -r " + local_gluster_logs + " " + log_dir + "/")
        execute_cmd("sudo rm -r " + local_gluster_logs)











