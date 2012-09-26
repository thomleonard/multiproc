"""
Auteur : Thomas Leonard
"""

from antares import *
from antares.core.PrintUtility import print_error, print_debug, \
                                      print_1, print_2, print_object
from scipy.spatial import cKDTree as KDTree
from copy import deepcopy
import os
import numpy as np


class Block2proc:
    """
    classe block 2 proc avec dictionnaires qui permettent de savoir :
        - les blocks d'un procs, 
        - le nb de points du proc, 
        - le nombre de block nomatch du proc,
        - le proc d'un block,
        - le nombre de points d'un block
    et toutes les informations disponibles dans une topologie
    """

# =======================================
# Initialisation
# =======================================

    def __init__(self, b2p_file, base=None):
        print_1('Read file block2proc : %s'%b2p_file)
        if not os.path.isfile(b2p_file):
            print_error('file %s does not exist' % b2p_file)
            raise IOError
        # set class attributes
        self.block2proc = None
        self.proc2block = None
        self.has_nomatch = None
        self.nb_proc = None
        self.nb_block = None
        self.base = None
        # initialize class
        self.__initialize(b2p_file)
        if base != None:
            assert(isinstance(base, Base))
            self.base = base
            self.__set_base()

    def __initialize(self, b2p_file):
        dico_detected = False
        data = open(b2p_file, 'r').read().split('\n')
        idx = 0
        while not dico_detected:
            line = data[idx].split('#')[0].replace(' ', '')
            if 'dict_block2proc={' in line:
                dico_detected = True
            else:
                idx += 1
        str_dico = ''.join(data[idx:]).split('}')[0] + '}'
        exec(str_dico)
        blocks = np.array(dict_block2proc.keys())
        procs = np.array(dict_block2proc.values())
        sorting = np.argsort(blocks)
        
        self.block2proc = procs[sorting]
        self.nb_proc = 1 + np.max(self.block2proc)
        self.proc2block = [np.where(self.block2proc == proc_idx)[0] for proc_idx in range(self.nb_proc)]
        self.nb_block = self.block2proc.shape[0]

    def __set_base(self):
        if len(self.base.keys()) != self.nb_block:
            print_error(("the base given doesn't have the same block "
                "number than the block2proc file (%i vs %i)" % (len(self.base.keys()), self.nb_block)))

        has_nomatch = []
        nomatch_family = Family()
        self.base.families['nomatch_blocks'] = nomatch_family
        for proc_idx in range(self.nb_proc):
            family = Family()
            self.base.families['proc%04i' % proc_idx] = family
            proc_has_nomatch = False
            for block_idx in self.proc2block[proc_idx]:
                family[self.base.keys()[block_idx]] = self.base[block_idx]
                self.base[block_idx].extras['has_nomatch'] = False
                for boundary in self.base[block_idx].boundaries.values():
                    if boundary['type'] == 'nomatch':
                        self.base[block_idx].extras['has_nomatch'] = True
                        proc_has_nomatch = True
                        nomatch_family[self.base.keys()[block_idx]] = self.base[block_idx]
            has_nomatch.append(proc_has_nomatch)
            family.add_extra('proc', proc_idx)
        self.has_nomatch = np.array(has_nomatch)

# =======================================
# Classical stuffs
# =======================================

    def __str__(self):
        attributs = []
        attributs.append({'param': 'number of blocks',
                          'value': self.nb_block})
        attributs.append({'param': 'number of procs',
                          'value': self.nb_proc})
        if self.base != None:
            nb_nomatch_blocks = 0
            for block in self.base.values():
                if block.extras['has_nomatch']:
                        nb_nomatch_blocks += 1
            attributs.append({'param': 'number of blocks with nomatch',
                              'value': nb_nomatch_blocks})
        if self.has_nomatch != None:
            nb_nomatch_procs = len(np.where(self.has_nomatch == True)[0])
            attributs.append({'param': 'number of procs with nomatch',
                              'value': nb_nomatch_procs})
        return print_object(object_name='Block2proc',
                            attributs=attributs)

    def get_load_balance(self, tolerance=20.):
        """
        tolerance is for proc balance print (in percent)
        """
        if self.base == None:
            print_error('A base must be given to be able to compute the load balance')
            raise ValueError
        # compute mean number of point per proc
        mean_size = 0
        for proc_idx in range(self.nb_proc):
            proc_family = self.base.families['proc%04i' % proc_idx]
            mean_size += self.base[proc_family].grid_points
        mean_size = float(mean_size) / float(self.nb_proc)
        # compute load balance
        mean_dist = 0
        max_dist = 0
        for proc_idx in range(self.nb_proc):
            proc_family = self.base.families['proc%04i' % proc_idx]
            dist = abs(mean_size - self.base[proc_family].grid_points)
            mean_dist += dist
            if dist > max_dist:
                max_dist = dist
                max_proc = proc_idx
            proc_balance = float(dist) / float(mean_size) * 100.
            if proc_balance > tolerance:
                print_2('proc %s : load_balance  %.2f%%' % (proc_idx, proc_balance))
        mean_dist = float(mean_dist) / float(self.nb_proc)
        load_balance = float(max_dist) / float(mean_size) * 100.
        mean_load_balance = float(mean_dist) / float(mean_size) * 100.
        print_2('maximum load balance : %.2f%% (proc %i)' % (load_balance, max_proc))
        print_2('mean load balance : %.2f%%' % mean_load_balance)
        print_2('mean number of points per proc : %i' % mean_size)
        return load_balance

    def dump(self, filename):
        print_1('Write file block2proc : %s' % filename)
        str_b2p = '# ---------------------------------------------------------\n'
        str_b2p += '# Script block2proc created with Antares\n'
        str_b2p += '# ---------------------------------------------------------\n'
        str_b2p += '\n'
        str_b2p += '# Number of processors   :\n'
        str_b2p += 'nproc = %i\n' % self.nb_proc
        str_b2p += '\n'
        str_b2p += 'dict_block2proc = {\n'
        for block_idx in range(self.nb_block):
            proc_idx = self.block2proc[block_idx]
            str_b2p += '    %i : %4i,\n' % (block_idx, proc_idx)
        str_b2p += '}\n'
        
        f = open(filename, 'w')
        f.write(str_b2p)
        f.close()

# =======================================
# Modify Block2proc
# =======================================

    def modulo_proc(self, modulo):
        print_1('Modify number of procs')
        modulo = int(modulo)
        if self.nb_proc % modulo != 0:
            print_error('number of proc %i is not divisible by %i' % (self.nb_proc, modulo))
            raise ValueError
        old_nb_proc = deepcopy(self.nb_proc)
        old_proc2block = deepcopy(self.proc2block)
        old_block2proc = deepcopy(self.block2proc)
        self.nb_proc = old_nb_proc // modulo
        self.proc2block = []
        self.proc2block = [ \
            np.concatenate([old_proc2block[proc_idx + self.nb_proc * modulo_idx] for modulo_idx in range(modulo)]) \
            for proc_idx in range(self.nb_proc)] 
        self.block2proc = old_block2proc % self.nb_proc
        if self.base != None:
            for proc_idx in range(old_nb_proc):
                del self.base.families['proc%04i' % proc_idx]
            self.__set_base()

    def set_block_to_proc(self, block_name, proc_number):
        old_proc_number = self.get_block(block_name)['proc']
        # modifie le num de proc du bloc
        self.get_block(block_name)['proc'] = proc_number
        # modifie les info du nouveau proc
        self.get_proc(proc_number)['blocks'].append(block_name)
        self.get_proc(proc_number)['nb_points'] += self.get_block(block_name)['nb_points']
        if self.get_block(block_name)['nomatch'] :
            self.get_proc(proc_number)['nomatch'] += 1
            self.get_proc(proc_number)['blocks_nomatch'].append(block_name)
        else :
            self.get_proc(proc_number)['blocks_non_nomatch'].append(block_name)
        # modifie les info de l'ancien proc
        indx = self.get_proc(old_proc_number)['blocks'].index(block_name)
        self.get_proc(old_proc_number)['blocks'].pop(indx)
        self.get_proc(old_proc_number)['nb_points'] -= self.get_block(block_name)['nb_points']
        if self.get_block(block_name)['nomatch'] :
            self.get_proc(old_proc_number)['nomatch'] -= 1
            indx = self.get_proc(old_proc_number)['blocks_nomatch'].index(block_name)
            self.get_proc(old_proc_number)['blocks_nomatch'].pop(indx)
        else :
            indx = self.get_proc(old_proc_number)['blocks_non_nomatch'].index(block_name)
            self.get_proc(old_proc_number)['blocks_non_nomatch'].pop(indx)
        self.set_nomatch_numbers()

    def all_nomatch_on_one_proc(self):
        print_1('Move all nomatch on one proc')
        if self.base == None:
            print_error('A base must be given to be able to detect nomatchs')
            raise ValueError
        # find block with the biggest nomatch
        nomatch_blocks = deepcopy(self.base.families['nomatch_blocks'].keys())
        biggest_nomatch = nomatch_blocks[0]
        biggest_nb_points = np.prod(self.base[biggest_nomatch].shape)
        for block_name in nomatch_blocks:
            nb_points = np.prod(self.base[block_name].shape)
            if nb_points > biggest_nb_points:
                biggest_nb_points = nb_points
                biggest_nomatch = block_name
                
        nomatch_blocks.remove(biggest_nomatch)
        biggest_index = self.base.keys().index(biggest_nomatch)
        target_proc = self.block2proc(biggest_index)
        # ---------------------------
        def find_closest(block_name, target_proc):
            # find the non-nomatch block with the closest size on the target_proc
            non_nomatch_blocks = []
            non_nomatch_sizes = []
            for block_idx in self.proc2block[target_proc]:
                if not self.base[block_idx].extras['has_nomatch']:
                    non_nomatch_blocks.append(block_idx)
                    non_nomatch_sizes.append(np.prod(self.base[block_idx]))
            non_nomatch_sizes = np.array(non_nomatch_sizes)
            if len(non_nomatch_blocks) == 0:
                xchange_block = None
            else:
                xchange_block = non_nomatch_blocks.index( \
                    np.argmin(abs(non_nomatch_sizes - np.prod(self.base[block_name].shape))))
            return xchange_block 
        # ---------------------------
        compteur = 0
        for block_name in nomatch_blocks:
            block_idx = self.base.keys().index(block_name)
            origin_proc = self.block2proc[block_idx]
            if origin_proc != target_proc:
                xchange_block = find_closest(block_name, target_proc)
                if xchange_block != None:
                    self.set_block_to_proc(xchange_block, origin_proc)
                    compteur += 1
                self.set_block_to_proc(block_name, target_proc)
                compteur += 1
        print_2('%i blocks have been moved' % compteur)

    def dispatch_nomatch_on_procs(self, tolerance=0.2):
        compteur = 0
        print_2('commence la repartition des nomatchs')
        avec_plus, avec_moins, avec_max, avec_min = self.find_avec_plus_moins_minmax()
        print_3('%s procs desiquilibres'%(len(avec_plus)+len(avec_moins)))
        # repartie sur les procs pas assez charges en nomatchs
        # updater avec_moins, avec_plus, avec_max, avec_min
        # ---------------------------
        def find_closest(mini_proc, input_list, non_nomatch_to_nomatch=True ):
            # cherche les deux blocks les plus proches pour un echange
            if non_nomatch_to_nomatch :
                type_blocks_1 = 'blocks_non_nomatch'
                type_blocks_2 = 'blocks_nomatch'
            else :
                type_blocks_1 = 'blocks_nomatch'
                type_blocks_2 = 'blocks_non_nomatch'
            non_nomatch_blocks = []
            non_nomatch_blocks_size = []
            for block in self.get_proc(mini_proc)[type_blocks_1]:
                non_nomatch_blocks.append(block)
                non_nomatch_blocks_size.append(self.get_block(block)['nb_points'])
            nomatch_blocks = []
            nomatch_blocks_size = []
            for p in input_list:
                nomatch_blocks.extend(self.get_proc(p)[type_blocks_2]) 
                for nmb in self.get_proc(p)[type_blocks_2]:
                    nomatch_blocks_size.append(self.get_block(nmb)['nb_points'])
            # trouver les plus proches
            kdtree = KDTree(zip(non_nomatch_blocks_size))
            distances, indices = kdtree.query(zip(nomatch_blocks_size), k=1)
            indx = list(distances).index(min(distances))
            tbc_nomatch_block = nomatch_blocks[indx]
            tbc_non_nomatch_block = non_nomatch_blocks[int(indices[int(indx)])]
            # print_3('desequilibrage %s%%'%(float(int(float(min(distances))/float(nomatch_blocks_size[indx])*10000.))/100.))
            new_proc = deepcopy(self.get_block(tbc_nomatch_block)['proc'])
            return [tbc_nomatch_block, mini_proc], [tbc_non_nomatch_block, new_proc]
        # ---------------------------
        def find_smallest(input_list):
            mini_block_size = self.get_block(self.get_proc(input_list[0])['blocks_nomatch'][0])['nb_points']
            mini_block = self.get_proc(input_list[0])['blocks_nomatch'][0]
            for p in range(len(input_list)):
                for n in self.get_proc(input_list[p])['blocks_nomatch']:
                    if self.get_block(n)['nb_points'] < mini_block_size:
                        mini_block_size = self.get_block(n)['nb_points']
                        mini_block = n
            return mini_block
        # ---------------------------
        def check_tol(temp_prc1, temp_prc2, compteur, tolerance):
            new_compteur = compteur
            temp_nb1 = self.get_proc(temp_prc1)['nb_points']
            temp_nb2 = self.get_proc(temp_prc2)['nb_points']
            if temp_nb1 > temp_nb2:
                nb1 = temp_nb1
                nb2 = temp_nb2
                prc1 = temp_prc1
                prc2 = temp_prc2 
            else:
                nb1 = temp_nb2
                nb2 = temp_nb1
                prc1 = temp_prc2
                prc2 = temp_prc1
#            print 'proc ',prc1,' :'
#            for iblk in self.get_proc(prc1)['blocks']:
#                 if self.get_block(iblk)['nomatch']:
#                    print '     ',iblk,' (nomatch) : ',self.get_block(iblk)['nb_points']
#                 else:
#                    print '     ',iblk,' (match) : ',self.get_block(iblk)['nb_points']
#            print 'proc ',prc2,' :'
#            for iblk in self.get_proc(prc2)['blocks']:
#                 if self.get_block(iblk)['nomatch']:
#                    print '     ',iblk,' (nomatch) : ',self.get_block(iblk)['nb_points']
#                 else:
#                    print '     ',iblk,' (match) : ',self.get_block(iblk)['nb_points']
            old_desequilibrage = abs(float(nb1-nb2))/(float(nb2+nb1)/2.)
            desequilibrage = abs(float(nb1-nb2))/(float(nb2+nb1)/2.)
            if desequilibrage > tolerance:
                # Si l'ecart de taille entre les deux procs est superieur a la tolerance
                # cherche a voir si il peut pas ajouter d'autres blocks non nomatch pour contrebalancer
                delta = nb1-nb2
                sizes = []
                for iblk in self.get_proc(prc1)['blocks_non_nomatch']:
                    sizes.append(self.get_block(iblk)['nb_points'])
                sizes.sort()
                sorted_block = []
                for indice in range(len(self.get_proc(prc1)['blocks_non_nomatch'])):
                    done = False
                    indice0 = 0
                    while not done:
                       blk_name = self.get_proc(prc1)['blocks_non_nomatch'][indice0] 
                       if (self.get_block(blk_name)['nb_points']) == sizes[indice]: 
                            if blk_name not in sorted_block:
                                sorted_block.append(blk_name)
                                done = True
                       indice0 += 1
                big_to_small = [sorted_block[len(sorted_block)-i-1] for i in range(len(sorted_block))]
                for blk in big_to_small:
                    new_nb1 = nb1-self.get_block(blk)['nb_points']
                    new_nb2 = nb2+self.get_block(blk)['nb_points']
                    new_desequilibrage = abs(float(new_nb1-new_nb2))/(float(new_nb2+new_nb1)/2.)
                    if new_desequilibrage < desequilibrage:
                        self.set_block_to_proc(blk, prc2)
                        new_compteur += 1
                        nb1 = self.get_proc(prc1)['nb_points']
                        nb2 = self.get_proc(prc2)['nb_points']
                        desequilibrage = abs(float(nb1-nb2))/(float(nb2+nb1)/2.)
            if desequilibrage > 0.3:
                print_debug('toujours un desiquilibrage superieur a la tolerance entre les procs %s et %s (deseq=%3f>%3f)'%(prc1,prc2,old_desequilibrage,desequilibrage))
            #    print 'proc ',prc1,' :'
            #    for iblk in self.get_proc(prc1)['blocks']:
            #         if self.get_block(iblk)['nomatch']:
            #            print '     ',iblk,' (nomatch) : ',self.get_block(iblk)['nb_points']
            #         else:
            #            print '     ',iblk,' (match) : ',self.get_block(iblk)['nb_points']
            #    print 'proc ',prc2,' :' 
            #    for iblk in self.get_proc(prc2)['blocks']:
            #         if self.get_block(iblk)['nomatch']:
            #            print '     ',iblk,' (nomatch) : ',self.get_block(iblk)['nb_points']
            #         else:
            #            print '     ',iblk,' (match) : ',self.get_block(iblk)['nb_points']
            #    print ''
            return new_compteur
        # ---------------------------
        # print_debug('avec_moins : %s'%str(avec_moins))
        while avec_moins != []:
            mini_proc = avec_moins[0]
            nb_mini_block = len(self.get_proc(avec_moins[0])['blocks'])
            for p in range(1, len(avec_moins)) :
                # cherche le proc qui a le moins de block dans les procs qui manquent de nomatch 
                if len(self.get_proc(avec_moins[p])['blocks']) < nb_mini_block :
                    nb_mini_block = len(self.get_proc(avec_moins[p])['blocks'])
                    mini_proc = avec_moins[p]
            # print_debug('mini_proc %s nomatchs > %s'%(mini_proc, str(self.get_proc(mini_proc)['blocks_nomatch'])))
            if nb_mini_block == 1:
                # Si le proc n'a qu'un seul block
                # cherche le plus petit nomatch pour l'ajouter au proc
                if len(avec_plus) != 0:
                    mini_block = find_smallest(avec_plus)
                else :
                    mini_block = find_smallest(avec_max)
                if len(self.get_proc(self.get_block(mini_block)['proc'])['blocks']) == 1 :
                    # si le proc duquel on cherche a prendre le nomatch ne contient que ce block
                    # erreur parce que on creer un proc qui n'aura plus de block
                    print_error("tente de deplacer le block %s du proc %s qui n'aura alors plus aucun block"%(mini_block, self.get_block(mini_block)['proc']))
                self.set_block_to_proc(mini_block, mini_proc)
                compteur += 1
            else:
                # Si le proc a plus d'un block
                # cherche a faire un echange equilibre avec un proc qui a trop de nomatch
                if len(avec_plus) != 0:
                    chg_blk_1, chg_blk_2 = find_closest(mini_proc, avec_plus)
                else :
                    chg_blk_1, chg_blk_2 = find_closest(mini_proc, avec_max)
                self.set_block_to_proc(chg_blk_1[0], chg_blk_1[1])
                self.set_block_to_proc(chg_blk_2[0], chg_blk_2[1])
                compteur += 2
                compteur = check_tol(chg_blk_1[1], chg_blk_2[1], compteur, tolerance)
            avec_plus, avec_moins, avec_max, avec_min = self.find_avec_plus_moins_minmax()
            # print_debug('mini_proc %s nomatchs > %s'%(mini_proc, str(self.get_proc(mini_proc)['blocks_nomatch'])))
        #   print_debug('avec_moins : %s'%str(avec_moins))
        # print_debug('avec_plus : %s'%str(avec_plus))
        while avec_plus != []:
            mini_proc = avec_plus[0]
            nb_mini_block = len(self.get_proc(avec_plus[0])['blocks'])
            for p in range(1, len(avec_plus)) :
                # cherche le proc qui a le moins de block dans les procs qui ont trop de nomatchs
                if len(self.get_proc(avec_plus[p])['blocks']) < nb_mini_block :
                    nb_mini_block = len(self.get_proc(avec_plus[p])['blocks'])
                    mini_proc = avec_plus[p]
            # print_debug('mini_proc %s nomatchs > %s'%(mini_proc, str(self.get_proc(mini_proc)['blocks_nomatch'])))
            chg_blk_1, chg_blk_2 = find_closest(mini_proc, avec_min, non_nomatch_to_nomatch=False)
            self.set_block_to_proc(chg_blk_1[0], chg_blk_1[1])
            self.set_block_to_proc(chg_blk_2[0], chg_blk_2[1])
            compteur += 2
            compteur = check_tol(chg_blk_1[1], chg_blk_2[1], compteur, tolerance)
            avec_plus, avec_moins, avec_max, avec_min = self.find_avec_plus_moins_minmax()
            # print_debug('mini_proc %s nomatchs > %s'%(mini_proc, str(self.get_proc(mini_proc)['blocks_nomatch'])))
            # print_debug('avec_plus : %s'%str(avec_plus))
        print_2('repartition finie')
        print_3('%s blocks on ete deplaces'%compteur)


    def find_avec_plus_moins_minmax(self):
        nb_mini_nomatch = int(self._nomatch_blocks)/int(self._nbprocs)
        if float(self._nomatch_blocks)/float(self._nbprocs) > nb_mini_nomatch :
            nb_max_nomatch = nb_mini_nomatch +1
        else :
            nb_max_nomatch = nb_mini_nomatch
        # trouve les procs avec trop/pas assez de nomatch
        avec_plus = []
        avec_moins = []
        avec_max = []
        avec_min = []
        for p in range(self._nbprocs) :
            if self.get_procs()[p]['nomatch'] > nb_max_nomatch :
                avec_plus.append(p)
            elif self.get_procs()[p]['nomatch'] < nb_mini_nomatch :
                avec_moins.append(p)
            elif self.get_procs()[p]['nomatch'] == nb_max_nomatch :
                avec_max.append(p)
            elif self.get_procs()[p]['nomatch'] == nb_mini_nomatch :
                avec_min.append(p)
        return avec_plus, avec_moins, avec_max, avec_min





