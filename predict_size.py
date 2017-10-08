#!/usr/bin/python3
from pymongo import MongoClient
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import math
import tensorflow as tf
from datetime import date,datetime

#### Parameters
learn_rate = 0.001
samples = 100000
mongodb_uri = 'mongodb://localhost:27017'
mongodb_db  = "stu2017"

def normalize(V) :
  return(tf.divide(tf.subtract(V, V.mean()), V.max() - V.min()))



def calc_mb(X,Y) :
  M_   = tf.Variable(tf.random_uniform([1], -1, 1, dtype="float32"))
  b_   = tf.Variable(tf.random_uniform([1], -1, 1, dtype="float32"))
  rate = tf.Variable(learn_rate)

  M, b = 0, 0

  hyp = tf.add(tf.multiply( normalize(Y),  M_),b_)

  cost = tf.reduce_mean(tf.square(hyp - Y))

  optimizer = tf.train.GradientDescentOptimizer(learn_rate)

  train = optimizer.minimize(cost)

  init = tf.global_variables_initializer()

  prev = 0

  with tf.Session() as sess :
    sess.run(init)

    for step in range(samples):
      sess.run(train)

    M, b = sess.run(M_), sess.run(b_)
  return(M,b)




db_con = MongoClient(mongodb_uri)
if db_con.server_info() != None :
  mongo_db = db_con[mongodb_db]

  core_usage = {}
  data_usage = []

  collection = mongo_db.nmon_stats

  docs = collection.find(projection={'stats.CPU_ALL.data' : 1, 'stats.LPAR.data' : 1 })

  for d in docs :
    if "LPAR" in d["stats"] :
      for lp in d["stats"]["LPAR"]["data"] :
        core_usage[lp["date"].timestamp()]=  float(lp['PhysicalCPU'])

      for lp in d["stats"]["CPU_ALL"]["data"] :
        data_usage.append({"date" : lp["date"].timestamp(), "use" : float(lp['Sys%']) +  float(lp['Wait%']) + float(lp['User%']) })

  for d in data_usage :
    d["pc"] = core_usage[d["date"]]


  docs = collection.aggregate([ { '$group' : { '_id' : { 'ent_max' : { '$max' : '$ent_capacity' } } }} ])
  ent_max = docs.next()['_id']['ent_max']

  print(ent_max)



  # Make the Pandas DataFrame
  Xs = pd.DataFrame.from_dict(data_usage, dtype=np.float32)

  PC = Xs["pc"].as_matrix()
  DT = Xs["date"].as_matrix()
  US = Xs["use"].as_matrix()

  # y = mx+b

  m,b = calc_mb(US,DT)

  # 95% usage of CPU ( estimate max date for saturation )
  max_use_dt = m*95+b

  m,b = calc_mb(PC,DT)

  # Estimated date to use 100% of the cores
  max_pc_dt = m*ent_max+b

  # Estimated amount of cores when use reach 95%
  est_pc_us_95 = max_use_dt - b / m

  print("Data da primeira amostragem : "+str(datetime.fromtimestamp(DT.min())))
  print("Data da ultima amostragem : "+str(datetime.fromtimestamp(DT.max())))

  print("Data estimada para 100% do Entitled Capacity : "+str(datetime.fromtimestamp(max_pc_dt)))
  print("Data estimada para 95% de CPU : "+str(datetime.fromtimestamp(max_use_dt)))
  print("Quantidade estimada de cores para quando o servidor estiver com 95% de uso : "+str(est_pc_us_95))



  docs.close()
  db_con.close()
else :
  print("Erro no banco")
