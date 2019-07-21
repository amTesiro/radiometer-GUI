#coding: utf-8
#! /usr/bin/env python
# This Python file uses the following encoding: utf-8
import os
import sys
import re
import time
import subprocess
import traceback
import pickle
import math
import copy
import logging
from special_process import getInputDict, set_option_multi_value, getRunMode, change_um_to_nm, convert_cloud_to_file, check_atmosphere_file, change_aerosol_haze, change_aerosol_season, change_aerosol_vulcan, get_atmos_file, create_new_file, create_grid_file_by_count, create_grid_file, getQtInputDict


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def getException(func):
    def deco(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = "ERROR:%s" % e
            #widgets.LogWindow(None, error_str)
            logging.info(traceback.format_exc())
            return False, traceback.format_exc()

    return deco

class RunUvspecProcess(object):
    def __init__(self, input_file, output_file):
        #threading.Thread.__init__(self)
        self.input_file = input_file
        self.output_file = output_file
        self.log = []
    def run(self):
        self.log.append("Running uvspec.\nInput file: %s \nOutput file: %s\n" % \
                         (self.input_file, self.output_file))

        exit_value = 0

        process_in = open(self.input_file, "r")
        process_out = open(self.output_file, "w")
        process_err = open(self.output_file + ".err", "w")

        try:
            process = subprocess.Popen("uvspec", stdin=process_in,
                                    stdout=process_out, stderr=process_err)
        except OSError:
            self.log.append("\n!!!Could not find UVSPEC in your PATH!!!\n\nIt is strongly recommended to change your PATH and restart the GUI!\n")
            time.sleep(5)
            self.log.append("cancel")
            self.exit_value = "Error"
            return self.log

        data = ""

        self.log.append("Uvspec has started.\n")
        while process.poll() == None: # None inidicates that uvspec is not yet finished
            time.sleep(0.1)
            #self.log.append("cancel")

        process_err.close()
        process_err = open(process_err.name, "r")

        data = process_err.read()
        if data.upper().find("ERROR") != -1: # catch errors with return code 0
                exit_value = "Error"

        process_in.close()
        process_out.close()
        process_err.close()

        self.log.append(data)
        self.exit_value = exit_value
        return self.log

        if not exit_value or process.poll() != 0: # correcting uvspec returncodes
            exit_value = process.poll()
def Save(fname, chose_data):
    data = ["" + "#Generated by libRadtran GUI(2019-07)\n"]
    if u"global_mode 单点模式" in chose_data:
        chose_data.remove(u"global_mode 单点模式")
    data.extend(chose_data)
    try:
        logger.info("Saving input file to '%s'." % (fname))
        f = open(fname, "w")
        f.write("\n".join(data).strip())
        logger.info("input:" + "\n".join(data).strip())
        f.write("\n")
        f.close()
    except IOError:
        msg = "Could not save input file to '%s'." % (fname)
        #print msg
        ErrorMessage(msg)

@getException
def OnRunSingle(input_list, out_file):
    #app = wx.App(redirect=variables.redirect, filename=variables.redirect_file)
    tmp_file = os.path.abspath(".tmp_UVSPEC.INP")
    Save(tmp_file, input_list) # Save a temporary INP file with the latest modifications
    chl_thread = RunUvspecProcess(tmp_file, out_file)
    chl_thread.run()
    logger.info(chl_thread.log)
    return True, chl_thread.log

def SaveCycle(fname, input_data):
    data = ["" + "#Generated by libRadtran GUI(2019)\n"]
    data.extend(input_data)
    try:
        f = open(fname, "w")
        f.write("\n".join(data).strip())
        logger.info("input:" + "\n".join(data).strip())

        f.write("\n")
        f.close()
    except IOError:
        msg = "Could not save input file to '%s'." % (fname)
        #print msg
        ErrorMessage(msg)

@getException
def OnRunNew(data_dict, out_file):
    out_file_list = []
    total_log = []
    total_exit_value = 0

    input_dict, ret_msg = getQtInputDict(data_dict)
    if not input_dict:
        total_exit_value=1
        total_log.append("%s\n" % ret_msg)

    dirname = os.path.dirname(out_file)
    out_dir = os.path.join(dirname, "output-%s" % time.strftime("%Y-%m-%d-%H-%M-%S"))
    os.mkdir(out_dir)
    with open(out_file, "w") as fp:
        fp.write(out_dir.encode("utf-8"))

    if "phi_value" in input_dict:
        phi_list = input_dict.get("phi_value", )
        input_dict.pop("phi_value")
    else:
        phi_list = []
    umu_list = []
    distance_list = []
    output_process = []
    output_quantity = []

    for key, input_data in input_dict.items():
        tmp_file = os.path.abspath("%s.INP" % key)
        SaveCycle(tmp_file, input_data) # Save a temporary INP file with the latest modifications
        #self.Saved = tmp_save # Set it to the previous value, since self.Saved sets it to True

        tmp_out_file = os.path.join(out_dir, key)
        umu, distance, output_process_select, output_quantity_select = key.split('_')
        if output_process_select not in output_process:
            output_process.append(output_process_select)
        if output_quantity_select not in output_quantity:
            output_quantity.append(output_quantity_select)
        if umu not in umu_list:
            umu_list.append(umu)
        if distance not in distance_list:
            distance_list.append(distance)
        chl_thread = RunUvspecProcess(tmp_file, tmp_out_file)
        chl_thread.run()
        #chl_thread.join()

        if chl_thread.exit_value == "Error":
            total_exit_value=1
            total_log.append("".join(chl_thread.log))
            break
        else:
            os.remove(tmp_file)
            out_file_list.append(tmp_out_file)
            total_log.append("\n%s-run finished!" % key)
    double_phi_list = [float(phi) for phi in phi_list]
    double_umu_list = [float(umu) for umu in umu_list];
    double_distance_list = [float(distance) for distance in distance_list];
    double_phi_list.sort();
    double_umu_list.sort();
    double_distance_list.sort();

    phi_list = [str(phi) for phi in double_phi_list];
    umu_list = [str(umu) for umu in double_umu_list];
    phi_list = [str(distance) for distance in double_distance_list];

    key_list = [','.join(output_process), ','.join(output_quantity), ','.join(phi_list), ','.join(umu_list), ','.join(distance_list)]
    tmp_key_path = os.path.join(out_dir, "key_path")
    with open(tmp_key_path, 'w') as fp:
        fp.write('\n'.join(key_list))
    return True, "".join(total_log)

@getException
def OnRun(out_dict, out_file, log_path):

    fh = logging.FileHandler(log_path)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    data_list = getQtInput(out_dict)
    print "*" * 50
    run_mode_list = out_dict.pop("global_mode", "")
    run_mode = run_mode_list[0].split(" ")[1]
    #print "global_mode", run_mode, u"批处理模式"

    if run_mode == u"批处理模式":
        logger.info("multi")
        return OnRunNew(out_dict, out_file)
    else:
        logger.info("single")

        return OnRunSingle(data_list, out_file)


def single_process_input(help_input_dict, out_dict):
    get_ic_and_wc(help_input_dict, out_dict)

    get_wave_grid(help_input_dict, out_dict)

    get_phi(help_input_dict, out_dict)

    get_umu(help_input_dict, out_dict)

    get_zout(help_input_dict, out_dict)

    get_altitude(help_input_dict, out_dict)

    get_atmosphere_file(help_input_dict, out_dict)

    get_aerosol(help_input_dict, out_dict)

    get_source(help_input_dict, out_dict)

    get_others(help_input_dict, out_dict)

def get_source(help_input_dict, out_dict):
    source_type = help_input_dict.get("source_type", [])
    source_unit = help_input_dict.get("source_unit", [])
    source_file = help_input_dict.get("source_file", [])
    if source_type:
        s_type = source_type[0].split(" ")[1]
        if source_file and source_unit:
            s_unit = source_unit[0].split(" ")[1]
            s_file = source_file[0].split(" ")[1]
            out_dict["source"] = ["source %s %s %s " % (s_type, s_file, s_unit)]
        else:
            out_dict["source"] = ["source %s " % (s_type)]

def get_others(help_input_dict, out_dict):
    omit_list = ["angle_of_pitch", "atmosphere_define", "global_mode", "main_wave", "azimuth_angle", "direction", "distance", "pressure_file", "temperature_file", "general_location", "latitude_file", "gas_file", "wavecount", "wavelength", "ic_set", "wc_set", "source_type", "source_file", "source_unit"]
    for key, val in help_input_dict.items():
        if key not in out_dict and key not in omit_list:
            out_dict[key] = val

def get_ic_and_wc(help_input_dict, out_dict):
    ic_set = help_input_dict.get("ic_set", "")
    ic_file = help_input_dict.get("ic_file", "")
    wc_set = help_input_dict.get("wc_set", "")
    wc_file = help_input_dict.get("wc_file", "")
    if ic_set:
        ic_value = convert_cloud_to_file("ic_set", ic_set)
    elif ic_file:
        ic_value = ic_file
    else:
        ic_value = []
    if wc_set:
        wc_value = convert_cloud_to_file("wc_set", wc_set)
    elif wc_file:
        wc_value = wc_file
    else:
        wc_value = []
    out_dict["ic_file"] = ic_value
    out_dict["wc_file"] = wc_value

def get_wave_grid(help_input_dict, out_dict):
    wave_mode = help_input_dict.get("main_wave", [])
    wave_mode = wave_mode[0].split(" ")[1] if wave_mode else None
    wavelength = help_input_dict.get("wavelength", [])
    wavecount = help_input_dict.get("wavecount", [])

    if wave_mode == u"设置波长":
        value = change_um_to_nm("wavelength", wavelength)
        wave_grid_file = create_grid_file(value)
        out_dict["wavelength_grid_file"] = wave_grid_file
    elif wave_mode == u"设置波数":
        wave_grid_file = create_grid_file_by_count(wavecount)
        out_dict["wavelength_grid_file"] = wave_grid_file

def get_umu(help_input_dict, out_dict):
    value = help_input_dict.get("angle_of_pitch", "")
    direction_val = help_input_dict.get("direction", None)
    direction = direction_val[0].split(" ")[1] if direction_val is not None else u"观测天空方向"
    if value:
        umu_angle = float(value[0].split(' ')[1])
        if direction == u"观测天空方向":
            true_cos = -math.cos(umu_angle/180 * math.pi)
        else:
            true_cos = math.cos(umu_angle/180 * math.pi)
        out_dict["umu"] = ["umu %s" % true_cos]

def get_phi(help_input_dict, out_dict):
    value = help_input_dict.get("azimuth_angle", "")
    if value:
        out_dict["phi"] = ["phi %s" % value[0].split(' ')[1]]

def get_aerosol(help_input_dict, out_dict):
    haze_val = help_input_dict.get("aerosol_haze", [])
    if haze_val:
        out_dict["aerosol_haze"] = change_aerosol_haze(haze_val)

    season_val = help_input_dict.get("aerosol_season", [])
    if season_val:
        out_dict["aerosol_season"] = change_aerosol_season(season_val)

    vulcan_val = help_input_dict.get("aerosol_vulcan", [])
    if vulcan_val:
        out_dict["aerosol_vulcan"] = change_aerosol_vulcan(vulcan_val)

def get_zout(help_input_dict, out_dict):
    zout_val = help_input_dict.pop("zout_sea", None)

    if zout_val is not None:
        zout = zout_val[0].split(" ")[1]
        if float(zout) >= 120:
            zout_str = "zout toa"
        else:
            zout_str = zout_val[0]
        out_dict["zout"] = [zout_str]

def get_altitude(help_input_dict, out_dict):
    altitude_val = help_input_dict.get("distance", None)
    direction_val = help_input_dict.get("direction", None)
    direction = direction_val[0].split(" ")[1] if direction_val is not None else u"观测天空方向"
    if altitude_val is not None and direction != u"观测天空方向":
        altitude = altitude_val[0].split(" ")[1]
        out_dict["altitude"] = ["altitude %s" % altitude]

def get_atmosphere_file(help_input_dict, out_dict):
    atmos_list = ["gas_file", "pressure_file", "temperature_file", "latitude_file"]
    atmos_file_list = []
    for atmos in atmos_list:
        if atmos in help_input_dict:
            atmos_file_list.append(help_input_dict[atmos])

    atmosphere_define = help_input_dict.get("atmosphere_define", None)
    atmosphere_define = atmosphere_define[0].split(" ")[1] if atmosphere_define is not None else ""

    direction_val = help_input_dict.get("direction", None)
    direction = direction_val[0].split(" ")[1] if direction_val is not None else u"观测天空方向"

    altitude_val = help_input_dict.get("distance", None)
    altitude = altitude_val[0].split(" ")[1] if altitude_val is not None else None

    if atmos_file_list:
        atmos_file_path = get_atmos_file(atmos_file_list, atmosphere_define)
        atmos_file_path = "atmosphere_file %s" % atmos_file_path
        if direction == u"观测天空方向" and altitude is not None:
            atmos_file_path = create_new_file([atmos_file_path], altitude)
        out_dict["atmosphere_file"] = [atmos_file_path]

def getInput():
    data=[]
    help_input_dict = {}
    input_dict = {}
    for name, obj in Options.items():
        if obj.IsChanged() and  obj.IsSet():
            help_input_dict[name] = obj.GetWriteValue()

    single_process_input(help_input_dict, input_dict)
    for in_key, in_val in input_dict.items():
        data.extend(in_val)

    return data

def getQtInput(data_dict):
    data=[]
    help_input_dict = data_dict
    input_dict = {}

    single_process_input(help_input_dict, input_dict)
    for in_key, in_val in input_dict.items():
        data.extend(in_val)

    return data
# if__name__ == "__main__":
#     pass