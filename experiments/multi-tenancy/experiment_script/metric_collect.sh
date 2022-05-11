#!/usr/bin/env bash

save_path=traces_multi_tenant_$( date +"%Y-%m-%d_%T" )
mkdir -p ${save_path}

mv metrics* client* ${save_path}
cd ${save_path}

dispatcher=$( kubectl get pods | head -n 2 | tail -n 1 | awk '{print $1}' )
kubectl cp default/${dispatcher}:/usr/src/app/events.csv events.csv
kubectl logs ${dispatcher} > dispatcher.log 2>&1

