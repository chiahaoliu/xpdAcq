"""thin wrapper for analysis pipeline"""
##############################################################################
#
# xpdacq            by Billinge Group
#                   Simon J. L. Billinge sb2896@columbia.edu
#                   (c) 2016 trustees of Columbia University in the City of
#                        New York.
#                   All rights reserved
#
# File coded by:    Christopher J. Wright, Timothy Liu
#
# See AUTHORS.txt for a list of people who contributed.
# See LICENSE.txt for license information.
#
##############################################################################
from multiprocessing import Queue, Process
from xpdan.pipelines import analysis_pipeline
# universal function to kickoff pipeline
def process_data(Q, pipeline, **kwargs):
    while True:
        # make the generator
        pipeline_gen = pipeline(Q, **kwargs)
        while True:
            # pull the documents
            name, doc = next(pipeline_gen)
            if name == 'stop':
                # Take it from the top!
                break

# centralized pipeline
Q = Queue()
GQ = iter(Q.get, None)
p = Process(target=process_data, args=(GQ, analysis_pipeline))
