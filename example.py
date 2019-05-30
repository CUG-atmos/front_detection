#!/usr/bin/env python
import numpy as np 
import front_detection as fd
from front_detection import catherine
from scipy.ndimage import label, generate_binary_structure
import glob
from netCDF4 import Dataset

import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import datetime as dt
import plotter
import reader

# plt.style.use(['ggplot', 'classic'])
plt.style.use(['seaborn'])

year = 2007
model_name = 'merra2'
hemis = 'NH'

folder_format = '/localdrive/drive10/jj/datacycs/out_nc/{0}/{1}/{2}/' 

model_folder = '/mnt/drive5/merra2/six_hrly/'

print('Debug: Reading in data ...', end='')

# loading in merra2 inst6_3d_ana_Np data
ncid = Dataset('/localdrive/drive10/merra2/inst6_3d_ana_Np/MERRA2_300.inst6_3d_ana_Np.20070101.nc4', 'r')
ncid.set_auto_mask(False)
in_lon = ncid.variables['lon'][:]
in_lat = ncid.variables['lat'][:]
in_lev = ncid.variables['lev'][:]
in_time = np.asarray(ncid.variables['time'][:], dtype=float)

in_slp = ncid.variables['SLP']
T = ncid.variables['T']
U = ncid.variables['U']
V = ncid.variables['V']
geoH = ncid.variables['H']
PS = ncid.variables['PS']

# creating the cdt grid 
lon, lat = np.meshgrid(in_lon, in_lat)

# getting the index of the level 850
lev850 = np.where(in_lev == 850)[0][0]

print(' Completed!')
 

# TODO
# I can probably move the read in all centers here, for the given range of years!

for t_step in range(1, in_time.shape[0]):

  # creating a datetime variable for the current time step
  date = dt.datetime(2007, 1, 1) + dt.timedelta(minutes=in_time[t_step])
  print(date)

  # getting SLP values for MERRA2
  slp = in_slp[t_step, :, :]/100.
  
  # getting Wind and temperature at 850 hPa for MERRA2
  prev_u850 = U[t_step-1, lev850, :, :]
  prev_u850[prev_u850 == U._FillValue] = np.nan
  u850 = U[t_step, lev850, :, :]
  u850[u850 == U._FillValue] = np.nan

  prev_v850 = V[t_step-1, lev850, :, :]
  prev_v850[prev_v850 == V._FillValue] = np.nan
  v850 = V[t_step, lev850, :, :]
  v850[v850 == V._FillValue] = np.nan
 
  # getting the temperature at 850 hPa
  t850 = T[t_step, lev850, :, :]
  t850[t850 == T._FillValue] = np.nan
  theta850 = fd.theta_from_temp_pres(t850, 850)

  # getting the 1km values of temperature
  # the code below is a work around to speed up the code, isntead of running a nest for loop

  # getting the height values from MERRA2
  H = geoH[t_step, :, :, :]
  H[H == geoH._FillValue] = np.nan
  H850 = geoH[t_step, lev850, :, :]
  H850[H850 == geoH._FillValue] = np.nan
  # H = H / 9.8

  # getting the surface pressure in hPa 
  surface_pres = PS[t_step, :, :]/100.
  surface_pres[surface_pres == PS._FillValue] = np.nan

  pres_3d = np.repeat(in_lev[:, np.newaxis], H.shape[1], axis=-1) # creating the pressure level into 3d array
  pres_3d = np.repeat(pres_3d[:, :, np.newaxis], H.shape[2], axis=-1) # creating the pressure level into 3d array 

  ps_3d = np.repeat(surface_pres[np.newaxis,:,:], H.shape[0], axis=0)

  # getting the surface height using the surface pressure and geo-potential height 
  pres_diff = np.abs(pres_3d - ps_3d)
  pres_diff_min_val = np.nanmin(pres_diff, axis=0) 
  pres_diff_min_val3d = np.repeat(pres_diff_min_val[np.newaxis, :, :], H.shape[0], axis=0)
  surface_H_ind = (pres_diff == pres_diff_min_val3d)
  ps_height = np.ma.masked_array(np.copy(H), mask=~surface_H_ind, fill_value=np.nan)  
  ps_height = np.nanmin(ps_height.filled(), axis=0) # surface height in km 

  # 1km height above surface
  h1km = ps_height + 1000. 
  h1km_3d = np.repeat(h1km[np.newaxis, :, :], H.shape[0], axis=0); 

  # difference between geopotential height and 1km height
  h1km_diff = np.abs(H - h1km_3d) 
  h1km_diff_min_val = np.nanmin(h1km_diff, axis=0) 
  h1km_diff_min_val_3d = np.repeat(h1km_diff_min_val[np.newaxis, :, :], H.shape[0], axis=0)
  h1km_ind = (h1km_diff == h1km_diff_min_val_3d)

  T_3d = np.ma.masked_array(T[t_step, :, :, :], mask=~h1km_ind, fill_value=np.nan) # creating a temperature 3d array
  t1km = np.nanmin(T_3d.filled(),axis=0)  # getting the 1km value by finding the minimum value
  t1km[t1km == T._FillValue] = np.nan
  
  U_3d = np.ma.masked_array(U[t_step, :, :, :], mask=~h1km_ind, fill_value=np.nan) # creating a temperature 3d array
  u1km = np.nanmin(U_3d.filled(),axis=0)  # getting the 1km value by finding the minimum value
  u1km[u1km == U._FillValue] = np.nan
  
  V_3d = np.ma.masked_array(V[t_step, :, :, :], mask=~h1km_ind, fill_value=np.nan) # creating a temperature 3d array
  v1km = np.nanmin(V_3d.filled(),axis=0)  # getting the 1km value by finding the minimum value
  v1km[v1km == V._FillValue] = np.nan

  pres = np.ma.masked_array(pres_3d, mask=~h1km_ind, fill_value=np.nan) # masking out pressure values using minimum 1km mask
  p1km = np.nanmin(pres.filled(), axis=0) # getting the pressure at 1km

  # computing the theta value at 1km
  theta1km = fd.theta_from_temp_pres(t1km, p1km) 

  # smoothing out the read in arrays
  iter_smooth = 10
  center_weight = 4.

  theta850 = fd.smooth_grid(theta850, iter=iter_smooth, center_weight=center_weight) 
  theta1km = fd.smooth_grid(theta1km, iter=iter_smooth, center_weight=center_weight) 

  u1km = fd.smooth_grid(u1km, iter=iter_smooth, center_weight=center_weight) 
  v1km = fd.smooth_grid(v1km, iter=iter_smooth, center_weight=center_weight) 

  prev_u850 = fd.smooth_grid(prev_u850, iter=iter_smooth, center_weight=center_weight) 
  u850 = fd.smooth_grid(u850, iter=iter_smooth, center_weight=center_weight) 
  prev_v850 = fd.smooth_grid(prev_v850, iter=iter_smooth, center_weight=center_weight) 
  v850 = fd.smooth_grid(v850, iter=iter_smooth, center_weight=center_weight) 

  # computing the simmonds fronts
  f_sim = fd.simmonds_et_al_2012(lat, lon, prev_u850, prev_v850, u850, v850) 

  # computing the hewson fronts using 1km temperature values, and geostrophic U & V winds at 850 hPa
  f_hew, var = fd.hewson_1998(lat, lon, theta1km, H850)
 
  # getting the front types
  wf_hew = f_hew['wf']
  cf_hew = f_hew['cf']
  cf_sim = f_sim['cf']
  wf_temp_grad = f_hew['temp_grad']

  wf_hew[np.isnan(wf_hew)] = 0
  cf_hew[np.isnan(cf_hew)] = 0
  cf_sim[np.isnan(cf_sim)] = 0

  wf = np.copy(wf_hew)
  cf = np.double((cf_hew + cf_sim) > 0)

  orig_wf = np.copy(wf)
  orig_cf = np.copy(cf)

  # cf = np.copy(cf_hew)
  
  ######################################################################################### 
  ############################ CODE TO CLEAN UP THE FRONTS ################################
  ######################################################################################### 

  ##############################################################
  ###### Group Fronts and get rid of small clusters ############
  ##############################################################

  # Grouping clusters of fronts
  s = generate_binary_structure(2,2)
  w_label, w_num = label(wf, structure=s)
  c_label, c_num = label(cf, structure=s)

  # getting the mean lat and lon of the clusters
  w_lat = np.empty((w_num+1,))*np.nan
  w_lon = np.empty((w_num+1,))*np.nan
  
  c_lat = np.empty((c_num+1,))*np.nan
  c_lon = np.empty((c_num+1,))*np.nan

  # keeping only clusters with 3 or more 
  # also saving the mean lat and lon of the cluster
  for i_w in range(1, w_num+1):
    ind = (w_label == i_w)
    x_ind, y_ind = np.where(ind)
    if (len(x_ind) < 3):
      wf[w_label == i_w] = 0.
      w_label[w_label == i_w] = 0.
    else: 
      w_lat[i_w] = np.nanmean(lat[ind])
      w_lon[i_w] = np.nanmean(lon[ind])

    # get rid of cluster centers below 20 or above 70
    if (abs(w_lat[i_w]) < 20) | (abs(w_lat[i_w]) > 70):
      w_lat[i_w] = np.nan
      w_lon[i_w] = np.nan
      wf[w_label == i_w] = 0.
      w_label[w_label == i_w] = 0.


  # cleaning up the cold fronts and picking only the eastern most point
  for i_c in range(1, c_num+1):
    ind = (c_label == i_c)
    x_ind, y_ind = np.where(ind)

    # keeping only clusters of 3 or more
    # also saving the mean lat and lon of the cluster
    if (len(x_ind) < 3):
      cf[c_label == i_c] = 0.
      c_label[c_label == i_c] = 0.
      continue
    else: 
      c_lat[i_c] = np.nanmean(lat[ind])
      c_lon[i_c] = np.nanmean(lon[ind])
    
    # get rid of cluster centers below 20 or above 70
    if (abs(c_lat[i_c]) < 20) | (abs(c_lat[i_c]) > 70):
      c_lat[i_c] = np.nan
      c_lon[i_c] = np.nan
      cf[c_label == i_c] = 0.
      c_label[c_label == i_c] = 0.
      continue

    # quick scatched up way to keep only eastern most points
    # optimize this later
    # FIXME issues with the edges
    for uni_x in set(x_ind):
      y_for_uni_x = y_ind[(x_ind == uni_x)]
      remove_y = y_for_uni_x[y_for_uni_x != np.nanmax(y_for_uni_x)]
      if (remove_y.size > 0):
        for y in remove_y: 
          cf[uni_x, y] = 0.
          c_label[uni_x, y] = 0.

    # after keeping the eastern most point, we do a new check to see
    # if the number of points is less than 3
    # if so we remove this detected front
    if (np.sum(cf[x_ind, y_ind]) < 3):
      cf[c_label == i_c] = 0.
      c_label[c_label == i_c] = 0.


  ############# Get Centers for the given date ######################
  # create tracked cyclone centers
  # find the centers for the given date
  # 
  # fd_date = date - dt.timedelta(hours=6.)
  # FIXME move the all_centers read to the top
  # FIXME check for edges/dateline  
  # FIXME --> i kind of did this, check below, i do condiitons based on lon -180,180 and 0, 360
  fd_date = date
  in_file = '/mnt/drive1/processed_data/tracks/merra2_tracks/ERAI_%d_cyc.mat'%(fd_date.year)
  all_centers = reader.read_center_from_mat_file(in_file)
  center = all_centers.find_centers_for_date(fd_date)

  ############# Storm Attribution ######################
  # Loop through the centers found via the tracking code for the time step
  w_keep_grid = np.zeros(lon.shape)
  c_keep_grid = np.zeros(lon.shape)

  w_lon_0_360 = np.copy(w_lon)
  w_lon_0_360[w_lon_0_360 < 0] += 360.
  c_lon_0_360 = np.copy(c_lon)
  c_lon_0_360[c_lon_0_360 < 0] += 360.

  for i_center, _  in enumerate(center.lat): 

    # used to keep track of the cold front clusters for each given storm center
    c_keep_grid_for_center = np.zeros(lon.shape)

    # have to account for dateline
    w_dist = fd.distance_in_deg(center.lat[i_center], center.lon[i_center], w_lat, w_lon)
    w_dist_0_360 = fd.distance_in_deg(center.lat[i_center], center.lon[i_center], w_lat, w_lon_0_360)

    c_dist = fd.distance_in_deg(center.lat[i_center], center.lon[i_center], c_lat, c_lon)
    c_dist_0_360 = fd.distance_in_deg(center.lat[i_center], center.lon[i_center], c_lat, c_lon_0_360)

    ################ Cleaning up warm fronts
    # keeping clusters within 15 degrees from the storm centers
    # keeping clusters where the center lat - mean cluster lat < 5
    # keeping clusters where the center lon is east of the storm center
    w_dist_ind = (w_dist < 15) | (w_dist_0_360 < 15)
    w_dist_lat_ind = (abs(center.lat[i_center] - w_lat) < 5)
    w_east_lon_ind = ((center.lon[i_center] - w_lon) < 0) | ((center.lon[i_center] - w_lon_0_360) < 0)

    w_keep_ind = np.argwhere(w_dist_ind & w_dist_lat_ind & w_east_lon_ind)

    # if there are two warm fronts we have to keep one with the maximum mean temp gradient
    if (len(w_keep_ind > 1)):
      mean_temp_grads = np.zeros((len(w_keep_ind), ))
      for ii, i_keep_ind in enumerate(w_keep_ind):
        mean_temp_grads[ii] = np.nanmean(wf_temp_grad[w_label == i_keep_ind])

      max_ind = w_keep_ind[np.nanargmax(mean_temp_grads)]
      w_keep_grid[(w_label == max_ind) & (wf == 1)] = 1
    else:
      w_keep_grid[np.isin(w_label, w_keep_ind) & (wf == 1)] = 1


    # w_keep_grid[np.isin(w_label, w_keep_ind) & (wf == 1)] = 1
    
    ################ Cleaning up warm fronts
    # keeping clusters within 15 degrees from the storm centers
    # keeping clusters where the mean lon is within 7.5 degrees from the center
    # keeping centers where the mean lat is equatorward of the storm center 
    # keeping centers where the mean lon is no further than 15 deg from lon of center
    c_dist_ind = (c_dist < 15) | (c_dist_0_360 < 15)
    c_dist_lon_ind = (abs(center.lon[i_center] - c_lon) < 7.5) | (abs(center.lon[i_center] - c_lon_0_360) < 7.5)
    c_equator_ind = (abs(c_lat) < abs(center.lon[i_center]))
    c_west_lon_ind = ((c_lon - center.lon[i_center]) < 15) | ((c_lon_0_360 - center.lon[i_center]) < 15)

    c_keep_ind = np.argwhere(c_dist_ind & c_dist_lon_ind & c_equator_ind & c_west_lon_ind)
    c_keep_grid[np.isin(c_label, c_keep_ind) & (cf == 1)] = 1


    # additional conditions base on the acutal clusters, instead of the mean 
    for i_keep_cf in c_keep_ind: 
      i_keep_grid = (c_label == i_keep_cf)

      i_c_lat = lat[i_keep_grid]
      i_c_lon = lon[i_keep_grid]

      i_c_lon_0_360 = np.copy(i_c_lon)
      i_c_lon_0_360[i_c_lon_0_360 < 0] += 360

      i_c_dist = fd.distance_in_deg(center.lat[i_center], center.lon[i_center], i_c_lat, i_c_lon)
      i_c_dist_0_360 = fd.distance_in_deg(center.lat[i_center], center.lon[i_center], i_c_lat, i_c_lon_0_360)
      i_c_dist_ind = (i_c_dist < 25) | (i_c_dist_0_360 < 25)

      # if there is atleast one point in the cluster within 25 degree of the low
      if (not np.any(i_c_dist_ind)):
        c_keep_grid[c_label == i_keep_cf] = 0.
        c_label[c_label == i_keep_cf] = 0.
        continue
      
      i_c_max_lat = np.nanmax(i_c_lat)
      i_c_max_lon = np.nanmax(i_c_lon)

      # if max lat of front is < 5 degrees of poleward of the low
      if not (abs(i_c_max_lat) - abs(center.lat[i_center]) < 5): 
        c_keep_grid[c_label == i_keep_cf] = 0
        c_label[c_label == i_keep_cf] = 0.
        continue

      # only setting the clusters we selected after all the criteria as 1.
      c_keep_grid_for_center[c_label == i_keep_cf] = 1.

    # keep on the right most clusters for each latitude for a given storm center
    x_ind, y_ind = np.where(c_keep_grid_for_center == 1)

    # quick scatched up way to keep only eastern most points
    # set up a grid called remove_grid, which I will to use clean up c_keep_grid
    # optimize this later
    # FIXME issues with the edges
    remove_grid = np.zeros(lon.shape)
    for uni_x in set(x_ind):
      y_for_uni_x = y_ind[(x_ind == uni_x)]
      remove_y = y_for_uni_x[y_for_uni_x != np.nanmax(y_for_uni_x)]
      if (remove_y.size > 0):
        for y in remove_y: 
          remove_grid[uni_x, y] = 1.
   
    # getting rid of all the points that are not the most eastern for a given storm center
    c_keep_grid[remove_grid == 1] = 0
   
  # cleaning up the fronts grid and label grids
  cf[c_keep_grid == 0] = 0
  c_label[c_keep_grid == 0] = 0
  wf[w_keep_grid == 0] = 0
  w_label[w_keep_grid == 0] = 0

  ############# PLOTTING THE IMAGES
  llat = 0
  ulat = 90
  llon = -180
  ulon = 0 

  plt.figure(figsize=(8,12))
  plt.subplot(3,1,1)
  fronts = orig_wf*10 + orig_cf*-10
  # fronts = cf*-10
  fronts[~((fronts == 10) | (fronts == -10))] = np.nan
  m = Basemap(projection='cyl', urcrnrlat=ulat, llcrnrlat=llat, urcrnrlon=ulon, llcrnrlon=llon)
  csf = plt.contourf(lon, lat, var)
  # csf = plt.contourf(lon, lat, slp)
  cs = plt.contour(lon, lat, slp, lw=0.1, alpha=0.5, ls='--', colors='k', levels=np.arange(980, 1100, 5))
  plt.clabel(cs, inline=1., fontsize=10., fmt='%.0f')
  pc = m.pcolormesh(lon, lat, fronts, cmap='bwr')
  m.colorbar(csf)
  m.drawcoastlines(linewidth=0.2)
  plt.axhline(y=0., linewidth=1.0, linestyle='--')
  plt.plot(center.lon, center.lat, 'y*', markersize=5)
  plt.title('Before Storm Attribution Fronts')

  plt.subplot(3,1,2)
  fronts = wf*10 + cf*-10
  # fronts = cf*-10
  fronts[~((fronts == 10) | (fronts == -10))] = np.nan
  m = Basemap(projection='cyl', urcrnrlat=ulat, llcrnrlat=llat, urcrnrlon=ulon, llcrnrlon=llon)
  csf = plt.contourf(lon, lat, var)
  # csf = plt.contourf(lon, lat, slp)
  cs = plt.contour(lon, lat, slp, lw=0.1, alpha=0.5, ls='--', colors='k', levels=np.arange(980, 1100, 5))
  plt.clabel(cs, inline=1., fontsize=10., fmt='%.0f')
  pc = m.pcolormesh(lon, lat, fronts, cmap='bwr')
  m.colorbar(csf)
  m.drawcoastlines(linewidth=0.2)
  plt.axhline(y=0., linewidth=1.0, linestyle='--')
  plt.plot(center.lon, center.lat, 'y*', markersize=5)
  plt.title('My Fronts')
  
  cath_wf, cath_cf, cath_slp, cath_lat, cath_lon, cf_lat, cf_lon, wf_lat, wf_lon = catherine.fronts_for_date(lat, lon, date.year, date.month, date.day, date.hour)
  
  plt.subplot(3,1,3)
  fronts = cath_wf*10 + cath_cf*-10
  fronts[~((fronts == 10) | (fronts == -10))] = np.nan
  m = Basemap(projection='cyl', urcrnrlat=ulat, llcrnrlat=llat, urcrnrlon=ulon, llcrnrlon=llon)
  # csf = plt.contourf(cath_lon, cath_lat, cath_slp)
  csf = plt.contourf(lon, lat, var)
  # csf = plt.contourf(lon, lat, slp)
  cs = plt.contour(lon, lat, slp, lw=0.1, alpha=0.5, ls='--', colors='k', levels=np.arange(980, 1100, 5))
  plt.clabel(cs, inline=1., fontsize=10., fmt='%.0f')
  pc = m.pcolormesh(lon, lat, fronts, cmap='bwr')
  m.colorbar(csf)
  m.drawcoastlines(linewidth=0.2)
  plt.axhline(y=0., linewidth=1.0, linestyle='--')
  center.lon[center.lon > 180] -= 360
  plt.plot(center.lon, center.lat, 'y*', markersize=5)
  plt.title('Catherine Fronts')

  plt.savefig('./images/test.png', dpi=300)

  plt.show()
  
  break

ncid.close()

print(date.year, date.month, date.day, date.hour)
