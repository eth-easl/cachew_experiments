#!/bin/bash

vm_file_name=${1:-"instance.name"}
project=${2:-"tfdata-service"}

# Define some utility functions
function usage {
    echo "usage: ${0} <params>*"
    echo "Terminates the VM used for the Cachew artifact evaluation."
    printf "\nParams:\n"
    echo "  vm_file_name:     the name of the file which stores the name of the VM"
    echo "  project:          the name of the project under which the VM was created"
    exit 1
}

vm_name=$( cat ${vm_file_name} )

echo "Deleting ${vm_name}..." 
echo | gcloud compute instances delete ${vm_name} --zone=us-central1-a --project=${project}
echo "Done!"