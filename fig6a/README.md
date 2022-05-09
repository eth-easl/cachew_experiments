1. **Starting the cluster**. Execute `./manage_cluster.sh start` in the `manage_cluster` subfolder. The script will create and setup a cluster of several virtual machines.
2. **Checking the status** of the cluster by executing `./manage_cluster.sh status` in the `manage_cluster` subfolder. If all the status indicators show a green `[OK]`, carry on with the next step.
3. **Executing the experiment.** Make sure to use a terminal multiplexer `tmux` in case your connection is interrupted. Execute `./run_figure_6a_experiment.sh` from the `wait_time` subfolder.
4. **Retrieve the results.** The script will generate the plot at `wait_time/resnet_epochTime_vs_numWorkers_cachew_k8s_atc.pdf`
