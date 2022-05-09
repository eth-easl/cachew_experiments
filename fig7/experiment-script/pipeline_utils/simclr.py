from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import time

import tensorflow
import tensorflow.compat.v2 as tf
import tensorflow_datasets as tfds
from absl import flags

import sys
sys.path.append("/home/aymond/ml_input_processing/experiments/ml/simclr")

from data import build_input_fn

FLAGS = flags.FLAGS

flags.DEFINE_bool(
    'augment', True,
    'Whether to do any augmentation of the data. Should always be true when training!')

flags.DEFINE_integer(
    'image_size', 224,
    'Input image size.')

flags.DEFINE_string(
    'train_split', 'train',
    'Split for training.')

flags.DEFINE_string(
    'eval_split', 'validation',
    'Split for evaluation.')

flags.DEFINE_bool(
    'cache_dataset', False,
    'Whether to cache the entire dataset in memory. If the dataset is '
    'ImageNet, this is a very bad idea, but for smaller datasets it can '
    'improve performance.')

flags.DEFINE_bool(
    'shuffle_files', False,
    'Whether to shuffle the training files')

flags.DEFINE_enum(
    'train_mode', 'pretrain', ['pretrain', 'finetune'],
    'The train mode controls different objectives and trainable components.')

flags.DEFINE_float(
    'color_jitter_strength', 1.0,
    'The strength of color jittering.')

flags.DEFINE_boolean(
    'use_blur', True,
    'Whether or not to use Gaussian blur for augmentation during pretraining.')

flags.DEFINE_boolean(
    'blur_in_model', True, # Test this!!!
    'Whether apply the Gaussian blur withing the model call (True, default) or in the input pipeline.')

flags.DEFINE_bool(
    'caching', False,
    'Whether to cache the dataset after augmentation.')

def make_dataset(params):
    train_batch_size = 256
    data_dir = "gs://tfdata-datasets/imagenet_tfds/imagenet_tfds"
    
    builder = tfds.builder("imagenet2012", data_dir=data_dir)

    nb_train_imgs = builder.info.splits['train'].num_examples
    batches_per_ep = nb_train_imgs//train_batch_size

    is_training = True
    input_context = tf.distribute.InputContext(
                num_input_pipelines=1, input_pipeline_id=0, num_replicas_in_sync=1
                )
    input_fn = build_input_fn(builder, train_batch_size, None, is_training)

    dataset = input_fn(input_context)
    
    return dataset
