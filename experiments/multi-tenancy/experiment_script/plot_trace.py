
from absl import app
from absl import flags

import matplotlib.pyplot as plt
import os
import pandas as pd


FLAGS = flags.FLAGS
flags.DEFINE_string("path", "", "Location to the experiment directory")
flags.DEFINE_string("save_path", None, "The location where the plots should be saved")
flags.DEFINE_float("y_lim", None, "(Optional) Specifies the upper bound of the y axis")
flags.DEFINE_float("x_lim", None, "(Optional) Specifies the upper bound of the x axis")


DISPATCHER_EVENTS_FILE_NAME = "events.csv"

JOB_1_LOG_NAME="job_1_out.log"
JOB_2_LOG_NAME="job_2_out.log"


point_color = {
  "scale_up": "blue", 
  "scale_down": "orange", 
  "starting_worker_count": "yellow"
}

job_names = ["job_1", "job_2"]
scale_colors = ["red", "blue"]
event_colors = ["orange", "cyan"]
line_style = ["dotted", "dashdot"]
scale_hitches = ['/', '\\']
epoch_colors = [["yellow", "blue", "green", "gray"], ["green", "green", "green", "gray"]]
epoch_colors_by_mode = {"GET": "green", "PUT": "blue", "PROFILE": "yellow"}


def plot_trace(path, save_path, y_lim, x_lim):
  if save_path:
    plt.figure(figsize=(20, 11))
    plt.rcParams.update({'font.size': 18})

  disp_events = pd.read_csv(os.path.join(path, DISPATCHER_EVENTS_FILE_NAME))

  # min_val = min(disp_events.min(axis=0)["time"], client_epoch.min(axis=0)["time"])
  min_val = disp_events.min(axis=0)["time"]

  # Subtract this time from the timestamps
  disp_events["time"] -= min_val
  disp_events["time"] /= 10 ** 6

  max_val = disp_events.max(axis=0)["time"]

  # Get the events pertaining to job_1 and job_2
  job_1_events = disp_events.loc[disp_events["job_name"] == job_names[0]]
  job_2_events = disp_events.loc[disp_events["job_name"] == job_names[1]]

  for idx, data in enumerate([job_1_events, job_2_events]):
    # Plot the worker count steps 
    xx = []
    yy = []
    for _, row in data.iterrows():
      if row["event_type"] in ["scale_up", "scale_down", "starting_worker_count", "end_training"]:
        xx.append(row["time"])
        yy.append(int(row["additional"]))

    # prefix = f"$W_{idx + 1}$:"
    prefix = f"W{idx}:"
    color = scale_colors[idx]
    name = job_names[idx]
    lstyle = line_style[idx]
    plt.step(xx, yy, label=f"worker count {name}", where="post", color=color, linewidth=3)

    # Mark points where event happens in dispatcher
    for _, row in data.iterrows():
      event_type = row["event_type"]
      # if event_type in ["scale_up", "scale_down"]:
      #   c = int(row["additional"]) + (-1 if event_type == "scale_up" else 0.75)
      #   txt = "Add worker" if event_type == "scale_up" else "Remove worker"
      #   plt.axvline(row["time"], color="orange", linewidth=1, linestyle=lstyle)
      #   plt.text(row["time"] + 5, c, txt, rotation=90)
      if event_type == "extended_epoch":
        plt.axvline(row["time"], color=color, linewidth=3.3, linestyle=(0, (1, 10)))
        plt.text(row["time"] + 2.5, 2.9, f"{prefix} Epoch extension", rotation=90, fontweight='bold', fontsize=20)
      elif event_type == "execution_policy_decision":
        plt.axvline(row["time"], color="green", linestyle=lstyle)
        plt.text(row["time"] + 2.5, 2.8, f"{prefix} Execution decision for " + row["additional"], rotation=90, fontweight='bold', fontsize=20)
      elif event_type == "execution_mode_change":
        delta = 2.9 if row["additional"] != "PROFILE" else 2.5
        plt.axvline(row["time"], color=color, linestyle=(0, (3, 1, 1, 1, 1, 1)), linewidth=2)
        plt.text(row["time"] + 2.5, delta, f"{prefix} Epoch starts in mode " + row["additional"], rotation=90, fontweight='bold', fontsize=20)

    # Mark epoch regions
    pairs = []
    running_pair = []
    pairs_mode = []
    for _, row in data.iterrows():
      if row["event_type"] in ["execution_mode_change", "extended_epoch", "end_training"]:
        running_pair.append(row["time"])
        if len(running_pair) == 2:
          pairs.append(running_pair)
          running_pair = [row["time"]]

        if len(running_pair) == 1:
          pairs_mode.append(row["additional"])
    hitch = scale_hitches[idx]
    times = []
    for i, pair in enumerate(pairs):
      t = int(pair[1] - pair[0])
      times.append(t)
      color = "white"
      if i < len(pairs_mode) and pairs_mode[i] in epoch_colors_by_mode:
        color = epoch_colors_by_mode[pairs_mode[i]]

      plt.axvspan(pair[0], pair[1], alpha=0.3, color=color, hatch=hitch)
      print(pair)
      # plt.text(pair[0] + t // 2 - 100, plt.ylim()[1] + 0.05, f"Time {t}s")


  plt.legend(loc='lower right', prop={'size': 20})
  plt.xlabel(f"Elapsed time [s]", fontsize=40)
  plt.ylabel(f"Worker count", fontsize=40)
  plt.xticks(fontsize=20)
  plt.yticks(fontsize=20)

  if y_lim:
    plt.ylim(top=y_lim)

  if x_lim:
    plt.xlim(left=0, right=x_lim)    
  else:
    plt.xlim(left=0, right=max_val)  

  if save_path:
#    plt.tight_layout()

    plt.savefig(save_path + ".png")
    plt.savefig(save_path + ".pdf", bbox_inches = 'tight')
  else:
    plt.show()

def print_epoch_times(path, save_path=None):
  paths = {
    "job_1": os.path.join(path, JOB_1_LOG_NAME),
    "job_2": os.path.join(path, JOB_2_LOG_NAME)
  }
  epoch_times = {}

  def _get_timestamp(x):
    return float(x.split(",")[0])

  for k, v in paths.items():
    epoch_times[k] = []
    with open(v) as f:
      lines = f.readlines()

    for i in range(0, len(lines), 2):
      epoch_times[k] += [
        _get_timestamp(lines[i + 1]) - _get_timestamp(lines[i])
      ]
  lines = []
  lines.append("Printing epoch times in seconds*:")
  for k, v in epoch_times.items():
    lines.append(f"{k}: {v}")
  lines.append("\n*Note: if Cachew inserted an extended epoch for one of the jobs, "
        "the respective epoch time will be artificially longer.")
  full_text = "\n".join(lines)
  print(full_text)
  
  if save_path is not None:
    with open("{}_epoch_time.txt".format(save_path), 'w') as f:
        f.write(full_text)


def main(argv):
  del argv

  path = FLAGS.path
  save_path = FLAGS.save_path
  y_lim = FLAGS.y_lim
  x_lim = FLAGS.x_lim

  plot_trace(path, save_path, y_lim, x_lim)
  print_epoch_times(path, save_path)


if __name__ == '__main__':
  app.run(main)
