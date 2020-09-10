#------------------------------------------------------------------
# Ver: Sept-04-2020
# Author: Vaidyanathan Sethuraman
# To generate the initial configuration file for lignin topology
# Use NAMD to run the script
# An iterative procedure is used

# References for lignin structure: 
# (A) Yan et al., Biomass and Bioenergy 34, 48-53, 2010 
# (B) Samuel et al., Frontiers in Energy Research, 1 (14) 2014

# 'None' is a keyword reserved - DONT USE IT for PDB/PSF filenames.
# Switchgrass variety: Alamo switchgrass

# H:G:S = 26:42:32 (A); G:S = 0.75 - 0.78, H = 2 (B)
# pCA:FA = 1 (A); pCA:FA = 6:32 (B) 

#------------------------------------------------------------------

# Import modules
import os
import sys
import numpy
import re
import shutil
import glob
import math

# Function definitions
from make_genpsf import gencpy
from make_genpsf import psfgen_headers
from make_genpsf import psfgen_postprocess
from make_genpsf import residue_ratios
from make_genpsf import linker_ratios
from make_genpsf import init_logwrite
from make_genpsf import cumul_probdist
from make_genpsf import create_segments
from make_genpsf import create_patches
from make_genpsf import write_multi_segments
from make_genpsf import write_segments_onego

# Input data
casenum    = 1  # case number
biomas_typ  = 'switchgrass_' # type of biomass; end with _
deg_poly   = 16 # degree of polymerization (final)
swit_opt   = 'A' # references, A,B (add more and hard code if necesary)
input_top = 'lignin.top' # topology file input
input_pdb  = 'G-bO4L-G.pdb' # file input - dimer
seg_name = 'swli' #name of segment: switchgrass lignin
num_chains = 1 # number of chains
tol = 0.1 # relative tolerance
maxatt = 500 # maximum attempts to obtain avg configuration
itertype  = 'single' # Op style: single-> one go. multi-> multi iter

# Output file names (will be generated automatically)
tcl_fname  = biomas_typ + str(casenum) + '.tcl' # outfile for tcl
pdbpsf_name = biomas_typ + str(casenum)  #prefix for pdb/psf files
reslist_fname = 'reslist_' + str(casenum) + '.tcl' #all seg list
links_fname = 'linklist_' + str(casenum)+ '.tcl' #all link list
log_fname = 'log_' + str(casenum) + '.txt' #log file

# Read defaults and throw exceptions
if not os.path.exists(input_top):
    exit('Topology file not found \n')

if not os.path.exists(input_pdb):
    exit('Dimer file not found \n')

resperc_dict = residue_ratios(swit_opt) # residue % dictionary mode
if not bool(resperc_dict):
    exit('ERROR: Unknown option for monomer parameters \n')

linkperc_dict = linker_ratios(swit_opt) # linker % dictionary mode
if not bool(linkperc_dict):
    exit('ERROR: Unknown option for linker parameters \n')

# Get directory info
srcdir = os.getcwd()
outdir = srcdir + str('/casenum_') + str(casenum) # out directory

# Create main directory and copy required files
if not os.path.isdir(outdir):
    os.mkdir(outdir)

gencpy(srcdir,outdir,input_top)
gencpy(srcdir,outdir,input_pdb)

# Open file and write headers
fmain = open(outdir + '/' + tcl_fname,'w')
psfgen_headers(fmain,input_top,pdbpsf_name)
fresin = open(outdir + '/' + reslist_fname,'w')
fresin.write(';# Contains all segments for NAMD files.\n')
flinkin = open(outdir + '/' + links_fname,'w')
flinkin.write(';# Contains all patches/links for NAMD files.\n')
flog = open(outdir + '/' + log_fname,'w')
init_logwrite(flog,casenum,biomas_typ,deg_poly,swit_opt,input_top\
              ,input_pdb,seg_name,num_chains)
print('Begin analysis for ',biomas_typ,', case_num: ', casenum)
            
# Create cumulative probability distribution of segments/patches
flog.write('Making cumulative distribution for segments..\n')
cumul_resarr = cumul_probdist(resperc_dict,flog)
flog.write(str(cumul_resarr))

flog.write('Making cumulative distribution for patches..\n')
cumul_linkarr = cumul_probdist(linkperc_dict,flog)
flog.write(str(cumul_linkarr))
    
# Set 2D default list and generate segments/linkers
res_list = [[] for i in range(num_chains)]
link_list = [[] for i in range(num_chains-1)]

# Create segments/links and check for avg probability 
flog.write('Creating residue list..\n')
res_list = create_segments(fresin,deg_poly,num_chains,seg_name,\
                           resperc_dict,cumul_resarr,tol,maxatt,flog)
flog.write('Creating patches list..\n')
link_list = create_patches(flinkin,deg_poly,num_chains,seg_name,\
                           linkperc_dict,cumul_linkarr,tol,maxatt,flog)

if itertype == 'single':
    write_segments_onego(fmain,deg_poly,num_chains,seg_name,\
                         res_list,link_list)
    psfgen_postprocess(fmain,input_pdb,itertype,0,'None')

elif itertype == 'multi':
    # Number of iterations needed per chain
    niter = int(math.log(deg_poly)/math.log(2)) #closest power of 2
    flog.write('Number of iterations per chain: %d\n ' %(niter))

    # Write segments according to iteration number
    for iterval in range(niter):
        iter_num  = iterval + 1
        nmonsthisiter = pow(2,iter_num)
        write_multi_segments(fmain,iter_num,nmonsthisiter,num_chains\
                             ,seg_name,res_list,link_list)
        psfgen_postprocess(fmain,input_pdb,itertype,iter_num,seg_name)
        fmain.write('namd2 mini.conf > mini.out\n')
        fmain.write(';# exit')

    # Write the rest in one go
    if deg_poly != pow(math.log(2),niter):
        iter_num = iter_num + 1
        write_multi_segments(fmain,iter_num,deg_poly,num_chains,seg_name,\
                             res_list,link_list)
        psfgen_postprocess(fmain,input_pdb,itertype,iter_num,seg_name)
        fmain.write('namd2 mini.conf > mini.out\n')
        fmain.write(';# exit')        

else:
    exit('ERROR: Unknown output write style option: ' + itertype)

#Exit file
fmain.write('exit')

# Close files
fclose(fresin)
fclose(flinkin)
fclose(flog)
fcose(fmain)
