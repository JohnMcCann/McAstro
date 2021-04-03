#!/usr/bin/env python3

class cap:
    # inheritance cap
    def __init__(self, *args, **kwargs):
        return

# Has only been vetted on slurm —John
class scheduler:
    def __init__(self, scheduler_name):
        self.name = scheduler_name.lower()
        # set scheduler variables
        if self.set_user_commands():
            return
        elif self.set_environment_variables():
            return
        elif self.set_job_specs():
            return
        return


    def set_user_commands(self):
        # User commands
        job_submission = {
            **dict.fromkeys(['slurm'], 'sbatch'),
            **dict.fromkeys(['pbs', 'torque'], 'qsub'),
            **dict.fromkeys(['lsf'], 'bsub')
        }
        job_deletion = {
            **dict.fromkeys(['slurm'], 'scancel'),
            **dict.fromkeys(['pbs', 'torque'], 'qdel'),
            **dict.fromkeys(['lsf'], 'bkill')
        }
        job_list = {
            **dict.fromkeys(['slurm'], 'squeue'),
            **dict.fromkeys(['pbs', 'torque'], 'qstat'),
            **dict.fromkeys(['lsf'], 'bjobs')
        }
        # Check scheduler
        if self.name not in job_submission.keys():
            print(f'ERROR: Scheduler ({self.name}) not recognized.')
            return 1
        # Set user commands
        self.job_submission = job_submission[self.name]
        self.job_deletion = job_deletion[self.name]
        self.job_list = job_list[self.name]
        return


    def set_environment_variables(self):
        # environment variables
        JOBID = {
            **dict.fromkeys(['slurm'], '$SLURM_JOBID'),
            **dict.fromkeys(['pbs', 'torque'], '$PBS_JOBID'),
            **dict.fromkeys(['lsf'], '$LSB_JOBID')
        }
        SUBMIT_DIR = {
            **dict.fromkeys(['slurm'], '$SLURM_SUBMIT_DIR'),
            **dict.fromkeys(['pbs', 'torque'], '$PBS_O_WORKDIR'),
            **dict.fromkeys(['lsf'], '$LSB_SUBCWD')
        }
        JOB_ARRAY_ID = {
            **dict.fromkeys(['slurm'], '$SLURM_ARRAY_TASK_ID'),
            **dict.fromkeys(['pbs', 'torque'], '$PBS_ARRAYID'),
            **dict.fromkeys(['lsf'], '$LSB_JOBINDEX')
        }
        NNODES = {
            **dict.fromkeys(['slurm'], '$SLURM_NNODES'),
            **dict.fromkeys(['pbs', 'torque'], '$PBS_NUM_NODES'),
            **dict.fromkeys(['lsf'], None)
        }
        NPROCS = {
            **dict.fromkeys(['slurm'], '$SLURM_NTASKS'), # or '$SLURM_NPROCS'
            **dict.fromkeys(['pbs', 'torque'], None),
            **dict.fromkeys(['lsf'], None)
        }
        CPUS_PER_NODE = {
            **dict.fromkeys(['slurm'], '$SLURM_JOB_CPUS_PER_NODE'),
            **dict.fromkeys(['pbs', 'torque'], '$PBS_NUM_PPN'),
            **dict.fromkeys(['lsf'], None)
        }
        # Check scheduler
        if self.name not in JOBID.keys():
            print(f'ERROR: Scheduler ({self.name}) not recognized.')
            return 1
        # Set environment variables
        self.JOBID = JOBID[self.name]
        self.SUBMIT_DIR = SUBMIT_DIR[self.name]
        self.CPUS_PER_NODE = CPUS_PER_NODE[self.name]
        self.JOB_ARRAY_ID = JOB_ARRAY_ID[self.name]
        self.NPROCS = NPROCS[self.name]
        return


    def set_job_specs(self):
        directive = {
            **dict.fromkeys(['slurm'], '#SBATCH'),
            **dict.fromkeys(['pbs', 'torque'], '#PBS'),
            **dict.fromkeys(['lsf'], '#BSUB')
        }
        queue = {
            **dict.fromkeys(['slurm'], '--partion='), # or '-p '
            **dict.fromkeys(['pbs', 'torque'], '-q '),
            **dict.fromkeys(['lsf'], '-q ')
        }
        node_count = {
            **dict.fromkeys(['slurm'], '--nodes='), # or '-N '
            **dict.fromkeys(['pbs', 'torque'], '-l nodes='),
            **dict.fromkeys(['lsf'], None)
        }
        task_count = {
            **dict.fromkeys(['slurm'], '--ntask='), # or '-n '
            **dict.fromkeys(['pbs', 'torque'], None),
            **dict.fromkeys(['lsf'], None)
        }
        cpu_per_task = {
            **dict.fromkeys(['slurm'], '--cpus-per-task='), # or '-c '
            **dict.fromkeys(['pbs', 'torque'], None),
            **dict.fromkeys(['lsf'], None)
        }
        task_per_node = {
            **dict.fromkeys(['slurm'], '--ntasks-per-node='),
            **dict.fromkeys(['pbs', 'torque'], '-l ppn='),
            **dict.fromkeys(['lsf'], None)
        }
        wallclock_limit = {
            **dict.fromkeys(['slurm'], '--time='), # or '-t '
            **dict.fromkeys(['pbs', 'torque'], '-l walltime='),
            **dict.fromkeys(['lsf'], '-t ')
        }
        standard_output = {
            **dict.fromkeys(['slurm'], '--output='), # or '-o '
            **dict.fromkeys(['pbs', 'torque'], '-o '),
            **dict.fromkeys(['lsf'], '-o ')
        }
        standard_error = {
            **dict.fromkeys(['slurm'], '--error='), # or '-e '
            **dict.fromkeys(['pbs', 'torque'], '-e '),
            **dict.fromkeys(['lsf'], '-e ')
        }
        job_name = {
            **dict.fromkeys(['slurm'], '--job-name='), # or '-J '
            **dict.fromkeys(['pbs', 'torque'], '-N '),
            **dict.fromkeys(['lsf'], '-J ')
        }
        cpu_per_node = {
            **dict.fromkeys(['slurm'], None),
            **dict.fromkeys(['pbs', 'torque'], None),
            **dict.fromkeys(['lsf'], None)
        }
        job_array = {
            **dict.fromkeys(['slurm'], '--array='), # or '-a '
            **dict.fromkeys(['pbs', 'torque'], '-t '),
            **dict.fromkeys(['lsf'], '-J array')
        }
        begin_time = {
            **dict.fromkeys(['slurm'], '--begin='), # or '-b '
            **dict.fromkeys(['pbs', 'torque'], '-A '),
            **dict.fromkeys(['lsf'], '-b ')
        }
        job_dependency = {
            **dict.fromkeys(['slurm'], '--dependency='), # or '-d '
            **dict.fromkeys(['pbs', 'torque'], '-d '),
            **dict.fromkeys(['lsf'], '-w ')
        }
        # Check scheduler
        if self.name not in directive.keys():
            print(f'ERROR: Scheduler ({self.name}) not recognized.')
            return 1
        # Set job specification
        self.directive = directive[self.name]
        self.queue = queue[self.name]
        self.node_count = node_count[self.name]
        self.task_count = task_count[self.name]
        self.cpu_per_task = cpu_per_task[self.name]
        self.task_per_node = task_per_node[self.name]
        self.wallclock_limit = wallclock_limit[self.name]
        self.standard_output = standard_output[self.name]
        self.standard_error = standard_error[self.name]
        self.job_name = job_name[self.name]
        self.cpu_per_node = cpu_per_node[self.name]
        self.job_array = job_array[self.name]
        self.begin_time = begin_time[self.name]
        self.job_dependency = job_dependency[self.name]
        return