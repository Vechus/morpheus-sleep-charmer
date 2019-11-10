#from adafruit_mcp3xxx.mcp3008 import MCP3008 
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn 
 
class GA1A12S202:     # Inizializziamo la classe passandogli l'oggetto adc e fissiamo il canale fisico  
    # (eventualmente poi faremo anche quello intercambiabile) 
    def __init__(self, mcp): 
        self.chan = AnalogIn(mcp, MCP.P1)
        # Valori da manuale sensore a 3.3V (per averli pronti da usare) 
        self.logRange = 5.0 
        self.rawRange = 1024.0 
 
    # Una volta inizializzato possiamo leggere i valori dal canale e fornire una funzione che trasformi il risultato 
    def read_light(self): 
        # Leggo il valore dall'ADC 
        adcVal = self.chan.value >> 6 #self.mcp.read(MCP.P1) #self.chan.value value not working properly, to be checked
 
        # Trasformo il valore (formula da manuale) 
        logLux = adcVal * self.logRange / self.rawRange 
        # Conversione da scala logaritmica 
        return 10**logLux  
 
 
