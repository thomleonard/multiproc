from antares import *
from multiproc.Block2proc import Block2proc

verbose(2)

reader = Reader()
reader['topology_file'] = 'script_topology.py'
base = reader.read()
print base.families.keys()

b2p = Block2proc(b2p_file='block2proc_32.py', base=base)
print b2p
print base.families.keys()

b2p.modulo_proc(2)
print b2p

print base.families.keys()

b2p.dump('block2proc_16.py')