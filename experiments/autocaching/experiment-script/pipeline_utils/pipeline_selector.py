from . import random_dataset
from . import sleep_synthetic_dataset
from . import synthetic_dataset
#from . import resnet_imagenet
from . import distribute_dataset
from . import read_inflate_sleep
#from . import resnet_model_garden
#from . import resnet_model_garden
#from . import retinanet
#from . import efficient_net
#from . import simclr

import tensorflow as tf


def make_dataset(pipeline_cfg_dict):
    if pipeline_cfg_dict["name"] == "random_dataset":
        return random_dataset.make_dataset(pipeline_cfg_dict["params"])
    elif pipeline_cfg_dict["name"] == "sleep_synthetic_dataset":
        return sleep_synthetic_dataset.make_dataset(pipeline_cfg_dict["params"])
    elif pipeline_cfg_dict["name"] == "synthetic_dataset":
        return synthetic_dataset.make_dataset(pipeline_cfg_dict["params"])
    elif pipeline_cfg_dict["name"] == "test_dataset":
        print("test dataset")
        dataset = tf.data.Dataset.range(500)
        dataset = dataset.apply(tf.data.experimental.sleep(100000))
        dataset = dataset.apply(tf.data.experimental.mark("source_cache"))

        return dataset
    elif pipeline_cfg_dict["name"] == "resnet_imagenet":
        return resnet_imagenet.make_dataset(pipeline_cfg_dict["params"])
    elif pipeline_cfg_dict["name"] == "distribute_dataset":
        return distribute_dataset.make_dataset(pipeline_cfg_dict["params"])
    elif pipeline_cfg_dict["name"] == "read_inflate_sleep":
        return read_inflate_sleep.make_dataset(pipeline_cfg_dict["params"])
    elif pipeline_cfg_dict["name"] == "resnet_model_garden":
        return resnet_model_garden.make_dataset(pipeline_cfg_dict["params"])
    elif pipeline_cfg_dict["name"] == "retinanet":
        return retinanet.make_dataset(pipeline_cfg_dict["params"])
    elif pipeline_cfg_dict["name"] == "efficient_net":
        return efficient_net.make_dataset(pipeline_cfg_dict["params"])
    elif pipeline_cfg_dict["name"] == "simclr":
        return simclr.make_dataset(pipeline_cfg_dict["params"])
