from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import time

import tensorflow
import tensorflow.compat.v2 as tf

import sys
sys.path.append("/home/aymond/ml_input_processing/experiments/ml/models")

from official.vision.detection.dataloader import input_reader
from official.modeling.hyperparams import params_dict
from official.vision.detection.configs.retinanet_config import RETINANET_CFG


def make_dataset(params):
    """Input function which provides batches for training."""

    batch_size = params["batch_size"]  # 64
    nb_train_imgs = params["nb_train_imgs"] #118287
    num_examples = nb_train_imgs
    training_file_pattern = params["training_file_pattern"] #'./gluster/training-data/coco/train-*'

    RETINANET_CFG.override({
        'train': {
            'batch_size': batch_size
        }
    }, is_strict=False)

    train_input_fn = input_reader.InputFn(
        file_pattern=training_file_pattern,
        params=RETINANET_CFG,
        mode=input_reader.ModeKeys.TRAIN,
        batch_size=batch_size,
        num_examples=num_examples)
    dataset = train_input_fn()

    return dataset
