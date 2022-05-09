import tensorflow as tf

import pipeline_utils


def make_dataset(params):
    dataset = pipeline_utils.make_dataset(params)

    client_buffer = params["client_buffer"]
    max_request_pipelining = params["max_request_pipelining"]
    processing_mode = params["processing_mode"]
    worker_disable_compress = params["worker_disable_compress"]
    service_ip = params["service_ip"]

    if max_request_pipelining == -1: #using tf_nighlty
        dataset = dataset.apply(tf.data.experimental.service.distribute(
            processing_mode=processing_mode,
            service="grpc://" + service_ip + ":31000",
            max_outstanding_requests=client_buffer))
    else:
        if worker_disable_compress:
            options = tf.data.Options()
            options.experimental_optimization.apply_default_optimizations = True
            options.experimental_optimization.noop_elimination = False
            options.experimental_optimization.apply_default_optimizations = True
                        
            dataset = dataset.with_options(options)

            dataset = dataset.apply(tf.data.experimental.service.distribute(
                processing_mode=processing_mode,
                service="grpc://" + service_ip + ":31000",
                max_outstanding_requests=client_buffer,
                job_name="BenchJob",
                max_request_pipelining_per_worker=max_request_pipelining,
                compression=None))
        else:
            dataset = dataset.apply(tf.data.experimental.service.distribute(
                processing_mode=processing_mode,
                service="grpc://" + service_ip + ":31000",
                job_name="BenchJob",
            max_outstanding_requests=client_buffer,
            max_request_pipelining_per_worker=max_request_pipelining
            ))

    return dataset
