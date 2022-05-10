#!/usr/bin/env bash
pkill -f "python dispatcher.py"
pkill -f "python worker.py"
pkill -f "python pipeline.py"
pkill -f "python sources/dispatcher.py"
pkill -f "python sources/worker.py"
pkill -f "python sources/pipeline.py"
ls | grep -P "^metrics_updates_job_[0-9]{4}.json$" | xargs -d"\n" rm