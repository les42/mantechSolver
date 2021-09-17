class EquipmentDataObject:
    def __init__(self):
        self.tamCn            = -537   # THE TAMCN FOR THE EQUIPMENT
        self.equipmentRow     = None   #
        self.numRequested     = -537   # NUMBER OF PIECES REQUESTED
        self.readiness        = -537   # TRL VALUE
        self.suitabilty       = -537   # SUITABILITY
        self.executability    = -537   # EXECUTABILITY
        self.minAuthorized    = 1      # MINIMUM NUMBER OF PIECES THAT THE SOLUTION CAN FIND
         
        self.fundingList      = list() # LIST OF FundingDataObjects FOR THE EQUIPMENT