#!/usr/bin/env python3

from builder.scheduler_variables import scheduler, cap


_file_path = os.path.dirname(os.path.abspath(__file__))+'/'
_cwd = os.path.abspath(os.getcwd())

    
class plot_scripts(cap):
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
        self.plot_submit = 'plot.sh'
        self.plot_builder_path = _file_path+'/'
        self.plot_template_path = (self.plot_builder_path
                                   +'template_athena_ae.sh')
        return


    def make_plot_submit(self, job_name='plot', output=None,
                           directory=''):
        # ERROR check
        if directory != '' and directory[-1] != '/':
            directory += '/'
        return