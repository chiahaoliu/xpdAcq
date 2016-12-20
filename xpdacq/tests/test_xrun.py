import unittest
import os
import shutil
import time
import yaml
import uuid
import warnings

from xpdacq.glbl import glbl
from xpdacq.beamtime import *
from xpdacq.utils import import_sample_info
from xpdacq.beamtimeSetup import (_start_beamtime, _end_beamtime)
from xpdacq.xpdacq import (_validate_dark, CustomizedRunEngine,
                           _auto_load_calibration_file,
                           open_collection)
from xpdacq.simulation import pe1c, cs700, shctl1, SimulatedPE1C

import bluesky.examples as be

class xrunTest(unittest.TestCase):
    def setUp(self):
        self.base_dir = glbl.base
        self.home_dir = os.path.join(self.base_dir, 'xpdUser')
        self.config_dir = os.path.join(self.base_dir, 'xpdConfig')
        self.PI_name = 'Billinge '
        self.saf_num = 300000  # must be 30000 for proper load of config yaml => don't change
        self.wavelength = 0.1812
        self.experimenters = [('van der Banerjee', 'S0ham', 1),
                              ('Terban ', ' Max', 2)]
        # make xpdUser dir. That is required for simulation
        os.makedirs(self.home_dir, exist_ok=True)
        # set simulation objects
        glbl.area_det = SimulatedPE1C('pe1c', {'pe1_image': lambda: 5})
        print("AT SETUP: numbe_of_sets = {}, images_per_set = {}, "
              "acquire_time ={}"
              .format(glbl.area_det.number_of_sets.get(),
                      glbl.area_det.images_per_set.get(),
                      glbl.area_det.cam.acquire_time.get()))
        glbl.temp_controller = cs700
        glbl.shutter = shctl1
        self.bt = _start_beamtime(self.PI_name, self.saf_num,
                                  self.experimenters,
                                  wavelength=self.wavelength)
        xlf = '300000_sample.xlsx'
        src = os.path.join(os.path.dirname(__file__), xlf)
        shutil.copyfile(src, os.path.join(glbl.import_dir, xlf))
        import_sample_info(self.saf_num, self.bt)
        self.xrun = CustomizedRunEngine(None)
        open_collection('unittest')


    def tearDown(self):
        os.chdir(self.base_dir)
        if os.path.isdir(self.home_dir):
            shutil.rmtree(self.home_dir)
        if os.path.isdir(os.path.join(self.base_dir, 'xpdConfig')):
            shutil.rmtree(os.path.join(self.base_dir, 'xpdConfig'))
        if os.path.isdir(os.path.join(self.base_dir, 'pe2_data')):
            shutil.rmtree(os.path.join(self.base_dir, 'pe2_data'))

    def test_validate_dark(self):
        """ test login in this function """
        # no dark_dict_list
        glbl._dark_dict_list = []
        self.assertFalse(glbl._dark_dict_list)
        rv = _validate_dark()
        self.assertEqual(rv, None)
        # initiate dark_dict_list
        dark_dict_list = []
        now = time.time()
        acq_time = 0.1
        # case1: adjust exposure time
        for i in range(5):
            dark_dict_list.append({'uid': str(uuid.uuid4()),
                                   'exposure': (i + 1) * 0.1,
                                   'timestamp': now,
                                   'acq_time': acq_time})
        glbl._dark_dict_list = dark_dict_list
        rv = _validate_dark()
        self.assertEqual(rv, dark_dict_list[0].get('uid'))

        # case2: adjust expire time
        dark_dict_list = []
        for i in range(5):
            dark_dict_list.append({'uid': str(uuid.uuid4()),
                                   'exposure': 0.1,
                                   'timestamp': now - (i + 1) * 60,
                                   'acq_time': acq_time})
        glbl._dark_dict_list = dark_dict_list
        # large window -> still find the best (freshest) one
        rv = _validate_dark()
        self.assertEqual(rv, dark_dict_list[0].get('uid'))
        # small window -> find None
        rv = _validate_dark(0.1)
        self.assertEqual(rv, None)
        # medium window -> find the first one as it's within 1 min window
        rv = _validate_dark(1.5)
        self.assertEqual(rv, dark_dict_list[0].get('uid'))

        # case3: adjust acqtime
        dark_dict_list = []
        for i in range(5):
            dark_dict_list.append({'uid': str(uuid.uuid4()),
                                   'exposure': 0.1,
                                   'timestamp': now,
                                   'acq_time': acq_time * (i+1)})
        glbl._dark_dict_list = dark_dict_list
        # leave for future debug
        #print("dark_dict_list = {}"
        #      .format([(el.get('exposure'),
        #                el.get('timestamp'),
        #                el.get('uid'),
        #                el.get('acq_time'))for el in glbl._dark_dict_list]))
        rv = _validate_dark()
        self.assertEqual(rv, dark_dict_list[0].get('uid'))

        # case4: with real xrun
        if glbl._dark_dict_list:
            glbl._dark_dict_list = []
        self.assertFalse(glbl._dark_dict_list)
        self.xrun.beamtime = self.bt
        xrun_uid = self.xrun({}, 0)
        print(xrun_uid)
        self.assertEqual(len(xrun_uid), 2)  # first one is auto_dark
        dark_uid = _validate_dark()
        self.assertEqual(xrun_uid[0], dark_uid)
        # test sc_dark_field_uid
        msg_list = []
        def msg_rv(msg):
            msg_list.append(msg)
        self.xrun.msg_hook = msg_rv
        self.xrun(0, 0)
        open_run = [el.kwargs for el in msg_list
                    if el.command == 'open_run'][0]
        self.assertEqual(dark_uid, open_run['sc_dk_field_uid'])
        # no auto-dark
        glbl.auto_dark = False
        new_xrun_uid = self.xrun(0, 0)
        self.assertEqual(len(new_xrun_uid), 1)  # no dark frame
        self.assertEqual(glbl._dark_dict_list[-1]['uid'],
                         dark_uid)  # no update

    def test_auto_load_calibration(self):
        # no config file in xpdUser/config_base
        auto_calibration_md_dict = _auto_load_calibration_file()
        self.assertIsNone(auto_calibration_md_dict)
        # one config file in xpdUser/config_base:
        cfg_f_name = glbl.calib_config_name
        cfg_src = os.path.join(os.path.dirname(__file__), cfg_f_name)
        # __file__ gives relative path
        cfg_dst = os.path.join(glbl.config_base, cfg_f_name)
        shutil.copy(cfg_src, cfg_dst)
        with open(cfg_dst) as f:
            config_from_file = yaml.load(f)
        glbl.calib_config_dict = config_from_file
        auto_calibration_md_dict = _auto_load_calibration_file()
        # is file loaded??
        self.assertTrue('time' in auto_calibration_md_dict)
        # is information loaded in correctly?
        self.assertEqual(auto_calibration_md_dict['pixel2'],
                         0.0002)
        self.assertEqual(auto_calibration_md_dict['file_name'],
                         'pyFAI_calib_Ni_20160813-1659.poni')
        self.assertEqual(auto_calibration_md_dict['time'],
                        '20160813-1815')
        # file-based config_dict is different from glbl.calib_config_dict
        self.assertTrue(os.path.isfile(cfg_dst))
        glbl.calib_config_dict = dict(auto_calibration_md_dict)
        glbl.calib_config_dict['new_filed']='i am new'
        reload_auto_calibration_md_dict = _auto_load_calibration_file()
        # trust file-based solution
        self.assertEqual(reload_auto_calibration_md_dict, config_from_file)
        self.assertFalse('new_field' in reload_auto_calibration_md_dict)
        # test with xrun : auto_load_calib = False -> nothing happpen
        msg_list = []
        def msg_rv(msg):
            msg_list.append(msg)
        self.xrun.msg_hook = msg_rv
        self.xrun.beamtime = self.bt
        glbl.auto_load_calib = False
        xrun_uid = self.xrun(0,0)
        open_run = [el.kwargs for el in msg_list
                    if el.command =='open_run'][0]
        self.assertFalse('calibration_md' in open_run)
        # test with xrun : auto_load_calib = True -> full calib_md
        msg_list = []
        def msg_rv(msg):
            msg_list.append(msg)
        self.xrun.msg_hook = msg_rv
        glbl.auto_load_calib = True
        xrun_uid = self.xrun(0,0)
        open_run = [el.kwargs for el in msg_list
                    if el.command == 'open_run'][0]
        # modify in place
        reload_auto_calibration_md_dict.pop('calibration_collection_uid')
        # test assertion
        self.assertTrue('calibration_md' in open_run)
        self.assertEqual(open_run['calibration_md'],
                         reload_auto_calibration_md_dict)
        # specific info encoded in test file
        self.assertEqual(open_run['calibration_collection_uid'],
                         'uuid1234')

    def test_xrun_with_xpdAcqPlans(self):
        exp = 5
        # test with ct
        msg_list = []
        def msg_rv(msg):
            msg_list.append(msg)
        self.xrun.msg_hook = msg_rv
        self.xrun.beamtime = self.bt
        self.xrun({}, ScanPlan(self.bt, ct, exp))
        open_run = [el.kwargs for el in msg_list
                    if el.command == 'open_run'].pop()
        self.assertEqual(open_run['sp_type'], 'ct')
        self.assertEqual(open_run['sp_requested_exposure'], exp)
        # test with Tramp
        Tstart, Tstop, Tstep = 300, 200, 10
        msg_list = []
        def msg_rv(msg):
            msg_list.append(msg)
        self.xrun.msg_hook = msg_rv
        self.xrun({}, ScanPlan(self.bt, Tramp, exp, Tstart,
                               Tstop, Tstep))
        open_run = [el.kwargs for el in msg_list
                    if el.command == 'open_run'].pop()
        self.assertEqual(open_run['sp_type'], 'Tramp')
        self.assertEqual(open_run['sp_requested_exposure'], exp)
        self.assertEqual(open_run['sp_startingT'], Tstart)
        self.assertEqual(open_run['sp_endingT'], Tstop)
        self.assertEqual(open_run['sp_requested_Tstep'], Tstep)
        # test with tseries
        delay, num = 1, 5
        msg_list = []
        def msg_rv(msg):
            msg_list.append(msg)
        self.xrun.msg_hook = msg_rv
        self.xrun({}, ScanPlan(self.bt, tseries, exp, delay, num))
        open_run = [el.kwargs for el in msg_list\
                    if el.command == 'open_run'].pop()
        self.assertEqual(open_run['sp_type'], 'tseries')
        self.assertEqual(open_run['sp_requested_exposure'], exp)
        self.assertEqual(open_run['sp_requested_delay'], delay)
        self.assertEqual(open_run['sp_requested_num'], num)
        # test with Tlist
        T_list = [300, 256, 128]
        msg_list = []
        def msg_rv(msg):
            msg_list.append(msg)
        self.xrun.msg_hook = msg_rv
        self.xrun({}, ScanPlan(self.bt, Tlist, exp, T_list))
        open_run = [el.kwargs for el in msg_list
                    if el.command == 'open_run'].pop()
        self.assertEqual(open_run['sp_type'], 'Tlist')
        self.assertEqual(open_run['sp_requested_exposure'], exp)
        self.assertEqual(open_run['sp_T_list'], T_list)

    def test_xrun_warning(self):
        # no beamtime linked -> RuntimeError
        self.assertRaises(RuntimeError, lambda : self.xrun.beamtime)
        self.xrun.beamtime = self.bt
        glbl.soft_wait = 0.1
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # trigger warning
            self.xrun.beamtime.wavelength = None
            self.xrun(0,0)
            print("wavelength = {}"
                  .format(self.xrun.beamtime.wavelength))
            # check warning
            assert len(w)==1
            assert issubclass(w[-1].category, UserWarning)

    # deprecate from v0.5 release
    #def test_open_collection(self):
    #    # no collection
    #    delattr(glbl, 'collection')
    #    self.assertRaises(RuntimeError, lambda: self.xrun(0, 0))
    #    # test collection num
    #    open_collection('unittest_collection')
    #    self.assertEqual(glbl.collection, [])
    #    self.xrun(0, 0)
    #    self.assertEqual(glbl.collection_num, 1)
