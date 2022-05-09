from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import time

import tensorflow
import tensorflow.compat.v2 as tf

import sys
sys.path.append("/home/aymond/ml_input_processing/experiments/ml/models/official")

from vision.image_classification.resnet.imagenet_preprocessing import input_fn


def make_dataset(params):
    """Input function which provides batches for training."""
    data_path = params["data_path"]
    dataset_num_private_threads = params["dataset_num_private_threads"]
    batch_size = params["batch_size"]
    drop_remainder = params["drop_remainder"]

    dataset = input_fn(
        is_training=True,
        data_dir=data_path,
        batch_size=batch_size,
        dtype=tf.float16,
        datasets_num_private_threads=dataset_num_private_threads,
        drop_remainder=False,
        filenames=None
    )

    return dataset
