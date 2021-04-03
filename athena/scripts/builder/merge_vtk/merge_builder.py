#!/usr/bin/env python3

import os
import shutil
import pathlib

from builder.scheduler_variables import scheduler, cap

_file_path = os.path.dirname(os.path.abspath(__file__))+'/'


class merge_scripts(cap):
    replace_line = '#replace this line\n'
    seperate_line = '#-------------------------\n'
    
    def __init__(self, scheduler_name, directives, *args, **kwargs):
        # interchangeable inherit structure
        kwargs['scheduler_name'] = scheduler_name
        kwargs['directives'] = directives
        super(merge_scripts, self).__init__(*args, **kwargs)
        # setup scheduler and directives
        scheduler_name = scheduler_name.lower()
        self.directives = directives
        self.scheduler = scheduler(scheduler_name)
        # Drop directives we will set internally
        self.drop_directives = [self.scheduler.job_name,
                                self.scheduler.wallclock_limit,
                                self.scheduler.standard_output]
        for k in self.directives.keys():
            if k in self.drop_directives:
                del self.directives[k]
        self.n_directives = len(self.directives)
        # merge_vtk script filenames and paths
        self.merge_submit_template = 'merge_submit_template.sh'
        self.merge_submit = 'merge_submit.sh'
        self.merge_script = 'merge_script.sh'
        self.merge_prep = 'merge_prep.sh'
        self.merge_builder = _file_path+'/'
        self.merge_prep_template = self.merge_builder+'template_merge.sh'
        return

    
    def make_merge_submit_template(self, node_share=False, nodes=None, ppn=None,
                                   job_name='vtk_merge', walltime='00:20:00',
                                   output=None, directory=''):
        """
        Keyword arguments:
            node_share: if cluster has node sharing enabled (boolean)
        """
        # ERROR check
        if directory != '' and directory[-1] != '/':
            directory += '/'
        if not node_share:
            if nodes is None or ppn is None:
                print("ERROR: If not node sharing, you must provide n nodes"
                      " and ppn.")
                return 1
        if output is None:
            if node_share:
                output = 'merge_%A-%a.out'
            else:
                output = 'merge_%j.out'
        # Write template
        with open(directory+self.merge_submit_template, 'w') as file_:
            file_.write('#!/bin/bash\n')
            # Add user defined directives
            for key, val in self.directives.items():
                file_.write(f'{self.scheduler.directive} {key}{val}\n')
            # Add default directives if not already given at initalization
            if (self.scheduler.job_name not in self.directives.keys()):
                file_.write(f'{self.scheduler.directive} '
                            f'{self.scheduler.job_name}{job_name}\n')
            if (self.scheduler.wallclock_limit not in self.directives.keys()):
                file_.write(f'{self.scheduler.directive} '
                            f'{self.scheduler.wallclock_limit}{walltime}\n')
            if (self.scheduler.standard_output not in self.directives.keys()):
                file_.write(f'{self.scheduler.directive} '
                            f'{self.scheduler.standard_output}{output}\n')
            # Add one directive line for job array, nodes for fixed resources
            if node_share:
                file_.write(self.replace_line)
            else:
                file_.write(f'{self.scheduler.directive} '
                            f'{self.scheduler.node_count}{nodes}\n')
            file_.write(self.seperate_line)
            # Write body of template
            file_.write(f'cd {self.scheduler.SUBMIT_DIR}\n\n')
            if node_share:
                file_.write(self.replace_line[:-1])
                return
            # Body of fixed resource template
            file_.write(self.replace_line)
            file_.write(self.replace_line)
            file_.write(self.replace_line)
            file_.write(self.replace_line+'\n')
            job_function = [
                f'jobs() {"{"}',
                f'  levels=$1',
                f'  dumps=$2',
                f'  core0=$3',
                f'  core1=$4',
                f'  for (( i=0; i<"${{#levels[@]}}"; i++ ));do',
                f'    lev="${{levels[$i]}}"',
                f'    for (( j=0; j<"${{#dumps[@]}}"; j++ ));do',
                f'      dump="${{dumps[$j]}}"',
                f'      printf "%s %s %s %s\\n" "$dump" "${{core0[$lev]}}" '
                f'"${{core1[$lev]}}" "$lev"',
                f'    done',
                f'  done',
                f'{"}"}'
            ]
            for line in job_function:
                file_.write(line+'\n')
            file_.write('\n'+f'jobs "$levels" "$dumps" "$core0" "$core1" | \\'
                        '\n'+f'xargs -P "{self.scheduler.CPUS_PER_NODE}"'
                        f' -n 4 ./{self.merge_script}')
        return


    def make_merge_prep(self, node_share=True, nodes=None, ppn=None,
                        job_name='vtk_merge', walltime='00:20:00',
                        output='array_%A-%a.out', directory=''):
        # ERROR check
        if directory != '' and directory[-1] != '/':
            directory += '/'
        # make merge_submit_template consistent with merge_prep
        if self.make_merge_submit_template(node_share=node_share, nodes=nodes,
                                           ppn=ppn, job_name=job_name,
                                           walltime=walltime, output=output,
                                           directory=directory):
            return
        # make merge_prep
        shutil.copy(self.merge_prep_template, directory+self.merge_prep)
        with open(directory+self.merge_prep, 'a') as file_:
            file_A = ".".join(self.merge_submit.split(".")[:-1])+"-A.sh"
            file_B = ".".join(self.merge_submit.split(".")[:-1])+"-B.sh"
            file_.write(f'\nfile_temp="{self.merge_submit_template}"\n'
                        f'file_A="{file_A}"\n'
                        f'file_B="{file_B}"\n')
            if node_share:
                lines = [
                    f'for ((j=0; j<"${{#ilist[@]}}"; j++));do',
                    f'  for i in $(seq 0 1 "$nlev");do',
                    f'    lev="${{order[$i]}}"',
                    f'    sed "{4+self.n_directives}s/.*/'
                    f'{self.scheduler.directive} '
                    f'{self.scheduler.job_array}'
                    f'"${{ilist[$j]}}"-"${{elist[$j]}}"\ '
                    f'"$file_temp" > "$file_A"',
                    f'    sed "{9+self.n_directives}s/.*/.\/{self.merge_script}'
                    f'\$((\\{self.scheduler.JOB_ARRAY_ID}-1)) '
                    f'"${{core[$lev]}}" "${{ecore[$lev]}}" "$lev"/" '
                    f'"$file_A" > "$file_B"',
                    f'    {self.scheduler.job_submission} < "$file_B"',
                    f'  done',
                    f'done'
                ]
            else:
                lines = [
                    f'sed "{9+self.n_directives}s/.*/'
                    f'levels=(${{order[*]}})/" "$file_temp" > "$file_A"',
                    f'sed "{10+self.n_directives}s/.*/'
                    f'dumps=(\$(seq "$(($s_in-1))" "$(($s_en-1))"))/" '
                    f'"$file_A" > "$file_B"',
                    f'sed "{11+self.n_directives}s/.*/'
                    f'core0=(${{core[*]}})/" "$file_B" > "$file_A"',
                    f'sed "{12+self.n_directives}s/.*/'
                    f'core1=(${{ecore[*]}})/" "$file_A" > "$file_B"',
                    f'{self.scheduler.job_submission} < "$file_B"',
                ]
            for line in lines:
                file_.write(line+'\n')
            file_.write(f'rm "$file_A" "$file_B"')
        return