from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from typing import List

import os
import time
from time import perf_counter

import tensoflow as tf

from absl import app
from absl import flags

import importlib

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'
<<<<<<< HEAD:experiments/service/exp-scripts/dataset_executor.py
os.environ['TF_CPP_MIN_VLOG_LEVEL'] = '3'
=======
os.environ['TF_CPP_MAX_VLOG_LEVEL'] = '3'
>>>>>>> aymond-tmp:experiments/service/exp-scripts/old/dataset_executor.py
#os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'cpp'
#os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION'] = '2'

FLAGS = flags.FLAGS
flags.DEFINE_string('pipeline', '', 'The name of the pipeline definition to use')
flags.DEFINE_string('service_addr', "grpc://localhost:5050", 'The address of the service')
flags.DEFINE_integer('num_epochs', 4, 'The number of epochs.')
flags.DEFINE_boolean('deterministic', False,
                     'Whether to produce elements in a deterministic order.')
flags.DEFINE_boolean('map_and_batch_fusion', True,
                     'Whether to perform fusion.')
flags.DEFINE_boolean('local', False, 'Wether to execute the pipeline locally')
flags.DEFINE_boolean('local_service', False, 'Wether to execute the pipeline in a local service')
flags.DEFINE_boolean('local_get', False, 'Test caching get locally, without service')
flags.DEFINE_boolean('local_put', False, 'Test caching put locally, without service')
flags.DEFINE_boolean('local_snapshot', False, 'Test snapshot locally, without service')
flags.DEFINE_integer('client_buffer', 2, 'The max_outstanding_requests for the dispatcher client')
flags.DEFINE_string('cache_dir', './cache', 'The path for the caching dir')
flags.DEFINE_boolean('clear_page_cache', False, 'Wether to clear the OS page cache between epochs.')

# pipeline specific flags
flags.DEFINE_string('data', './data', 'A path with the data.')
                     
def setup_local_service(num_workers):
    dispatcher = tf.data.experimental.service.DispatchServer()
    dispatcher_address = dispatcher.target.split("://")[1]

    workers = []
    for _ in num_workers:
        worker = tf.data.experimental.service.WorkerServer(
        tf.data.experimental.service.WorkerConfig(dispatcher_address=dispatcher_address))

        workers.append(worker)

    return dispatcher, workers


@tf.function
def process_epoch(dataset):
  options = tf.data.Options()
  options.experimental_deterministic = FLAGS.deterministic
  options.experimental_optimization.map_and_batch_fusion = FLAGS.map_and_batch_fusion
  dataset = dataset.with_options(options)

  for _ in dataset:
    pass
    

@tf.function
def process_epoch_take(dataset, n):
  dataset = dataset.take(n)
  options = tf.data.Options()
  options.experimental_deterministic = FLAGS.deterministic
  options.experimental_optimization.map_and_batch_fusion = FLAGS.map_and_batch_fusion
  dataset = dataset.with_options(options)

  for _ in dataset:
    pass
    
def debug(dataset):
  print(dataset.element_spec)
  for e in dataset.take(1):
    print(e[0].numpy()[0])
    print("-------")
    print(e[1].numpy()[0])



def main(argv):
  del argv
  
  print(FLAGS.pipeline)
  ds_factory = importlib.import_module(FLAGS.pipeline)
  dataset = ds_factory.make_dataset(FLAGS.data)
  
  # Declare dispatcher and workers in case local service is chosen.
  dispatcher = None
  worker = None
  
  results = []
  
  # Clean cache
  #
  
  if FLAGS.local_get:
    print("Testing ops without service")
    #put_dataset = dataset.apply(tf.data.experimental.service_cache_put(FLAGS.cache_dir, 8))
    element_spec = dataset.element_spec
    #process_epoch(put_dataset)
    
    dataset = tf.data.experimental.serviceCacheGetDataset(FLAGS.cache_dir, 8, element_spec)
    dataset = ds_factory.post_cache_processing(dataset)
  elif FLAGS.local_put:
    os.system('rm -rf ' + FLAGS.cache_dir + '/*')
    dataset = dataset.apply(tf.data.experimental.service_cache_put(FLAGS.cache_dir, 8))
  elif FLAGS.local_snapshot:
    dataset = dataset.apply(tf.data.experimental.snapshot(FLAGS.cache_dir, compression=None))#, shard_func=lambda x, y: x % 8))
    dataset = ds_factory.post_cache_processing(dataset)
  elif FLAGS.local:
    dataset = ds_factory.post_cache_processing(dataset)
  elif FLAGS.local_service:
    print("local_service")
    dispatcher, worker = setup_local_service()
    dataset = dataset.apply(
      tf.data.experimental.service.distribute(
        processing_mode="parallel_epochs", service=dispatcher.target, max_outstanding_requests=16))
    dataset = ds_factory.post_cache_processing(dataset)
    process_epoch(dataset)
  else:
    print("service")
    dataset = dataset.apply(
      tf.data.experimental.service.distribute(
        processing_mode="parallel_epochs", service=FLAGS.service_addr, max_outstanding_requests=16)) 
    # use this to populate the cache
    dataset = ds_factory.post_cache_processing(dataset)
    process_epoch(dataset)


  for _ in range(FLAGS.num_epochs):
    if(FLAGS.clear_page_cache):
      print("Clearing cache..")
      time.sleep(5)
      os.system('sync; echo 1 > /proc/sys/vm/drop_caches')
      # this also clears dentries and inodes.
      # sync; echo 3 > /proc/sys/vm/drop_caches
      
    start = perf_counter()
    # iterate through parts of the dataset only, so that 
    #process_epoch_take(dataset, 500)
    process_epoch(dataset)
    end = perf_counter()
    print('Epoch took: {}'.format(end - start))
    results.append(end - start)
    
  with open("./logs/results.log", "w") as logs:
    for r in results:
        logs.write(str(r) + ",\n")


if __name__ == '__main__':
  app.run(main)
