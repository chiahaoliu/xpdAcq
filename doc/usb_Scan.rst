.. _usb_scan:

ScanPlan objects
----------------

ScanPlan objects (of type ``'sp'`` ) are created just like :ref:`Experiment and Sample <usb_experiment>` objects,
but they serve a slightly different purpose and so we deal with them separately here. To review the syntax
of creating (*instantiating* ) and retrieving (``bt.get()`` ) acquire objects in general, please review
the information :ref:`here <usb_experiment>` and :ref:`here <usb_where>` , respectively.

Firstly, what is a scanplan?  A scanplan is a grouped set of detector exposures.  The set may
contain just one exposure (we call that a count scan, ``'ct'`` ).  Or it may be a series of exposures
taken one after the other, possibly with a delay between.  We
call that a time-series (or ``'tseries'`` ).  Another popular one that is supported is the
a temperature series, or temperature ramp, ``'Tramp'``.  More are also on the way, but
these simple scanplans may also be combined together in scripts, giving the user significant
control over how to construct their experiment.

To run a scan we need a *ScanPlan* and a *Sample*.  The ScanPlan is the detailed description of
what the scan will do, but it doesn't generate any *scan* until it is run on a particular sample.
Separating a scan into a plan and an execution (which is different than how SPEC works
for those old enough) makes it very easy to run a number of different samples with the
exact same scanplan, or (if you really want to) to collect dark images with exactly the same scan pattern, and so on.
We also want to save scan metadata accurately when the scan is actually run.  To ensure
this, each scan object takes the scanplan parameters and it uses the same parameters
both to run the scan at run-time, and to save them, along with the sample information,
in the metadata for each exposure.

With this in mind, the workflow is that *we never edit a scanplan and rerun it* (stop that you SPEC people!).
What we do is that we create a new ScanPlan object, **and give it a different name**,
every time we want to do a different, *even slightly different*, scan. These are all
saved for reload and will be sent home with you at the end of the experiment.  A word of advice:
come up with your own easy to remember naming scheme. For example, when you create
a ``'ct'`` scan object use the scheme ``'ct<#>'`` where you replace ``<#>`` with the length
of the count in seconds, so a 1.5 second exposure would be named ``'ct1.5'``.  You might
call temperature ramps as ``T``.  These take start temperature, stop temperature and step size,
so a good naming scheme would be ``'T<startT>.<stopT>.<Tstep>'``, e.g., ``'T300.500.10'``.

Setting up ScanPlans
""""""""""""""""""""

Typing ``s = ScanPlan?`` returns

.. autofunction:: xpdacq.beamtime.ScanPlan


Here are some examples of valid count-type ScanPlan definitions:

.. code-block:: python

  >>> sc = ScanPlan(bt, ct, 5)                      # the simplest count scan definition

A few things to note:
  # First argument is always ``bt``, beamtime object.
  * Because ``count`` type ``ScanPlans``, the second argument is always ``'ct'``.
  * The scan parameter is fed in after scan type, starting from the third positional argument.

Types of ScanPlan available in current version:
  * ``'ct'`` just exposes the the detector for a number of seconds. e.g.,  ``ScanPlan(bt, ct, 17.5)``
  * ``'tseries'`` executes a series of ``'num'`` counts of exposure time ``'exposure'`` seconds with  a delay of ``'delay'`` seconds between them.  e.g., ``ScanPlan(bt, tseries, 1, 59, 50)`` will measure 50 scans of 1 second with a delay of 59 seconds in between each of them.
  * ``'Tramp'`` executes a temperature ramp from ``'startingT'`` to ``'endingT'`` in temperature steps of ``'Tstep'`` with exposure time of ``'exposure'``.  e.g., ``ScanPlan(bt, Tramp, 1, 200, 500, 5)`` will automatically change the temperature,
    starting at 200 K and ending at 500 K, measuring a scan of 1 s at every 5 K step. The temperature controller will hold at each temperature until the temperature stabilizes before starting the measurement.

Summary table on ScanPlan
"""""""""""""""""""""""""""

  =========== ==================================================================================================
  ScanPlan    Syntax
  =========== ==================================================================================================
  ``ct``      ``ScanPlan(bt, ct, 17.5)``
  ``tseries`` ``ScanPlan(bt, tseries, 1, 59, 50)``
  ``Tramp``   ``ScanPlan(bt, Tramp , 1, 200, 500, 5)``
  =========== ==================================================================================================

.. _customize_scan:

Write your own ScanPlan
""""""""""""""""""""""""

``xpdAcq`` also consumes any scan plan from ``bluesky``. The ability to write your own bluesky plans gives enormous flexibility
but has a steep learning curve, but you should be able to get help setting these up from your local contact. For more details about how to write a ``bluesky`` scan plan,
please see `full document <http://nsls-ii.github.io/bluesky/plans.html>`_.

Here we will show a brief example for illustration. The specific illustration is a scan that drives a motor called ``motor`` through a specific list of points while collecting
an image at each point from the detector ``area_detector``.  It uses a predefined ``bluesky``
plan for this purpose, ``list_scan``.  To use this in ``xpdAcq`` you would first define your ``bluesky`` plan
and assign it to the object we have called ``mybsplan`` in this example:

.. code-block:: python

  from bluesky.plans import list_scan

  # it is entirely optional to add metadata to the scan, but here is what you would do:
  mymd = {'memoy_aid': 'This metadata should be about the scan, not the sample which would be added when the scanplan is run',
          'author': 'Simon',
          'etc': 'make up any key-value pairs'}

  mybsplan = list_scan([glbl.area_det], motor, [1,3,5,7,9], md=mymd) # drives motor to positions 1,3,5,7,9 and fires ``area detector`` at each position
  mybsplan = subs_wrapper(mybsplan, LiveTable([glbl.area_det])) # set up the scan so LiveTable will give updates on how the scan is progressing

Then to use it successfully in xpdAcq you have to do a bit of configuration of global parameters.  This work is done
automatically for you in the ``xpdAcq`` built-in plans.  There are many things you could set up, but the simplest example
is that we want the detector to collect 50 frames each time we fire it, which would give a 50s exposure at a frame-rate of 0.1s (frame-rate
is another ``glbl`` option that you could reset).

.. code-block:: python

  glbl.area_det.images_per_set.put(50)  # set detector to collect 50 frames, so 5 s exposure if continuous acquisition with 0.1s frame-rate

Finally, later on in the experiment when you are ready to run it, you would run this plan just the same as a regular ``ScanPlan`` object!


OK, it is time to :ref:`run our scans <usb_running>`
