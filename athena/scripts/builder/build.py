#!/usr/bin/env python3

import os
import shutil
import pathlib

from builder.scheduler_variables import scheduler, cap
from builder.merge_vtk.merge_builder import merge_scripts
from builder.plot.plot_builder import plot_scripts
from builder.merge_vtk.ray_trace_builder import ray_trace_scripts
from builder.athena_ae.athena_builder import athena_scripts


_file_path = os.path.dirname(os.path.abspath(__file__))+'/'
_cwd = os.path.abspath(os.getcwd())

class scheduler_scripts(merge_scripts, plot_scripts, ray_trace_scripts,
                        athena_scripts):
    def __init__(self, scheduler_name, directives, *args, **kwargs):
        # interchangeable inherit structure
        kwargs['scheduler_name'] = scheduler_name
        kwargs['directives'] = directives
        super(scheduler_scripts, self).__init__(*args, **kwargs)
        # setup scheduler and directives
        scheduler_name = scheduler_name.lower()
        self.directives = directives
        self.scheduler = scheduler(scheduler_name)
        # builder filenames and paths
        self.build_path = _cwd
        self.vtk_merge_path = None
        self.plot_path = None
        self.ray_trace_path = None
        self.athena_ae_path = None
        return


    def build_all(self, athena_up=True):
        self.build_vtk_merge()
        self.build_plot()
        self.build_ray_trace()
        # Do athena last, so that submit script correctly copies other scripts
        self.build_athena()
        if athena_up:
            shutil.copy(self.athena_ae_path+self.athena_submit,
                        '../'+self.athena_submit)
        return


    def build_vtk_merge(self, directory="vtk_merge/", node_share=False,
                        nodes=None, ppn=None, job_name='vtk_merge',
                        walltime='00:20:00', output=None):
        # ERROR check
        if directory[-1] != '/':
            directory += '/'
        self.vtk_merge_path = directory
        # make directory
        pathlib.Path(self.vtk_merge_path).mkdir(parents=True, exist_ok=True)
        # make merge prep and submit template
        self.make_merge_prep(node_share=node_share, nodes=nodes, ppn=ppn,
                             job_name=job_name, walltime=walltime,
                             output=output, directory=self.vtk_merge_path)
        # copy merge script into directory
        shutil.copy(self.merge_builder+self.merge_script,
                    self.vtk_merge_path+self.merge_script)
        return


    def build_athena(self, job_name='athena_ae', output='%x-%j.out',
                     directory="athena_ae/", biuld_path=_cwd):
        # ERROR check
        if directory[-1] != '/':
            directory += '/'
        self.athena_ae_path = directory
        # make directory
        pathlib.Path(self.athena_ae_path).mkdir(parents=True, exist_ok=True)
        # make athena submit script
        self.make_athena_submit(job_name=job_name, output=output,
                                vtk_merge_path=self.vtk_merge_path,
                                plot_path=self.plot_path,
                                ray_trace_path=self.ray_trace_path,
                                directory=self.athena_ae_path,
                                biuld_path=biuld_path)
        return


    def build_plot(self):
        return


    def build_ray_trace(self):
        return