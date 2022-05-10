import time

from tqdm import tqdm
import numpy as np
from absl import app
from absl import flags
import itertools
import os
import pandas as pd
import tensorflow as tf
import time
import yaml

import config_wrapper
import deployment_utils
import experiment_utils
import pipeline_utils
import system_utils

# Logging on the client side
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '4'
os.environ['TF_CPP_MAX_VLOG_LEVEL'] = '0'

FLAGS = flags.FLAGS
flags.DEFINE_string("global_config", "./global_config.yaml", "The path to the global configuration file(global_config.yaml)")
flags.DEFINE_string("exp_config", "./default_exp_config.yaml", "The path to the experiment config file (exp_config.yaml)")

flags.DEFINE_boolean("test", False, "runs the test function")


def test(global_cfg, exp_cfg):
    print("Testing")
    deployment_utils.get_service_logs(global_cfg, exp_cfg)
    time.sleep(10)
    print("Done")

  
def run_config(global_cfg, exp_cfg):
    # Get the raw dataset
    # print("Getting dataset for pipeline: " + exp_cfg.get("experiment/pipeline/name"))
    dataset = pipeline_utils.make_dataset(exp_cfg.get("experiment/pipeline"))
    
    # Determine deployment type
    deployment = exp_cfg.get("experiment/deployment/type")
    # print("Deployment type: " + deployment)

    # Service
    # Start service or local service and distribute dataset
    if deployment == "kubernetes-service":
     #   print("Starting service...")
        deployment_utils.deploy_service(global_cfg, exp_cfg, restart=True)
     #   print("Leaving some time for the workers to connect...")
        time.sleep(30)
        # Distribute the dataset
        #service_ip = deployment_utils.get_service_ip()
        dispatcher_node = deployment_utils.get_dispatcher_node()
        dataset = pipeline_utils.distribute_dataset(exp_cfg, dataset, dispatcher_node)
    elif deployment == "local-service":
        deployment_utils.deploy_local_service(global_cfg, exp_cfg)
        time.sleep(10)
        dataset = pipeline_utils.distribute_dataset(exp_cfg, dataset, "localhost")

    # Local cache
    # Append cache ops and clean up cache.
    if deployment in ["local-get", "local-put", "local-snapshot", "local-TFRecordReader"]:
        cache_path = exp_cfg.get("experiment/deployment/params/cache_path")
        if cache_path is None or cache_path == "":
            cache_path = global_cfg.get("local_tmp_dir", "./tmp") + "/cache"

        system_utils.make_dir(cache_path)
        system_utils.empty_cache_dir(cache_path)

        if deployment == "local-get":
            # TODO spin up Filestore instance and mount?
            # Empty and write to cache
            put_dataset = pipeline_utils.append_cache_put(global_cfg, exp_cfg, dataset)
            experiment_utils.iterate(put_dataset)

            dataset = pipeline_utils.append_cache_get(global_cfg, exp_cfg, dataset)
            dataset = dataset.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
        elif deployment == "local-put":
            dataset = pipeline_utils.append_cache_put(global_cfg, exp_cfg, dataset)
        elif deployment == "local-snapshot":
            system_utils.empty_dir(cache_path)  # Will clear all cache...
            dataset = dataset.apply(tf.data.experimental.snapshot(cache_path, compression=None))
            experiment_utils.iterate(dataset)  # Go through once for write.
        elif deployment == "local-TFRecordReader":
            system_utils.empty_dir(cache_path)  # Will clear all cache...
            to_tf_record_ds = pipeline_utils.append_to_tf_record(global_cfg, exp_cfg, dataset)
            experiment_utils.iterate(to_tf_record_ds)

            dataset = pipeline_utils.get_from_tf_record_ds(global_cfg, exp_cfg, dataset)

    # run x epochs and measure.
    results = []
    # TODO move this loop out and restart service if needed
    for rep in range(exp_cfg.get("experiment/client/params/repetitions")):
        print("Repetition " + str(rep) + "...")
        results.extend(experiment_utils.measure_iteration(global_cfg, exp_cfg, dataset))

    # Kill local service
    if deployment == "local-service":
        #pass
        deployment_utils.stop_local_service(global_cfg, exp_cfg)
    elif deployment == "kubernetes-service":
        deployment_utils.get_service_logs(global_cfg, exp_cfg)

    return results


def get_range_indices(exp_cfg):
    range_keys = exp_cfg.get("experiment/range_configs")
    if range_keys is None or range_keys == "":
        return None, None

    ranges = []
    for range_key in range_keys:
        ranges.append(exp_cfg.get(range_key, []))

    indices = itertools.product(*ranges)

    return range_keys, indices


# ----------------------------------------------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------------------------------------------

def main(argv):
    del argv

    # Loading config files
    global_cfg = config_wrapper.Config(FLAGS.global_config)
    exp_cfg = config_wrapper.Config(FLAGS.exp_config)#,  "./default_exp_config.yaml")

    if FLAGS.test:
        test(global_cfg, exp_cfg)
        return

    range_keys, indices = get_range_indices(exp_cfg)

    if range_keys is None:
        range_keys = []
        indices = [[]]

    raw_results = dict()
    # Construct aggregated dict
    agg_results = dict()
    for key in range_keys + ["start_timestamp", "end_timestamp", "avg", "std", "num_epochs_for_avg", "avg_all_epochs",
                             "std_all_epochs", "num_epochs", "num_repetitions"]:
        agg_results[key] = []

    path_to_log = exp_cfg.get("experiment/meta/path_to_log")
    timestamp = time.localtime()
    timestamp = time.strftime("%Y-%m-%d-%H-%M", timestamp)
    path_to_log += "/" + timestamp
    exp_cfg.set("experiment/meta/path_to_log", path_to_log)
    system_utils.make_dir(path_to_log)
    exp_name = exp_cfg.get("experiment/meta/name")

    exp_cfg.write_to_disk(path_to_log, exp_name + "_config.yaml")
    #system_utils.start_disk_monitor(path_to_log + "/" + exp_name + "_iostat.json")

    for i in tqdm(list(indices)):
        i_string = "config"
        i_string_path = "config"
        for key_num in range(len(range_keys)):
            # print("Setting " + str(range_keys[key_num]) + " as " + str(i[key_num]))
            # header string
            i_string = i_string + "/" + range_keys[key_num] + ":" + str(i[key_num])
            i_string_path = i_string_path + "/" + ((range_keys[key_num]).split("/"))[-1] + ":" + str(i[key_num])
            # aggregated results table
            agg_results[range_keys[key_num]].append(i[key_num])
            # config
            exp_cfg.set(range_keys[key_num], i[key_num])

        # Update exp config file:
        exp_cfg.set("experiment/meta/path_to_log", path_to_log + "/logs_for_" + i_string_path)
        # print(i_string_path)

        # Run configuration:
        start_timestamp = time.localtime()
        run_results = run_config(global_cfg, exp_cfg)
        end_timestamp = time.localtime()
        # Append raw results:
        raw_results[i_string] = run_results
        # Aggregate and append raw results:
        if len(run_results)>2:
            agg_results["avg"].append(np.average(run_results[2:]))
            agg_results["std"].append(np.std(run_results[2:]))
            agg_results["num_epochs_for_avg"].append(exp_cfg.get("experiment/client/params/epochs") - 2)
        else:
            agg_results["avg"].append(np.average(run_results))
            agg_results["std"].append(np.std(run_results))
            agg_results["num_epochs_for_avg"].append(exp_cfg.get("experiment/client/params/epochs"))

        agg_results["avg_all_epochs"].append(np.average(run_results))
        agg_results["std_all_epochs"].append(np.std(run_results))
        agg_results["num_epochs"].append(exp_cfg.get("experiment/client/params/epochs"))
        agg_results["num_repetitions"].append(exp_cfg.get("experiment/client/params/repetitions"))
        agg_results["start_timestamp"].append(time.strftime("%m/%d/%y %H:%M:%S", start_timestamp))
        agg_results["end_timestamp"].append(time.strftime("%m/%d/%y %H:%M:%S", end_timestamp))

        # Write results to disk
        df = pd.DataFrame().from_dict(raw_results)
        df.to_csv(path_to_log + "/" + exp_name + "_raw_results.csv", index=False)

        df_agg = pd.DataFrame().from_dict(agg_results)
        df_agg.to_csv(path_to_log + "/" + exp_name + "_agg_results.csv", index=False)

    system_utils.stop_disk_monitor()


if __name__ == '__main__':
    app.run(main)
