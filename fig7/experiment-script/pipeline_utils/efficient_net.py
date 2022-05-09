from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import time

import tensorflow
import tensorflow.compat.v2 as tf

import sys
sys.path.append("/home/aymond/ml_input_processing/experiments/ml/automl/efficientnetv2")

import datasets
import effnetv2_configs
import hparams
import copy

def make_dataset(params):
    """Input function which provides batches for training."""

    data_dir = params["data_dir"] #gs://tfdata-imagenet/

    model_name = "efficientnetv2-b0"
    dataset_cfg = "imagenet"

    config = copy.deepcopy(hparams.base_config)
    config.override(effnetv2_configs.get_model_config(model_name))
    config.override(datasets.get_dataset_config(dataset_cfg))
    config.model.num_classes = config.data.num_classes

    # epochs not needed
    train_split = "train"
    image_dtype = "bfloat16"
    train_size = config.train.isize
    eval_size = config.eval.isize

    if train_size <= 16.:
            train_size = int(eval_size * train_size) // 16 * 16
    image_size = train_size

    ds_params = {}
    ds_params["batch_size"] = config.train.batch_size
    ds = datasets.build_dataset_input(True, image_size, image_dtype, data_dir, train_split, config.data).input_fn(ds_params)

    return ds
