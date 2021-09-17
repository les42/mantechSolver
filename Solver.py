from TimeIt import TimeIt
from PlanDataObject import PlanDataObject
from EquipmentDataObject import EquipmentDataObject
from FundingDataObject import FundingDataObject
from ExpEval import ExpEval

import random
import math
import array as arr
import nvsympy as nsp
import numpy as np
import sympy as sp
from nvtranslate import derive_by_array, lambdify, Function, Symbol
from scipy.sparse import (
    block_diag,
    diags,
    eye,
    csr_matrix,
)

nMax_k_Iterations = 10000
nMax_L_Iterations = 100
tinyDelta         = 0.003

def newtonRaphsonSolver (symbolsList: list, lambda_L, lambda_gradient, lambda_hessian, 
                         qk, Q_Zero, M, alpha, beta, symbolsArray, objectivePriceByX,
                         planPriorityAcceptAll_Tolerance):
    alpha  = 7
    beta   = .82
    eta    = .001254 

    iii = 0
    totRisk = 0
    for q in qk:
        lambda_Risk = sp.lambdify([symbolsArray], symbolsList[iii][4])
        totRisk    += lambda_Risk(qk)
        iii+=1
    print (f"Initial total risk = { totRisk }")

    with TimeIt("Lambdify L"):
        Q_l             = Q_Zero
        k               = 0
        innerL          = 0
        prevQsum        = 0
        while k < nMax_k_Iterations:
            gradient = lambda_gradient(qk)
            # print(f"k={k}")

            MTM         = np.matmul(M, M)
            l           = 0
            while l < nMax_L_Iterations:
                step        =  - alpha * eta * np.matmul(MTM, Q_l) + eta * M
                # if k == 2 and l == 96:
                #     print(f"  l={l}")
                Q_lplus1    = Q_l + step 
                delta_Q     = np.linalg.norm(step,2)
                Q_l         = Q_lplus1
                if delta_Q < 0.001: #sqrt(epsilon):
                    break
                l          += 1
                innerL += l 

            # UPDATE qk+1 AND TEST 
            q_kplus1 = qk - beta * np.matmul(Q_l, gradient)
            diff     = qk - q_kplus1
            delta_q  = np.linalg.norm((diff),2)
            # print(f"k={k} {qk}")
            qsum = 0
            for i in range(len(diff)):
                qsum += diff[i]
            # print(f"delta_q= {delta_q} k= {k} qsum= {qsum}")
            if delta_q < tinyDelta or prevQsum > qsum:
                break

            # TEST FAILED, FIND THE HESSIAN INVERSE APPROXIMATION (Q)
            # ITERATE
            prevQsum = qsum
            qk       = q_kplus1
            k       += 1
            M        = lambda_hessian (qk)
            M        = np.array(M)

            # iii      = 0
            # totRisk = 0
            # for q in qk:
            #     p           = int(q+0.5)
            #     lambda_Risk = sp.lambdify([symbolsArray], symbolsList[iii][4])
            #     totRisk    += lambda_Risk(qk)
            #     iii+=1
            # print (f"total risk = { totRisk }")

           

        # t1 = time.time()
        print(" ")
        print("------ NEWTON-RAPHSON NEW AND IMPROVED ")
        print("inner multiplies= ",innerL," Iterations = " + str(k) + ", alpha = " + str(alpha) + ", beta = " + str(beta))
        iii      = 0
        price    = 0
        oldPrice = 0
        totRisk  = 0
        prevPlan = None
        for q in qk:
            p         = int(q+0.5)
            if (symbolsList[iii][9].priority >= planPriorityAcceptAll_Tolerance):
                p = symbolsList[iii][2]

            lambda_Risk = sp.lambdify([symbolsArray], symbolsList[iii][4])

            if (symbolsList[iii][9] != prevPlan):
                print("-----------------------------------------------------------\n")


                print("-----------------------------------------------------------")
                prevPlan = symbolsList[iii][9]
                print(f"---  Plan ID: {prevPlan.ID}   UID: {prevPlan.name} Priority: {prevPlan.priority}")
            # print(f"       symbol = {symbolsList[iii][0]}\t \tpriority= {symbolsList[iii][5]:.5f}\t suitability= {symbolsList[iii][6]:.5f} \t TRL= {symbolsList[iii][7]:.5f} \t executability= {symbolsList[iii][8]:.5f}\tinitial= {symbolsList[iii][1]}\tr= {symbolsList[iii][2]}\tsol= {p}")
            
            equipmentItem = symbolsList[iii][10]
            print(f"---      Equipment:  tamCn = {int(equipmentItem.tamCn):06d}   " + 
                                      f" suit= {symbolsList[iii][6]:.5f}  " + 
                                      f" TRL= {symbolsList[iii][7]:.5f}   " + 
                                      f" exec= {symbolsList[iii][8]:.5f}  " + 
                                    #   f" unitPrice= {int(symbolsList[iii][3] + 0.5):010d}\t" + 
                                      f" unitPrice= {symbolsList[iii][3]:.5f}\t\t" + 
                                      f" REQ= {symbolsList[iii][2]:03d}  " + 
                                      f" SLN= {p:03d}" + 
                                      f" --- {equipmentItem.equipmentRow.values[7]}\t")

            price    += p * symbolsList[iii][3]
            oldPrice += symbolsList[iii][2] * symbolsList[iii][3]
            iii += 1
            totRisk    += lambda_Risk(qk)

        print("-----------------------------------------------------------")
        print (f"final total risk = { totRisk }")
        print (f"old price =========> {int(oldPrice)}") 
        print (f"new price =========> {int(price)}") 

        lambda_Price = sp.lambdify([symbolsArray], objectivePriceByX)
        print(f"\nlambda_Price = {lambda_Price(qk)}")

def applyNetwonRaphsonFunction(
    equationSymbolsDict: dict,
    symbolsList: list,
    lagrangian: Function,
    objectivePriceByX,
    planPriorityAcceptAll_Tolerance
):

    # nMaxIterations = 1000

    # # GET THE VECTORS INTO qk WITH INITIALIZATIONS
    qkInit          = np.array(list(equationSymbolsDict.values()))
    particleEpsilon = 0.001
    
    qk_set          = np.array(qkInit)
    symbolsArray    = np.array(list(equationSymbolsDict.keys()))

    print("# symbols", len(symbolsArray))
    print(equationSymbolsDict)

    # LAGRANGIAN
    L               = lagrangian
    print(L)

    # GRADIENT OF LAGRANGIAN
    # gradLDict = dict()
    # hessLDict = dict()
    # iii = 0
    # with TimeIt("Compute grad(L)"):
    #     for symbol in symbolsArray:
    #         gL                = (sp.derive_by_array(L, symbol))
    #         gradLDict[symbol] = gL
    #         lambda_L = sp.lambdify([symbolsArray], gL)
    #         LL       = lambda_L(qkInit)
    #         print(iii)
    #         print(LL)

    #         iii += 1
        # # print(L)
        # #gradL      = derive_by_array(L, symbolsArray)#equationSymbolsDict.keys())
    gradLSYMPY = sp.derive_by_array(L, symbolsArray)

    # strMath = str(gradLSYMPY)
    # for symbol in equationSymbolsDict.keys():
    #     strMath = strMath.replace(str(symbol), str(equationSymbolsDict[symbol]))
    # print("\n gradLSYMPY")
    # print(strMath)

    # gradLSYMPY = sp.simplify(gradLSYMPY)
    # i   = 0
    # for g in gradL.exprs:
    #     e     = str(g).replace("^", "**")
    #     spexp = sp.parse_expr(e)
    #     print(f" nv-------------{i}")
    #     print(g)
    #     # spexp = spexp.simplify()
    #     print(f" sp-------{i}-")
    #     print(gradLSYMPY[i])
    #     i += 1


    # HESSIAN OF GRADIENT
    with TimeIt("Compute Hessian"):
        # hessianF = derive_by_array(gradL, symbolsArray)
        hessianF   = sp.derive_by_array(gradLSYMPY, symbolsArray)
        

    # LAMBDIFY: LAGRANGIAN, GRADIENT AND HESSIAN
    with TimeIt("Lambdify L"):
        # lambda_L = lambdify([symbolsArray], L)
        lambda_L = sp.lambdify([symbolsArray], L)
    with TimeIt("Lambdify grad(L)"):
        # lambda_gradient = lambdify([symbolsArray], gradL)
        lambda_gradient = sp.lambdify([symbolsArray], gradLSYMPY)
    with TimeIt("Lambdify Hessian"):
        lambda_hessian = sp.lambdify([symbolsArray], hessianF)

    # LL     = lambda_L(qkInit)
    M      = lambda_hessian (qkInit)
    M      = np.array(M)
    Q_Zero = M

    alpha  = 1
    beta   = 1

    v      = newtonRaphsonSolver(symbolsList, lambda_L, lambda_gradient, lambda_hessian, 
                                 qk_set, Q_Zero, M, alpha, beta, symbolsArray, objectivePriceByX, 
                                 planPriorityAcceptAll_Tolerance)

    return

class Solver:
    def solve(self, plans:dict, planPriorityAcceptAll_Tolerance):
        with TimeIt("Compute Total Lagrangian"):
            random.seed(537)
            epsilonVal1        = 5
            epsilonVal2        = 5
            epsilonVal3        = 5
            alpha              = 4.84215 
            beta               = .0985
            symbolsDict        = dict()
            symbolsList        = list()
            riskTotal          = 0 # nsp.Constant(0)
            planIndex_k        = 0
            constraintsList    = list()
            toa                = 0

            # GET PRIORITY MIN/MAX FOR PRIORITY NORMALIZATION 
            pTot               = 0
            pMin               = 4242424242
            pMax               = 0
            for key in plans.keys():
                pMin = min(pMin, plans[key].priority)
                pMax = max(pMax, plans[key].priority)


            # LOOP OVER THE PLANS
            sumXik = 0
            sumYik = 0
            iii    = -1
            objectivePriceByX  = 0  
            for key in plans.keys():
                plan           = plans[key]
                iii += 1
                # if (iii % 10 != 0):
                # #if (iii == 20):
                #     continue
                # NORMALIZE PRIORITY
                # if (pMin != pMax):
                #     priorityReq = (plan.priority - pMin) / (pMax - pMin)
                # else:
                priorityReq        = plan.priority # 0.2 * planIndex_k + 0.00001 # plan.priority
 
                s                  = float(priorityReq) 
                Uk                 = 1# * (planIndex_k + 1)

                planCost           = 0
                risk_k             = 0  
                equipIndex_i       = 0 
                objective          = 0  
                for equipmentElementList in plan.equipmentList:
                    elementIndex_n = 0 
                    for equipmentElement in equipmentElementList: 
                        u       = float(equipmentElement.suitabilty)    #float(synthSuit)  
                        r       = float(equipmentElement.readiness)     #float(synthRdy) 
                        e       = float(equipmentElement.executability) #float(synthExec)
                        if (math.isnan(u) or math.isnan(r) or math.isnan(e)):
                            continue
                        yikn    = equipmentElement.numRequested 
                        yiknMin = equipmentElement.minAuthorized
                        sumYik += yikn

                        xikn    = sp.Symbol(f"X_i{equipIndex_i:03d}_{elementIndex_n:03d}_k{planIndex_k:03d}") 
                        symbolsDict[xikn] = float(yikn * .75)
                        sumXik += xikn

                        constraintsList.append((1, yikn - xikn + epsilonVal2))
                        # constraintsList.append((1, xikn - yiknMin))
                        constraintsList.append((1, xikn + epsilonVal3))
                        
                        price              = 0
                        for funding in equipmentElement.fundingList:
                            price += funding.price

                        toa               += price
                        planCost          += price
                        
                        unitPrice          = price / yikn
                        v                  = (r * u * e * s)
                        risk_k             = (yikn * v / (yikn - xikn + epsilonVal1)) # - epsilonVal1 * float(random.randrange(1,9)))) # (v / ((yikn - (zikn + xikn))))

                        symbolsList.append((xikn, symbolsDict[xikn], yikn, unitPrice, risk_k, s, u, r, e, plan, equipmentElement))

                        objectivePriceByX += unitPrice * (xikn) # + zikn)
                        objective         += (alpha * unitPrice * (xikn) + beta * risk_k)
                        # constraintsList.append((Uk, objective))

                        elementIndex_n    += 1

                    equipIndex_i   += 1


                # Z              = sp.Symbol('minimiZe' + str(planIndex_k))
                # symbolsDict[Z] = planCost
                # symbolsList.append((Z, symbolsDict[Z], toa, 0, 0, 0, 0, 0, 0, 0, 0))
                # objective     -= Z
                constraintsList.append((Uk, objective))

                planIndex_k   += 1
                
            # THE OBJECTIVE CONSTRAINT    
                                   
            # objConstraint  = -sp.log(alpha * objectivePart1 + beta * objectivePart2 - Z)
            objConstraint  = 0 #-sp.log(objective - Z)# * float(random.randrange(1,9)))


            # BUDGET CONSTRAINTS
            # constraintsList.append((1, objectivePriceByX - toa))

            # ADD IN THE CONSTRAINTS
            for constraint in constraintsList:
                objConstraint      -= constraint[0] * sp.log(constraint[1])
            # objConstraint -= sp.log(Z)

            print("\n objConstraint: ")
            print(objConstraint)

            # strMath = str(objConstraint)
            # for symbol in symbolsDict.keys():
            #     strMath = strMath.replace(str(symbol), str(symbolsDict[symbol]))
            # print("\n ")
            # print(strMath)
        # -----------------------------------------------------
        # APPLY NEWTON RAPHSON SOLVER
        with TimeIt("applyNetwonRaphsonFunction"):
            applyNetwonRaphsonFunction(symbolsDict, symbolsList, objConstraint, objectivePriceByX, planPriorityAcceptAll_Tolerance)
