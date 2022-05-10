# PyEnv
echo "Installing PyEnv..."
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
  libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev openssl libssl-dev \
  git-all wget
curl https://pyenv.run | bash
export PATH="$HOME/.pyenv/bin:$PATH" >> ~/.bashrc
eval "$(pyenv init -)" >> ~/.bashrc
eval "$(pyenv virtualenv-init -)" >> ~/.bashrc
source ~/.bashrc 
pyenv install 3.9.12
pyenv global 3.9.12
python -m pip install -r requirements.txt
echo "Done"

# Download the build file
gsutil cp gs://cachew-builds/tensorflow-2.8.0-cp39-cp39-linux_x86_64.whl ${HOME}
python -m pip uninstall -y tensorflow && python -m pip install ${HOME}/tensorflow-2.8.0-cp39-cp39-linux_x86_64.whl

# Create a bucket for the state store
gsutil mb gs://${USER}-kubernetes-state || echo "Bucket gs://${USER}-kubernetes-state already exists"

# Get the repositories
git clone https://github.com/eth-easl/cachew_experiments.git && cd cachew_experiments

# Modify the relevant elements of the scripts
replace_relevant_entries() {
  file_path=$1

  sed "s|nethz=\"dkluser\"|nethz=\"${USER}\"|" -i ${file_path}
  sed "s|export KOPS_STATE_STORE=gs://easl-dbk-kubernetes-state|export KOPS_STATE_STORE=gs://${USER}-kubernetes-state|" -i ${file_path}
}

replace_relevant_entries "experiments/autocaching/manage_cluster.sh"
replace_relevant_entries "experiments/autoscaling/manage_cluster/manage_cluster.sh"
replace_relevant_entries "experiments/multi-tenancy/manage_cluster.sh"