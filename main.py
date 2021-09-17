from numpy import empty, int32, true_divide
from pandas.core.frame import DataFrame
import psycopg2
import pandas as pd
import pandas.io.sql as psql
import math
import pickle

from PlanDataObject import PlanDataObject
from EquipmentDataObject import EquipmentDataObject
from FundingDataObject import FundingDataObject
# from SolverSynth import Solver
from Solver import Solver


def list_tables(conn):

    cursor = conn.cursor()
    cursor.execute("""SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'""")

    # file = open("/home/lengelbrecht/myfile.txt","w+")
    for table in cursor.fetchall():
        if ("countries" not in table[0].lower()):
            print_table(conn, table[0], file)
           # print(table)
    # file.close()

    return

def find_tableColumn(conn):

    cursor = conn.cursor()
    cursor.execute("""SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'""")

    for table in cursor.fetchall():
        tableFrame    = pd.read_sql('SELECT * from "'+ table[0] +'"', conn)
        for v in tableFrame.columns:
            if ("price" in v.lower()):
                print("------------------------------------------------------------")
                print("--   " + v + " " + table[0])
                print("------------------------------------------------------------")

    return

def print_table(conn, table_name, file):


    my_table    = pd.read_sql('SELECT * from "'+ table_name +'"', conn)
    #another_attempt= psql.read_sql("SELECT * FROM my-table-name", connection)

    print("------------------------------------------------------------")
    print("--   " + table_name)
    print("------------------------------------------------------------")
    print(my_table)
    print(" ")
    print(" ")

    # file.write("------------------------------------------------------------\n")
    # file.write("--   " + table_name + "\n")
    # file.write("------------------------------------------------------------\n")
    # file.write(str(my_table))
    # file.write(" \n")
    # file.write(" \n")

    return

def postgres_test(fiscalYear):

    try:
        pswd            = "GMTj6qBMW7"        
        hostname        = "10.186.188.40"
        # pswd            = input("pswd: ")
        sConnect        = "dbname='mantech_dev_db' user='veritone' host='{0}' password='{1}' connect_timeout=1 ".format(hostname, pswd)
        conn            = psycopg2.connect(sConnect)


        # GET THE FISCAL YEAR CODE
        sqlString       = 'SELECT * from "FiscalYear" where cast ("name" as int)='+str(int(fiscalYear))
        fy_DataFrame    = pd.read_sql(sqlString, conn)
        fiscalYearCode  = fy_DataFrame.iloc[0].ID

        # GET ALL OF THE PLANS
        plansDict       = dict()
        plansDataFrame  = pd.read_sql('SELECT * from "Plans"', conn)

        # GET ALL OF THE PRIORITIES
        prioritiesDict  = dict()
        prioritiesFrame = pd.read_sql('SELECT * from "PriorityWeight"', conn)
        for pri in prioritiesFrame.values:
            prioritiesDict[pri[0]] = pri[2]

        # GET ALL OF THE BASISES
        basisDict       = dict()
        basisFrame      = pd.read_sql('SELECT * from "PlanBasis"', conn)
        for basis in basisFrame.values:
            basisDict[basis[0]] = basis[8]

        neededEquipDict = dict()

        # LOOP OVER THE PLANS TO GET THE OWNING ORGANIZATION
        i      = 0
        kk     = 0
        nPlans = 0
        for plan in plansDataFrame.iloc:
            try:
                # print(plansDataFrame.values[i])

                planObject                = PlanDataObject()
                planFY                    = plan.fiscalYear
                if planFY != fiscalYearCode:
                    continue
                print("--- " + str(plan.ID))

                nPlans                   += 1
                planObject.fiscalYearCode = fiscalYearCode   
                if (plan.country != None):
                    break;

                planTemporalFrame         = pd.read_sql('SELECT * from "PlanTemporalPriorities" where "plan"='+str(int(plan.ID)), conn)
                pplt                      = pd.read_sql('SELECT * from "Plans_places_LINK_TABLE" where "Plans_ID_FROM"='+str(int(plan.ID)), conn)
                placeID                   = pplt.values[0][1]
                place                     = pd.read_sql('SELECT * from "Places" where "ID"='+str(int(placeID)), conn)
                countryID                 = place.country[0]
                theater                   = pd.read_sql('SELECT * from "Theater" where "theaterCommand"='+str(int(plan.theaterCommand)), conn)
                theaterID                 = theater.ID[0]
                theaterTemporalFrame      = pd.read_sql('SELECT * from "TheaterTemporalPriorities" where "theater"='+str(int(theaterID)), conn)
                countryTemporalFrame      = pd.read_sql('SELECT * from "CountryTemporalPriorities" where "country"='+str(int(countryID)), conn)

                theaterPW                 = prioritiesDict[plan.theaterPriority]
                theaterTemporalPW         = theaterTemporalFrame.weight

                countryPW                 = prioritiesDict[plan.countryPriority]
                countryTemporalPW         = countryTemporalFrame.weight

                planPW                    = prioritiesDict[plan.planPriority]
                if (len(planTemporalFrame.values) == 0):
                    planTemporalPW   = 0
                else:
                    planTemporalPW   = planTemporalFrame.values[0][4]


                execuProb                 = plan.probabilityOfExecution
                execuProbTemporalPW       = 1

                if (math.isnan(plan.tpfdd)):
                    tpfddPW          = 0
                else:
                    tpfddPW          = prioritiesDict[int(plan.tpfdd)]
                tpfddTemporalPW           = 1

                if (math.isnan(plan.planBasis)):
                    planBasis        = 0
                else:
                    planBasis        = basisDict[plan.planBasis]
                planBasisTemporalPW       = 1

                # planObject.priority       = (theaterPW * theaterTemporalPW   + 
                #                              countryPW * countryTemporalPW   +
                #                              planPW    * planTemporalPW      +
                #                              planBasis * planBasisTemporalPW +
                #                              execuProb * execuProbTemporalPW +
                #                              tpfddPW   * tpfddTemporalPW) / 0.6438
                planObject.priority       = (theaterPW * 0.4083   + 
                                             countryPW * 0.2417   +
                                             planPW    * 0.1583   +
                                             planBasis * 0.1028   +
                                             execuProb * 0.0611   +
                                             tpfddPW   * 0.0278) / 0.6438

                # print (plan.values)
                planObject.ID             = plan.ID
                planObject.name           = plan.uid

                organizationID            = plan.ownOrgId
                planDataIsGood            = False
                if not math.isnan(organizationID):

                    # GET THE ORG-TAMCN ROWS ASSOCIATED WITH THIS ORGANIZATION FROM THE OrganizationTamCns TABLE
                    sqlString    = 'SELECT * from "OrganizationTamCns" where "organization"='+str(int(organizationID))
                    ot_DataFrame = pd.read_sql(sqlString, conn)
                    
                    # print("------------------------------------------------------------")
                    # print("--- " + str(plan.ID))
                    # print("---  Organization: " + str(kk) + " " + str(organizationID))
                    # print("------------------------------------------------------------")
                    # print("--- " + sqlString)

                    for otElement in ot_DataFrame.iloc:
                        if not math.isnan(otElement.ID) and not math.isnan(otElement.tamCn):

                            # GET THE EQUIPMENT ROWS FOR THIS TAMCN VALUE FROM THE Equipments TABLE
                            tamCn          = otElement.tamCn
                            # if tamCn == 331:
                            #     print("   --- ")
                            sqlString      = 'SELECT * from "Equipments" where "tamCns"='+str(int(tamCn))
                            equipDataFrame = pd.read_sql(sqlString, conn)
                            # print("   --- " + sqlString)

                            
                            # GET EXECUTABILITY AND SUITABILITY
                            # print(f"mantech_plans_for_task_all_fields {fiscalYear} {organizationID} {tamCn}")
                            cursor = conn.cursor()
                            cursor.callproc('mantech_plans_for_task_all_fields', [str(int(fiscalYear)), "", "", None, None, str(int(organizationID)), str(int(tamCn)), '"phases" desc',])
                            result         = cursor.fetchall()
                            conn.commit()
                            if len(result) == 0:
                                continue
                            quantity       = otElement.authorized
                            # quantity       = result[0][2][0]
                            executability  = result[0][14][0]
                            suitability    = result[0][12][0]
                            print(f"executability: {executability} suitabliitiiy: {suitability}")
                            if (executability == None or suitability == None):
                                continue
                            # print(f"EEK")
                            # sqlString      = "SELECT * FROM  mantech_executability_score(%d)" % (int(tamCn)) 
                            # execDataFrame  = pd.read_sql(sqlString, conn)
                            # # GET SUITABILITY
                            # chunk_size = 10000
                            # offset = 0
                            # dfs = []
                            # sql = "SELECT * FROM  mantech_algorithms_details_by_tamcns_id(%d)" % (int(tamCn)) 
                            # cnum = 0
                            # for chunk in pd.read_sql(sql, con=conn, chunksize=10000000):
                            #     print(cnum)
                            #     # Start Appending Data Chunks from SQL Result set into List
                            #     dfs.append(chunk)
                            #     cnum += 1
                            # suit_DataFrame = pd.concat(dfs)
                            # # sqlString      = 'SELECT * from mantech_algorithms_details_by_tamcns_id(' + str(int(tamCn)) + ')'
                            # # suit_DataFrame = pd.read_sql(sqlString, conn)
                            # if suit_DataFrame.empty:
                            #     continue

                            # suitability    = suit_DataFrame.iloc
                            # for s in suit_DataFrame.iloc:
                            #     print(s)
                            #     print(" ")

                            # GET THE EQUIPMENT LIST FOR THIS ORGANIZATION
                            equipElementList = list()
                            for equipmentRow in equipDataFrame.iloc:
                                #print(equipElement)
                                edo                  = EquipmentDataObject()
                                edo.equipmentRow     = equipmentRow
                                edo.readiness        = equipmentRow.technologyReadinessLevel
                                edo.tamCn            = tamCn
                                edo.numRequested     = quantity
                                edo.suitabilty       = suitability
                                edo.executability    = executability
                                equipElementList.append(edo)

                                if tamCn not in neededEquipDict.keys():
                                    neededEquipDict[tamCn] = edo
                                # print("\n######### EQUIP: " + str(equipmentRow.values[7]) + " ID: " + str(equipmentRow.ID) + " TRL: " + str(equipmentRow.technologyReadinessLevel)+ " Multiplier: " + str(quantity))

                            # IF WE HAVE EQUIPMENT, GET THE TAMCN ROWS FOR THIS TAMCN VALUE FROM THE TamCns TABLE
                            if len(equipElementList) > 0:

                                sqlString       = 'SELECT * from "TamCns" where "ID"='+str(int(tamCn))
                                tamcnDataFrame  = pd.read_sql(sqlString, conn)
                                # print("   --- " + sqlString)

                                hasFundElements = False
                                for tamcnElement in tamcnDataFrame.iloc:

                                    # GET THE PROGRAM NUMBER
                                    programID        = tamcnElement.program
                                    # print("      programID: " + str(programID) + " tamcnElement.tamCnNumber: " + str(tamcnElement.tamCnNumber) + " .fiscalYear: " + str(tamcnElement.fiscalYear))

                                    if programID != None:
                                        # GET THE MCPC LIST ASSOCIATED WITH THE PROGRAM
                                        sqlString        = 'SELECT * from "McPcs_programs_LINK_TABLE" where "programs_ID_TO"='+str(int(programID))
                                        programDataFrame = pd.read_sql(sqlString, conn)
                                        # print("      --- " + sqlString)

                                        for programElement in programDataFrame.iloc:
                                            mcpcID = programElement.McPcs_ID_FROM
                                            # print("         mcpcID: " + str(mcpcID))

                                            if mcpcID != None:
                                                # GET THE FUNDING DISTRIBUTION LIST, GIVEN THE MCPC NUMBER, FROM THE LINK TABLE
                                                sqlString    = 'SELECT * from "McPcs_fundingDistributions_LINK_TABLE" where "McPcs_ID_FROM"='+str(int(mcpcID))
                                                mf_DataFrame = pd.read_sql(sqlString, conn)
                                                # print("         --- " + sqlString)

                                                for mf in mf_DataFrame.iloc:
                                                    fundingID = mf.fundingDistributions_ID_TO
                                                    # print("            fundingID: " + str(fundingID))

                                                    if fundingID != None:
                                                        # GET THE FUNDING DISTRIBUTION ROWS FOR THIS ID
                                                        sqlString        = 'SELECT * from "FundingDistributions" where "ID"='+str(int(fundingID))
                                                        fundingDataFrame = pd.read_sql(sqlString, conn)
                                                        # print("            --- " + sqlString)

                                                        j = 0
                                                        for fundingRow in fundingDataFrame.iloc:
                                                            if fundingRow.fiscalYear == fiscalYearCode:
                                                                # if fundingRow.appBillKind != None and fundingRow.fiscalYear == fiscalYearCode:
                                                                #     sqlString            = 'SELECT * from "AppBillKind" where "ID"='+str(int(fundingRow.appBillKind))
                                                                #     appBillKindDataFrame = pd.read_sql(sqlString, conn)
                                                                #     print("      ####===== FUND:" + str(j) + " program year:" + str(fundingRow.programYear) + " value:" + str(fundingRow.value) + 
                                                                #         " fiscalYear:" + str(fundingRow.fiscalYear) + " appBillKind:" + str(appBillKindDataFrame.iloc[0].values[2]))
                                                                for equipElement in equipElementList:
                                                                    fdo             = FundingDataObject()
                                                                    # fdo.appBillKind = appBillKindDataFrame.iloc[0].values[2]
                                                                    fdo.price       = fundingRow.value
                                                                    equipElement.fundingList.append(fdo)
                                                            
                                                                    j = j + 1

                                                        if j > 0:
                                                            hasFundElements = True

                                if hasFundElements:
                                    planObject.equipmentList.append(equipElementList)
                                    planDataIsGood = True

                if planDataIsGood:
                    plansDict[i] = planObject
                    i           += 1

                    # if i==110:
                    #     break
                kk += 1

            except Exception as error:
                print("YIKES:")
                print(error)

        conn.close()
        return plansDict, neededEquipDict

    except Exception as error:
        print(error)
        return None, None


# # MAIN PROGRAM
# datFile = "/home/lengelbrecht/.pickle/snalp.dat"
datFile = "/home/lengelbrecht/.pickle/snalpBig2.dat"
datFile = "/home/lengelbrecht/.pickle/snalpSmall.dat"

plansDict, neededEquipDict = postgres_test(2021)
# with open(datFile, 'wb') as handle:
#     pickle.dump(plansDict, handle, protocol=pickle.HIGHEST_PROTOCOL)   

# with open(datFile, 'rb') as handle:
#     plansDict = pickle.load(handle)  

print ("NUM PLANS:" + str(len(plansDict)))

solver                = Solver()
solver.solve(plansDict, .75)