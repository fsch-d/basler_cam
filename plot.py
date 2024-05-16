import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit



f = open('05-02_IR.txt', 'r') # 'r' = read
data = np.genfromtxt(f, delimiter=' ')



xdata = np.asarray(data[:,0])
y1data = np.asarray(data[:,1])
y2data = np.asarray(data[:,2])








plt.figure(1)
plt.plot(xdata, y2data*500, '-', label='peak value')
plt.plot(xdata, y1data, '-', label='sum')
plt.legend()


plt.show()
