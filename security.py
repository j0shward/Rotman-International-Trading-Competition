from time import sleep, time
from threading import Thread
import requests
import itertools

import pandas as pd
import numpy as np
import math

import warnings
warnings.filterwarnings('ignore')

class Options(Security):

    def __init__(self, ticker, api, poll_delay=0.01, is_currency=False):
        super().__init__( ticker, api,poll_delay=0.01,is_currency=is_currency) #calls all of the arguments from the super class 'Security'

        self.strike = int(str(self.ticker)[5:7])
        self.maturity = int(str(self.ticker)[3]) / 12
        self.option_type = str(self.ticker)[4]

    """___________________Vanilla Option Pricer________________________"""

    def vanilla(self, S, K, T, r, sigma,ticker, option = 'C'):
 
        S = self.get_midprice()
        K = self.strike
        T = self.maturity
        option = self.option_type
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        
        if option == 'C':
            result = (S * si.norm.cdf(d1, 0.0, 1.0) - K * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0))
        if option == 'P':
            result = (K * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0) - S * si.norm.cdf(-d1, 0.0, 1.0))
        return result

    def option_disect(self):
        S = self.get_midprice()
        K = self.strike
        T = self.maturity
        option = self.option_type

        return S, K, T, option
    