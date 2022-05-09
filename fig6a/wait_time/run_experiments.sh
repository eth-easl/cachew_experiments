#!/usr/bin/env bash

# Script parameters
mode=${1:-"compute"}
model=${2:-"resnet"}
runs=${3:-1}
base_log_dir=${4:-"${HOME}/logs"}
gcs_bucket="gs://aymond-cachew-simclr-wait-times/source_cache" #gs://easl-graurd-experiment-logs/wait_times  # If this is non-empty experiment results are copied to GCS at this address


# Model selection
if [ "${model}" == "resnet" ]; then
  echo "Running experiments on ResNet..."
  scale=(1 2 4 8)
  base_dir="/mnt/disks/data/sources/model_experiments/ml_input_processing/experiments/ml/models/official/vision/image_classification/resnet"
  executable="run_imageNet.sh"
  preprocessing_source="imagenet_preprocessing.py"
  service_loc="/mnt/disks/data/sources/easl-utils/tf-data/service"
  # We need to activate venv on GPU
  source /mnt/disks/data/venv/bin/activate
elif [ "${model}" == "retinanet" ]; then 
  echo "Running experiments on RetinaNet..."
  scale=(1 2 4 6 8)
  base_dir="/home/dan/ml_input_processing/experiments/ml/models/official/vision/detection"
  executable="run_retinanet_TPU.sh"
  preprocessing_source="dataloader/input_reader.py"
  service_loc="/home/dan/easl-utils/tf-data/service"
elif [ "${model}" == "efficientnet" ]; then 
  echo "Running experiments on EfficientNet..."
  scale=(2 4 8 16)
  base_dir="/home/dan/ml_input_processing/experiments/ml/automl/efficientnetv2"
  executable="run_effNetV2.sh"
  preprocessing_source="datasets.py"
  service_loc="/home/dan/easl-utils/tf-data/service"
elif [ "${model}" == "simCLR" ]; then
  echo "Running experiments on SimCLR..."
  scale=(1 2 4 8 10 14 16 18)
  base_dir="/home/aymond/ml_input_processing/experiments/ml/simclr"
  executable="train_imagenet.sh"
  preprocessing_source="data.py"
  service_loc="/home/aymond/easl-utils/tf-data/service"
else
  echo "ERROR: The selected model does not exist!"
  echo "Usage: ./run_experiments.sh <model> <runs> <base_log_dir>"
  exit
fi 

# Create log dir 
log_dir=${base_log_dir}/${model}_$( date +"%Y-%m-%d_%T" )
mkdir -p ${log_dir}
echo "Dumping metrics in ${log_dir}"

# Dump some organizational stats
(
tee "${log_dir}/config.json" <<-EOF
{
  "execution_mode": "${mode}",
  "model": "${model}",
  "runs": "${runs}",
  "scale": "${scale[@]}",
  "service_image:": $( cat ${service_loc}/default_config.yaml | head -n 2 | tail -n 1 | awk '{print $2}' ),
  "vm_name": "$( hostname )",
  "log_dir": "${log_dir}",
  "model_dir": "${base_dir}"
}
EOF
)

# Define function which does a run at a given scale
function run_one {(
  trap "exit 1" ERR

  run=${1}
  scale=${2}
  config_name=${3}

  # Run the experiment
  experiment_dir=${log_dir}/${scale}_workers/run_${run}
  cluster_log_dir=${experiment_dir}/cluster
  mkdir -p ${cluster_log_dir}  # Implicitly creates experiment_dir
  echo "Starting run ${run} with ${scale} workers and writing to ${experiment_dir}..."
  ( cd ${base_dir} && CACHEW_METRICS_DUMP=${experiment_dir}/metrics.csv ./${executable} > ${experiment_dir}/output.log 2>&1 )
  echo "Finished run ${run} with ${scale} workers!"

  # Dump the kubernetes cluster stats
  pods=$( kubectl get pods )
  echo "${pods}" > ${cluster_log_dir}/pods.txt
  
  echo "${pods}" | tail -n +2 | while read line; do
    pod_name=$( echo ${line} | awk '{print $1}' )
    kubectl logs ${pod_name} > ${cluster_log_dir}/${pod_name}.log
    kubectl describe pods ${pod_name} > ${cluster_log_dir}/${pod_name}_describe.txt
  done 

  # Restart the cluster
  echo "Restarting service..."
  python ${service_loc}/service_deploy.py --config=${config_name} --restart
  echo "Service restarted!"
)}

# Define a function which starts a cluster; note: must be in service folder when calling
function start_cluster {(
  local workers=${1}
  local cache_policy=${2}

  echo "Deploying service with ${workers} workers..."
  sed "s/num_workers:[ \t]\+[0-9]\+/num_workers: $workers/g" "${service_loc}/default_config.yaml" \
    | sed "s/cache_policy:[ \t]\+[0-9]\+/cache_policy: $cache_policy/g" > ${service_loc}/temp_config.yaml
  python ${service_loc}/service_deploy.py --config=${service_loc}/temp_config.yaml
  echo "Done deploying service!"
)}

# Define a function which terminates a cluster and logs events; note: must be in service folder when calling 
function terminate_cluster {(
  local scale=${1}

  # Log the node activity
  cluster_log_dir=${log_dir}/${scale}_workers/cluster
  mkdir -p ${cluster_log_dir}
  nodes="$( kubectl get nodes )"
  echo "${nodes}" > ${cluster_log_dir}/nodes.txt
  
  echo "${nodes}" | tail -n +2 | while read line; do
    node_name=$( echo ${line} | awk '{print $1}' )
    kubectl describe nodes ${node_name} > ${cluster_log_dir}/${node_name}_describe.txt
  done

  # Stop the service
  echo "Tearing down service..."
  python ${service_loc}/service_deploy.py --config=${service_loc}/temp_config.yaml --stop
  echo "Service torn down!"
)}

# Define a function which updates the dispatcher IP in the pre-processing scripts
function update_dispatcher {(
  dispatcher_name=$( kubectl get nodes | head -n 2 | tail -n 1 | awk '{print $1}' )
  sed -i "s/DISPATCHER_IP=['\"][a-zA-Z0-9-]*['\"]/DISPATCHER_IP='${dispatcher_name}'/" "${base_dir}/${preprocessing_source}"
)}

# Define a function which executes the entire experiment
function run_many {(
  trap "exit 1" ERR

  mode=${1}
  scale=${2}
  runs=${3}
  cache_worker_count=4
  cache_policy=2  # 2 is for compute; 30 is write to cache; 31 is read from cache

  # Move to the service directory
  current_dir=$( pwd )
  cd ${service_loc}

  # If the mode is cache, we need to first cache the data
  if [ "${mode}" == "cache" ]; then
    echo "Writing the data to cache"
    start_cluster "${cache_worker_count}" "30"
    update_dispatcher

    run_one "1" "cache_dump" "${service_loc}/temp_config.yaml"
 
    terminate_cluster "cache_dump"
    echo "Finished writing data to cache"

    # Set the cache_policy for the actual experiments
    cache_policy=31  
  elif [ "${mode}" == "source_cache" ]; then
    echo "Writing source data to cache"
    start_cluster "${cache_worker_count}" "40"
    update_dispatcher

    run_one "1" "source_cache_dump" "${service_loc}/temp_config.yaml"
    terminate_cluster "source_cache_dump"
    echo "Finished writing source data to cache"

    # Set the cahce_policy for the actual experiments
    cache_policy=41
  fi

  # Start the experiments
  for i in "${scale[@]}"; do
    start_cluster "${i}" "${cache_policy}"
    update_dispatcher

    for j in $(seq 1 ${runs}); do
      run_one "${j}" "${i}" "${service_loc}/temp_config.yaml"
    done
    
    terminate_cluster "${i}"
  done  

  # Move to dir before call to avoid side effects 
  cd ${current_dir}
)}

# Run the experiments
run_many "${mode}" "${scale}" "${runs}"

# Copy the results to GCS
if [ ! -z "${gcs_bucket}" ]; then
  echo "Copying ${log_dir} to GCS at address ${gcs_bucket}..."
  gsutil -m cp -r ${log_dir} ${gcs_bucket}
  echo "Done copying ${log_dir} to GCS!"
fi
