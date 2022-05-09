import tensorflow as tf
import numpy as np
import math
import random
import os

import sys
currentdir = os.path.dirname(os.path.realpath(__file__))
vision_dir = os.path.dirname(currentdir)
official_dir = os.path.dirname(vision_dir)
models_dir = os.path.dirname(official_dir)
sys.path.append(models_dir)

from official.vision.detection.dataloader import input_reader
from official.modeling.hyperparams import params_dict
from official.vision.detection.configs.retinanet_config import RETINANET_CFG

epochs = 1
batch_size = 64 # 64
nb_train_imgs = 118287
num_examples = nb_train_imgs
steps_per_ep = num_examples//batch_size + 1
#training_file_pattern = '/training-data/coco/train-*'
training_file_pattern = "gs://tfdata-datasets/coco/train-*"
#training_file_pattern = '/home/tgyal/training-data/coco/train-*'

RETINANET_CFG.override({
    'train': {
        'batch_size': batch_size
    }
}, is_strict=False)

def process_epoch(dataset, steps_per_ep):
    i=0
    for _ in dataset:
        i=i+1
        print(f"  batch {i}/{steps_per_ep}", end='\r')
        if i >= steps_per_ep:
            break
    print(f"got {i} out of {steps_per_ep} batches")


train_input_fn = input_reader.InputFn(
        file_pattern=training_file_pattern,
        params=RETINANET_CFG,
        mode=input_reader.ModeKeys.TRAIN,
        batch_size=batch_size,
        num_examples=num_examples)
dataset = train_input_fn()

for i in range(epochs):
    print(f"Epoch {i+1}/{epochs}")
    """
    for t in dataset.take(1):
        print(t[0].shape)
        print(t[0].dtype)
        values = t[1].values()
        index = 0
        for e in t[1].values():
            if index in [0, 1, 2]:
                print(type(e))
                for el in e.values():
                    print(el.shape)
                    print(el.dtype)
            else:
                print(e.shape)
                print(e.dtype)
            index += 1
    """
    process_epoch(dataset, steps_per_ep)
    print("")
