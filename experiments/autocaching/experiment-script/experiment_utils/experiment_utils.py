import tensorflow as tf
from time import perf_counter

import config_wrapper
import system_utils
import time


#@tf.function
def process_epoch(dataset):
    acc = 0
    for e in dataset:
        acc += 1
        #print(e)
        #print("element number: " + str(acc))
        #print(len(tf.strings.bytes_split(e[0])))
        pass

    #print("Number of elements " + str(acc))
    return


@tf.function
def take_rows(iterator, max_rows):
    while max_rows > 0:
        max_rows -= 1
        try:
            e = next(iterator)
        except StopIteration:
            return
    return

@tf.function
def terminate_epoch(iterator):
    while True:
        try:
            e = next(iterator)
        except StopIteration:
            return


def measure_iteration(global_cfg, exp_cfg, dataset):
    results = []

    clear_os_cache = exp_cfg.get("experiment/deployment/params/clear_os_cache", False)
    is_local_put = exp_cfg.get("experiment/deployement/type") == "local-put"
    if is_local_put:
        cache_dir = exp_cfg.get("experiment/deployment/params/cache_path")
        if cache_dir is None or cache_dir == "":
            cache_dir = global_cfg.get("local_tmp_dir", "./tmp") + "/cache"

    epochs = exp_cfg.get("experiment/client/params/epochs")

    # Last operation on dataset.
    # Only iterate over n elements if specified
    # dataset = dataset.take(exp_cfg.get("experiment/client/params/take_num_rows", -1))
    # Measure with take operation to ignore client heartbeat latency effect.
    for epoch in range(epochs):
        if clear_os_cache:
            system_utils.clear_os_cache()

        if exp_cfg.get("experiment/deployment/type/") == "local-put":
            system_utils.empty_cache_dir(cache_dir)

        #max_rows = exp_cfg.get("experiment/client/params/take_num_rows", -1)
        print(epoch)
        start = perf_counter()
        process_epoch(dataset)
        if clear_os_cache and is_local_put:
            system_utils.flush_os_cache()
        end = perf_counter()

        results.append(end - start)
        time.sleep(2)

    return results


def iterate(dataset):
    process_epoch(dataset)
