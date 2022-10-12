from itertools import count, product, islice
from string import ascii_lowercase

import pymel.core as pm
import re, os, socket
from pprint import pprint
from nuTools import misc
from nuTools import naming
from nuTools import config

reload(misc)
class Renamer():
    def __init__(self):
        if pm.window('renamerMainWin', ex=True):
            pm.deleteUI('renamerMainWin')
        self.mainWin = pm.window('renamerMainWin', title='Renamer v1.3', s=False, mnb=True, mxb=False, w=255, h=350)
        self.mCol = pm.columnLayout(adj=True, rs=3, co=['both', 3])

        self.srRowCol = pm.rowColumnLayout(nc=2, co=[(1, 'left', 90), (2, 'left', 25)])
        self.srRadioCol = pm.radioCollection()
        self.srSelRadioButt = pm.radioButton(l='Selected', sl=True, cc=pm.Callback(self.uiChange,'scope'))
        self.srSceneRadioButt = pm.radioButton(l='Scene', sl=False)
        pm.setParent('..')

        self.hCol = pm.columnLayout(adj=True, co=['left', 95])
        self.heirachyChkBox = pm.checkBox(l='hierachy', v=False)
        pm.setParent('..')

        self.srNsRowCol = pm.rowColumnLayout(nc=2, co=[(1, 'left', 3), (2, 'left', 3)])
        self.srTxRowCol = pm.rowColumnLayout(nc=2, co=[(1, 'left', 3), (2, 'left', 3)])
        self.searchTxt = pm.text(l='Search: ')
        self.searchTxtFld = pm.textField(w=200)
        self.replaceTxt = pm.text(l='Replace: ')
        self.replaceTxtFld = pm.textField(w=200)
        pm.setParent('..')

        self.nsRemButt = pm.button(l='Remove all\nNamespace', bgc=[(0.0), (0.3), (0.3)], c=pm.Callback(self.getTargets, 'removeNameSpace'))
        pm.setParent('..')

        self.srButt = pm.button(l='Search and Replace',bgc=[(0.0), (0.5), (0.0)], h=38, c=pm.Callback(self.getTargets,'searchReplace'))

        self.lrRowCol = pm.rowColumnLayout(nc=3, co=[(1, 'left', 7), (2, 'left', 7), (3, 'left', 7)])
        self.lrButt = pm.button(l='LFT / RGT', h=28, bgc=[(0.15), (0.1), (0.3)], c=pm.Callback(self.getTargets, 'LR'), w=100)
        self.lrButt = pm.button(l='UPR / LWR', h=28, bgc=[(0.15), (0.1), (0.3)], c=pm.Callback(self.getTargets, 'UL'), w=100)
        self.lrButt = pm.button(l='FRT / BCK', h=28, bgc=[(0.15), (0.1), (0.3)], c=pm.Callback(self.getTargets, 'FB'), w=100)
        self.titleButt = pm.button(l='TITLE', h=28, bgc=[(0.15), (0.1), (0.3)], c=pm.Callback(self.getTargets, 'TI'), w=100)
        self.upperCaseButt = pm.button(l='UPPER', h=28, bgc=[(0.15), (0.1), (0.3)], c=pm.Callback(self.getTargets, 'UC'), w=100)
        self.lowerCaseButt = pm.button(l='LOWER', h=28, bgc=[(0.15), (0.1), (0.3)], c=pm.Callback(self.getTargets, 'LC'), w=100)
        pm.setParent('..')

        self.reRowCol = pm.rowColumnLayout(nc=3, co=[(1, 'both', 3), (2, 'both', 3), (3, 'both', 3)], rs=(1, 3))
        self.prefixTxt = pm.text(l='Prefix')
        self.elemTxt = pm.text(l='Element')
        self.suffixTxt = pm.text(l='Suffix')
        self.prefixTxtFld = pm.textField(w=85)
        self.elemTxtFld = pm.textField(w=155)
        self.suffixTxtFld = pm.textField(w=65)
        self.prefixAddButt = pm.button(l='Add\nPrefix', bgc=[(0.0), (0.2), (0.3)], c=pm.Callback(self.getTargets,'addPrefix'))
        self.elementButt = pm.button(l='Rename', h=38, bgc=[(0.0), (0.5), (0.0)], c=pm.Callback(self.getTargets,'rename'))
        self.suffixAddButt = pm.button(l='Add\nSuffix', bgc=[(0.0), (0.2), (0.3)], c=pm.Callback(self.getTargets,'addSuffix'))
        pm.setParent('..')

        self.lrRowCol = pm.columnLayout(adj=True, co=['left', 250])
        self.autoSuffixButt = pm.button(l='Auto Suffix', h=30, bgc=[(0.0), (0.3), (0.3)], c=pm.Callback(self.getTargets,'autoSuffix'))
        
        pm.setParent('..')

        self.sep01 = pm.separator()

        
        
        self.rnRowCol = pm.rowColumnLayout(nc=2, co=[(1, 'left', 98), (2, 'left', 50)])
        self.hashTxt = pm.text(l='number #')
        self.atTxt = pm.text(l='alphabet @')
        # self.rnRadioCol = pm.radioCollection()
        # self.rnHashNumRadioButt = pm.radioButton(l='Number#', sl=True)
        # self.rnHashAlRadioButt = pm.radioButton(l='Alphabet@')
        pm.setParent('..')

        self.rnRowCol = pm.rowColumnLayout(nc=6, co=[(1, 'left', 20), (2, 'left', 3), (3, 'left', 5), (4, 'left', 3), (5, 'left', 45), (6, 'left', 3)])
        self.numStartTxt = pm.text(l='start')
        self.numStartIntFld = pm.intField(w=22, v=1)
        self.padTxt = pm.text(l='padding')
        self.padIntFld = pm.intField(w=35, v=2)
        self.capitalChkBox = pm.checkBox(l='Upper Case', v=True)
        pm.setParent('..')

        self.sepRowCol = pm.rowColumnLayout(nc=2, co=[(1, 'left', 75), (2, 'left', 3)])
        self.sepTxt = pm.text(l='Seperator:')
        self.sepTxtFld = pm.textField(w=85, tx='_')
        pm.setParent('..')

        pm.showWindow()

    def uiChange(self, operation):

        if self.srSelRadioButt.getSelect() == True:
            self.heirachyChkBox.setEnable(True)
        else:
            self.heirachyChkBox.setEnable(False)

    def getTargets(self, operation):
        rets = []
        hei = self.heirachyChkBox.getValue()

        # selected radio button selected
        if self.srSelRadioButt.getSelect() == True:
            sels = misc.getSel(selType='any', num='inf')
            # get all children under hierachy
            if self.heirachyChkBox.getValue() == True:
                alIter = self.multiletters(ascii_lowercase)
                for s in sels:
                    rets = pm.listRelatives(s, ad=True, typ='transform', ni=True)
                    if rets:
                        rets = rets[::-1]
                    rets.insert(0, s)
                    alp = alIter.next()
                    self.caller(rets, operation, alpahbet=alp)
                return
            else: # only do selection
                self.caller(sels, operation)    
        else: # scene radio button selected
            self.caller(pm.ls(), operation)


    def caller(self, rets, operation, alpahbet=None):
        # print rets
        if operation == 'searchReplace':
            self.searchReplace(rets)
        elif operation == 'rename':
            self.rename(rets, alpahbet)
        elif operation == 'addSuffix':
            self.addSuffix(rets, alpahbet)
        elif operation == 'addPrefix':
            self.addPrefix(rets, alpahbet)
        elif operation == 'autoSuffix':
            self.autoSuffix(rets)
        elif operation == 'LR':
            self.flipPosition(rets, operation)
        elif operation == 'UL':
            self.flipPosition(rets, operation)
        elif operation == 'FB':
            self.flipPosition(rets, operation)
        elif operation == 'TI':
            self.toTitle(rets)
        elif operation == 'UC':
            self.toUpper(rets)
        elif operation == 'LC':
            self.tolower(rets)
        elif operation == 'removeNameSpace':
            self.removeNameSpace(rets)

    def toTitle(self, rets):
        for obj in rets:
            name = obj.nodeName().title()
            obj.rename(name)

    def toUpper(self, rets):
        for obj in rets:
            name = obj.nodeName().upper()
            obj.rename(name)

    def tolower(self, rets):
        for obj in rets:
            name = obj.nodeName().lower()
            obj.rename(name)

    def removeNameSpace(self, rets):
        i = 0
        f = 0
        for obj in rets:
            objName = obj.nodeName()
            nameSplits = objName.split(':')
            if len(nameSplits) > 1:
                newName = nameSplits[-1]
                f += 1
                try:
                    obj.rename(newName)
                    i += 1
                except:
                    pass
        print '\n%s  nameSpace(s) found,  %s  removed.' %(f, i),    

    def searchReplace(self, rets):
        searchTxt = self.searchTxtFld.getText().replace(' ', '')
        searchFor = searchTxt.split(',')

        replaceTxt = self.replaceTxtFld.getText().replace(' ', '')
        replaceWith = replaceTxt.split(',')
        i = 0

        srs = zip(searchFor, replaceWith)

        for obj in rets:
            objName = obj.nodeName()
            newName = ''
            for sr in srs:
                if sr[0] in objName:
                    newName = objName.replace(sr[0], sr[1])
                    objName = newName
            try:
                obj.rename(newName)
                i += 1
            except:
                pass
        print '\n%s  matching found, %s renamed.' %(len(rets), i),

    def autoSuffix(self, rets): 
        sep = self.sepTxtFld.getText()
        r = 0
        for i in rets:
            suffix = misc.getSuffix(i)
            if not i.nodeName().endswith('%s%s' %(sep, suffix)):
                newName = '%s%s%s' %(i.nodeName(), sep, suffix)
            else:
                continue
            try:
                i.rename(newName)
                r+=1
            except:
                pass
        print '\nAuto suffix added to  %s  out of  %s.' %(r, len(rets)),

    def flipPosition(self, rets, op):        
        r = 0
        result = []
        for i in rets:
            ret = self.doFlip(i, op)
            if ret:
                r+=1

        print '\n%s out of  %s  positions has been flipped.' %(r, len(rets)),

    def doFlip(self, obj, op):
        if op == 'LR':
            posDict = {"Lft":"Rht", "_Lft_":"_Rgt_", "LFT":"RGT", "_lf_":"_rt_", "L_":"R_"}
        elif op == 'UL':
            posDict = {"Up":"Lo", "_Up_":"_Lo_", "UP":"LO", "UPR":"LWR", "uppr":"lowr"}
        elif op == 'FB':
            posDict = {"Fr":"Bk", "_Fr_":"_Bk_", "Frn":"Bck", "FRT":"BCK", "_fr_":"_bk_", "fnt_":"bck_"}

        oldName = obj.nodeName().rstrip('1234567890')
        # mname = re.search(r"(\d+$)", oldName)
        # try:
        #   endDigit = mname.group()
        #   oldName = oldName.replace(endDigit, '')
        # except:
        #   pass
        doRename = False
        for k, v in posDict.iteritems():
            if k in oldName:
                newName = oldName.replace(k, v)
                doRename = True
            elif v in oldName:
                newName = oldName.replace(v, k)
                doRename = True
            if doRename:
                pm.rename(obj, newName)     
                return True

    def multiletters(self, seq):
        for n in count(1):
            for s in product(seq, repeat=n):
                yield ''.join(s)

    def rename(self, rets, alpahbet=None):
        nameTxt = self.elemTxtFld.getText()
        padding = self.padIntFld.getValue()
        if not alpahbet:
            letters = self.multiletters(ascii_lowercase)
        n = self.numStartIntFld.getValue()
        i, s = 0, 0
        for i in range(len(rets)):
            num = str(n).zfill(padding)
            newName = nameTxt.replace('#', num)
            if not alpahbet:
                alp = letters.next()
            else:
                alp = alpahbet
            if self.capitalChkBox.getValue() == True:
                alp = alp.upper()
            newName = newName.replace('@', alp)
            n += 1
            try:
                rets[i].rename(newName)
                s += 1
            except:
                continue
            

        print '\nRenamed %s out of %s object(s)' %(s, len(rets)),

    def addPrefix(self, rets, alpahbet=None):
        prefixTxt = self.prefixTxtFld.getText()
        sep = self.sepTxtFld.getText()
        padding = self.padIntFld.getValue()
        if not alpahbet:
            letters = self.multiletters(ascii_lowercase)
        n = self.numStartIntFld.getValue()
        i, s = 0, 0
        for i in range(len(rets)):
            oldName = rets[i].nodeName()
            num = str(n).zfill(padding)
            prefix = prefixTxt.replace('#', num)
            if not alpahbet:
                alp = letters.next()
            else:
                alp = alpahbet
            if self.capitalChkBox.getValue() == True:
                alp = alp.upper()
            prefix = prefix.replace('@', alp)
            n += 1
            try:
                rets[i].rename('%s%s%s' %(prefix, sep, oldName))
                s += 1
            except:
                continue
            
        print '\nPrefix added  %s  out of  %s.' %(s, len(rets)),

    def addSuffix(self, rets, alpahbet=None):
        suffixTxt = self.suffixTxtFld.getText()
        padding = self.padIntFld.getValue()
        sep = self.sepTxtFld.getText()
        if not alpahbet:
            letters = self.multiletters(ascii_lowercase)
        n = self.numStartIntFld.getValue()
        i, s = 0, 0
        for i in range(len(rets)):
            oldName = rets[i].nodeName()
            num = str(n).zfill(padding)
            suffix = suffixTxt.replace('#', num)
            if not alpahbet:
                alp = letters.next()
            else:
                alp = alpahbet
            if self.capitalChkBox.getValue() == True:
                alp = alp.upper()
            suffix = suffix.replace('@', alp)
            n += 1
            try:
                rets[i].rename('%s%s%s' %(oldName, sep, suffix))
                s += 1
            except:
                continue
            
        print '\nSuffix added  %s  out of  %s.' %(s, len(rets)),


