kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-mssm-01 exec -it pod/freqtrade-bot-mssm-01-5f5bdfb5b4-kbc7z -c freqtrade -- cat /extra_strategies/utils/CustomAdam.py
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import tensorflow as tf
from keras.optimizers import Adam

class CustomAdam(Adam):

   def get_config(self):
        config = super().get_config()
        config.update(
            {
                "learning_rate": self._serialize_hyperparameter(
                    "learning_rate"
                ),
                # "decay": self._initial_decay,
                "decay": self._serialize_hyperparameter("decay"),
                "beta_1": self._serialize_hyperparameter("beta_1"),
                "beta_2": self._serialize_hyperparameter("beta_2"),
                "epsilon": self.epsilon,
                "amsgrad": self.amsgrad,
            }
        )
        return config