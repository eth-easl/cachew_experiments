#!/bin/bash
# stop execution if any error happens

# source: http://tech.franzone.blog/2008/08/25/bash-script-init-style-status-message/
# Column number to place the status message
RES_COL=70
# Command to move out to the configured column number
MOVE_TO_COL="echo -en \\033[${RES_COL}G"
# Command to set the color to SUCCESS (Green)
SETCOLOR_SUCCESS="echo -en \\033[1;32m"
# Command to set the color to FAILED (Red)
SETCOLOR_FAILURE="echo -en \\033[1;31m"
# Command to set the color back to normal
SETCOLOR_NORMAL="echo -en \\033[0;39m"

# Function to print the SUCCESS status
echo_success() {
    $MOVE_TO_COL
    echo -n "["
    $SETCOLOR_SUCCESS
    echo -n $" OK "
    $SETCOLOR_NORMAL
    echo -n "]"
    echo -ne "\r"
    echo ""
}

# Function to print the FAILED status message
echo_failure() {
    $MOVE_TO_COL
    echo -n "["
    $SETCOLOR_FAILURE
    echo -n $"FAILED"
    $SETCOLOR_NORMAL
    echo -n "]"
    echo -ne "\r"
    echo ""
}

programname=$0
gluster_nodes=1
num_kubernetes_nodes=20
num_tfdata_workers=20
nethz="otmraz"
region="europe-west4"
zone="europe-west4-a"
mnt="/mnt/disks/gluster_data"
service_config_yaml="default_config.yaml"
logfile="${programname}_log.txt"
export KOPS_STATE_STORE=gs://otmraz-tpu-test-europe

function usage {
    echo "usage: $programname [start/status/stop/restart_service]"
    echo "starts/terminates glusterfs"
    echo "  -f [Cachew service config yaml]"
    echo "  -g [number of GlusterFS nodes]"
    echo "  -n [nethz ID]"
    exit 1
}

cmd=$1
shift
if [[ "$cmd" != "start" ]] && [[ "$cmd" != "stop" ]] && [[ "$cmd" != "status" ]] && [[ "$cmd" != "restart_service" ]]; then
    usage
    echo "specify start or terminate"
    exit 1
fi

while getopts "h?g:n:f:" opt; do
  case "$opt" in
    h|\?)
      usage
      ;;
    f)  service_config_yaml=$OPTARG
      ;;
    g)  gluster_nodes=$OPTARG
      ;;
    n)  nethz=$OPTARG
      ;;
  esac
done

export KOPS_CLUSTER_NAME=${nethz}-tfdata-service.k8s.local


gluster_name () {
  echo "$nethz-glusterfs-node-$1"
}

get_hostname () {
    gcloud compute instances list | grep "$1" | head -n 1 | awk '{print $1}'
}

get_external_ip () {
    gcloud compute instances describe "$1" | yq -r '.networkInterfaces[0].accessConfigs[0].natIP'
}

get_internal_ip () {
    gcloud compute instances describe "$1" | yq -r '.networkInterfaces[0].networkIP'
}

get_kube_workers () {
  kubectl get nodes | grep node | awk '{print $1}'
}

get_kube_tfdata_workers () {
  kubectl get nodes | grep node | awk '{print $1}' | grep nodes
}

get_kube_dispatcher () {
  kubectl get nodes | grep dispatcher | awk '{print $1}'
}

check_gcloud_authenticated () {
  echo -n "Checking whether gcloud is authenticated"
  if gcloud compute instances list > /dev/null 2>&1; then
    echo_success
  else
    echo_failure
  fi

  echo -n "Setting gcloud region to $region and $zone"
  if gcloud config set compute/region $region >> "$logfile" 2>&1 && \
    gcloud config set compute/zone $zone >> "$logfile" 2>&1; then
    echo_success
  else
    echo_failure
  fi

}

check_gluster_mounted () {
  echo -n "Checking whether GlusterFS is mounted at $mnt"
  if mountpoint -q "$mnt"; then
    echo_success
  else
    echo_failure
  fi
}

check_tfdata_service_up () {
  echo -n "Checking whether Cachew nodes are up"
  if tfdata_service_pods_running; then
    echo_success
  else
    echo_failure
  fi
}

check_gluster_up () {
  for (( i=0; i<gluster_nodes; i++ )); do
    gname_prefix=$(gluster_name "$i")
    gname=$(get_hostname "$gname_prefix")
    echo -n "Checking whether $gname_prefix is up"
    if [[ -z $gname ]]; then
      echo_failure
      return 1
    else
      echo_success
    fi
  done
  return 0
}

start_gluster () {
  echo -n "Starting GlusterFS Nodes (may take ~10min)"
  if timeout 15m python gluster_deploy.py \
    --create_cluster \
    --nethz "$nethz" \
    --num_nodes "$gluster_nodes" \
    --region "$region" \
    --zone "$zone" >> "$logfile" 2>&1; then
    echo_success
    return 0
  fi
  echo_failure
  return 1
}

stop_gluster () {
  echo -n "Stopping GlusterFS"
  if python gluster_deploy.py \
    --delete_cluster \
    --nethz "$nethz" \
    --num_nodes "$gluster_nodes" \
    --region "$region" \
    --zone "$zone" >> "$logfile" 2>&1; then
    echo_success
    return 0
  else
    echo_failure
  fi
}

umount_glusterfs () {
  gname_prefix=$(gluster_name "0")
  gname=$(get_hostname "$gname_prefix")
  echo -n "Unmounting GlusterFS at $mnt"
  if sudo umount "$mnt" >> "$logfile" 2>&1; then
    echo_success
  else
    echo_failure
  fi
}

mount_glusterfs () {
  gname_prefix=$(gluster_name "0")
  gname=$(get_hostname "$gname_prefix")
  echo -n "Mounting GlusterFS at $mnt"
  if sudo mount -t glusterfs "${gname}":/tfdata_cache "$mnt" >> "$logfile" 2>&1; then
    echo_success
  else
    echo_failure
  fi
}

check_kubernetes () {
  echo -n "Checking if Kubernetes Cluster is up"
  if kubectl get pods > /dev/null 2>&1; then
    echo_success
  else
    echo_failure
  fi
}

stop_kubernetes () {
  echo -n "Stopping and deleting the cluster"
  if kops delete cluster --name "$KOPS_CLUSTER_NAME" --yes >> "$logfile" 2>&1; then
    echo_success
  else
    echo_failure
  fi
}

start_kubernetes () {
  if [ $num_kubernetes_nodes -eq 0 ] ; then
    echo -n "Generating kubernetes config yaml (no workers)"
    if jinja2 templates/kubernetes_cluster.yaml \
      -D "nethz=$nethz" \
      -D "zone=$zone" \
      -D "region=$region" > ./tmp/kubernetes_cluster_no_workers.yaml < /dev/null; then
      echo_success
    else
      echo_failure
    fi

  else
    echo -n "Generating kubernetes config yaml"
    if jinja2 templates/kubernetes_cluster.yaml \
      -D "nethz=$nethz" \
      -D "zone=$zone" \
      -D "region=$region" \
      -D "num_nodes=$num_kubernetes_nodes" > ./tmp/kubernetes_cluster.yaml < /dev/null; then
      echo_success
    else
      echo_failure
    fi
  fi

  echo -n "Starting kubernetes cluster"
  export KOPS_CLUSTER_NAME=${nethz}-tfdata-service.k8s.local
  export KOPS_FEATURE_FLAGS=AlphaAllowGCE

  if kops create -f "./tmp/kubernetes_cluster.yaml" >> "$logfile" 2>&1 && \
      kops update cluster --name "$KOPS_CLUSTER_NAME" --yes >> "$logfile" 2>&1 && \
      kops export kubecfg --name "$KOPS_CLUSTER_NAME" --admin >> "$logfile" 2>&1 && \
      kops validate cluster --wait 15m >> "$logfile" 2>&1; then
    echo_success
  else
    echo_failure
  fi

}


setup_kubernetes_nodes () {
  echo -n "Creating gluster endpoints"
  gname_prefix=$(gluster_name "0")
  gname=$(get_hostname "$gname_prefix")
  gluster_ip=$(get_internal_ip "$gname")
  if jinja2 ./templates/gluster_endpoint.yaml -D ip="$gluster_ip" > tmp/gluster_endpoint.yaml < /dev/null && \
    [[ -n "$gluster_ip" ]] && \
    kubectl apply -f tmp/gluster_endpoint.yaml >> "$logfile" 2>&1; then
    echo_success
  else
    echo_failure
  fi

  if false; then


    list=$(get_kube_workers)
    while IFS= read -r node_name; do
      echo -n "Setting up node $node_name..."
      timeout=0
      until ( gcloud compute ssh --strict-host-key-checking=no "$node_name" --command="gcloud auth configure-docker --quiet" && \
           gcloud compute ssh --strict-host-key-checking=no "$node_name" --command="mkdir /tmp/turboboost/ || true" && \
           gcloud compute scp --strict-host-key-checking=no --recurse ./templates/disable_turbo_boost.sh "$node_name:/tmp/turboboost/disable_turbo_boost.sh" && \
           gcloud compute ssh --strict-host-key-checking=no "$node_name" --command="sudo apt-get install msr-tools && sudo modprobe msr && /tmp/turboboost/disable_turbo_boost.sh disable" ) < /dev/null >> "$logfile" 2>&1; do
        timeout=$((timeout + 1))
        if (( timeout > 20 )); then
          echo_failure
        fi
        sleep 5
      done
     echo_success
    done <<< "$list"
  fi
}

tfdata_service_pods_running () {
  # there must be some data-service pods
  # and they must be running
  (! kubectl get pods | awk '/data-service/ && (!/Running/ || /0\/1/)' | grep -q . )
}

deploy_tfdata_service () {
  echo $'disp_port: 31000\nworkers:' > tmp/inp.yaml
  for (( i=0; i<num_tfdata_workers; i++ )); do
    echo "- index: $i" >> tmp/inp.yaml
    echo "  port: $(( 31001 + i))" >> tmp/inp.yaml
  done

  if [ $num_kubernetes_nodes -eq 0 ] ; then
    echo -n "Creating services and interfaces (no worker)..."
    if jinja2 ./templates/data_service_interfaces_no_worker.yaml ./tmp/inp.yaml > ./tmp/data_service_interfaces.yaml < /dev/null && \
      kubectl apply -f tmp/data_service_interfaces.yaml >> "$logfile" 2>&1; then
      echo_success
    else
      echo_failure
    fi
  else
    echo -n "Creating services and interfaces..."
    if jinja2 ./templates/data_service_interfaces.yaml ./tmp/inp.yaml > ./tmp/data_service_interfaces.yaml < /dev/null && \
      kubectl apply -f tmp/data_service_interfaces.yaml >> "$logfile" 2>&1; then
      echo_success
    else
      echo_failure
    fi
  fi

  echo -n "Waiting for service to come up..."
  timeout=0
  until ! kubectl get services | grep "data-service" | grep -q "<pending>"; do
    timeout=$((timeout + 1))
    if (( timeout > 20 )); then
      echo_failure
      return
    fi
    sleep 5
  done
  echo_success

  echo -n "Deploying Cachew service..."
  if [[ ! -f "$service_config_yaml" ]]; then
    echo_failure

  fi
  kube_worker_names=$(get_kube_tfdata_workers)
  kube_dispatcher_name=$(get_kube_dispatcher)
  readarray -t worker_names_array <<<"$kube_worker_names"

  num_kube_workers=$(echo "$kube_worker_names" | wc -l)
  if [[ "$num_kube_workers"  != "$num_tfdata_workers" ]]; then
    echo "number of kube workers ($num_kube_workers) and tf data workers ($num_tfdata_workers) does not match." >> "$logfile"
    if [ $num_tfdata_workers -ne 0 ] ; then
      echo_failure
      return 1
    fi
  fi

  cp $service_config_yaml tmp/data_service_inp.yaml
  echo "workers:" >> tmp/data_service_inp.yaml
  for (( i=0; i<num_tfdata_workers; i++ )); do
    {
      echo "- index: $i"
      echo "  port: $(( 31001 + i))"
      echo "  name: data-service-worker-${i}"
      echo "  ip: ${worker_names_array[$i]}"
    } >> tmp/data_service_inp.yaml

  done

  {
    echo "dispatcher_ip: $kube_dispatcher_name"
    echo "disp_port: 31000"
    echo "docker_image: gcr.io/tfdata-service/$(yq -r ".image" $service_config_yaml)"
  } >> tmp/data_service_inp.yaml

  if [ $num_kubernetes_nodes -eq 0 ] ; then
    jinja2 ./templates/data_service_no_worker.yaml ./tmp/data_service_inp.yaml > ./tmp/data_service.yaml < /dev/null
    if kubectl apply -f tmp/data_service.yaml >> "$logfile" 2>&1; then
      echo_success
    else
      echo_failure
    fi
  else
    jinja2 ./templates/data_service.yaml ./tmp/data_service_inp.yaml > ./tmp/data_service.yaml < /dev/null
    if kubectl apply -f tmp/data_service.yaml >> "$logfile" 2>&1; then
      echo_success
    else
      echo_failure
    fi
  fi

  echo -n "Waiting for service to come up..."
  timeout=0
  until tfdata_service_pods_running; do
    timeout=$((timeout + 1))
    if (( timeout > 20 )); then
      echo_failure
      return
    fi
    sleep 5
  done
  echo_success
}

stop_tfdata_service () {
  services=$(kubectl get services | grep data-service | awk '{print $1}')
  readarray -t services_arr <<<"$services"

  for service in "${services_arr[@]}"
  do
    echo -n "Stopping $service..."
    if kubectl delete rs "$service" >> "$logfile" 2>&1 \
      && kubectl delete service "$service"  >> "$logfile" 2>&1; then
      echo_success
    else
      echo_failure
    fi
  done
}

install_dependencies () {
  pip3 install jinja2-cli > /dev/null 2>&1
  pip3 install yq > /dev/null 2>&1
  [[ ! -d tmp/ ]] && mkdir -p tmp/
}

install_dependencies

if [[ "$cmd" == "status" ]]; then
  #set -e
  check_gcloud_authenticated
  check_gluster_up
  check_gluster_mounted
  check_kubernetes
  check_tfdata_service_up
elif [[ "$cmd" == "restart_service" ]]; then
  check_gcloud_authenticated
  stop_tfdata_service
  deploy_tfdata_service
elif [[ "$cmd" == "start" ]]; then
  check_gcloud_authenticated
  start_gluster
  mount_glusterfs
  stop_kubernetes
  start_kubernetes
  setup_kubernetes_nodes
  deploy_tfdata_service
elif [[ "$cmd" == "stop" ]]; then
  check_gcloud_authenticated
  stop_tfdata_service
  umount_glusterfs
  stop_gluster
  stop_kubernetes
fi
