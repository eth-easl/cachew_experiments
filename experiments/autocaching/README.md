1. **Starting the cluster**. Execute `./manage_cluster.sh start`. The script will create and setup a cluster of several virtual machines.
2. **Checking the status** of the cluster by executing `./manage_cluster.sh status`. If all the status indicators show a green `[OK]`, carry on with the next step.
3. **Running a short test-experiment.** Make sure to use a terminal multiplexer such as `tmux` in case your connection is interrupted. Execute `./experiment_fig7.sh -s` to run a short version of the experiment. Check the plot at `time_per_row_highlight.png`, it should have five data points.
4. **Run the full experiment.** Again, make sure to use a terminal multiplexer like `tmux`. Run the experiment using `./experiment_fig7.sh`. The plot will be created at `time_per_row_highlight.png`.
