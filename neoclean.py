from datetime import datetime as dt
import re
import math
import numpy as np
import pandas as pd
import parsejobs
pd.options.display.max_rows = 999
surveyDefaultBinaryQs = ["QID81 - ¿Está empleada/o actualmente?", "¿Sabe Usted lo que son las pruebas genéticas?", "¿Te has hecho una prueba genética alguna vez?", "Exámen de seno / Mamografía", "Exámen cervical / Papanicolao", "Exámen colorectal / Colonoscopía"]
surveyDefaultNumericQs = ["Por favor complete con sus datos: - Edad", "QID73 - ¿Hace cuántos años vive en los Estados Unidos?", "QID80 - ¿Cuántas personas viven con Usted?"]
id = "Por favor complete con sus datos: - Número de identificación del estudio"
post = "Por favor complete con sus datos: - Código Postal"

jobs = parsejobs.parseJobsTxt("jobs.txt")
class survey:
    def __init__(self,name):
        self.name = name.strip(".xlsx")
        self.read = pd.read_excel(name)
        self.merged = ""
        self.data = self.read.copy()
        self.changes = []
        self.flagged = []
        self.index = 0
        self.q = ""
    def logChange(self, qtype, init, reason=""):
        final = self.data.loc[self.index,self.q]
        rid = self.data.loc[self.index,id]
        if str(init).lower().strip("'") != str(final).lower().strip("'"):
            if final == "":
                final = "an empty string"
            self.changes.append(str(qtype).upper() + ": Replaced " + str(init) + " with " + str(final) + " at respondant with ID " + str(rid)+ " question " + str(init) + " " + reason)

    def validID(self,tmp, log=True):
        if re.search("[a-zA-Z]{2,3}\d{4}", str(tmp)):
            if log:
                self.flag("Possible ID")
            return 1
        else:
            return 0
    def flag(self, reason="invalid"):
        self.flagged.append([self.index, self.q, self.data.loc[self.index, self.q], reason])
    def cleanNumeric(self, q, index):
        self.index = index
        self.q = q
        tmp = self.data.loc[index,q]
        if self.validID(tmp):
            return
        elif isinstance(tmp, float) or isinstance(tmp, int) or str(tmp).isnumeric():
            return
        elif tmp == ".":
            self.data.loc[index,q] = ""
        else:
            self.data.loc[index,q] = self.data.loc[index,q].replace("O", "0")
            self.data.loc[index,q] = re.sub("\D", "", self.data.loc[index,q])
        self.logChange("numeric", tmp)
    def standardizeEmployment(self, q, index):
        for job in jobs:
            if self.data.loc[index,q] in job[1]:
                self.data.loc[index,q] = job[0]
                return 0
        return 1
    def cleanBinary(self, q, index):
        self.index = index
        self.q = q
        tmp = str(self.data.loc[index,q])
        if self.validID(tmp):
            return
        self.data.loc[index,q] = str(self.data.loc[index,q]).lower()
        if "no" in self.data.loc[index,q] or "desemplead" in self.data.loc[index,q] or "retirada" in self.data.loc[index,q] or "voluntari" in self.data.loc[index,q]: # check next col to see what job is, if none then no
            self.data.loc[index,q] = "no"
        elif "sí" in self.data.loc[index,q] or "si" in self.data.loc[index,q] or "emplead" in self.data.loc[index,q]:
            self.data.loc[index,q] = "si"
        else:
            self.flag()
        self.logChange("binary", tmp)
    def inferLoc(self,value): # do as suggestion- maybe write to a new suggestion file
        return 0
    #     if self.validID(value):
    #         return 1
    #     if re.search("\d{4}",str(value)):
    #         if self.data[self.idx,post] in SAC:
    #             return "SAC" + value
    #         elif self.data[self.idx,post] in LA:
    #            return "LA" + value
    #         elif self.data[self.idx,post] in SF:
    #            return "SF" + value
    #     return 0
    def cleanID(self, index): # fix pls
        self.index = index
        self.q =  "id"
        tmp = self.data.loc[index, id].upper().strip(" ")
        nloc = ""
        try:
            self.data.loc[index, id] = re.find("[a-zA-Z]{2,3}\d{4}").groups(0)
        except:
            self.flag()
        self.logChange("id", tmp)
    def removeDirectDupes(self):
        tmp= self.data
        self.data = self.data.drop_duplicates(b.columns.difference(["Response ID", "Duration (in seconds)", "Unnamed: 0", "Recorded Date", "Start Date", "End Date"]))
        if not self.data.equals(tmp):
            pass
        else:
            print("no direct duplicates!")
    def getDupePairs(self, dupes):
         pairs, group, nans = [], [], []
         tmp = ""
         for idx, row in dupes.iterrows():
             try:
                 if math.isnan(float(row[id])) or row[id] == "NaN":
                     nans.append(row)
             except:
                if row[id] == tmp or tmp == "":
                    pass
                else:
                    pairs.append(group)
                    group = []
                tmp = row[id]
         pairs.append(group)
         return pairs, nans
    def resolveRedoes(self): # just falg don't delete- deleting is bad when autmated cuz we don't rly know what it is
        dupes = self.data[self.data.duplicated(subset=[id, "IP Address"], keep=False)]
        print(dupes)
        pairs, nans = self.getDupePairs(dupes)
        for pair in pairs:
            idx = 0
            latest = 0
            best = pair[0]
            for b in pair:
                #if dt.strptime(str(b["End Date"]), "%Y-%m-%d %H:%M:%S") > dt.strptime(str(best["End Date"],"%Y-%m-%d %H:%M:%S")):
                if b["End Date"] > best["End Date"]:
                    latest = idx
                    best = b[idx]
                idx += 1
            n = 0
            for bruh in pair:
                if n == latest:
                    pass
                else:
                    self.data = self.data.drop(self.data[self.data == bruh].index)
                n += 1

    def resolveIdDupes(self):
         self.removeDirectDupes()
         dupes = self.data[self.data.duplicated(subset=[id], keep=False)].sort_values(by=[id])
         pairs, nans = self.getDupePairs(dupes)
         if pairs == [[]] and nans == []:
             print("No collisions detected!")
         else:
             if True: # currently just writing out collisions- not sure what Laura wants to do w resolving em
                dupes.to_excel(self.name + "_collisions.xlsx")
                print("Collisions written to " + self.name + "_collisions.xlsx")
             else:
                 choice = input(str(len(pairs)) + " duplicate pair(s) detected! Would you like to resolve them here? [y/N]\n")
                 if choice.lower() == "y" or choice.lower() == "yes":
                     if pairs != [[]]:
                         for pair in pairs:
                             print("Colliding id detected!")
                             n = 1
                             for bruh in pair:
                                 print("Respondant " + str(n) + ":")
                                 print(bruh)
                                 n += 1
                             choice = "N"
                             while not isinstance(choice, int):
                                try:
                                    choice = int(input("Which respondant would you like to keep?\n"))
                                    if choice > len(pair):
                                        print("Please input a valid respondant number!")
                                        choice = "N"
                                except:
                                    print("please input a number!")
                             n = 1
                             for bruh in pair:
                                 if n == choice:
                                     pass
                                 else:
                                     self.data = self.data.drop(self.data[self.data["Response ID"] == bruh["Response ID"]].index)
                                 n += 1
                     if not nans == []:
                         self.handlenanID(nans)
                 else:
                    print("ok! Please resolve them in the original input xlsx, and rerun this script!")
    def handlenanID(self, nans):
         print(str(len(nans)) + " nan ids detected!")
         n = 1
         for bruh in nans:
             print("Respondant " + str(n) + ":")
             print(bruh)
             n += 1
         choice = "N"
         while not isinstance(choice, int):
            try:
                choice = int(input("Which respondant would you like to keep?\n"))
                if choice > len(nans):
                    print("Please input a valid respondant number!")
                    choice = "N"
            except:
                print("please input a number!")
         n = 1
         for bruh in nans:
             if n == choice:
                 pass
             else:
                 self.data = self.data.drop(self.data[self.data["Response ID"] == bruh["Response ID"]].index)
             n += 1
    def merge(self, other):
        try:
            self.merged = self.data.merge(other.data, left_on=[id,post], right_on=[id,post], validate="1:1")
            print("merged!")
        except:
            print("Merge failed! Attempting to resolve collisions...")
            self.attemptResolvebyMerge(other)
    def attemptResolvebyMerge(self, other):
        self.resolveIdDupes(other=other.data)
        other.resolveIdDupes(other=self.data)
        try:
            self.data.merge(other.data, left_on=[id], right_on=[id], validate="1:1")
        except:
            print("fail")
    def cleanColumn(self, dtype, colname=""):
        if dtype.lower() == "binary":
            for idx, row in self.data.iterrows():
                self.cleanBinary(colname, idx)
        elif dtype.lower() == "numeric":
            for idx, row in self.data.iterrows():
                self.cleanNumeric(colname, idx)
        elif dtype.lower() == "id":
            for idx, row in self.data.iterrows():
                self.cleanID(idx)
        elif dtype.lower() == "job":
            for idx, row in self.data.iterrows():
                self.standardizeEmployment(colname, idx)
        else:
            print("Sorry! " + dtype + " is not a valid datatype. Please enter either binary, numeric, or id")
    def write(self):
        self.data.compare(self.read).to_excel(self.name + "_diff.xlsx")
        self.data.to_excel(self.name + "_cleaned.xlsx")
        if self.merged != "":
            self.merged.to_excel(self.name + "_merged.xlsx")
        if self.flagged != "":
            pd.DataFrame(self.flagged,columns=["Respondant", "question", "value"]).to_excel(self.name + "_flagged.xlsx")
        if self.changes != []:
            with open(self.name + "_changes.txt", "w") as f:
                for change in self.changes:
                    f.write("\n")
                    f.write(change)
