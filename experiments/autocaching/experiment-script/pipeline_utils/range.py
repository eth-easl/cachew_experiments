from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# TODO remove debugger.
import pdb

import os
import time

import tensorflow
import tensorflow.compat.v2 as tf

from absl import app
from absl import flags

FLAGS = flags.FLAGS


def make_dataset(data_path):
  """Input function which provides batches for training."""
  dataset = tf.data.Dataset.range(100)

  return dataset
