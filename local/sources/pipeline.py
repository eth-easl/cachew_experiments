import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'
os.environ['TF_CPP_MAX_VLOG_LEVEL'] = '0'

import tensorflow as tf
import time

EPOCH_COUNT = 2 
DISPATCHER_TARGET = "grpc://localhost:40000"  # We assume the dispatcher is running on localhost:40000

dataset = tf.data.Dataset.from_tensor_slices(list(range(100)))
dataset = dataset.apply(tf.data.experimental.mark("source_cache"))  # The autocache marker node
dataset = dataset.map(lambda x: x + 1)
dataset = dataset.apply(tf.data.experimental.sleep(int(400 * 1000)))  # Sleep 400 ms
dataset = dataset.apply(tf.data.experimental.service.distribute(
    processing_mode="distributed_epoch", service=DISPATCHER_TARGET, 
    job_name="my_job"))  # Distribute the input pipeline to the tf.data service

print("Starting training...")
for epoch in range(EPOCH_COUNT):
  print(f"Starting epoch number {epoch + 1}...")
  process_time = time.time()
  for i in dataset:
    time.sleep(0.2)
  process_time = time.time() - process_time
  print(f"Epoch number {epoch + 1} has completed in {process_time} seconds!")
print("Training done!")