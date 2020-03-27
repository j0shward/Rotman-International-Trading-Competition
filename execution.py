from time import sleep, time
from threading import Thread
import requests
import itertools

import pandas as pd
import numpy as np
import math
import scipy.stats as st

import warnings
warnings.filterwarnings('ignore')

import sys
import os

class OptionsExecutionManager(ExecutionManager):
    def __init__(self, api, tickers, securities):
        super().__init__(api, tickers, securities) #calls all of the arguments from the super class 'Security'
        self.position_size = 100
        
        # Override for options specific limits
        """" Risk Limits """
        res = requests.get(self.endpoint + '/limits', headers=self.headers)

        if res.ok:
            # For some reason it returns a list rather than single dict
            limits = res.json()[1]
            self.gross_limit = limits['gross_limit']
            self.net_limit = limits['net_limit']
            print("[OptionsExecManager] Options Position Net Limits: %s" % self.net_limit)
        else:
            print('[Execution Manager] Error could not obtain position limits from API!')

    def compute_delta(self,S,K,T,r,sigma,option): #get sigma from api
        return self.delta(S,K, T, r, sigma,option)

    def delta(self,S, K, T, r, sigma, option):

        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        
        if option == 'C':
            result = st.norm.cdf(d1, 0.0, 1.0)
        if option == 'P':
            result = -st.norm.cdf(-d1, 0.0, 1.0)
            
        return result

    def delta_hedge(self,S,K, T, r, sigma, option, order_type, order_size):
        
        #option multiplier is 100x
        delta = self.compute_delta(S,K, T, r, sigma, option) * order_size

        delta = abs(delta) # as the delta of puts is negative but that is dealt with with order_type in create_order
        delta = max(round(delta, 0), 1)

        delta_order_size = max(round(delta/S,0),1)

        order = self.create_order('RTM' , 'MARKET',order_type, delta_order_size) if delta > 0 else None
        return order
    
    def vol_forecast(self):
        news = requests.get(self.endpoint + '/news', params={'limit':1}, headers=self.headers)
        if news.ok:
            body = news.json()[0]['body'] #call the body of the news article

            if body[4] == 'l': #'the latest annualised' - direct figure
                sigma = int(body[-3:-1])/100

            elif body[4] == 'a': #'the annualized' - expectation of range
                sigma = (int(body[-26:-24]) + int(body[-32:-30]))/200
                
            else: sigma = 0.2

        else:
            print('[Indicators] Could not reach API! %s' % res.json())
            sigma = 0.2

        print("Vol Forecast is",sigma)

        return sigma

    """___________________Newton Raphson Implied Volatility Calculator________________________"""

    def nr_imp_vol(self,S, K, T, f, r, sigma, option = 'C' ):   
    
        #S: spot price
        #K: strike price
        #T: time to maturity
        #f: Option value
        #r: interest rate
        #sigma: volatility of underlying asset
        #option: where it is a call or a put option
        
        d1 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        
        if option == 'C':
            fx = S * st.norm.cdf(d1, 0.0, 1.0) - K * np.exp(-r * T) * st.norm.cdf(d2, 0.0, 1.0) - f
            vega = (1 / np.sqrt(2 * np.pi)) * S * np.sqrt(T) * np.exp(-(st.norm.cdf(d1, 0.0, 1.0) ** 2) * 0.5)
            
        if option == 'P':
            fx = K * np.exp(-r * T) * st.norm.cdf(-d2, 0.0, 1.0) - S * st.norm.cdf(-d1, 0.0, 1.0) - f
            vega = (1 / np.sqrt(2 * np.pi)) * S * np.sqrt(T) * np.exp(-(st.norm.cdf(d1, 0.0, 1.0) ** 2) * 0.5)
        
        tolerance = 0.000001 #limit of margin accepted for newton raphson algorithm
        x0 = sigma #we take our known 
        xnew  = x0
        xold = x0 - 1
            
        while abs(xnew - xold) > tolerance:
        
            xold = xnew
            xnew = (xnew - fx - f) / vega
            
            return abs(xnew)