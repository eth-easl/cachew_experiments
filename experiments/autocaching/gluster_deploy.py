import shlex
import sys
from subprocess import Popen, PIPE
from absl import app
from absl import flags
import yaml

FLAGS = flags.FLAGS

flags.DEFINE_string("zone", "us-central1-a", "The zone in which to deploy the service")
flags.DEFINE_string("region", "us-central1", "The region in which to deploy the service")

flags.DEFINE_string('nethz', "dkluser",
                    "Your NETHZ. This is used to ensure there is no name collision between different clusters")
flags.DEFINE_integer("num_nodes", 2, "The number of glusterfs nodes.")

flags.DEFINE_boolean("create_cluster", False, "The script creates a new cluster from scratch or increases the number of gluster nodes")
flags.DEFINE_boolean("delete_cluster", False, "The script deletes all VMs in the cluster.")

def execute_cmd(cmd):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    args = shlex.split(cmd)

    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    proc.wait()
    out, err = proc.communicate()
    exitcode = proc.returncode

    if exitcode != 0:
        pass
        #print(out)
        #print(err)


    return exitcode, out, err

# Node creation and setup
# -------------------------------------------------------------------------------

def create_and_setup_nodes():
    for node_id in range(FLAGS.num_nodes):
        create_and_setup_node(node_id)


def create_and_setup_node(node_id):
    node_name = FLAGS.nethz + "-glusterfs-node-" + str(node_id)

    print("Creating VM for node " + node_name + "...")
    create_vm_cmd = \
        "gcloud compute instances create " + node_name + \
        " --machine-type=n2-standard-2 --image-family=ubuntu-1804-lts --image-project=ubuntu-os-cloud " + \
        "--local-ssd interface=nvme --local-ssd interface=nvme --zone=" + FLAGS.zone
    code, out, err = execute_cmd(create_vm_cmd)
    if code!=0:
        print("WARNING: non-zero exit status from create vm command ({}, {}, {})".format(code, out, err))
        sys.exit(code)
    
    print("Waiting for VM to be up...")
    vm_up = False
    while not vm_up:
        code, out, err = execute_cmd("gcloud compute ssh --strict-host-key-checking=no --zone=" + FLAGS.zone + " " + node_name + "  --command=true --quiet")
        if code==0:
            vm_up = True

    print("Installing gluster...")
    install_gluster_cmd = "sudo add-apt-repository -y ppa:gluster/glusterfs-9 && sudo apt update -y " + \
        "&& sudo apt install -y glusterfs-server && sudo systemctl enable glusterd"
    execute_cmd("gcloud compute ssh --strict-host-key-checking=no --zone=" + FLAGS.zone + " " + node_name + " --command=\"" + install_gluster_cmd + "\" --quiet")

    print("Formatting disks")
    format_disks_cmd = "sudo apt install mdadm -y --no-install-recommends && " + \
        "sudo mdadm --create /dev/md0 --level=0 --raid-devices=2 /dev/nvme0n1 /dev/nvme0n2 && " + \
        "sudo mkfs.xfs -f -i size=512 /dev/md0 && sudo mkdir -p /data/brick1/ && sudo mount /dev/md0 /data/brick1"

    execute_cmd("gcloud compute ssh --strict-host-key-checking=no --zone=" + FLAGS.zone + " " + node_name + " --command=\"" + format_disks_cmd + "\" --quiet")

    node_ip = get_node_ip(node_id)

    for other_id in range(node_id-1):
        other_ip = get_node_ip(other_id)
        add_accept_connections(other_id, node_ip)
        add_accept_connections(node_id, other_ip)


def delete_all_nodes():
    for node_id in range(get_num_nodes()):
        delete_node(node_id)


def delete_node(node_id):
    node_name = FLAGS.nethz + "-glusterfs-node-" + str(node_id)

    delete_node_cmd = "gcloud compute instances delete --zone=" + FLAGS.zone + " " + node_name + " --quiet"
    execute_cmd(delete_node_cmd)


def add_accept_connections(node_id, from_node_ip):
    node_name = FLAGS.nethz + "-glusterfs-node-" + str(node_id)

    add_accept_cmd = "sudo iptables -I INPUT -p all -s " + from_node_ip + " -j ACCEPT "
    execute_cmd("gcloud compute ssh --strict-host-key-checking=no --zone=" + FLAGS.zone + " " + node_name + " --command=\"" + add_accept_cmd + "\" --quiet")


def get_node_ip(node_id):
    node_name = FLAGS.nethz + "-glusterfs-node-" + str(node_id)

    code, out, err = execute_cmd("gcloud compute instances list")

    address = ""
    lines = out.decode('ascii').split("\n")
    for line in lines:
        split_line = line.split()
        if len(split_line) < 5:
            continue
        if split_line[0] == node_name:
            return split_line[4]

    assert(address != "")

# Volume creation and updates
# -------------------------------------------------------------------------------


def create_volume():
    node_name_0 = FLAGS.nethz + "-glusterfs-node-0"

    if FLAGS.num_nodes > 1:
        probe_peers_cmd = "true "
        for node_id in range(1, FLAGS.num_nodes):
            node_name = FLAGS.nethz + "-glusterfs-node-" + str(node_id)
            probe_peers_cmd = probe_peers_cmd + " && sudo gluster peer  probe " + node_name + " "

        execute_cmd("gcloud compute ssh --strict-host-key-checking=no --zone=" + FLAGS.zone + " " + node_name_0 + " --command=\"" + probe_peers_cmd + "\" --quiet")

    create_volume_cmd = "sudo gluster volume create tfdata_cache "
    for node_id in range(FLAGS.num_nodes):
        node_name = FLAGS.nethz + "-glusterfs-node-" + str(node_id)
        create_volume_cmd = create_volume_cmd + node_name + ":/data/brick1/tfdata_cache "

    create_volume_cmd = create_volume_cmd + " && sudo gluster volume start tfdata_cache"
    code, out, err = execute_cmd("gcloud compute ssh --strict-host-key-checking=no --zone=" + FLAGS.zone + " " + node_name_0 + " --command=\"" + create_volume_cmd + "\" --quiet")


# Utils
# -------------------------------------------------------------------------------

def get_num_nodes():
    get_instances_cmd = "gcloud compute instances list"
    code, out, err = execute_cmd(get_instances_cmd)

    node_name_prefix = FLAGS.nethz + "-glusterfs-node-"

    names = []
    for line in out.decode('ascii').split("\n"):
        splits = line.split()
        if len(splits) < 1:
            pass
        elif node_name_prefix in splits[0]:
            names.append(splits[0])

    return len(names)


def main(argv):
    if FLAGS.create_cluster:
        num_nodes = get_num_nodes()
        if num_nodes == 0:
            print("Creating volume from scratch...")
            create_and_setup_nodes()
            create_volume()
            print("Volume created: first volume node is " + FLAGS.nethz +\
                  "-glusterfs-node-0 with ip " +get_node_ip(0) + ".")
        else:
            print("Growing existing cluster")
            for node_id in range(num_nodes, FLAGS.num_nodes):
                create_and_setup_node(node_id)
                add_brick(node_id)

    elif FLAGS.delete_cluster:
        delete_all_nodes()


if __name__ == '__main__':
    app.run(main)
