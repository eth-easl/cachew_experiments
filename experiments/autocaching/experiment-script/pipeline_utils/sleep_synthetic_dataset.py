import tensorflow as tf
import numpy as np

from . import synthetic_dataset

#########################################################
#   Synthetic Sleep Dataset Generator
#########################################################
def synthetic_sleep_dataset_generator(columns, rows, bytes_per_row, datatype, sleep_time_microsec):
    assert(bytes_per_row <= 1024 * 1024 * 1024) # Do not allow rows larger than 1GB.

    num_unique_rows = 1
    num_repeat = rows

    el_per_column = int(np.ceil(bytes_per_row / (columns * datatype.size)))
    shape = [el_per_column]  # we will maybe vary the shape of individual tensors.

    dataset_arr = []

    for c in range(columns):
        column_arr = []
        for r in range(num_unique_rows):
            #element = tf.convert_to_tensor(np.random.rand(*shape), dtype=datatype)   # each column could have elements with multi-dim shape.
            element = tf.convert_to_tensor((np.random.rand(*shape)*0x7FFFFFFF) - (0x3FFFFFFF), dtype=datatype)

            column_arr.append(element)
        dataset_arr.append(column_arr)

    # Directly "zip" the columns here so that all datasets have the same number of ops
    dataset = tf.data.Dataset.from_tensor_slices(tuple(dataset_arr))
    dataset = dataset.repeat()
    dataset = dataset.take(num_repeat-1)
    # TODO remove source cache...
    dataset = dataset.apply(tf.data.experimental.mark("source_cache"))

    dataset = dataset.apply(tf.data.experimental.sleep(int(sleep_time_microsec)))

    return dataset

def make_dataset(params):
    rows = params["rows"]
    columns = params["columns"]
    bytes_per_row = params["bytes_per_row"]
    datatype = params["datatype"]
    sleep_time_msec = params["sleep_time_msec"] # to milisec

    # set defaults
    if rows is None:
        print("Setting default num rows")
        rows = 1000
    if columns is None:
        print("Setting default columns")
        columns = 1
    if bytes_per_row is None:
        print("Setting default bytes per row")
        bytes_per_row = 1024 * 1024 * 3 * 4  # images with three channels in float32.
    if datatype is None:
        datatype = tf.int32
    elif datatype == "int32":
        datatype = tf.int32
    elif datatype == "int64":
        datatype = tf.int64
    elif datatype == "float32":
        datatype = tf.float32
    if sleep_time_msec is None:
        print("Setting default sleep time")
        sleep_time_msec = 1000*1000 # 1sec in milisec.

    return synthetic_sleep_dataset_generator(columns, rows, bytes_per_row, datatype, sleep_time_msec*1000)
