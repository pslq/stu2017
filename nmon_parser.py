#!/usr/bin/python3

import os, re, sys, copy, csv, itertools, gzip, locale,codecs
from datetime import datetime, date, time
from pymongo import MongoClient
from multiprocessing import Lock, Pool


def try_conv_complex(v) :
  try :
    return(int(v))
  except ValueError:
    try :
      return(float(v))
    except ValueError:
      try :
        return(complex(v))
      except ValueError:
        return(v)

# Convert dict keys to string
def convert_dict_keys_to_str(dict_to_conv) :
  if type(dict_to_conv) == dict :
    for k,v in dict_to_conv.items() :
      if type(v) == dict :
        convert_dict_keys_to_str(v)
      nv = v
      nk = str(k)
      del(dict_to_conv[k])
      dict_to_conv[nk] = nv

def mongo_try_insert_one(collection, dictionary) :
  ret = None
  try:
    ret = collection.insert_one(dictionary)
  except (pymongo.errors.DuplicateKeyError) as e :
    print(e)
  finally :
    return(ret)


def line_cleanup(f, split=False, delimiter='') :
  for line in f :
    if line :
      while "\t" in line or '  ' in line :
        line = line.replace("\t", ' ').replace('  ', ' ')
      line = line.strip(' ').rstrip("\n")

      if split == True :
        yield (line.split(delimiter))
      else :
        yield (line)

def pq_open_file(filename) :
  ret = None
  try :
    if filename != None : ret = codecs.open(filename, "r", encoding='utf-8', errors='ignore')
  finally :
    return(ret)



def nmon_parser(directory, paralel, mongodb_uri, mongodb_db) :
  if paralel == 1 :
    for dirs  in os.scandir(directory):
      if ( dirs.name.endswith(".nmon") or dirs.name.endswith(".nmon.gz") ) and dirs.is_file() :
        nmon_unpac([directory+"/"+dirs.name, mongodb_uri, mongodb_db])
  else :
    res = None
    with Pool(processes=paralel) as pool:
      for dirs  in os.scandir(directory):
        if ( dirs.name.endswith(".nmon") or dirs.name.endswith(".nmon.gz") ) and dirs.is_file() :
          res = pool.apply_async(nmon_unpac, [(directory+"/"+dirs.name, mongodb_uri, mongodb_db)])

      if res != None :
        res.wait()


def nmon_unpac(args) :
  f_name = args[0]
  mongodb_uri = args[1]
  mongodb_db = args[2]
  print("Parsing nmon file: "+f_name)
  if f_name.endswith(".gz")  :
    f = gzip.open(f_name, mode='rt')
  elif f_name.endswith(".nmon") : 
    f = pq_open_file(f_name)
  else :
    print("ERR...")

  if f != None :
    nmon_file(f, mongodb_uri, mongodb_db)
    f.close()



def nmon_file(fdpr, mongodb_uri, mongodb_db) :

  locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

  db_con = MongoClient(mongodb_uri)
  if db_con.server_info() != None and fdpr != None :
    db = db_con[mongodb_db]
    collection = db.nmon_stats

    basic_info = { "start_time" : None, "start_date" : None, "interval" : None, "snapshots" : None, "serial" : None, "lpar_id" : None, "host" : None, "runname" : None, "ent_capacity" : 0, "ent_vp" : 0 }
    dates = {}
    lpar_data = {}
    for sp in line_cleanup(fdpr, delimiter=",", split=True) :
      if sp[0] == "ZZZZ" :
        tm = None
        try :
          dates[sp[1]] = datetime.strptime(sp[3]+" "+sp[2], "%d-%b-%Y %H:%M:%S")
        except :
          dates[sp[1]] = None
      elif sp[0] == "AAA" :
        if sp[1] == "time" :
          basic_info["start_time"] = sp[2]
        if sp[1] == "date" :
          basic_info["start_date"] = sp[2]
        if sp[1] == "interval" :
          basic_info["interval"] = try_conv_complex(sp[2])
        if sp[1] == "snapshots" :
          basic_info["snapshots"] = sp[2]
        if sp[1] == "SerialNumber" :
          basic_info["serial"] = sp[2]
        if sp[1] == "LPARNumberName" :
          basic_info["lpar_id"] = try_conv_complex(sp[2])
        if sp[1] == 'host' :
          basic_info["host"] = sp[2]
        if sp[1] == "runname" :
          basic_info["runname"] = sp[2]

      elif sp[0] == "BBBL" :
        if sp[2] == "Entitled Capacity" :
          basic_info["ent_capacity"] = try_conv_complex(sp[3])
        elif sp[2] == "Logical CPU" :
          basic_info["ent_vp"] = try_conv_complex(sp[3])

      elif re.search("^PCPU_ALL$|^SCPU_ALL$|^CPU_ALL$|^LPAR$|^MEM$|^PROC$|^NET$|^NETPACKET$|^NETSIZE$|^NETERROR$|^IOADAPT$", sp[0]) != None :
        if sp[1].startswith("T") == True :
          tmp_add = { "TPOS" : sp[1] }
          for p in range(2, (len(sp)-1)) :
            if p-2 < len(lpar_data[sp[0]]["labels"]) :
              lb = lpar_data[sp[0]]["labels"][p-2]
              tmp_add[lb] = sp[p]
            else :
              print("ERROR Parsing: ")
              print(sp)
          lpar_data[sp[0]]["data"].append(tmp_add)
        else :
          if sp[0] not in lpar_data :
            lpar_data[sp[0]] = { "labels" : [], "data" : [] } 
            for p in range(2, (len(sp)-1)) :
              lpar_data[sp[0]]["labels"].append(sp[p])

    
    # Cleanup None Dates from ZZZZ fields
    if basic_info["start_time"] != None and basic_info["start_date"] != None and basic_info["interval"] != None :
      day, month, year = basic_info["start_date"].split("-")
      month = month.title()
      basic_info["date"] = datetime.strptime(day+" "+month+" "+year+" "+basic_info["start_time"].replace(".",":"), "%d %b %Y %H:%M:%S")

      if basic_info["date"] != None :
        for d in dates :
          if dates[d] == None :
            try :
              dates[d] = datetime.fromtimestamp(basic_info["date"].timestamp() + (try_conv_complex(d.lstrip("T"))*basic_info["interval"]))
            except :
              del(dates[d])

    if basic_info["date"] != None :
      # Insert date reference
      for l in lpar_data :
        for elm in lpar_data[l]["data"] :
          if elm["TPOS"] in dates : 
            elm["date"] = dates[elm["TPOS"]]
          else :
            del(elm)


      fd = collection.find_one({ "start_date" : basic_info["start_date"], "serial" : basic_info["serial"], "lpar_id" : basic_info["lpar_id"], "runname" : basic_info["runname"]  })
      if fd == None :
        convert_dict_keys_to_str(lpar_data)
        basic_info["stats"] = lpar_data
        day, month, year = basic_info["start_date"].split("-")
        month = month.title()
        basic_info["date"] = datetime.strptime(day+" "+month+" "+year+" "+basic_info["start_time"].replace(".",":"), "%d %b %Y %H:%M:%S")
        mongo_try_insert_one(collection, basic_info)

    db_con.close()


if __name__ == "__main__":
  directory = "/home/pqueiroz/clientes/IBM/STU_2017/dset/nmon"
  mongodb_uri = 'mongodb://localhost:27017'
  mongodb_db = 'stu2017'
  paralel = 1

  nmon_parser(directory, paralel, mongodb_uri, mongodb_db) 
