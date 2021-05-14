##
# @file MagicalDB.py
# @author Keren Zhu
# @date 06/27/2019
# @brief The database for the magical flow. Ideally it should include everything needed
#

import DesignDB
import magicalFlow
import json

class MagicalDB(object):
    def __init__(self, params):
        self.designDB = DesignDB.DesignDB()
        self.params = params
        self.digitalNetNames = ["clk"]
        self.techDB = magicalFlow.TechDB()

    def parse(self):
        self.parse_simple_techfile(self.params.simple_tech_file)
        self.parse_input_netlist(self.params)
        self.parse_placer_spacing(self.params.placer_spacing)
        self.designDB.db.findRootCkt() # After the parsing, find the root circuit of the hierarchy
        self.postProcessing()
        return True

    def postProcessing(self):
        self.markPowerNets()
        self.markDigitalNets()
        #self.computeCurrentFlow()

    def parse_simple_techfile(self, params):
        magicalFlow.parseSimpleTechFile( params, self.techDB)

    def parse_input_netlist(self, params):
        if (params.hspice_netlist is not None):
            self.read_hspice_netlist(params.resultDir+params.hspice_netlist)
            return
        if (params.spectre_netlist is not None):
            self.read_spectre_netlist(params.resultDir+params.spectre_netlist)
            return
        raise ParamException("No input netlist file!")

    def read_spectre_netlist(self, sp_netlist):
        self.designDB.read_spectre_netlist(sp_netlist, self.techDB)

    def read_hspice_netlist(self, sp_netlist):
        self.designDB.read_hspice_netlist(sp_netlist, self.techDB)

    def parse_placer_spacing(self, filename):
        dbu = self.techDB.units().dbu
        if filename is not None:
            with open(filename, 'r') as f:
                placer_spacing = json.load(f)
                print(placer_spacing)
                if "SAME_SPACING" in placer_spacing:
                    for layerName, spacing in placer_spacing["SAME_SPACING"].items():
                        self.techDB.addSameLayerSpacingRule(layerName, int(round(spacing * dbu)))
                if "N_WELL_LAYER" in placer_spacing:
                    self.techDB.setNwellLayerName(placer_spacing["N_WELL_LAYER"])
                self.placerSpacing = placer_spacing


    """
    Current & Signal Flow
    """
    def computeCurrentFlow(self):
        csflow = magicalFlow.CSFlow(self.designDB.db)
        for cktIdx in range(self.designDB.db.numCkts()):
            ckt = self.designDB.db.subCkt(cktIdx)
            if ckt.implType == magicalFlow.ImplTypeUNSET:
                csflow.computeCurrentFlow(ckt)
                with open(self.params.resultDir + ckt.name + '.sigpath','w') as f:
                    pinNamePaths = csflow.currentPinPaths();
                    cellNamePaths = csflow.currentCellPaths();
                    assert len(pinNamePaths) == len(cellNamePaths)
                    for i in range(len(pinNamePaths)):
                        assert len(pinNamePaths[i]) == len(cellNamePaths[i])
                        for j in range(len(pinNamePaths[i])):
                            f.write(cellNamePaths[i][j] + " " + pinNamePaths[i][j] + " ")
                        f.write("\n")
    """
    Post-processing
    """
    def markPowerNets(self):
        for cktIdx in range(self.designDB.db.numCkts()):
            ckt = self.designDB.db.subCkt(cktIdx)
            # using flags from body connections
            for psubIdx in range(ckt.numPsubs()):
                psubNet = ckt.psub(psubIdx)
                psubNet.markVssFlag()
            for nwellIdx in range(ckt.numNwells()):
                nwellNet = ckt.nwell(nwellIdx)
                nwellNet.markVddFlag()
            # Using external naming-based labeling
            vddNetNames = self.params.vddNetNames
            vssNetNames = self.params.vssNetNames
            for netIdx in range(ckt.numNets()):
                net = ckt.net(netIdx)
                if net.name in vddNetNames:
                    net.markVddFlag()
                if net.name in vssNetNames:
                    net.markVssFlag()
    def markDigitalNets(self):
        for cktIdx in range(self.designDB.db.numCkts()):
            ckt = self.designDB.db.subCkt(cktIdx)
            # Using external naming-based labeling
            digitalNetNames = self.params.digitalNetNames
            for netIdx in range(ckt.numNets()):
                net = ckt.net(netIdx)
                if net.name in digitalNetNames:
                    net.markDigitalFlag()
                else:
                    net.markAnalogFlag()

    """
    Some wrapper
    """
    def topCktIdx(self):
        """
        @brief Get the index of circuit graph of the hierarchy
        """
        return self.designDB.db.rootCktIdx()
    """
    utility
    """
    def implTypeStr(self, implType):
        if implType == magicalFlow.ImplTypeUNSET:
            return "UNSET"
        if implType == magicalFlow.ImplTypePCELL_Cap:
            return "PCELLL_CAP"
        if implType ==  magicalFlow.ImplTypePCELL_Res:
            return "PCELL_RES"
        if implType == magicalFlow.ImplTypePCELL_Nch:
            return "PCELL_NCH"
        if implType == magicalFlow.ImplTypePCELL_Pch:
            return "PCELL_PCH"
        return "UNKNOWN"
