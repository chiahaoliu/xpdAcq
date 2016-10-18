import unittest
import os
import shutil
import time
import yaml
import uuid
from unittest.mock import MagicMock
from configparser import ConfigParser
from time import strftime

from xpdacq.glbl import glbl
from xpdacq.beamtime import *
from xpdacq.utils import import_sample_info
from xpdacq.beamtimeSetup import (_start_beamtime, _end_beamtime)
from xpdacq.xpdacq import (_validate_dark, CustomizedRunEngine,
                           _auto_load_calibration_file,
                           open_collection)
from xpdacq.simulation import SimulatedPE1C, build_pymongo_backed_broker
import bluesky.examples as be

from xpdacq.calib import run_calibration

class PrunTest(unittest.TestCase):
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
        self.bt = _start_beamtime(self.PI_name, self.saf_num,
                                  self.experimenters,
                                  wavelength=self.wavelength)
        xlf = '300000_sample.xlsx'
        src = os.path.join(os.path.dirname(__file__), xlf)
        shutil.copyfile(src, os.path.join(glbl.import_dir, xlf))
        glbl.shutter_control = True
        self.xrun = CustomizedRunEngine(self.bt)
        open_collection('unittest')
        # simulation objects
        glbl.area_det = SimulatedPE1C('pe1c', {'pe1_image': lambda: 5})
        glbl.temp_controller = be.motor
        glbl.shutter = be.Mover('motor', {'motor': lambda x: x}, {'x': 0})
        # FIXME: replace with pytest fixture with fullness of time
        glbl.db = build_pymongo_backed_broker()
        glbl.get_events = glbl.db.get_events
        glbl.get_images = glbl.db.get_images
        glbl.verify_files_saved = MagicMock()


    def tearDown(self):
        os.chdir(self.base_dir)
        if os.path.isdir(self.home_dir):
            shutil.rmtree(self.home_dir)
        if os.path.isdir(os.path.join(self.base_dir, 'xpdConfig')):
            shutil.rmtree(os.path.join(self.base_dir, 'xpdConfig'))
        if os.path.isdir(os.path.join(self.base_dir, 'pe1_data')):
            shutil.rmtree(os.path.join(self.base_dir, 'pe1_data'))

    def test_run_calibration_smoke(self):
        # test if it can be run with default argument
        run_calibration()
