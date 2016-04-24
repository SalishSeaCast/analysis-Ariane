"""
Loop over specified length segments, running Ariane and saving Results"""

import argparse
import datetime
import netCDF4 as nc
import numpy as np
import scipy.io as sio
import os
import subprocess

from salishsea_tools import tidetools

TARGET_TMPL = 'SalishSea_1h_{:02d}_grid_{:s}.nc'
FILENAME_TMPL = 'SalishSea_1h_{:%Y%m%d}_{:%Y%m%d}_grid_{:s}.nc'
SUBDIR_TMPL = '{:%d%b%y}'


def make_links(rundate, runlength, runtype):
    print (rundate)
    dir = '/results/SalishSea/'+runtype+'/'
    tardir = 'Links'
    for grid in ['T', 'U', 'V', 'W']:
        for fileno in range(runlength):
            target = TARGET_TMPL.format(fileno+1, grid)
            date = rundate + datetime.timedelta(days=fileno)
            link = FILENAME_TMPL.format(date, date, grid)
            subdir = SUBDIR_TMPL.format(date).lower()
            os.unlink(os.path.join(tardir, target))
            os.symlink(os.path.join(dir, subdir, link),
                       os.path.join(tardir, target))


def find_start_point(nav_lon, nav_lat, xind, yind, drifter, index):
    lon1 = nav_lon[xind, yind]
    lon2 = nav_lon[xind+1, yind]
    lon3 = nav_lon[xind, yind+1]
    lat1 = nav_lat[xind, yind]
    lat2 = nav_lat[xind+1, yind]
    lat3 = nav_lat[xind, yind+1]
    M = np.array([[lon1, lat1, 1],
                 [lon2, lat2, 1],
                 [lon3, lat3, 1]])
    lon_for = np.linalg.solve(M, [0, 1, 0])
    lat_for = np.linalg.solve(M, [0, 0, 1])
    xp = (xind
          + lon_for[0]*drifter['lon'][index]
          + lon_for[1]*drifter['lat'][index]
          + lon_for[2])
    yp = (yind
          + lat_for[0]*drifter['lon'][index]
          + lat_for[1]*drifter['lat'][index]
          + lat_for[2])

    print (xind, xp)
    print (yind, yp)
    return (xp, yp)


# from http://sociograph.blogspot.ca/2011/04/how-to-avoid-gotcha-when-converting.html
def convert_time(matlab_datenum):
    python_datetime = (datetime.datetime.fromordinal(int(matlab_datenum))
                       + datetime.timedelta(days=matlab_datenum%1)
                       - datetime.timedelta(days = 366))
    return python_datetime


def get_drifter(drifterid):
    drifters = sio.loadmat('driftersPositions.mat')
    mattime = np.array(
                  [t[0] for t in drifters['drifters'][0][drifterid-1][4]])
    pytime = []
    for i, time in enumerate(mattime):
        time = convert_time(time)
        pytime.append(time)

    drifter = {'name': drifters['drifters'][0][drifterid-1][0][0],
               'id': drifters['drifters'][0][drifterid-1][1][0],
               'lat': np.array(
                    [t[0] for t in drifters['drifters'][0][drifterid-1][2]]),
               'lon': np.array(
                    [t[0] for t in drifters['drifters'][0][drifterid-1][3]]),
               'time': pytime, }
    return drifter


def write_initial_positions(index, drifter, grid):
    bathy, nav_lon, nav_lat = tidetools.get_bathy_data(grid)
    xind, yind = tidetools.find_closest_model_point(
                  drifter['lon'][index], drifter['lat'][index],
                  nav_lon, nav_lat, bathy, allow_land=True)
    xp, yp = find_start_point(nav_lon, nav_lat, xind, yind, drifter, index)
    initial_conditions = np.ones((81, 5))
    # longitude index
    initial_conditions[0:-1:3, 0] = yp
    initial_conditions[1:-1:3, 0] = yp - 0.5
    initial_conditions[2:81:3, 0] = yp + 0.5
    # latitude index
    for i in range(0, 81, 9):
        initial_conditions[0+i:3+i, 1] = xp + 0.5
        initial_conditions[0+3+i:3+3+i, 1] = xp
        initial_conditions[0+6+i:3+6+i, 1] = xp + 1
    # depth
    initial_conditions[0:27, 2] = -1.5
    initial_conditions[27:54, 2] = -2.5
    initial_conditions[54:81, 2] = -3.5
    # time
    tp = (drifter['time'][index].hour
          + drifter['time'][index].minute/60.
          + drifter['time'][index].second/3600.)
    for i in range(0, 81, 27):
        initial_conditions[0+i:9+i, 3] = tp
        initial_conditions[0+9+i:9+9+i, 3] = tp + 0.25
        initial_conditions[0+18+i:9+18+i, 3] = tp - 0.25

    np.savetxt('initial_positions.txt', initial_conditions, fmt='%10.5f')


def run_ariane():
    with open('babypoo', 'wt') as stdout:
        with open('errpoo', 'wt') as stderr:
            subprocess.run(
                "ariane", stdout=stdout, stderr=stderr,
                universal_newlines=True)


def rename_results(runtype, drifterid, index):
    filename = 'ariane_trajectories_qualitative.nc'
    newname = 'traj_'+runtype+'_d_'+str(drifterid)+'_i_'+str(index)+'.nc'
    print (newname)
    os.rename(filename, newname)


def find_indexes(ci, drifter, runlength):
    ni = []
    ni.append(ci)
    while ci != 'stop':
        nv = next((obj for obj in drifter['time'][ci:0:-1] if obj >
                   drifter['time'][ci] + datetime.timedelta(hours=runlength)),
                  'stop')
        if nv == 'stop':
            ci = nv
        else:
            ti = drifter['time'].index(nv)
            ni.append(ti)
            ci = ti
    return ni


def main(args):
    drifterid = args.drifterid
    firstindex = args.firstindex
    runlength = args.runlength
    runtype = args.runtype

    drifter = get_drifter(drifterid)
    indexes = find_indexes(firstindex, drifter, runlength)
    grid = nc.Dataset('../../nemo-forcing/grid/bathy_meter_SalishSea2.nc')
    for index in indexes:
        write_initial_positions(index, drifter, grid)
        rundate = drifter['time'][index]
        make_links(rundate.date(), 2, runtype)
        print ('Start', rundate)
        run_ariane()
        rename_results(runtype, drifterid, index)
        print ('End', rundate)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'drifterid', help='Which drifter to follow', type=int)
    parser.add_argument(
        'firstindex', help='Starting Index', type=int)
    parser.add_argument(
        'runlength', help='Number of hour between segments', type=int)
    parser.add_argument(
        'runtype', help='nowcast or nowcast-green', type=str)
    args = parser.parse_args()
    main(args)
