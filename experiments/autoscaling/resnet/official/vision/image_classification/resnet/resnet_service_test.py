from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# TODO remove debugger.
import pdb
from typing import List

import os


os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'
os.environ['TF_CPP_MAX_VLOG_LEVEL'] = '0'

import time

import tensorflow
import tensorflow.compat.v2 as tf

from absl import app
from absl import flags

FLAGS = flags.FLAGS

# Service specific flags
flags.DEFINE_string('dispatcher_ip', '34.66.61.164', 'use EXTERNAL_IP of the dispatcher, from `kubectl get services` command output.')

flags.DEFINE_string('data_dir', '/training-data/imagenet2012/tfrecords', 'Path for training data.')
flags.DEFINE_integer('batch_size', 312, 'Batch size.')
flags.DEFINE_integer('num_epochs', 1, 'The number of epochs.')


nb_train_imgs=1281167 # ImageNet
steps_per_ep = nb_train_imgs//FLAGS.batch_size
    
def make_dataset():
    ds = input_fn(
        is_training=True,
        data_dir=data_dir,
        batch_size=batch_size,
        dtype=tf.float16,
        datasets_num_private_threads=4, #32
        drop_remainder=False,
        dataset_repeat=False
    )
    return ds


def main(argv):
  del argv

  dataset = make_dataset()

  # tf-data service
  dataset = dataset.apply(tf.data.experimental.service.distribute(
      processing_mode="distributed_epoch", service="grpc://" + FLAGS.dispatcher_ip + ":31000", max_outstanding_requests=8, max_request_pipelining_per_worker=8
  ))


  @tf.function
  def process_epoch(dataset):
    for _ in dataset:
      pass

  for _ in range(FLAGS.num_epochs):
    start = time.time()
    process_epoch(dataset)
    print('Epoch took: {}'.format(time.time() - start))


if __name__ == '__main__':
  app.run(main)
