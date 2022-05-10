"""
All credits to Jonny Jackson for this piece of code.
https://jonnyjxn.medium.com/how-to-config-your-machine-learning-experiments-without-the-headaches-bb379de1b957

updates:
    - self.data should be default_cfg that was overwritten by the merge function
    - line 40: we need to start with some dict first..
"""
import copy

import yaml

import system_utils


class Config(object):
    """Simple dict wrapper that adds a thin API allowing for slash-based retrieval of
    nested elements, e.g. cfg.get_config("meta/dataset_name")
    """

    def __init__(self, config_path, default_path=None):
        with open(config_path) as cf_file:
            cfg = yaml.safe_load(cf_file.read())
            self._data = cfg

        if default_path is not None:
            with open(default_path) as def_cf_file:
                default_cfg = yaml.safe_load(def_cf_file.read())

            merge_dictionaries_recursively(default_cfg, cfg)
            self._data = default_cfg # update _data to be the merged config.

    def get(self, path=None, default=None):
        # we need to deep-copy self._data to avoid over-writing its data
        sub_dictionary = dict(self._data)

        if path is None:
            return sub_dictionary

        path_items = path.split("/")[:-1]
        data_item = path.split("/")[-1]

        try:
            recursive_dict = sub_dictionary
            for path_item in path_items:
                recursive_dict = recursive_dict.get(path_item)

            value = recursive_dict.get(data_item, default)
            value = copy.deepcopy(value)  # return a deep copy.

            return value
        except (TypeError, AttributeError):
            return default

    def set(self, path, item):
        assert(path is not None)

        path_items = path.split("/")[:-1]
        data_item = path.split("/")[-1]

        recursive_dict = self._data
        for path_item in path_items:
            next_dict = recursive_dict.get(path_item)
            if next_dict is None:
                recursive_dict[path_item] = next_dict = dict()
            recursive_dict = next_dict

        recursive_dict[data_item] = copy.deepcopy(item)

    def write_to_disk(self, path, name):
        system_utils.make_dir(path)
        filename = path + "/" + name
        with open(filename, "w") as yaml_file:
            yaml.dump(self._data, yaml_file)


def merge_dictionaries_recursively(dict1, dict2):
    ''' Update two config dictionaries recursively.
    Args:
      dict1 (dict): first dictionary to be updated
      dict2 (dict): second dictionary which entries should be preferred
    '''
    if dict2 is None: return

    for k, v in dict2.items():
        if k not in dict1:
            dict1[k] = dict()
        if isinstance(v, dict):
            merge_dictionaries_recursively(dict1[k], v)
        else:
            dict1[k] = v