timestamp=$(date "+%Y-%m-%d-%Hh%Mm%S")
log_out="$HOME/logs/maskrcnn_$timestamp.txt"
#model_dir="model_dir"
model_dir="gs://tfdata-train-logs/maskRCNN/$timestamp-Test"

save_checkpoint_freq=2000
#num_gpus=1
#strategy_type="one_device"
num_gpus=4
strategy_type="mirrored"
config_file="$HOME/ml_input_processing/experiments/ml/models/official/vision/detection/mymaskrcnn.yaml"

run_file="$HOME/ml_input_processing/experiments/ml/models/official/vision/detection/main.py"

python3 $run_file --strategy_type=$strategy_type  --num_gpus=$num_gpus  --model_dir=$model_dir  --save_checkpoint_freq=$save_checkpoint_freq  --mode=train  --model=mask_rcnn  --config_file=$config_file 2>&1 | tee $log_out