kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-larissa-do-nothing exec -it pod/freqtrade-bot-larissa-do-nothing-57877f7948-6n8vf -c freqtrade -- cat /extra_strategies/utils/RBMEncoder.py

import numpy as np
from pandas import DataFrame, Series
import pandas as pd
from sklearn.neural_network import BernoulliRBM

import random
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1'
os.environ['TF_DETERMINISTIC_OPS'] = '1'

import tensorflow as tf

seed = 42
os.environ['PYTHONHASHSEED'] = str(seed)
random.seed(seed)
tf.random.set_seed(seed)
np.random.seed(seed)

tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.WARN)

#import keras



class RBMEncoder():

    rbm = None

    def __init__(self):
        super().__init__()
        self.rbm = BernoulliRBM(random_state=0, verbose=True)

    def transform(self, dataframe: DataFrame) -> DataFrame:
        self.rbm.learning_rate = 0.06
        self.rbm.n_iter = 20
        self.rbm.n_components = dataframe.shape[1]
        self.rbm = self.rbm.fit(dataframe)
        return self.rbm.transform(dataframe)