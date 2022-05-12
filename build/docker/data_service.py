# Copyright 2020 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Run a tf.data service server."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from absl import app
from absl import flags
import tensorflow as tf
import os
import yaml

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'

FLAGS = flags.FLAGS

flags.DEFINE_integer("port", 0, "Port to listen on")
flags.DEFINE_bool("is_dispatcher", False, "Whether to start a dispatcher (as opposed to a worker server")
flags.DEFINE_string("dispatcher_address", "", "The address of the dispatcher. This is only needed when starting a worker server.")
flags.DEFINE_string("worker_address", "", "The address of the worker server. This is only needed when starting a worker server.")
flags.DEFINE_integer("worker_heartbeat_interval_ms", None, "The hearbeat interval between worker and dispatcher.")

# EASL introduce
flags.DEFINE_integer("cache_policy", 1, "The cache policy the dispatcher should apply.")
flags.DEFINE_integer("cache_format", 2, "The cache file format the dispatcher should tell the workers to use.")
flags.DEFINE_integer("cache_compression", 1, "The cache compression format the dispatcher should tell the workers to use.")
flags.DEFINE_integer("cache_ops_parallelism", 8, "The number of readers/writers the dispatcher should tell the workers to use.")
flags.DEFINE_string("cache_path", "./outputs/", "The base path to use for the cache content.")
flags.DEFINE_integer("scaling_policy", 1, "The scaling policy the dispatcher should apply.")
# TODO update? The log_dir flag is already defined by the absl module. We just use the existing one for this simple script.
#flags.DEFINE_string("log_dir", "", "The path to use for dumping metrics at dispatcher. No logs printed if empty.")
flags.DEFINE_integer("log_dumps_interval_ms", 50, "The interval at which the dispatcher should dump log files.")
flags.DEFINE_integer("vlog", 0, "The tensorflow vlog level to set.")

flags.DEFINE_string("config", "", "Specifies the path to the config file. Empty string signifies no config and is ignored.")

FLAGS = flags.FLAGS


def parse_config():
    with open(FLAGS.config) as config_file:
        config = yaml.safe_load(config_file.read())

    return config


def main(unused_argv):
    if FLAGS.config != "":
        yaml_config = parse_config()
        os.environ['TF_CPP_MAX_VLOG_LEVEL'] = str(yaml_config["vlog"])
    else:
        os.environ['TF_CPP_MAX_VLOG_LEVEL'] = str(FLAGS.vlog)

    if FLAGS.is_dispatcher:
        print("Starting tf.data service dispatcher")
        if FLAGS.config != "":  # assume there is a config file
            print("HERE!")
            print(yaml_config["scaling_policy"])
            print(type(yaml_config["scaling_policy"]))
            dispacher_config = tf.data.experimental.service.DispatcherConfig(
                port=yaml_config["port"],
                protocol="grpc",
                cache_policy=yaml_config["cache_policy"],
                cache_format=yaml_config["cache_format"],
                cache_compression=yaml_config["cache_compression"],
                cache_ops_parallelism=yaml_config["cache_ops_parallelism"],
                cache_path=yaml_config["cache_path"],
                scaling_policy=yaml_config["scaling_policy"],
                log_dir=yaml_config["log_dir"],
                log_dumps_interval_ms=yaml_config["log_dumps_interval_ms"]
            )
        else:
            dispacher_config = tf.data.experimental.service.DispatcherConfig(
                port=FLAGS.port,
                protocol="grpc",
                cache_policy=FLAGS.cache_policy,
                cache_format=FLAGS.cache_format,
                cache_compression=FLAGS.cache_compression,
                cache_ops_parallelism=FLAGS.cache_ops_parallelism,
                cache_path=FLAGS.cache_path,
                scaling_policy=FLAGS.scaling_policy,
                log_dir=FLAGS.log_dir,
                log_dumps_interval_ms=FLAGS.log_dumps_interval_ms
            )

        server = tf.data.experimental.service.DispatchServer(dispacher_config)
    else:
        print("Starting tf.data service worker")
        if FLAGS.config != "" : # assume there is a config file
            worker_config = tf.data.experimental.service.WorkerConfig(
                port=yaml_config["port"],
                protocol="grpc",
                dispatcher_address=yaml_config["dispatcher_address"],
                worker_address=yaml_config["worker_address"],
                heartbeat_interval_ms=yaml_config["worker_heartbeat_interval_ms"]
            )
        else:
            worker_config = tf.data.experimental.service.WorkerConfig(
                port=FLAGS.port,
                protocol="grpc",
                dispatcher_address=FLAGS.dispatcher_address,
                worker_address=FLAGS.worker_address,
                heartbeat_interval_ms=FLAGS.worker_heartbeat_interval_ms)
        server = tf.data.experimental.service.WorkerServer(worker_config)

    print("Blocking on ")
    server.join()


if __name__ == "__main__":
  tf.compat.v1.app.run()
