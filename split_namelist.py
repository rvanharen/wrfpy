#!/usr/bin/env python

'''
description:    split WRF namelist into first domain / rest
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

import f90nml
import copy
import mpl_toolkits.basemap.pyproj as pyproj 

class split_nml_shared(config):
  '''
  shared functionality for split_nml_wrf and split_nml_wps
  '''
  def __init__(self):
    config.__init__(self)

  def read_namelist(self, namelist)
    '''
    read user supplied namelist
    '''
    self.nml = f90nml.read(namelist)
    # get list of namelist keys
    self.keys = self.wrf_nml.keys()


  def create_namelist_copies(self)
    '''
    create two (shallow) copies of the variable containing the namelist
    which will be used to create the output namelists
    '''
    self.nml_coarse = copy.copy(self.nml)
    self.nml_fine = copy.copy(self.nml)


  def modify_coarse_namelist(self):
    '''
    modify coarse namelist (resulting namelist contains outer domain only)
    '''
    for section in self.nml.keys():
      for key in self.nml[section].keys():
        if isinstance(self.nml[section][key], list):
          if key not in ['eta_levels']:  # don't modify these keys
            # use only first item from list
            self.nml_coarse[section][key] = self.nml[section][key][0]
        elif key == 'max_dom':
          self.nml[section][key] = 1  # only outer domain
        # else don't modify the key


  def modify_fine_namelist(self):
    '''
    modify fine namelist (resulting namelist contains all but outer domain)
    '''
    special_cases1 = ['parent_grid_ratio', 'i_parent_start', 'j_parent_start',
                     'parent_time_step_ratio']
    special_cases2 = ['grid_id', 'parent_id']
    for section in self.nml.keys():
      for key in self.nml[section].keys():
        if isinstance(self.nml[section][key], list):
          if key in special_cases1:
            if len(self.nml][section][key] > 2:
              self.nml_fine[section][key] = 1 + self.nml[
                section][key][2:]
            else:
              self.nml_fine[section][key] = 1
          elif key in special_cases2:
            self.nml_fine[section][key] = self.nml[section][key][:-1]
          elif key not in ['eta_levels']:  # don't modify these keys
            # use only first item from list
            self.nml_fine[section][key] = self.nml[section][key][0]
        elif key=='time_step':
          self.nml_fine[section][key] = int(
            float(self.nml[section][key]) / self.nml['domains'][
              'parent_grid_ratio'][1])
        elif key=='max_dom':
          self.nml_fine[section][key] = self.nml[section][key] - 1




class split_nml_wrf(split_nml_shared):
  def __init__(self):
    split_nml_shared.__init__(self)
    split_nml_shared.read_namelist(wrf_namelist)  # TODO: define wrf_namelist
    split_nml_shared.create_namelist_copies()
    split_nml_shared.modify_coarse_namelist()
    split_nml_shared.modify_fine_namelist()
    self._save_namelists()


  def _save_namelists(self):
    '''
    write coarse and fine WRF namelist.input to the respective run directories
    as namelist.forecast
    '''
    coarse_namelist_dir = self.config{'filesystem'}{'wrf_run_dir'} + '_coarse'
    fine_namelist_dir = self.config{'filesystem'}{'wrf_run_dir'} + '_fine'
    self.nml_coarse.write(os.path.join(coarse_namelist_dir,
                                       'namelist.forecast'))
    self.nml_fine.write(os.path.join(fine_namelist_dir,
                                     'namelist.forecast'))




class split_nml_wps(split_nml_shared):
  def __init__(self):
    split_nml_shared.__init__(self)
    split_nml_shared.read_namelist(wps_namelist)  # TODO: define wps_namelist
    split_nml_shared.create_namelist_copies()
    split_nml_shared.modify_coarse_namelist()
    self._modify_fine_namelist_wps()
    self._save_namelists()


  def _modify_fine_namelist_wps(self):
    '''
    wps specific fine namelist changes
    '''
    # calculate new dx, dy, ref_lon, ref_lat for second domain
    self._calculate_center_second_domain()
    # modify dx, dy, ref_lon, ref_lat for second domain
    self.nml_fine['geogrid']['dx'] = self.dx
    self.nml_fine['geogrid']['dy'] = self.dy
    self.nml_fine['geogrid']['ref_lon'] = self.ref_lon
    self.nml_fine['geogrid']['ref_lat'] = self.ref_lat


  def _calculate_center_second_domain(self):
    '''
    Calculate the center of the second domain for running in UPP mode
    '''
    grid_ratio = self.nml['geogrid']['parent_grid_ratio'][1]
    i_start = self.nml['geogrid']['i_parent_start']
    j_start = self.nml['geogrid']['j_parent_start']
    e_we = self.nml['geogrid']['e_we']
    e_sn = self.nml['geogrid']['e_sn']
    ref_lat = self.nml['geogrid']['ref_lat']
    ref_lon = self.nml['geogrid']['ref_lon']
    truelat1 = self.nml['geogrid']['truelat1']
    truelat2 = self.nml['geogrid']['truelat2']
    # new dx and dy
    self.dx = float(self.nml['geogrid']['dx']) / grid_ratio
    self.dy = float(self.nml['geogrid']['dy']) / grid_ratio
    # define projection string
    projstring  = ("+proj=lcc +lat_1=%s +lat_2=%s +lat_0=%s +lon_0=%s ",
                   "+x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
                   %(truelat1, truelat2, ref_lat, ref_lon))
    lambert = pyproj.Proj( projstring )
    # calculate east/west/south/north
    west = (-self.nml['geogrid']['dx'] * (e_we[0] - 1) * 0.5) + (
      (i_start[1] - 1) * self.nml['geogrid']['dx'])
    south = (-self.nml['geogrid']['dy'] * (e_sn[0] - 1) * 0.5) + (
      (j_start[1] - 1) * self.nml['geogrid']['dy'])
    east = (self.nml['geogrid']['dx'] * (e_we[0] - 1) * 0.5) + (
      (e_we[1] - 1) * self.dx)
    north = (self.nml['geogrid']['dy'] * (e_sn[0] - 1) * 0.5) + (
      (e_sn[1] - 1) * self.dy)
    # new ref_lat and ref_lon
    self.ref_lon, self.ref_lat = projection((west + east) * 0.5,
                                            (north + south) * 0.5,
                                            inverse=True )


  def _save_namelists(self):
    '''
    write coarse and fine WRF namelist.input to the respective run directories
    as namelist.forecast
    '''
    coarse_namelist_dir = os.path.join(self.config{'filesystem'}{'work_dir'},
                                       'wps_coarse')
    fine_namelist_dir = os.path.join(self.config{'filesystem'}{'work_dir'},
                                       'wps_fine')
    self.nml_coarse.write(os.path.join(coarse_namelist_dir,
                                           'namelist.wps'))
    self.nml_fine.write(os.path.join(fine_namelist_dir,
                                         'namelist.wps'))