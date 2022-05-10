#!/bin/bash

function usage {
    echo "usage: $programname"
    echo "runs experiment and generates figure"
    echo "  -s    short version (to test everything works)"
    exit 1
}

programname=$0
short_exp=""
while getopts "h?s" opt; do
  case "$opt" in
    h|\?)
      usage
      ;;
    s)  short_exp=true
      ;;
  esac
done

out_dir=$(realpath "./experiment_out")
out_dir_bak=$(realpath "./experiments_bak")

if [[ -d $out_dir ]]; then
  sudo mv -"$out_dir"/* "$out_dir_bak"
fi
mkdir -p "$out_dir"

experiment_yaml=""
if [[ -n $short_exp ]]; then
  echo "Doing short run..."
  experiment_yaml="short_exp.yaml"
else
  echo "Complete experiment..."
  experiment_yaml="full_exp.yaml"
fi


{
  cd experiment-script/ || exit 1
  sed -i "s#path_to_log:.*#path_to_log: $out_dir#g" $experiment_yaml
  echo "local_root_dir: $(realpath .)
# Local temporary directory for storing temp config files, the cache, etc..
local_tmp_dir: $out_dir
service_deployment_dir: $(realpath ../)
glusterfs_ip:  #not in use
glusterfs_mount_path: /mnt/disks/gluster_data" > global_config.yaml
  python run.py –global_config global_config.yaml --exp_config $experiment_yaml
}
cd - || exit 1

echo "Extracting cachew decisions from logs"
exp_dir=$(ls --directory "$out_dir"/*/ | head -n 1)
echo "Analyzing exp $exp_dir"
{
  echo "sleep_time_msec,decision"
  grep -r "Caching decision" "$exp_dir"/logs_for_config/cache_policy\:5/ | sed --expression='s/^.*sleep_time_msec:\([0-9]*\).*for dataset_key [^:]*: \(.*\)/\1,\2/g'
} > "$exp_dir/cachew_decision.csv"

echo "Plotting..."
pwd
python plotting-scripts/plot_highlight.py --data "$exp_dir"/*agg* --caching_decision "$exp_dir"/cachew_decision.csv
