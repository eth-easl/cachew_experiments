#!/bin/bash
git add -u
git commit -m "push to deploy"
git push origin HEAD

ssh instbig "cd cachew_artefact && git stash && git pull"
