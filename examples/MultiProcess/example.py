
from multiproc.MultiProcess import MultiProcess
from antares import *

# ============================================================
# Function to parallelize
# ============================================================

def cut(queue, base, keys):
    treatment = Treatment('cut')
    treatment['base'] = base
    for key, value in keys.items():
        treatment[key] = value
    result = treatment.execute()
    
    writer = Writer()
    writer['base'] = result
    writer['filename'] = 'Output/cut_<zone>.dat'
    writer['file_format'] = 'bin_tp_u'
    writer.dump()

    queue.put(result)
    
# ============================================================
# Script
# ============================================================


reader = Reader()
reader['filename'] = '../Mesh_bin_tp_0/mesh_<zone>.dat'
reader['file_format'] = 'bin_tp'
base = reader.read()

func_keys = {
'type': 'plane',
'origin': [0., 0., 0.],
'normal': [1., 0., 0.],
}

multi = MultiProcess()
multi.func2parallelize = cut
multi.nb_proc = 2
multi.base = base
multi.func_keys = func_keys
outputs = multi.execute()

result = Base()
for output in outputs:
    for zone in output.keys():
        result[zone] = output[zone]

print result[0][0]
writer = Writer()
writer['base'] = result
writer['filename'] = 'Output/cut.dat'
writer['file_format'] = 'bin_tp_u'
writer['writer'] = 'WriterTecplot_python'
writer.dump()

