"""
    test_package_cli.py
    post package installation test of cli.py and toolkit.py

"""
import os
from collections import OrderedDict

from pychunklbl import toolkit


def get_cli_switch_dict(cli_file_name):
    """ Usage: key_switch_dict = get_cli_switch_dict(cli_file_name)
    Get the ordered dictionary of input switch names for python file with "add_argument" - & -- names

    Args:
        cli_file_name:      python file with input args parser

    Returns:
        key_switch_dict:    {'a': argument_a, 'b': bee_arg, ...}
    """
    key_switch_tuples_list = []
    key_switch_dict = {}

    with open(cli_file_name, 'r') as fh:
        lines = fh.readlines()

    trigger_string = 'parser.add_argument('
    if len(lines) > 0:
        for line in lines:
            if trigger_string in line:
                start_loc = line.find(trigger_string) + len(trigger_string)
                sw_keys = line[start_loc:].strip().strip(',').split(',')
                if len(sw_keys) > 1:
                    key_switch_tuples_list.append((sw_keys[1].strip().strip('"').strip('--'),
                                                   sw_keys[0].strip('"').strip('-')))
    if len(key_switch_tuples_list) > 0:
        key_switch_dict = OrderedDict(sorted(key_switch_tuples_list))

    return key_switch_dict


def cli_dot_py_switch_string_from_yml(yml_file_name, key_switch_dict):
    """ Usage: cli_switch_string = cli_dot_py_switch_string_from_yml(yml_file_name)
    open yaml file & build the command line switch string

    Args:
        yml_file_name:
        key_switch_dict:

    Returns:
        cli_switch_string:  a string suitable for appending to python filename.py call
    """
    skip_list = ['run_directory', 'run_file']
    cli_switch_string = ''

    root_dir, yml_file_name = os.path.split(yml_file_name)
    run_pars = toolkit.get_run_parameters(root_dir, yml_file_name)

    for k, v in run_pars.items():
        if isinstance(v, int):
            v = '%i' % (v)
        elif isinstance(v, float):
            v = '%f' % (v)
        elif isinstance(v, bool):
            if v:
                v = True
            else:
                v = False

        if k in key_switch_dict:
            k2 = key_switch_dict[k]
            if not k in skip_list:
                cli_switch_string += '-' + k2 + ' ' + v + ' '

    return cli_switch_string

