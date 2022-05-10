import argparse
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'
os.environ['TF_CPP_MAX_VLOG_LEVEL'] = '0'

import tensorflow as tf

parser = argparse.ArgumentParser(description='Start up a tf.data worker.')
parser.add_argument('-d', '--dispatcher_port', type=int, default=40000,
                    help='The port of the dispatcher process')
parser.add_argument('-p', '--port', type=int, default=40001,
                    help='The port of this worker process')

args = parser.parse_args()

DISPATCHER_TARGET = f"localhost:{args.dispatcher_port}"
WORKER_TARGET = f"localhost:{args.port}"

# Start the worker
worker = tf.data.experimental.service.WorkerServer(
        tf.data.experimental.service.WorkerConfig(
                dispatcher_address=DISPATCHER_TARGET, 
                port=args.port, 
                protocol="grpc"
        )
)

worker.join()