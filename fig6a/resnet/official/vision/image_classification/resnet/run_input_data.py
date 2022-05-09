import tensorflow as tf
from imagenet_preprocessing import input_fn

data_dir = "/training-data/imagenet2012/tfrecords"; nb_train_imgs=1281167 # ImageNet
#data_dir = "/training-data/imagenet-tiny/tfrecords"; nb_train_imgs=100000 # Tiny
#data_dir = "/training-data/imagenet_test/tfrecords"; nb_train_imgs=4 # contains 4 images

epochs = 4
batch_size = 312*4
steps_per_ep = nb_train_imgs//batch_size + 1
filenames = None

def process_epoch(dataset, steps_per_ep):
    i=0
    for _ in dataset:
        i=i+1
        print(f"  batch {i}/{steps_per_ep}", end='\r')
        if i >= steps_per_ep:
            break

ds = input_fn(
    is_training=True,
    data_dir=data_dir,
    batch_size=batch_size,
    dtype=tf.float16,
    datasets_num_private_threads=32,
    drop_remainder=False,
    filenames=filenames,
)

for i in range(epochs):
    print(f"Epoch {i+1}/{epochs}")
    process_epoch(ds, steps_per_ep)
    print("")


