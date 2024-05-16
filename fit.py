import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit


# Define the fit functions
def loading(x, A, gamma1, nu, bg):
   y = A*(1-np.exp(-x*gamma1))/(1+np.exp(-x*gamma1)/nu) + bg
   return y

def depleting(x, N0, gamma, beta, bg):
   y = N0*np.exp(-x*gamma)/(1+N0*beta/gamma*(1-np.exp(-x*gamma))) + bg
   return y

def ld_cycle(x, ydata, A, gamma, nu, beta, xls, xds):
   bg = np.ma.masked_array(ydata, mask=(x > xls)).mean()
   y = np.ones_like(x)*bg
   y = np.where(x > xls, loading(x - xls, A, 2*A*beta+gamma, nu, bg), y)
   y = np.where(x > xds, depleting(x - xds, loading(xds-xls, A,  2*A*beta+gamma, nu, bg)-bg, gamma, beta, bg), y)
   return y




#print(loading(30, 210,  0.8, 5, 3)-3)
#exit()
   #return np.concatenate([np.ones(nstartl)*bg, loading(x[nstartl:nstartd]-x[nstartl], A, 2*A*beta+gamma, nu, bg),
                         #depleting(x[nstartd:]-x[nstartd],loading(x[nstartd]-x[nstartl], A,  2*A*beta+gamma, nu, bg)-bg, gamma, beta, bg)])



f = open('04-24-24_a.txt', 'r') # 'r' = read
data = np.genfromtxt(f, delimiter=' ')



xdata = np.asarray(data[:,0])
y1data = np.asarray(data[:,1])
y2data = np.asarray(data[:,2])





guesstotal1 = [400000, 0.1, 1, 0, 8, 28] 
guesstotal2 = [200, 0.2, 3, 0, 5.8, 40]
bounds2 =[(0,0,0,0,0,0),(np.inf,np.inf,50,np.inf,np.inf,np.inf)]
pars1, cov1 = curve_fit(lambda x, A, gamma, nu, beta, xls, xds: ld_cycle(x, y1data, A, gamma, nu, beta, xls, xds), xdata, y1data, p0=guesstotal1, bounds = bounds2)
pars2, cov2 = curve_fit(lambda x, A, gamma, nu, beta, xls, xds: ld_cycle(x, y2data, A, gamma, nu, beta, xls, xds), xdata, y2data, p0=guesstotal2, bounds = bounds2)
#pars2, cov2 = curve_fit(lambda x, A, gamma, nu, beta: ld_cycle(x, A, gamma, nu, beta, y2bg, 0, 0), xdata, y2data, p0=guesstotal2, bounds = bounds2)
print(f"amplitudes: 1. {pars1[0]}\t 2. {pars2[0]}")
print(f"gamma: 1. {pars1[1]}\t 2. {pars2[1]}")
print(f"nu: 1. {pars1[2]}\t 2. {pars2[2]}")
print(f"beta: 1. {pars1[3]}\t 2. {pars2[3]}")


fit1 = ld_cycle(xdata, y1data, pars1[0], pars1[1], pars1[2], pars1[3], pars1[4], pars1[5])
fit2 = ld_cycle(xdata, y2data, pars2[0], pars2[1], pars2[2], pars2[3], pars2[4], pars2[5])



plt.figure(2)
plt.plot(xdata, y2data*500, '-', label='peak value')
plt.plot(xdata, fit2*500, '-', label='fit')
plt.plot(xdata, y1data, '-', label='sum')
plt.plot(xdata, fit1, '-', label='fit')
#plt.plot(xdata, fit_y, '-', label='fit')
plt.legend()


plt.show()
