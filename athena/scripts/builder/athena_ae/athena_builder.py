#!/usr/bin/env python3

import os
import shutil
import tempfile

from builder.scheduler_variables import scheduler, cap


_file_path = os.path.dirname(os.path.abspath(__file__))+'/'
_cwd = os.path.abspath(os.getcwd())

    
class athena_scripts(cap):
    def __init__(self, scheduler_name, directives, *args, **kwargs):
        # # interchangeable inherit structure
        kwargs['scheduler_name'] = scheduler_name
        kwargs['directives'] = directives
        super(athena_scripts, self).__init__(*args, **kwargs)
        # setup scheduler and directives
        scheduler_name = scheduler_name.lower()
        self.directives = directives
        self.scheduler = scheduler(scheduler_name)
        # Drop directives we will set internally
        self.drop_directives = [self.scheduler.job_name,
                                self.scheduler.standard_output]
        for k in self.directives.keys():
            if k in self.drop_directives:
                del self.directives[k]
        self.n_directives = len(self.directives)
        # athena_ae script filenames and paths
        self.athena_submit = 'athena_ae.sh'
        self.athena_builder_path = _file_path+'/'
        self.athena_template_path = (self.athena_builder_path
                                     +'template_athena_ae.sh')
        return


    def make_athena_submit(self, job_name='athena_ae', output=None,
                           vtk_merge_path=None, plot_path=None,
                           ray_trace_path=None, directory='',
                           biuld_path=_cwd):
        # ERROR check
        if directory != '' and directory[-1] != '/':
            directory += '/'
        if vtk_merge_path is not None and vtk_merge_path[-1] != '/':
            vtk_merge_path += '/'
        if plot_path is not None and plot_path[-1] != '/':
            plot_path += '/'
        if ray_trace_path is not None and ray_trace_path[-1] != '/':
            ray_trace_path += '/'
        if biuld_path is not None and biuld_path[-1] != '/':
            biuld_path += '/'
        # Write a temporary file from template
        temp_file, temp_path = tempfile.mkstemp()
        with os.fdopen(temp_file, 'w') as file_:
            with open(self.athena_template_path) as template_:
                for line in template_:
                    # write fixed directive lines
                    if line == '# replace this line with directive_lines\n':
                        for key, val in self.directives.items():
                            file_.write(
                                f'{self.scheduler.directive} {key}{val}\n')
                        # Add default directives if not already given at initalization
                        if (self.scheduler.job_name
                            not in self.directives.keys()):
                            file_.write(
                                f'{self.scheduler.directive} '
                                f'{self.scheduler.job_name}{job_name}\n')
                        if (self.scheduler.standard_output
                            not in self.directives.keys()):
                            file_.write(
                                f'{self.scheduler.directive} '
                                f'{self.scheduler.standard_output}{output}\n')
                    # write variable directive lines
                    elif line == '# Scheduler directives that vary run to run\n':
                        file_.write(
                            '# Scheduler directives that vary run to run\n')
                        file_.write(
                            f'{self.scheduler.directive} '
                            f'{self.scheduler.wallclock_limit}    '
                            f'                      # Time limit hrs:min:sec\n')
                        file_.write(
                            f'{self.scheduler.directive} '
                            f'{self.scheduler.task_count}     '
                            f'                    # Number of MPI ranks\n')
                    # write ncores
                    elif line == '# repalce this line with ncores_line\n':
                        file_.write(
                            f'ncores="{self.scheduler.NPROCS}"'
                            f'                   # number of cores\n')
                    # write script lines
                    elif ((vtk_merge_path is not None
                         or plot_path is not None
                         or ray_trace_path is not None)
                        and line == '# replace this line with script_lines\n'):
                        script_lines = [
                            f'# Copy over post processing scripts',
                            f'script_build_path="{biuld_path}"',
                            f'if test -d "$script_path";then']
                        if vtk_merge_path is not None:
                            script_lines += [
                                f'  cp "${{script_build_path}}"'
                                f'{vtk_merge_path}* "$raw_path"'
                            ]
                        if plot_path is not None:
                            script_lines += [
                                f'  cp "${{script_build_path}}"'
                                f'{plot_path}* "$anly_path"'
                            ]
                        if ray_trace_path is not None:
                            script_lines += [
                                f'  cp "${{script_build_path}}"'
                                f'{ray_trace_path}* "$anly_path"'
                            ]
                        script_lines += [
                            f'fi'
                        ]
                        for sline in script_lines:
                            file_.write(sline+'\n')
                    # copy template lines
                    else:
                        file_.write(line)
        # Copy the file permissions of template
        shutil.copymode(self.athena_template_path, temp_path)
        # Rename temporary file
        shutil.move(temp_path, directory+self.athena_submit)

        return