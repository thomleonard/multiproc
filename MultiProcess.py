from multiprocessing import Process, Queue
import numpy as np

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
            zone_per_proc = nb_zones // self.nb_proc
            rest = nb_zones - self.nb_proc * zone_per_proc
            if rest != 0:
                block2proc =  - np.ones((self.nb_proc, zone_per_proc + 1), dtype=np.int)
            else:
                block2proc =  - np.ones((self.nb_proc, zone_per_proc), dtype=np.int)
    
            for i in range(zone_per_proc):
                block2proc[:, i] = self.base.keys()[i * self.nb_proc: (i + 1) * self.nb_proc]

            if rest != 0:
                block2proc[:rest, zone_per_proc] = self.base.keys()[zone_per_proc * self.nb_proc:]
        else:
            pass
        self.block2proc = block2proc


    def execute(self):
        self.set_block2proc()
        
        print "\n >>>  Launch task on %s process" % self.nb_proc
        
        process = []
        queues = []
        for i in range(self.nb_proc):
            list_zones = tuple(self.block2proc[i][np.where(self.block2proc[i] >= 0)])
            sub_base = self.base[list_zones]
            queues.append(Queue())
            process.append(Process(target=self.func2parallelize, 
                                   args=(queues[i], 
                                         sub_base, 
                                         self.func_keys)))
            # launch process
            process[i].start()

        # get output
        outputs = []
        for i in range(self.nb_proc):
            outputs.append(queues[i].get())
        
        # force to wait that all process are finish 
        # (and then that all gets have been done)
        for i in range(self.nb_proc):
            process[i].join()
        
        return outputs

