# PyEnv
echo "Installing PyEnv..."
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
  libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev openssl libssl-dev \
  git-all wget
curl https://pyenv.run | bash

# this is just for the script
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# afterwards if the user logs in, this will get executed
{
  echo 'export PATH="$HOME/.pyenv/bin:$PATH"'
  echo 'eval "$(pyenv init -)"'
  echo 'eval "$(pyenv virtualenv-init -)"'
} >> $HOME/.bashrc

pyenv install 3.9.12
pyenv global 3.9.12
python -m pip install -r requirements.txt

echo "Done"

# Download the build file
gsutil cp gs://cachew-builds/tensorflow-2.8.0-cp39-cp39-linux_x86_64.whl ${HOME}
python -m pip install --force-reinstall ${HOME}/tensorflow-2.8.0-cp39-cp39-linux_x86_64.whl

# Fix protobuf & markupsafe installations
pip install protobuf==3.20.0
pip install markupsafe==2.0.1 # This one gives an error for werkzeug (not sure if it's a problem)

# Create a bucket for the state store if it doesn't exist
gsutil ls -b gs://tfdata-kops-state-otmraz || gsutil mb gs://tfdata-kops-state-otmraz


# Get the repositories
#git clone https://github.com/eth-easl/cachew_experiments.git && cd cachew_experiments
git clone --single-branch --branch otmraz-exp https://github.com/eth-easl/cachew_experiments.git

# Modify the relevant elements of the scripts
replace_relevant_entries() {
  file_path=$1

  # shell script
  {
    sed "s|nethz=\"dkluser\"|nethz=\"otmraz\"|" -i ${file_path} > /dev/null
    sed "s|export KOPS_STATE_STORE=gs://easl-dbk-kubernetes-state|export KOPS_STATE_STORE=gs://tfdata-kops-state-otmraz|" -i ${file_path}

    # for the python files
#    sed 's|"gs://tfdata-imagenet-dada/tfrecords/train"|"gs://tfdata-imagenet-atc-cachew/train"|' -i ${file_path}
    sed 's|"gs://tfdata-imagenet"|"gs://tfdata-imagenet-atc-cachew"|' -i ${file_path}

    # for the YAML file
    sed "s|nethz: \"dkluser\"|nethz: \"otmraz\"|" -i ${file_path}
    #sed "s|project: tfdata-service|project: cachew-artifact-eval|" -i ${file_path}

    #sed "s|tfdata-service/kubernetes-node-glusterfs-enabled|cachew-artifact-eval/kubernetes-node-glusterfs-enabled|" -i ${file_path}
  } >> logfile.txt 2>&1
}

replace_relevant_entries "$HOME/cachew_experiments/experiments/autocaching/manage_cluster.sh"
replace_relevant_entries "$HOME/cachew_experiments/experiments/autocaching/templates/kubernetes_cluster.yaml"
replace_relevant_entries "$HOME/cachew_experiments/experiments/autocaching/default_config.yaml"
replace_relevant_entries "$HOME/cachew_experiments/experiments/autocaching/experiment-script/full_exp.yaml"
replace_relevant_entries "$HOME/cachew_experiments/experiments/autocaching/experiment-script/short_exp.yaml"
replace_relevant_entries "$HOME/cachew_experiments/experiments/autocaching/manage_cluster/default_config.yaml"
replace_relevant_entries "$HOME/cachew_experiments/experiments/autoscaling/manage_cluster/templates/kubernetes_cluster.yaml"
replace_relevant_entries "$HOME/cachew_experiments/experiments/autoscaling/manage_cluster/manage_cluster.sh"
replace_relevant_entries "$HOME/cachew_experiments/experiments/autoscaling/resnet/run_imageNet.sh"
replace_relevant_entries "$HOME/cachew_experiments/experiments/multi-tenancy/manage_cluster/default_config.yaml"
