from multiprocessing import Process, Queue
import numpy as np
import antares
from antares.core.PrintUtility import print_1

class MultiProcess:
    
    def __init__(self):
        """
        the func2parallelize must take 3 argument :
           - a queue (to allow a return)    
           - a base (MultiProcess.base)
           - a third of free type (MultiProcess.func_keys)
        """
        self.func2parallelize = None
        self.nb_proc = 1
        self.base = None
        self.func_keys = None
        self.block2proc = None
        
    def set_block2proc(self, from_file=None):
        if from_file == None:
            nb_zones = len(self.base.keys())
            block2proc = np.arange(nb_zones) % self.nb_proc
        else:
            raise NotImplementedError
        self.block2proc = block2proc


    def execute(self):
        self.set_block2proc()
        print_1("Launch task on %s process" % self.nb_proc)
        verbose = antares.verbose()
        antares.verbose(0)
        process = []
        queues = []
        for proc_idx in range(self.nb_proc):
            zone_indices = tuple(np.where(self.block2proc == proc_idx)[0])
            sub_base = self.base[zone_indices]
            queues.append(Queue())
            process.append(Process(target=self.func2parallelize, 
                                   args=(queues[proc_idx], 
                                         sub_base, 
                                         self.func_keys)))
            # launch process
            process[proc_idx].start()

        # get output
        outputs = []
        for proc_idx in range(self.nb_proc):
            outputs.append(queues[proc_idx].get())
        
        # force to wait that all process are finish 
        # (and then that all gets have been done)
        for proc_idx in range(self.nb_proc):
            process[proc_idx].join()
        antares.verbose(verbose)
        return outputs

