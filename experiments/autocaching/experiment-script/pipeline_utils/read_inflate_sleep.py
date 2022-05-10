from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import time
import contextlib

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '4'
import tensorflow
import tensorflow.compat.v2 as tf


def inflate(input):
    size = tf.cast(tf.math.floor(tf.strings.length(input)/2), tf.int32)
    half_input = tf.strings.substr(input, 0, size)

    return input, input, half_input #input # , half_input #, input, input, input, input



def _get_filenames(data_path, num_files_to_read):
  """Return filenames for dataset."""
  return [
      os.path.join(data_path, 'train-%05d-of-01024' % i)
      for i in range(num_files_to_read)
    ]



def make_dataset(params):
  """Input function which provides batches for training."""
  data_path = params["data_path"]
  batch_size = params["batch_size"]
  num_files_to_read = params["num_files_to_read"]
  sleep_time_msec = params["sleep_time_msec"]  # to milisec

  filenames = _get_filenames(data_path, num_files_to_read)

  dataset = tf.data.Dataset.from_tensor_slices(filenames)
  #dataset = dataset.shuffle(buffer_size=num_files_to_read)

  dataset = dataset.interleave(
      tf.data.TFRecordDataset,
      num_parallel_calls=tf.data.experimental.AUTOTUNE,
      cycle_length=4)
  dataset = dataset.prefetch(tf.data.experimental.AUTOTUNE)

  dataset = dataset.apply(tf.data.experimental.mark("source_cache"))

  # Parses the raw records into images and labels.
  dataset = dataset.map(
      inflate, num_parallel_calls=tf.data.experimental.AUTOTUNE)
  dataset = dataset.batch(batch_size)

  dataset = dataset.apply(tf.data.experimental.sleep(int(sleep_time_msec * 1000)))

  return dataset

