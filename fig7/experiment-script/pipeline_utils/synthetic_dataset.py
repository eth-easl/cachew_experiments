import tensorflow as tf
import numpy as np


#########################################################
#   Synthetic Dataset Generator
#########################################################

def synthetic_dataset_generator(columns, rows, bytes_per_row, datatype):
    assert(bytes_per_row <= 1024 * 1024 * 1024) # Do not allow rows larger than 1GB.

    num_unique_rows = 1
    num_repeat = rows

    el_per_column = int(np.ceil(bytes_per_row / (columns * datatype.size)))
    shape = [el_per_column]  # we will maybe vary the shape of individual tensors.

    dataset_arr = []

    for c in range(columns):
        column_arr = []
        for r in range(num_unique_rows):
            element = tf.convert_to_tensor(np.random.rand(*shape), dtype=datatype)   # each column could have elements with multi-dim shape.
            column_arr.append(element)
        dataset_arr.append(column_arr)

    # Directly "zip" the columns here so that all datasets have the same number of ops
    return tf.data.Dataset.from_tensor_slices(tuple(dataset_arr)).repeat(num_repeat)


def make_dataset(params):
    rows = params["rows"]
    columns = params["columns"]
    bytes_per_row = params["bytes_per_row"]
    datatype = params["datatype"]

    # set defaults
    if rows is None:
        rows = 1000
    if columns is None:
        columns = 1
    if bytes_per_row is None:
        bytes_per_row = 1024 * 1024 * 3 * 4  # images with three channels in float32.
    if datatype is None:
        datatype = tf.int32
    elif datatype == "int32":
        datatype = tf.int32
    elif datatype == "int64":
        datatype = tf.int64

    return synthetic_dataset_generator(columns, rows, bytes_per_row, datatype)
