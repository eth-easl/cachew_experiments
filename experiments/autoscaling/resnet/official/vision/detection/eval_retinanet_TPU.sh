CACHE_DIR=$HOME/training-data/cache_temp
#CACHE_DIR=/training-data/cache_temp
DATA_DIR="$HOME/training-data/coco"
#DATA_DIR="gs://tfdata-datasets/coco"
stop_instance_when_done=false

exp_name="2021-07-23-14h58m11-TPU-Baseline_SSD"
#model_dir="gs://tfdata-train-logs/retinanet/$timestamp-TPU-$exp_name"
model_dir="gs://tfdata-train-logs/retinanet/$exp_name"
log_out="$HOME/logs/retinanet-eval-$exp_name.txt"

TPU_NAME="tfdata-tpu-vm"
TPU_VM=true
TRAIN_FILE_PATTERN="$DATA_DIR/train-*"
EVAL_FILE_PATTERN="$DATA_DIR/val-*"
VAL_JSON_FILE="$DATA_DIR/raw-data/annotations/instances_val2017.json"
ITERS_PER_LOOP=1848 # 1848 steps = 1 epoch


if [ "$TPU_VM" = true ] ; then
    TPU_ADDRESS="local"
else
    TPU_ADDRESS=$TPU_NAME
fi

run_file="$HOME/ml_input_processing/experiments/ml/models/official/vision/detection/main.py"

echo "Running evaluation..."

python3 $run_file \
  --strategy_type=tpu \
  --tpu="${TPU_ADDRESS?}" \
  --model_dir="${model_dir?}" \
  --mode=eval \
  --params_override="{ type: retinanet, eval: { val_json_file: ${VAL_JSON_FILE?}, eval_file_pattern: ${EVAL_FILE_PATTERN?}, num_steps_per_eval: ${ITERS_PER_LOOP}, eval_samples: 5000 } }"

echo "Finished evaluation!"

ZONE=us-central1-a

if [ "$stop_instance_when_done" = true ] ; then
    echo "WARNING: Deleting training disk and stopping instance in 60 seconds..."
    for i in $(seq 1 1 59); do
        sleep 1
        echo $((60-$i))
    done
    
    if [ "$TPU_VM" = true ] ; then
        #sudo umount /dev/sdb $HOME/training-data
        DISK_NAME="$TPU_NAME-training-data"
    else
        sudo umount /dev/sdb /training-data
        DISK_NAME="$HOSTNAME-training-data"
        
        echo "Detaching $DISK_NAME disk..."
        gcloud compute instances detach-disk $HOSTNAME --disk $DISK_NAME --zone $ZONE
    fi

    #echo "Deleting $DISK_NAME disk..."
    #gcloud compute disks delete $DISK_NAME --zone $ZONE --quiet
    
    if [ "$TPU_VM" = true ] ; then
        # stop TPU VM
        gcloud alpha compute tpus tpu-vm stop $TPU_NAME --zone=$ZONE
        
    else
        # stop TPU node
        gcloud compute tpus stop $HOSTNAME --zone=$ZONE
        
        # stop instance
        gcloud compute instances stop $HOSTNAME --zone $ZONE
    
    fi
fi
