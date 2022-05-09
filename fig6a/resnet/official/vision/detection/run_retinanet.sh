#CACHE_DIR=$HOME/training-data/cache_temp
CACHE_DIR=/training-data/cache_temp
stop_instance_when_done=true

timestamp=$(date "+%Y-%m-%d-%Hh%Mm%S")
exp_name="Test"
model_dir="gs://tfdata-train-logs/retinanet/$timestamp-$exp_name"
log_out="$HOME/logs/retinanet_$exp_name_$timestamp.txt"

save_checkpoint_freq=2000
#num_gpus=1
#strategy_type="one_device"
num_gpus=8
strategy_type="mirrored"
config_file="$HOME/ml_input_processing/experiments/ml/models/official/vision/detection/myretinanet.yaml"

run_file="$HOME/ml_input_processing/experiments/ml/models/official/vision/detection/main.py"

python3 $run_file --strategy_type=$strategy_type  --num_gpus=$num_gpus  --model_dir=$model_dir  --save_checkpoint_freq=$save_checkpoint_freq  --mode=train  --model=retinanet  --config_file=$config_file 2>&1 | tee $log_out


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
