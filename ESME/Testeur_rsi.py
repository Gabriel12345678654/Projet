import yfinance as yf
import pandas as pd
import talib as ta
from talib import RSI
import matplotlib.pyplot as plt
from skopt import gp_minimize
from skopt.space import Integer
from skopt.utils import use_named_args
from skopt.space import Integer, Real, Categorical
from datetime import datetime
import winsound
import time
start_time = time.time()  # Enregistre l'heure de début


#Simulation:-----------------------------------------------
min_roi = 70000  #Seuil minimal de rendement
n_calls = 100 #Nombre d'itérations
#Paramètres fixes:-----------------------------------------
action = '^FCHI'
periode = '1d'
start_date = datetime.strptime('2014-09-18', '%Y-%m-%d')
end_date = datetime.strptime('2021-09-18', '%Y-%m-%d')
initial_capital = 1000
coef_TP_longs = 0.7
coef_TP_shorts = 0.7
perte_solde = 30 #variation max en %
#Définir les plages de valeurs ici :
#----------------------------------------------------------
space = [
    Integer(1, 5, name='levier'),
    Integer(150, 300, name='take_profit_long'),
    Integer(5, 30, name='stop_loss'),
    Integer(2, 30, name='take_profit_short_0'),
    Integer(1, 20, name='stop_loss_short'),
    Integer(2, 200, name='fast_length'),
    Integer(2, 200, name='slow_length'),
    Integer(2, 200, name='signal_length'),
    Integer(2, 200, name='trend_length'),
    Integer(2, 200, name='f'),
    Integer(2, 200, name='s'),
    Categorical(['EMA', 'SMA'], name='sma_source'),
    Categorical(['EMA', 'SMA'], name='sma_signal'),
    Real(0.5, 1, name='sensi_longs'),
    Real(0.1, 1, name='sensi_shorts'),
    Integer(50, 100, name='rsi_high'),
    Integer(1, 50, name='rsi_low')
]
#----------------------------------------------------------

data = yf.Ticker(action)
prix = data.history(period=periode, start=start_date)

    
def objective(params):
    # Extract the parameters
    levier, take_profit_long, stop_loss, take_profit_short_0, stop_loss_short, fast_length, slow_length, signal_length, trend_length, f, s, sma_source, sma_signal, sensi_longs, sensi_shorts, rsi_high, rsi_low = params
    
    #Initialisation
    take_profit_long = take_profit_long/100
    stop_loss = stop_loss/100
    take_profit_short_0 = take_profit_short_0/100
    stop_loss_short = stop_loss_short/100
    frais = 1-(0.075/100)
    solde = initial_capital
    solde_max = initial_capital
    prix_entree = prix['Close'][1]
    take_profit = take_profit_long
    take_profit_short = take_profit_short_0
    opération = ''
    ignore_strategy = False
    
    #calculs
    trend_ema = ta.EMA(prix['Close'], trend_length)
    fast_ma = ta.EMA(prix['Close'], fast_length) if sma_source == 'EMA' else ta.SMA(prix['Close'], fast_length)
    slow_ma = ta.EMA(prix['Close'], slow_length) if sma_source == 'EMA' else ta.SMA(prix['Close'], slow_length)
    macd = fast_ma - slow_ma
    signal = ta.EMA(macd, signal_length) if sma_signal == 'EMA' else ta.SMA(macd, signal_length)
    rsi = RSI(prix['Close'], timeperiod=14)
    for i in range(len(prix.index)):
        long_entry = macd[i] > signal[i] and ta.EMA(prix['Close'], f)[i] > ta.EMA(prix['Close'], s)[i] and prix['Close'][i] > trend_ema[i] and rsi[i] < rsi_low
        short_entry = macd[i] < signal[i] and ta.EMA(prix['Close'], f)[i] < ta.EMA(prix['Close'], s)[i] and prix['Close'][i] < trend_ema[i] and rsi[i] > rsi_high
        tp_long = prix['Close'][i] >= (prix_entree * (1 + take_profit)) 
        sl_long = prix['Close'][i] <= (prix_entree * (1 - (stop_loss / levier)))
        tp_short = prix['Close'][i] <= (prix_entree * (1 - take_profit_short))
        sl_short = prix['Close'][i] >= (prix_entree * (1 + (stop_loss_short / levier)))
        previous_balance = solde
        
        if short_entry and opération != 'Short' and solde > 0:
            if opération == 'Long':
                solde = solde*(1+levier*((prix['Close'][i]/prix_entree)-1))*frais
                if solde > solde_max : solde_max = solde
            prix_entree = prix['Close'][i]
            take_profit = take_profit_long
            opération = 'Short'
            
        elif long_entry and opération != 'Long' and solde > 0:
            if opération == 'Short':
                solde = solde*(1+levier*(1-(prix['Close'][i]/prix_entree)))*frais
                if solde > solde_max : solde_max = solde
            prix_entree = prix['Close'][i]
            take_profit_short = take_profit_short_0
            opération = 'Long'
            
        elif tp_long and opération == 'Long':
            solde = solde*(1+levier*((prix['Close'][i]/prix_entree)-1))*frais
            if solde > solde_max : solde_max = solde
            take_profit = take_profit*coef_TP_longs
            take_profit_short = take_profit_short_0
            opération = 'TP Long'
            
        elif sl_long and opération == 'Long':
            solde = solde*(1+levier*((prix['Close'][i]/prix_entree)-1))*frais
            if solde > solde_max : solde_max = solde
            take_profit = take_profit_long
            take_profit_short = take_profit_short_0
            opération = 'SL Long'
            
        elif tp_short and opération == 'Short':
            solde = solde*(1+levier*(1-(prix['Close'][i]/prix_entree)))*frais
            if solde > solde_max : solde_max = solde
            take_profit = take_profit_long
            take_profit_short = take_profit_short*coef_TP_shorts
            opération = 'TP Short'
            
        elif sl_short and opération == 'Short':
            solde = solde*(1+levier*(1-(prix['Close'][i]/prix_entree)))*frais
            if solde > solde_max : solde_max = solde
            take_profit = take_profit_long
            take_profit_short = take_profit_short_0
            opération = 'SL Short'
        if solde <= 0:
            break
        
        # Vérifiez si le solde a baissé de plus de x%
        if (solde_max - solde) / solde_max > (perte_solde/100):
           ignore_strategy = True
           break
        if solde <= 0:
            ignore_strategy = True
            break
    # Si la stratégie doit être ignorée, retournez une valeur qui ne sera pas optimisée
    if ignore_strategy:
        return 1e10  

    # Calculate the return on investment
    roi = (solde / initial_capital) * 100
    
    # Return the negative ROI, since the optimization will minimize this value
    return -roi




while True:
    result = gp_minimize(objective, space, n_calls=n_calls, random_state=None, verbose=0)
    best_roi = -result.fun

    # Vérifie si le rendement est supérieur au seuil minimal
    if best_roi >= min_roi:
        break  # Si le rendement est suffisant, sortez de la boucle

# Afficher les résultats

print("-----------------")
print("Rendement =", round(best_roi), '%')
print("Meilleurs paramètres à copier:")
print('------')
print("levier =", result.x[0])
print("take_profit_long =", result.x[1])
print("stop_loss =", result.x[2])
print("take_profit_short_0 =", result.x[3])
print("stop_loss_short =", result.x[4])
print("fast_length =", result.x[5])
print("slow_length =", result.x[6])
print("signal_length =", result.x[7])
print("trend_length =", result.x[8])
print("f =", result.x[9])
print("s =", result.x[10])
print("sma_source =", result.x[11])
print("sma_signal =", result.x[12])
print("sensi_longs =", result.x[13])
print("sensi_shorts =", result.x[14])
print("rsi_long =", result.x[15])
print("rsi_low =", result.x[16])
print('------')
end_time = time.time()  # Enregistre l'heure de fin
execution_time = end_time - start_time  # Calcule le temps d'exécution
print("Temps d'exécution : {:.2f} secondes".format(execution_time))
print("-----------------")
frere_jacques_notes = [(392, 150), (392, 150), (440, 150), (392, 150), (523, 150), (493, 300)]
for frequency, duration in frere_jacques_notes:
    winsound.Beep(frequency, duration)







