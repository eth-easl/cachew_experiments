# Copyright 2021 The TensorFlow Authors. All Rights Reserved.
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

"""Data loader and input processing."""

from __future__ import absolute_import
from __future__ import division
# from __future__ import google_type_annotations
from __future__ import print_function

import tensorflow as tf

import os
import glob
from typing import Text, Optional
from official.modeling.hyperparams import params_dict
from official.vision.detection.dataloader import factory
from official.vision.detection.dataloader import mode_keys as ModeKeys

DATA_AUGM_REPEAT = None
# CACHE_DIR = "/training-data/cache_temp"
CACHE_DIR = f"{os.getenv('HOME')}/training-data/cache_temp"
CACHE_PARALLELISM = 16
DISPATCHER_IP = 'aymond-cachew-dispatcher-kb8w'  # TODO: change this to your own deployed dispatcher
# DISPATCHER_IP=None
MAX_PIPELINING = 8
MAX_OUTSTANDING_REQUESTS = 96
TAKE1_CACHE_REPEAT = False

shuffle_buffer = 1000


class InputFn(object):
    """Input function that creates dataset from files."""

    def __init__(self,
                 file_pattern: Text,
                 params: params_dict.ParamsDict,
                 mode: Text,
                 batch_size: int,
                 num_examples: Optional[int] = -1):
        """Initialize.

        Args:
          file_pattern: the file pattern for the data example (TFRecords).
          params: the parameter object for constructing example parser and model.
          mode: ModeKeys.TRAIN or ModeKeys.Eval
          batch_size: the data batch size.
          num_examples: If positive, only takes this number of examples and raise
            tf.errors.OutOfRangeError after that. If non-positive, it will be
            ignored.
        """
        assert file_pattern is not None
        assert mode is not None
        assert batch_size is not None
        self._file_pattern = file_pattern
        self._mode = mode
        self._is_training = (mode == ModeKeys.TRAIN)
        self._batch_size = batch_size
        self._num_examples = num_examples
        self._parser_fn = factory.parser_generator(params, mode)
        self._dataset_fn = tf.data.TFRecordDataset

        self._input_sharding = (not self._is_training)
        try:
            if self._is_training:
                self._input_sharding = params.train.input_sharding
            else:
                self._input_sharding = params.eval.input_sharding
        except AttributeError:
            pass

    def __call__(self, ctx=None, batch_size: int = None):
        """Provides tf.data.Dataset object.

        Args:
          ctx: context object.
          batch_size: expected batch size input data.

        Returns:
          tf.data.Dataset object.
        """
        if not batch_size:
            batch_size = self._batch_size
        assert batch_size is not None
        files_list = tf.io.gfile.glob(self._file_pattern)  # glob.glob(self._file_pattern)
        dataset = tf.data.Dataset.from_tensor_slices(files_list)
        # dataset = dataset.shuffle(len(files_list))
        # dataset = tf.data.Dataset.list_files(
        #    self._file_pattern, shuffle=self._is_training)

        if self._input_sharding and ctx and ctx.num_input_pipelines > 1:
            dataset = dataset.shard(ctx.num_input_pipelines, ctx.input_pipeline_id)
        # dataset = dataset.cache()

        if self._is_training and DATA_AUGM_REPEAT is None and DISPATCHER_IP is None:
            dataset = dataset.repeat()

        dataset = dataset.interleave(
            map_func=self._dataset_fn,
            cycle_length=32,
            num_parallel_calls=tf.data.experimental.AUTOTUNE)

        dataset = dataset.apply(tf.data.experimental.mark("source_cache"))

        if self._is_training:
            dataset = dataset.shuffle(shuffle_buffer)
        if self._num_examples > 0:
            dataset = dataset.take(self._num_examples)

        # Parses the fetched records to input tensors for model function.
        dataset = dataset.map(
            self._parser_fn, num_parallel_calls=tf.data.experimental.AUTOTUNE)
        dataset = dataset.batch(batch_size, drop_remainder=True)
        dataset = dataset.prefetch(tf.data.experimental.AUTOTUNE)

        if TAKE1_CACHE_REPEAT:
            dataset = dataset.take(1).cache().repeat()
        # return dataset.element_spec

        if DISPATCHER_IP is not None and self._is_training:
            dataset = dataset.apply(tf.data.experimental.service.distribute(
                processing_mode="distributed_epoch", service="grpc://" + DISPATCHER_IP + ":31000",
                max_outstanding_requests=MAX_OUTSTANDING_REQUESTS, max_request_pipelining_per_worker=MAX_PIPELINING,
                compression=None
            ))
            dataset = dataset.repeat()

        # Caching
        if self._is_training and DATA_AUGM_REPEAT is not None:
            snapshot_path = CACHE_DIR + "/snapshot_{:03d}"

            cache_format = 2
            cache_compression = 1
            parallelism = 8

            # Periodic caching using tf.data.experimental.service_cache_put
            dataset = dataset.apply(tf.data.experimental.service_cache_put(CACHE_DIR,
                                                                           cache_format=cache_format,
                                                                           cache_compression=cache_compression,
                                                                           parallelism=CACHE_PARALLELISM))
            element_spec = dataset.element_spec
            # tf.print("ELEMENT_SPEC", element_spec)
            cached_dataset = tf.data.experimental.serviceCacheGetDataset(CACHE_DIR,
                                                                         cache_format=cache_format,
                                                                         cache_compression=cache_compression,
                                                                         parallelism=CACHE_PARALLELISM,
                                                                         element_spec=element_spec)
            # cached_dataset=cached_dataset.shuffle(buffer_size=shuffle_buffer)
            cached_dataset = cached_dataset.repeat(DATA_AUGM_REPEAT - 1)

            dataset = dataset.concatenate(cached_dataset)
            dataset = dataset.repeat()

            # Standard periodic caching
            # for ep in range(3):
            #    d = dataset.apply(tf.data.experimental.snapshot(snapshot_path.format(ep), compression=None))
            #    d = d.repeat(DATA_AUGM_REPEAT)
            #    if ep == 0:
            #        dataset_snapshot = d
            #    else:
            #        dataset_snapshot = dataset_snapshot.concatenate(d)
        #
        # dataset = dataset_snapshot.repeat()

        # Partial periodic caching
        # cache_ratio = 0.5
        # nb_batches_to_cache = int(cache_ratio * NUM_IMAGES['train'] / batch_size)
        # for i in range(3):
        #    cache_dataset = dataset.take(nb_batches_to_cache)    
        #    fresh_dataset = dataset.skip(nb_batches_to_cache)
        #    cache_dataset = cache_dataset.apply(tf.data.experimental.snapshot(snapshot_path.format(i), compression=None))
        #    
        #    #d = cache_dataset.concatenate(fresh_dataset)
        #    weights = [cache_ratio, 1-cache_ratio]
        #    d = tf.data.experimental.sample_from_datasets([cache_dataset, fresh_dataset], weights, seed=None)
        #    
        #    d = d.repeat(DATA_AUGM_REPEAT)
        #    if i == 0:
        #        dataset_snapshot = d
        #    else:
        #        dataset_snapshot = dataset_snapshot.concatenate(d)
        #
        # dataset = dataset_snapshot.repeat()

        # Adaptive periodic caching (hard-coded for 6-3-1 caching periods with boundaries at epochs [30, 60])
        # for snap_nb in range(30//6):
        #    d = dataset.apply(tf.data.experimental.snapshot(snapshot_path.format(snap_nb%3), compression=None))
        #    d = d.repeat(6)
        #    if snap_nb == 0:
        #        dataset_snapshot = d
        #    else:
        #        dataset_snapshot = dataset_snapshot.concatenate(d)
        #
        # for snap_nb in range(30//6, 30//6 + (60-30)//3):
        #    d = dataset.apply(tf.data.experimental.snapshot(snapshot_path.format(snap_nb%3), compression=None))
        #    d = d.repeat(3)
        #    dataset_snapshot = dataset_snapshot.concatenate(d)
        #
        # d = dataset.repeat()
        # dataset = dataset_snapshot.concatenate(d)

        return dataset
