import numpy as np
import pandas as pd
import sys
import os
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

## First argument is directory with experiment results

model_name = "resnet"
cachew_color = '#ff8000'
k8s_color = '#3333ff'
compute_color = '#000000'
source_cache_color = '#606060'
full_cache_color = '#a0a0a0'
large_marker = 160
normal_marker = 80

epoch_csv = os.path.join(sys.argv[1], "epochs.csv")
cachew_scaling_decision_csv = os.path.join(sys.argv[1], "cachew_decision.txt")
kubernetes_hpa_scaling_decision_csv = os.path.join(sys.argv[1], "hpa_decision.txt")

compute : pd.DataFrame
compute = pd.read_csv(epoch_csv) # type: ignore
compute.sort_values("workers", inplace=True)
compute_x = compute['workers'].to_numpy()
compute_y = compute['epoch_time'].to_numpy()
compute_c = []
compute_s = []
compute_e = []

cachew_worker_count = pd.read_csv(cachew_scaling_decision_csv,  names=['workers']) \
                        .iloc[:,-3:] \
                        ["workers"].median() # type: ignore

kubernetes_hpa_worker_count = pd.read_csv(kubernetes_hpa_scaling_decision_csv,  names=['workers']) \
                        .iloc[:,-3:] \
                        ["workers"].median() # type: ignore
print(cachew_worker_count)
print(kubernetes_hpa_worker_count)

for i in compute_x:
	if cachew_worker_count == i:
		compute_c.append(cachew_color)
		compute_s.append(large_marker + 30)
		compute_e.append('black')
	elif kubernetes_hpa_worker_count == i:
		compute_c.append(k8s_color)
		compute_s.append(large_marker)
		compute_e.append(k8s_color)
	else:
		compute_c.append(compute_color)
		compute_s.append(normal_marker)
		compute_e.append(compute_color)

plt.rcParams.update({'font.size': 20})
plt.rcParams.update({'figure.figsize':(10, 6)})
plt.grid(color='lightgrey', linestyle=':', linewidth=1)
plt.plot(compute_x, compute_y, linestyle='--', color='#000000', label='Compute', lw=2, zorder=1)
plt.scatter(compute_x, compute_y, marker='s', c=compute_c, s=compute_s, zorder=2, edgecolors=compute_e)

plt.xlabel('Number of workers')
plt.ylabel('Epoch time (seconds)')
#plt.title('ResNet50')
custom_legend = [Line2D([0], [0], color='#000000', lw=2, marker='s', linestyle="--", markersize=8),
                Line2D([0], [0], color='#ffffff'),
                Patch(facecolor='#3333ff', edgecolor='#3333ff',
                     label='Kubernetes HPA'), 
                Patch(facecolor='#ff8000', edgecolor='#ff8000',
                         label='Cachew'),]
plt.legend(custom_legend, ['Compute',  ' ', 'Kubernetes HPA', 'Cachew'])
#plt.legend()
plt.savefig(model_name + "_epochTime_vs_numWorkers_cachew_k8s_atc.pdf")
plt.show()
