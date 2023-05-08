import yfinance as yf
import pandas as pd
import talib as ta
from talib import RSI
import matplotlib.pyplot as plt
from skopt import gp_minimize
from skopt.space import Integer
from skopt.utils import use_named_args
from skopt.space import Integer, Categorical
from datetime import datetime
import winsound
import time
start_time = time.time()  # Enregistre l'heure de début
SMA = 'SMA'
EMA = 'EMA'


"CAC 40 (^FCHI)"
"CMC Crypto 200 Index by Solacti (^CMC200)"
#Paramètres fixes:---------------------------------------------------
action = '^FCHI'
periode = '1d'
start_date = datetime.strptime('2021-09-18', '%Y-%m-%d')
initial_capital = 1000
coef_TP_longs = 1
coef_TP_shorts = 1
#Coller les paramètres ici:-----------------------------------------
levier = 4
take_profit_long = 165
stop_loss = 19
take_profit_short_0 = 25
stop_loss_short = 5
fast_length = 124
slow_length = 10
signal_length = 139
trend_length = 94
f = 45
s = 83
sma_source = SMA
sma_signal = SMA
sensi_longs = 0.65
sensi_shorts = 0.18
rsi_high = 60
rsi_low = 40
#--------------------------------------------------------------------





#Initialisation
data = yf.Ticker(action)
prix = data.history(period=periode, start=start_date)
take_profit_long = take_profit_long/100
stop_loss = stop_loss/100
take_profit_short_0 = take_profit_short_0/100
stop_loss_short = stop_loss_short/100
frais = 1-(0.075/100)
solde = initial_capital
closed_trades = 0
prix_entree = prix['Close'][1]
solde_max = initial_capital
solde_min = initial_capital
take_profit = take_profit_long
take_profit_short = take_profit_short_0
opération = ''
balances = [initial_capital] + [0] * (len(prix) - 1)
profit_longs = 0
pertes_longs = 0
profit_shorts = 0
pertes_shorts = 0
trades_longs = 0
trades_shorts = 0
#calculs
trend_ema = ta.EMA(prix['Close'], trend_length)
fast_ma = ta.EMA(prix['Close'], fast_length) if sma_source == 'EMA' else ta.SMA(prix['Close'], fast_length)
slow_ma = ta.EMA(prix['Close'], slow_length) if sma_source == 'EMA' else ta.SMA(prix['Close'], slow_length)
macd = fast_ma - slow_ma
signal = ta.EMA(macd, signal_length) if sma_signal == 'EMA' else ta.SMA(macd, signal_length)
rsi = RSI(prix['Close'], timeperiod=14)

# Tracé du graphique pour le prix du bitcoin
fig, ax = plt.subplots(figsize=(40, 24))
ax.plot(prix.index, prix['Close'], label='Prix de clôture', lw=0.2, color='blue')
ax.set_xlabel('Date')
ax.set_ylabel('Prix en euros')

# Création de la deuxième échelle y pour le solde
ax2 = ax.twinx()
ax2.set_ylabel('Solde en euros')


for i in range(len(prix.index)):

    #signaux de long et de short
    long_entry = macd[i] > signal[i] and ta.EMA(prix['Close'], f)[i] > ta.EMA(prix['Close'], s)[i] and prix['Close'][i] > trend_ema[i] and rsi[i] < rsi_low
    short_entry = macd[i] < signal[i] and ta.EMA(prix['Close'], f)[i] < ta.EMA(prix['Close'], s)[i] and prix['Close'][i] < trend_ema[i] and rsi[i] > rsi_high

    tp_long = prix['Close'][i] >= (prix_entree * (1 + take_profit)) 
    sl_long = prix['Close'][i] <= (prix_entree * (1 - (stop_loss / levier)))
    tp_short = prix['Close'][i] <= (prix_entree * (1 - take_profit_short))
    sl_short = prix['Close'][i] >= (prix_entree * (1 + (stop_loss_short / levier)))

    if short_entry and opération != 'Short' and solde > 0:
        if opération == 'Long':
            solde = solde*(1+levier*((prix['Close'][i]/prix_entree)-1))*frais
            closed_trades += 1
            trades_longs += 1
            if solde > solde_max : solde_max = solde
            if solde < solde_min : solde_min = solde
            if solde*levier*((prix['Close'][i]/prix_entree)-1)*frais > 0:
                profit_longs = profit_longs + solde*levier*((prix['Close'][i]/prix_entree)-1)*frais
            else:
                pertes_longs = pertes_longs + solde*levier*((prix['Close'][i]/prix_entree)-1)*frais
            
        prix_entree = prix['Close'][i]
        ax.scatter(prix.index[i], prix['Close'][i], marker='v', color='b', s=10)
        take_profit = take_profit_long
        opération = 'Short'

    elif long_entry and opération != 'Long' and solde > 0:
        if opération == 'Short':
            solde = solde*(1+levier*(1-(prix['Close'][i]/prix_entree)))*frais
            closed_trades += 1
            trades_shorts += 1
            if solde > solde_max : solde_max = solde
            if solde < solde_min : solde_min = solde
            if solde*levier*((prix['Close'][i]/prix_entree)-1)*frais > 0:
                profit_shorts = profit_shorts + solde*levier*((prix['Close'][i]/prix_entree)-1)*frais
            else:
                pertes_shorts = pertes_shorts + solde*levier*((prix['Close'][i]/prix_entree)-1)*frais
            
        prix_entree = prix['Close'][i]
        ax.scatter(prix.index[i], prix['Close'][i], marker='^', color='b', s=10)
        take_profit_short = take_profit_short_0
        opération = 'Long'

    elif tp_long and opération == 'Long':
        solde = solde*(1+levier*((prix['Close'][i]/prix_entree)-1))*frais
        closed_trades += 1
        trades_longs += 1
        if solde > solde_max : solde_max = solde
        if solde < solde_min : solde_min = solde
        take_profit = take_profit*coef_TP_longs
        take_profit_short = take_profit_short_0
        opération = 'TP Long'
        ax.scatter(prix.index[i], prix['Close'][i], marker='.', color='g', s=50)
        profit_longs = profit_longs + solde*levier*((prix['Close'][i]/prix_entree)-1)*frais
        
    elif sl_long and opération == 'Long':
        solde = solde*(1+levier*((prix['Close'][i]/prix_entree)-1))*frais
        closed_trades += 1
        trades_longs += 1
        if solde > solde_max : solde_max = solde
        if solde < solde_min : solde_min = solde
        take_profit = take_profit_long
        take_profit_short = take_profit_short_0
        opération = 'SL Long'
        ax.scatter(prix.index[i], prix['Close'][i], marker='x', color='r', s=10)
        pertes_longs = pertes_longs + solde*levier*((prix['Close'][i]/prix_entree)-1)*frais
        
    elif tp_short and opération == 'Short':
        solde = solde*(1+levier*(1-(prix['Close'][i]/prix_entree)))*frais
        closed_trades += 1
        trades_shorts += 1
        if solde > solde_max : solde_max = solde
        if solde < solde_min : solde_min = solde
        take_profit = take_profit_long
        take_profit_short = take_profit_short*coef_TP_shorts
        opération = 'TP Short'
        ax.scatter(prix.index[i], prix['Close'][i], marker='.', color='g', s=50)
        profit_shorts = profit_shorts + solde*levier*((prix['Close'][i]/prix_entree)-1)*frais
        
    elif sl_short and opération == 'Short':
        solde = solde*(1+levier*(1-(prix['Close'][i]/prix_entree)))*frais
        closed_trades += 1
        trades_shorts += 1
        if solde > solde_max : solde_max = solde
        if solde < solde_min : solde_min = solde
        take_profit = take_profit_long
        take_profit_short = take_profit_short_0
        opération = 'SL Short'
        ax.scatter(prix.index[i], prix['Close'][i], marker='x', color='r', s=10)
        pertes_shorts = pertes_shorts + solde*levier*((prix['Close'][i]/prix_entree)-1)*frais
        
    if solde <= 0:
        print('Bankrupt le : ', prix.index[i])
        ax.scatter(prix.index[i], prix['Close'][i], marker='X', color='r', s=500)
        break
    balances[i] = solde



# Tracer les courbes
ax2.plot(prix.index, balances, label='Solde', lw=0.5, color='red')
ax2.set_ylim(bottom=0, top=max(balances))
ax.legend()
ax2.legend()
plt.show()

#rendement annuel
end_date = datetime.strptime(prix.index[-1].strftime('%Y-%m-%d'), '%Y-%m-%d')
total_days = (end_date - start_date).days
years = total_days / 365
roi = (solde / initial_capital)
cagr = (roi ** (1 / years)) - 1
cagr_percentage = cagr * 100

#Résultats
print('--------------------')
print('Solde final :', "{:,}".format(round(solde)), '€')
print('Rendement total:', "{:,}".format(round((roi)*100,)),'%')
print('Rendement annuel :', "{:,}".format((round(cagr_percentage))),'%')
print('Trades :', "{:,}".format(closed_trades))
print('Trades longs:', "{:,}".format(trades_longs))
print('Trades shorts:', "{:,}".format(trades_shorts))
print('Solde max :',"{:,}".format(round(solde_max,2)))
print('Solde min :',"{:,}".format(round(solde_min,2)))
print('Rendement longs :', "{:,}".format(((profit_longs / -pertes_longs) * 100) if pertes_longs != 0 else 0), '%')
print('Rendement Shorts :', "{:,}".format(((profit_shorts / -pertes_shorts) * 100) if pertes_shorts != 0 else 0), '%')
end_time = time.time()  # Enregistre l'heure de fin
execution_time = end_time - start_time  # Calcule le temps d'exécution
print("Temps d'exécution : {:.2f} secondes".format(execution_time))
print('--------------------')

frere_jacques_notes = [(392, 150), (392, 150), (440, 150), (392, 150), (523, 150), (493, 300)]
for frequency, duration in frere_jacques_notes:
    winsound.Beep(frequency, duration)




