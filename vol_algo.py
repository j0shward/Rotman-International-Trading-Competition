from execution import TradingTick, ExecutionManager, OptionsExecutionManager
from security import Security, Options
from sources import API
import numpy as np
import pandas as pd
from time import sleep

#Deal with the API for sourcing data and sending orders
#my API key is in api.JSON


api = API('./configs/api_config.JSON')

tickers = {'ticker_C_1':['RTM1C45','RTM1C46','RTM1C47','RTM1C48','RTM1C49','RTM1C50','RTM1C51','RTM1C52','RTM1C53','RTM1C54'],
    'ticker_C_2':['RTM2C45','RTM2C46','RTM2C47','RTM2C48','RTM2C49','RTM2C50','RTM2C51','RTM2C52','RTM2C53','RTM2C54'],
    'ticker_P_1':['RTM1P45','RTM1P46','RTM1P47','RTM1P48','RTM1P49','RTM1P50','RTM1P51','RTM1P52','RTM1P53','RTM1P54'],
    'ticker_P_2':['RTM2P45','RTM2P46','RTM2P47','RTM2P48','RTM2P49','RTM2P50','RTM2P51','RTM2P52','RTM2P53','RTM2P54']}

class OptionsTradingManager:

    def __init__(self,api,r=0):
        self.api =api
        self.r=r
        
        self.options = {}
        self.securities = {}
        self.tickers = pd.DataFrame(data=tickers)
        tickers_reshaped = np.array(self.tickers.values).reshape(-1,)
        all_tickers = tickers_reshaped.tolist()

        for ticker in tickers_reshaped:
            sec = Options(ticker, self.api, is_currency=False)
            sec.start()
            self.options[ticker] = sec
        
        self.underlying = Security('RTM', self.api, is_currency=False) # Add the underlying asset as something to monitor
        self.underlying.start()
        self.securities['RTM'] = self.underlying
        all_tickers.append('RTM')
        
        self.options_execution_manager = OptionsExecutionManager(self.api, tickers_reshaped.tolist(), self.options)
        self.securities_execution_manager = ExecutionManager(self.api, ['RTM'], self.securities)

        self.options_execution_manager.start()

    
    def __enter__(self):
        # TODO: Fix time duration its not 295 seconds!
        sleep(5)

        is_second_run = False

        for t in TradingTick(600, self.api):
            print('time is',t)
            self.sigma = self.options_execution_manager.vol_forecast()

            if t >= 285: is_second_run = True

            if is_second_run:
                #self.tickers = {'ticker_C_2':self.tickers['ticker_C_2'], 'ticker_P_2':self.tickers['ticker_P_2']}
                #print('Put Call Parity:')
                #self.specific_option_misprice_2(self.tickers)
                print('options mispriced through vol forecast:')
                self.imp_vol_mp_2(self.tickers)
                print('option mispriced through price')
                self.f_misprice_2(self.tickers,r=0)

            else:
                #print('Put Call Parity:')
                #self.specific_option_misprice_1(self.tickers)
                print('options mispriced through vol forecast:')
                self.imp_vol_mp_1(self.tickers)
                #print('term structure')
                #self.termstructure(self.tickers)
                print('option mispriced through price')
                self.f_misprice_1(self.tickers,r=0)

            #close all positions every 3 trade execution ticks
            if (t-5) % 12 == 0:
                self.options_execution_manager.close_all_positions()


            sleep(4)
    '''
    def __enter__(self):
        # TODO: Fix time duration its not 295 seconds!
        sleep(5)

        a = [0,290]

        for a in a:

            for t in TradingTick(300, self.api):
                print('time is',t+a)
                self.sigma = self.options_execution_manager.vol_forecast()

                if t+a >= 290:
                    self.tickers = {'ticker_C_2':self.tickers['ticker_C_2'], 'ticker_P_2':self.tickers['ticker_P_2']}
                    self.specific_option_misprice_2(self.tickers)
                    self.imp_vol_mp_2(self.tickers)

                else:
                    self.specific_option_misprice_1(self.tickers)
                    self.imp_vol_mp_1(self.tickers)
                    self.termstructure(self.tickers)

                sleep(4)
    '''
    def __exit__(self, t, value, traceback):
        print("-------------- Trading Period Finished! -----------------")

    "___________________Term Structure Trading Algorithm________________________"

    def termstructure(self,tickers,r=0):
        for i in range(len(tickers)):

            C_1 = self.options[tickers['ticker_C_1'][i]].get_midprice()
            P_1 = self.options[tickers['ticker_P_1'][i]].get_midprice()
            C_2 = self.options[tickers['ticker_C_2'][i]].get_midprice()
            P_2 = self.options[tickers['ticker_P_2'][i]].get_midprice()

            S, K_C_1, T_C_1, option_C_1 = self.options[tickers['ticker_C_1'][i]].option_disect()
            S, K_P_1, T_P_1, option_P_1 = self.options[tickers['ticker_P_1'][i]].option_disect()
            S, K_C_2, T_C_2, option_C_2 = self.options[tickers['ticker_C_2'][i]].option_disect()
            S, K_P_2, T_P_2, option_P_2 = self.options[tickers['ticker_P_2'][i]].option_disect()

            S = self.underlying.get_midprice()

            C_1_vol = self.options_execution_manager.nr_imp_vol(S, K_C_1, T_C_1, C_1, r, self.sigma, option = 'C')
            P_1_vol = self.options_execution_manager.nr_imp_vol(S, K_P_1, T_P_1, P_1, r, self.sigma, option = 'P')
            C_2_vol = self.options_execution_manager.nr_imp_vol(S, K_C_2, T_C_2, C_2, r, self.sigma, option = 'C')
            P_2_vol = self.options_execution_manager.nr_imp_vol(S, K_P_2, T_P_2, P_2, r, self.sigma, option = 'P')
            
            orders = []
            sec_orders = []

            #if strike >= 100% term structure should be normal
            if K_C_1/S >= 1:
                
                #if inverted call term structure
                if 1.3*C_2_vol < C_1_vol:
                    print("At Strike",K_C_1,"Buy 2M and Sell 1M Call")

                    orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET','BUY', 1))
                    sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_2,T_C_2,r,self.sigma,'C','SELL',1))

                    orders.append(self.options_execution_manager.create_order(tickers['ticker_C_1'][i] , 'MARKET','SELL', 1))
                    sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_1,T_C_1,r,self.sigma,'C','BUY',1))
                
                #if inverted put term structure
                if 1.3*P_2_vol < P_1_vol:
                    print("At Strike",K_C_1,"Buy 2M and Sell 1M Put")

                    orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET','BUY', 1))
                    sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_2,T_P_2,r,self.sigma,'P','BUY',1))

                    orders.append(self.options_execution_manager.create_order(tickers['ticker_P_1'][i] , 'MARKET','SELL', 1))
                    sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_1,T_P_1,r,self.sigma,'P','SELL',1))

            
            #if strike < 5% term structure should be inverted
            if K_C_1/S < 1:
                
                #if normal call term structure
                if 0.7*C_2_vol >= C_1_vol:
                    print("At Strike",K_C_1,"Buy 1M and Sell 2M Call")

                    orders.append(self.options_execution_manager.create_order(tickers['ticker_C_1'][i] , 'MARKET','BUY', 1))
                    sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_1,T_C_1,r,self.sigma,'C','SELL',1))

                    orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET','SELL', 1))
                    sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_2,T_C_2,r,self.sigma,'C','BUY',1))
                
                #if normal put term structure
                if 0.7*P_2_vol >= P_1_vol:
                    print("At Strike",K_C_1,"Buy 1M and Sell 2M Put")

                    orders.append(self.options_execution_manager.create_order(tickers['ticker_P_1'][i] , 'MARKET','BUY', 1))
                    sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_1,T_P_1,r,self.sigma,'P','BUY',1))

                    orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET','SELL', 1))
                    sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_2,T_P_2,r,self.sigma,'P','SELL',1))

        oids = self.options_execution_manager.execute_orders(orders, 'OPTION')
        self.securities_execution_manager.execute_orders(sec_orders, 'OPTION')

    "___________________Option Implied Volatility Mispricing Algorithm________________________"

    def imp_vol_mp_1(self,tickers,r=0):

        orders = []
        sec_orders = []

        call_skew_1 = []
        call_skew_2 = []
        put_skew_1 = []
        put_skew_2 = []

        for i in range(len(tickers)):

            C_1 = self.options[tickers['ticker_C_1'][i]].get_midprice()
            P_1 = self.options[tickers['ticker_P_1'][i]].get_midprice()
            C_2 = self.options[tickers['ticker_C_2'][i]].get_midprice()
            P_2 = self.options[tickers['ticker_P_2'][i]].get_midprice()

            S, K_C_1, T_C_1, option_C_1 = self.options[tickers['ticker_C_1'][i]].option_disect()
            S, K_P_1, T_P_1, option_P_1 = self.options[tickers['ticker_P_1'][i]].option_disect()
            S, K_C_2, T_C_2, option_C_2 = self.options[tickers['ticker_C_2'][i]].option_disect()
            S, K_P_2, T_P_2, option_P_2 = self.options[tickers['ticker_P_2'][i]].option_disect()

            S = self.underlying.get_midprice()

            C_1_vol = self.options_execution_manager.nr_imp_vol(S, K_C_1, T_C_1, C_1, r, self.sigma, option = 'C')
            P_1_vol = self.options_execution_manager.nr_imp_vol(S, K_P_1, T_P_1, P_1, r, self.sigma, option = 'P')
            C_2_vol = self.options_execution_manager.nr_imp_vol(S, K_C_2, T_C_2, C_2, r, self.sigma, option = 'C')
            P_2_vol = self.options_execution_manager.nr_imp_vol(S, K_P_2, T_P_2, P_2, r, self.sigma, option = 'P')

            call_skew_1.append(C_1_vol)
            put_skew_1.append(P_1_vol)
            call_skew_2.append(C_2_vol)
            put_skew_2.append(P_2_vol)

            if 1.3*C_1_vol < self.sigma:
                print("At Strike",K_C_1,"Buy 1M Call") #Buy as the implied vol is priced below what is forecast
                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_1'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_1,T_C_1,r,self.sigma,'C','SELL',1))
            elif 0.7*C_1_vol > self.sigma:
                print("At Strike",K_C_1,"Sell 1M Call") #Sell as the implied vol is priced above what is forecast
                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_1'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_1,T_C_1,r,self.sigma,'C','BUY',1))
            else:
                print("At Strike",K_C_1,"The Call volatility is priced appropriately")

            if 1.3*P_1_vol < self.sigma:
                print("At Strike",K_P_1,"Buy 1M Put") #Buy as the implied vol is priced below what is forecast
                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_1'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_1,T_P_1,r,self.sigma,'P','BUY',1))
            elif 0.7*P_1_vol > self.sigma:
                print("At Strike",K_P_1,"Sell 1M Put") #Sell as the implied vol is priced above what is forecast
                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_1'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_1,T_P_1,r,self.sigma,'P','SELL',1))
            else:
                print("At Strike",K_P_1,"The Call volatility is priced appropriately")
                                
            if 1.3*C_2_vol < self.sigma:
                print("At Strike",K_C_2,"Buy 2M Call") #Buy as the implied vol is priced below what is forecast
                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_2,T_C_2,r,self.sigma,'C','SELL',1))
            elif 0.7*C_2_vol > self.sigma:
                print("At Strike",K_C_2,"Sell 2M Call") #Sell as the implied vol is priced above what is forecast
                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_2,T_C_2,r,self.sigma,'C','BUY',1))
            else:
                print("At Strike",K_C_2,"The Call volatility is priced appropriately")

            if 1.3*P_2_vol < self.sigma:
                print("At Strike",K_P_2,"Buy 2M Put") #Buy as the implied vol is priced below what is forecast
                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_2,T_P_2,r,self.sigma,'P','BUY',1))
            elif 0.7*P_2_vol > self.sigma:
                print("At Strike",K_P_2,"Sell 2M Put") #Sell as the implied vol is priced above what is forecast
                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_2,T_P_2,r,self.sigma,'P','SELL',1))
            else:
                print("At Strike",K_P_2,"The Call volatility is priced appropriately")

        oids = self.options_execution_manager.execute_orders(orders, 'OPTION')
        self.securities_execution_manager.execute_orders(sec_orders, 'OPTION')
        
        # plt.plot(call_skew_1,marker='o',markersize=8,color='blue',linewidth=2)
        # plt.plot(put_skew_1, marker='o',markersize=8,color='red',linewidth=2)
        # plt.plot(call_skew_2,marker='o',markersize=8,color='green',linewidth=2)
        # plt.plot(put_skew_2, marker='o',markersize=8,color='orange',linewidth=2)
        # plt.legend([call_skew_1, put_skew_1,call_skew_2, put_skew_2], ['call_skew 1m', 'put_skew 1m, call_skew 2m', 'put_skew 2m'])
        # red_patch = mpatches.Patch(color='red', label='put_skew 1M')
        # blue_patch = mpatches.Patch(color='blue', label='call_skew 1M')
        # green_patch = mpatches.Patch(color='green', label='call_skew 2M')
        # orange_patch = mpatches.Patch(color='orange', label='put_skew 2M')
        # plt.legend(handles=[blue_patch,red_patch,green_patch,orange_patch])
        # plt.show()
    
    def imp_vol_mp_2(self,tickers,r=0):
        orders = []
        sec_orders = []

        call_skew_2 = []
        put_skew_2 = []

        for i in range(len(tickers)):
            C_2 = self.options[tickers['ticker_C_2'][i]].get_midprice()
            P_2 = self.options[tickers['ticker_P_2'][i]].get_midprice()

            S, K_C_2, T_C_2, option_C_2 = self.options[tickers['ticker_C_2'][i]].option_disect()
            S, K_P_2, T_P_2, option_P_2 = self.options[tickers['ticker_P_2'][i]].option_disect()

            S = self.underlying.get_midprice()

            C_2_vol = self.options_execution_manager.nr_imp_vol(S, K_C_2, T_C_2, C_2, r, self.sigma, option = 'C')
            P_2_vol = self.options_execution_manager.nr_imp_vol(S, K_P_2, T_P_2, P_2, r, self.sigma, option = 'P')
            C_2_vol = self.options_execution_manager.nr_imp_vol(S, K_C_2, T_C_2, C_2, r, self.sigma, option = 'C')
            P_2_vol = self.options_execution_manager.nr_imp_vol(S, K_P_2, T_P_2, P_2, r, self.sigma, option = 'P')

            call_skew_2.append(C_2_vol)
            put_skew_2.append(P_2_vol)
            
            if 1.3*C_2_vol < self.sigma:
                print("At Strike",K_C_2,"Buy 2M Call") #Buy as the implied vol is priced below what is forecast
                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_2,T_C_2,r,self.sigma,'C','SELL',1))
            elif 0.7*C_2_vol > self.sigma:
                print("At Strike",K_C_2,"Sell 2M Call") #Sell as the implied vol is priced above what is forecast
                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_2,T_C_2,r,self.sigma,'C','BUY',1))
            else:
                print("At Strike",K_C_2,"The Call volatility is priced appropriately")

            if 1.3*P_2_vol < self.sigma:
                print("At Strike",K_P_2,"Buy 2M Put") #Buy as the implied vol is priced below what is forecast
                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_2,T_P_2,r,self.sigma,'P','BUY',1))
            elif 0.7*P_2_vol > self.sigma:
                print("At Strike",K_P_2,"Sell 2M Put") #Sell as the implied vol is priced above what is forecast
                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_2,T_P_2,r,self.sigma,'P','SELL',1))
            else:
                print("At Strike",K_P_2,"The Call volatility is priced appropriately")

        oids = self.options_execution_manager.execute_orders(orders, 'OPTION')
        self.securities_execution_manager.execute_orders(sec_orders, 'OPTION')
        

    "___________________Put Call Parity Trading Algorithm________________________"

    def specific_option_misprice_1(self,tickers,r=0):

        orders = []
        sec_orders = []


        for i in range(len(tickers)):
            C_1 = self.options[tickers['ticker_C_1'][i]].get_midprice()
            P_1 = self.options[tickers['ticker_P_1'][i]].get_midprice()

            S, K, T, option = self.options[tickers['ticker_C_1'][i]].option_disect()
            r = self.r

            if 0.5*C_1 > P_1 + S - K*np.exp(-r*T):
                
                print("At Strike",K,"Buy Put 1M, Sell Call 1M")

                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_1'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K,T,r,self.sigma,'C','BUY',1))

                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_1'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K,T,r,self.sigma,'P','BUY',1))
                
            elif C_1 < P_1 + S - K*np.exp(-r*T):
                
                print("At Strike",K,"Buy Call 1M, Sell Put 1M")

                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_1'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K,T,r,self.sigma,'C','SELL',1))

                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_1'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K,T,r,self.sigma,'P','SELL',1))
                

            C_2 = self.options[tickers['ticker_C_2'][i]].get_midprice()
            P_2 = self.options[tickers['ticker_P_2'][i]].get_midprice()

            S, K, T, option = self.options[tickers['ticker_C_2'][i]].option_disect()

            if 0.5*C_2 > P_2 + S - K*np.exp(-r*T):
                
                print("At Strike",K,"Buy Put 2M, Sell Call 2M")

                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET', 'SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K,T,r,self.sigma,'C','BUY',1))

                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET', 'BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K,T,r,self.sigma,'P','BUY',1))

            elif C_2 < P_2 + S - K*np.exp(-r*T):
                
                print("At Strike",K,"Buy Call 2M, Sell Put 2M")

                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET',  'BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K,T,r,self.sigma,'C','SELL',1))

                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET',  'SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K,T,r,self.sigma,'P','SELL',1))
        
        oids = self.options_execution_manager.execute_orders(orders, 'OPTION')
        self.securities_execution_manager.execute_orders(sec_orders, 'OPTION')

    def specific_option_misprice_2(self,tickers,r=0):

        orders = []
        sec_orders = []


        for i in range(len(tickers)):
            C_2 = self.options[tickers['ticker_C_2'][i]].get_midprice()
            P_2 = self.options[tickers['ticker_P_2'][i]].get_midprice()

            S, K, T, option = self.options[tickers['ticker_C_2'][i]].option_disect()

            if 0.5*C_2 > P_2 + S - K*np.exp(-r*T):
                
                print("At Strike",K,"Buy Put 2M, Sell Call 2M")

                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET', 'SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K,T,r,self.sigma,'C','BUY',1))

                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET', 'BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K,T,r,self.sigma,'P','BUY',1))

            elif C_2 < P_2 + S - K*np.exp(-r*T):
                
                print("At Strike",K,"Buy Call 2M, Sell Put 2M")

                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET',  'BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K,T,r,self.sigma,'C','SELL',1))

                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET',  'SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K,T,r,self.sigma,'P','SELL',1))

        oids = self.options_execution_manager.execute_orders(orders, 'OPTION')
        self.securities_execution_manager.execute_orders(sec_orders, 'OPTION')

    "___________________Option Value Mispricing Algorithm________________________"

    def f_misprice_1(self,tickers,r=0):
        '''
        rather than finding arbs in the implied vol it may be more effective to simply compare the market price
        '''

        orders = []
        sec_orders = []

        for i in range(len(tickers)):

            C_1 = self.options[tickers['ticker_C_1'][i]].get_midprice()
            P_1 = self.options[tickers['ticker_P_1'][i]].get_midprice()
            C_2 = self.options[tickers['ticker_C_2'][i]].get_midprice()
            P_2 = self.options[tickers['ticker_P_2'][i]].get_midprice()

            S, K_C_1, T_C_1, option_C_1 = self.options[tickers['ticker_C_1'][i]].option_disect()
            S, K_P_1, T_P_1, option_P_1 = self.options[tickers['ticker_P_1'][i]].option_disect()
            S, K_C_2, T_C_2, option_C_2 = self.options[tickers['ticker_C_2'][i]].option_disect()
            S, K_P_2, T_P_2, option_P_2 = self.options[tickers['ticker_P_2'][i]].option_disect()

            S = self.underlying.get_midprice()

            C_1_value = self.options.vanilla(S, K_C_1, T_C_1, C_1, r, self.sigma,tickers['ticker_C_1'][i], option = 'C')
            P_1_value = self.options.vanilla(S, K_P_1, T_P_1, P_1, r, self.sigma,tickers['ticker_P_1'][i], option = 'P')
            C_2_value = self.options.vanilla(S, K_C_2, T_C_2, C_2, r, self.sigma,tickers['ticker_C_2'][i], option = 'C')
            P_2_value = self.options.vanilla(S, K_P_2, T_P_2, P_2, r, self.sigma,tickers['ticker_P_2'][i], option = 'P')

            if C_1_value > C_1:
                print("At Strike",K_C_1,"Buy 1M Call")
                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_1'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_1,T_C_1,r,self.sigma,'C','SELL',1))
            elif C_1_value < C_1:
                print("At Strike",K_C_1,"Sell 1M Call")
                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_1'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_1,T_C_1,r,self.sigma,'C','BUY',1))
            else:
                print("At Strike",K_C_1,"The Call volatility is priced appropriately")

            if P_1_value > P_1:
                print("At Strike",K_P_1,"Buy 1M Put")
                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_1'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_1,T_P_1,r,self.sigma,'P','BUY',1))
            elif P_1_value < P_1:
                print("At Strike",K_P_1,"Sell 1M Put")
                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_1'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_1,T_P_1,r,self.sigma,'P','SELL',1))
            else:
                print("At Strike",K_P_1,"The Call volatility is priced appropriately")
                                
            if C_2_value > C_2:
                print("At Strike",K_C_2,"Buy 2M Call")
                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_2,T_C_2,r,self.sigma,'C','SELL',1))
            elif C_2_value < C_2:
                print("At Strike",K_C_2,"Sell 2M Call")
                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_2,T_C_2,r,self.sigma,'C','BUY',1))
            else:
                print("At Strike",K_C_2,"The Call volatility is priced appropriately")

            if P_2_value > P_2:
                print("At Strike",K_P_2,"Buy 2M Put")
                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_2,T_P_2,r,self.sigma,'P','BUY',1))
            elif P_2_value < P_2:
                print("At Strike",K_P_2,"Sell 2M Put")
                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_2,T_P_2,r,self.sigma,'P','SELL',1))
            else:
                print("At Strike",K_P_2,"The Call volatility is priced appropriately")

        oids = self.options_execution_manager.execute_orders(orders, 'OPTION')
        self.securities_execution_manager.execute_orders(sec_orders, 'OPTION')

    def f_misprice_2(self,tickers,r=0):
        '''
        rather than finding arbs in the implied vol it may be more effective to simply compare the market price
        '''

        orders = []
        sec_orders = []

        for i in range(len(tickers)):

            C_2 = self.options[tickers['ticker_C_2'][i]].get_midprice()
            P_2 = self.options[tickers['ticker_P_2'][i]].get_midprice()

            S, K_C_2, T_C_2, option_C_2 = self.options[tickers['ticker_C_2'][i]].option_disect()
            S, K_P_2, T_P_2, option_P_2 = self.options[tickers['ticker_P_2'][i]].option_disect()

            S = self.underlying.get_midprice()

            C_2_value = self.options.vanilla(S, K_C_2, T_C_2, C_2, r, self.sigma,tickers['ticker_C_2'][i], option = 'C')
            P_2_value = self.options.vanilla(S, K_P_2, T_P_2, P_2, r, self.sigma,tickers['ticker_P_2'][i], option = 'P')
                                
            if C_2_value > C_2:
                print("At Strike",K_C_2,"Buy 2M Call")
                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_2,T_C_2,r,self.sigma,'C','SELL',1))
            elif C_2_value < C_2:
                print("At Strike",K_C_2,"Sell 2M Call")
                orders.append(self.options_execution_manager.create_order(tickers['ticker_C_2'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_C_2,T_C_2,r,self.sigma,'C','BUY',1))
            else:
                print("At Strike",K_C_2,"The Call volatility is priced appropriately")

            if P_2_value > P_2:
                print("At Strike",K_P_2,"Buy 2M Put")
                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET','BUY', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_2,T_P_2,r,self.sigma,'P','BUY',1))
            elif P_2_value < P_2:
                print("At Strike",K_P_2,"Sell 2M Put")
                orders.append(self.options_execution_manager.create_order(tickers['ticker_P_2'][i] , 'MARKET','SELL', 1))
                sec_orders.append(self.options_execution_manager.delta_hedge(S,K_P_2,T_P_2,r,self.sigma,'P','SELL',1))
            else:
                print("At Strike",K_P_2,"The Call volatility is priced appropriately")

        oids = self.options_execution_manager.execute_orders(orders, 'OPTION')
        self.securities_execution_manager.execute_orders(sec_orders, 'OPTION')



"""-------------- RUNTIME --------------"""
def install_thread_excepthook():
    """
    Workaround for sys.excepthook thread bug
    (https://sourceforge.net/tracker/?func=detail&atid=105470&aid=1230540&group_id=5470).
    Call once from __main__ before creating any threads.
    If using psyco, call psycho.cannotcompile(threading.Thread.run)
    since this replaces a new-style class method.
    """
    import sys
    run_old = threading.Thread.run
    def run(*args, **kwargs):
        try:
            run_old(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            sys.excepthook(*sys.exc_info())
    threading.Thread.run = run

#TODO: Get threads print statements working
def main():
    print('reached')
    with OptionsTradingManager(api) as tm:
        
        for t in TradingTick(295,  api):
            pass

if __name__ == '__main__':
    # install_thread_excepthook()
    main()
        