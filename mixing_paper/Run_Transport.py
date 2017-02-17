"""
Loop over dates, editing namelist file to run different dates, run
Ariane and save the statistical results"""

import argparse
import os

import RunAriane


def _make_namelist(minvalue, maxvalue, dir_name):
    template_filename = 'namelist_template'
    namelist_filename = 'namelist'
    with open(os.path.join(dir_name, namelist_filename), 'wt') as namelist:
        with open(os.path.join(dir_name, template_filename)) as template:
            for line in template.readlines():
                if line[2:6] == 'lmin':
                    namelist.writelines('  lmin= {},\n'.format(minvalue))
                elif line[2:6] == 'lmax':
                    namelist.writelines('  lmax= {},\n'.format(maxvalue))
                else:
                    namelist.writelines(line)


def main(args):
    dir_name = './'
    for nday in range(args.startday, args.startday + args.numberofdays):
        print ('Start', nday)
        _make_namelist(nday, nday, dir_name)
        RunAriane.run_ariane()
        RunAriane.rename_results(nday=nday, labeltype='day')
        print ('End', nday)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'numberofdays', help='Number of different dates to do', type=int)
    parser.add_argument(
        'startday', help='Which day to start with', type=int)
    args = parser.parse_args()
    main(args)
