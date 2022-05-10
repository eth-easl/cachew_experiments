#!/usr/bin/env bash

# Set up environment
cd "$(dirname "$0")"

# Remove old traces
./kill_service.sh
rm -f outputs/* 2> /dev/null
rm -f logs/* 2> /dev/null

# Get the desired worker count
worker_count=${1:-1} 
client_count=${2:-1}

# Start the service
exec python sources/dispatcher.py > logs/dispatcher.log 2>&1 &
echo $!
sleep 1

for i in $(seq 1 ${worker_count}); do
	exec python sources/worker.py -p $(( 40000 + ${i} )) > logs/worker_${i}.log 2>&1 &
	echo $!
	sleep 1
done 

for i in $(seq 1 ${client_count}); do
	exec python sources/pipeline.py > logs/pipeline_${i}.log 2>&1 &
	echo $!
done