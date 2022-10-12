# -------------------------- rigSkirtFK ----------------------------------
import pymel.core as pm
from nuTools.rigTools import fkRig as nfk
reload(nfk)
def main() :
        grpRig = pm.group(em=True, n='skirtFkRig_grp')
        grpLFTRig = pm.group(em=True, n='skirtLFTRig_grp')
        grpRGTRig = pm.group(em=True, n='skirtRGTRig_grp')
        grpJntZro = pm.group(em=True, n='skirtJntZro_grp')
        #snap Grp
        snapLFTGrp = pm.parentConstraint('skirt1LFT_tmpJnt', grpLFTRig, mo=False)
        snapRGTGrp = pm.parentConstraint('skirt1RGT_tmpJnt', grpRGTRig, mo=False)
        pm.delete(snapLFTGrp)
        pm.delete(snapRGTGrp)

# Rig skirt Fnt
        fkRig = nfk.FkRig(elem='skirt',
                side='Fnt',
                jnts=(
                'skirt1Fnt_tmpJnt',
                'skirt2Fnt_tmpJnt',
                'skirt3Fnt_tmpJnt',
                'skirt4Fnt_tmpJnt',
                'skirt5Fnt_tmpJnt'), 
                ctrlShp='circle')
        fkRig.rig()
        pm.parent ('skirtRigFnt_grp' ,grpRig)
        #groupOfJnt
        grpJnt = pm.group(em=True, n='skirtFntJntZro_grp')
        snapGrp = pm.parentConstraint ('skirt1Fnt_jnt', grpJnt, mo=False)
        pm.delete(snapGrp)
        pm.parent ('skirt1Fnt_jnt', grpJnt)
        pm.parent (grpJnt, grpJntZro)
        #delete Grp Free
        pm.parent ('skirt1FntZro_grp', grpRig)
        pm.delete ('skirtRigFnt_grp')

# Rig skirt Fnt LFT
        fkRig = nfk.FkRig(elem='skirt',
                side='FntLFT',
                jnts=(
                'skirt1FntLFT_tmpJnt',
                'skirt2FntLFT_tmpJnt',
                'skirt3FntLFT_tmpJnt',
                'skirt4FntLFT_tmpJnt',
                'skirt5FntLFT_tmpJnt'), 
                ctrlShp='circle')              
        fkRig.rig()
        grpFntLFT = pm.parent ('skirtRigFntLFT_grp' ,grpLFTRig)
        #groupOfJnt
        grpJnt = pm.group(em=True, n='skirtFntLFTJntZro_grp')
        snapGrp = pm.parentConstraint ('skirt1FntLFT_jnt', grpJnt, mo=False)
        pm.delete(snapGrp)
        pm.parent ('skirt1FntLFT_jnt', grpJnt)
        pm.parent (grpJnt, grpJntZro)

# Rig skirt  LFT
        fkRig = nfk.FkRig(elem='skirt',
                side='LFT',
                jnts=(
                'skirt1LFT_tmpJnt',
                'skirt2LFT_tmpJnt',
                'skirt3LFT_tmpJnt',
                'skirt4LFT_tmpJnt',
                'skirt5LFT_tmpJnt'), 
                ctrlShp='circle')              
        fkRig.rig()
        grpLFT = pm.parent ('skirtRigLFT_grp' ,grpLFTRig)
        #groupOfJnt
        grpJnt = pm.group(em=True, n='skirtLFTJntZro_grp')
        snapGrp = pm.parentConstraint ('skirt1LFT_jnt', grpJnt, mo=False)
        pm.delete(snapGrp)
        pm.parent ('skirt1LFT_jnt', grpJnt)
        pm.parent (grpJnt, grpJntZro)

# Rig skirt Bak LFT
        fkRig = nfk.FkRig(elem='skirt',
                side='BakLFT',
                jnts=(
                'skirt1BakLFT_tmpJnt',
                'skirt2BakLFT_tmpJnt',
                'skirt3BakLFT_tmpJnt',
                'skirt4BakLFT_tmpJnt',
                'skirt5BakLFT_tmpJnt'), 
                ctrlShp='circle')              
        fkRig.rig()
        grpBakLFT = pm.parent ('skirtRigBakLFT_grp' ,grpLFTRig)
        #groupOfJnt
        grpJnt = pm.group(em=True, n='skirtBakLFTJntZro_grp')
        snapGrp = pm.parentConstraint ('skirt1BakLFT_jnt', grpJnt, mo=False)
        pm.delete(snapGrp)
        pm.parent ('skirt1BakLFT_jnt', grpJnt)
        pm.parent (grpJnt, grpJntZro)

# Rig skirt Bak 
        fkRig = nfk.FkRig(elem='skirt',
                side='Bak',
                jnts=(
                'skirt1Bak_tmpJnt',
                'skirt2Bak_tmpJnt',
                'skirt3Bak_tmpJnt',
                'skirt4Bak_tmpJnt',
                'skirt5Bak_tmpJnt'), 
                ctrlShp='circle')              
        fkRig.rig()
        pm.parent ('skirtRigBak_grp' ,grpRig)
        #groupOfJnt
        grpJnt = pm.group(em=True, n='skirtBakJntZro_grp')
        snapGrp = pm.parentConstraint ('skirt1Bak_jnt', grpJnt, mo=False)
        pm.delete(snapGrp)
        pm.parent ('skirt1Bak_jnt', grpJnt)
        pm.parent (grpJnt, grpJntZro)
        #delete Grp Free
        pm.parent ('skirt1BakZro_grp', grpRig)
        pm.delete ('skirtRigBak_grp')

# Rig skirt Fnt RGT
        fkRig = nfk.FkRig(elem='skirt',
                side='FntRGT',
                jnts=(
                'skirt1FntRGT_tmpJnt',
                'skirt2FntRGT_tmpJnt',
                'skirt3FntRGT_tmpJnt',
                'skirt4FntRGT_tmpJnt',
                'skirt5FntRGT_tmpJnt'), 
                ctrlShp='circle')              
        fkRig.rig()
        grpFntRGT = pm.parent ('skirtRigFntRGT_grp' ,grpRGTRig)
        #groupOfJnt
        grpJnt = pm.group(em=True, n='skirtFntRGTJntZro_grp')
        snapGrp = pm.parentConstraint ('skirt1FntRGT_jnt', grpJnt, mo=False)
        pm.delete(snapGrp)
        pm.parent ('skirt1FntRGT_jnt', grpJnt)
        pm.parent (grpJnt, grpJntZro)

# Rig skirt  RGT
        fkRig = nfk.FkRig(elem='skirt',
                side='RGT',
                jnts=(
                'skirt1RGT_tmpJnt',
                'skirt2RGT_tmpJnt',
                'skirt3RGT_tmpJnt',
                'skirt4RGT_tmpJnt',
                'skirt5RGT_tmpJnt'), 
                ctrlShp='circle')              
        fkRig.rig()
        grpRGT = pm.parent ('skirtRigRGT_grp' ,grpRGTRig)
        #groupOfJnt
        grpJnt = pm.group(em=True, n='skirtRGTJntZro_grp')
        snapGrp = pm.parentConstraint ('skirt1RGT_jnt', grpJnt, mo=False)
        pm.delete(snapGrp)
        pm.parent ('skirt1RGT_jnt', grpJnt)
        pm.parent (grpJnt, grpJntZro)

# Rig skirt Bak 
        fkRig = nfk.FkRig(elem='skirt',
                side='BakRGT',
                jnts=(
                'skirt1BakRGT_tmpJnt',
                'skirt2BakRGT_tmpJnt',
                'skirt3BakRGT_tmpJnt',
                'skirt4BakRGT_tmpJnt',
                'skirt5BakRGT_tmpJnt'), 
                ctrlShp='circle')              
        fkRig.rig()
        grpBakRGT = pm.parent ('skirtRigBakRGT_grp' ,grpRGTRig)
        #groupOfJnt
        grpJnt = pm.group(em=True, n='skirtBakRGTJntZro_grp')
        snapGrp = pm.parentConstraint ('skirt1BakRGT_jnt', grpJnt, mo=False)
        pm.delete(snapGrp)
        pm.parent ('skirt1BakRGT_jnt', grpJnt)
        pm.parent (grpJnt, grpJntZro)

#parent LFT and RGT Side
        pm.parent(grpLFTRig, grpRig)
        pm.parent(grpRGTRig, grpRig)
#create group of mainJnt        
        grpJnt = pm.group(em=True, n='skirtCenZro_grp')
        snapGrp = pm.parentConstraint ('skirt_jnt', grpJnt, mo=False)
        pm.delete(snapGrp)
        pm.parent ('skirt_jnt', grpJnt)
        pm.parent(grpJnt, grpJntZro)
#delete_tmpJnt
        pm.delete('skirtFkTmpJnt_grp')

