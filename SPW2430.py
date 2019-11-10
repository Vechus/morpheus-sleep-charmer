import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
from math import log10, fabs

class SPW2430:
    def __init__(self,mcp):
        self.chan = AnalogIn(mcp, MCP.P0) # non so a quale PIN è collegato (decidiamo noi a quali metterli)
        
        # da DATASHEET ricavo i parametri: 
        # 0)ADC MCP3008: 10bit
        # 1)the microphone requires 3.3V DC
        # 2)0.67V DC bias 
        # 3)use the “quietest” supply available (on an Arduino, this would be the 3.3V supply). (similar to GA1A12S202) 
       
        self.Vrange = 3.3 # (1)  
        self.rawRange = 1023.0 # 2**Nbit con Nbit=10 (0) 
        #V_bias= 0.67 a ingresso nullo uscita di 0.67 V

    def read_noise(self):

        noise = self.chan.value >> 6 #lettura di questo valore in bit
        #Tramite questa conversione in teoria restituisce il valore convertito in dB

        #Non sono sicura dello 0.67, non va magari sottratto all'interno del range? 
        #V_noise = (noise * self.Vrange/self.rawRange) - 0.67 
        #Conversione in Pa tramite la sensitività dello strumento
        #moltiplico per 1000 per trasformare in mV e divido per 7.9433 che è la sensitività om mV/Pa
        #P_noise = (fabs(V_noise + 1E-05)*1000)/7.9433  
        #classica conversione dai Pa ai dB
        #dB_noise = 20*log10(P_noise/0.00002)
        V_noise = fabs((noise * self.Vrange/self.rawRange) - 0.67) + 0.67
        #dB_noise = -42 + 20*log10(1/V_noise) + 20*log10(self.rawRange)
        #dB_noise = -42 + 20*log10(7.9e-03/V_noise)
        dB_noise = 42 + 20*log10(V_noise/0.67)
        #print("noise {} V_noise {} db {}".format(noise, V_noise, dB_noise))

        return noise # restituisce il valore senza però riposare per 30 secondi come nel LightSensor
      

      
