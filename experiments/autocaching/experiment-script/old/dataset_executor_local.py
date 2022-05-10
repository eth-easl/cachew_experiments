from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from typing import List

import os
import time
from time import perf_counter

import tensorflow as tf

from absl import app
from absl import flags

import importlib

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'
os.environ['TF_CPP_MIN_VLOG_LEVEL'] = '3'

FLAGS = flags.FLAGS
flags.DEFINE_string('pipeline', '', 'The name of the pipeline definition to use')
flags.DEFINE_string('service_addr', "grpc://localhost:5050", 'The address of the service')
flags.DEFINE_integer('num_epochs', 5, 'The number of epochs.')
flags.DEFINE_boolean('deterministic', False,
                     'Whether to produce elements in a deterministic order.')
flags.DEFINE_boolean('map_and_batch_fusion', True,
                     'Whether to perform fusion.')
flags.DEFINE_boolean('local', False, 'Wether to execute the pipeline locally')
flags.DEFINE_boolean('put', False, 'Test put dataset only')
flags.DEFINE_boolean('get', False, 'Test get dataset only')


# pipeline specific flags
flags.DEFINE_string('data', './data', 'A path with the data.')
                     
    
@tf.function
def process_epoch(dataset):
  options = tf.data.Options()
  options.experimental_deterministic = FLAGS.deterministic
  options.experimental_optimization.map_and_batch_fusion = FLAGS.map_and_batch_fusion
  dataset = dataset.with_options(options)
  for _ in dataset:
    pass


def main(argv):
  del argv
  
  print(FLAGS.pipeline)
  ds_factory = importlib.import_module(FLAGS.pipeline)  
  put_cache_ds, get_cache_ds = ds_factory.make_dataset(FLAGS.data, "./cache")
  dataset = None
  
  results = []
  
  if FLAGS.get:
    print("Testing cache get op locally")
    # Use put op once to fill up cache.
    process_epoch(put_cache_ds)
    print("Filled up cache")
    dataset = get_cache_ds

  elif FLAGS.put:
    print("--put not implemented yet")
    return
  elif FLAGS.local:
    pass
    print("local")
  
  else:
    print("Please choose betwee --put, --get and --local")
    return


  for _ in range(FLAGS.num_epochs):
    start = perf_counter()
    process_epoch(dataset)
    end = perf_counter()
    print('Epoch took: {}'.format(end - start))
    results.append(end - start)
    
  with open("./logs/results.log", "w") as logs:
    for r in results:
        logs.write(str(r) + ",\n")


if __name__ == '__main__':
  app.run(main)
