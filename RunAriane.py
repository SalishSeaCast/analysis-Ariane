"""
Loop over dates, setting up a series of forcing links, running Ariane
and saving the statistic results"""

import argparse
import arrow
import os
import subprocess

TARGET_TMPL = 'SalishSea_1h_{:02d}_grid_{:s}.nc'
FILENAME_TMPL = 'SalishSea_1h_{:%Y%m%d}_{:%Y%m%d}_grid_{:s}.nc'
SUBDIR_TMPL = '{:%d%b%y}'


def make_links(rundate, runlength):
    dir = '/results/SalishSea/nowcast/'
    tardir = 'Links'
    for grid in ['T', 'U', 'V', 'W']:
        for fileno in range(runlength):
            target = TARGET_TMPL.format(fileno+1, grid)
            date = rundate.replace(days=+fileno).datetime
            link = FILENAME_TMPL.format(date, date, grid)
            subdir = SUBDIR_TMPL.format(date).lower()
#            os.unlink(os.path.join(tardir, target))
            os.symlink(os.path.join(dir, subdir, link),
                       os.path.join(tardir, target))


def run_ariane():
    with open('babypoo', 'wt') as stdout:
        with open('errpoo', 'wt') as stderr:
            subprocess.run(
                "ariane", stdout=stdout, stderr=stderr,
                universal_newlines=True)


def rename_results(rundate=arrow.utcnow(), nday=1, labeltype='date'):
    tempdir = 'TempStatsFiles/'
    finaldir = 'StatsFiles'
    for filename in os.listdir(tempdir):
        if labeltype == 'date':
            newname = (filename.split('.')[0] + '.' +
                       SUBDIR_TMPL.format(rundate.datetime).lower())
        else:
            newname = filename.split('.')[0] + '.day' + str(nday)
        os.rename(os.path.join(tempdir, filename),
                  os.path.join(finaldir, newname))


def main(args):
    initialrundate = arrow.get(args.initialrundate, 'YYYY-MM-DD')
    for nday in range(args.numberofdays):
        rundate = initialrundate.replace(days=+nday)
        print ('Start', rundate)
        if args.forback == 'forward':
            startfile = rundate
        elif args.forback == 'backward':
            startfile = rundate.replace(days=-(args.runlength-1))
        make_links(startfile, args.runlength)
        print ('Startfile', startfile)
        run_ariane()
        rename_results(rundate=rundate)
        print ('End', rundate)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'initialrundate', help='Date to start from as YYYY-MM-DD', type=str)
    parser.add_argument(
        'numberofdays', help='Number of different dates to do', type=int)
    parser.add_argument(
        'runlength', help='Number of days to track particles', type=int)
    parser.add_argument('forback', help='Run forward or backward', type=str)
    args = parser.parse_args()
    main(args)
