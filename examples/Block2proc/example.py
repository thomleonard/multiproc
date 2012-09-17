from antares import *
from Block2proc import Block2proc

verbose(2)

reader = Reader()
reader['topology_file'] = 'script_topology.py'
base = reader.read()

b2p = Block2proc(b2p_file='block2proc_32.py', base=base)
print b2p


