CACHE_DIR=$HOME/training-data/cache_temp
#CACHE_DIR=/training-data/cache_temp
#DATA_DIR="$HOME/training-data/coco"
DATA_DIR="gs://tfdata-datasets/coco"
stop_instance_when_done=false

timestamp=$(date "+%Y-%m-%d-%Hh%Mm%S")
exp_name="test_autoscale"
model_dir="gs://tfdata-train-logs/retinanet/$timestamp-TPU-$exp_name"
log_out="$HOME/logs/retinanet-$exp_name-$timestamp.txt"

LOCAL_WORKERS=0
TPU_NAME="tfdata-tpu-vm" # TODO: change this to own TPU machine
TPU_VM=true
RESNET_CHECKPOINT="gs://cloud-tpu-checkpoints/retinanet/resnet50-checkpoint-2018-02-07"
TRAIN_FILE_PATTERN="$DATA_DIR/train-*"
EVAL_FILE_PATTERN="$DATA_DIR/val-*"
VAL_JSON_FILE="$DATA_DIR/raw-data/annotations/instances_val2017.json"
ITERS_PER_LOOP=1848 # 1848 steps = 1 epoch

epochs=6 # default: 13
total_steps=$(($epochs * $ITERS_PER_LOOP))
eval=false

save_checkpoint_freq=0
rm -r $CACHE_DIR/*

if [ "$TPU_VM" = true ]; then
  TPU_ADDRESS="local"
else
  TPU_ADDRESS=$TPU_NAME
fi

run_file="$HOME/ml_input_processing/experiments/ml/models/official/vision/detection/main.py"
echo "Launching training..."

python3 $run_file \
  --local_workers="${LOCAL_WORKERS}" \
  --strategy_type=tpu \
  --tpu="${TPU_ADDRESS?}" \
  --model_dir="${model_dir?}" \
  --save_checkpoint_freq=$save_checkpoint_freq \
  --mode=train \
  --params_override="{ type: retinanet, train: { checkpoint: { path: ${RESNET_CHECKPOINT?}, prefix: resnet50/ }, train_file_pattern: ${TRAIN_FILE_PATTERN?}, iterations_per_loop: ${ITERS_PER_LOOP}, total_steps: ${total_steps}}, eval: { val_json_file: ${VAL_JSON_FILE?}, eval_file_pattern: ${EVAL_FILE_PATTERN?}, num_steps_per_eval: ${ITERS_PER_LOOP} } }" 2>&1 | tee $log_out

echo "Finished training!"

if [ "$eval" = true ]; then
  echo "Running evaluation..."

  python3 $run_file \
    --local_workers="${LOCAL_WORKERS}" \
    --strategy_type=tpu \
    --tpu="${TPU_ADDRESS?}" \
    --model_dir="${model_dir?}" \
    --mode=eval \
    --params_override="{ type: retinanet, eval: { val_json_file: ${VAL_JSON_FILE?}, eval_file_pattern: ${EVAL_FILE_PATTERN?}, num_steps_per_eval: ${ITERS_PER_LOOP}, eval_samples: 5000 } }"

  echo "Finished evaluation!"
fi

ZONE=us-central1-a

if [ "$stop_instance_when_done" = true ]; then
  echo "WARNING: Deleting training disk and stopping instance in 60 seconds..."
  for i in $(seq 1 1 59); do
    sleep 1
    echo $((60 - $i))
  done

  if [ "$TPU_VM" = true ]; then
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

  if [ "$TPU_VM" = true ]; then
    # stop TPU VM
    gcloud alpha compute tpus tpu-vm stop $TPU_NAME --zone=$ZONE

  else
    # stop TPU node
    gcloud compute tpus stop $HOSTNAME --zone=$ZONE

    # stop instance
    gcloud compute instances stop $HOSTNAME --zone $ZONE

  fi
fi
