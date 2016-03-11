#!/usr/bin/env python
##############################################################################
#
# xpdacq            by Billinge Group
#                   Simon J. L. Billinge sb2896@columbia.edu
#                   (c) 2016 trustees of Columbia University in the City of
#                        New York.
#                   All rights reserved
#
# File coded by:    Timothy Liu, Simon Billinge
#
# See AUTHORS.txt for a list of people who contributed.
# See LICENSE.txt for license information.
#
##############################################################################
#from dataportal import DataBroker as db
#from dataportal import get_events, get_table, get_images
#from metadatastore.commands import find_run_starts

import os
import datetime
from time import strftime
import numpy as np
import tifffile as tif
import matplotlib as plt
from xpdacq.glbl import glbl
#from xpdacq.glbl import _dataBroker as db
#from xpdacq.glbl import _getEvents as get_events
#from xpdacq.glbl import _getImages as get_images

# top definition for minial impacts on the code. Can be changed later
db = glbl.db
get_events = glbl.get_events
get_images = glbl.get_images

_fname_field = ['sa_name','sc_name'] 
w_dir = os.path.join(glbl.home, 'tiff_base')
W_DIR = w_dir # in case of crashes in old codes

def bt_uid():
    return bt.get(0).md['bt_uid']

def _feature_gen(header):
    ''' generate a human readable file name. 

    file name is generated by metadata information in header 
    '''
    uid = header.start.uid[:6]
    feature_list = []
    
    
    field = header['start']
    for key in _fname_field:

        # get special label
        try:
            if header.start['xp_isdark']:
                feature_list.append('dark')
        except KeyError:
            pass

        try:
            el = field[key]
            # truncate string length
            if len(el)>12:
                value = el[:12]
            else:
                value = el
            # clear space
            feature = [ ch for ch in list(el) if ch!=' ']
            feature_list.append(''.join(feature))
        except KeyError:
            pass # protection to allow missing required fields. This should not happen
    # FIXME - find a way to include motor information
    f_name = "_".join(feature_list)
    exp_time = _timestampstr(header.start.time, hour=True)
    return '_'.join([f_name, exp_time])

def _timestampstr(timestamp, hour=False):
    ''' convert timestamp to strftime formate '''
    if not hour:
        timestring = datetime.datetime.fromtimestamp(float(timestamp)).strftime('%Y%m%d')
    elif hour:
        timestring = datetime.datetime.fromtimestamp(float(timestamp)).strftime('%Y%m%d-%H%M')
    return timestring

def save_last_tiff(dark_subtraction=True):
    save_tiff(db[-1], dark_subtraction)

def save_tiff(headers, dark_subtraction = True):
    ''' save images obtained from dataBroker as tiff format files. It returns nothing.

    arguments:
        headers - list - a list of header objects obtained from a query to dataBroker
    '''
    F_EXTEN = '.tiff'
    e = '''Can not find a proper dark image applied to this header.
        Files will be saved but not no dark subtraction will be applied'''
    is_dark_subtracted = False # assume not has been done
    
    # prepare header
    if type(list(headers)[1]) == str:
        header_list = list()
        header_list.append(headers)
    else:
        header_list = headers

    for header in header_list:
        print('Saving your image(s) now....')
        img_field = _identify_image_field(header)
        for ev in header:
            img = ev['data'][img_field]
            ind = ev['seq_num']
            # dark subtration logic 
            if dark_subtraction:
                dark_uid_appended = header.start['sc_params']['dk_field_uid']
                try:
                    # bluesky only looks for uid it defines
                    dark_search = {'group':'XPD','xp_dark_uid':dark_uid_appended} # this should be refine later
                    dark_header = db(**dark_search)
                    dark_img = np.array(get_images(dark_header, img_field)).squeeze()
                except ValueError: 
                    print(e) # protection. Should not happen
                    dark_img = np.zeros_like(light_imgs)
                img -= dark_img
                is_dark_subtracted = True # label it only if it is successfully done
            f_name = _feature_gen(header)
            if is_dark_subtracted:
                f_name = 'sub_' + f_name # give it a label
            if 'temperature' in ev['data']:
                f_name = f_name + '_'+str(ev['data']['temperature'])+'K'
            combind_f_name = '{}_{}{}'.join(f_name,ind, F_EXTEN) # add index value
            w_name = os.path.join(W_DIR, combind_f_name)
            tif.imsave(w_name, img) 
            if os.path.isfile(w_name):
                print('image "%s" has been saved at "%s"' % (combind_f_name, W_DIR))
            else:
                print('Sorry, something went wrong with your tif saving')
                return
            if max_count is not None and ind<= max_count:
                break
    print('||********Saving process SUCCEEDED********||')

def plot_images(header):
    ''' function to plot images from header.
    
    It plots images, return nothing
    Parameters
    ----------
        header : databroker header object
            header pulled out from central file system
    '''
    # prepare header
    if type(list(headers)[1]) == str:
        header_list = list()
        header_list.append(headers)
    else:
        header_list = headers
    
    for header in header_list:
        uid = header.start.uid 
        img_field = _identify_image_field(header)
        imgs = np.array(get_images(header, img_field))
        print('Plotting your data now...')
        for i in range(imgs.shape[0]):
            img = imgs[i]
            plot_title = '_'.join(uid, str(i))
            # just display user uid and index of this image
            try:
                fig = plt.figure(plot_title)
                plt.imshow(img)
                plt.show()
            except:
                pass # allow matplotlib to crash without stopping other function

def plot_last_scan():
    ''' function to plot images from last header
    '''
    plot_images(db[-1])


def _identify_image_field(header):
    ''' small function to identify image filed key words in header
    '''
    try:
        img_field =[el for el in header.descriptors[0]['data_keys'] if el.endswith('_image')][0]
        print('Images are pulling out from %s' % img_field)
        return img_field
    except IndexError:
        uid = header.start.uid
        print('This header with uid = %s does not contain any image' % uid)
        print('Was area detector correctly mounted then?')
        print('Stop here')
        return

