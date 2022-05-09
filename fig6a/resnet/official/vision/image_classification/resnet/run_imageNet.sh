#!/bin/bash

timestamp=$(date "+%Y-%m-%d-%Hh%Mm%S")
exp_name="Test"
model_dir="gs://tfdata-train-logs/resnet50/ImageNet/$timestamp-$exp_name"

# Choose the dataset directory here
#data_dir="/training-data/imagenet2012/tfrecords" # ImageNet from SSD
data_dir="gs://tfdata-imagenet" # ImageNet from GCS
#data_dir="/training-data/imagenet-tiny/tfrecords" # Tiny
#data_dir="/training-data/imagenet_test/tfrecords" # Test dataset with 4 images

epochs=90
target_accuracy=2 #"0.749"
stop_instance_when_done=true ##################WARNING##################

num_training_images=1281167 # ImageNet
#num_training_images=100000 # Tiny ImageNet
#num_training_images=4 # Test dataset

num_gpus=4
per_gpu_batch_size=312
batch_size=$(($per_gpu_batch_size * $num_gpus))
steps_per_loop=$(($num_training_images / $batch_size + 1))
enable_checkpoint_and_export="false" # save model
skip_eval=true

# remove old snapshots
rm -r /training-data/cache_temp/snapshot*

# commandline flags to the training script
params=""
params+="--num_gpus=$num_gpus "
params+="--dtype=fp16 "
params+="--batch_size=$batch_size "
params+="--train_epochs=$epochs "
params+="--target_accuracy=$target_accuracy "
params+="--skip_eval=$skip_eval "

params+="--epochs_between_evals=1 "
#params+="--optimizer=SGD "
#params+="--lr_schedule=polynomial "
#params+="--label_smoothing=0.1 "
#params+="--weight_decay=0.0002 "

params+="--report_accuracy_metrics=true "
params+="--log_steps=125 "
params+="--enable_tensorboard=false "

params+="--steps_per_loop=$steps_per_loop "
params+="--enable_eager=true "
params+="--tf_gpu_thread_mode=gpu_private " #gpu_private / gpu_shared / global
#params+="--per_gpu_thread_count=1 "
params+="--datasets_num_private_threads=32 "
params+="--data_dir=$data_dir "
params+="--model_dir=$model_dir "
params+="--enable_checkpoint_and_export=$enable_checkpoint_and_export "
params+="--single_l2_loss_op "
params+="--verbosity=0 "
#params+="--nouse_tf_function --nouse_tf_while_loop"


# Launch training
cmd="python3 resnet_ctl_imagenet_main.py ${params[@]}"
log_out="$HOME/logs/resnet50-$exp_name-$timestamp.txt"

echo "Running experiment '$exp_name'"
echo "Training model and piping output to $log_out ..."
${cmd[@]} 2>&1 | tee $log_out

echo ""
echo "Finished training!"

if [ "$stop_instance_when_done" = true ] ; then
    echo "WARNING: Deleting training disk and stopping instance in 60 seconds..."
    for i in $(seq 1 1 59); do
        sleep 1
        echo $((60-$i))
    done

    sudo umount /dev/sdb /training-data

    DISK_NAME="$HOSTNAME-training-data"
    echo "Detaching $DISK_NAME disk..."
    gcloud compute instances detach-disk $HOSTNAME --disk $DISK_NAME --zone us-central1-a

    echo "Deleting $DISK_NAME disk..."
    gcloud compute disks delete $DISK_NAME --zone us-central1-a --quiet

    # stop instance
    gcloud compute instances stop $HOSTNAME --zone us-central1-a
fi

