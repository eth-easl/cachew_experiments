#!/bin/bash

# Get the parameters of this deployment
name=${1:-""}
USER=anon8
gpu_count=${2:-0}
machine_type=${3:-"n1-standard-8"}
project=${4:-"cachew-artifact-eval"}

# Define some utility functions
function usage {
    echo "usage: ${0} <params>*"
    echo "Sets up a VM for the Cachew artifact evaluation."
    printf "\nParams:\n"
    echo "  name:             (required) the name of the VM being created"
    echo "  gpu_count:        (optional) the number of V100 GPUs to be attached to the VM; default: 0"
    echo "  machine_type:     (optional) the type of the VM being created; default: n1-standard-8"
    echo "  project:          (optional) the project within which the VM is being created; default: tfdata-service"
    exit 1
}

if [ -z "${name}" ]; then
  usage
fi

additional_parameters=""
if [ ${gpu_count} -gt 0 ]; then
  additional_parameters="--accelerator=count=${gpu_count},type=nvidia-tesla-v100"
fi

# Create the image
gcloud beta compute instances create ${name} \
  --project=${project} \
  --zone=us-central1-a \
  --machine-type=${machine_type} \
  --network-interface=network-tier=PREMIUM,subnet=default \
  --maintenance-policy=TERMINATE \
  --provisioning-model=STANDARD \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --min-cpu-platform=Automatic \
  --no-shielded-secure-boot \
  --shielded-vtpm \
  --shielded-integrity-monitoring \
  --reservation-affinity=any \
  --source-machine-image=projects/cachew-artifact-eval/global/machineImages/atc-artifact-eval-v01 ${additional_parameters}

# Check if the VM has been successfully deployed
if [ $? -ne 0 ]; then
  code=$?
  echo "Error: could not create VM"
  echo " > Exit code:" ${code}
  exit
fi

# Log instance details and write instance name locally
(
tee "config.json" <<-EOF
{
  "name": "${name}",
  "gpu_count": ${gpu_count},
  "machine_type": "${machine_type}",
  "project": "${project}"
}
EOF
)
echo ${name} > instance.name

# Wait until the VM is up
echo "Checking if VM is up..."
IP=$(gcloud compute instances list --project=${project} | awk '/'${name}'/ {print $5}')
until nc -w 1 -z $IP 22; do
    echo "VM not up, waiting..."
    sleep 2
done
echo "VM is up!"

# Set up the environment
echo "Setting up environment..."
gcloud compute scp requirements.txt $USER@${name}:~ --zone=us-central1-a --project=${project}
gcloud compute ssh $USER@${name} --zone=us-central1-a --project=${project} -- "bash -s" < environment.sh

# Setup is finished
echo "Deployment complete!"
echo "Use this command to access your VM: gcloud compute ssh ${name} --zone=us-central1-a --project=${project}"
