from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# TODO remove debugger.
import pdb

import os
import time

import tensorflow
import tensorflow.compat.v2 as tf

from absl import app
from absl import flags

FLAGS = flags.FLAGS
NUM_TRAIN_FILES = 10 # Updated
#SHUFFLE_BUFFER_SIZE = 10 # Updated

DEFAULT_IMAGE_SIZE = 64 # Updated
NUM_CHANNELS = 3

_R_MEAN = 123.68
_G_MEAN = 116.78
_B_MEAN = 103.94
CHANNEL_MEANS = [_R_MEAN, _G_MEAN, _B_MEAN]

flags.DEFINE_integer('batch_size', 192, 'The batch size to use.')
flags.DEFINE_integer('io_parallelism', tf.data.experimental.AUTOTUNE, 'The parallelism for interleave.')
flags.DEFINE_integer('map_parallelism', tf.data.experimental.AUTOTUNE, 'The parallelism for map.')
flags.DEFINE_integer('prefetch_buffer', tf.data.experimental.AUTOTUNE, 'The buffer size for prefetch.')
flags.DEFINE_integer('shuffle_buffer', 1024, 'The buffer size for shuffle.')


def _decode_crop_and_flip(image_buffer, bbox, num_channels):
  """Crops the given image to a random part of the image, and randomly flips.

  We use the fused decode_and_crop op, which performs better than the two ops
  used separately in series, but note that this requires that the image be
  passed in as an un-decoded string Tensor.

  Args:
    image_buffer: scalar string Tensor representing the raw JPEG image buffer.
    bbox: 3-D float Tensor of bounding boxes arranged [1, num_boxes, coords]
      where each coordinate is [0, 1) and the coordinates are arranged as [ymin,
      xmin, ymax, xmax].
    num_channels: Integer depth of the image buffer for decoding.

  Returns:
    3-D tensor with cropped image.
  """
  # A large fraction of image datasets contain a human-annotated bounding box
  # delineating the region of the image containing the object of interest.  We
  # choose to create a new bounding box for the object which is a randomly
  # distorted version of the human-annotated bounding box that obeys an
  # allowed range of aspect ratios, sizes and overlap with the human-annotated
  # bounding box. If no box is supplied, then we assume the bounding box is
  # the entire image.
  sample_distorted_bounding_box = tf.image.sample_distorted_bounding_box(
      tf.image.extract_jpeg_shape(image_buffer),
      bounding_boxes=bbox,
      min_object_covered=0.1,
      aspect_ratio_range=[0.75, 1.33],
      area_range=[0.05, 1.0],
      max_attempts=100,
      use_image_if_no_bounding_boxes=True)
  bbox_begin, bbox_size, _ = sample_distorted_bounding_box

  # Reassemble the bounding box in the format the crop op requires.
  offset_y, offset_x, _ = tf.unstack(bbox_begin)
  target_height, target_width, _ = tf.unstack(bbox_size)
  crop_window = tf.stack([offset_y, offset_x, target_height, target_width])

  # Use the fused decode and crop op here, which is faster than each in series.
  cropped = tf.image.decode_and_crop_jpeg(
      image_buffer, crop_window, channels=num_channels)

  # Flip to add a little more random distortion in.
  cropped = tf.image.random_flip_left_right(cropped)
  return cropped


def _mean_image_subtraction(image, means, num_channels):
  """Subtracts the given means from each image channel.

  For example:
    means = [123.68, 116.779, 103.939]
    image = _mean_image_subtraction(image, means)
  Note that the rank of `image` must be known.

  Args:
    image: a tensor of size [height, width, C].
    means: a C-vector of values to subtract from each channel.
    num_channels: number of color channels in the image that will be distorted.

  Returns:
    the centered image.

  Raises:
    ValueError: If the rank of `image` is unknown, if `image` has a rank other
      than three or if the number of channels in `image` doesn't match the
      number of values in `means`.
  """
  if image.get_shape().ndims != 3:
    raise ValueError('Input must be of size [height, width, C>0]')

  if len(means) != num_channels:
    raise ValueError('len(means) must match the number of channels')

  # We have a 1-D tensor of means; convert to 3-D.
  # Note(b/130245863): we explicitly call `broadcast` instead of simply
  # expanding dimensions for better performance.
  means = tf.broadcast_to(means, tf.shape(image))

  return image - means


def _resize_image(image, height, width):
  """Simple wrapper around tf.resize_images.

  This is primarily to make sure we use the same `ResizeMethod` and other
  details each time.

  Args:
    image: A 3-D image `Tensor`.
    height: The target height for the resized image.
    width: The target width for the resized image.

  Returns:
    resized_image: A 3-D tensor containing the resized image. The first two
      dimensions have the shape [height, width].
  """
  return tensorflow.compat.v1.image.resize(
      image, [height, width],
      method=tf.image.ResizeMethod.BILINEAR,
      align_corners=False)


def preprocess_image(image_buffer, bbox, output_height, output_width,
                     num_channels):
  """Preprocesses the given image.

  Preprocessing includes decoding, cropping, and resizing for both training
  and eval images. Training preprocessing, however, introduces some random
  distortion of the image to improve accuracy.

  Args:
    image_buffer: scalar string Tensor representing the raw JPEG image buffer.
    bbox: 3-D float Tensor of bounding boxes arranged [1, num_boxes, coords]
      where each coordinate is [0, 1) and the coordinates are arranged as [ymin,
      xmin, ymax, xmax].
    output_height: The height of the image after preprocessing.
    output_width: The width of the image after preprocessing.
    num_channels: Integer depth of the image buffer for decoding.

  Returns:
    A preprocessed image.
  """
  image = _decode_crop_and_flip(image_buffer, bbox, num_channels)
  image = _resize_image(image, output_height, output_width)
  image.set_shape([output_height, output_width, num_channels])
  return _mean_image_subtraction(image, CHANNEL_MEANS, num_channels)


def parse_example_proto(example_serialized):
  """Parses an Example proto containing a training example of an image.

  The output of the is a dataset containing serialized Example protocol buffers.
  Each Example proto contains the following fields (with example values):
    image/height: 462
    image/width: 581
    image/colorspace: 'RGB'
    image/channels: 3
    image/class/label: 615
    image/class/synset: 'n03623198'
    ###image/class/text: 'knee pad'
    ###image/object/bbox/xmin: 0.1
    ###image/object/bbox/xmax: 0.9
    ###image/object/bbox/ymin: 0.2
    ###image/object/bbox/ymax: 0.6
    ###image/object/bbox/label: 615
    image/format: 'JPEG'
    image/filename: 'ILSVRC2012_val_00041207.JPEG'
    image/encoded: <JPEG encoded string>

  Args:
    example_serialized: scalar Tensor tf.string containing a serialized Example
      protocol buffer.

  Returns:
    image_buffer: Tensor tf.string containing the contents of a JPEG file.
    label: Tensor tf.int32 containing the label.
    bbox: 3-D float Tensor of bounding boxes arranged [1, num_boxes, coords]
      where each coordinate is [0, 1) and the coordinates are arranged as
      [ymin, xmin, ymax, xmax].
  """
  # Dense features in Example proto.
  feature_map = {
      'image/encoded':
          tf.io.FixedLenFeature([], dtype=tf.string, default_value=''),
      'image/class/label':
          tf.io.FixedLenFeature([], dtype=tf.int64, default_value=-1),
      'image/class/text': # not present in the TFRecord files, the parsing function seems to ignore this...
          tf.io.FixedLenFeature([], dtype=tf.string, default_value=''),
  }

  # No bbox in our tiny-imagenet TFRecord files.

  sparse_float32 = tf.io.VarLenFeature(dtype=tf.float32)
  # Sparse features in Example proto.
  feature_map.update({
      k: sparse_float32 for k in [
          'image/object/bbox/xmin', 'image/object/bbox/ymin',
          'image/object/bbox/xmax', 'image/object/bbox/ymax'
      ]
  }) # will just be ignored since we do not have bbox features in our TFRecords.

  features = tf.io.parse_single_example(
      serialized=example_serialized, features=feature_map)
  label = tf.cast(features['image/class/label'], dtype=tf.int32)

  xmin = tf.expand_dims(features['image/object/bbox/xmin'].values, 0)
  ymin = tf.expand_dims(features['image/object/bbox/ymin'].values, 0)
  xmax = tf.expand_dims(features['image/object/bbox/xmax'].values, 0)
  ymax = tf.expand_dims(features['image/object/bbox/ymax'].values, 0)

  # Note that we impose an ordering of (y, x) just to make life difficult.
  bbox = tf.concat([ymin, xmin, ymax, xmax], 0)

  # Force the variable number of bounding boxes into the shape
  # [1, num_boxes, coords].
  bbox = tf.expand_dims(bbox, 0)
  bbox = tf.transpose(a=bbox, perm=[0, 2, 1])

  # replace bbox with 0, 1.
  #bbox = tf.constant([0.0, 0.0, 1.0, 1.0], dtype=tf.float32, shape=[1, 1, 4])

  return features['image/encoded'], label, bbox


def parse_record(serialized_example):
  """Parses a record containing a training example of an image.

  The input record is parsed into a label and image, and the image is passed
  through preprocessing steps (cropping, flipping, and so on).

  Args:
    serialized_example: A scalar Tensor tf.string containing a serialized
      Example protocol buffer.

  Returns:
    Tuple with processed image tensor in a channel-last format and
    one-hot-encoded label tensor.
  """
  image_buffer, label, bbox = parse_example_proto(serialized_example)

  image = preprocess_image(
      image_buffer=image_buffer,
      bbox=bbox,
      output_height=DEFAULT_IMAGE_SIZE,
      output_width=DEFAULT_IMAGE_SIZE,
      num_channels=NUM_CHANNELS)
  image = tf.cast(image, tf.float32)

  # Subtract one so that labels are in [0, 1000), and cast to float32 for
  # Keras model.
  label = tf.cast(
      tf.cast(tf.reshape(label, shape=[1]), dtype=tf.int32) - 1,
      dtype=tf.float32)
  return image, label

def _get_filenames(data_path):
  """Return filenames for dataset."""
  return [
      os.path.join(data_path, 'train-%05d-of-%05d' % (i, NUM_TRAIN_FILES))
      for i in range(NUM_TRAIN_FILES)
      ]


def make_dataset(data_path):
  """Input function which provides batches for training."""
  filenames = _get_filenames(data_path)
  dataset = tf.data.Dataset.from_tensor_slices(filenames)
  dataset = dataset.shuffle(buffer_size=NUM_TRAIN_FILES)

  if FLAGS.io_parallelism:
    dataset = dataset.interleave(
        tf.data.TFRecordDataset,
        num_parallel_calls=FLAGS.io_parallelism,
        cycle_length=4)
  else:
    dataset = dataset.flat_map(tf.data.TFRecordDataset)


  # Shuffles records before repeating to respect epoch boundaries.
  if FLAGS.shuffle_buffer:
    dataset = dataset.shuffle(buffer_size=FLAGS.shuffle_buffer)

  # Parses the raw records into images and labels.
  dataset = dataset.map(
      parse_record, num_parallel_calls=FLAGS.map_parallelism)
  dataset = dataset.batch(FLAGS.batch_size)
  dataset = dataset.prefetch(buffer_size=FLAGS.prefetch_buffer)
  
  #dataset = dataset.apply(tf.data.experimental.snapshot("./", compression='SNAPPY'))

  return dataset


"""
def main(argv):
  del argv
  
  results = []

  dataset = make_dataset()

  @tf.function
  # todo add decorator
  def process_epoch(dataset):
    options = tf.data.Options()
    options.experimental_deterministic = FLAGS.deterministic
    options.experimental_optimization.map_and_batch_fusion = FLAGS.map_and_batch_fusion
    dataset = dataset.with_options(options)
    for _ in dataset:
      pass

  for _ in range(FLAGS.num_epochs):
    start = time.time()
    process_epoch(dataset)
    end = time.time()
    print('Epoch took: {}'.format(end - start))
    results.append(end - start)
    
  with open("results.log", "w") as logs:
    for r in results:
        logs.write(str(r) + ",\n")
        
        


if __name__ == '__main__':
  app.run(main)
  """
