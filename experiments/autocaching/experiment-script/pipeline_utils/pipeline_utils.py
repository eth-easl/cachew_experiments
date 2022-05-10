import tensorflow as tf

import system_utils


def distribute_dataset(exp_cfg, dataset, service_ip):
    processing_mode = exp_cfg.get("experiment/client/params/processing_mode")
    client_buffer = exp_cfg.get("experiment/client/params/client_buffer")
    max_request_pipelining_per_worker = exp_cfg.get("experiment/client/params/max_request_pipelining_per_worker")

    worker_disable_compress = exp_cfg.get("experiment/deployment/params/worker_disable_compress", False)
    print(processing_mode)
    nightly = exp_cfg.get("experiment/deployment/params/nightly")
    if max_request_pipelining_per_worker == -1 or nightly : #using tf_nighlty
        dataset = dataset.apply(tf.data.experimental.service.distribute(
            processing_mode=processing_mode,
            service="grpc://" + service_ip + ":31000",
            max_outstanding_requests=client_buffer))

    else:
        if worker_disable_compress:
            options = tf.data.Options()
            options.experimental_optimization.noop_elimination = False
            dataset = dataset.with_options(options)

            dataset = dataset.apply(tf.data.experimental.service.distribute(
                job_name="BenchJob",
                processing_mode=processing_mode,
                service="grpc://" + service_ip + ":31000",
                max_outstanding_requests=client_buffer,
                max_request_pipelining_per_worker=max_request_pipelining_per_worker,
                compression=None))
        else:
            dataset = dataset.apply(tf.data.experimental.service.distribute(
                job_name="BenchJob",
                processing_mode=processing_mode,
                service="grpc://" + service_ip + ":31000",
                max_outstanding_requests=client_buffer,
                max_request_pipelining_per_worker=max_request_pipelining_per_worker
                ))

    return dataset


def append_cache_get(global_cfg, exp_cfg, dataset):
    path = exp_cfg.get("experiment/deployment/params/cache_path")
    if path is None or path == "":
        path = global_cfg.get("local_tmp_dir", "./tmp") + "/cache"

    cache_format = exp_cfg.get("experiment/deployment/params/cache_format")
    cache_compression = exp_cfg.get("experiment/deployment/params/cache_compression")
    cache_ops_parallelism = exp_cfg.get("experiment/deployment/params/cache_ops_parallelism")

    element_spec = dataset.element_spec

    return tf.data.experimental.serviceCacheGetDataset(
        path, cache_format, cache_compression, cache_ops_parallelism, element_spec)


def append_cache_put(global_cfg, exp_cfg, dataset):
    path = exp_cfg.get("experiment/deployment/params/cache_path")
    if path is None or path == "":
        path = global_cfg.get("local_tmp_dir", "./tmp") + "/cache"

    cache_format = exp_cfg.get("experiment/deployment/params/cache_format")
    cache_compression = exp_cfg.get("experiment/deployment/params/cache_compression")
    cache_ops_parallelism = exp_cfg.get("experiment/deployment/params/cache_ops_parallelism")

    return dataset.apply(tf.data.experimental.service_cache_put(
        path, cache_format, cache_compression, cache_ops_parallelism))

def append_to_tf_record(global_cfg, exp_cfg, dataset):
    path = exp_cfg.get("experiment/deployment/params/cache_path")
    if path is None or path == "":
        path = global_cfg.get("local_tmp_dir", "./tmp") + "/cache/"

    shards = exp_cfg.get("experiment/deployment/params/num_shards")

    def reduce_func(key, dataset):
        filename = tf.strings.join([path, tf.strings.as_string(key)])
        writer = tf.data.experimental.TFRecordWriter(filename)
        writer.write(dataset.map(lambda _, x: x))
        return tf.data.Dataset.from_tensors(filename)

    dataset = dataset.map(tf.io.serialize_tensor)
    dataset = dataset.enumerate()
    dataset = dataset.apply(tf.data.experimental.group_by_window(
        lambda i, _: i % shards, reduce_func, tf.int64.max
    ))

    return dataset


def get_from_tf_record_ds(global_cfg, exp_cfg, ds):
    path = exp_cfg.get("experiment/deployment/params/cache_path")
    if path is None or path == "":
        path = global_cfg.get("local_tmp_dir", "./tmp") + "/cache/"

    shards = exp_cfg.get("experiment/deployment/params/num_shards")

    filenames = []
    for s in range(shards):
        filenames.append(tf.strings.join([path, tf.strings.as_string(s)]))

    dataset = tf.data.Dataset.from_tensor_slices(filenames)
    dataset = dataset.interleave(
        tf.data.TFRecordDataset,
        num_parallel_calls=shards,
        cycle_length=shards)

    type = ds.element_spec[0].dtype
    dataset = dataset.map(lambda x: tf.io.parse_tensor(x, type))

    return dataset



