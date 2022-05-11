#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# kill all background tasks upon exit
trap 'kill $(jobs -p)' EXIT

# Set the input parameters
#easl_utils_scripts_path=${1:-"/home/jupyter/service/easl-utils"}
job_1_batch_time_ms=${1:-100}
job_2_batch_time_ms=${2:-50}
file_count=${3:-512}
service_nodes=${4:-10}
zone=${5:-"us-central1-a"}

# Infer the paths to the scripts
service_path=$(realpath ../manage_cluster)
#gluster_path=${service_path}/gluster
experiment_path=$(realpath .)
experiment_dir=${SCRIPT_DIR}/traces_multi_tenant_$( date +"%Y-%m-%d_%T" )

mkdir -p "${experiment_dir}"

#echo "Service scripts: " $service_path
#echo "Gluster scripts: " $gluster_path
#echo "Multi-tenant scripts: " $experiment_path

echo "Results directory: $experiment_dir"

# Dump some organizational stats
(
tee "${experiment_dir}/config.json" <<-EOF
{
  "deployment_zone": "${zone}",
  "cachew_worker_count": "${service_nodes}",
  "input_pipeline": "ResNet",
  "model": "sleep_model",
  "job_1_batch_time_ms": "${job_1_batch_time_ms}",
  "job_2_batch_time_ms": "${job_2_batch_time_ms}",
  "vm_name": "$( hostname )",
  "service_image": "$(yq -r ".image" "${service_path}/default_config.yaml")",
  "log_dir": "${experiment_dir}"
}
EOF
)

# stop execution if any error happens
#set -e
#set -o pipefail

program_name=$0

# Define some utility functions
function usage {
    echo "usage: ./${program_name} <params>*"
    echo "Handles the end-to-end execution of the experiment at the basis of Figure 10."
    echo "  easl_utils_scripts_path:      path to the easl_utils location"
    echo "  job_1_batch_time_ms:          number of ms per batch for job_1"
    echo "  job_2_batch_time_ms:          number of ms per batch for job_2"
    echo "  file_count:                   the number of source ImageNet files to use out of 1024"
    echo "  service_nodes:                the number of Cachew workers"
    echo "  zone:                         the zone where the deployments are taking place"
    exit 1
}

get_hostname () {
    gcloud compute instances list | grep "$1" | head -n 1 | awk '{print $1}'
}

get_internal_ip () {
   gcloud compute instances describe "$1" | yq -r '.networkInterfaces[0].networkIP'
}

get_line_count () {
  wc -l $1 | awk '{print $1}'
}

# Create the GlusterFS cluster
#cd ${gluster_path}
#echo "Creating the GlusterFS cluster..."
#sed -i "s/num_nodes:[ \t]\+[0-9]\+/num_nodes: $gluster_nodes/g" "gluster_default_config.yaml"
#python gluster_deploy.py --create_or_grow
#sudo copy_to_gluster.sh  # Note that this requires 'sudo'
#echo "Done creating the GlusterFS cluster..."

echo "Deleting everything on gluster"
[[ -d /mnt/disks/gluster_data/cache ]] && sudo rm -rf /mnt/disks/gluster_data/cache
# Create the kubernetes cluster
cd "${service_path}"
echo "Creating the Cachew service..."
#nethz=$(yq -r ".nethz" "${service_path}/default_config.yaml")
#nethz=$( cat ${gluster_path}/gluster_default_config.yaml | head -n 3 | tail -n 1 | awk '{split($0,a," "); print a[2]}' )
#gluster_internal=`get_internal_ip "${nethz}-glusterfs-node-0"`
#sed -i "s/glusterfs.*$/glusterfs_ip: $gluster_internal/g" "default_config.yaml"
#sed -i "s/num_workers:[ \t]\+[0-9]\+/num_workers: $service_nodes/g" "default_config.yaml"
#sed -i "s/scaling_policy:[ \t]\+[0-9]\+/scaling_policy: 1/g" "default_config.yaml"
#sed -i "s/cache_policy:[ \t]\+[0-9]\+/cache_policy: 1/g" "default_config.yaml"
./manage_cluster.sh restart_service  -w "$service_nodes" -k "$service_nodes" -s 1
echo "Done creating the Cachew service..."

# Set up the experiment
cd "${experiment_path}"
dispatcher_nethz=$(yq -r ".nethz" "${service_path}/default_config.yaml")
dispatcher_host=$(get_hostname "${dispatcher_nethz}-cachew-dispatcher")
dispatcher_ip=$(get_internal_ip "${dispatcher_host}")

echo "Starting Job #1..."
python resnet_input_pipeline.py --dispatcher_ip=${dispatcher_host} --job_name="job_1" --sleep_time_ms=${job_1_batch_time_ms} --file_count=${file_count} > ${experiment_dir}/job_1_out.log 2> ${experiment_dir}/job_1_err.log &
job_1_pid=$!

# Wait until we're in the third epoch for job 1 (i.e. the get from cache epoch)
line_count=`get_line_count ${experiment_dir}/job_1_out.log`
until [ ${line_count} -ge 5 ]; do
  sleep 3
  line_count=`get_line_count ${experiment_dir}/job_1_out.log`
done
sleep 3

echo "Woke up and starting Job #2 now..."
python resnet_input_pipeline.py --dispatcher_ip=${dispatcher_host} --job_name="job_2" --sleep_time_ms=${job_2_batch_time_ms} --file_count=${file_count} > ${experiment_dir}/job_2_out.log 2> ${experiment_dir}/job_2_err.log # Wait until this job finishes
echo "Job #2 finished, checking if Job #1 finished as well..."
tail --pid=${job_1_pid} -f /dev/null
echo "Both Jobs have finished"


cd "$experiment_dir"
# Gather the metrics and produce the plot
echo "Gathering metrics... $experiment_dir"
dispatcher_pod=$( kubectl get pods | head -n 2 | tail -n 1 | awk '{print $1}' )
kubectl cp "default/${dispatcher_pod}:/usr/src/app/events.csv" "events.csv"
kubectl logs "${dispatcher_pod}" > dispatcher.log 2>&1
python "${SCRIPT_DIR}/plot_trace.py" --path="./" --save_path="./multi_tenant_plot"
cd "$SCRIPT_DIR"

echo "Metrics gathered and plot generated"

# Tear down resources

#cd ${service_path} && python service_deploy.py --stop
#cd ${gluster_path} && python gluster_deploy.py --delete_cluster
#echo "Resources torn down and experiment finished"
