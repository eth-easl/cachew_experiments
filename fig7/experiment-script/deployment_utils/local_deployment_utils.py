import copy
import os
import sys
import yaml

import config_wrapper
import system_utils
from system_utils import execute_cmd
from system_utils import execute_cmd_detach_log


def deploy_local_service(global_cfg, exp_cfg):
    # Make sure local service is down
    stop_local_service(global_cfg, exp_cfg)

    port = 31000
    # Get base config from experiment config:
    service_cfg_dict = exp_cfg.get("experiment/deployment/params")

    # Make tmp dir for configs and logs
    tmp_dir = global_cfg.get("local_tmp_dir", "./tmp") + "/local_service_configs"
    os.makedirs(tmp_dir, exist_ok=True)
    log_dir = exp_cfg.get("experiment/meta/path_to_log")
    os.makedirs(log_dir, exist_ok=True)

    # Move to deployment scripts
    cur_working_dir = os.getcwd()
    os.chdir(global_cfg.get("local_service_deployment_dir"))

    # Start local dispatcher
    # Add new parameters for dispatcher:
    dispatcher_cfg_dict = copy.deepcopy(service_cfg_dict)

    default_cache_path = global_cfg.get("local_service_deployment_dir") + "/outputs"
    cache_path = exp_cfg.get("experiment/deployment/params/cache_path", default_cache_path)
    dispatcher_cfg_dict["cache_path"] = cache_path
    # Clear cache
    system_utils.empty_dir(cache_path)

    dispatcher_cfg_dict["port"] = port
    dispatcher_cfg_dict["dispatcher_address"] = "localhost"
    if dispatcher_cfg_dict["log_dumps"]:
        dispatcher_cfg_dict["log_dir"] = log_dir + "/"
        #dispatcher_cfg_dict["log_dir"] = "gs://tfdata_service_dispatcher_log_dumps"
    # Write dispatcher config to file
    dispatcher_cfg_file = tmp_dir + "/tmp_dispatcher_cfg.yaml"
    with open(dispatcher_cfg_file, "w") as tmp_dispatcher_cfg_yaml:
        yaml.dump(dispatcher_cfg_dict, tmp_dispatcher_cfg_yaml)
    # Start dispatcher
    dispatcher_cmd = "exec python data_service.py --is_dispatcher --config " + dispatcher_cfg_file
    execute_cmd_detach_log(dispatcher_cmd, log_dir + "/dispatcher.log")
    print("Started local dispatcher")

    # Start the local worker
    # TODO support multiple workers...
    worker_cfg_dict = copy.deepcopy(service_cfg_dict)
    worker_cfg_dict["dispatcher_address"] = "localhost:" + str(port)

    for w in range(service_cfg_dict["num_workers"]):
        worker_cfg_dict["port"] = port + w + 1
        worker_cfg_dict["worker_address"] = "localhost:" + str(port+w+1)

        # Write worker config to file
        worker_cfg_file = tmp_dir + "/tmp_worker_cfg_" + str(w) + ".yaml"
        with open(worker_cfg_file, "w") as tmp_worker_cfg_yaml:
            yaml.dump(worker_cfg_dict, tmp_worker_cfg_yaml)
        # Start worker
        worker_cmd = "exec python data_service.py --config " + worker_cfg_file
        execute_cmd_detach_log(worker_cmd, log_dir + "/worker_" + str(w) + ".log")
        print("Started local worker " + str(w))

    # Come back to current working dir
    os.chdir(cur_working_dir)


def stop_local_service(global_cfg, exp_cfg):
    execute_cmd("pkill -f \"python data_service.py\"")
    # Cleanup cache
    default_cache_path = global_cfg.get("local_service_deployment_dir") + "/outputs"
    cache_path = exp_cfg.get("experiment/deployment/params/cache_path", default_cache_path)

